from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from decimal import Decimal


class MainMenuCB(CallbackData, prefix="main_menu"):
    """CallbackData для главного меню."""
    action: str


class BillingCB(CallbackData, prefix="billing"):
    """CallbackData для биллинга."""
    action: str
    amount: int | None = None


class PlanCB(CallbackData, prefix="plan"):
    """CallbackData для тарифов."""
    plan_name: str


def get_main_menu(balance: Decimal = Decimal("0.00")) -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🚀 Создать кампанию", callback_data=MainMenuCB(action="campaign_create").pack()),
        InlineKeyboardButton(text="📊 Мои кампании", callback_data=MainMenuCB(action="campaigns_list").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="👤 Кабинет", callback_data=MainMenuCB(action="cabinet").pack()),
        InlineKeyboardButton(text=f"💳 {balance:.2f}₽", callback_data=MainMenuCB(action="balance").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 ИИ-генерация", callback_data=MainMenuCB(action="ai_generate").pack()),
        InlineKeyboardButton(text="📋 Шаблоны", callback_data=MainMenuCB(action="templates").pack()),
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data=MainMenuCB(action="help").pack()),
    )
    
    return builder.as_markup()


def get_amount_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора суммы пополнения."""
    builder = InlineKeyboardBuilder()
    
    amounts = [100, 500, 1000]
    
    for amount in amounts:
        builder.button(
            text=f"{amount}₽",
            callback_data=BillingCB(action="select", amount=amount).pack()
        )
    
    builder.button(
        text="Другая сумма",
        callback_data=BillingCB(action="custom", amount=None).pack()
    )
    
    builder.adjust(2, 2)
    
    return builder.as_markup()


def get_plans_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа."""
    plans = [
        ("FREE", "0₽/мес"),
        ("STARTER", "299₽/мес"),
        ("PRO", "999₽/мес"),
        ("BUSINESS", "2999₽/мес"),
    ]
    
    builder = InlineKeyboardBuilder()
    
    for plan_name, price in plans:
        builder.button(
            text=f"{plan_name} — {price}",
            callback_data=PlanCB(plan_name=plan_name.lower()).pack()
        )
    
    builder.adjust(1)
    
    return builder.as_markup()
