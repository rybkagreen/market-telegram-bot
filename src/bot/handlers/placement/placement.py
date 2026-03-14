"""
Handlers размещения — сторона рекламодателя.
Этап 3.2 — создание и управление заявками на размещение.

Callback prefix: placement:*
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InaccessibleMessage,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.placement.placement import (
    get_cancel_confirm_kb,
    get_placement_card_kb,
    get_placement_list_kb,
)
from src.bot.keyboards.shared.channels_catalog import ChannelsCB
from src.bot.states.placement import PlacementStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementStatus
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = Router(name="placement_advertiser")

# =============================================================================
# БИЗНЕС-КОНСТАНТЫ
# =============================================================================

CANCEL_BEFORE_DELTA: float = -5.0
CANCEL_AFTER_DELTA: float = -20.0
CANCEL_SYSTEMATIC_DELTA: float = -20.0
CANCEL_SYSTEMATIC_THRESHOLD: int = 3
REFUND_BEFORE_ESCROW_PCT: int = 100
REFUND_AFTER_ESCROW_PCT: int = 50
OWNER_PAYOUT_PCT: int = 80
PLATFORM_FEE_PCT: int = 20
SLA_OWNER_RESPONSE_HOURS: int = 24
SLA_PAYMENT_HOURS: int = 24
MAX_COUNTER_OFFER_ROUNDS: int = 3

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_status_emoji(status: PlacementStatus) -> str:
    """Получить emoji для статуса."""
    emoji_map = {
        PlacementStatus.PENDING_OWNER: "⏳",
        PlacementStatus.COUNTER_OFFER: "💱",
        PlacementStatus.PENDING_PAYMENT: "💳",
        PlacementStatus.ESCROW: "🔒",
        PlacementStatus.PUBLISHED: "✅",
        PlacementStatus.FAILED: "❌",
        PlacementStatus.REFUNDED: "↩️",
        PlacementStatus.CANCELLED: "🚫",
    }
    return emoji_map.get(status, "📝")


def get_status_ru(status: PlacementStatus) -> str:
    """Получить русское описание статуса."""
    status_map = {
        PlacementStatus.PENDING_OWNER: "Ожидает ответа владельца",
        PlacementStatus.COUNTER_OFFER: "Контр-предложение",
        PlacementStatus.PENDING_PAYMENT: "Ожидает оплаты",
        PlacementStatus.ESCROW: "Средства заморожены",
        PlacementStatus.PUBLISHED: "Опубликовано",
        PlacementStatus.FAILED: "Ошибка публикации",
        PlacementStatus.REFUNDED: "Возврат средств",
        PlacementStatus.CANCELLED: "Отменено",
    }
    return status_map.get(status, "Неизвестно")


async def check_placement_owner(callback: CallbackQuery, placement) -> bool:
    """
    Проверить что пользователь — владелец заявки (advertiser).

    Args:
        callback: Callback query.
        placement: Объект заявки.

    Returns:
        True если владелец, False иначе.
    """
    if placement.advertiser_id != callback.from_user.id:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return False
    return True


# =============================================================================
# H1: СПИСОК ЗАЯВОК
# =============================================================================


@router.callback_query(F.data == "placement:list")
async def handle_placement_list(callback: CallbackQuery) -> None:
    """H1 — Список заявок рекламодателя."""
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
        placements = await repo.get_by_advertiser(user.id, limit=10)

    if not placements:
        text = (
            "📋 <b>Мои заявки</b>\n\n"
            "У вас пока нет активных заявок.\n\n"
            "Создайте первую заявку на размещение в канале!"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="📺 Выбрать канал", callback_data="placement:select_channel")
        kb.button(text="🔙 В меню", callback_data="main:main_menu")
        kb.adjust(1)
    else:
        text = "📋 <b>Мои заявки</b>\n\nВыберите заявку:"
        placements_data = [
            {
                "id": p.id,
                "channel_name": p.channel.username or f"ID:{p.channel_id}",
                "status": p.status.value,
            }
            for p in placements
        ]
        kb = get_placement_list_kb(placements_data)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H2: ВЫБОР КАНАЛА
# =============================================================================


@router.callback_query(F.data == "placement:select_channel")
async def handle_select_channel(callback: CallbackQuery) -> None:
    """H2 — Выбор канала для размещения из каталога."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    text = (
        "📺 <b>Выбор канала для размещения</b>\n\n"
        "Перейдите в каталог каналов и выберите подходящий канал для вашей рекламы.\n\n"
        "После выбора канала вы сможете:\n"
        "• Ввести текст рекламного поста\n"
        "• Выбрать дату публикации\n"
        "• Отправить заявку владельцу"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="📺 Открыть каталог", callback_data=ChannelsCB(action="categories").pack())
    kb.button(text="◀️ Назад", callback_data="placement:list")
    kb.adjust(1)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H3: НАЧАЛО СОЗДАНИЯ ЗАЯВКИ
