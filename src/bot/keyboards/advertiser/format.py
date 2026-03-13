"""
Клавиатуры для выбора формата публикации.
S-09: kb_select_format — фильтрация по тарифу.
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.constants.payments import PLAN_LIMITS

# Эмодзи и лейблы для форматов
FORMAT_LABELS: dict[str, str] = {
    "post_24h": "📝 Пост 24ч",
    "post_48h": "📝 Пост 48ч (+40%)",
    "post_7d": "📝 Пост 7 дней (+100%)",
    "pin_24h": "📌 Закреп 24ч (+200%)",
    "pin_48h": "📌 Закреп 48ч (+300%)",
}


def kb_select_format(plan: str) -> InlineKeyboardMarkup:
    """
    Выбор формата публикации с фильтрацией по тарифу.

    Args:
        plan: Тариф пользователя (free/starter/pro/business).

    Returns:
        InlineKeyboardMarkup с доступными форматами.
    """
    builder = InlineKeyboardBuilder()

    # Получаем доступные форматы для тарифа
    allowed_formats = PLAN_LIMITS.get(plan, {}).get("formats", ["post_24h"])

    # Создаём кнопки только для доступных форматов
    for fmt in allowed_formats:
        label = FORMAT_LABELS.get(fmt, fmt)
        builder.button(
            text=label,
            callback_data=f"placement:format:{fmt}",
        )

    # Кнопка отмены
    builder.button(
        text="❌ Отмена",
        callback_data="placement:format:cancel",
    )

    # 1 кнопка в ряд
    builder.adjust(1)

    return builder.as_markup()


def kb_format_multiplier_info() -> InlineKeyboardMarkup:
    """
    Информация о коэффициентах форматов.

    Returns:
        InlineKeyboardMarkup с кнопкой "Назад".
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔙 Назад",
        callback_data="placement:info_back",
    )

    builder.adjust(1)

    return builder.as_markup()
