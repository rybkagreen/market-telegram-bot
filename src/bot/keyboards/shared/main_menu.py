"""Shared main menu keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню — без переключателя ролей."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 Кабинет", callback_data="main:cabinet"))
    builder.row(
        InlineKeyboardButton(text="📣 Рекламодатель", callback_data="main:adv_menu"),
        InlineKeyboardButton(text="📺 Владелец", callback_data="main:own_menu"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 Помощь", callback_data="main:help"),
        InlineKeyboardButton(text="✉️ Обратная связь", callback_data="main:feedback"),
    )
    return builder.as_markup()


def tos_kb() -> InlineKeyboardMarkup:
    """Клавиатура принятия условий использования."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Принять условия", callback_data="terms:accept"))
    builder.row(InlineKeyboardButton(text="❌ Отклонить", callback_data="terms:decline"))
    return builder.as_markup()
