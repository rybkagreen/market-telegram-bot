"""Клавиатуры для размещения (placement)."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_placement_list_kb(placements: list) -> InlineKeyboardMarkup:
    """Список заявок на размещение."""
    builder = InlineKeyboardBuilder()

    for p in placements[:10]:
        status_emoji = {"published": "✅", "pending": "⏳", "cancelled": "❌"}.get(
            p.get("status", ""), "📝"
        )
        title = p.get("channel_name", "Канал")[:30]
        builder.button(text=f"{status_emoji} {title}", callback_data=f"placement:view:{p['id']}")

    builder.button(text="◀️ Назад", callback_data="main:main_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_placement_card_kb(placement_id: int, status: str) -> InlineKeyboardMarkup:
    """Карточка заявки (кнопки зависят от статуса)."""
    builder = InlineKeyboardBuilder()

    if status == "pending_payment":
        builder.button(text="💳 Оплатить", callback_data=f"placement:pay:{placement_id}")
        builder.button(text="❌ Отменить", callback_data=f"placement:cancel:{placement_id}")
    elif status == "counter_offer":
        builder.button(text="✅ Принять", callback_data=f"placement:accept_counter:{placement_id}")
        builder.button(text="❌ Отклонить", callback_data=f"placement:cancel:{placement_id}")
    else:
        builder.button(text="◀️ Назад", callback_data="placement:list")

    builder.adjust(1)
    return builder.as_markup()


def get_cancel_confirm_kb(placement_id: int) -> InlineKeyboardMarkup:
    """Подтверждение отмены заявки."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, отменить", callback_data=f"placement:cancel_confirm:{placement_id}")
    builder.button(text="◀️ Нет, назад", callback_data=f"placement:view:{placement_id}")
    builder.adjust(1)
    return builder.as_markup()
