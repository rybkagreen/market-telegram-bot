"""
Клавиатуры для выплат (payout).
"""

from decimal import Decimal

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.constants.payments import MIN_PAYOUT, QUICK_TOPUP_AMOUNTS


def kb_payout_amounts(earned_rub: Decimal) -> InlineKeyboardMarkup:
    """
    Выбор суммы выплаты.

    Args:
        earned_rub: Доступный баланс для вывода.

    Returns:
        InlineKeyboardMarkup с кнопками сумм + "Всё" + "Ввести сумму" + "Отмена"
    """
    builder = InlineKeyboardBuilder()

    # Кнопки быстрых сумм (адаптируем из QUICK_TOPUP_AMOUNTS)
    for amount in QUICK_TOPUP_AMOUNTS[:5]:  # Берём первые 5
        if Decimal(str(amount)) >= MIN_PAYOUT and Decimal(str(amount)) <= earned_rub:
            formatted = f"{amount:,}".replace(",", " ")
            builder.button(
                text=f"{formatted} ₽",
                callback_data=f"payout:amount:{amount}",
            )

    # Кнопка "Всё" (максимальная сумма)
    if earned_rub >= MIN_PAYOUT:
        builder.button(
            text="💰 Всё",
            callback_data="payout:amount:all",
        )

    # Кнопка ввода вручную
    builder.button(
        text="✏️ Ввести сумму",
        callback_data="payout:manual",
    )

    # Кнопка отмены
    builder.button(
        text="❌ Отмена",
        callback_data="payout:cancel",
    )

    builder.adjust(3, 3, 1, 1)

    return builder.as_markup()


def kb_payout_confirm(gross: Decimal, fee: Decimal, net: Decimal) -> InlineKeyboardMarkup:
    """
    Подтверждение выплаты с показом комиссии.

    Args:
        gross: Запрошенная сумма.
        fee: Комиссия платформы (1.5%).
        net: Сумма к перечислению.

    Returns:
        InlineKeyboardMarkup с кнопками [✅ Подтвердить] [❌ Отмена]
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Подтвердить выплату",
        callback_data="payout:confirm",
    )

    builder.button(
        text="❌ Отмена",
        callback_data="payout:cancel",
    )

    builder.adjust(1)

    return builder.as_markup()
