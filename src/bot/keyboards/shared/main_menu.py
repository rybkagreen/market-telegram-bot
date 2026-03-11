"""
Клавиатура главного меню бота.
Этап 0: Строгая архитектура меню согласно спецификации v3.0.

Иерархия:
- Уровень 1: Главное меню (4 кнопки, shared для всех)
- Уровень 2A: Меню рекламодателя (5 кнопок)
- Уровень 2B: Меню владельца (5 кнопок)
- Уровень 2C: Комбинированное меню (dual-role)
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
# Уровень 1 — Главное меню (shared, 4 кнопки)
# ─────────────────────────────────────────────


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """
    Главное меню — 4 кнопки, shared для всех ролей.
    Вызывается из handle_start() и по callback main:main_menu.

    Кнопки:
    - 👤 Кабинет → main:cabinet
    - 🔄 Выбрать роль → main:change_role
    - 💬 Помощь → main:help
    - ✉️ Обратная связь → main:feedback
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="👤 Кабинет", callback_data=MainMenuCB(action="cabinet"))
    builder.button(text="🔄 Выбрать роль", callback_data=MainMenuCB(action="change_role"))
    builder.button(text="💬 Помощь", callback_data=MainMenuCB(action="help"))
    builder.button(text="✉️ Обратная связь", callback_data=MainMenuCB(action="feedback"))

    builder.adjust(2, 2)
    return builder.as_markup()


# ─────────────────────────────────────────────
# Уровень 2A — Меню рекламодателя (5 кнопок)
# ─────────────────────────────────────────────


