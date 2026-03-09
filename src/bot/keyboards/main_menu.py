"""
Клавиатура главного меню бота.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config.settings import settings


class MainMenuCB(CallbackData, prefix="main"):
    """CallbackData для главного меню."""

    action: str
    value: str = ""


class ModelCB(CallbackData, prefix="model"):
    """CallbackData для выбора модели ИИ."""

    provider: str


class OnboardingCB(CallbackData, prefix="onboard"):
    """Выбор роли при первом входе."""

    role: str  # "advertiser" | "owner" | "both"


def _is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом."""
    return user_id in settings.admin_ids


# ─────────────────────────────────────────────
# Роль-зависимые меню (Спринт 0-4 редизайн)
# ─────────────────────────────────────────────


def get_onboarding_kb() -> InlineKeyboardMarkup:
    """
    Экран выбора роли для нового пользователя.
    Показывается когда нет ни каналов, ни кампаний.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📣 Размещать рекламу в каналах",
        callback_data=OnboardingCB(role="advertiser"),
    )
    builder.button(
        text="📺 Зарабатывать на своём канале",
        callback_data=OnboardingCB(role="owner"),
    )
    builder.button(
        text="📊 Как устроена платформа",
        callback_data=MainMenuCB(action="platform_stats"),
    )
    builder.adjust(1)
    return builder.as_markup()


def get_advertiser_menu_kb(
    credits: int,
    user_id: int | None = None,
    active_campaigns: int = 0,
) -> InlineKeyboardMarkup:
    """
    Меню рекламодателя.
    Показывается когда у пользователя есть кампании, но нет своих каналов.

    Args:
        credits: Баланс пользователя.
        user_id: Telegram ID для проверки прав администратора.
        active_campaigns: Количество активных кампаний.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="📣 Создать кампанию", callback_data=MainMenuCB(action="create_menu"))

    # Задача 2.4: Счётчик активных кампаний
    campaigns_label = (
        f"📋 Мои кампании [{active_campaigns}]" if active_campaigns > 0 else "📋 Мои кампании"
    )
    builder.button(text=campaigns_label, callback_data=MainMenuCB(action="my_campaigns"))

    builder.button(text="📡 Каталог каналов", callback_data=MainMenuCB(action="channels_db"))
    builder.button(text="💼 B2B-пакеты", callback_data=MainMenuCB(action="b2b"))
    builder.button(text="📊 Моя статистика", callback_data=MainMenuCB(action="analytics"))
    builder.button(
        text=f"👤 Кабинет • {credits:,} кр".replace(",", " "),
        callback_data=MainMenuCB(action="cabinet"),
    )
    # Задача 2.5: Разделить поддержку на две кнопки
    builder.button(text="💬 Помощь", callback_data=MainMenuCB(action="help"))
    builder.button(text="✉️ Обратная связь", callback_data=MainMenuCB(action="feedback"))
    # Задача 2.5: Переименование кнопки смены роли
    builder.button(
        text="🔄 Переключить роль",
        callback_data=MainMenuCB(action="change_role"),
    )

    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 2, 1, 1, 1)
    else:
        builder.adjust(2, 2, 2, 1, 1)

    return builder.as_markup()


def get_owner_menu_kb(
    credits: int,
    pending_count: int = 0,
    user_id: int | None = None,
    channels_count: int = 0,
    available_payout: int = 0,
) -> InlineKeyboardMarkup:
    """
    Меню владельца канала.
    Показывается когда у пользователя есть каналы, но нет кампаний.

    Args:
        credits: Баланс пользователя.
        pending_count: Количество ожидающих заявок на размещение.
        user_id: Telegram ID для проверки прав администратора.
        channels_count: Количество каналов пользователя.
        available_payout: Сумма доступная к выводу.
    """
    builder = InlineKeyboardBuilder()

    # Задача 2.2: Счётчик каналов
    channels_label = f"📺 Мои каналы ({channels_count})" if channels_count > 0 else "📺 Мои каналы"

    # Задача 2.2: Индикатор заявок
    requests_label = f"📋 Заявки [{pending_count}] 🔴" if pending_count > 0 else "📋 Заявки"

    builder.button(text=channels_label, callback_data=MainMenuCB(action="my_channels"))
    builder.button(text=requests_label, callback_data=MainMenuCB(action="my_requests"))
    builder.button(text="➕ Добавить канал", callback_data=MainMenuCB(action="add_channel"))

    # Задача 2.1: Сумма на кнопке "Выплаты"
    payout_label = f"💸 Выплаты • {available_payout} кр" if available_payout > 0 else "💸 Выплаты"
    builder.button(text=payout_label, callback_data=MainMenuCB(action="payouts"))

    # Задача 2.3: Переименование кнопок
    builder.button(text="📊 Моя статистика", callback_data=MainMenuCB(action="analytics"))
    builder.button(
        text=f"👤 Кабинет • {credits:,} кр".replace(",", " "),
        callback_data=MainMenuCB(action="cabinet"),
    )
    # Задача 2.3: Разделить поддержку на две кнопки
    builder.button(text="💬 Помощь", callback_data=MainMenuCB(action="help"))
    builder.button(text="✉️ Обратная связь", callback_data=MainMenuCB(action="feedback"))
    # Задача 2.3: Переименование кнопки смены роли
    builder.button(
        text="🔄 Переключить роль",
        callback_data=MainMenuCB(action="change_role"),
    )

    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 2, 1, 1, 1)
    else:
        builder.adjust(2, 2, 2, 1, 1)

    return builder.as_markup()


