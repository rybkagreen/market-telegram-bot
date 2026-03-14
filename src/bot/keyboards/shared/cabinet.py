"""
Cabinet keyboard.
"""

from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def cabinet_kb(role: str, earned_rub: Decimal) -> InlineKeyboardMarkup:
    """
    Клавиатура кабинета.

    Условные кнопки:
    - Пополнить billing:topup_start если role in (advertiser, both)
    - Запросить вывод payout:request_start если role in (owner, both) AND earned_rub >= 1000
    """
    builder = InlineKeyboardBuilder()

    if role in ("advertiser", "both"):
        builder.row(InlineKeyboardButton(text="Пополнить", callback_data="billing:topup_start"))

    if role in ("owner", "both") and earned_rub >= Decimal("1000"):
        builder.row(
            InlineKeyboardButton(text="Запросить вывод", callback_data="payout:request_start")
        )

    builder.row(InlineKeyboardButton(text="Изменить тариф", callback_data="billing:plans"))
    builder.row(InlineKeyboardButton(text="Реферальная программа", callback_data="cabinet:referral"))
    builder.row(InlineKeyboardButton(text="Геймификация", callback_data="cabinet:gamification"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="main:main_menu"))

    return builder.as_markup()
