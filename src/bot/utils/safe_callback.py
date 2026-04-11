"""Safe callback utility."""

import logging

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


async def safe_callback_edit(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Безопасное редактирование callback."""
    if not isinstance(callback.message, Message):
        return
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.debug(
            "edit_text failed for callback %s, falling back to answer: %s",
            callback.id,
            e,
        )
        try:
            await callback.message.answer(text, reply_markup=reply_markup)
        except Exception as e2:
            logger.error("Both edit_text and answer failed for callback %s: %s", callback.id, e2)
            import sentry_sdk

            sentry_sdk.capture_exception()
