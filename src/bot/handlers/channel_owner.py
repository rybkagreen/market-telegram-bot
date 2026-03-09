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

from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.states.channel_owner import AddChannelStates, EditChannelStates, PayoutRequestStates
from src.bot.states.mediakit import MediakitStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.core.services.mediakit_service import mediakit_service
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
        member_count=getattr(chat, "member_count", 0) or 0,  # type: ignore[arg-type]  # ChatFullInfo may not have member_count
    )

    # Задача 4.2: Переходим в состояние ожидания подтверждения добавления бота
    await state.set_state(AddChannelStates.waiting_bot_admin_confirmation)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Добавил, проверьте", callback_data="channel_add:check_admin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Не могу найти бота", callback_data="channel_add:help_admin"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="channel_add:back_to_username")],
            [InlineKeyboardButton(text="✖ Отмена", callback_data="main:main_menu")],
        ]
    )

    await message.answer(
        "📋 <b>Теперь добавьте @RekHarborBot администратором.</b>\n\n"
        "<b>Пошаговая инструкция:</b>\n"
        f"1. Откройте ваш канал @{username}\n"
        '2. Нажмите на название → "Управление каналом"\n'
        '3. "Администраторы" → "Добавить администратора"\n'
        "4. Найдите @RekHarborBot\n"
        '5. Оставьте включённым ТОЛЬКО "Публикация сообщений"\n'
        '6. Нажмите "Сохранить"\n\n'
        "🔒 <b>Бот не может:</b> удалять посты, управлять\n"
        "   участниками, редактировать описание канала.\n"
        "   Только публиковать.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    AddChannelStates.waiting_bot_admin_confirmation, F.data == "channel_add:check_admin"
)
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


@router.callback_query(
    AddChannelStates.waiting_bot_admin_confirmation, F.data == "channel_add:help_admin"
)
async def process_help_admin(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать помощь по добавлению бота администратором."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 К инструкции", callback_data="channel_add:back_to_admin_instruction"
                )
            ],
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


