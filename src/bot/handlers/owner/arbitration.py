"""Owner arbitration handler — заявки на размещение."""

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.shared.notifications import (
    notify_advertiser_accepted,
    notify_advertiser_counter,
    notify_advertiser_rejected,
)
from src.bot.states.arbitration import ArbitrationStates
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = Router()

MY_REQUESTS_SCENE = "main:my_requests"
CHANNEL_WORD = "канал"
ALL_REQUESTS_BTN = "📋 Все заявки"
SKIP_BTN = "⏩ Пропустить"

_FORMAT_NAMES = {
    "post_24h": "Пост 24ч",
    "post_48h": "Пост 48ч",
    "post_7d": "Пост 7 дней",
    "pin_24h": "Закреп 24ч",
    "pin_48h": "Закреп 48ч",
}


def _fmt_name(req: PlacementRequest) -> str:
    val = (
        req.publication_format.value
        if hasattr(req.publication_format, "value")
        else str(req.publication_format)
    )
    return _FORMAT_NAMES.get(val, val)


# ---------------------------------------------------------------------------
# Список заявок
# ---------------------------------------------------------------------------


@router.callback_query(F.data == MY_REQUESTS_SCENE)
async def show_owner_requests(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать заявки владельца."""
    if not isinstance(callback.message, Message):
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    all_reqs = await PlacementRequestRepository(session).get_by_owner(user.id)

    pending = [
        r
        for r in all_reqs
        if r.status in (PlacementStatus.pending_owner, PlacementStatus.counter_offer)
    ]
    processing = [r for r in all_reqs if r.status == PlacementStatus.pending_payment]
    escrow = [r for r in all_reqs if r.status == PlacementStatus.escrow]
    published = [r for r in all_reqs if r.status == PlacementStatus.published]

    builder = InlineKeyboardBuilder()
    for req in pending[:10]:
        ch = await session.get(TelegramChat, req.channel_id)
        ch_label = f"@{ch.username}" if ch and ch.username else str(req.channel_id)
        builder.button(
            text=f"🔴 #{req.id} {ch_label} — {req.proposed_price:.0f}₽",
            callback_data=f"own:request:{req.id}",
        )
    builder.button(text="🔙 Меню владельца", callback_data="main:own_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        f"📋 *Заявки на размещение*\n\n"
        f"🔴 Новые: *{len(pending)}*\n"
        f"🟡 В обработке: *{len(processing)}*\n"
        f"🔵 В эскроу: *{len(escrow)}*\n"
        f"🟢 Опубликованные: *{len(published)}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Детали заявки
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("own:request:fulltext:"))
async def show_fulltext(callback: CallbackQuery, session: AsyncSession) -> None:
    """Полный текст объявления."""
    if not isinstance(callback.message, Message):
        return
    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к заявке", callback_data=f"own:request:{request_id}")
    await callback.message.edit_text(
        f"📋 *Полный текст заявки #{request_id}*\n\n{req.ad_text}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^own:request:\d+$"))
async def show_request_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    """Детали заявки."""
    if not isinstance(callback.message, Message):
        return
    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    from src.db.models.channel_settings import ChannelSettings

    ch = await session.get(TelegramChat, req.channel_id)
    settings = await session.get(ChannelSettings, req.channel_id)
    advertiser = await session.get(User, req.advertiser_id)

    your_price = settings.price_per_post if settings else Decimal("1000")
    adv_username = (advertiser.username or f"id{advertiser.telegram_id}") if advertiser else "—"
    proposed_time = (
        req.proposed_schedule.strftime("%d.%m %H:%M") if req.proposed_schedule else "Не указано"
    )
    expires = req.expires_at.strftime("%d.%m %H:%M") if req.expires_at else "—"
    ad_preview = req.ad_text[:200] + ("..." if len(req.ad_text) > 200 else "")

    status_val = req.status.value if hasattr(req.status, "value") else str(req.status)
    builder = InlineKeyboardBuilder()
    if status_val in ("pending_owner", "counter_offer"):
        builder.button(text="✅ Принять", callback_data=f"own:accept:{request_id}")
        builder.button(text="✏️ Контр-предложение", callback_data=f"own:counter:{request_id}")
        builder.button(text="❌ Отклонить", callback_data=f"own:reject:{request_id}")
    builder.button(text="👁 Полный текст", callback_data=f"own:request:fulltext:{request_id}")
    builder.button(text="🔙 Все заявки", callback_data=MY_REQUESTS_SCENE)
    builder.adjust(1)

    ch_label = f"@{ch.username}" if ch and ch.username else str(req.channel_id)
    await callback.message.edit_text(
        f"📋 *Заявка #{request_id}*\n\n"
        f"📺 Канал: {ch_label}\n"
        f"👤 Рекламодатель: @{adv_username}\n"
        f"📄 Формат: *{_fmt_name(req)}*\n"
        f"💰 Предложение: *{req.proposed_price:.0f} ₽* (ваша цена: {your_price:.0f} ₽)\n"
        f"⏰ Запрошенное время: *{proposed_time}*\n\n"
        f"─── Текст объявления ───\n{ad_preview}\n\n"
        f"⏱ Ответьте до: *{expires}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Принять заявку
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("own:accept:"))
async def accept_request(callback: CallbackQuery, session: AsyncSession) -> None:
    """Принять заявку и уведомить рекламодателя."""
    if not isinstance(callback.message, Message):
        return
    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req or req.status not in (PlacementStatus.pending_owner, PlacementStatus.counter_offer):
        await callback.answer("❌ Невозможно принять", show_alert=True)
        return

    req.status = PlacementStatus.pending_payment
    if not req.final_price:
        req.final_price = req.proposed_price
    if not req.final_schedule:
        req.final_schedule = req.proposed_schedule
    req.expires_at = datetime.now(UTC) + timedelta(hours=24)
    await session.commit()

    advertiser = await session.get(User, req.advertiser_id)
    channel = await session.get(TelegramChat, req.channel_id)
    if advertiser and callback.bot:
        schedule_str = (
            req.final_schedule.strftime("%d.%m.%Y %H:%M")
            if req.final_schedule
            else "По договорённости"
        )
        try:
            await notify_advertiser_accepted(
                bot=callback.bot,
                advertiser_telegram_id=advertiser.telegram_id,
                request_id=request_id,
                channel_name=channel.username if channel else CHANNEL_WORD,
                format_name=_fmt_name(req),
                final_price=req.final_price,
                final_schedule=schedule_str,
            )
        except Exception as exc:
            logger.warning("notify_advertiser_accepted failed: %s", exc)

    builder = InlineKeyboardBuilder()
    builder.button(text=ALL_REQUESTS_BTN, callback_data=MY_REQUESTS_SCENE)
    await callback.message.edit_text(
        f"✅ *Заявка #{request_id} принята!*\n\n"
        "Рекламодатель получил уведомление с ссылкой на оплату.\n"
        "⏱ На оплату — 24 часа.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Отклонить заявку (FSM)
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("own:reject:"))
async def reject_request_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать FSM отклонения."""
    if not isinstance(callback.message, Message):
        return
    request_id = int((callback.data or "").split(":")[-1])
    await state.update_data(rejecting_request_id=request_id)
    await state.set_state(ArbitrationStates.waiting_reject_comment)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=f"own:request:{request_id}")
    await callback.message.edit_text(
        f"❌ *Отклонение заявки #{request_id}*\n\n"
        "⚠️ Укажите причину отклонения (мин. 10 символов).\n\n"
        "Необоснованный отказ = штраф репутации:\n"
        "1й: −10 | 2й: −15 | 3й: −20 + бан 7 дней\n\n"
        "Введите причину:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(ArbitrationStates.waiting_reject_comment)
async def reject_request_comment(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Сохранить причину и отклонить заявку."""
    if message.text is None:
        return
    comment = message.text.strip()
    if len(comment) < 10:
        await message.answer("❌ Минимум 10 символов.")
        return
    if not re.search(r"[а-яА-ЯёЁa-zA-Z]", comment):
        await message.answer("❌ Комментарий должен быть осмысленным.")
        return

    data = await state.get_data()
    request_id = data["rejecting_request_id"]
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await state.clear()
        return

    req.status = PlacementStatus.cancelled
    req.rejection_reason = comment
    await session.commit()

    # Штраф репутации
    owner = await session.get(User, req.owner_id)
    if owner:
        try:
            from src.core.services.reputation_service import ReputationService
            from src.db.repositories.reputation_repo import ReputationRepo

            rep_service = ReputationService(session, ReputationRepo(session))
            await rep_service.on_invalid_rejection(owner_id=owner.id, placement_request_id=req.id)
        except Exception as exc:
            logger.warning("reputation update failed: %s", exc)

    # Уведомить рекламодателя
    advertiser = await session.get(User, req.advertiser_id)
    channel = await session.get(TelegramChat, req.channel_id)
    if advertiser and message.bot:
        try:
            await notify_advertiser_rejected(
                bot=message.bot,
                advertiser_telegram_id=advertiser.telegram_id,
                request_id=request_id,
                channel_name=channel.username if channel else CHANNEL_WORD,
            )
        except Exception as exc:
            logger.warning("notify_advertiser_rejected failed: %s", exc)

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text=ALL_REQUESTS_BTN, callback_data=MY_REQUESTS_SCENE)
    await message.answer(
        f"✅ Заявка #{request_id} отклонена.\nПричина: _{comment}_",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Контр-предложение (FSM: цена → время → комментарий)
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("own:counter:"))
async def counter_offer_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Начать FSM контр-предложения."""
    if not isinstance(callback.message, Message):
        return
    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return
    if req.counter_offer_count >= 3:
        await callback.answer("❌ Достигнут лимит контр-предложений (3/3)", show_alert=True)
        return

    from src.db.models.channel_settings import ChannelSettings

    settings = await session.get(ChannelSettings, req.channel_id)
    your_price = settings.price_per_post if settings else Decimal("1000")

    await state.update_data(counter_request_id=request_id)
    await state.set_state(ArbitrationStates.entering_counter_price)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=f"own:request:{request_id}")
    await callback.message.edit_text(
        f"✏️ *Контр-предложение по заявке #{request_id}*\n\n"
        f"💰 Ваша цена: *{your_price:.0f} ₽*\n"
        f"💰 Предложение: *{req.proposed_price:.0f} ₽*\n"
        f"Раунд: *{req.counter_offer_count + 1}/3*\n\n"
        "Введите вашу цену (₽):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(ArbitrationStates.entering_counter_price)
async def counter_price_input(message: Message, state: FSMContext) -> None:
    """Ввод цены контр-предложения."""
    if message.text is None:
        return
    try:
        price = Decimal(message.text.strip().replace(" ", ""))
        if price < 100:
            await message.answer("❌ Минимальная цена — 100 ₽")
            return
    except InvalidOperation:
        await message.answer("❌ Введите число (например: 1200)")
        return

    await state.update_data(counter_price=str(price))
    await state.set_state(ArbitrationStates.entering_counter_time)

    builder = InlineKeyboardBuilder()
    builder.button(text=SKIP_BTN, callback_data="counter:time:skip")
    await message.answer(
        f"✅ Цена: *{price:.0f} ₽*\n\n"
        "⏰ Введите предпочтительное время публикации\n"
        "(формат: ДД.ММ ЧЧ:ММ, например: 20.03 15:00)\n"
        "или нажмите «Пропустить»:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "counter:time:skip", ArbitrationStates.entering_counter_time)
async def counter_time_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропустить ввод времени."""
    await state.update_data(counter_time=None)
    await state.set_state(ArbitrationStates.entering_counter_comment)

    builder = InlineKeyboardBuilder()
    builder.button(text=SKIP_BTN, callback_data="counter:comment:skip")
    await safe_edit_or_answer(
        callback,
        "💬 Добавьте комментарий к контр-предложению (необязательно):",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.message(ArbitrationStates.entering_counter_time)
async def counter_time_input(message: Message, state: FSMContext) -> None:
    """Ввод времени контр-предложения."""
    if message.text is None:
        return
    try:
        t = datetime.strptime(message.text.strip(), "%d.%m %H:%M")  # noqa: DTZ007
        t = t.replace(year=datetime.now().year)  # noqa: DTZ005
    except ValueError:
        await message.answer("❌ Неверный формат. Введите: ДД.ММ ЧЧ:ММ (например: 20.03 15:00)")
        return

    await state.update_data(counter_time=t.isoformat())
    await state.set_state(ArbitrationStates.entering_counter_comment)

    builder = InlineKeyboardBuilder()
    builder.button(text=SKIP_BTN, callback_data="counter:comment:skip")
    await message.answer(
        f"✅ Время: *{message.text.strip()}*\n\n💬 Добавьте комментарий (необязательно):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "counter:comment:skip", ArbitrationStates.entering_counter_comment)
async def counter_comment_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Пропустить комментарий и отправить контр-предложение."""
    await state.update_data(counter_comment=None)
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await _send_counter_offer(callback.message, state, session, callback.bot)
    await callback.answer()


@router.message(ArbitrationStates.entering_counter_comment)
async def counter_comment_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Принять комментарий и отправить контр-предложение."""
    if message.text is None:
        return
    await state.update_data(counter_comment=message.text.strip())
    await _send_counter_offer(message, state, session, message.bot)


async def safe_edit_or_answer(callback: CallbackQuery, text: str, **kwargs) -> None:
    """Безопасно редактировать или отправить сообщение."""
    if not isinstance(callback.message, Message):
        return
    if hasattr(callback.message, "edit_text"):
        await callback.message.edit_text(text, **kwargs)
    else:
        await callback.message.answer(text, **kwargs)


async def _send_counter_offer(
    msg_obj: Message,
    state: FSMContext,
    session: AsyncSession,
    bot,
) -> None:
    """Зафиксировать контр-предложение в БД и уведомить рекламодателя."""
    data = await state.get_data()
    request_id = data["counter_request_id"]
    counter_price = Decimal(data["counter_price"])
    counter_time_str = data.get("counter_time")
    counter_comment = data.get("counter_comment")

    req = await session.get(PlacementRequest, request_id)
    if not req:
        await state.clear()
        return

    req.counter_price = counter_price
    if counter_time_str:
        req.counter_schedule = datetime.fromisoformat(counter_time_str)
    req.counter_comment = counter_comment
    req.counter_offer_count += 1
    req.status = PlacementStatus.counter_offer
    req.expires_at = datetime.now(UTC) + timedelta(hours=24)
    await session.commit()

    await state.clear()

    advertiser = await session.get(User, req.advertiser_id)
    channel = await session.get(TelegramChat, req.channel_id)
    if advertiser and bot:
        counter_schedule_str = (
            req.counter_schedule.strftime("%d.%m %H:%M")
            if req.counter_schedule
            else "без изменений"
        )
        try:
            await notify_advertiser_counter(
                bot=bot,
                advertiser_telegram_id=advertiser.telegram_id,
                request_id=request_id,
                channel_name=channel.username if channel else CHANNEL_WORD,
                counter_price=counter_price,
                counter_schedule=counter_schedule_str,
                counter_round=req.counter_offer_count,
            )
        except Exception as exc:
            logger.warning("notify_advertiser_counter failed: %s", exc)

    builder = InlineKeyboardBuilder()
    builder.button(text=ALL_REQUESTS_BTN, callback_data=MY_REQUESTS_SCENE)

    text = (
        f"✅ *Контр-предложение отправлено!*\n\n"
        f"💰 Ваша цена: *{counter_price:.0f} ₽*\n"
        "⏱ Рекламодатель должен ответить в течение 24 часов."
    )

    if hasattr(msg_obj, "edit_text"):
        await msg_obj.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await msg_obj.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