def get_advertiser_menu_kb(
    active_campaigns: int = 0,
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Меню рекламодателя — ровно 5 кнопок.

    Args:
        active_campaigns: если > 0, добавляет счётчик в кнопку "Мои кампании".
        user_id: Telegram ID для проверки прав администратора.

    Кнопки:
    - 📊 Статистика и аналитика → main:analytics
    - 📣 Создать кампанию → main:create_campaign
    - 📋 Мои кампании → main:my_campaigns
    - 💼 B2B-пакеты → main:b2b
    - 🔙 В главное меню → main:main_menu
    """
    builder = InlineKeyboardBuilder()

    # Кнопка 1: Статистика и аналитика
    builder.button(
        text="📊 Статистика и аналитика",
        callback_data=MainMenuCB(action="analytics"),
    )

    # Кнопка 2: Создать кампанию
    builder.button(
        text="📣 Создать кампанию",
        callback_data=MainMenuCB(action="create_campaign"),
    )

    # Кнопка 3: Мои кампании (со счётчиком если есть активные)
    campaigns_label = (
        f"📋 Мои кампании ({active_campaigns})" if active_campaigns > 0 else "📋 Мои кампании"
    )
    builder.button(
        text=campaigns_label,
        callback_data=MainMenuCB(action="my_campaigns"),
    )

    # Кнопка 4: B2B-пакеты
    builder.button(
        text="💼 B2B-пакеты",
        callback_data=MainMenuCB(action="b2b"),
    )

    # Кнопка 5: В главное меню (всегда последняя)
    builder.button(
        text="🔙 В главное меню",
        callback_data=MainMenuCB(action="main_menu"),
    )

    # Добавляем кнопку Админ для администраторов
    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 1, 1)
    else:
        builder.adjust(2, 2, 1)

    return builder.as_markup()


# ─────────────────────────────────────────────
# Уровень 2B — Меню владельца канала (5 кнопок)
# ─────────────────────────────────────────────


def get_owner_menu_kb(
    pending_requests: int = 0,
    available_payout: int = 0,
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Меню владельца — ровно 5 кнопок.

    Args:
        pending_requests: если > 0, добавляет счётчик в кнопку "Заявки".
        available_payout: опционально отображать в кнопке "Выплаты".
        user_id: Telegram ID для проверки прав администратора.

    Кнопки:
    - 📊 Статистика → main:owner_analytics
    - 📺 Мои каналы → main:my_channels
    - 📋 Заявки → main:my_requests
    - 💸 Выплаты → main:payouts
    - 🔙 В главное меню → main:main_menu
    """
    builder = InlineKeyboardBuilder()

    # Кнопка 1: Статистика (ТОЛЬКО owner_analytics, НЕ analytics!)
    builder.button(
        text="📊 Статистика",
        callback_data=MainMenuCB(action="owner_analytics"),
    )

    # Кнопка 2: Мои каналы
    builder.button(
        text="📺 Мои каналы",
        callback_data=MainMenuCB(action="my_channels"),
    )

    # Кнопка 3: Заявки (со счётчиком если есть ожидающие)
    requests_label = (
        f"📋 Заявки 🔴 ({pending_requests})" if pending_requests > 0 else "📋 Заявки"
    )
    builder.button(
        text=requests_label,
        callback_data=MainMenuCB(action="my_requests"),
    )

    # Кнопка 4: Выплаты (с суммой если доступна)
    payout_label = (
        f"💸 Выплаты • {available_payout} кр" if available_payout > 0 else "💸 Выплаты"
    )
    builder.button(
        text=payout_label,
        callback_data=MainMenuCB(action="payouts"),
    )

    # Кнопка 5: В главное меню (всегда последняя)
    builder.button(
        text="🔙 В главное меню",
        callback_data=MainMenuCB(action="main_menu"),
    )

    # Добавляем кнопку Админ для администраторов
    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(2, 2, 1, 1)
    else:
        builder.adjust(2, 2, 1)

    return builder.as_markup()


# ─────────────────────────────────────────────
# Уровень 2C — Комбинированное меню (dual-role)
# ─────────────────────────────────────────────


def get_combined_menu_kb(
    active_campaigns: int = 0,
    pending_requests: int = 0,
    available_payout: int = 0,
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Объединённое меню для dual-role — секции advertiser + owner + возврат.

    Args:
        active_campaigns: для счётчика кампаний.
        pending_requests: для счётчика заявок.
        available_payout: для суммы выплат.
        user_id: Telegram ID для проверки прав администратора.
    """
    builder = InlineKeyboardBuilder()

    # ── Раздел рекламодателя ──
    builder.button(
        text="── 📣 РЕКЛАМОДАТЕЛЬ ──",
        callback_data=MainMenuCB(action="noop"),  # заголовок, не кликабелен
    )
    builder.button(
        text="📊 Статистика и аналитика",
        callback_data=MainMenuCB(action="analytics"),
    )
    builder.button(
        text="📣 Создать кампанию",
        callback_data=MainMenuCB(action="create_campaign"),
    )

    campaigns_label = (
        f"📋 Мои кампании ({active_campaigns})" if active_campaigns > 0 else "📋 Мои кампании"
    )
    builder.button(
        text=campaigns_label,
        callback_data=MainMenuCB(action="my_campaigns"),
    )
    builder.button(
        text="💼 B2B-пакеты",
        callback_data=MainMenuCB(action="b2b"),
    )

    # ── Раздел владельца канала ──
    builder.button(
        text="── 📺 ВЛАДЕЛЕЦ КАНАЛА ──",
        callback_data=MainMenuCB(action="noop"),  # заголовок, не кликабелен
    )
    builder.button(
        text="📊 Статистика каналов",
        callback_data=MainMenuCB(action="owner_analytics"),
    )
    builder.button(
        text="📺 Мои каналы",
        callback_data=MainMenuCB(action="my_channels"),
    )

    requests_label = (
        f"📋 Заявки 🔴 ({pending_requests})" if pending_requests > 0 else "📋 Заявки"
    )
    builder.button(
        text=requests_label,
        callback_data=MainMenuCB(action="my_requests"),
    )

    payout_label = (
        f"💸 Выплаты • {available_payout} кр" if available_payout > 0 else "💸 Выплаты"
    )
    builder.button(
        text=payout_label,
        callback_data=MainMenuCB(action="payouts"),
    )

    # ── Общие ──
    builder.button(
        text="🔙 В главное меню",
        callback_data=MainMenuCB(action="main_menu"),
    )

    if user_id and _is_admin(user_id):
        builder.button(text="🔐 Админ", callback_data=MainMenuCB(action="admin_panel"))
        builder.adjust(1, 2, 2, 1, 2, 2, 1, 1)
    else:
        builder.adjust(1, 2, 2, 1, 2, 2, 1, 1)

    return builder.as_markup()


# ─────────────────────────────────────────────
# Диспетчер по роли
# ─────────────────────────────────────────────


def get_role_menu_kb(
    role: str,
    active_campaigns: int = 0,
    pending_requests: int = 0,
    available_payout: int = 0,
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Диспетчер по роли:
    - "new"        → get_main_menu_kb()
    - "advertiser" → get_advertiser_menu_kb(...)
    - "owner"      → get_owner_menu_kb(...)
    - "both"       → get_combined_menu_kb(...)

    Args:
        role: Роль пользователя ("new", "advertiser", "owner", "both").
        active_campaigns: для advertiser/both.
        pending_requests: для owner/both.
        available_payout: для owner/both.
        user_id: для проверки администратора.

    Returns:
        InlineKeyboardMarkup соответствующий роли пользователя.
    """
    if role == "new":
        return get_main_menu_kb()
    elif role == "advertiser":
        return get_advertiser_menu_kb(
            active_campaigns=active_campaigns,
            user_id=user_id,
        )
    elif role == "owner":
        return get_owner_menu_kb(
            pending_requests=pending_requests,
            available_payout=available_payout,
            user_id=user_id,
        )
    elif role == "both":
        return get_combined_menu_kb(
            active_campaigns=active_campaigns,
            pending_requests=pending_requests,
            available_payout=available_payout,
            user_id=user_id,
        )
    else:
        # Fallback для неизвестной роли
        return get_main_menu_kb()


# ─────────────────────────────────────────────
# Обратная совместимость (deprecated)
# ─────────────────────────────────────────────


def get_main_menu(
    credits: int = 0,  # unused, оставлен для совместимости
    user_id: int | None = None,
    role: str = "new",
    pending_count: int = 0,
    active_campaigns: int = 0,
    channels_count: int = 0,  # unused
    available_payout: int = 0,
) -> InlineKeyboardMarkup:
    """
    Устаревшая функция-обёртка для обратной совместимости.
    Используйте напрямую get_role_menu_kb().

    Args:
        credits: Не используется (для совместимости).
        user_id: Telegram ID для проверки прав администратора.
        role: Роль пользователя.
        pending_count: Количество ожидающих заявок.
        active_campaigns: Количество активных кампаний.
        channels_count: Не используется.
        available_payout: Сумма доступная к выводу.

    Returns:
        InlineKeyboardMarkup соответствующий роли пользователя.
    """
    return get_role_menu_kb(
        role=role,
        active_campaigns=active_campaigns,
        pending_requests=pending_count,
        available_payout=available_payout,
        user_id=user_id,
    )


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