@router.callback_query(
    AddChannelStates.waiting_bot_admin_confirmation,
    F.data == "channel_add:back_to_admin_instruction",
)
async def process_back_to_admin_instruction(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    """Показать инструкцию заново."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    username = data.get("channel_username", "канала")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Добавил, проверьте", callback_data="channel_add:check_admin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Не могу найти бота", callback_data="channel_add:help_admin"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="channel_add:back_to_username")],
        ]
    )

    await safe_callback_edit(
        callback,
        f"📋 <b>Теперь добавьте @RekHarborBot администратором.</b>\n\n"
        f"<b>Пошаговая инструкция:</b>\n"
        f"1. Откройте ваш канал @{username}\n"
        f'2. Нажмите на название → "Управление каналом"\n'
        f'3. "Администраторы" → "Добавить администратора"\n'
        f"4. Найдите @RekHarborBot\n"
        f'5. Оставьте включённым ТОЛЬКО "Публикация сообщений"\n'
        f'6. Нажмите "Сохранить"\n\n'
        f"🔒 <b>Бот не может:</b> удалять посты, управлять\n"
        f"   участниками, редактировать описание канала.\n"
        f"   Только публиковать.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    AddChannelStates.waiting_bot_admin_confirmation, F.data == "channel_add:back_to_username"
)
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
        keyboard_buttons.append(
            [InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"topic_toggle_{code}")]
        )

    done_text = f"✅ Готово (выбрано: {len(selected_topics)})" if selected_topics else "✅ Готово"
    keyboard_buttons.append([InlineKeyboardButton(text=done_text, callback_data="topics_done")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_price")])
    keyboard_buttons.append([InlineKeyboardButton(text="✖ Отмена", callback_data="main:main_menu")])

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
        keyboard_buttons.append(
            [InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"topic_toggle_{code}")]
        )

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
        max_posts_buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"channel_add:max_posts:{n}")]
        )

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


@router.callback_query(
    AddChannelStates.waiting_settings, F.data.startswith("channel_add:max_posts:")
)
async def process_max_posts_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменение лимита постов в день."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    n = int((callback.data or "").split(":")[-1])
    await state.update_data(max_posts_per_day=n)
    await show_settings_step(callback, state)


@router.callback_query(
    AddChannelStates.waiting_settings, F.data.startswith("channel_add:approval:")
)
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
        keyboard_buttons.append(
            [InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"topic_toggle_{code}")]
        )

    done_text = f"✅ Готово (выбрано: {len(selected_topics)})" if selected_topics else "✅ Готово"
    keyboard_buttons.append([InlineKeyboardButton(text=done_text, callback_data="topics_done")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_price")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await safe_callback_edit(
        callback,
        "<b>Какую рекламу вы готовы публиковать?</b>\nВыберите одну или несколько тематик:",
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

    topics_display = (
        ", ".join([t.capitalize() for t in selected_topics]) if selected_topics else "Не указаны"
    )
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
                "У вас нет зарегистрированных каналов.\n\nДобавьте канал командой /add_channel"
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

            pending_count = (
                sum(
                    1
                    for log in channel.mailing_logs
                    if log.status == MailingStatus.PENDING_APPROVAL
                )
                if channel.mailing_logs
                else 0
            )

            price_str = f"{channel.price_per_post or 0} кр"

            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📺 @{channel.username} — {topic_display}",
                        callback_data=f"channel_menu:{channel.id}",
                    )
                ]
            )
            # Задача 4.7: Добавляем информацию под кнопкой
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"  💰 {price_str}  •  {status_icon}  •  Заявок: {pending_count}",
                        callback_data=f"channel_menu:{channel.id}",
                    )
                ]
            )

        keyboard_buttons.append(
            [InlineKeyboardButton(text="📊 Статистика", callback_data="channels_stats")]
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer(
            f"📺 <b>Ваши каналы ({len(channels)})</b>\n\nНажмите на канал для управления:",
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
        pending_payouts = (
            sum(p.amount for p in channel.payouts if p.is_pending)
            if channel.payouts
            else Decimal("0")
        )

        # Задача 4.7: Статус приёма рекламы
        status_text = "Принимает рекламу" if channel.is_accepting_ads else "Реклама отключена"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[  # type: ignore[unused-ignore]
                [
                    InlineKeyboardButton(
                        text="⚙️ Настройки", callback_data=f"ch_settings:{channel_id}"
                    ),
                    InlineKeyboardButton(
                        text="📊 Медиакит", callback_data=f"ch_mediakit:{channel_id}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Заявки", callback_data=f"ch_requests:{channel_id}"
                    ),
                    InlineKeyboardButton(
                        text="💰 Выплаты", callback_data=f"ch_payouts:{channel_id}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📜 История выплат", callback_data=f"ch_payout_history:{channel_id}"
                    ),
                ],
                [
                    # Задача 4.7: Кнопка паузы/возобновления
                    InlineKeyboardButton(
                        text="⏸ Пауза" if channel.is_accepting_ads else "▶️ Возобновить",
                        callback_data=f"ch_toggle:{channel_id}",
                    ),
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="my_channels_back")],
            ]
        )

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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Изменить цену", callback_data=f"ch_edit_price:{channel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏷 Изменить тематики", callback_data=f"ch_edit_topics:{channel_id}"
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"channel_menu:{channel_id}")],
        ]
    )

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
            await callback.answer(
                f"Реклама {'включена' if channel.is_accepting_ads else 'отключена'}"
            )
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
        if campaign.tracking_url:
            card_text += f"🔗 Ссылка: {campaign.tracking_url}\n"

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
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Одобрить", callback_data=f"approve_placement:{placement_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отклонить", callback_data=f"reject_placement_reason:{placement_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ Запросить правки",
                        callback_data=f"request_changes_placement:{placement_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data=f"ch_requests:{placement.chat_id if placement.chat else 0}",
                    )
                ],
            ]
        )

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
        if placement.chat is not None and placement.chat.owner_user_id is not None:
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
    keyboard_buttons.append(
        [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"show_placement:{placement_id}")]
    )

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
            f'Кампания: "{campaign.title}"\n'
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


# ─────────────────────────────────────────────
# TASK 2: Выплаты — запрос выплаты владельцем
# ─────────────────────────────────────────────


@router.callback_query(F.data.startswith("ch_payouts:"))
async def show_channel_payouts(callback: CallbackQuery) -> None:
    """
    Показать экран выплат канала.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        from src.db.repositories.payout_repo import PayoutRepository

        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем что канал принадлежит пользователю
        if channel.owner_user_id != user.id:
            await callback.answer("❌ Это не ваш канал", show_alert=True)
            return

        # Получаем доступную сумму к выплате
        payout_repo = PayoutRepository(session)
        available_amount = await payout_repo.get_available_amount(user.id)

        # Получаем последние 5 выплат
        recent_payouts = await payout_repo.get_by_owner(user.id, limit=5, offset=0)

        # Формируем текст
        text = (
            f"💸 <b>Выплаты по каналу</b>\n\n"
            f"📺 @{channel.username or channel.title}\n\n"
            f"💰 <b>Доступно к выводу: {available_amount:.0f} кр</b>\n\n"
        )

        if recent_payouts:
            text += "<b>Последние выплаты:</b>\n"
            for payout in recent_payouts[:5]:
                status_icon = {
                    "pending": "⏳",
                    "processing": "🔄",
                    "paid": "✅",
                    "failed": "❌",
                    "cancelled": "🚫",
                }.get(payout.status.value, "📝")
                text += f"{status_icon} {payout.amount:.0f} кр ({payout.created_at.strftime('%d.%m')})\n"
        else:
            text += "История выплат пуста.\n"

        # Проверяем минимальную сумму выплаты
        from src.config.settings import settings

        min_payout = settings.min_payout_usdt * settings.credits_per_usdt  # Конвертируем в кредиты

        keyboard_buttons = []

        if available_amount >= min_payout:
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text="💸 Запросить выплату",
                        callback_data=f"request_payout:{channel_id}",
                    )
                ]
            )
        else:
            text += f"\n⚠️ Минимальная сумма выплаты: {min_payout:.0f} кр\n"

        keyboard_buttons.append(
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data=f"channel_menu:{channel_id}"),
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await safe_callback_edit(
            callback,
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("request_payout:"))
async def start_payout_request(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать запрос выплаты — выбор метода.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    await state.set_state(PayoutRequestStates.selecting_method)
    await state.update_data(channel_id=channel_id)

    text = (
        "💸 <b>Запрос выплаты</b>\n\n"
        "Выберите способ получения выплаты:\n\n"
        "💳 <b>USDT (TRC20)</b> — комиссия сети ~1 USDT\n"
        "💎 <b>TON</b> — комиссия сети ~0.1 TON\n\n"
        "Выплата будет отправлена на указанный вами кошелёк."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 USDT", callback_data=f"payout_method:{channel_id}:USDT"
                )
            ],
            [InlineKeyboardButton(text="💎 TON", callback_data=f"payout_method:{channel_id}:TON")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_payouts:{channel_id}")],
        ]
    )

    await safe_callback_edit(
        callback,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("payout_method:"))
