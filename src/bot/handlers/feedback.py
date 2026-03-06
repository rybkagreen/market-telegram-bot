"""
Handlers для обратной связи: отзывы, bug reports, идеи.

Все сообщения отправляются в Telegram-чат поддержки (SUPPORT_CHAT_ID из .env)
или напрямую админам из ADMIN_IDS.
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.feedback import FeedbackCB, get_feedback_confirm_kb, get_feedback_type_kb
from src.bot.keyboards.main_menu import MainMenuCB, get_main_menu
from src.bot.states.feedback import FeedbackStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.config.settings import settings
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()

# Типы обратной связи
FEEDBACK_TYPES = {
    "feedback": ("💬 Отзыв", "Поделитесь вашим мнением о боте"),
    "bug": ("🐛 Баг-репорт", "Опишите ошибку и шаги для её воспроизведения"),
    "idea": ("💡 Идея", "Предложите улучшение или новую функцию"),
}


@router.callback_query(MainMenuCB.filter(F.action == "feedback"))
async def handle_feedback_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Открыть меню обратной связи."""
    await state.clear()

    text = (
        "💬 <b>Обратная связь</b>\n\n"
        "Выберите тип обращения:\n\n"
        "💬 <b>Отзыв</b> — расскажите что нравится или что можно улучшить\n"
        "🐛 <b>Баг-репорт</b> — нашли ошибку? Опишите её\n"
        "💡 <b>Идея</b> — предложите новую функцию\n\n"
        "Мы читаем каждое сообщение! 🙏"
    )

    await safe_callback_edit(callback, text, reply_markup=get_feedback_type_kb())
    await state.set_state(FeedbackStates.choosing_type)


@router.callback_query(FeedbackStates.choosing_type, FeedbackCB.filter(F.action == "type"))
async def handle_feedback_type(
    callback: CallbackQuery,
    callback_data: FeedbackCB,
    state: FSMContext,
) -> None:
    """Обработать выбор типа обратной связи."""
    feedback_type = callback_data.value
    type_name, type_hint = FEEDBACK_TYPES.get(feedback_type, ("💬 Отзыв", ""))

    await state.update_data(feedback_type=feedback_type, type_name=type_name)

    prompts = {
        "feedback": (
            "💬 <b>Ваш отзыв</b>\n\n"
            "Расскажите о вашем опыте использования бота.\n"
            "Что нравится? Что хотели бы улучшить?\n\n"
            "📏 Минимум 20 символов."
        ),
        "bug": (
            "🐛 <b>Баг-репорт</b>\n\n"
            "Опишите ошибку максимально подробно:\n"
            "— Что вы делали когда возникла ошибка?\n"
            "— Что ожидали увидеть?\n"
            "— Что произошло вместо этого?\n\n"
            "Пример:\n"
            "<i>«Нажал кнопку Создать кампанию → ввёл текст → "
            "нажал Запустить → бот ничего не ответил»</i>\n\n"
            "📏 Минимум 30 символов."
        ),
        "idea": (
            "💡 <b>Ваша идея</b>\n\n"
            "Опишите какую функцию или улучшение вы хотели бы видеть.\n"
            "Чем подробнее — тем лучше!\n\n"
            "📏 Минимум 20 символов."
        ),
    }

    text = prompts.get(feedback_type, prompts["feedback"])

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=FeedbackCB(action="cancel"))
    builder.adjust(1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await state.set_state(FeedbackStates.waiting_text)


@router.message(FeedbackStates.waiting_text)
async def handle_feedback_text(message: Message, state: FSMContext) -> None:
    """Обработать введённый текст обратной связи."""
    data = await state.get_data()
    feedback_type = data.get("feedback_type", "feedback")
    min_len = 30 if feedback_type == "bug" else 20

    text = message.text.strip() if message.text else ""

    if len(text) < min_len:
        await message.answer(
            f"❌ Слишком коротко (минимум {min_len} символов).\n\nНапишите подробнее:"
        )
        return

    if len(text) > 2000:
        await message.answer("❌ Слишком длинно (максимум 2000 символов).\n\nСократите текст:")
        return

    await state.update_data(feedback_text=text)

    type_name = data.get("type_name", "💬 Отзыв")
    preview = text[:300] + ("..." if len(text) > 300 else "")

    confirm_text = f"📋 <b>Предпросмотр</b>\n\nТип: <b>{type_name}</b>\n\n{preview}\n\nОтправить?"

    await message.answer(confirm_text, reply_markup=get_feedback_confirm_kb())
    await state.set_state(FeedbackStates.waiting_confirm)


@router.callback_query(FeedbackStates.waiting_confirm, FeedbackCB.filter(F.action == "confirm"))
async def handle_feedback_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Отправить обратную связь администраторам."""
    data = await state.get_data()
    feedback_type = data.get("feedback_type", "feedback")
    feedback_text = data.get("feedback_text", "")
    type_name = data.get("type_name", "💬 Отзыв")

    # Формируем сообщение для админов
    user = callback.from_user
    username = f"@{user.username}" if user.username else f"ID:{user.id}"
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

    admin_message = (
        f"📨 <b>Новое обращение</b>\n\n"
        f"Тип: <b>{type_name}</b>\n"
        f"От: {username} (ID: <code>{user.id}</code>)\n"
        f"Имя: {user.first_name or '—'}\n"
        f"Время: {timestamp}\n\n"
        f"<b>Сообщение:</b>\n"
        f"{feedback_text}"
    )

    # Отправляем всем админам
    sent_count = 0
    bot = callback.bot
    if bot is None:
        logger.error("Bot instance is None in feedback handler")
        await callback.answer("Ошибка отправки. Попробуйте позже.", show_alert=True)
        return

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode="HTML",
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send feedback to admin {admin_id}: {e}")

    await state.clear()

    if sent_count > 0:
        success_text = (
            "✅ <b>Спасибо за обратную связь!</b>\n\n"
            "Ваше сообщение получено и будет рассмотрено.\n"
            "Если вы сообщили об ошибке — мы постараемся исправить её в ближайшем обновлении."
        )
    else:
        success_text = (
            "⚠️ Не удалось доставить сообщение.\nПопробуйте позже или напишите в поддержку напрямую."
        )

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        _ = await user_repo.get_by_telegram_id(callback.from_user.id)

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1)

    await safe_callback_edit(callback, success_text, reply_markup=builder.as_markup())
    logger.info(
        f"Feedback sent: type={feedback_type}, "
        f"user={callback.from_user.id}, "
        f"sent_to={sent_count} admins"
    )


@router.callback_query(FeedbackStates.waiting_confirm, FeedbackCB.filter(F.action == "edit"))
async def handle_feedback_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к редактированию текста."""
    data = await state.get_data()
    feedback_type = data.get("feedback_type", "feedback")

    prompts = {
        "feedback": "💬 Введите новый текст отзыва:",
        "bug": "🐛 Опишите ошибку заново:",
        "idea": "💡 Опишите идею заново:",
    }

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=FeedbackCB(action="cancel"))
    builder.adjust(1)

    await safe_callback_edit(callback, prompts.get(feedback_type, "Введите текст:"), reply_markup=builder.as_markup()
    )
    await state.set_state(FeedbackStates.waiting_text)


@router.callback_query(FeedbackCB.filter(F.action == "cancel"))
async def handle_feedback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить отправку обратной связи."""
    await state.clear()

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        credits = user.credits if user else 0
        user_id = user.id if user else None

    await safe_callback_edit(callback, "❌ Отменено.", reply_markup=get_main_menu(credits, user_id))
