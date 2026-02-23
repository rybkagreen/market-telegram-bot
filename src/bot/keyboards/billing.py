"""
Клавиатуры для биллинга и платежей.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class BillingCB(CallbackData, prefix="billing"):
    """CallbackData для биллинга."""

    action: str
    value: str = ""


def get_amount_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора суммы пополнения.

    Returns:
        InlineKeyboardMarkup с предустановленными суммами.
    """
    builder = InlineKeyboardBuilder()
    for amount in ["100", "500", "1000"]:
        builder.button(
            text=f"{amount}₽",
            callback_data=BillingCB(action="topup", value=amount)
        )
    builder.button(
        text="Другая сумма",
        callback_data=BillingCB(action="topup", value="custom")
    )
    builder.adjust(3, 1)
    return builder.as_markup()


def get_plans_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора тарифного плана.

    Returns:
        InlineKeyboardMarkup с тарифами.
    """
    plans = [
        ("🆓 FREE", "free"),
        ("🚀 STARTER 299₽/мес", "starter"),
        ("💎 PRO 999₽/мес", "pro"),
        ("🏢 BUSINESS 2999₽/мес", "business"),
    ]
    builder = InlineKeyboardBuilder()
    for label, value in plans:
        builder.button(
            text=label,
            callback_data=BillingCB(action="plan", value=value)
        )
    builder.adjust(1)
    return builder.as_markup()


def get_payment_methods_kb(payment_url: str) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой оплаты.

    Args:
        payment_url: Ссылка на платежную страницу.

    Returns:
        InlineKeyboardMarkup с кнопкой оплаты.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💳 Оплатить",
        url=payment_url
    )
    builder.button(
        text="🔄 Проверить статус",
        callback_data=BillingCB(action="check_payment", value="pending")
    )
    builder.adjust(2)
    return builder.as_markup()
