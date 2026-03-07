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
from sqlalchemy import func, select

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
        "<b>Убедитесь что канал:</b>\n"
        "• Публичный (есть @username)\n"
        "• Не менее 500 подписчиков\n"
        "• Открытый (не закрытый для вступления)\n\n"
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
    await state.update_data(
        channel_username=username,
        channel_telegram_id=chat.id,
        channel_title=chat.title or username,
        member_count=chat.member_count or 0,
    )

    # Задача 4.2: Переходим в состояние ожидания подтверждения добавления бота
    await state.set_state(AddChannelStates.waiting_bot_admin_confirmation)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавил, проверьте", callback_data="channel_add:check_admin")],
            [InlineKeyboardButton(text="❓ Не могу найти бота", callback_data="channel_add:help_admin")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="channel_add:back_to_username")],
        ]
    )

    await message.answer(
        "📋 <b>Теперь добавьте @RekHarborBot администратором.</b>\n\n"
        "<b>Пошаговая инструкция:</b>\n"
        f"1. Откройте ваш канал @{username}\n"
        "2. Нажмите на название → \"Управление каналом\"\n"
        "3. \"Администраторы\" → \"Добавить администратора\"\n"
        "4. Найдите @RekHarborBot\n"
        "5. Оставьте включённым ТОЛЬКО \"Публикация сообщений\"\n"
        "6. Нажмите \"Сохранить\"\n\n"
        "🔒 <b>Бот не может:</b> удалять посты, управлять\n"
        "   участниками, редактировать описание канала.\n"
        "   Только публиковать.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(AddChannelStates.waiting_bot_admin_confirmation, F.data == "channel_add:check_admin")
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
        await callback.answer(
            "❌ Бот ещё не добавлен администратором или нет права публикации.\n"
            "Следуйте инструкции выше и нажмите «Добавил, проверьте» снова.",
            show_alert=True,
        )
        return

    # ✅ Бот является администратором — переходим к шагу цены
    await state.set_state(AddChannelStates.waiting_price)

    # Получаем member_count из FSM для расчёта рекомендаций
    member_count = data.get("member_count", 0)

    # Расчёт рекомендуемой цены
    min_price = max(50, member_count // 100) if member_count > 0 else 50
    rec_price = int(min_price * 2.5)

    await safe_callback_edit(
        callback,
        f"✅ <b>Отлично! Бот добавлен в @{channel_username}</b>\n\n"
        f"👥 Подписчиков: {member_count:,}\n\n"
        f"Теперь укажите <b>цену за один рекламный пост</b> (в кредитах).\n\n"
        f"<b>Рекомендации для канала ~{member_count:,} подп.:</b>\n"
        f"• Минимальная: {min_price} кр\n"
        f"• Оптимальная: {rec_price} кр ← рекомендуем\n"
        f"• Максимальная конкурентная: {min_price * 5} кр\n\n"
        f"Вы получаете 80% от указанной цены.\n"
        f"При цене {rec_price} кр → ваш заработок: {int(rec_price * 0.8)} кр/пост\n\n"
        f"Введите число:",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
# Обработчики для шага waiting_bot_admin_confirmation
# ─────────────────────────────────────────────

@router.callback_query(AddChannelStates.waiting_bot_admin_confirmation, F.data == "channel_add:help_admin")
async def process_help_admin(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать помощь по добавлению бота администратором."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К инструкции", callback_data="channel_add:back_to_admin_instruction")],
        ]
    )

    await callback.message.answer(
        "❓ <b>Как найти @RekHarborBot</b>\n\n"
        "В поле поиска администраторов введите:\n"
        "• RekHarborBot\n"
        "• или @RekHarborBot\n\n"
        "Если бот не ищется — попробуйте сначала написать "
        "боту /start чтобы он появился в истории диалогов.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AddChannelStates.waiting_bot_admin_confirmation, F.data == "channel_add:back_to_admin_instruction")
async def process_back_to_admin_instruction(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Показать инструкцию заново."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    username = data.get("channel_username", "канала")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавил, проверьте", callback_data="channel_add:check_admin")],
            [InlineKeyboardButton(text="❓ Не могу найти бота", callback_data="channel_add:help_admin")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="channel_add:back_to_username")],
        ]
    )

    await safe_callback_edit(
        callback,
        f"📋 <b>Теперь добавьте @RekHarborBot администратором.</b>\n\n"
        f"<b>Пошаговая инструкция:</b>\n"
        f"1. Откройте ваш канал @{username}\n"
        f"2. Нажмите на название → \"Управление каналом\"\n"
        f"3. \"Администраторы\" → \"Добавить администратора\"\n"
        f"4. Найдите @RekHarborBot\n"
        f"5. Оставьте включённым ТОЛЬКО \"Публикация сообщений\"\n"
        f"6. Нажмите \"Сохранить\"\n\n"
        f"🔒 <b>Бот не может:</b> удалять посты, управлять\n"
        f"   участниками, редактировать описание канала.\n"
        f"   Только публиковать.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AddChannelStates.waiting_bot_admin_confirmation, F.data == "channel_add:back_to_username")
async def process_back_to_username(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к шагу ввода username."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(AddChannelStates.waiting_username)

    await safe_callback_edit(
        callback,
        "📺 <b>Регистрация канала на платформе</b>\n\n"
        "Введите @username вашего канала (например: @mychannel)\n\n"
        "<b>Убедитесь что канал:</b>\n"
        "• Публичный (есть @username)\n"
        "• Не менее 500 подписчиков\n"
        "• Открытый (не закрытый для вступления)",
        parse_mode="HTML",
    )
    await callback.answer()


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
    if price < 50:
        await message.answer("❌ Минимальная цена — 50 кредитов. Укажите другую цену:")
        return

    await state.update_data(price_per_post=price)
    await state.set_state(AddChannelStates.waiting_topics)

    # Задача 4.4: Создаём клавиатуру с тематиками (toggle)
    data = await state.get_data()
    selected_topics: list[str] = data.get("selected_topics", [])

    keyboard_buttons = []
    for label, code in TOPICS:
        prefix = "✅ " if code in selected_topics else ""
        keyboard_buttons.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"topic_toggle_{code}")])

    done_text = f"✅ Готово (выбрано: {len(selected_topics)})" if selected_topics else "✅ Готово"
    keyboard_buttons.append([InlineKeyboardButton(text=done_text, callback_data="topics_done")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_price")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        f"💰 Цена <b>{price} кр</b> за пост — записано.\n\n"
        "<b>Какую рекламу вы готовы публиковать?</b>\n"
        "Выберите одну или несколько тематик:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(AddChannelStates.waiting_topics, F.data.startswith("topic_toggle_"))
async def process_channel_topics_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора тематик (toggle — добавить/убрать)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    selected_topics: list[str] = data.get("selected_topics", [])

    # Тоггл тематики
    topic_code = (callback.data or "").replace("topic_toggle_", "")
    if topic_code in selected_topics:
        selected_topics.remove(topic_code)
    else:
        selected_topics.append(topic_code)

    await state.update_data(selected_topics=selected_topics)

    # Перерисовываем клавиатуру с обновлёнными галочками
    keyboard_buttons = []
    for label, code in TOPICS:
        prefix = "✅ " if code in selected_topics else ""
        keyboard_buttons.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"topic_toggle_{code}")])

    done_text = f"✅ Готово (выбрано: {len(selected_topics)})" if selected_topics else "✅ Готово"
    keyboard_buttons.append([InlineKeyboardButton(text=done_text, callback_data="topics_done")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_price")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(AddChannelStates.waiting_topics, F.data == "topics_done")
async def process_channel_topics_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершение выбора тематик — переход к настройкам."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    selected_topics: list[str] = data.get("selected_topics", [])

    if not selected_topics:
        await callback.answer("⚠️ Выберите хотя бы одну тематику", show_alert=True)
        return

    # Переход к шагу waiting_settings
    await state.set_state(AddChannelStates.waiting_settings)

    # Сохраняем дефолтные настройки
    await state.update_data(
        max_posts_per_day=2,
        approval_mode="auto",
    )

    await show_settings_step(callback, state)


@router.callback_query(AddChannelStates.waiting_topics, F.data == "back_to_price")
async def process_back_to_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к шагу ввода цены."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(AddChannelStates.waiting_price)

    data = await state.get_data()
    member_count = data.get("member_count", 0)

    # Расчёт рекомендаций
    min_price = max(50, member_count // 100) if member_count > 0 else 50
    rec_price = int(min_price * 2.5)

    await safe_callback_edit(
        callback,
        f"💰 <b>Укажите цену за один рекламный пост</b> (в кредитах).\n\n"
        f"<b>Рекомендации для канала ~{member_count:,} подп.:</b>\n"
        f"• Минимальная: {min_price} кр\n"
        f"• Оптимальная: {rec_price} кр ← рекомендуем\n"
        f"• Максимальная конкурентная: {min_price * 5} кр\n\n"
        f"Вы получаете 80% от указанной цены.\n"
        f"При цене {rec_price} кр → ваш заработок: {int(rec_price * 0.8)} кр/пост\n\n"
        f"Введите число:",
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────
# Шаг waiting_settings — параметры размещения
# ─────────────────────────────────────────────

async def show_settings_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать шаг настроек размещения."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    max_posts = data.get("max_posts_per_day", 2)
    approval_mode = data.get("approval_mode", "auto")

    # Кнопки для max_posts_per_day
    max_posts_buttons = []
    for n in [1, 2, 3, 5]:
        prefix = "→ " if n == max_posts else ""
        label = f"{prefix}{n} пост" if n == 1 else f"{prefix}{n} поста"
        max_posts_buttons.append([InlineKeyboardButton(text=label, callback_data=f"channel_add:max_posts:{n}")])

    # Кнопки для approval_mode
    approval_buttons = [
        [
            InlineKeyboardButton(
                text=f"{'→ ' if approval_mode == 'auto' else ''}🤖 Авто за 24ч",
                callback_data="channel_add:approval:auto",
            ),
            InlineKeyboardButton(
                text=f"{'→ ' if approval_mode == 'manual' else ''}👁 Только вручную",
                callback_data="channel_add:approval:manual",
            ),
        ],
    ]

    # Кнопки навигации
    nav_buttons = [
        [InlineKeyboardButton(text="✅ Далее", callback_data="channel_add:settings_done")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_topics")],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=max_posts_buttons + approval_buttons + nav_buttons,
    )

    approval_text = (
        "🤖 <b>Авто за 24ч</b> — если вы не ответите в течение 24 часов, заявка одобряется"
        if approval_mode == "auto"
        else "👁 <b>Только вручную</b> — каждая заявка требует вашего одобрения"
    )

    await safe_callback_edit(
        callback,
        f"⚙️ <b>Настройте параметры размещения:</b>\n\n"
        f"<b>Максимум постов в день:</b>\n"
        f"→ {max_posts} (выберите ниже)\n\n"
        f"<b>Режим одобрения заявок:</b>\n"
        f"{approval_text}\n\n"
        f"💡 <i>Можно изменить позже в настройках канала.</i>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AddChannelStates.waiting_settings, F.data.startswith("channel_add:max_posts:"))
async def process_max_posts_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменение лимита постов в день."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    n = int((callback.data or "").split(":")[-1])
    await state.update_data(max_posts_per_day=n)
    await show_settings_step(callback, state)


@router.callback_query(AddChannelStates.waiting_settings, F.data.startswith("channel_add:approval:"))
async def process_approval_mode_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменение режима одобрения."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    mode = (callback.data or "").split(":")[-1]
    await state.update_data(approval_mode=mode)
    await show_settings_step(callback, state)


@router.callback_query(AddChannelStates.waiting_settings, F.data == "channel_add:settings_done")
async def process_settings_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершение настроек — переход к подтверждению."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(AddChannelStates.waiting_confirm)
    await show_confirm_step(callback, state)


@router.callback_query(AddChannelStates.waiting_settings, F.data == "back_to_topics")
async def process_back_to_topics(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к шагу выбора тематик."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(AddChannelStates.waiting_topics)

    data = await state.get_data()
    selected_topics: list[str] = data.get("selected_topics", [])

    keyboard_buttons = []
    for label, code in TOPICS:
        prefix = "✅ " if code in selected_topics else ""
        keyboard_buttons.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"topic_toggle_{code}")])

    done_text = f"✅ Готово (выбрано: {len(selected_topics)})" if selected_topics else "✅ Готово"
    keyboard_buttons.append([InlineKeyboardButton(text=done_text, callback_data="topics_done")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_price")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await safe_callback_edit(
        callback,
        "<b>Какую рекламу вы готовы публиковать?</b>\n"
        "Выберите одну или несколько тематик:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────
# Шаг waiting_confirm — подтверждение
# ─────────────────────────────────────────────

async def show_confirm_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать шаг подтверждения."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    username = data.get("channel_username", "")
    member_count = data.get("member_count", 0)
    selected_topics: list[str] = data.get("selected_topics", [])
    price = data.get("price_per_post", 0)
    max_posts = data.get("max_posts_per_day", 2)
    approval_mode = data.get("approval_mode", "auto")

    topics_display = ", ".join([t.capitalize() for t in selected_topics]) if selected_topics else "Не указаны"
    approval_text = "автоодобрение через 24 ч" if approval_mode == "auto" else "только вручную"
    owner_payout = int(price * 0.8) if price else 0

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавить канал", callback_data="channel_add:confirm")],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="back_to_settings")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="main:main_menu")],
        ]
    )

    await safe_callback_edit(
        callback,
        f"✅ <b>Всё готово! Проверьте параметры:</b>\n\n"
        f"📺 @{username}\n"
        f"👥 {member_count:,} подписчиков\n"
        f"🏷 Тематика: {topics_display}\n"
        f"💰 Цена: {price} кр → вы получаете: {owner_payout} кр/пост\n"
        f"📋 Режим: {approval_text}\n"
        f"📅 Лимит: {max_posts} поста в день\n\n"
        f"Канал появится в каталоге рекламодателей сразу после добавления.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AddChannelStates.waiting_confirm, F.data == "back_to_settings")
async def process_back_to_settings(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к шагу настроек."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(AddChannelStates.waiting_settings)
    await show_settings_step(callback, state)


@router.callback_query(AddChannelStates.waiting_confirm, F.data == "channel_add:confirm")
async def process_confirm_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение добавления канала — сохранение в БД."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    channel_username = data.get("channel_username", "")
    channel_telegram_id = data.get("channel_telegram_id")
    channel_title = data.get("channel_title", channel_username)
    member_count = data.get("member_count", 0)
    price_per_post = data.get("price_per_post", 0)
    selected_topics: list[str] = data.get("selected_topics", [])
    max_posts_per_day = data.get("max_posts_per_day", 2)
    approval_mode = data.get("approval_mode", "auto")

    # Сохраняем в БД
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        chat_repo = ChatAnalyticsRepository(session)

        # Получаем внутреннего пользователя
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден. Начните с /start", show_alert=True)
            await state.clear()
            return

        # Получаем или создаём канал
        if channel_username:
            chat, _ = await chat_repo.get_or_create_chat(channel_username)
            chat.telegram_id = channel_telegram_id
            chat.title = channel_title
            chat.member_count = member_count
            chat.topic = ",".join(selected_topics) if selected_topics else None
            chat.price_per_post = price_per_post
            chat.max_posts_per_day = max_posts_per_day
            chat.approval_mode = approval_mode
            chat.bot_is_admin = True
            chat.admin_added_at = datetime.now(UTC)
            chat.owner_user_id = user.id
            chat.is_accepting_ads = True
            chat.is_active = True

            await session.flush()

    await state.clear()

    topics_display = ", ".join(selected_topics) if selected_topics else "будут указаны позже"

    await safe_callback_edit(
        callback,
        f"🎉 <b>Канал @{channel_username} успешно зарегистрирован!</b>\n\n"
        f"📺 Канал: {channel_title}\n"
        f"👥 {member_count:,} подписчиков\n"
        f"💰 Цена за пост: {price_per_post} кр\n"
        f"🏷 Тематики: {topics_display}\n"
        f"📅 Лимит постов: {max_posts_per_day}/день\n"
        f"📋 Режим: {'авто' if approval_mode == 'auto' else 'ручной'}\n\n"
        f"✅ Канал виден рекламодателям в каталоге.\n\n"
        f"Управление каналом: /my_channels",
        parse_mode="HTML",
    )


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

            # Задача 4.7: Определить тематику и статус
            topic_display = channel.topic or "Не указана"
            status_icon = "✅ Принимает рекламу" if channel.is_accepting_ads else "⏸ Пауза"

            # Задача 4.7: Количество ожидающих заявок
            from src.db.models.mailing_log import MailingStatus
            pending_count = sum(1 for log in channel.mailing_logs if log.status == MailingStatus.PENDING_APPROVAL) if channel.mailing_logs else 0

            price_str = f"{channel.price_per_post or 0} кр"

            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📺 @{channel.username} — {topic_display}",
                    callback_data=f"channel_menu:{channel.id}",
                )
            ])
            # Задача 4.7: Добавляем информацию под кнопкой
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"  💰 {price_str}  •  {status_icon}  •  Заявок: {pending_count}",
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

        # Задача 4.7: Статус приёма рекламы
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
                # Задача 4.7: Кнопка паузы/возобновления
                InlineKeyboardButton(
                    text="⏸ Пауза" if channel.is_accepting_ads else "▶️ Возобновить",
                    callback_data=f"ch_toggle:{channel_id}",
                ),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="my_channels_back")],
        ])

        await safe_callback_edit(
            callback,
            f"📺 <b>@{channel.username or channel.title}</b>\n\n"
            f"👥 Подписчиков: {channel.member_count:,}\n"
            f"💰 Цена за пост: {channel.price_per_post or 0} кр\n"
            f"📈 Размещений всего: {total_placements}\n"
            f"💸 К выплате: {pending_payouts:.0f} кр\n"
            f"{status_text}",
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
            # Обновляем меню с новой кнопкой
            await show_channel_menu(callback)


@router.callback_query(F.data == "my_channels_back")
async def my_channels_back(callback: CallbackQuery) -> None:
    """Возврат к списку каналов."""
    await cmd_my_channels(callback.message)


# ─────────────────────────────────────────────
# Обработка входящих заявок на размещение
# ─────────────────────────────────────────────

async def show_placement_card(callback: CallbackQuery, placement_id: int) -> None:
    """Показать карточку заявки на размещение (Задача 4.8)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    async with async_session_factory() as session:
        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog

        placement = await session.get(MailingLog, placement_id)
        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        # Получаем кампанию
        campaign = await session.get(Campaign, placement.campaign_id)
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Задача 4.8: Подсчитаем кампании рекламодателя
        advertiser_campaigns_count = await session.execute(
            select(func.count(Campaign.id)).where(Campaign.user_id == campaign.user_id)
        )
        advertiser_campaigns_count = advertiser_campaigns_count.scalar_one() or 0

        # Задача 4.8: Время истечения 24ч
        from datetime import timedelta
        time_left = placement.created_at + timedelta(hours=24) - datetime.now(UTC)
        hours_left = max(0, int(time_left.total_seconds() // 3600))
        mins_left = max(0, int((time_left.total_seconds() % 3600) // 60))

        # Задача 4.8: Выплата владельцу (80%)
        payout_amount = int(placement.cost * 0.8) if placement.cost else 0

        # Формируем текст карточки
        card_text = (
            f"📋 <b>Заявка #{placement.id}</b>  •  @{placement.chat.username if placement.chat else 'канал'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>ТЕКСТ ПОСТА:</b>\n\n"
            f"{campaign.text[:500]}{'...' if len(campaign.text) > 500 else ''}\n\n"
        )

        # Задача 4.8: Добавить ссылку если есть
        if campaign.url:
            card_text += f"🔗 Ссылка: {campaign.url}\n"

        # Задача 4.8: Добавить информацию о медиа если есть
        if campaign.image_file_id:
            card_text += "🖼 Медиа: изображение прикреплено\n"

        card_text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Желаемое время: {placement.scheduled_at.strftime('%d.%m.%Y %H:%M') if placement.scheduled_at else 'Как можно скорее'}\n"
            f"⏱ Заявка истекает через: {hours_left} ч {mins_left} мин\n"
            f"💰 Ваша выплата: {payout_amount} кр (80% от {placement.cost} кр)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ Рекламодатель: {advertiser_campaigns_count} кампаний"
        )

        # Задача 4.9: Клавиатура с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_placement:{placement_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_placement_reason:{placement_id}")],
            [InlineKeyboardButton(text="✏️ Запросить правки", callback_data=f"request_changes_placement:{placement_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_requests:{placement.chat_id if placement.chat else 0}")],
        ])

        await safe_callback_edit(
            callback,
            card_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


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
        
        # Спринт 5: Начисляем XP владельцу за одобрение размещения
        from src.tasks.notification_tasks import notify_owner_xp_for_publication
        
        # 10 XP за одобрение заявки (дополнительно к 30 XP за публикацию)
        notify_owner_xp_for_publication.delay(
            owner_id=placement.chat.owner_user_id,
            channel_id=placement.chat_id,
            placement_id=placement_id,
        )

    await callback.answer("✅ Заявка одобрена!")

    # Показываем карточку заново с обновлённым статусом
    await show_placement_card(callback, placement_id)


@router.callback_query(F.data.startswith("reject_placement_reason:"))
async def reject_placement_reason(callback: CallbackQuery) -> None:
    """
    Задача 4.9: Промежуточная клавиатура выбора причины отклонения.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])

    # Задача 4.9: Список причин
    reasons = [
        ("🚫 Не моя тематика", "topic"),
        ("📝 Плохой текст", "text_quality"),
        ("📅 Неудобное время", "timing"),
        ("💰 Цена слишком низкая", "price"),
        ("🔒 Временно не принимаю рекламу", "paused"),
        ("✍️ Другая причина", "other"),
    ]

    keyboard_buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"reject_placement:{placement_id}:{code}")]
        for label, code in reasons
    ]
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data=f"show_placement:{placement_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await safe_callback_edit(
        callback,
        "❌ <b>Выберите причину отклонения:</b>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reject_placement:"))