async def select_payout_method(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбор метода выплаты — переход к вводу адреса.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = (callback.data or "").split(":")
    channel_id = int(data[1])
    method = data[2]

    await state.set_state(PayoutRequestStates.entering_address)
    await state.update_data(payout_method=method)

    method_name = "USDT (TRC20)" if method == "USDT" else "TON"
    method_example = (
        "TxxxxxxxxxxxxxxxxxxxxxxxxxxxxB" if method == "USDT" else "EQxxxxxxxxxxxxxxxxxxxxx"
    )

    text = (
        f"💸 <b>Введите адрес кошелька {method_name}</b>\n\n"
        f"Пример: <code>{method_example}</code>\n\n"
        "⚠️ Проверьте адрес внимательно — выплата будет отправлена на этот кошелёк.\n\n"
        "👇 Отправьте адрес кошелька сообщением ниже:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"request_payout:{channel_id}")],
        ]
    )

    await safe_callback_edit(
        callback,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(PayoutRequestStates.entering_address)
async def process_payout_address(message: Message, state: FSMContext) -> None:
    """
    Обработка адреса кошелька для выплаты.
    """
    if not message.text:
        await message.answer("Пожалуйста, отправьте адрес кошелька текстом.")
        return

    wallet_address = message.text.strip()
    data = await state.get_data()
    method = data.get("payout_method")

    # Валидация адреса
    if method == "USDT":
        # USDT (TRC20) — адрес начинается с T, длина 34 символа
        if len(wallet_address) < 34 or not wallet_address.startswith("T"):
            await message.answer(
                "❌ Неверный формат адреса USDT (TRC20).\n\n"
                "Адрес должен начинаться с 'T' и быть длиной 34 символа.\n\n"
                "Попробуйте ещё раз:"
            )
            return
    elif method == "TON" and not wallet_address.startswith(("EQ", "UQ")):
        # TON — адрес начинается с EQ или UQ
        await message.answer(
            "❌ Неверный формат адреса TON.\n\n"
            "Адрес должен начинаться с 'EQ' или 'UQ'.\n\n"
            "Попробуйте ещё раз:"
        )
        return

    await state.update_data(wallet_address=wallet_address)
    await state.set_state(PayoutRequestStates.confirming)

    # Получаем сумму к выплате
    async with async_session_factory() as session:
        from src.db.repositories.payout_repo import PayoutRepository

        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)  # type: ignore[union-attr]
        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        payout_repo = PayoutRepository(session)
        available_amount = await payout_repo.get_available_amount(user.id)

    # Обрезаем адрес для отображения
    if len(wallet_address) > 16:
        address_display = f"{wallet_address[:8]}...{wallet_address[-8:]}"
    else:
        address_display = wallet_address

    method_name = "USDT" if method == "USDT" else "TON"

    text = (
        "✅ <b>Подтвердите выплату</b>\n\n"
        f"💰 Сумма: <b>{available_amount:.0f} кр</b>\n"
        f"💳 Метод: <b>{method_name}</b>\n"
        f"🏦 Кошелёк: <code>{address_display}</code>\n\n"
        "⏱ Обработка занимает до 24 часов.\n\n"
        "Выберите действие:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"confirm_payout:{data.get('channel_id')}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=f"ch_payouts:{data.get('channel_id')}"
                )
            ],
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("confirm_payout:"))
async def confirm_payout_request(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Подтверждение запроса выплаты — создание Payout.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])
    data = await state.get_data()

    async with async_session_factory() as session:
        from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus
        from src.db.repositories.payout_repo import PayoutRepository

        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем доступную сумму
        payout_repo = PayoutRepository(session)
        available_amount = await payout_repo.get_available_amount(user.id)

        if available_amount <= 0:
            await callback.answer("❌ Нет доступных средств для выплаты", show_alert=True)
            return

        # Создаём запись о выплате
        payout = Payout(
            owner_id=user.id,
            channel_id=channel_id,
            placement_id=None,  # NULL для aggregate payout (не привязан к конкретному placement)
            amount=available_amount,
            platform_fee=Decimal("0"),  # Комиссия уже удержана при создании placement
            currency=PayoutCurrency.USDT
            if data.get("payout_method") == "USDT"
            else PayoutCurrency.TON,
            status=PayoutStatus.PENDING,
            wallet_address=data.get("wallet_address"),
        )

        session.add(payout)
        await session.flush()

    await state.clear()

    text = (
        "✅ <b>Заявка на выплату создана!</b>\n\n"
        f"💰 Сумма: <b>{available_amount:.0f} {data.get('payout_method', 'USDT')}</b>\n"
        f"🏦 Кошелёк: <code>{data.get('wallet_address')}</code>\n\n"
        "⏱ Обработка занимает до 24 часов.\n\n"
        "Вы получите уведомление когда выплата будет обработана."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📺 Мои каналы", callback_data=MainMenuCB(action="my_channels").pack()
                )
            ],
        ]
    )

    await safe_callback_edit(
        callback,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer("✅ Заявка создана!")


# ─────────────────────────────────────────────
# TASK 5: Редактирование настроек канала
# ─────────────────────────────────────────────


@router.callback_query(F.data.startswith("ch_edit_price:"))
async def start_edit_channel_price(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать редактирование цены канала.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    await state.set_state(EditChannelStates.waiting_new_price)
    await state.update_data(channel_id=channel_id)

    text = (
        "💰 <b>Изменение цены за пост</b>\n\n"
        "Введите новую цену за рекламный пост (в кредитах).\n\n"
        "⚠️ Минимальная цена: <b>50 кр</b>\n\n"
        "👇 Отправьте числовое значение:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_settings:{channel_id}")],
        ]
    )

    await safe_callback_edit(
        callback,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(EditChannelStates.waiting_new_price)
async def process_new_channel_price(message: Message, state: FSMContext) -> None:
    """
    Обработка новой цены канала.
    """
    if not message.text:
        await message.answer("Пожалуйста, введите число.")
        return

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Пожалуйста, введите число (только цифры).")
        return

    new_price = int(text)
    if new_price < 50:
        await message.answer("❌ Минимальная цена — 50 кредитов. Введите другую цену:")
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")

    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await message.answer("❌ Канал не найден.")
            await state.clear()
            return

        old_price = channel.price_per_post
        channel.price_per_post = new_price
        await session.flush()

    await state.clear()

    text = (
        "✅ <b>Цена обновлена!</b>\n\n"
        f"📺 Канал: @{channel.username}\n"
        f"💰 Старая цена: {old_price} кр\n"
        f"💰 Новая цена: <b>{new_price} кр</b>\n\n"
        f"Ваш заработок за пост: <b>{int(new_price * 0.8)} кр</b> (80%)"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"ch_settings:{channel_id}")],
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("ch_edit_topics:"))
async def start_edit_channel_topics(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать редактирование тематик канала.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Получаем текущие тематики
        current_topics = channel.topic.split(",") if channel.topic else []

        await state.set_state(EditChannelStates.choosing_topics)
        await state.update_data(channel_id=channel_id, current_topics=current_topics)

        # Список тематик (должен совпадать с topics в add_channel)
        topics = [
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

        # Строим клавиатуру с toggle кнопками
        keyboard_buttons = []
        for label, code in topics:
            prefix = "✅ " if code in current_topics else ""
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{prefix}{label}",
                        callback_data=f"topic_toggle:{channel_id}:{code}",
                    )
                ]
            )

        selected_count = len(current_topics)
        done_text = (
            f"✅ Сохранить ({selected_count} выбрано)" if selected_count > 0 else "✅ Сохранить"
        )
        keyboard_buttons.append(
            [
                InlineKeyboardButton(text=done_text, callback_data=f"topics_save:{channel_id}"),
            ]
        )
        keyboard_buttons.append(
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_settings:{channel_id}"),
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        text = (
            "🏷 <b>Редактирование тематик</b>\n\n"
            "Выберите тематики вашего канала.\n"
            "Нажмите на тематику чтобы добавить/убрать.\n\n"
            f"Текущие: {', '.join(current_topics) if current_topics else ' none'}"
        )

        await safe_callback_edit(
            callback,
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("topic_toggle:"))
async def toggle_channel_topic(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Переключить тематику канала (toggle).
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = (callback.data or "").split(":")
    channel_id = int(data[1])
    topic_code = data[2]

    data_store = await state.get_data()
    current_topics: list[str] = data_store.get("current_topics", [])

    # Toggle тематики
    if topic_code in current_topics:
        current_topics.remove(topic_code)
    else:
        current_topics.append(topic_code)

    await state.update_data(current_topics=current_topics)

    # Список тематик
    topics = [
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

    # Перерисовываем клавиатуру
    keyboard_buttons = []
    for label, code in topics:
        prefix = "✅ " if code in current_topics else ""
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix}{label}",
                    callback_data=f"topic_toggle:{channel_id}:{code}",
                )
            ]
        )

    selected_count = len(current_topics)
    done_text = f"✅ Сохранить ({selected_count} выбрано)" if selected_count > 0 else "✅ Сохранить"
    keyboard_buttons.append(
        [
            InlineKeyboardButton(text=done_text, callback_data=f"topics_save:{channel_id}"),
        ]
    )
    keyboard_buttons.append(
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_settings:{channel_id}"),
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    text = (
        "🏷 <b>Редактирование тематик</b>\n\n"
        "Выберите тематики вашего канала.\n\n"
        f"Текущие: {', '.join(current_topics) if current_topics else ' none'}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("topics_save:"))
async def save_channel_topics(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Сохранить выбранные тематики канала.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])
    data = await state.get_data()
    current_topics: list[str] = data.get("current_topics", [])

    if not current_topics:
        await callback.answer("⚠️ Выберите хотя бы одну тематику", show_alert=True)
        return

    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        channel.topic = ",".join(current_topics)
        await session.flush()

    await state.clear()

    text = (
        "✅ <b>Тематики обновлены!</b>\n\n"
        f"📺 Канал: @{channel.username}\n"
        f"🏷 Тематики: <b>{', '.join(current_topics)}</b>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"ch_settings:{channel_id}")],
        ]
    )

    await safe_callback_edit(
        callback,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer("✅ Тематики сохранены!")


# ─────────────────────────────────────────────
# СПРИНТ 9: МЕДИАКИТ КАНАЛА
# ─────────────────────────────────────────────


@router.callback_query(F.data.startswith("ch_mediakit:"))
async def show_channel_mediakit(callback: CallbackQuery) -> None:
    """Показать медиакит канала (режим редактирования для владельца)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat

        channel = await session.get(TelegramChat, channel_id)
        if not channel or channel.owner_user_id != callback.from_user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        # Получить или создать медиакит
        from src.core.services.mediakit_service import mediakit_service

        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)

    text = (
        f"📊 <b>Медиакит канала</b>\n\n"
        f"📡 @{channel.username or channel.title}\n\n"
        f"Статус: {'✅ Публичный' if mediakit.is_public else '🔒 Приватный'}\n"
        f"Просмотров: {mediakit.views_count}\n"
        f"Скачиваний: {mediakit.downloads_count}\n\n"
        f"Настройте медиакит чтобы привлечь больше рекламодателей."
    )

    from src.bot.keyboards.mediakit import get_mediakit_menu_kb

    keyboard = get_mediakit_menu_kb(channel_id)

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("mediakit_edit:"))
async def edit_mediakit(callback: CallbackQuery) -> None:
    """Редактирование медиакита."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    text = (
        "✏️ <b>Редактирование медиакита</b>\n\n"
        "Выберите что хотите изменить:\n\n"
        "📝 Описание\n"
        "🖼 Логотип\n"
        "🎨 Цвет темы\n"
        "📊 Метрики для отображения\n"
        "🔒 Настройки приватности"
    )

    from src.bot.keyboards.mediakit import get_mediakit_edit_kb

    keyboard = get_mediakit_edit_kb(channel_id)

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("mediakit_desc:"))
async def edit_mediakit_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактирование описания медиакита."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    await state.set_state(MediakitStates.waiting_description)
    await state.update_data(mediakit_channel_id=channel_id)

    text = (
        "📝 <b>Описание канала</b>\n\n"
        "Введите краткое описание вашего канала.\n"
        "Это поможет рекламодателям лучше понять вашу аудиторию.\n\n"
        "👇 Введите описание:"
    )

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"ch_mediakit:{channel_id}")],
        ]
    )

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.message(MediakitStates.waiting_description)
async def process_mediakit_description(message: Message, state: FSMContext) -> None:
    """Обработать введённое описание."""
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return

    description = message.text.strip()
    if len(description) > 2000:
        await message.answer("❌ Описание слишком длинное (максимум 2000 символов).")
        return

    data = await state.get_data()
    channel_id = data.get("mediakit_channel_id")

    if channel_id is None:
        await message.answer("❌ Ошибка: канал не найден. Начните сначала.")
        return

    async with async_session_factory() as session:
        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)
        mediakit.custom_description = description
        await session.commit()

    await state.clear()

    text = "✅ Описание сохранено!"
    await message.answer(text)


