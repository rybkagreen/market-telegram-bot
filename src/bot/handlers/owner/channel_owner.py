"""Owner channel owner handler."""

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberAdministrator, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.channel_owner import AddChannelStates
from src.db.models.channel_settings import ChannelSettings
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.telegram_chat_repo import TelegramChatRepository
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "main:my_channels")
async def show_my_channels(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать мои каналы."""
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
    await callback.message.edit_text(
        f"📺 *Мои каналы* ({count})\n\n{body}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^own:channel:\d+$"))
async def show_channel_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    """Детали канала."""
    channel_id = int(callback.data.split(":")[-1])
    ch = await session.get(TelegramChat, channel_id)
    if not ch:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return

    settings = await session.get(ChannelSettings, channel_id)
    price = settings.price_per_post if settings else Decimal("1000")

    pub_result = await session.execute(
        select(func.count())
        .select_from(PlacementRequest)
        .where(
            PlacementRequest.channel_id == channel_id,
            PlacementRequest.status == PlacementStatus.published,
        )
    )
    publications_count = pub_result.scalar_one()

    pending_reqs = await PlacementRequestRepository(session).get_pending_for_owner(ch.owner_id)
    pending = sum(1 for r in pending_reqs if r.channel_id == channel_id)

    earned_result = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == ch.owner_id,
            Transaction.type == TransactionType.escrow_release,
        )
    )
    total_earned = earned_result.scalar_one() or 0

    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Настройки", callback_data=f"own:settings:{channel_id}")
    builder.button(text=f"📋 Заявки ({pending})", callback_data=f"own:channel_requests:{channel_id}")
    builder.button(text="❌ Удалить канал", callback_data=f"own:delete_channel:{channel_id}")
    builder.button(text="🔙 Мои каналы", callback_data="main:my_channels")
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
    await state.set_state(AddChannelStates.entering_username)
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="main:my_channels")
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
async def add_channel_username(message: Message, state: FSMContext, session: AsyncSession) -> None:  # noqa: ARG001
    """Получить и проверить username канала."""
    username = message.text.strip().lstrip("@").lower()
    if not username or len(username) < 3:
        await message.answer("❌ Неверный username. Введите @username канала.")
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
        builder.button(text="🔙 Назад", callback_data="main:my_channels")
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
    await state.set_state(AddChannelStates.confirming)

    def right_icon(v: bool) -> str:
        return "✅" if v else "❌"

    warnings = []
    if not can_delete:
        warnings.append("⚠️ Без права удалять — форматы с авто-удалением недоступны.")
    if not can_pin:
        warnings.append("⚠️ Без права закреплять — форматы «Закреп» недоступны.")
    rights_warning = "\n".join(warnings) if warnings else "✅ Все права выданы"

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить канал", callback_data="own:add_channel:confirm")
    builder.button(text="❌ Отмена", callback_data="main:my_channels")
    builder.adjust(1)

    await message.answer(
        f"📺 *Канал найден!*\n\n"
        f"*{chat.title}* (@{username})\n"
        f"👥 Подписчиков: *{member_count:,}*\n\n"
        f"─── Права бота ───\n"
        f"Публиковать: {right_icon(can_post)} | "
        f"Удалять: {right_icon(can_delete)} | "
        f"Закреплять: {right_icon(can_pin)}\n\n"
        f"{rights_warning}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "own:add_channel:confirm", AddChannelStates.confirming)
async def add_channel_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Подтвердить добавление канала."""
    data = await state.get_data()
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    ch = TelegramChat(
        telegram_id=data["channel_telegram_id"],
        username=data["username"],
        title=data["title"],
        owner_id=user.id,
        member_count=data["member_count"],
        is_active=True,
    )
    session.add(ch)
    await session.flush()

    ch_settings = ChannelSettings(channel_id=ch.id)
    session.add(ch_settings)
    await session.commit()

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Настроить цену", callback_data=f"own:settings:{ch.id}")
    builder.button(text="📺 Мои каналы", callback_data="main:my_channels")
    builder.adjust(1)

    await callback.message.edit_text(
        f"✅ *Канал @{data['username']} добавлен!*\n\n"
        "Теперь настройте цену и форматы публикаций.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("own:delete_channel:"))
async def delete_channel(callback: CallbackQuery, session: AsyncSession) -> None:
    """Деактивировать канал (soft-delete)."""
    channel_id = int(callback.data.split(":")[-1])

    result = await session.execute(
        select(PlacementRequest)
        .where(
            PlacementRequest.channel_id == channel_id,
            PlacementRequest.status.in_([PlacementStatus.escrow, PlacementStatus.published]),
        )
        .limit(1)
    )
    if result.scalar_one_or_none():
        await callback.answer(
            "❌ Невозможно удалить — есть активные размещения", show_alert=True
        )
        return

    ch = await session.get(TelegramChat, channel_id)
    if ch:
        ch.is_active = False
        await session.commit()

    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Мои каналы", callback_data="main:my_channels")
    await callback.message.edit_text(
        "✅ Канал удалён из платформы.\n\nИсторические данные сохранены.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()
