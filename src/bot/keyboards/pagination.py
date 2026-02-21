from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class PaginationCB(CallbackData, prefix="pg"):
    """CallbackData для пагинации."""
    action: str  # prev, next, page
    page: int
    prefix: str  # префикс для контекста (например, "campaigns", "transactions")


def get_pagination_kb(page: int, total_pages: int, prefix: str = "") -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации.
    
    Args:
        page: Текущая страница (1-based)
        total_pages: Всего страниц
        prefix: Префикс для контекста (например, "campaigns", "transactions")
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка "Назад"
    if page > 1:
        builder.button(
            text="◀ Prev",
            callback_data=PaginationCB(action="prev", page=page - 1, prefix=prefix).pack()
        )
    else:
        builder.button(text="◀", callback_data="pg_none")
    
    # Текущая страница
    builder.button(
        text=f"{page}/{total_pages}",
        callback_data="pg_none"
    )
    
    # Кнопка "Вперёд"
    if page < total_pages:
        builder.button(
            text="Next ▶",
            callback_data=PaginationCB(action="next", page=page + 1, prefix=prefix).pack()
        )
    else:
        builder.button(text="▶", callback_data="pg_none")
    
    builder.adjust(3)
    
    return builder.as_markup()
