"""Клавиатуры для сравнения каналов."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.shared.channels_catalog import ChannelsCB


class ComparisonCB(CallbackData, prefix="comparison"):
    """CallbackData для сравнения каналов."""

    action: str
    channel_id: str = ""


def get_channel_with_compare_kb(
    channel_id: int,
    channel_username: str,
    is_selected: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для канала с кнопкой "Сравнить".

    Args:
        channel_id: ID канала.
        channel_username: Username канала.
        is_selected: Выбран ли канал для сравнения.
    """
    builder = InlineKeyboardBuilder()

    compare_text = "✅ В сравнении" if is_selected else "📊 Сравнить"
    builder.button(
        text=compare_text,
        callback_data=ComparisonCB(
            action="toggle",
            channel_id=str(channel_id),
        ).pack(),
    )

    builder.button(
        text="📡 Открыть канал",
        callback_data=ChannelsCB(
            action="view_channel",
            value=str(channel_id),
        ).pack(),
    )

    builder.adjust(2)
    return builder.as_markup()


def get_comparison_bar_kb(selected_count: int) -> InlineKeyboardMarkup:
    """
    Панель управления сравнением.

    Args:
        selected_count: Количество выбранных каналов.
    """
    builder = InlineKeyboardBuilder()

    if selected_count > 0:
        builder.button(
            text=f"📊 Сравнить ({selected_count})",
            callback_data=ComparisonCB(action="compare").pack(),
        )
        builder.button(
            text="❌ Сбросить",
            callback_data=ComparisonCB(action="clear").pack(),
        )
        builder.adjust(2)
    else:
        builder.button(
            text="🔙 В каталог",
            callback_data=ChannelsCB(action="categories").pack(),
        )
        builder.adjust(1)

    return builder.as_markup()


def get_comparison_result_kb(channel_ids: list[int]) -> InlineKeyboardMarkup:
    """
    Клавиатура для страницы сравнения.

    Args:
        channel_ids: Список ID сравниваемых каналов.
    """
    builder = InlineKeyboardBuilder()

    # Кнопки для каждого канала
    for channel_id in channel_ids[:5]:  # Максимум 5
        builder.button(
            text="📋 Добавить в кампанию",
            callback_data=f"add_to_campaign:{channel_id}",
        )

    builder.button(
        text="🔙 В каталог",
        callback_data=ChannelsCB(action="categories").pack(),
    )
    builder.adjust(1)

    return builder.as_markup()


def get_compare_action_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура когда выбраны 2+ канала.

    Показывает кнопки для перехода к сравнению.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📊 Сравнить выбранные",
        callback_data=ComparisonCB(action="compare").pack(),
    )
    builder.button(
        text="🗑 Сбросить",
        callback_data=ComparisonCB(action="clear").pack(),
    )
    builder.button(
        text="📋 Изменить выбор",
        callback_data=ChannelsCB(action="show_compare_list", value="all").pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
