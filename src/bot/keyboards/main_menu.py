from decimal import Decimal
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .billing import MainMenuCB


def get_main_menu(balance: Decimal = Decimal("0.00")) -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🚀 Создать кампанию", callback_data=MainMenuCB(action="campaign_create").pack()),
        InlineKeyboardButton(text="📊 Мои кампании", callback_data=MainMenuCB(action="campaigns_list").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="👤 Кабинет", callback_data=MainMenuCB(action="cabinet").pack()),
        InlineKeyboardButton(text=f"💳 {balance:.2f}₽", callback_data=MainMenuCB(action="balance").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 ИИ-генерация", callback_data=MainMenuCB(action="ai_generate").pack()),
        InlineKeyboardButton(text="📋 Шаблоны", callback_data=MainMenuCB(action="templates").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data=MainMenuCB(action="help").pack()),
    )
    
    return builder.as_markup()
