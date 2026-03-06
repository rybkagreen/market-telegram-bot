"""Утилиты для безопасной работы с callback query в aiogram 3.x."""
import contextlib
import logging
from typing import Any

from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def safe_callback_edit(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
    **kwargs: Any,
) -> bool:
    """
    Безопасное редактирование сообщения из callback query.

    Обрабатывает случаи когда сообщение удалено (InaccessibleMessage) или None.

    Returns:
        True если редактирование успешно, False иначе.
    """
    if callback.message is None:
        logger.warning("safe_callback_edit: callback.message is None")
        return False

    if isinstance(callback.message, InaccessibleMessage):
        logger.warning(
            "safe_callback_edit: message is InaccessibleMessage, "
            f"chat_id={callback.message.chat.id}"
        )
        # Попробуем ответить новым сообщением вместо редактирования
        with contextlib.suppress(Exception):
            await callback.answer(text[:200])  # answer ограничен 200 символами
        return False

    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            **kwargs,
        )
        return True
    except Exception as e:
        logger.error(f"safe_callback_edit failed: {e}")
        return False


async def safe_callback_answer(
    callback: CallbackQuery,
    text: str = "",
    show_alert: bool = False,
) -> None:
    """Безопасный ответ на callback query."""
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except Exception as e:
        logger.error(f"safe_callback_answer failed: {e}")
