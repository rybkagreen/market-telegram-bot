"""Common keyboards (back, cancel, confirm)."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def back_kb(cb: str) -> InlineKeyboardMarkup:
    """Кнопка Назад."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Назад", callback_data=cb))
    return builder.as_markup()


def cancel_kb(cb: str) -> InlineKeyboardMarkup:
    """Кнопка Отмена."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отмена", callback_data=cb))
    return builder.as_markup()


def confirm_cancel_kb(ok_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    """Кнопки Подтвердить и Отмена."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Подтвердить", callback_data=ok_cb))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data=cancel_cb))
    return builder.as_markup()
