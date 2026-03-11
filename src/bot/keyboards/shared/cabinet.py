"""Клавиатуры личного кабинета."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.billing.billing import BillingCB
from src.bot.keyboards.shared.main_menu import MainMenuCB


class CabinetCB(CallbackData, prefix="cabinet"):
    """CallbackData для кабинета."""

    action: str
    value: str = ""


def get_cabinet_kb(
    notifications_enabled: bool,
    role: str = "advertiser",
    available_payout: int = 0,
) -> InlineKeyboardMarkup:
    """
    Меню личного кабинета с переключателем уведомлений.
    Задача 5.4: Расширенная клавиатура в зависимости от роли.

    Args:
        notifications_enabled: Текущее состояние уведомлений пользователя.
        role: Роль пользователя (advertiser, owner, both).
        available_payout: Сумма доступная к выводу (для владельца).
    """
    builder = InlineKeyboardBuilder()

    # Задача 5.4: Разные кнопки для рекламодателя и владельца
    if role in ("owner", "both") and available_payout >= 500:
        # Для владельца — кнопка вывода (только если >= 500 кр)
        builder.button(
            text=f"💸 Вывести {available_payout} кр",
            callback_data=MainMenuCB(action="payouts"),
        )

    # Задача 5.4: Кнопка пополнения для всех
    builder.button(
        text="💰 Пополнить баланс",
        callback_data=BillingCB(action="topup", value="0"),
    )

    # Задача 5.4: Кнопка смены тарифа (для рекламодателя)
    if role in ("advertiser", "both"):
        builder.button(
            text="📦 Сменить тариф",
            callback_data=BillingCB(action="plans", value="0"),
        )

    # Задача 5.4: Кнопки значков и рефералов
    builder.button(text="🏅 Мои значки", callback_data=CabinetCB(action="badges"))
    builder.button(
        text="👥 Реферальная программа",
        callback_data=BillingCB(action="referral", value="0"),
    )

    # Переключатель уведомлений — показываем текущее состояние
    notif_text = "🔔 Уведомления: ВКЛ" if notifications_enabled else "🔕 Уведомления: ВЫКЛ"
    builder.button(
        text=notif_text,
        callback_data=CabinetCB(action="toggle_notifications"),
    )

    # Кнопка возврата в меню
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))

    # Адаптивная раскладка
    if role in ("owner", "both") and available_payout >= 500:
        builder.adjust(1, 2, 2, 1)
    elif role in ("advertiser", "both"):
        builder.adjust(2, 2, 2, 1)
    else:
        builder.adjust(2, 2, 2, 1)

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
