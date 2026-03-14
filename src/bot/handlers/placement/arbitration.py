"""
Handlers арбитража — сторона владельца канала.
Этап 3.3 — управление входящими заявками на размещение.

Callback prefix: arbitration:*
"""

import logging
import re
from datetime import UTC, datetime
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.placement.arbitration import (
    get_arbitration_card_kb,
    get_arbitration_list_kb,
    get_reject_reason_kb,
)
from src.bot.keyboards.shared.main_menu import MainMenuCB
from src.bot.states.arbitration import ArbitrationStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementStatus
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = Router(name="arbitration_owner")

# =============================================================================
# БИЗНЕС-КОНСТАНТЫ
# =============================================================================

REJECT_INVALID_DELTA_1: float = -10.0
REJECT_INVALID_DELTA_2: float = -15.0
REJECT_INVALID_DELTA_3: float = -20.0
REJECT_FREQUENT_DELTA: float = -5.0
REJECT_FREQUENT_THRESHOLD_PCT: int = 50
BAN_DURATION_DAYS: int = 7
PERMANENT_BAN_VIOLATIONS: int = 5
MAX_COUNTER_OFFER_ROUNDS: int = 3
SLA_OWNER_RESPONSE_HOURS: int = 24
SLA_COUNTER_OFFER_HOURS: int = 24
OWNER_PAYOUT_PCT: int = 80
PLATFORM_FEE_PCT: int = 20
REJECTION_REASON_MIN_LEN: int = 10

# Предустановленные причины отказа
REJECTION_REASONS = {
    "topic_mismatch": "🚫 Не моя тематика",
    "low_quality": "📝 Низкое качество текста",
    "bad_timing": "📅 Неудобное время размещения",
    "low_price": "💰 Цена слишком низкая",
    "paused": "🔒 Временно не принимаю рекламу",
    "other": "✍️ Другая причина",
}

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_time_left(expires_at: datetime) -> str:
    """Получить оставшееся время до истечения."""
    now = datetime.now(UTC)
    delta = expires_at - now
    if delta.total_seconds() <= 0:
        return "ИСТЕКЛО"
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    return f"{hours}ч {minutes}мин"


def validate_rejection_reason(text: str) -> tuple[bool, str]:
    """
    Валидировать причину отклонения.

    Returns:
        (is_valid, error_message)
    """
    if len(text) < REJECTION_REASON_MIN_LEN:
        return False, f"Минимум {REJECTION_REASON_MIN_LEN} символов"

    if not re.search(r"[а-яёa-z]", text, re.IGNORECASE):
        return False, "Должна содержать буквы"

    # Проверка на бессмыслицу (5+ одинаковых символов)
    if re.search(r"(.)\1{4,}", text):
        return False, "Недопустимый формат"

    # Чёрный список
    blacklist = ["asdf", "1234", "qwerty", "нет", "no"]
    if any(b in text.lower() for b in blacklist):
        return False, "Недопустимая причина"

    return True, ""


async def check_channel_owner(callback: CallbackQuery, channel) -> bool:
    """
    Проверить что пользователь — владелец канала.

    Args:
        callback: Callback query.
        channel: Объект канала.

    Returns:
        True если владелец, False иначе.
    """
    if not channel or channel.owner_user_id != callback.from_user.id:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return False
    return True


# =============================================================================
# H1: СПИСОК ВХОДЯЩИХ ЗАЯВОК
# =============================================================================


