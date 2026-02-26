"""
Клавиатура главного меню бота.
"""

from decimal import Decimal

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config.settings import settings


class MainMenuCB(CallbackData, prefix="main"):
    """CallbackData для главного меню."""

    action: str


class ModelCB(CallbackData, prefix="model"):
    """CallbackData для выбора модели ИИ."""

    provider: str


def _is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом."""
    return user_id in settings.admin_ids


def get_main_menu(balance: Decimal, user_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Построить клавиатуру главного меню.

    Args:
        balance: Баланс пользователя.
        user_id: ID пользователя (опционально, для определения админа).

    Returns:
        InlineKeyboardMarkup с кнопками меню.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="🚀 Создать кампанию", callback_data=MainMenuCB(action="create_campaign"))
    builder.button(text="📊 Мои кампании", callback_data=MainMenuCB(action="my_campaigns"))
    builder.button(text="👤 Кабинет", callback_data=MainMenuCB(action="cabinet"))
    builder.button(text=f"💳 {balance}₽", callback_data=MainMenuCB(action="balance"))
    builder.button(text="🤖 ИИ-генерация", callback_data=MainMenuCB(action="ai_gen"))

    # Кнопка модели ИИ — разная для админов и пользователей
    if user_id and _is_admin(user_id):
        builder.button(text="🎛 Модель ИИ (админ)", callback_data=ModelCB(provider="select"))
    else:
        builder.button(text="ℹ️ Моя модель ИИ", callback_data=ModelCB(provider="select"))

    builder.button(text="📋 Шаблоны", callback_data=MainMenuCB(action="templates"))
    builder.button(text="ℹ️ Помощь", callback_data=MainMenuCB(action="help"))

    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()
