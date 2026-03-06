"""
Хэндлеры для владельцев каналов.
Спринт 0: регистрация канала (/add_channel) с верификацией bot_is_admin.
Спринт 1: управление каналами (/my_channels).
"""
import logging
from datetime import UTC, datetime
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InaccessibleMessage,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.bot.states.channel_owner import AddChannelStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.models.analytics import TelegramChat
from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = Router(name="channel_owner")

# Текст инструкции как добавить бота администратором
ADD_BOT_INSTRUCTION = """
📋 <b>Как добавить бота администратором:</b>

1. Откройте ваш канал в Telegram
2. Нажмите на название канала → <b>Управление каналом</b>
3. Перейдите в <b>Администраторы</b>
4. Нажмите <b>Добавить администратора</b>
5. Найдите <b>@{bot_username}</b>
6. Убедитесь что включено право <b>«Публикация сообщений»</b>
7. Нажмите «Сохранить»

После добавления нажмите кнопку ниже ↓
"""

# Список тематик (должен совпадать с topic_classifier.py)
TOPICS = [
    ("💻 IT", "it"),
    ("💼 Бизнес", "business"),
    ("📈 Маркетинг", "marketing"),
    ("💰 Финансы", "finance"),
    ("🏠 Недвижимость", "realestate"),
    ("🔗 Крипта", "crypto"),
    ("📰 Новости", "news"),
    ("🎓 Образование", "education"),
    ("🌐 Другое", "other"),
]


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, state: FSMContext) -> None:
    """Начало флоу добавления канала."""
    await state.set_state(AddChannelStates.waiting_username)
    await message.answer(
        "📺 <b>Регистрация канала на платформе</b>\n\n"
        "Введите @username вашего канала (например: @mychannel)\n\n"
        "⚠️ Канал должен быть публичным (иметь @username)",
        parse_mode="HTML",
    )