@router.callback_query(F.data == "arbitration:list")
async def handle_arbitration_list(callback: CallbackQuery) -> None:
    """H1 — Список входящих заявок для владельца."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    async with async_session_factory() as session:
        from src.db.repositories.user_repo import UserRepo

        user_repo = UserRepo(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        repo = PlacementRequestRepo(session)
        requests = await repo.get_pending_for_owner(user.id)

    if not requests:
        text = (
            "📋 <b>Входящие заявки</b>\n\n"
            "У вас нет входящих заявок.\n\n"
            "Новые заявки будут появляться здесь, когда рекламодатели выберут ваш канал."
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 В меню", callback_data="main:main_menu")
        kb.adjust(1)
    else:
        count = len(requests)
        text = f"📋 <b>Входящие заявки</b>\n\nВходящих заявок: {count}\n\nВыберите заявку:"

        requests_data = [
            {
                "id": r.id,
                "advertiser_name": r.advertiser.username or f"ID:{r.advertiser_id}",
                "status": r.status.value,
            }
            for r in requests
        ]
        kb = get_arbitration_list_kb(requests_data)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H2: КАРТОЧКА ЗАЯВКИ
# =============================================================================


@router.callback_query(F.data.startswith("arbitration:view:"))
async def handle_view_request(callback: CallbackQuery) -> None:
    """H2 — Карточка входящей заявки для владельца."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        from src.db.models.analytics import TelegramChat

        channel = await session.get(TelegramChat, placement.channel_id)
        if not await check_channel_owner(callback, channel):
            return

        # Проверка на истечение
        is_expired = placement.expires_at < datetime.now(UTC)
        time_left = get_time_left(placement.expires_at)

    # Сформировать текст карточки
    channel_username = channel.username or f"ID:{channel.id}"
    owner_payout = float(placement.proposed_price) * (OWNER_PAYOUT_PCT / 100)

    post_text_preview = (
        placement.final_text[:800] + "..."
        if len(placement.final_text) > 800
        else placement.final_text
    )

    text = (
        f"📋 <b>Заявка #{placement.id} от рекламодателя</b>\n\n"
        f"📺 Канал: @{channel_username}\n"
        f"💰 Предложенная цена: {placement.proposed_price:.0f} ₽ → вы получите: {owner_payout:.0f} ₽\n"
        f"📅 Желаемая дата: {placement.proposed_schedule.strftime('%d.%m.%Y') if placement.proposed_schedule else 'Не указана'}\n"
        f"⏱ Истекает через: {time_left}\n"
        f"💱 Раунд переговоров: {placement.counter_offer_count}/{MAX_COUNTER_OFFER_ROUNDS}\n"
    )

    if is_expired:
        text += "\n⚠️ <b>Срок действия заявки истёк!</b>\n"

    text += (
        f"\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>ТЕКСТ ПОСТА:</b>\n"
        f"{post_text_preview}\n\n"
        f"(медиа: {'есть' if placement.final_text else 'нет'})"
    )

    kb = get_arbitration_card_kb(placement_id)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H3: ПРИНЯТЬ ЗАЯВКУ
# =============================================================================


@router.callback_query(F.data.startswith("arbitration:accept:"))
async def handle_accept(callback: CallbackQuery) -> None:
    """H3 — Владелец принимает заявку."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat

        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        channel = await session.get(TelegramChat, placement.channel_id)
        if not await check_channel_owner(callback, channel):
            return

        if placement.status not in (PlacementStatus.PENDING_OWNER, PlacementStatus.COUNTER_OFFER):
            await callback.answer("❌ Нельзя принять заявку в текущем статусе", show_alert=True)
            return

        service = PlacementRequestService(
            session=session,
            placement_repo=PlacementRequestRepo(session),
            channel_settings_repo=ChannelSettingsRepo(session),
            reputation_repo=ReputationRepo(session),
            billing_service=None,
        )

        try:
            await service.owner_accept(placement_id, channel.owner_user_id)
            await callback.answer(
                "✅ Заявка принята! Ожидайте оплаты от рекламодателя (до 24 ч)", show_alert=False
            )

            text = (
                f"✅ <b>Заявка принята!</b>\n\n"
                f"Рекламодатель должен оплатить заявку в течение {SLA_OWNER_RESPONSE_HOURS} ч.\n"
                f"После оплаты средства будут заморожены, а публикация запланирована."
            )

            kb = InlineKeyboardBuilder()
            kb.button(text="📋 Все заявки", callback_data="arbitration:list")
            kb.adjust(1)

            await safe_callback_edit(callback.message, text, reply_markup=kb)
        except ValueError as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# =============================================================================
# H4: МЕНЮ ОТКЛОНЕНИЯ
# =============================================================================


@router.callback_query(F.data.startswith("arbitration:reject:"))
async def handle_reject_menu(callback: CallbackQuery) -> None:
    """H4 — Показать меню выбора причины отклонения."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat

        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        channel = await session.get(TelegramChat, placement.channel_id)
        if not await check_channel_owner(callback, channel):
            return

    kb = get_reject_reason_kb(placement_id)

    text = (
        "❌ <b>Отклонение заявки</b>\n\n"
        "Выберите причину отклонения:\n\n"
        "⚠️ При необоснованном отказе вы можете получить штраф к репутации."
    )

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H4a: ВЫБОР ПРИЧИНЫ ОТКЛОНЕНИЯ
# =============================================================================


