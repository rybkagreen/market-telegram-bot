"""Advertiser menu keyboard."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def adv_menu_kb() -> InlineKeyboardMarkup:
    """Меню рекламодателя. БЕЗ B2B."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика и аналитика", callback_data="main:analytics"))
    builder.row(InlineKeyboardButton(text="📣 Создать кампанию", callback_data="main:create_campaign"))
    builder.row(InlineKeyboardButton(text="📋 Мои кампании", callback_data="main:my_campaigns"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main:main_menu"))
    return builder.as_markup()
