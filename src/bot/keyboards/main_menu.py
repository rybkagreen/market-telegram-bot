from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu(balance: float = 0.0) -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🚀 Создать кампанию", callback_data="campaign_create"),
        InlineKeyboardButton(text="📊 Мои кампании", callback_data="campaigns_list"),
    )
    builder.row(
        InlineKeyboardButton(text="👤 Кабинет", callback_data="cabinet"),
        InlineKeyboardButton(text=f"💳 {balance:.2f}₽", callback_data="balance"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 ИИ-генерация", callback_data="ai_generate"),
        InlineKeyboardButton(text="📋 Шаблоны", callback_data="templates"),
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
    )
    
    return builder.as_markup()
