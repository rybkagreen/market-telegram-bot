"""Billing topup keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.constants.payments import QUICK_TOPUP_AMOUNTS


def topup_amounts_kb() -> InlineKeyboardMarkup:
    """Выбор суммы пополнения."""
    builder = InlineKeyboardBuilder()
    for amount in QUICK_TOPUP_AMOUNTS:
        builder.row(
            InlineKeyboardButton(text=f"{amount} ₽", callback_data=f"topup:amount:{amount}")
        )
    builder.row(InlineKeyboardButton(text="Ввести свою сумму", callback_data="topup:amount:custom"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="main:cabinet"))
    return builder.as_markup()


def topup_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение пополнения."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Перейти к оплате", callback_data="topup:pay"))
    builder.row(InlineKeyboardButton(text="Изменить сумму", callback_data="billing:topup_start"))
    return builder.as_markup()


def topup_payment_kb(url: str, pid: str) -> InlineKeyboardMarkup:
    """Клавиатура оплаты."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Оплатить", url=url))
    builder.row(
        InlineKeyboardButton(text="Я оплатил", callback_data=f"topup:check:{pid}"),
        InlineKeyboardButton(text="Отмена", callback_data=f"topup:cancel:{pid}"),
    )
    return builder.as_markup()


def topup_success_kb() -> InlineKeyboardMarkup:
    """Успешное пополнение."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Создать кампанию", callback_data="main:create_campaign"))
    builder.row(InlineKeyboardButton(text="В кабинет", callback_data="main:cabinet"))
    return builder.as_markup()
