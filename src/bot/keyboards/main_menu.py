"""
Клавиатура главного меню бота.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config.settings import settings


class MainMenuCB(CallbackData, prefix="main"):
    """CallbackData для главного меню."""

    action: str
    value: str = ""


class ModelCB(CallbackData, prefix="model"):
    """CallbackData для выбора модели ИИ."""

    provider: str


def _is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом."""
    return user_id in settings.admin_ids


def get_main_menu(credits: int, user_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Главное меню бота.

    6 кнопок: Кампания, Мои кампании, Аналитика, Шаблоны, Кабинет, Баланс.
    Для админов: дополнительная кнопка Админ-панель.
    Для всех: кнопка Обратная связь.

    Args:
        credits: Баланс пользователя в кредитах.
        user_id: ID пользователя (опционально, для определения админа).

    Returns:
        InlineKeyboardMarkup с кнопками меню.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="🚀 Создать кампанию", callback_data=MainMenuCB(action="create_campaign"))
    builder.button(text="📋 Мои кампании", callback_data=MainMenuCB(action="my_campaigns"))
    builder.button(text="📊 Аналитика", callback_data=MainMenuCB(action="analytics"))
    builder.button(text="📄 Шаблоны", callback_data=MainMenuCB(action="templates"))
    builder.button(text="👤 Кабинет", callback_data=MainMenuCB(action="cabinet"))
    builder.button(text=f"💳 {credits:,} кр", callback_data=MainMenuCB(action="balance"))

    # Кнопка для всех: обратная связь
    builder.button(text="💬 Обратная связь", callback_data=MainMenuCB(action="feedback"))

    # Только для админов: панель управления
    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ-панель", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 2, 1, 1)
    else:
        builder.adjust(2, 2, 2, 1)

    return builder.as_markup()
