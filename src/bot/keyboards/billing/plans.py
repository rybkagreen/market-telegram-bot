"""Billing plans keyboard."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def plans_kb(current_plan: str) -> InlineKeyboardMarkup:
    """Выбор тарифа."""
    builder = InlineKeyboardBuilder()

    plans = [
        ("starter", "Starter"),
        ("pro", "Pro"),
        ("business", "Agency"),
    ]

    for plan_code, plan_name in plans:
        if plan_code != current_plan:
            builder.row(InlineKeyboardButton(text=f"{plan_name} план", callback_data=f"plan:buy:{plan_code}"))

    builder.row(InlineKeyboardButton(text="В кабинет", callback_data="main:cabinet"))
    return builder.as_markup()
