"""Owner requests keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def requests_list_kb(reqs: list) -> InlineKeyboardMarkup:
    """Список заявок."""
    builder = InlineKeyboardBuilder()
    for req in reqs[:10]:
        builder.row(InlineKeyboardButton(text=f"Заявка #{req['id']}", callback_data=f"own:request:{req['id']}"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="main:own_menu"))
    return builder.as_markup()


def request_detail_kb(rid: int, round: int) -> InlineKeyboardMarkup:
    """Детали заявки."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Принять", callback_data=f"own:accept:{rid}"))
    builder.row(InlineKeyboardButton(text="Контр", callback_data=f"own:counter:{rid}"))
    builder.row(InlineKeyboardButton(text="Отклонить", callback_data=f"own:reject:{rid}"))
    builder.row(InlineKeyboardButton(text="Полный текст", callback_data=f"own:request:fulltext:{rid}"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="main:my_requests"))
    return builder.as_markup()


def reject_reason_kb(rid: int) -> InlineKeyboardMarkup:
    """Выбор причины отклонения."""
    builder = InlineKeyboardBuilder()
    reasons = [
        ("Не подходит тематика", "topic"),
        ("Низкое качество", "quality"),
        ("Дорого", "price"),
        ("Другое", "other"),
    ]
    for reason_text, reason_code in reasons:
        builder.row(InlineKeyboardButton(text=reason_text, callback_data=f"own:reject:reason:{reason_code}:{rid}"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data=f"own:request:{rid}"))
    return builder.as_markup()


def counter_offer_kb(rid: int) -> InlineKeyboardMarkup:
    """Контр-оффер."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отправить", callback_data=f"own:counter:send:{rid}"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data=f"own:request:{rid}"))
    return builder.as_markup()
