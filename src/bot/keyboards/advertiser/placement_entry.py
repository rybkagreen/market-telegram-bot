"""
Клавиатуры для точки входа placement флоу.
S-PLACEMENT-ENTRY: развилка broadcast/placement, выбор категории.
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.advertiser.campaign_ai import CAMPAIGN_CATEGORIES
from src.bot.keyboards.shared.main_menu import MainMenuCB


def kb_type_fork() -> InlineKeyboardMarkup:
    """
    Развилка — выбор типа кампании.

    Кнопки:
    - 📌 Разместить в конкретном канале → placement_entry:type:placement
    - 📢 Broadcast — рассылка по каналам → placement_entry:type:broadcast
    - 🔙 Главное меню → main:main_menu
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📌 Разместить в конкретном канале",
        callback_data="placement_entry:type:placement",
    )
    builder.button(
        text="📢 Broadcast — рассылка по каналам",
        callback_data="placement_entry:type:broadcast",
    )
    builder.button(
        text="🔙 Главное меню",
        callback_data=MainMenuCB(action="main_menu").pack(),
    )

    builder.adjust(1, 1, 1)

    return builder.as_markup()


def kb_placement_categories() -> InlineKeyboardMarkup:
    """
    Выбор категории для placement флоу.

    Использует CAMPAIGN_CATEGORIES из campaign_ai.py (20 категорий).
    Callback: placement_entry:cat:{key}
    """
    builder = InlineKeyboardBuilder()

    for cat_key, cat_name in CAMPAIGN_CATEGORIES.items():
        builder.button(
            text=cat_name,
            callback_data=f"placement_entry:cat:{cat_key}",
        )

    builder.button(
        text="🔙 Назад к выбору типа",
        callback_data="placement_entry:back:fork",
    )

    builder.adjust(2, 2, 2, 2, 2, 1)

    return builder.as_markup()


def kb_placement_subcategories(subcategories: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """
    Выбор подкатегории (если есть для выбранной категории).

    Args:
        subcategories: Список кортежей (key, display_name).

    Callback: placement_entry:subcat:{key}
    """
    builder = InlineKeyboardBuilder()

    for subcat_key, subcat_name in subcategories:
        builder.button(
            text=subcat_name,
            callback_data=f"placement_entry:subcat:{subcat_key}",
        )

    builder.button(
        text="Пропустить →",
        callback_data="placement_entry:subcat:skip",
    )
    builder.button(
        text="🔙 Назад к категории",
        callback_data="placement_entry:back:category",
    )

    builder.adjust(2, 1, 1)

    return builder.as_markup()