def get_combined_menu_kb(
    credits: int,
    pending_count: int = 0,
    user_id: int | None = None,
    active_campaigns: int = 0,
    channels_count: int = 0,
    available_payout: int = 0,
) -> InlineKeyboardMarkup:
    """
    Комбинированное меню для пользователей с обеими ролями.
    Два визуальных раздела разделены заголовочными кнопками-разделителями.

    Args:
        credits: Баланс пользователя.
        pending_count: Количество ожидающих заявок на размещение.
        user_id: Telegram ID для проверки прав администратора.
        active_campaigns: Количество активных кампаний.
        channels_count: Количество каналов.
        available_payout: Сумма доступная к выводу.
    """
    builder = InlineKeyboardBuilder()

    # ── Раздел рекламодателя ──
    builder.button(
        text="── 📣 Реклама ──",
        callback_data=MainMenuCB(action="noop"),  # заголовок, не кликабелен
    )
    builder.button(text="Создать кампанию", callback_data=MainMenuCB(action="create_menu"))

    # Задача 2.6: Счётчик активных кампаний
    campaigns_label = (
        f"Мои кампании [{active_campaigns}]" if active_campaigns > 0 else "Мои кампании"
    )
    builder.button(text=campaigns_label, callback_data=MainMenuCB(action="my_campaigns"))

    builder.button(text="Каталог каналов", callback_data=MainMenuCB(action="channels_db"))
    builder.button(text="B2B-пакеты", callback_data=MainMenuCB(action="b2b"))

    # ── Раздел владельца канала ──
    # Задача 2.6: Счётчик каналов и индикатор заявок
    channels_label = f"Мои каналы ({channels_count})" if channels_count > 0 else "Мои каналы"
    requests_label = f"Заявки [{pending_count}] 🔴" if pending_count > 0 else "Заявки"
    builder.button(
        text="── 📺 Мой канал ──",
        callback_data=MainMenuCB(action="noop"),
    )
    builder.button(text=channels_label, callback_data=MainMenuCB(action="my_channels"))
    builder.button(text=requests_label, callback_data=MainMenuCB(action="my_requests"))
    builder.button(text="Добавить канал", callback_data=MainMenuCB(action="add_channel"))

    # Задача 2.6: Сумма на кнопке "Выплаты"
    payout_label = f"Выплаты • {available_payout} кр" if available_payout > 0 else "Выплаты"
    builder.button(text=payout_label, callback_data=MainMenuCB(action="payouts"))

    # ── Общие ──
    builder.button(text="📊 Моя статистика", callback_data=MainMenuCB(action="analytics"))
    builder.button(
        text=f"👤 Кабинет • {credits:,} кр".replace(",", " "),
        callback_data=MainMenuCB(action="cabinet"),
    )
    # Задача 2.6: Разделить поддержку на две кнопки
    builder.button(text="💬 Помощь", callback_data=MainMenuCB(action="help"))
    builder.button(text="✉️ Обратная связь", callback_data=MainMenuCB(action="feedback"))
    # Задача 2.6: Переименование кнопки смены роли
    builder.button(text="🔄 Переключить роль", callback_data=MainMenuCB(action="change_role"))

    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(1, 2, 2, 1, 2, 2, 2, 1, 1)
    else:
        builder.adjust(1, 2, 2, 1, 2, 2, 2, 1)

    return builder.as_markup()


# ─────────────────────────────────────────────
# Основная функция-диспетчер
# ─────────────────────────────────────────────


def get_main_menu(
    credits: int,
    user_id: int | None = None,
    # Новые параметры для роль-зависимого меню:
    role: str = "new",  # "new" | "advertiser" | "owner" | "both"
    pending_count: int = 0,  # для бейджа заявок
    active_campaigns: int = 0,  # для бейджа кампаний
    channels_count: int = 0,  # для бейджа каналов
    available_payout: int = 0,  # для суммы выплат
) -> InlineKeyboardMarkup:
    """
    Главное меню бота — адаптируется под роль пользователя.

    Args:
        credits: Баланс для отображения в кнопке кабинета.
        user_id: Telegram ID для проверки прав администратора.
        role: Роль пользователя из UserRoleService.get_user_context().
        pending_count: Количество непрочитанных заявок (для владельцев).
        active_campaigns: Количество активных кампаний (для рекламодателей).
        channels_count: Количество каналов (для владельцев).
        available_payout: Сумма доступная к выводу (для владельцев).

    Returns:
        InlineKeyboardMarkup соответствующий роли пользователя.
    """
    if role == "advertiser":
        return get_advertiser_menu_kb(
            credits=credits,
            user_id=user_id,
            active_campaigns=active_campaigns,
        )
    elif role == "owner":
        return get_owner_menu_kb(
            credits=credits,
            pending_count=pending_count,
            user_id=user_id,
            channels_count=channels_count,
            available_payout=available_payout,
        )
    elif role == "both":
        return get_combined_menu_kb(
            credits=credits,
            pending_count=pending_count,
            user_id=user_id,
            active_campaigns=active_campaigns,
            channels_count=channels_count,
            available_payout=available_payout,
        )
    else:  # "new"
        return get_onboarding_kb()
