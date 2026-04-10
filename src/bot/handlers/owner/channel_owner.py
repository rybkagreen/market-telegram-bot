"""Owner channel owner handler."""

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberAdministrator, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.channel_owner import AddChannelStates
from src.db.models.channel_settings import ChannelSettings
from src.db.models.telegram_chat import TelegramChat
from src.db.models.transaction import TransactionType
from src.db.repositories.category_repo import CategoryRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.telegram_chat_repo import TelegramChatRepository
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository

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
    await callback.message.edit_text(
        f"📺 *Мои каналы* ({count})\n\n{body}",
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
    builder.button(text="❌ Удалить канал", callback_data=f"own:delete_channel:{channel_id}")
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

    ch = TelegramChat(
        telegram_id=data["channel_telegram_id"],
        username=data["username"],
        title=data["title"],
        owner_id=user.id,
        member_count=data["member_count"],
        category=data.get("category"),
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
        await session.commit()

    builder = InlineKeyboardBuilder()
    builder.button(text=MY_CHANNELS_BTN, callback_data=MY_CHANNELS_SCENE)
    await callback.message.edit_text(
        "✅ Канал удалён из платформы.\n\nИсторические данные сохранены.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()