@router.callback_query(F.data.startswith("arbitration:reject_reason:"))
async def handle_reject_reason_select(callback: CallbackQuery, state: FSMContext) -> None:
    """H4a — Выбор конкретной причины отказа."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    parts = callback.data.split(":")
    placement_id = int(parts[2])
    reason_code = parts[3]

    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat

        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        channel = await session.get(TelegramChat, placement.channel_id)
        if not await check_channel_owner(callback, channel):
            return

    if reason_code == "other":
        # Запросить текстовое пояснение
        await state.update_data(placement_id=placement_id, reason_code=reason_code)
        await state.set_state(ArbitrationStates.waiting_rejection_reason)

        await callback.answer(
            "✍️ Введите причину отклонения (минимум 10 символов):", show_alert=True
        )
    else:
        # Использовать предустановленную причину
        reason_text = REJECTION_REASONS.get(reason_code, reason_code)
        await handle_reject_execute(callback, state, placement_id, reason_code, reason_text)


# =============================================================================
# H4b: ВВОД ТЕКСТОВОЙ ПРИЧИНЫ
# =============================================================================


@router.message(ArbitrationStates.waiting_rejection_reason)
async def process_rejection_reason_text(message: Message, state: FSMContext) -> None:
    """H4b — Получить текстовую причину отказа."""
    if message.text is None:
        await message.answer("❌ Введите текстовую причину.")
        return

    text = message.text.strip()

    is_valid, error_msg = validate_rejection_reason(text)

    if not is_valid:
        await message.answer(f"❌ {error_msg}. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    placement_id = data.get("placement_id")
    reason_code = data.get("reason_code")

    if not placement_id:
        await message.answer("❌ Ошибка сессии. Попробуйте ещё раз.")
        await state.clear()
        return

    # Выполнить отклонение
    async with async_session_factory() as session:
        await handle_reject_execute_internal(
            session=session,
            callback=None,
            state=state,
            placement_id=placement_id,
            reason_code=reason_code or "other",
            reason_text=text,
            message=message,
        )


async def handle_reject_execute_internal(
    session,
    callback: CallbackQuery | None,
    state: FSMContext,
    placement_id: int,
    reason_code: str,
    reason_text: str | None,
    message: Message | None = None,
) -> None:
    """Внутренняя функция выполнения отклонения."""
    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        if callback:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
        elif message:
            await message.answer("❌ Заявка не найдена")
        return

    # Получить владельца
    from src.db.models.analytics import TelegramChat

    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel:
        return

    owner_id = channel.owner_user_id

    # Сформировать финальную причину
    final_reason = reason_text or REJECTION_REASONS.get(reason_code, reason_code)

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        await service.owner_reject(placement_id, owner_id, final_reason)

        # Получить репутацию
        rep_repo = ReputationRepo(session)
        rep_score = await rep_repo.get_by_user(owner_id)
        owner_score = rep_score.owner_score if rep_score else 5.0

        text = (
            f"❌ <b>Заявка отклонена</b>\n\n"
            f"Причина: {final_reason}\n"
            f"Ваша репутация владельца: ⭐ {owner_score:.1f}"
        )

        kb = InlineKeyboardBuilder()
        kb.button(text="📋 Все заявки", callback_data="arbitration:list")
        kb.adjust(1)

        if callback:
            await safe_callback_edit(callback.message, text, reply_markup=kb)
            await callback.answer()
        elif message:
            await message.answer(text, reply_markup=kb)

        await state.clear()

    except ValueError as e:
        error_text = f"❌ Ошибка: {e}"
        if callback:
            await callback.answer(error_text, show_alert=True)
        elif message:
            await message.answer(error_text)


async def handle_reject_execute(
    callback: CallbackQuery,
    state: FSMContext,
    placement_id: int,
    reason_code: str,
    reason_text: str | None,
) -> None:
    """H4c — Применить отклонение (вызывается из H4a)."""
    async with async_session_factory() as session:
        await handle_reject_execute_internal(
            session=session,
            callback=callback,
            state=state,
            placement_id=placement_id,
            reason_code=reason_code,
            reason_text=reason_text,
            message=None,
        )


# =============================================================================
# H5: КОНТР-ПРЕДЛОЖЕНИЕ
# =============================================================================


@router.callback_query(F.data.startswith("arbitration:counter:"))
async def handle_counter_offer_init(callback: CallbackQuery, state: FSMContext) -> None:
    """H5 — Начало флоу контр-предложения."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat

        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        channel = await session.get(TelegramChat, placement.channel_id)
        if not await check_channel_owner(callback, channel):
            return

        # Проверка лимита раундов
        if placement.counter_offer_count >= MAX_COUNTER_OFFER_ROUNDS:
            await callback.answer(
                f"❌ Лимит раундов ({MAX_COUNTER_OFFER_ROUNDS}) исчерпан", show_alert=True
            )
            return

        if placement.status != PlacementStatus.PENDING_OWNER:
            await callback.answer(
                "❌ Нельзя сделать контр-предложение в текущем статусе", show_alert=True
            )
            return

    await state.update_data(placement_id=placement_id)
    await state.set_state(ArbitrationStates.waiting_counter_price)

    text = (
        f"💱 <b>Контр-предложение</b>\n\n"
        f"Текущая цена: {placement.proposed_price:.0f} ₽\n"
        f"Введите вашу цену (минимум 100 ₽):"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Отмена", callback_data=f"arbitration:view:{placement_id}")
    kb.adjust(1)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H5a: ВВОД ЦЕНЫ КОНТР-ПРЕДЛОЖЕНИЯ
# =============================================================================


@router.message(ArbitrationStates.waiting_counter_price)
async def process_counter_price(message: Message, state: FSMContext) -> None:
    """H5a — Получить новую цену контр-предложения."""
    if message.text is None:
        await message.answer("❌ Введите число.")
        return

    text = message.text.strip()

    if not text.isdigit():
        await message.answer("❌ Цена должна быть числом.")
        return

    counter_price = int(text)

    if counter_price < 100:
        await message.answer("❌ Минимальная цена: 100 ₽.")
        return

    await state.update_data(counter_price=counter_price)
    await state.set_state(ArbitrationStates.waiting_counter_comment)

    await message.answer(
        "✅ Цена принята.\n\nДобавьте комментарий или нажмите /skip чтобы пропустить:"
    )


# =============================================================================
# H5b: ВВОД КОММЕНТАРИЯ
# =============================================================================


@router.message(ArbitrationStates.waiting_counter_comment)
async def process_counter_comment(message: Message, state: FSMContext) -> None:
    """H5b — Получить комментарий к контр-предложению или пропустить."""
    data = await state.get_data()
    placement_id = data.get("placement_id")
    counter_price = data.get("counter_price")

    if not placement_id or not counter_price:
        await message.answer("❌ Ошибка сессии. Попробуйте ещё раз.")
        await state.clear()
        return

    # counter_comment не используется напрямую — передаётся в service.owner_counter_offer()
    # Если /skip — None, иначе текст комментария

    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat

        channel = await session.get(TelegramChat, placement_id)
        if not channel:
            await message.answer("❌ Канал не найден.")
            await state.clear()
            return

        service = PlacementRequestService(
            session=session,
            placement_repo=PlacementRequestRepo(session),
            channel_settings_repo=ChannelSettingsRepo(session),
            reputation_repo=ReputationRepo(session),
            billing_service=None,
        )

        try:
            await service.owner_counter_offer(
                placement_id=placement_id,
                owner_id=channel.owner_user_id,
                proposed_price=Decimal(str(counter_price)),
                proposed_schedule=None,
            )

            await state.clear()

            text = (
                f"💱 <b>Контр-предложение отправлено!</b>\n\n"
                f"Новая цена: {counter_price:.0f} ₽\n"
                f"Рекламодатель ответит в течение {SLA_COUNTER_OFFER_HOURS} ч."
            )

            kb = InlineKeyboardBuilder()
            kb.button(text="📋 Все заявки", callback_data="arbitration:list")
            kb.adjust(1)

            await message.answer(text, reply_markup=kb)

        except ValueError as e:
            await message.answer(f"❌ Ошибка: {e}")


# =============================================================================
# H6: ТОЧКА ВХОДА ИЗ ГЛАВНОГО МЕНЮ
# =============================================================================


@router.callback_query(MainMenuCB.filter(F.action == "my_requests"))
async def handle_my_requests(callback: CallbackQuery) -> None:
    """H6 — Точка входа из главного меню owner — редирект на arbitration:list."""
    await handle_arbitration_list(callback)