@router.callback_query(F.data.startswith("mediakit_logo:"))
async def edit_mediakit_logo(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить загрузку логотипа."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    await state.set_state(MediakitStates.waiting_logo)
    await state.update_data(mediakit_channel_id=channel_id)

    text = (
        "🖼 <b>Загрузка логотипа</b>\n\n"
        "Отправьте изображение логотипа канала.\n\n"
        "Требования:\n"
        "• Формат: PNG, JPG\n"
        "• Размер: до 5 MB\n"
        "• Соотношение: 1:1 (квадрат)\n\n"
        "👇 Отправьте изображение:"
    )

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"ch_mediakit:{channel_id}")],
        ]
    )

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.message(MediakitStates.waiting_logo, F.photo)
async def process_mediakit_logo_upload(message: Message, state: FSMContext) -> None:
    """Обработать загруженный логотип."""
    # Получить file_id самого большого фото
    if not message.photo:
        await message.answer("❌ Фото не найдено. Отправьте изображение.")
        return

    image_file_id = message.photo[-1].file_id

    data = await state.get_data()
    channel_id = data.get("mediakit_channel_id")

    if channel_id is None:
        await message.answer("❌ Ошибка: канал не найден. Начните сначала.")
        return

    async with async_session_factory() as session:
        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)
        mediakit.logo_file_id = image_file_id
        await session.commit()

    await state.clear()

    await message.answer("✅ Логотип сохранён!")


