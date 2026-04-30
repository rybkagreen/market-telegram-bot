"""Owner menu keyboard."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.utils.portal_deeplink import portal_webapp


def own_menu_kb(pending_count: int = 0) -> InlineKeyboardMarkup:
    """Меню владельца."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="main:owner_analytics"))
    builder.row(InlineKeyboardButton(text="📺 Мои каналы", callback_data="main:my_channels"))

    badge = f" 🔴{pending_count}" if pending_count > 0 else ""
    builder.row(InlineKeyboardButton(text=f"📋 Заявки{badge}", callback_data="main:my_requests"))

    builder.row(
        InlineKeyboardButton(text="💸 Выплаты", web_app=portal_webapp("/own/payouts/request"))
    )
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main:main_menu"))
    return builder.as_markup()