@router.message(AddChannelStates.waiting_username)
async def process_channel_username(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Обработка введённого username канала."""
    if message.text is None:
        await message.answer("Пожалуйста, введите текстовый @username канала.")
        return

    username = (message.text or "").strip().lstrip("@")

    if not username:
        await message.answer("Username не может быть пустым. Попробуйте ещё раз.")
        return

    # Проверяем что канал существует через Bot API
    try:
        chat = await bot.get_chat(f"@{username}")
    except Exception as e:
        logger.warning(f"Cannot get chat @{username}: {e}")
        await message.answer(
            f"❌ Не удалось найти канал <b>@{username}</b>.\n\n"
            "Убедитесь что:\n"
            "• Канал публичный\n"
            "• Username написан верно\n\n"
            "Попробуйте ещё раз:",
            parse_mode="HTML",
        )
        return

    if chat.type not in ("channel", "supergroup"):
        await message.answer("❌ Это не канал. Пожалуйста, укажите @username Telegram-канала.")
        return

    # Сохраняем данные в FSM
    bot_info = await bot.get_me()
    await state.update_data(
        channel_username=username,
        channel_telegram_id=chat.id,
        channel_title=chat.title or username,
    )
    await state.set_state(AddChannelStates.waiting_verification)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Я добавил бота, проверить", callback_data="check_bot_admin")]]
    )

    await message.answer(
        ADD_BOT_INSTRUCTION.format(bot_username=bot_info.username),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(AddChannelStates.waiting_verification, F.data == "check_bot_admin")
async def process_verify_bot_admin(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Верификация что бот добавлен администратором."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    channel_id = data.get("channel_telegram_id")
    channel_username = data.get("channel_username")

    if channel_id is None:
        await callback.answer("Ошибка сессии. Начните заново: /add_channel", show_alert=True)
        await state.clear()
        return

    # Проверяем права бота в канале через getChatMember
    try:
        bot_info = await bot.get_me()
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot_info.id)
    except Exception as e:
        logger.error(f"Cannot check bot membership in {channel_id}: {e}")
        await callback.answer("Не удалось проверить права. Попробуйте ещё раз.", show_alert=True)
        return

    # Проверяем что бот является администратором с правом публикации
    is_admin = member.status == "administrator" and getattr(member, "can_post_messages", False)

    if not is_admin:
        await safe_callback_edit(
            callback,
            "❌ <b>Бот не найден среди администраторов</b> или у него нет права публикации.\n\n"
            "Пожалуйста:\n"
            "1. Убедитесь что бот добавлен как администратор\n"
            "2. Включите право <b>«Публикация сообщений»</b>\n"
            "3. Нажмите кнопку снова",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Проверить ещё раз", callback_data="check_bot_admin")]]
            ),
            parse_mode="HTML",
        )
        return

    # ✅ Бот является администратором — сохраняем в БД
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        chat_repo = ChatAnalyticsRepository(session)

        # Получаем внутреннего пользователя по telegram_id
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден. Начните с /start", show_alert=True)
            await state.clear()
            return

        # Обновляем или создаём канал в БД
        if not channel_username:
            await callback.answer("❌ Ошибка данных канала. Начните заново: /add_channel", show_alert=True)
            await state.clear()
            return

        chat, _ = await chat_repo.get_or_create_chat(channel_username)
        chat.telegram_id = channel_id
        chat.title = data.get("channel_title", channel_username)
        chat.bot_is_admin = True
        chat.admin_added_at = datetime.now(UTC)
        chat.owner_user_id = user.id
        chat.is_accepting_ads = False  # Пока не установили цену и тематики

        await session.flush()

    logger.info(f"Channel @{channel_username} verified: bot is admin. Owner: {callback.from_user.id}")

    # Переходим к следующему шагу — цена за пост
    await state.set_state(AddChannelStates.waiting_price)
    await safe_callback_edit(
        callback,
        f"✅ <b>Отлично! Бот добавлен в @{channel_username}</b>\n\n"
        "Теперь укажите <b>цену за один рекламный пост</b> (в рублях).\n\n"
        "Например: <code>1500</code>\n\n"
        "💡 Рекламодатели увидят эту цену в каталоге.",
        parse_mode="HTML",
    )


@router.message(AddChannelStates.waiting_price)
async def process_channel_price(message: Message, state: FSMContext) -> None:
    """Обработка введённой цены за пост."""
    text = (message.text or "").strip()

    if not text.isdigit() or int(text) <= 0:
        await message.answer(
            "❌ Пожалуйста, введите цену числом (только цифры, больше 0).\n"
            "Например: <code>1500</code>",
            parse_mode="HTML",
        )
        return

    price = int(text)
    if price < 100:
        await message.answer("❌ Минимальная цена — 100 рублей. Укажите другую цену:")
        return

    await state.update_data(price_per_post=price)
    await state.set_state(AddChannelStates.waiting_topics)

    # Создаём клавиатуру с тематиками
    keyboard_buttons = []
    for i in range(0, len(TOPICS), 3):
        row = [
            InlineKeyboardButton(text=label, callback_data=f"topic_{code}")
            for label, code in TOPICS[i : i + 3]
        ]
        keyboard_buttons.append(row)

    keyboard_buttons.append(
        [InlineKeyboardButton(text="✅ Готово (выбрать позже)", callback_data="topics_done")]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        f"💰 Цена <b>{price} ₽</b> за пост — записано.\n\n"
        "Теперь выберите <b>тематики</b> которые подходят вашему каналу.\n"
        "Рекламодатели используют их для поиска:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(AddChannelStates.waiting_topics, F.data.startswith("topic_") | (F.data == "topics_done"))
async def process_channel_topics(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработка выбора тематик (мультиселект или завершение)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    selected_topics: list[str] = data.get("selected_topics", [])

    if callback.data == "topics_done":
        # Завершение — активируем канал
        await _finalize_channel_registration(callback, state, selected_topics)
        return

    # Тоггл тематики
    topic_code = (callback.data or "").replace("topic_", "")
    if topic_code in selected_topics:
        selected_topics.remove(topic_code)
    else:
        selected_topics.append(topic_code)

    await state.update_data(selected_topics=selected_topics)

    topics_str = ", ".join(selected_topics) if selected_topics else "не выбрано"
    await callback.answer(f"Выбрано: {topics_str}"[:200])


async def _finalize_channel_registration(
    callback: CallbackQuery,
    state: FSMContext,
    selected_topics: list[str],
) -> None:
    """Финальный шаг — сохранение канала и активация в каталоге."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    channel_username = data.get("channel_username", "")
    channel_telegram_id = data.get("channel_telegram_id")
    channel_title = data.get("channel_title", channel_username)
    price_per_post = data.get("price_per_post")

    # Сохраняем в БД
    async with async_session_factory() as session:
        chat_repo = ChatAnalyticsRepository(session)

        # Получаем или создаём канал
        if channel_username:
            chat, _ = await chat_repo.get_or_create_chat(channel_username)
            chat.telegram_id = channel_telegram_id
            chat.title = channel_title
            chat.topic = ",".join(selected_topics) if selected_topics else None
            chat.price_per_post = price_per_post
            chat.is_accepting_ads = True  # Теперь канал готов принимать рекламу

            await session.flush()

    await state.clear()

    topics_display = ", ".join(selected_topics) if selected_topics else "будут указаны позже"

    await safe_callback_edit(
        callback,
        f"🎉 <b>Канал @{channel_username} успешно зарегистрирован!</b>\n\n"
        f"📺 Канал: {channel_title}\n"
        f"💰 Цена за пост: {price_per_post} ₽\n"
        f"🏷 Тематики: {topics_display}\n\n"
        "✅ Канал виден рекламодателям в каталоге.\n\n"
        "Управление каналом: /my_channels",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
# /my_channels — список каналов владельца
# ─────────────────────────────────────────────

@router.message(Command("my_channels"))
async def cmd_my_channels(message: Message) -> None:
    """
    Список каналов зарегистрированных пользователем.
    Показывает статус, баланс к выплате и быстрые кнопки управления.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        chat_repo = ChatAnalyticsRepository(session)

        user = await user_repo.get_by_telegram_id(message.from_user.id)  # type: ignore[union-attr]
        if not user:
            await message.answer("❌ Пользователь не найден. Начните с /start")
            return

        channels = await chat_repo.get_by_owner_id(user.id)  # type: ignore[arg-type]
        if not channels:
            await message.answer(
                "У вас нет зарегистрированных каналов.\n\n"
                "Добавьте канал командой /add_channel"
            )
            return

        # Строим клавиатуру с каналами
        keyboard_buttons = []
        for channel in channels:
            if channel.username is None:
                continue
            status_icon = "🟢" if channel.is_accepting_ads else "🔴"
            price_str = f"{channel.price_per_post or 0} ₽"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{status_icon} @{channel.username} — {price_str}",
                    callback_data=f"channel_menu:{channel.id}",
                )
            ])

        keyboard_buttons.append([InlineKeyboardButton(text="📊 Статистика", callback_data="channels_stats")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer(
            f"📺 <b>Ваши каналы ({len(channels)})</b>\n\n"
            f"Нажмите на канал для управления:",
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("channel_menu:"))
async def show_channel_menu(callback: CallbackQuery) -> None:
    """
    Меню управления конкретным каналом.
    Показывает статистику и кнопки действий.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)

        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Считаем количество размещений
        total_placements = len(channel.mailing_logs) if channel.mailing_logs else 0

        # Считаем сумму к выплате
        pending_payouts = sum(p.amount for p in channel.payouts if p.is_pending) if channel.payouts else Decimal("0")

        status_icon = "🟢" if channel.is_accepting_ads else "🔴"
        status_text = "Принимает рекламу" if channel.is_accepting_ads else "Реклама отключена"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[  # type: ignore[unused-ignore]
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"ch_settings:{channel_id}"),
                InlineKeyboardButton(text="📊 Аналитика", callback_data=f"ch_analytics:{channel_id}"),
            ],
            [
                InlineKeyboardButton(text="📋 Заявки", callback_data=f"ch_requests:{channel_id}"),
                InlineKeyboardButton(text="💰 Выплаты", callback_data=f"ch_payouts:{channel_id}"),
            ],
            [
                InlineKeyboardButton(
                    text="🔴 Отключить рекламу" if channel.is_accepting_ads else "🟢 Включить рекламу",
                    callback_data=f"ch_toggle:{channel_id}",
                ),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="my_channels_back")],
        ])

        await safe_callback_edit(
            callback,
            f"📺 <b>@{channel.username or channel.title}</b>\n\n"
            f"👥 Подписчиков: {channel.member_count:,}\n"
            f"💰 Цена за пост: {channel.price_per_post or 0} ₽\n"
            f"📈 Размещений всего: {total_placements}\n"
            f"💸 К выплате: {pending_payouts:.0f} ₽\n"
            f"{status_icon} {status_text}",
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("ch_settings:"))
async def show_channel_settings(callback: CallbackQuery) -> None:
    """Меню настроек канала."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"ch_edit_price:{channel_id}")],
        [InlineKeyboardButton(text="🏷 Изменить тематики", callback_data=f"ch_edit_topics:{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"channel_menu:{channel_id}")],
    ])

    await safe_callback_edit(
        callback,
        "⚙️ <b>Настройки канала</b>\n\nЧто хотите изменить?",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("ch_toggle:"))
async def toggle_accepting_ads(callback: CallbackQuery) -> None:
    """Переключить статус приёма рекламы."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        if channel:
            channel.is_accepting_ads = not channel.is_accepting_ads
            await session.flush()
            await callback.answer(f"Реклама {'включена' if channel.is_accepting_ads else 'отключена'}")
            await show_channel_menu(callback)


