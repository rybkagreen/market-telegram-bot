"""Placement wizard handler - 6 steps."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.advertiser.placement import (
    category_kb,
    channel_card_kb,
    text_method_kb,
    video_upload_keyboard,
)
from src.bot.states.placement import PlacementStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.constants.payments import OWNER_SHARE, PLATFORM_COMMISSION
from src.db.repositories.category_repo import CategoryRepo
from src.db.repositories.user_repo import UserRepository

router = Router()

REQUEST_NOT_FOUND = "❌ Заявка не найдена"

FORMATS = {
    "post_24h": {
        "name": "📄 Пост 24ч",
        "multiplier": 1.0,
        "plans": ["free", "starter", "pro", "business"],
        "allow_key": "allow_format_post_24h",
    },
    "post_48h": {
        "name": "📄 Пост 48ч",
        "multiplier": 1.4,
        "plans": ["starter", "pro", "business"],
        "allow_key": "allow_format_post_48h",
    },
    "post_7d": {
        "name": "📄 Пост 7 дней",
        "multiplier": 2.0,
        "plans": ["pro", "business"],
        "allow_key": "allow_format_post_7d",
    },
    "pin_24h": {
        "name": "📌 Закреп 24ч",
        "multiplier": 3.0,
        "plans": ["business"],
        "allow_key": "allow_format_pin_24h",
    },
    "pin_48h": {
        "name": "📌 Закреп 48ч",
        "multiplier": 4.0,
        "plans": ["business"],
        "allow_key": "allow_format_pin_48h",
    },
}

FORMAT_NAMES = {
    "post_24h": "Пост 24ч",
    "post_48h": "Пост 48ч",
    "post_7d": "Пост 7 дней",
    "pin_24h": "Закреп 24ч",
    "pin_48h": "Закреп 48ч",
}

STATUS_LABELS = {
    "pending_owner": "⏳ Ожидает ответа владельца",
    "counter_offer": "✏️ Владелец предложил другие условия",
    "pending_payment": "💳 Ожидает оплаты",
    "escrow": "🔒 В эскроу — ожидает публикации",
    "published": "📢 Опубликовано",
    "failed": "❌ Ошибка публикации",
    "refunded": "🔓 Средства возвращены",
    "cancelled": "❌ Отменено",
}


@router.callback_query(lambda c: c.data == "main:create_campaign")
async def camp_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Начать создание кампании."""
    if not isinstance(callback.message, Message):
        return
    await state.set_state(PlacementStates.selecting_category)
    categories = await CategoryRepo(session).get_all_active()
    await callback.answer("Создание кампании")
    await callback.message.answer("📋 Выберите категорию:", reply_markup=category_kb(categories))


@router.callback_query(lambda c: c.data.startswith("camp:cat:"))
async def camp_step1_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Шаг 1: Выбор категории → сразу к выбору каналов."""
    category = (callback.data or "").split(":")[-1]
    await state.update_data(category=category)
    await state.set_state(PlacementStates.selecting_channels)
    await safe_callback_edit(
        callback, "📢 Выберите каналы:", reply_markup=channel_card_kb(1, False, 0)
    )


@router.callback_query(F.data == "camp:back:category", PlacementStates.selecting_channels)
async def camp_back_to_category(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Вернуться к выбору категории."""
    await state.set_state(PlacementStates.selecting_category)
    categories = await CategoryRepo(session).get_all_active()
    await safe_callback_edit(
        callback, "📋 Выберите категорию:", reply_markup=category_kb(categories)
    )


