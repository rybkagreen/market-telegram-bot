"""
Клавиатуры для пополнения баланса (топап).
S-09: Quick amounts + confirm keyboard.
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.constants.payments import QUICK_TOPUP_AMOUNTS


def kb_topup_amounts() -> InlineKeyboardMarkup:
    """
    Быстрый выбор суммы пополнения.

    Returns:
        InlineKeyboardMarkup с кнопками [500 ₽] [1 000 ₽] [2 000 ₽] [5 000 ₽] [10 000 ₽] [20 000 ₽]
        + [Ввести сумму вручную] + [Отмена]
    """
    builder = InlineKeyboardBuilder()

    # Кнопки быстрых сумм (3 в ряд)
    for amount in QUICK_TOPUP_AMOUNTS:
        # Форматируем с пробелами: 1 000, 2 000, etc.
        formatted = f"{amount:,}".replace(",", " ")
        builder.button(
            text=f"{formatted} ₽",
            callback_data=f"topup:amount:{amount}",
        )

    # Кнопка ввода вручную
    builder.button(
        text="✏️ Ввести сумму вручную",
        callback_data="topup:manual",
    )

    # Кнопка отмены
    builder.button(
        text="❌ Отмена",
        callback_data="topup:cancel",
    )

    # 3 кнопки в ряд для сумм, потом отдельные строки
    builder.adjust(3, 3, 1, 1)

    return builder.as_markup()


def kb_topup_confirm(gross_amount: int) -> InlineKeyboardMarkup:
    """
    Подтверждение перед оплатой.

    Args:
        gross_amount: Сумма к оплате (gross).

    Returns:
        InlineKeyboardMarkup с кнопками [✅ Оплатить {gross} ₽] [❌ Отмена]
    """
    builder = InlineKeyboardBuilder()

    formatted = f"{gross_amount:,}".replace(",", " ")

    builder.button(
        text=f"✅ Оплатить {formatted} ₽",
        callback_data="topup:confirm",
    )

    builder.button(
        text="❌ Отмена",
        callback_data="topup:cancel",
    )

    builder.adjust(1)

    return builder.as_markup()