@router.callback_query(F.data == "my_channels_back")
async def my_channels_back(callback: CallbackQuery) -> None:
    """Возврат к списку каналов."""
    await cmd_my_channels(callback.message)


# ─────────────────────────────────────────────
# Обработка входящих заявок на размещение
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("approve_placement:"))
async def approve_placement(callback: CallbackQuery) -> None:
    """
    Владелец канала одобряет заявку на размещение.
    Переводит размещение в статус QUEUED для исполнения рассыльщиком.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        from src.db.models.mailing_log import MailingLog, MailingStatus

        placement = await session.get(MailingLog, placement_id)
        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        if placement.status != MailingStatus.PENDING_APPROVAL:
            await callback.answer("Заявка уже обработана", show_alert=True)
            return

        placement.status = MailingStatus.QUEUED
        await session.flush()

    await safe_callback_edit(
        callback,
        "✅ <b>Заявка одобрена!</b>\n\n"
        "Пост будет опубликован в согласованное время.\n"
        "После публикации вы получите уведомление и выплата будет начислена.",
        parse_mode="HTML",
    )
    await callback.answer("Заявка одобрена")


@router.callback_query(F.data.startswith("reject_placement:"))
async def reject_placement(callback: CallbackQuery) -> None:
    """
    Владелец канала отклоняет заявку.
    Средства рекламодателя размораживаются и возвращаются на баланс.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        from src.db.models.mailing_log import MailingLog, MailingStatus

        placement = await session.get(MailingLog, placement_id)
        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        placement.status = MailingStatus.REJECTED
        await session.flush()

    await safe_callback_edit(
        callback,
        "❌ <b>Заявка отклонена</b>\n\n"
        "Средства рекламодателя будут возвращены на его баланс.",
        parse_mode="HTML",
    )
    await callback.answer("Заявка отклонена")
