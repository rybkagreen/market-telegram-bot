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
    parse_mode: str = "HTML",  # По умолчанию HTML для форматирования
    **kwargs: Any,
) -> bool:
    """
    Безопасное редактирование сообщения из callback query.

    Обрабатывает случаи когда:
    - сообщение удалено (InaccessibleMessage)
    - сообщение None
    - сообщение содержит фото (использует edit_message_caption)
    - сообщение без текста (отправляет новое)

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
        # Попытка редактирования текста
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            **kwargs,
        )
        return True
    except ValueError as e:
        # Ошибка: "there is no text in the message to edit"
        # Сообщение может быть фото или иметь только клавиатуру
        error_str = str(e).lower()
        if "no text" in error_str or "text" in error_str:
            logger.warning(
                f"Message has no text (may be media or keyboard-only), "
                f"trying edit_message_caption: {e}"
            )
            try:
                # Попытка редактирования caption (для фото) через Bot
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    **kwargs,
                )
                return True
            except Exception as caption_err:
                logger.warning(f"edit_message_caption failed: {caption_err}")
                # Если caption тоже не работает, отправляем новое сообщение
                with contextlib.suppress(Exception):
                    await callback.message.answer(
                        text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                        **kwargs,
                    )
                return False
        else:
            logger.warning(f"safe_callback_edit ValueError: {e}")
            return False
    except Exception as e:
        # Другие ошибки (сообщение удалено, недоступно и т.д.)
        logger.warning(f"safe_callback_edit failed: {e}")
        # Попробуем отправить новое сообщение
        with contextlib.suppress(Exception):
            await callback.message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs,
            )
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