@router.callback_query(lambda c: c.data.startswith("camp:channel:"))
async def camp_step3_channels(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Шаг 3: Выбор каналов. Self-dealing check: exclude channel.owner_id == user.id"""
    value = (callback.data or "").split(":")[-1]
    if value == "skip":
        await state.set_state(PlacementStates.selecting_channels)
        await callback.answer()
        return
    channel_id = int(value)

    # Self-dealing prevention: check channel owner (owner_id is FK to users.id, not telegram_id)
    from src.db.repositories.telegram_chat_repo import TelegramChatRepository

    channel = await TelegramChatRepository(session).get_by_id(channel_id)
    db_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)

    if channel is not None and db_user is not None and channel.owner_id == db_user.id:
        await callback.answer("❌ Нельзя размещать рекламу на собственном канале", show_alert=True)
        return

    await state.update_data(selected_channels=[channel_id])
    await callback.answer("Канал выбран")


# ISSUE #8: Handler camp:channels:done
@router.callback_query(F.data == "camp:channels:done", PlacementStates.selecting_channels)
async def camp_select_format(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Шаг 4: Выбор формата публикации после подтверждения каналов."""
    if not isinstance(callback.message, Message):
        return

    from src.db.models.channel_settings import ChannelSettings
    from src.db.models.telegram_chat import TelegramChat

    data = await state.get_data()
    selected_channels = data.get("selected_channels", [])

    if not selected_channels:
        await callback.answer("❌ Выберите хотя бы один канал", show_alert=True)
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    channels = []
    settings_map = {}
    for ch_id in selected_channels:
        ch = await session.get(TelegramChat, ch_id)
        s = await session.get(ChannelSettings, ch_id)
        if ch:
            channels.append(ch)
            settings_map[ch_id] = s

    channels_names = ", ".join([f"@{ch.username}" for ch in channels if ch.username])

    builder = InlineKeyboardBuilder()
    format_prices = {}
    breakdown_lines = []

    for fmt_key, fmt_info in FORMATS.items():
        plans: list[str] = fmt_info["plans"]  # type: ignore[assignment]
        allow_key: str = fmt_info["allow_key"]  # type: ignore[assignment]
        if user.plan not in plans:
            continue
        all_allow = all(
            getattr(s, allow_key, False)
            for ch in channels
            for s in (settings_map.get(ch.id),)
            if s is not None
        )
        if not all_allow:
            continue
        total = sum(
            Decimal(str(s.price_per_post)) * Decimal(str(fmt_info["multiplier"]))
            for ch in channels
            for s in (settings_map.get(ch.id),)
            if s is not None
        )
        format_prices[fmt_key] = total
        builder.button(
            text=f"{fmt_info['name']} — {total:.0f} ₽", callback_data=f"camp:format:{fmt_key}"
        )
        breakdown_lines.append(f"• {fmt_info['name']}: {total:.0f} ₽")

    builder.button(text="🔙 Назад", callback_data="camp:back:channels")
    builder.adjust(1)

    await state.update_data(format_prices={k: str(v) for k, v in format_prices.items()})
    await state.set_state(PlacementStates.selecting_format)

    breakdown_text = "\n".join(breakdown_lines) if breakdown_lines else "Нет доступных форматов"

    await callback.message.edit_text(
        f"📣 *Создание кампании*\nШаг 4 из 6: Формат публикации\n\n"
        f"Выбраны каналы: *{channels_names}*\n\n"
        f"─── Цены по форматам ───\n{breakdown_text}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("camp:format:"))
async def camp_step4_format(callback: CallbackQuery, state: FSMContext) -> None:
    """Шаг 4: Выбор формата."""
    if not isinstance(callback.message, Message):
        return
    fmt = (callback.data or "").split(":")[-1]
    await state.update_data(format=fmt)
    await state.set_state(PlacementStates.entering_text)
    await callback.message.answer("📝 Введите текст:", reply_markup=text_method_kb("free", 0))


@router.callback_query(lambda c: c.data.startswith("camp:text:"))
async def camp_step5_text(callback: CallbackQuery, state: FSMContext) -> None:
    """Шаг 5: Ввод текста → предложение добавить видео."""
    if not isinstance(callback.message, Message):
        return
    await state.update_data(text="sample")
    # Offer video upload (S3 addition)
    await callback.message.answer(
        "Хотите добавить видео к рекламному посту? (опционально)",
        reply_markup=video_upload_keyboard(),
    )


@router.callback_query(lambda c: c.data == "camp:submit")
async def camp_step6_submit(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Шаг 6: Отправка кампании."""
    from src.bot.handlers.shared.notifications import notify_owner_new_request
    from src.db.models.telegram_chat import TelegramChat
    from src.db.models.user import User
    from src.db.repositories.placement_request_repo import PlacementRequestRepository

    data = await state.get_data()

    selected_channels = data.get("selected_channels", [])
    if not selected_channels:
        await callback.answer("❌ Не выбран канал", show_alert=True)
        return

    channel_id = selected_channels[0]
    fmt = data.get("format", "post_24h")
    format_prices = data.get("format_prices", {})
    proposed_price = Decimal(format_prices.get(fmt, "0"))
    ad_text = data.get("text", "")

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    placement = await PlacementRequestRepository(session).create_placement(
        advertiser_id=user.id,
        channel_id=channel_id,
        proposed_price=proposed_price,
        final_text=ad_text,
        publication_format=fmt,
    )
    await session.commit()

    channel = await session.get(TelegramChat, channel_id)
    if channel:
        owner = await session.get(User, channel.owner_id)
        if owner:
            if callback.bot is None:
                return
            await notify_owner_new_request(callback.bot, owner.telegram_id, placement.id)

    await state.clear()
    await callback.answer(
        f"✅ Заявка #{placement.id} создана! Ожидайте подтверждения.", show_alert=True
    )


# ISSUE #9: Handler camp:pay:{request_id} — экран оплаты
@router.callback_query(F.data.startswith("camp:pay:") & ~F.data.startswith("camp:pay:balance:"))
async def camp_pay(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать экран оплаты для заявки."""
    if not isinstance(callback.message, Message):
        return

    from src.db.models.placement_request import PlacementRequest
    from src.db.models.telegram_chat import TelegramChat

    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer(REQUEST_NOT_FOUND, show_alert=True)
        return

    channel = await session.get(TelegramChat, req.channel_id)
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)

    price = req.final_price or req.proposed_price
    owner_amount = price * OWNER_SHARE
    platform_amount = price * PLATFORM_COMMISSION

    fmt_name = FORMAT_NAMES.get(
        req.publication_format.value
        if hasattr(req.publication_format, "value")
        else str(req.publication_format),
        str(req.publication_format),
    )
    schedule = (
        req.final_schedule.strftime("%d.%m.%Y %H:%M") if req.final_schedule else "По договорённости"
    )

    builder = InlineKeyboardBuilder()
    if user and user.balance_rub >= price:
        builder.button(
            text=f"💳 Оплатить с баланса ({user.balance_rub:.0f} ₽)",
            callback_data=f"camp:pay:balance:{request_id}",
        )
    else:
        builder.button(text="💳 Пополнить баланс", callback_data="billing:topup_start")
    builder.button(text="❌ Отменить заявку", callback_data=f"camp:cancel:{request_id}")
    builder.adjust(1)

    channel_name = f"@{channel.username}" if channel and channel.username else "канал"
    await callback.message.edit_text(
        f"💳 *Оплата заявки #{request_id}*\n\n"
        f"📺 {channel_name}\n"
        f"📄 Формат: *{fmt_name}*\n"
        f"⏰ Время: *{schedule}*\n\n"
        f"─── К оплате ───\n"
        f"💰 Сумма эскроу: *{price:.0f} ₽*\n"
        f"🔒 Средства заморожены до авто-удаления поста\n\n"
        f"─── Распределение ───\n"
        f"• Владельцу (после удаления): *{owner_amount:.0f} ₽* (85%)\n"
        f"• Комиссия платформы: *{platform_amount:.0f} ₽* (15%)\n\n"
        f"⚠️ Отмена после оплаты: возврат только 50%",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ISSUE #9: Handler camp:pay:balance:{request_id} — списание с баланса + эскроу
@router.callback_query(F.data.startswith("camp:pay:balance:"))
async def camp_pay_balance(callback: CallbackQuery, session: AsyncSession) -> None:
    """Оплатить заявку с баланса и заморозить эскроу."""
    if not isinstance(callback.message, Message):
        return

    import logging

    from src.core.services.billing_service import BillingService
    from src.db.models.placement_request import PlacementRequest, PlacementStatus
    from src.db.models.telegram_chat import TelegramChat

    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer(REQUEST_NOT_FOUND, show_alert=True)
        return
    if req.status != PlacementStatus.pending_payment:
        await callback.answer("❌ Заявка уже обработана", show_alert=True)
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    price = req.final_price or req.proposed_price

    if user.balance_rub < price:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return

    billing = BillingService()
    try:
        await billing.freeze_escrow(
            session=session,
            user_id=user.id,
            placement_id=request_id,
            amount=price,
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"freeze_escrow error: {e}")
        await callback.answer("❌ Ошибка оплаты. Попробуйте позже.", show_alert=True)
        return

    req.status = PlacementStatus.escrow

    # --- ORD auto-trigger (S7 addition) ---
    try:
        from src.core.services.ord_service import get_ord_service

        ord_svc = get_ord_service(session)
        await ord_svc.register_creative(
            placement_request_id=req.id,
            ad_text=req.ad_text or "",
            media_type=req.media_type or "none",
        )
    except Exception as _ord_exc:
        logging.getLogger(__name__).warning(
            f"ORD auto-trigger failed for placement {req.id}: {_ord_exc}"
        )
        # Never block escrow transition
    # --- end ORD auto-trigger ---

    await session.commit()

    channel = await session.get(TelegramChat, req.channel_id)
    schedule = (
        req.final_schedule.strftime("%d.%m.%Y %H:%M") if req.final_schedule else "По договорённости"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Отслеживать статус", callback_data=f"camp:status:{request_id}")
    builder.button(
        text="❌ Отменить (возврат 50%)", callback_data=f"camp:cancel_after_escrow:{request_id}"
    )
    builder.adjust(1)

    channel_name = f"@{channel.username}" if channel and channel.username else "канал"
    await callback.message.edit_text(
        f"🔒 *Средства заморожены в эскроу!*\n\n"
        f"✅ Заблокировано: *{price:.0f} ₽*\n"
        f"📅 Публикация: *{schedule}*\n"
        f"📺 Канал: {channel_name}\n\n"
        f"💡 Бот автоматически опубликует рекламу и удалит её по расписанию.\n"
        f"Деньги владелец получит после удаления.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ISSUE #10: Статус заявки
@router.callback_query(F.data.startswith("camp:status:"))
async def camp_status(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать статус заявки."""
    if not isinstance(callback.message, Message):
        return

    from src.db.models.placement_request import PlacementRequest
    from src.db.models.telegram_chat import TelegramChat

    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer(REQUEST_NOT_FOUND, show_alert=True)
        return

    channel = await session.get(TelegramChat, req.channel_id)
    price = req.final_price or req.proposed_price
    status_val = req.status.value if hasattr(req.status, "value") else str(req.status)
    status_label = STATUS_LABELS.get(status_val, status_val)
    schedule = req.final_schedule.strftime("%d.%m.%Y %H:%M") if req.final_schedule else "—"

    builder = InlineKeyboardBuilder()
    if status_val == "escrow":
        builder.button(
            text="❌ Отменить (возврат 50%)", callback_data=f"camp:cancel_after_escrow:{request_id}"
        )
    builder.button(text="🔙 Мои кампании", callback_data="main:my_campaigns")
    builder.adjust(1)

    channel_name = f"@{channel.username}" if channel and channel.username else "—"
    await callback.message.edit_text(
        f"📋 *Заявка #{request_id}*\n\n"
        f"📺 Канал: {channel_name}\n"
        f"💰 Сумма: *{price:.0f} ₽*\n"
        f"📅 Публикация: *{schedule}*\n"
        f"📊 Статус: *{status_label}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ISSUE #10: Отмена после эскроу
@router.callback_query(F.data.startswith("camp:cancel_after_escrow:"))
async def camp_cancel_after_escrow(callback: CallbackQuery, session: AsyncSession) -> None:
    """Отменить заявку в статусе escrow (возврат 50%)."""
    if not isinstance(callback.message, Message):
        return

    import logging

    from src.core.services.billing_service import BillingService
    from src.db.models.placement_request import PlacementRequest, PlacementStatus

    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req or req.status != PlacementStatus.escrow:
        await callback.answer("❌ Невозможно отменить", show_alert=True)
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    price = req.final_price or req.proposed_price
    refund = price * Decimal("0.50")

    billing = BillingService()
    try:
        await billing.refund_escrow(
            session=session,
            placement_id=request_id,
            final_price=price,
            advertiser_id=user.id,
            owner_id=req.owner_id,
            scenario="after_escrow_before_confirmation",
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"refund_escrow error: {e}")

    req.status = PlacementStatus.cancelled
    await session.commit()

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои кампании", callback_data="main:my_campaigns")

    await callback.message.edit_text(
        f"❌ *Заявка отменена*\n\n"
        f"🔓 Возврат 50%: *{refund:.0f} ₽*\n"
        f"⏱ Зачисление в течение 24 часов.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()