# =============================================================================


@router.callback_query(F.data.startswith("placement:create:"))
async def handle_create_placement(callback: CallbackQuery, state: FSMContext) -> None:
    """H3 — Начало создания заявки — показать карточку канала."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        from src.db.repositories.user_repo import UserRepo

        user_repo = UserRepo(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверка на блокировку
        rep_repo = ReputationRepo(session)
        rep_score = await rep_repo.get_by_user(user.id)
        if rep_score and rep_score.is_advertiser_blocked:
            await callback.answer("❌ Ваш аккаунт заблокирован", show_alert=True)
            return

        # Получить канал и настройки
        from src.db.models.analytics import TelegramChat

        channel = await session.get(TelegramChat, channel_id)
        if not channel or not channel.is_active:
            await callback.answer("❌ Канал не найден или не активен", show_alert=True)
            return

        settings_repo = ChannelSettingsRepo(session)
        settings = await settings_repo.get_or_create_default(channel_id, channel.owner_user_id or 0)

    # Сохранить данные в state
    await state.update_data(
        channel_id=channel_id,
        proposed_price=float(settings.price_per_post),
    )

    text = (
        f"📺 <b>Создание заявки на размещение</b>\n\n"
        f"Канал: @{channel.username or channel.title}\n"
        f"Подписчиков: {channel.member_count:,}\n"
        f"Цена за пост: {settings.price_per_post:.0f} ₽\n"
        f"Вы получаете: {float(settings.price_per_post) * 0.8:.0f} ₽ (80%)\n"
        f"Комиссия платформы: {float(settings.price_per_post) * 0.2:.0f} ₽ (20%)\n\n"
        f"Введите текст вашего рекламного поста:"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✖️ Отмена", callback_data="placement:list")
    kb.adjust(1)

    await state.set_state(PlacementStates.waiting_post_text)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H3a: ВВОД ТЕКСТА ПОСТА
# =============================================================================


@router.message(PlacementStates.waiting_post_text)
async def process_post_text(message: Message, state: FSMContext) -> None:
    """H3a — Получить текст рекламного поста."""
    if message.text is None:
        await message.answer("❌ Пожалуйста, введите текст поста.")
        return

    text = message.text.strip()

    if len(text) < 10:
        await message.answer("❌ Текст слишком короткий. Минимум 10 символов.")
        return

    if len(text) > 4096:
        await message.answer("❌ Текст слишком длинный. Максимум 4096 символов.")
        return

    await state.update_data(post_text=text)
    await state.set_state(PlacementStates.waiting_post_media)

    await message.answer(
        "✅ Текст принят.\n\nОтправьте изображение для поста или нажмите /skip чтобы пропустить:"
    )


# =============================================================================
# H3b: ВВОД МЕДИА
# =============================================================================


@router.message(PlacementStates.waiting_post_media)
async def process_post_media(message: Message, state: FSMContext) -> None:
    """H3b — Получить медиа или пропустить."""
    media_file_id = None

    if message.text and message.text.strip().lower() == "/skip":
        media_file_id = None
    elif message.photo:
        media_file_id = message.photo[-1].file_id
    elif message.document:
        media_file_id = message.document.file_id

    await state.update_data(media_file_id=media_file_id)
    await state.set_state(PlacementStates.waiting_schedule_date)

    kb = InlineKeyboardBuilder()
    kb.button(text="Сегодня", callback_data="placement:schedule:0")
    kb.button(text="Завтра", callback_data="placement:schedule:1")
    kb.button(text="Через 2 дня", callback_data="placement:schedule:2")
    kb.button(text="Указать дату", callback_data="placement:schedule:custom")
    kb.button(text="◀️ Отмена", callback_data="placement:list")
    kb.adjust(2, 2, 1)

    await message.answer(
        "✅ Медиа сохранено.\n\nВыберите дату публикации:",
        reply_markup=kb,
    )


# =============================================================================
# H3c: ВЫБОР ДАТЫ
# =============================================================================


@router.callback_query(F.data.startswith("placement:schedule:"))
async def handle_schedule_select(callback: CallbackQuery, state: FSMContext) -> None:
    """H3c — Выбор даты публикации."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    days_offset = int(callback.data.split(":")[2])

    if days_offset == -1:  # custom
        await callback.answer("📅 Введите дату в формате ДД.ММ.ГГГГ", show_alert=True)
        return

    scheduled_at = datetime.now(UTC) + timedelta(days=days_offset)

    await state.update_data(scheduled_at=scheduled_at.isoformat())

    # Собрать данные для превью
    data = await state.get_data()
    channel_id = data.get("channel_id")
    post_text = (
        data.get("post_text", "")[:100] + "..."
        if len(data.get("post_text", "")) > 100
        else data.get("post_text", "")
    )

    text = (
        f"✅ <b>Предпросмотр заявки</b>\n\n"
        f"📺 Канал: ID:{channel_id}\n"
        f"📝 Текст: {post_text}\n"
        f"📅 Дата публикации: {scheduled_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Готовы отправить заявку?"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить заявку", callback_data="placement:confirm_create")
    kb.button(text="◀️ Назад", callback_data="placement:select_channel")
    kb.adjust(1)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H3d: ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ
# =============================================================================


@router.callback_query(F.data == "placement:confirm_create")
async def handle_confirm_create(callback: CallbackQuery, state: FSMContext) -> None:
    """H3d — Финальное подтверждение — создать PlacementRequest."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    async with async_session_factory() as session:
        from src.db.repositories.campaign_repo import CampaignRepo
        from src.db.repositories.user_repo import UserRepo

        user_repo = UserRepo(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Собрать данные
        data = await state.get_data()
        channel_id = data.get("channel_id")
        proposed_price = Decimal(str(data.get("proposed_price", 100)))
        post_text = data.get("post_text", "")
        scheduled_at_str = data.get("scheduled_at")
        scheduled_at = datetime.fromisoformat(scheduled_at_str) if scheduled_at_str else None

        # Создать кампанию-заглушку для placement
        campaign_repo = CampaignRepo(session)
        campaign = await campaign_repo.create(
            advertiser_id=user.id,
            title=f"Placement #{channel_id}",
            text=post_text,
            status="draft",
        )

        # Создать заявку
        service = PlacementRequestService(
            session=session,
            placement_repo=PlacementRequestRepo(session),
            channel_settings_repo=ChannelSettingsRepo(session),
            reputation_repo=ReputationRepo(session),
            billing_service=None,  # TODO: inject billing service
        )

        try:
            placement = await service.create_request(
                advertiser_id=user.id,
                campaign_id=campaign.id,
                channel_id=channel_id,
                proposed_price=proposed_price,
                final_text=post_text,
                proposed_schedule=scheduled_at,
            )

            await state.clear()

            text = (
                f"✅ <b>Заявка отправлена!</b>\n\n"
                f"Владелец ответит в течение {SLA_OWNER_RESPONSE_HOURS} ч.\n"
                f"Номер заявки: #{placement.id}"
            )

            kb = InlineKeyboardBuilder()
            kb.button(text="📋 Мои заявки", callback_data="placement:list")
            kb.adjust(1)

            await safe_callback_edit(callback.message, text, reply_markup=kb)
            await callback.answer()

        except ValueError as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
            await state.clear()


# =============================================================================
# H4: КАРТОЧКА ЗАЯВКИ
# =============================================================================


@router.callback_query(F.data.startswith("placement:view:"))
async def handle_view_placement(callback: CallbackQuery) -> None:
    """H4 — Карточка заявки — зависит от статуса."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        if not await check_placement_owner(callback, placement):
            return

    # Сформировать текст карточки
    channel_username = placement.channel.username or f"ID:{placement.channel_id}"
    status_emoji = get_status_emoji(placement.status)
    status_ru = get_status_ru(placement.status)

    text = (
        f"{status_emoji} <b>Заявка #{placement.id} — {status_ru}</b>\n\n"
        f"📺 Канал: @{channel_username}\n"
        f"💰 Предложенная цена: {placement.proposed_price:.0f} ₽\n"
    )

    if placement.final_price:
        text += f"💰 Финальная цена: {placement.final_price:.0f} ₽\n"

    if placement.final_schedule:
        text += f"📅 Дата публикации: {placement.final_schedule.strftime('%d.%m.%Y %H:%M')}\n"

    if placement.status in (PlacementStatus.PENDING_OWNER, PlacementStatus.COUNTER_OFFER):
        text += f"⏱ Истекает: {placement.expires_at.strftime('%d.%m.%Y %H:%M')}\n"

    text += f"💱 Контр-предложений: {placement.counter_offer_count}/{MAX_COUNTER_OFFER_ROUNDS}"

    kb = get_placement_card_kb(placement_id, placement.status.value)

    await safe_callback_edit(callback.message, text, reply_markup=kb)
    await callback.answer()


# =============================================================================
# H5: ПРИНЯТЬ КОНТР-ПРЕДЛОЖЕНИЕ
# =============================================================================


@router.callback_query(F.data.startswith("placement:accept_counter:"))
async def handle_accept_counter(callback: CallbackQuery) -> None:
    """H5 — Рекламодатель принимает контр-предложение владельца."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        if not await check_placement_owner(callback, placement):
            return

        if placement.status != PlacementStatus.COUNTER_OFFER:
            await callback.answer("❌ Нет контр-предложения для принятия", show_alert=True)
            return

        service = PlacementRequestService(
            session=session,
            placement_repo=PlacementRequestRepo(session),
            channel_settings_repo=ChannelSettingsRepo(session),
            reputation_repo=ReputationRepo(session),
            billing_service=None,
        )

        try:
            await service.advertiser_accept_counter(placement_id, placement.advertiser_id)
            await callback.answer("✅ Контр-предложение принято, оплатите заявку", show_alert=False)
            # Обновить карточку
            await handle_view_placement(callback)
        except ValueError as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# =============================================================================
# H6: ОТМЕНА ЗАЯВКИ
# =============================================================================


@router.callback_query(F.data.startswith("placement:cancel:"))
async def handle_cancel_init(callback: CallbackQuery) -> None:
    """H6 — Инициация отмены — показать предупреждение о штрафе."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        if not await check_placement_owner(callback, placement):
            return

        # Рассчитать штраф
        if placement.status in (PlacementStatus.PENDING_OWNER, PlacementStatus.PENDING_PAYMENT):
            delta = CANCEL_BEFORE_DELTA
            refund_pct = REFUND_BEFORE_ESCROW_PCT
        elif placement.status == PlacementStatus.ESCROW:
            delta = CANCEL_AFTER_DELTA
            refund_pct = REFUND_AFTER_ESCROW_PCT
        else:
            delta = 0
            refund_pct = 0

        text = (
            f"⚠️ <b>Отмена заявки #{placement_id}</b>\n\n"
            f"Текущий статус: {get_status_ru(placement.status)}\n\n"
            f"Штраф за отмену: {delta} к репутации\n"
            f"Возврат средств: {refund_pct}%\n\n"
            f"Вы уверены?"
        )

        kb = get_cancel_confirm_kb(placement_id)

        await safe_callback_edit(callback.message, text, reply_markup=kb)
        await callback.answer()


@router.callback_query(F.data.startswith("placement:cancel_confirm:"))
async def handle_cancel_confirm(callback: CallbackQuery) -> None:
    """H6a — Подтверждение отмены — применить штраф."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        if not await check_placement_owner(callback, placement):
            return

        service = PlacementRequestService(
            session=session,
            placement_repo=PlacementRequestRepo(session),
            channel_settings_repo=ChannelSettingsRepo(session),
            reputation_repo=ReputationRepo(session),
            billing_service=None,
        )

        try:
            await service.advertiser_cancel(placement_id, placement.advertiser_id)
            await callback.answer("✅ Заявка отменена", show_alert=False)

            text = "✅ <b>Заявка отменена</b>\n\nСредства возвращены на баланс."
            kb = InlineKeyboardBuilder()
            kb.button(text="📋 Мои заявки", callback_data="placement:list")
            kb.adjust(1)

            await safe_callback_edit(callback.message, text, reply_markup=kb)
        except ValueError as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# =============================================================================
# H7: ОПЛАТА
# =============================================================================


@router.callback_query(F.data.startswith("placement:pay:"))
async def handle_pay_placement(callback: CallbackQuery) -> None:
    """H7 — Оплата заявки → эскроу."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        repo = PlacementRequestRepo(session)
        placement = await repo.get_by_id(placement_id)

        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        if not await check_placement_owner(callback, placement):
            return

        if placement.status != PlacementStatus.PENDING_PAYMENT:
            await callback.answer("❌ Заявка не готова к оплате", show_alert=True)
            return

        # Проверить баланс
        from src.db.repositories.user_repo import UserRepo

        user_repo = UserRepo(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        final_price = float(placement.final_price or placement.proposed_price)

        if user.balance_rub < final_price:
            text = (
                f"❌ <b>Недостаточно средств</b>\n\n"
                f"Требуется: {final_price:.0f} ₽\n"
                f"Ваш рублёвый баланс: {user.balance_rub:.0f} ₽\n\n"
                f"Пополните баланс и попробуйте снова."
            )
            kb = InlineKeyboardBuilder()
            kb.button(text="💰 Пополнить", callback_data="billing:topup")
            kb.button(text="◀️ Назад", callback_data=f"placement:view:{placement_id}")
            kb.adjust(1)

            await safe_callback_edit(callback.message, text, reply_markup=kb)
            await callback.answer()
            return

        # Оплатить
        service = PlacementRequestService(
            session=session,
            placement_repo=PlacementRequestRepo(session),
            channel_settings_repo=ChannelSettingsRepo(session),
            reputation_repo=ReputationRepo(session),
            billing_service=None,
        )

        try:
            await service.process_payment(placement_id, placement.advertiser_id)

            text = (
                f"🔒 <b>Средства заморожены</b>\n\n"
                f"Сумма: {final_price:.0f} ₽\n"
                f"Публикация запланирована на: {placement.final_schedule.strftime('%d.%m.%Y %H:%M') if placement.final_schedule else 'будет согласована'}"
            )

            kb = InlineKeyboardBuilder()
            kb.button(text="📋 Мои заявки", callback_data="placement:list")
            kb.adjust(1)

            await safe_callback_edit(callback.message, text, reply_markup=kb)
            await callback.answer()

        except ValueError as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
