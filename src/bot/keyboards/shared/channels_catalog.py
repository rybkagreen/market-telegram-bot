"""
Клавиатуры для базы каналов (analytics_chats).
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.shared.main_menu import MainMenuCB


class ChannelsCB(CallbackData, prefix="channels"):
    """CallbackData для базы каналов."""

    action: str
    value: str = ""  # Для одиночного выбора
    values: str = ""  # Для мультивыбора (JSON через запятую)
    page: int = 1
    filter_type: str = ""  # "category", "tariff", "members"


# Категории каналов для фильтра
CHANNEL_CATEGORIES = [
    ("💼 Бизнес", "бизнес"),
    ("📈 Маркетинг", "маркетинг"),
    ("💻 IT", "it"),
    ("💰 Финансы", "финансы"),
    ("🪙 Крипто", "крипто"),
    ("🎓 Образование", "образование"),
    ("🏠 Недвижимость", "недвижимость"),
    ("🛍️ Товары", "товары"),
    ("🔧 Услуги", "услуги"),
    ("🎬 Развлечения", "развлечения"),
    ("📰 Новости", "новости"),
    ("🌍 Другое", "other"),
]

# Тарифы
TARIFFS = [
    ("🆓 FREE", "free"),
    ("🚀 STARTER", "starter"),
    ("💎 PRO", "pro"),
    ("🏢 BUSINESS", "business"),
]


def get_channels_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню базы каналов."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📊 Статистика базы",
        callback_data=ChannelsCB(action="stats"),
    )
    builder.button(
        text="🔍 Поиск по категориям",
        callback_data=ChannelsCB(action="categories"),
    )
    builder.button(
        text="📡 Топ каналов",
        callback_data=ChannelsCB(action="top_channels"),
    )
    builder.button(
        text="🔙 В главное меню",
        callback_data=MainMenuCB(action="main_menu"),
    )
    builder.adjust(1, 1, 1)

    return builder.as_markup()


def get_categories_kb() -> InlineKeyboardMarkup:
    """Выбор категории канала (одиночный выбор)."""
    builder = InlineKeyboardBuilder()

    for label, value in CHANNEL_CATEGORIES:
        builder.button(
            text=label,
            callback_data=ChannelsCB(action="category", value=value).pack(),
        )

    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="menu").pack(),
    )
    builder.adjust(2, 2, 2, 2, 2, 2, 1)

    return builder.as_markup()


def get_multi_select_categories_kb(
    selected: list[str] | None = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура с мультивыбором категорий.

    Args:
        selected: Список выбранных категорий (коды).
    """
    builder = InlineKeyboardBuilder()
    selected = selected or []

    for label, code in CHANNEL_CATEGORIES:
        # Галочка если выбрано
        prefix = "✅ " if code in selected else ""
        builder.button(
            text=f"{prefix}{label}",
            callback_data=ChannelsCB(
                action="toggle_category",
                value=code,
            ).pack(),
        )

    # Кнопки действий
    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="categories").pack(),
    )
    builder.button(
        text="🎯 Применить фильтры",
        callback_data=ChannelsCB(action="apply_filters").pack(),
    )
    builder.adjust(2, 2, 2, 2, 2, 2, 2)

    return builder.as_markup()


def get_multi_select_tariffs_kb(
    selected: list[str] | None = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура с мультивыбором тарифов.

    Args:
        selected: Список выбранных тарифов (коды).
    """
    builder = InlineKeyboardBuilder()
    selected = selected or []

    for label, value in TARIFFS:
        # Галочка если выбрано
        prefix = "✅ " if value in selected else ""
        builder.button(
            text=f"{prefix}{label}",
            callback_data=ChannelsCB(
                action="toggle_tariff",
                value=value,
            ).pack(),
        )

    # Кнопки действий
    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="categories").pack(),
    )
    builder.button(
        text="🎯 Применить фильтры",
        callback_data=ChannelsCB(action="apply_filters").pack(),
    )
    builder.adjust(2, 2, 2)

    return builder.as_markup()


def get_active_filters_bar(
    categories: list[str],
    tariffs: list[str],
) -> str:
    """
    Сгенерировать строку активных фильтров.

    Returns:
        Текст для отображения над результатами.
    """
    filters = []

    if categories:
        cat_names = [cat.capitalize() for cat in categories]
        filters.append(f"📁 Категории: {', '.join(cat_names)}")

    if tariffs:
        tariff_names = [t.upper() for t in tariffs]
        filters.append(f"💎 Тарифы: {', '.join(tariff_names)}")

    if filters:
        return "🔍 <b>Активные фильтры:</b>\n" + "\n".join(filters) + "\n"
    return ""


def get_filter_indicator(selected_count: int) -> str:
    """Вернуть иконку с количеством выбранных фильтров."""
    if selected_count == 0:
        return "🔍 Фильтры"
    elif selected_count <= 3:
        return f"🔍 Фильтры ({selected_count})"
    else:
        return f"🔍 Фильтры ({selected_count}+)"


def get_tariff_filter_kb(category: str | None = None) -> InlineKeyboardMarkup:
    """
    Фильтр по тарифам.

    Args:
        category: Категория канала (опционально).
    """
    builder = InlineKeyboardBuilder()

    for label, value in TARIFFS:
        callback_value = f"{value}"
        if category:
            callback_value = f"{category}_{value}"
        builder.button(
            text=label,
            callback_data=ChannelsCB(action="tariff", value=callback_value),
        )

    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="categories" if category else "menu"),
    )
    builder.adjust(2, 2)

    return builder.as_markup()


def get_subcategories_kb(topic: str) -> InlineKeyboardMarkup:
    """
    Подкатегории для топика.

    Args:
        topic: Родительский топик.
    """
    # Подкатегории будут загружаться динамически
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📊 Показать статистику",
        callback_data=ChannelsCB(action="subcategory_stats", value=topic),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="categories"),
    )
    builder.adjust(1)

    return builder.as_markup()


def get_channels_pagination_kb(
    current_page: int,
    total_pages: int,
    category: str | None = None,
) -> InlineKeyboardMarkup:
    """
    Пагинация для списка каналов.

    Args:
        current_page: Текущая страница.
        total_pages: Всего страниц.
        category: Категория (опционально).
    """
    builder = InlineKeyboardBuilder()

    # Предыдущая страница
    if current_page > 1:
        prev_page = current_page - 1
        builder.button(
            text="⬅️ Назад",
            callback_data=ChannelsCB(
                action="page",
                value=category or "all",
                page=prev_page,
            ),
        )

    # Индикатор страницы
    builder.button(
        text=f"{current_page}/{total_pages}",
        callback_data="channels:noop",
    )

    # Следующая страница
    if current_page < total_pages:
        next_page = current_page + 1
        builder.button(
            text="➡️ Вперёд",
            callback_data=ChannelsCB(
                action="page",
                value=category or "all",
                page=next_page,
            ),
        )

    builder.button(
        text="🔙 В меню",
        callback_data=ChannelsCB(action="menu"),
    )

    if current_page > 1 or current_page < total_pages:
        builder.adjust(1, 2, 1)
    else:
        builder.adjust(2, 1)

    return builder.as_markup()


def get_channel_detail_kb(channel_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для детальной страницы канала.

    Args:
        channel_id: ID канала.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📋 Добавить в кампанию",
        callback_data=ChannelsCB(action="add_to_campaign", value=str(channel_id)),
    )
    builder.button(
        text="🔙 Назад к каталогу",
        callback_data=ChannelsCB(action="top_channels"),
    )
    builder.adjust(1)

    return builder.as_markup()