async def reject_placement(callback: CallbackQuery) -> None:
    """
    Задача 4.9: Владелец канала отклоняет заявку с указанием причины.
    Средства рекламодателя размораживаются и возвращаются на баланс.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = (callback.data or "").split(":")
    placement_id = int(data[1])
    reason_code = data[2] if len(data) > 2 else "other"

    async with async_session_factory() as session:
        from src.db.models.mailing_log import MailingLog, MailingStatus

        placement = await session.get(MailingLog, placement_id)
        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        # Задача 4.9: Сохраняем причину
        placement.status = MailingStatus.REJECTED
        placement.rejection_reason = reason_code
        await session.flush()

    # Задача 4.9: Уведомление рекламодателю будет отправлено через notification_service

    await callback.answer("❌ Заявка отклонена")

    # Возвращаемся к списку заявок
    await show_placement_card(callback, placement_id)


@router.callback_query(F.data.startswith("request_changes_placement:"))
async def request_changes_placement(callback: CallbackQuery) -> None:
    """
    Задача 4.10: Владелец запрашивает правки текста.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog, MailingStatus

        placement = await session.get(MailingLog, placement_id)
        if not placement:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        campaign = await session.get(Campaign, placement.campaign_id)
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Задача 4.10: Устанавливаем статус
        placement.status = MailingStatus.CHANGES_REQUESTED
        await session.flush()

        # Задача 4.10: Отправляем уведомление рекламодателю
        from src.tasks.notification_tasks import notify_user

        channel_username = placement.chat.username if placement.chat else "канала"

        notify_user.delay(
            user_id=campaign.user_id,
            message=f"✏️ Владелец @{channel_username} просит исправить текст рекламного поста.\n\n"
                    f"Кампания: \"{campaign.title}\"\n"
                    f"Канал: @{channel_username}\n\n"
                    f"Отредактируйте текст кампании и отправьте заявку повторно.",
            parse_mode="HTML",
        )

    await callback.answer("✅ Запрос на правки отправлен рекламодателю")

    # Показываем карточку заново
    await show_placement_card(callback, placement_id)


@router.callback_query(F.data.startswith("show_placement:"))
async def show_placement(callback: CallbackQuery) -> None:
    """Показать карточку заявки (для кнопки 'Назад')."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])
    await show_placement_card(callback, placement_id)