@router.callback_query(F.data.startswith("mediakit_color:"))
async def edit_mediakit_color(callback: CallbackQuery) -> None:
    """Выбор цвета темы."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    text = "🎨 <b>Выберите цвет темы</b>\n\nЦвет будет использоваться в PDF медиаките."

    from src.bot.keyboards.mediakit import get_color_selector_kb

    keyboard = get_color_selector_kb(channel_id)

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("mediakit_color_set:"))
async def set_mediakit_color(callback: CallbackQuery) -> None:
    """Установить цвет темы."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    parts = (callback.data or "").split(":")
    channel_id = int(parts[1])
    color = parts[2] if len(parts) > 2 else "#1a73e8"

    async with async_session_factory() as session:
        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)
        mediakit.theme_color = color
        await session.commit()

    await callback.answer(f"✅ Цвет установлен: {color}", show_alert=False)

    # Вернуться к меню редактирования
    await edit_mediakit(callback)


@router.callback_query(F.data.startswith("mediakit_download:"))
async def download_mediakit_pdf(callback: CallbackQuery) -> None:
    """Скачать PDF медиакита."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    await callback.answer("⏳ Генерирую PDF...", show_alert=False)

    async with async_session_factory() as session:
        # Получить медиакит
        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)

        # Получить данные
        mediakit_data = await mediakit_service.get_mediakit_data(channel_id)

        # Сгенерировать PDF
        from src.utils.mediakit_pdf import generate_mediakit_pdf

        pdf_bytes = generate_mediakit_pdf(mediakit_data)

        # Отправить файл
        from aiogram.types import BufferedInputFile

        await callback.message.answer_document(
            document=BufferedInputFile(pdf_bytes, filename=f"mediakit_{channel_id}.pdf"),
            caption=f"📊 Медиакит канала\n\nСгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        )

        # Засчитать скачивание
        mediakit.downloads_count += 1
        await session.commit()


# ─────────────────────────────────────────────
# TASK 3: Отзывы владельца о рекламодателе
# ─────────────────────────────────────────────


@router.callback_query(F.data.startswith("owner_review:"))
async def handle_owner_review(callback: CallbackQuery) -> None:
    """
    Владелец оценивает рекламодателя после публикации.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data_parts = (callback.data or "").split(":")
    if len(data_parts) != 3:
        await callback.answer("❌ Неверный формат", show_alert=True)
        return

    placement_id = int(data_parts[1])
    score = int(data_parts[2])

    async with async_session_factory() as session:
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat
        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog
        from src.db.models.review import Review, ReviewerRole

        # Получить placement
        placement = await session.get(MailingLog, placement_id)
        if not placement:
            await callback.answer("❌ Размещение не найдено", show_alert=True)
            return

        # Получить кампанию для получения advertiser_id
        campaign = await session.get(Campaign, placement.campaign_id)
        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Получить канал для получения owner_id
        channel = await session.get(TelegramChat, placement.chat_id)
        if not channel or not channel.owner_user_id:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Проверить что владелец ещё не оставлял отзыв
        stmt = select(Review).where(
            Review.placement_id == placement_id,
            Review.reviewer_id == channel.owner_user_id,
            Review.reviewer_role == ReviewerRole.OWNER,
        )
        result = await session.execute(stmt)
        existing_review = result.scalar_one_or_none()

        if existing_review:
            await callback.answer("⚠️ Вы уже оставляли отзыв для этого размещения", show_alert=True)
            return

        # Создать отзыв
        review = Review(
            reviewer_id=channel.owner_user_id,  # Владелец оставляет отзыв
            reviewee_id=campaign.user_id,  # Рекламодатель — тот кого оценивают
            channel_id=channel.id,
            placement_id=placement_id,
            reviewer_role=ReviewerRole.OWNER,
            score_material=score,  # Качество материала
            score_requirements=score,  # Адекватность требований
            score_payment=score,  # Скорость оплаты
            is_hidden=False,
        )

        session.add(review)
        await session.commit()

    await callback.answer(f"✅ Оценка {score} принята!")

    await safe_callback_edit(
        callback,
        "✅ <b>Спасибо за отзыв!</b>\n\n"
        f"Вы поставили оценку: {score} ⭐\n\n"
        "Ваше мнение поможет улучшить платформу.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "owner_review_skip")
async def handle_owner_review_skip(callback: CallbackQuery) -> None:
    """
    Пропуск отзыва владельца.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await safe_callback_edit(
        callback,
        "ℹ️ <b>Отзыв пропущен</b>\n\nВы всегда можете оставить отзыв позже через /my_channels",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
# TASK 2: История выплат
# ─────────────────────────────────────────────


@router.callback_query(F.data.startswith("ch_payout_history:"))
async def show_payout_history(callback: CallbackQuery) -> None:
    """
    Показать историю выплат по каналу (последние 20).
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        from sqlalchemy import select

        from src.db.models.payout import Payout

        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Получить последние 20 выплат
        stmt = (
            select(Payout)
            .where(Payout.channel_id == channel_id)
            .order_by(Payout.created_at.desc())
            .limit(20)
        )
        result = await session.execute(stmt)
        payouts = list(result.scalars().all())

        if not payouts:
            text = (
                f"💸 <b>История выплат по каналу</b>\n\n"
                f"📺 @{channel.username or channel.title}\n\n"
                f"История выплат пуста."
            )
        else:
            text = (
                f"💸 <b>История выплат по каналу</b>\n\n📺 @{channel.username or channel.title}\n\n"
            )

            total_paid = sum(p.amount for p in payouts if p.status.value == "paid")
            text += f"<b>Всего выплачено: {total_paid:.0f} кр</b>\n\n"

            for payout in payouts[:20]:
                status_icon = {
                    "pending": "⏳",
                    "processing": "🔄",
                    "paid": "✅",
                    "failed": "❌",
                    "cancelled": "🚫",
                }.get(payout.status.value, "📝")

                date_str = payout.created_at.strftime("%d.%m.%Y")
                text += f"{status_icon} {date_str}: <b>{payout.amount:.0f} кр</b>\n"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"channel_menu:{channel_id}")],
        ]
    )

    await safe_callback_edit(
        callback,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
