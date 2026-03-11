"""
Клавиатуры для AI-аналитики кампаний.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.shared.main_menu import MainMenuCB


class CampaignAICB(CallbackData, prefix="campaign_ai"):
    """CallbackData для AI-аналитики кампаний."""

    action: str
    campaign_id: str = ""


def get_campaign_list_kb(campaigns: list[dict]) -> InlineKeyboardMarkup:
    """
    Список кампаний для выбора AI-аналитики.

    Args:
        campaigns: Список кампаний с полями id, title, status.
    """
    builder = InlineKeyboardBuilder()

    for camp in campaigns[:10]:  # Максимум 10 кампаний
        status_emoji = {
            "done": "✅",
            "error": "❌",
            "cancelled": "🚫",
        }.get(camp.get("status", ""), "📝")

        title = camp.get("title", "Без названия")[:30]
        builder.button(
            text=f"{status_emoji} {title}",
            callback_data=CampaignAICB(action="analyze", campaign_id=str(camp["id"])),
        )

    builder.button(
        text="🔙 В меню аналитики",
        callback_data=MainMenuCB(action="analytics"),
    )
    builder.adjust(1)

    return builder.as_markup()


def get_ai_analysis_result_kb(campaign_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура после показа AI-анализа.

    Args:
        campaign_id: ID проанализированной кампании.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔄 Повторить анализ",
        callback_data=CampaignAICB(action="analyze", campaign_id=str(campaign_id)),
    )
    builder.button(
        text="📋 Другие кампании",
        callback_data=CampaignAICB(action="list"),
    )
    builder.button(
        text="🔙 В меню аналитики",
        callback_data=MainMenuCB(action="analytics"),
    )
    builder.adjust(1, 1)

    return builder.as_markup()


def get_ai_premium_lock_kb() -> InlineKeyboardMarkup:
    """Клавиатура для блокировки AI-аналитики на FREE/STARTER."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="💳 Изменить тариф",
        callback_data=MainMenuCB(action="balance"),
    )
    builder.button(
        text="🔙 В меню аналитики",
        callback_data=MainMenuCB(action="analytics"),
    )
    builder.adjust(1)

    return builder.as_markup()
