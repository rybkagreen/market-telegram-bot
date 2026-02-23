"""
Клавиатура главного меню бота.
"""

from decimal import Decimal

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MainMenuCB(CallbackData, prefix="main"):
    """CallbackData для главного меню."""

    action: str


def get_main_menu(balance: Decimal) -> InlineKeyboardMarkup:
    """
    Построить клавиатуру главного меню.

    Args:
        balance: Баланс пользователя.

    Returns:
        InlineKeyboardMarkup с кнопками меню.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚀 Создать кампанию",
        callback_data=MainMenuCB(action="create_campaign")
    )
    builder.button(
        text="📊 Мои кампании",
        callback_data=MainMenuCB(action="my_campaigns")
    )
    builder.button(
        text="👤 Кабинет",
        callback_data=MainMenuCB(action="cabinet")
    )
    builder.button(
        text=f"💳 {balance}₽",
        callback_data=MainMenuCB(action="balance")
    )
    builder.button(
        text="🤖 ИИ-генерация",
        callback_data=MainMenuCB(action="ai_gen")
    )
    builder.button(
        text="📋 Шаблоны",
        callback_data=MainMenuCB(action="templates")
    )
    builder.button(
        text="ℹ️ Помощь",
        callback_data=MainMenuCB(action="help")
    )

    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()
