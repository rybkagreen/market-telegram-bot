"""My campaigns keyboard."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Status icon mapping for keyboard buttons
_STATUS_ICONS: dict[str, str] = {
    "pending_owner": "⏳",
    "counter_offer": "💬",
    "pending_payment": "💳",
    "escrow": "🔒",
    "published": "✅",
    "failed": "❌",
    "failed_permissions": "🚫",
    "refunded": "💰",
    "cancelled": "🚫",
}


def my_campaigns_kb(campaigns: list[dict]) -> InlineKeyboardMarkup:
    """Список моих кампаний с индикаторами статуса.

    Args:
        campaigns: List of dicts with at least {'id': int, 'status': str}.
    """
    builder = InlineKeyboardBuilder()
    for camp in campaigns[:15]:
        camp_id = camp["id"]
        camp_status = camp.get("status", "")
        icon = _STATUS_ICONS.get(camp_status, "")
        button_text = f"{icon} Кампания #{camp_id}" if icon else f"Кампания #{camp_id}"
        builder.row(InlineKeyboardButton(text=button_text, callback_data=f"camp:detail:{camp_id}"))
    builder.row(InlineKeyboardButton(text="Создать", callback_data="main:create_campaign"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="main:adv_menu"))
    return builder.as_markup()
