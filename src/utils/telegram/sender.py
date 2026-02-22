"""
Telegram Sender для отправки сообщений с обработкой ошибок.
Использует aiogram Bot для отправки сообщений в чаты.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramMigrateToChat,
    TelegramRetryAfter,
)

logger = logging.getLogger(__name__)


class SendStatus(str, Enum):
    """Статусы отправки сообщения."""

    SENT = "sent"  # Успешно отправлено
    FAILED = "failed"  # Ошибка при отправке
    SKIPPED = "skipped"  # Пропущено (rate limit, blacklist)
    RETRY = "retry"  # Требуется повторная попытка


@dataclass
class SendResult:
    """Результат отправки сообщения."""

    status: SendStatus
    message_id: int | None = None
    error_message: str | None = None
    retry_after: int | None = None  # Задержка перед повторной попыткой (сек)


class TelegramSender:
    """
    Сервис для отправки сообщений в Telegram.

    Методы:
        send_message: Отправить сообщение с retry
        send_message_safe: Отправить сообщение без исключений
    """

    def __init__(self, bot: Bot) -> None:
        """
        Инициализация sender.

        Args:
            bot: aiogram Bot instance.
        """
        self.bot = bot
        self._max_retries = 3
        self._base_delay = 1  # секунда

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
    ) -> SendResult:
        """
        Отправить сообщение с экспоненциальным retry.

        Args:
            chat_id: Telegram ID чата.
            text: Текст сообщения.
            parse_mode: Режим парсинга (HTML/Markdown).
            disable_notification: Отправить без уведомления.

        Returns:
            SendResult с результатом отправки.
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                )

                return SendResult(
                    status=SendStatus.SENT,
                    message_id=message.message_id,
                )

            except TelegramRetryAfter as e:
                # FloodWait — ждём указанное время + небольшой буфер
                retry_after = e.retry_after + 5
                logger.warning(
                    f"FloodWait for {e.retry_after}s on chat {chat_id}, "
                    f"retrying after {retry_after}s"
                )

                if attempt < self._max_retries - 1:
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    return SendResult(
                        status=SendStatus.RETRY,
                        retry_after=retry_after,
                        error_message=f"FloodWait: {e.retry_after}s",
                    )

            except TelegramMigrateToChat as e:
                # Чат мигрировал (группа → супергруппа)
                logger.info(f"Chat {chat_id} migrated to {e.migrate_to_chat_id}")
                # Возвращаем новый ID для обновления в БД
                return SendResult(
                    status=SendStatus.RETRY,
                    error_message=f"Migrated to chat: {e.migrate_to_chat_id}",
                    retry_after=0,
                )

            except TelegramForbiddenError:
                # Бот заблокирован или удалён из чата
                logger.warning(f"Bot forbidden for chat {chat_id}")
                return SendResult(
                    status=SendStatus.FAILED,
                    error_message="Bot forbidden",
                )

            except Exception as e:
                last_error = e
                logger.error(f"Error sending message to {chat_id}: {e}")

                if attempt < self._max_retries - 1:
                    # Экспоненциальная задержка: 1s, 4s, 9s
                    delay = self._base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    break

        # Все попытки исчерпаны
        return SendResult(
            status=SendStatus.FAILED,
            error_message=str(last_error) if last_error else "Unknown error",
        )

    async def send_message_safe(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
    ) -> SendResult:
        """
        Отправить сообщение без выброса исключений.

        Args:
            chat_id: Telegram ID чата.
            text: Текст сообщения.
            parse_mode: Режим парсинга.
            disable_notification: Отправить без уведомления.

        Returns:
            SendResult с результатом отправки.
        """
        try:
            return await self.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
            )
        except Exception as e:
            logger.exception(f"Unexpected error sending to {chat_id}: {e}")
            return SendResult(
                status=SendStatus.FAILED,
                error_message=f"Unexpected: {str(e)}",
            )

    async def close(self) -> None:
        """Закрыть сессию бота."""
        await self.bot.session.close()


async def create_sender(bot_token: str) -> TelegramSender:
    """
    Создать TelegramSender.

    Args:
        bot_token: Токен бота.

    Returns:
        TelegramSender instance.
    """
    bot = Bot(token=bot_token)
    return TelegramSender(bot)
