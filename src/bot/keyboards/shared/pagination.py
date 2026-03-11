"""
Клавиатура пагинации для списков.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class PaginationCB(CallbackData, prefix="page"):
    """CallbackData для пагинации."""

    prefix: str
    page: int


def get_pagination_kb(page: int, total_pages: int, cb_prefix: str) -> InlineKeyboardMarkup:
    """
    Построить клавиатуру пагинации.

    Args:
        page: Текущая страница (1-based).
        total_pages: Всего страниц.
        cb_prefix: Префикс для callback_data.

    Returns:
        InlineKeyboardMarkup с кнопками навигации.
    """
    builder = InlineKeyboardBuilder()

    if page > 1:
        builder.button(text="◀ Пред", callback_data=PaginationCB(prefix=cb_prefix, page=page - 1))

    builder.button(
        text=f"{page}/{total_pages}", callback_data=PaginationCB(prefix=cb_prefix, page=page)
    )

    if page < total_pages:
        builder.button(text="След ▶", callback_data=PaginationCB(prefix=cb_prefix, page=page + 1))

    builder.adjust(3)
    return builder.as_markup()
