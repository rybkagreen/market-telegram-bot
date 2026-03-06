"""
Utilities для работы с сообщениями Telegram.
"""

import logging

from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from aiogram.utils.keyboard import InlineKeyboardMarkup  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


async def safe_edit_message(
    message: Message | CallbackQuery | InaccessibleMessage | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> bool:
    """
    Универсальная функция редактирования сообщения.
    Работает и с обычными сообщениями, и с сообщениями с фото/медиа.

    Args:
        message: Сообщение или CallbackQuery для редактирования.
        text: Текст для отображения.
        reply_markup: Клавиатура (опционально).
        parse_mode: Режим парсинга (по умолчанию HTML).

    Returns:
        True если редактирование успешно, False иначе.
    """
    if message is None:
        logger.warning("safe_edit_message called with None")
        return False

    # Получаем Message из CallbackQuery
    if isinstance(message, CallbackQuery):
        target_message = message.message
        if not target_message:
            logger.warning("CallbackQuery.message is None")
            return False
    else:
        target_message = message

    # Проверяем что сообщение доступно для редактирования
    if isinstance(target_message, InaccessibleMessage):
        logger.warning("Cannot edit InaccessibleMessage")
        return False

    try:
        # Пробуем edit_text
        await target_message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except Exception as e:
        error_text = str(e)

        # Если сообщение с фото/медиа — используем edit_message_caption
        if "there is no text" in error_text.lower() or "message to edit" in error_text.lower():
            try:
                await target_message.edit_message_caption(  # type: ignore[attr-defined]
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                logger.debug("Used edit_message_caption instead of edit_text")
                return True
            except Exception as caption_error:
                logger.debug(f"edit_message_caption also failed: {caption_error}")

        # Fallback: отправляем новое сообщение
        try:
            await target_message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            logger.debug("Used answer() as fallback")
            return True
        except Exception as final_error:
            logger.error(f"All edit attempts failed: {final_error}")
            return False

    return True
