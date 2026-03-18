"""Safe callback utility."""

from aiogram.types import CallbackQuery, InlineKeyboardMarkup


async def safe_callback_edit(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Безопасное редактирование callback."""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup)
