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
        text="📣 Хочу размещать рекламу",
        callback_data=OnboardingCB(role="advertiser"),
    )
    builder.button(
        text="📺 У меня есть Telegram-канал",
        callback_data=OnboardingCB(role="owner"),
    )
    builder.button(
        text="📊 Посмотреть статистику платформы",
        callback_data=MainMenuCB(action="platform_stats"),
    )
    builder.adjust(1)
    return builder.as_markup()


def get_advertiser_menu_kb(credits: int, user_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Меню рекламодателя.
    Показывается когда у пользователя есть кампании, но нет своих каналов.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="📣 Создать кампанию", callback_data=MainMenuCB(action="create_menu"))
    builder.button(text="📋 Мои кампании", callback_data=MainMenuCB(action="my_campaigns"))
    builder.button(text="📡 Каталог каналов", callback_data=MainMenuCB(action="channels_db"))
    builder.button(text="💼 B2B-пакеты", callback_data=MainMenuCB(action="b2b"))
    builder.button(text="📊 Аналитика", callback_data=MainMenuCB(action="analytics"))
    builder.button(
        text=f"👤 Кабинет • {credits:,} кр".replace(",", " "),
        callback_data=MainMenuCB(action="cabinet"),
    )
    builder.button(text="💬 Поддержка", callback_data=MainMenuCB(action="feedback"))

    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 2, 1, 1)
    else:
        builder.adjust(2, 2, 2, 1)

    return builder.as_markup()


def get_owner_menu_kb(
    credits: int,
    pending_count: int = 0,
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Меню владельца канала.
    Показывается когда у пользователя есть каналы, но нет кампаний.

    Args:
        credits: Баланс пользователя.
        pending_count: Количество ожидающих заявок на размещение.
        user_id: Telegram ID для проверки прав администратора.
    """
    builder = InlineKeyboardBuilder()

    requests_label = (
        f"📋 Заявки [{pending_count}]" if pending_count > 0
        else "📋 Заявки"
    )

    builder.button(text="📺 Мои каналы", callback_data=MainMenuCB(action="my_channels"))
    builder.button(text=requests_label, callback_data=MainMenuCB(action="my_requests"))
    builder.button(text="➕ Добавить канал", callback_data=MainMenuCB(action="add_channel"))
    builder.button(text="💸 Выплаты", callback_data=MainMenuCB(action="payouts"))
    builder.button(text="📊 Аналитика", callback_data=MainMenuCB(action="analytics"))
    builder.button(
        text=f"👤 Кабинет • {credits:,} кр".replace(",", " "),
        callback_data=MainMenuCB(action="cabinet"),
    )
    builder.button(text="💬 Поддержка", callback_data=MainMenuCB(action="feedback"))

    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 2, 1, 1)
    else:
        builder.adjust(2, 2, 2, 1)

    return builder.as_markup()


def get_combined_menu_kb(
    credits: int,
    pending_count: int = 0,
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Комбинированное меню для пользователей с обеими ролями.
    Два визуальных раздела разделены заголовочными кнопками-разделителями.

    Args:
        credits: Баланс пользователя.
        pending_count: Количество ожидающих заявок на размещение.
        user_id: Telegram ID для проверки прав администратора.
    """
    builder = InlineKeyboardBuilder()

    # ── Раздел рекламодателя ──
    builder.button(
        text="── 📣 Реклама ──",
        callback_data=MainMenuCB(action="noop"),  # заголовок, не кликабелен
    )
    builder.button(text="Создать кампанию", callback_data=MainMenuCB(action="create_menu"))
    builder.button(text="Мои кампании", callback_data=MainMenuCB(action="my_campaigns"))
    builder.button(text="Каталог каналов", callback_data=MainMenuCB(action="channels_db"))
    builder.button(text="B2B-пакеты", callback_data=MainMenuCB(action="b2b"))

    # ── Раздел владельца канала ──
    requests_label = (
        f"Заявки [{pending_count}]" if pending_count > 0
        else "Заявки"
    )
    builder.button(
        text="── 📺 Мой канал ──",
        callback_data=MainMenuCB(action="noop"),
    )
    builder.button(text="Мои каналы", callback_data=MainMenuCB(action="my_channels"))
    builder.button(text=requests_label, callback_data=MainMenuCB(action="my_requests"))
    builder.button(text="Добавить канал", callback_data=MainMenuCB(action="add_channel"))
    builder.button(text="Выплаты", callback_data=MainMenuCB(action="payouts"))

    # ── Общие ──
    builder.button(text="📊 Аналитика", callback_data=MainMenuCB(action="analytics"))
    builder.button(
        text=f"👤 Кабинет • {credits:,} кр".replace(",", " "),
        callback_data=MainMenuCB(action="cabinet"),
    )
    builder.button(text="💬 Поддержка", callback_data=MainMenuCB(action="feedback"))

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
) -> InlineKeyboardMarkup:
    """
    Главное меню бота — адаптируется под роль пользователя.

    Args:
        credits: Баланс для отображения в кнопке кабинета.
        user_id: Telegram ID для проверки прав администратора.
        role: Роль пользователя из UserRoleService.get_user_context().
        pending_count: Количество непрочитанных заявок (для владельцев).

    Returns:
        InlineKeyboardMarkup соответствующий роли пользователя.
    """
    if role == "advertiser":
        return get_advertiser_menu_kb(credits=credits, user_id=user_id)
    elif role == "owner":
        return get_owner_menu_kb(credits=credits, pending_count=pending_count, user_id=user_id)
    elif role == "both":
        return get_combined_menu_kb(credits=credits, pending_count=pending_count, user_id=user_id)
    else:  # "new"
        return get_onboarding_kb()
