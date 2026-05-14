"""Owner channel owner handler."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberAdministrator, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.channel_owner import AddChannelStates
from src.core.enums.blogger_registry import BloggerRegistryVerificationMethod
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.channel_add_context import ChannelAddContext
from src.core.services.legal_compliance_service import LegalComplianceService
from src.db.models.channel_settings import ChannelSettings
from src.db.models.telegram_chat import TelegramChat
from src.db.models.transaction import TransactionType
from src.db.repositories.audit_log_repo import AuditLogRepo
from src.db.repositories.category_repo import CategoryRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.telegram_chat_repo import TelegramChatRepository
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.utils.telegram.verify_blogger_registry import (
    TrustchannelbotResolutionError,
    verify_trustchannelbot_admin,
)

logger = logging.getLogger(__name__)
router = Router()

MY_CHANNELS_SCENE = "main:my_channels"
CANCEL_BTN = "❌ Отмена"
MY_CHANNELS_BTN = "📺 Мои каналы"


@router.callback_query(F.data == MY_CHANNELS_SCENE)
async def show_my_channels(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать мои каналы."""
    if not isinstance(callback.message, Message):
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    channels = await TelegramChatRepository(session).get_by_owner(user.id)
    builder = InlineKeyboardBuilder()
    for ch in channels:
        label = f"@{ch.username}" if ch.username else ch.title or f"id{ch.telegram_id}"
        builder.button(text=label, callback_data=f"own:channel:{ch.id}")
    builder.button(text="➕ Добавить канал", callback_data="own:add_channel")
    builder.button(text="🔙 Меню владельца", callback_data="main:own_menu")
    builder.adjust(1)

    count = len(channels)
    body = "Выберите канал для управления:" if count else "У вас пока нет добавленных каналов."
    builder.button(text="📦 Скрытые каналы", callback_data="own:inactive_channels")
    builder.adjust(1)
    await callback.message.edit_text(
        f"📺 *Мои каналы* ({count})\n\n{body}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "own:inactive_channels")
async def show_inactive_channels(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать скрытые (неактивные) каналы."""
    if not isinstance(callback.message, Message):
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    channels = await TelegramChatRepository(session).get_inactive_by_owner(user.id)
    builder = InlineKeyboardBuilder()
    for ch in channels:
        label = f"♻️ @{ch.username}" if ch.username else f"♻️ {ch.title or f'id{ch.telegram_id}'}"
        builder.button(text=label, callback_data=f"own:restore_channel:{ch.id}")
    builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
    builder.adjust(1)

    count = len(channels)
    body = "У вас нет скрытых каналов." if count == 0 else "Нажмите на канал для восстановления:"
    await callback.message.edit_text(
        f"📦 *Скрытые каналы* ({count})\n\n{body}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^own:channel:\d+$"))
async def show_channel_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    """Детали канала."""
    if not isinstance(callback.message, Message):
        return
    channel_id = int((callback.data or "").split(":")[-1])
    ch = await session.get(TelegramChat, channel_id)
    if not ch:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return

    settings = await session.get(ChannelSettings, channel_id)
    price = settings.price_per_post if settings else Decimal("1000")

    publications_count = await PlacementRequestRepository(session).count_published_by_channel(
        channel_id
    )

    pending_reqs = await PlacementRequestRepository(session).get_pending_for_owner(ch.owner_id)
    pending = sum(1 for r in pending_reqs if r.channel_id == channel_id)

    earned = await TransactionRepository(session).sum_by_user_and_type(
        ch.owner_id,
        TransactionType.escrow_release,
    )
    total_earned = earned or 0

    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Настройки", callback_data=f"own:settings:{channel_id}")
    builder.button(
        text=f"📋 Заявки ({pending})", callback_data=f"own:channel_requests:{channel_id}"
    )
    builder.button(text="👻 Скрыть канал", callback_data=f"own:delete_channel:{channel_id}")
    builder.button(text="🔙 Мои каналы", callback_data=MY_CHANNELS_SCENE)
    builder.adjust(1)

    await callback.message.edit_text(
        f"📺 *@{ch.username}*\n\n"
        f"👥 Подписчиков: *{ch.member_count:,}*\n"
        f"⭐ Рейтинг: *{ch.rating:.1f}*\n"
        f"✅ Публикаций: *{publications_count}*\n"
        f"💰 Заработано: *{total_earned:.0f} ₽*\n\n"
        f"─── Настройки ───\n"
        f"💰 Базовая цена: *{price:.0f} ₽*\n"
        f"📅 Макс. постов/день: *{settings.max_posts_per_day if settings else 2}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "own:add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление канала (FSM)."""
    if not isinstance(callback.message, Message):
        return
    await state.set_state(AddChannelStates.entering_username)
    builder = InlineKeyboardBuilder()
    builder.button(text=CANCEL_BTN, callback_data=MY_CHANNELS_SCENE)
    builder.adjust(1)

    await callback.message.edit_text(
        "➕ *Добавление канала*\n\n"
        "⚠️ *Перед добавлением:*\n"
        "1. Сделайте @RekHarborBot администратором\n"
        "2. Выдайте права:\n"
        "   ✅ Публиковать сообщения\n"
        "   ✅ *Удалять сообщения* (обязательно!)\n"
        "   ✅ *Закреплять сообщения* (для форматов «Закреп»)\n\n"
        "Введите @username канала:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(AddChannelStates.entering_username)
async def add_channel_username(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Получить и проверить username канала, затем показать выбор категории."""
    username = (message.text or "").strip().lstrip("@").lower()
    if not username or len(username) < 3:
        await message.answer("❌ Неверный username. Введите @username канала.")
        return

    if message.bot is None:
        return
    try:
        chat = await message.bot.get_chat(f"@{username}")
    except Exception:
        await message.answer(
            f"❌ Канал @{username} не найден.\n\nУбедитесь что канал публичный и username верный."
        )
        return

    try:
        bot_member = await message.bot.get_chat_member(chat.id, message.bot.id)
        if not isinstance(bot_member, ChatMemberAdministrator):
            raise ValueError("not admin")
        can_post = bot_member.can_post_messages or False
        can_delete = bot_member.can_delete_messages or False
        can_pin = bot_member.can_pin_messages or False
    except Exception:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data=MY_CHANNELS_SCENE)
        await message.answer(
            f"❌ Бот не является администратором @{username}.\n\n"
            "Добавьте @RekHarborBot как администратора и попробуйте снова.",
            reply_markup=builder.as_markup(),
        )
        await state.clear()
        return

    member_count = getattr(chat, "member_count", 0) or 0
    await state.update_data(
        channel_telegram_id=chat.id,
        username=username,
        title=chat.title or username,
        member_count=member_count,
        can_post=can_post,
        can_delete=can_delete,
        can_pin=can_pin,
    )

    # Переходим к выбору категории
    categories = await CategoryRepo(session).get_all_active()
    await state.set_state(AddChannelStates.selecting_category)

    builder = InlineKeyboardBuilder()
    cats_list = list(categories)
    for i in range(0, len(cats_list), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                text=f"{cats_list[i].emoji} {cats_list[i].name_ru}",
                callback_data=f"own:add_channel:cat:{cats_list[i].slug}",
            )
        )
        if i + 1 < len(cats_list):
            row.append(
                InlineKeyboardButton(
                    text=f"{cats_list[i + 1].emoji} {cats_list[i + 1].name_ru}",
                    callback_data=f"own:add_channel:cat:{cats_list[i + 1].slug}",
                )
            )
        builder.row(*row)
    builder.row(InlineKeyboardButton(text=CANCEL_BTN, callback_data="own:add_channel:cancel"))

    await message.answer(
        "📂 *Выберите категорию канала*\n\nЭто поможет рекламодателям найти ваш канал.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


@router.callback_query(
    F.data.startswith("own:add_channel:cat:"), AddChannelStates.selecting_category
)
async def add_channel_select_category(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Выбрать категорию канала и перейти к подтверждению."""
    if not isinstance(callback.message, Message):
        return
    slug = (callback.data or "").split(":")[-1]
    category = await CategoryRepo(session).get_by_slug(slug)
    if not category:
        await callback.answer("❌ Неверная категория", show_alert=True)
        return

    await state.update_data(category=slug)
    await state.set_state(AddChannelStates.confirming)

    data = await state.get_data()

    def right_icon(v: bool) -> str:
        return "✅" if v else "❌"

    warnings = []
    if not data.get("can_delete"):
        warnings.append("⚠️ Без права удалять — форматы с авто-удалением недоступны.")
    if not data.get("can_pin"):
        warnings.append("⚠️ Без права закреплять — форматы «Закреп» недоступны.")
    rights_warning = "\n".join(warnings) if warnings else "✅ Все права выданы"

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить канал", callback_data="own:add_channel:confirm")
    builder.button(text="🔙 Назад", callback_data="own:add_channel:back_to_cat")
    builder.button(text=CANCEL_BTN, callback_data=MY_CHANNELS_SCENE)
    builder.adjust(1)

    await callback.message.edit_text(
        f"📺 *Подтверждение добавления*\n\n"
        f"*{data['title']}* (@{data['username']})\n"
        f"👥 Подписчиков: *{data['member_count']:,}*\n"
        f"📂 Категория: *{category.emoji} {category.name_ru}*\n\n"
        f"─── Права бота ───\n"
        f"Публиковать: {right_icon(data.get('can_post', False))} | "
        f"Удалять: {right_icon(data.get('can_delete', False))} | "
        f"Закреплять: {right_icon(data.get('can_pin', False))}\n\n"
        f"{rights_warning}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "own:add_channel:back_to_cat", AddChannelStates.confirming)
async def add_channel_back_to_category(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Вернуться к выбору категории."""
    if not isinstance(callback.message, Message):
        return
    await state.set_state(AddChannelStates.selecting_category)

    categories = await CategoryRepo(session).get_all_active()
    builder = InlineKeyboardBuilder()
    cats_list = list(categories)
    for i in range(0, len(cats_list), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                text=f"{cats_list[i].emoji} {cats_list[i].name_ru}",
                callback_data=f"own:add_channel:cat:{cats_list[i].slug}",
            )
        )
        if i + 1 < len(cats_list):
            row.append(
                InlineKeyboardButton(
                    text=f"{cats_list[i + 1].emoji} {cats_list[i + 1].name_ru}",
                    callback_data=f"own:add_channel:cat:{cats_list[i + 1].slug}",
                )
            )
        builder.row(*row)
    builder.row(InlineKeyboardButton(text=CANCEL_BTN, callback_data="own:add_channel:cancel"))

    await callback.message.edit_text(
        "📂 *Выберите категорию канала*\n\nЭто поможет рекламодателям найти ваш канал.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "own:add_channel:cancel")
async def add_channel_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить добавление канала."""
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
    await callback.message.edit_text(
        "❌ Добавление канала отменено.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "own:add_channel:confirm", AddChannelStates.confirming)
async def add_channel_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Подтвердить добавление канала."""
    if not isinstance(callback.message, Message):
        return
    data = await state.get_data()
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Phase 3b §3.B.6 — owner role compliance precondition (5b.7a).
    # No admin test-mode carve-out for bot path: API has body.is_test +
    # is_admin gate, but bot UX hardcodes is_active=True and lacks the
    # parameter (pre-existing — flagged in 5b.7a closure as O.7 deferred).
    compliance = LegalComplianceService(session)
    gate_results = await compliance.check_gates_for_user_role(user, role="owner")
    blockers = [r for r in gate_results if not r.passed]
    if blockers:
        await AuditLogRepo(session).log(
            action="channel_add_declined",
            resource_type="channel",
            user_id=user.id,
            extra={"blockers": [r.gate.value for r in blockers]},
        )
        await callback.answer("❌ Добавление канала недоступно", show_alert=True)
        lines = [
            "❌ *Добавление канала недоступно*",
            "",
            "Чтобы добавить канал, заполните юр. профиль и подпишите договор владельца канала:",
        ]
        for r in blockers:
            line = f"• {r.gate.value}: {r.reason_code}"
            if r.remediation_url:
                line += f" → {r.remediation_url}"
            lines.append(line)
        builder = InlineKeyboardBuilder()
        builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
        await state.clear()
        return

    # BL-107 / ФЗ-303 — Trustchannelbot admin check + G19 channel-context gate
    # (Phase B.4 wiring). O.7 deferred: bot path passes is_test=False — admin
    # parity FSM step lives в Phase B.7.
    verification_audit: dict[str, Any] = {
        "is_blogger_registry_verified": False,
        "blogger_registry_verified_at": None,
        "blogger_registry_verification_method": None,
        "member_count_at_verification": None,
        "last_blogger_registry_check_at": None,
    }
    bot = callback.message.bot
    if bot is None:
        await callback.answer("❌ Бот недоступен", show_alert=True)
        await state.clear()
        return

    try:
        is_verified = await verify_trustchannelbot_admin(bot, data["channel_telegram_id"])
    except TrustchannelbotResolutionError as exc:
        logger.warning(
            "Trustchannelbot resolution failed for channel %s: %s",
            data["channel_telegram_id"],
            exc,
        )
        await AuditLogRepo(session).log(
            action="channel_add_declined",
            resource_type="channel",
            user_id=user.id,
            extra={"blockers": [PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED.value]},
        )
        await callback.answer(
            "❌ Не удалось проверить статус регистрации канала. Попробуйте позже.",
            show_alert=True,
        )
        await state.clear()
        return

    channel_data = ChannelAddContext(
        telegram_id=data["channel_telegram_id"],
        username=data["username"],
        member_count=data["member_count"],
        is_test=False,  # O.7 deferred to Phase B.7 (bot UX has no is_test parameter)
        description=None,
        is_blogger_registry_verified=is_verified,
    )
    channel_gate_results = await compliance.check_gates_for_channel_add(user, channel_data)
    channel_blockers = [r for r in channel_gate_results if not r.passed]
    if channel_blockers:
        await AuditLogRepo(session).log(
            action="channel_add_declined",
            resource_type="channel",
            user_id=user.id,
            extra={"blockers": [r.gate.value for r in channel_blockers]},
        )
        await callback.answer("❌ Канал требует регистрации в реестре блогеров", show_alert=True)
        lines = [
            "❌ *Регистрация в реестре блогеров (ФЗ-303)*",
            "",
            "Канал с аудиторией ≥10 000 подписчиков обязан быть зарегистрирован в реестре"
            " блогеров Роскомнадзора. Добавьте @Trustchannelbot администратором канала и"
            " попробуйте снова.",
            "",
        ]
        for r in channel_blockers:
            line = f"• {r.gate.value}: {r.reason_code}"
            if r.remediation_url:
                line += f" → {r.remediation_url}"
            lines.append(line)
        builder = InlineKeyboardBuilder()
        builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
        await state.clear()
        return

    now_utc = datetime.now(UTC)
    verification_audit["last_blogger_registry_check_at"] = now_utc
    if is_verified:
        verification_audit.update({
            "is_blogger_registry_verified": True,
            "blogger_registry_verified_at": now_utc,
            "blogger_registry_verification_method": (
                BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN
            ),
            "member_count_at_verification": data["member_count"],
        })

    ch = TelegramChat(
        telegram_id=data["channel_telegram_id"],
        username=data["username"],
        title=data["title"],
        owner_id=user.id,
        member_count=data["member_count"],
        category=data.get("category"),
        is_active=True,
        **verification_audit,
    )
    session.add(ch)
    await session.flush()

    ch_settings = ChannelSettings(channel_id=ch.id)
    session.add(ch_settings)
    # S-48 (5b.7a O.4): explicit commit removed — DBSessionMiddleware autocommits
    # on handler success (src/bot/middlewares/db_session.py). Pre-existing
    # double-commit was a no-op but blurred Pattern 1 contract for handlers.

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Настроить цену", callback_data=f"own:settings:{ch.id}")
    builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
    builder.adjust(1)

    await callback.message.edit_text(
        f"✅ *Канал @{data['username']} добавлен!*\n\nТеперь настройте цену и форматы публикаций.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("own:delete_channel:"))
async def delete_channel(callback: CallbackQuery, session: AsyncSession) -> None:
    """Деактивировать канал (soft-delete)."""
    if not isinstance(callback.message, Message):
        return
    channel_id = int((callback.data or "").split(":")[-1])

    has_active = await PlacementRequestRepository(session).has_active_placements(channel_id)
    if has_active:
        await callback.answer("❌ Невозможно удалить — есть активные размещения", show_alert=True)
        return

    ch = await session.get(TelegramChat, channel_id)
    if ch:
        ch.is_active = False

    builder = InlineKeyboardBuilder()
    builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
    await callback.message.edit_text(
        "✅ Канал скрыт из платформы.\n\nИсторические данные сохранены.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("own:restore_channel:"))
async def restore_channel(callback: CallbackQuery, session: AsyncSession) -> None:
    """Восстановить канал (reactivate)."""
    if not isinstance(callback.message, Message):
        return
    channel_id = int((callback.data or "").split(":")[-1])

    ch = await session.get(TelegramChat, channel_id)
    if ch is None:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return
    ch.is_active = True

    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Настройки", callback_data=f"own:channel:{channel_id}")
    builder.button(text="📦 Скрытые каналы", callback_data="own:inactive_channels")
    builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
    builder.adjust(1)
    await callback.message.edit_text(
        f"✅ Канал *{ch.username or ch.title}* восстановлен и снова виден рекламодателям.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()
