"""Admin keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Админ меню."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Пользователи", callback_data="admin:users"))
    builder.row(InlineKeyboardButton(text="Платформа", callback_data="admin:platform"))
    builder.row(InlineKeyboardButton(text="Выплаты", callback_data="admin:payouts"))
    builder.row(InlineKeyboardButton(text="Споры", callback_data="admin:disputes"))
    return builder.as_markup()


def dispute_review_kb(did: int) -> InlineKeyboardMarkup:
    """Рассмотрение спора."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Вина владельца", callback_data=f"admin:dispute:resolve:owner_fault:{did}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="Частичный", callback_data=f"admin:dispute:resolve:partial:{did}")
    )
    builder.row(
        InlineKeyboardButton(
            text="Необоснована", callback_data=f"admin:dispute:resolve:advertiser_fault:{did}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Техошибка", callback_data=f"admin:dispute:resolve:technical:{did}"
        )
    )
    return builder.as_markup()


def disputes_list_kb(disputes: list) -> InlineKeyboardMarkup:
    """Список споров."""
    builder = InlineKeyboardBuilder()
    for disp in disputes[:10]:
        builder.row(
            InlineKeyboardButton(
                text=f"Спор #{disp['id']}", callback_data=f"admin:dispute:{disp['id']}"
            )
        )
    return builder.as_markup()
