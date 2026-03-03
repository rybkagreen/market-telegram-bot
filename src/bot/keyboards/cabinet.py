"""Клавиатуры личного кабинета."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.billing import BillingCB
from src.bot.keyboards.main_menu import MainMenuCB


class CabinetCB(CallbackData, prefix="cabinet"):
    """CallbackData для кабинета."""

    action: str
    value: str = ""


def get_cabinet_kb(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """
    Меню личного кабинета с переключателем уведомлений.

    Args:
        notifications_enabled: Текущее состояние уведомлений пользователя.
    """
    builder = InlineKeyboardBuilder()

    # Переключатель уведомлений — показываем текущее состояние
    notif_text = "🔔 Уведомления: ВКЛ" if notifications_enabled else "🔕 Уведомления: ВЫКЛ"
    builder.button(
        text=notif_text,
        callback_data=CabinetCB(action="toggle_notifications"),
    )

    # Существующие кнопки кабинета
    builder.button(text="💳 Пополнить", callback_data=BillingCB(action="topup", value="0"))
    builder.button(
        text="📊 История транзакций", callback_data=BillingCB(action="history", value="0")
    )
    builder.button(text="👥 Рефералы", callback_data=BillingCB(action="referral", value="0"))
    builder.button(text="🔄 Сменить тариф", callback_data=BillingCB(action="plans", value="0"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_notifications_prompt_kb() -> InlineKeyboardMarkup:
    """
    Запрос на включение уведомлений при запуске кампании.
    Показывается только если уведомления выключены.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔔 Да, включить уведомления",
        callback_data=CabinetCB(action="enable_notif_and_launch"),
    )
    builder.button(
        text="▶️ Запустить без уведомлений",
        callback_data=CabinetCB(action="launch_without_notif"),
    )
    builder.adjust(1)
    return builder.as_markup()
