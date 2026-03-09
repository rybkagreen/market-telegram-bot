"""Клавиатуры для медиакита канала."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.channels import ChannelsCB


class MediakitCB(CallbackData, prefix="mediakit"):
    """CallbackData для медиакита."""

    action: str
    channel_id: str = ""
    color: str = ""


COLOR_PRESETS = [
    ("🔵 Синий", "#1a73e8"),
    ("🔴 Красный", "#d93025"),
    ("🟢 Зелёный", "#188038"),
    ("🟡 Жёлтый", "#f9ab00"),
    ("🟣 Фиолетовый", "#7c4dff"),
    ("⚫ Чёрный", "#202124"),
    ("⚪ Белый", "#ffffff"),
]


def get_mediakit_menu_kb(channel_id: int) -> InlineKeyboardMarkup:
    """Меню медиакита для владельца."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✏️ Редактировать",
        callback_data=MediakitCB(action="edit", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="📤 Скачать PDF",
        callback_data=MediakitCB(action="download", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="🔗 Получить ссылку",
        callback_data=MediakitCB(action="link", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="👁 Предпросмотр",
        callback_data=MediakitCB(action="preview", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=f"channel_menu:{channel_id}",
    )
    builder.adjust(1, 1, 1, 1)

    return builder.as_markup()


def get_mediakit_edit_kb(channel_id: int) -> InlineKeyboardMarkup:
    """Меню редактирования медиакита."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📝 Описание",
        callback_data=MediakitCB(action="edit_desc", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="🖼 Логотип",
        callback_data=MediakitCB(action="edit_logo", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="🎨 Цвет темы",
        callback_data=MediakitCB(action="edit_color", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="📊 Метрики",
        callback_data=MediakitCB(action="edit_metrics", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="🔒 Приватность",
        callback_data=MediakitCB(action="edit_privacy", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=MediakitCB(action="menu", channel_id=str(channel_id)).pack(),
    )
    builder.adjust(1, 1, 1, 1, 1)

    return builder.as_markup()


def get_color_selector_kb(channel_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора цвета темы."""
    builder = InlineKeyboardBuilder()

    for label, color in COLOR_PRESETS:
        builder.button(
            text=label,
            callback_data=MediakitCB(
                action="color_set", channel_id=str(channel_id), color=color
            ).pack(),
        )

    builder.button(
        text="🔙 Назад",
        callback_data=MediakitCB(action="edit", channel_id=str(channel_id)).pack(),
    )
    builder.adjust(2, 2, 2, 1)

    return builder.as_markup()


def get_metrics_selector_kb(
    channel_id: int, selected: list[str] | None = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора метрик для отображения.

    Args:
        channel_id: ID канала.
        selected: Список выбранных метрик.
    """
    builder = InlineKeyboardBuilder()
    selected = selected or []

    metrics = [
        ("subscribers", "👥 Подписчики"),
        ("avg_views", "👁 Просмотры"),
        ("er", "📈 ER"),
        ("post_frequency", "📝 Частота"),
        ("price", "💰 Цена"),
        ("topics", "🏷 Тематики"),
    ]

    for code, label in metrics:
        prefix = "✅ " if code in selected else ""
        builder.button(
            text=f"{prefix}{label}",
            callback_data=MediakitCB(
                action=f"toggle_metric_{code}", channel_id=str(channel_id)
            ).pack(),
        )

    builder.button(
        text="💾 Сохранить",
        callback_data=MediakitCB(action="save_metrics", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=MediakitCB(action="edit", channel_id=str(channel_id)).pack(),
    )
    builder.adjust(2, 2, 2, 1, 1)

    return builder.as_markup()


def get_public_mediakit_kb(channel_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для публичной страницы медиакита."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📤 Скачать PDF",
        callback_data=MediakitCB(action="download_public", channel_id=str(channel_id)).pack(),
    )
    builder.button(
        text="📋 Добавить в кампанию",
        callback_data=f"add_to_campaign:{channel_id}",
    )
    builder.button(
        text="🔙 В каталог",
        callback_data=ChannelsCB(action="categories").pack(),
    )
    builder.adjust(1, 1, 1)

    return builder.as_markup()
