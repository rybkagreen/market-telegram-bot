"""Клавиатуры для настроек канала (channel_settings)."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_channel_cfg_menu_kb(channel_id: int, settings) -> InlineKeyboardMarkup:
    """Главное меню настроек канала."""
    builder = InlineKeyboardBuilder()

    builder.button(text="💰 Цена за пост", callback_data=f"ch_cfg:price:{channel_id}")
    builder.button(text="🕐 Расписание", callback_data=f"ch_cfg:schedule:{channel_id}")
    builder.button(text="📦 Пакеты", callback_data=f"ch_cfg:packages:{channel_id}")
    builder.button(text="📅 Подписка", callback_data=f"ch_cfg:subscription:{channel_id}")

    auto_text = "👁 Выключить" if settings.auto_accept_enabled else "🤖 Включить"
    builder.button(
        text=f"Авто-принятие: {auto_text}", callback_data=f"ch_cfg:auto_accept:{channel_id}"
    )
    builder.button(text="◀️ Назад", callback_data=f"channel_menu:{channel_id}")

    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_schedule_kb(channel_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для ввода расписания."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Отмена", callback_data=f"ch_cfg:view:{channel_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_packages_kb(channel_id: int, settings) -> InlineKeyboardMarkup:
    """Клавиатура настроек пакетов."""
    builder = InlineKeyboardBuilder()

    daily_toggle = "❌ Выключить" if settings.daily_package_enabled else "✅ Включить"
    builder.button(
        text=f"Дневной пакет: {daily_toggle}", callback_data=f"ch_cfg:pkg_daily_toggle:{channel_id}"
    )
    builder.button(
        text=f"Скидка дня: {settings.daily_package_discount}%",
        callback_data=f"ch_cfg:pkg_daily_discount:{channel_id}",
    )

    weekly_toggle = "❌ Выключить" if settings.weekly_package_enabled else "✅ Включить"
    builder.button(
        text=f"Недельный пакет: {weekly_toggle}",
        callback_data=f"ch_cfg:pkg_weekly_toggle:{channel_id}",
    )
    builder.button(
        text=f"Скидка недели: {settings.weekly_package_discount}%",
        callback_data=f"ch_cfg:pkg_weekly_discount:{channel_id}",
    )

    builder.button(
        text=f"Лимит постов/день: {settings.daily_package_max}",
        callback_data=f"ch_cfg:max_posts:{channel_id}",
    )
    builder.button(text="◀️ Назад", callback_data=f"ch_cfg:view:{channel_id}")

    builder.adjust(2, 2, 1)
    return builder.as_markup()
