"""Payout keyboards."""

from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def payout_amounts_kb(earned: Decimal) -> InlineKeyboardMarkup:
    """Выбор суммы вывода."""
    builder = InlineKeyboardBuilder()
    amounts = [1000, 3000, 5000, 10000]
    for amount in amounts:
        if amount <= earned:
            builder.row(InlineKeyboardButton(text=f"{amount} ₽", callback_data=f"payout:amount:{amount}"))
    if earned >= 1000:
        builder.row(InlineKeyboardButton(text=f"Всё ({earned:.0f} ₽)", callback_data="payout:amount:all"))
    builder.row(InlineKeyboardButton(text="Ввести сумму", callback_data="payout:amount:custom"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="main:payouts"))
    return builder.as_markup()


def payout_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение вывода."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Подтвердить (ввод реквизитов)", callback_data="payout:confirm"))
    builder.row(InlineKeyboardButton(text="Изменить сумму", callback_data="payout:request_start"))
    return builder.as_markup()
