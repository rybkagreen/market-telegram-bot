"""
Клавиатуры для биллинга: кредиты, CryptoBot, Telegram Stars.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import MainMenuCB
from src.constants.payments import CREDIT_PACKAGES, CURRENCIES


class BillingCB(CallbackData, prefix="billing"):
    """CallbackData для биллинга."""

    action: str
    value: str = ""


def get_topup_methods_kb() -> InlineKeyboardMarkup:
    """Выбор метода пополнения."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💎 Криптовалюта (CryptoBot)",
        callback_data=BillingCB(action="topup_crypto"),
    )
    builder.button(
        text="⭐ Telegram Stars",
        callback_data=BillingCB(action="topup_stars"),
    )
    builder.button(
        text="📋 История транзакций",
        callback_data=BillingCB(action="history", value="1"),
    )
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu"),
    )
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def get_packages_kb(method: str) -> InlineKeyboardMarkup:
    """
    Выбор пакета кредитов.

    Args:
        method: "crypto" или "stars"
    """
    builder = InlineKeyboardBuilder()
    for label, _credits, bonus, value in CREDIT_PACKAGES:
        bonus_text = f" +{bonus} бонус" if bonus > 0 else ""
        builder.button(
            text=f"{label}{bonus_text}",
            callback_data=BillingCB(action=f"pkg_{method}", value=value),
        )
    builder.button(
        text="🔙 Назад",
        callback_data=BillingCB(action="topup_menu"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_currency_kb(credits: int) -> InlineKeyboardMarkup:
    """
    Выбор криптовалюты для конкретного пакета.

    Args:
        credits: Количество кредитов в пакете (для отображения суммы в валюте).
    """
    builder = InlineKeyboardBuilder()
    for currency in CURRENCIES:
        builder.button(
            text=currency,
            callback_data=BillingCB(action="pay_crypto", value=f"{credits}_{currency}"),
        )
    builder.button(
        text="🔙 Назад",
        callback_data=BillingCB(action="topup_crypto"),
    )
    builder.adjust(3, 2, 1)
    return builder.as_markup()


def get_plans_kb() -> InlineKeyboardMarkup:
    """
    Задача 7.1: Тарифные планы с обновлёнными описаниями.
    """
    builder = InlineKeyboardBuilder()

    # Задача 7.1: Обновлённые тексты тарифов
    plans = [
        (
            "🆓 FREE — 0 кр/мес\n• Кампании: недоступны\n• AI: недоступен",
            "free",
        ),
        (
            "🚀 STARTER — 299 кр/мес\n"
            "• 5 кампаний/мес\n"
            "• 50 каналов/кампанию\n"
            "• AI: базовая генерация текстов",
            "starter",
        ),
        (
            "💎 PRO — 999 кр/мес\n"
            "• 20 кампаний/мес\n"
            "• 200 каналов/кампанию\n"
            "• AI: расширенная генерация ✨\n"
            "• 5 AI-генераций включено",
            "pro",
        ),
        (
            "🏢 BUSINESS — 2 999 кр/мес\n"
            "• 100 кампаний/мес\n"
            "• 1 000 каналов/кампанию\n"
            "• AI: расширенная генерация ✨\n"
            "• 20 AI-генераций включено\n"
            "• Приоритетная поддержка",
            "business",
        ),
    ]

    for label, value in plans:
        builder.button(text=label, callback_data=BillingCB(action="plan", value=value))

    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1)

    return builder.as_markup()


def get_amount_kb() -> InlineKeyboardMarkup:
    """Быстрый переход к пополнению (для обратной совместимости)."""
    return get_topup_methods_kb()


def get_payment_methods_kb(payment_url: str, invoice_id: str) -> InlineKeyboardMarkup:
    """Кнопка оплаты через CryptoBot."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить", url=payment_url)
    builder.button(
        text="🔄 Проверить",
        callback_data=BillingCB(action="check_invoice", value=invoice_id),
    )
    builder.adjust(2)
    return builder.as_markup()
