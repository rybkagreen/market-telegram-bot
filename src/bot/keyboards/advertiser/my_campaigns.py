"""My campaigns keyboard."""


from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def my_campaigns_kb(campaigns: list) -> InlineKeyboardMarkup:
    """Список моих кампаний."""
    builder = InlineKeyboardBuilder()
    for camp in campaigns[:10]:
        builder.row(InlineKeyboardButton(text=f"Кампания #{camp['id']}", callback_data=f"camp:detail:{camp['id']}"))
    builder.row(InlineKeyboardButton(text="Создать", callback_data="main:create_campaign"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="main:adv_menu"))
    return builder.as_markup()
