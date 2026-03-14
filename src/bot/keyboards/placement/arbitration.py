"""Клавиатуры для арбитража (arbitration)."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_arbitration_list_kb(requests: list) -> InlineKeyboardMarkup:
    """Список заявок на арбитраж."""
    builder = InlineKeyboardBuilder()

    for r in requests[:10]:
        status_emoji = {"pending": "⏳", "accepted": "✅", "rejected": "❌"}.get(
            r.get("status", ""), "📝"
        )
        title = r.get("advertiser_name", "Рекламодатель")[:30]
        builder.button(text=f"{status_emoji} {title}", callback_data=f"arbitration:view:{r['id']}")

    builder.button(text="◀️ Назад", callback_data="main:main_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_arbitration_card_kb(placement_id: int) -> InlineKeyboardMarkup:
    """Карточка заявки на арбитраж."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"arbitration:accept:{placement_id}")
    builder.button(text="❌ Отклонить", callback_data=f"arbitration:reject:{placement_id}")
    builder.button(text="💱 Контр-предложение", callback_data=f"arbitration:counter:{placement_id}")
    builder.button(text="◀️ Назад", callback_data="arbitration:list")
    builder.adjust(1)
    return builder.as_markup()


def get_reject_reason_kb(placement_id: int) -> InlineKeyboardMarkup:
    """Выбор причины отклонения."""
    builder = InlineKeyboardBuilder()
    reasons = [
        "Не подходит тематика",
        "Низкое качество контента",
        "Завышенная цена",
        "Неподходящее время",
        "Другое",
    ]
    for reason in reasons:
        builder.button(
            text=reason, callback_data=f"arbitration:reject_confirm:{placement_id}:{reason}"
        )
    builder.button(text="◀️ Назад", callback_data=f"arbitration:view:{placement_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_counter_offer_kb(placement_id: int) -> InlineKeyboardMarkup:
    """Контр-предложение."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data=f"arbitration:counter_confirm:{placement_id}")
    builder.button(text="◀️ Назад", callback_data=f"arbitration:view:{placement_id}")
    builder.adjust(1)
    return builder.as_markup()
