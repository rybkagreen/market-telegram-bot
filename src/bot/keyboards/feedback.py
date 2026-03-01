"""
Клавиатуры для обратной связи.
"""
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import MainMenuCB


class FeedbackCB(CallbackData, prefix="feedback"):
    """CallbackData для обратной связи."""
    action: str
    value: str = ""


def get_feedback_type_kb() -> InlineKeyboardMarkup:
    """Выбор типа обратной связи."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💬 Оставить отзыв",
        callback_data=FeedbackCB(action="type", value="feedback")
    )
    builder.button(
        text="🐛 Сообщить об ошибке",
        callback_data=FeedbackCB(action="type", value="bug")
    )
    builder.button(
        text="💡 Предложить идею",
        callback_data=FeedbackCB(action="type", value="idea")
    )
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu")
    )
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def get_feedback_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение отправки."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Отправить",
        callback_data=FeedbackCB(action="confirm")
    )
    builder.button(
        text="✏️ Изменить",
        callback_data=FeedbackCB(action="edit")
    )
    builder.button(
        text="❌ Отмена",
        callback_data=FeedbackCB(action="cancel")
    )
    builder.adjust(2, 1)
    return builder.as_markup()
