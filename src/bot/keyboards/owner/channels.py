"""Owner channels keyboards."""


from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BACK_BTN = "Назад"


def channels_list_kb(channels: list) -> InlineKeyboardMarkup:
    """Список каналов."""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(InlineKeyboardButton(text=ch.get("title", "Канал"), callback_data=f"own:channel:{ch['id']}"))
    builder.row(InlineKeyboardButton(text="Добавить", callback_data="own:add_channel"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="main:own_menu"))
    return builder.as_markup()


def channel_detail_kb(cid: int, pending: int) -> InlineKeyboardMarkup:
    """Детали канала."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Настройки", callback_data=f"own:settings:{cid}"))
    builder.row(InlineKeyboardButton(text=f"Заявки({pending})", callback_data=f"own:channel_requests:{cid}"))
    builder.row(InlineKeyboardButton(text="Удалить", callback_data=f"own:delete_channel:{cid}"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="main:my_channels"))
    return builder.as_markup()


def channel_settings_kb(cid: int) -> InlineKeyboardMarkup:
    """Настройки канала."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Цена", callback_data=f"own:settings:price:{cid}"))
    builder.row(InlineKeyboardButton(text="Форматы", callback_data=f"own:settings:formats:{cid}"))
    builder.row(InlineKeyboardButton(text="Расписание", callback_data=f"own:settings:schedule:{cid}"))
    builder.row(InlineKeyboardButton(text="Автоподтверждение", callback_data=f"own:settings:autoaccept:{cid}"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"own:channel:{cid}"))
    return builder.as_markup()


def format_toggles_kb(cid: int, settings: dict) -> InlineKeyboardMarkup:
    """Переключение форматов."""
    builder = InlineKeyboardBuilder()
    formats = [
        ("post_24h", "Пост 24ч"),
        ("post_48h", "Пост 48ч"),
        ("post_7d", "Пост 7дн"),
        ("pin_24h", "Закреп 24ч"),
        ("pin_48h", "Закреп 48ч"),
    ]
    for fmt_code, fmt_name in formats:
        enabled = settings.get(f"allow_format_{fmt_code}", False)
        icon = "✅" if enabled else "❌"
        builder.row(InlineKeyboardButton(text=f"{icon} {fmt_name}", callback_data=f"own:format:toggle:{fmt_code}:{cid}"))
    builder.row(InlineKeyboardButton(text="Сохранить", callback_data=f"own:settings:formats:save:{cid}"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"own:settings:{cid}"))
    return builder.as_markup()
