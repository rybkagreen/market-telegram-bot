"""
Middleware для защиты от спама (throttling) через Redis.
"""

import logging

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from redis.asyncio import Redis
from typing import Any, Awaitable, Callable, Union

logger = logging.getLogger(__name__)

THROTTLE_TIME = 0.5  # секунды между запросами


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов от пользователей.

    Использует Redis для хранения ключей с TTL.
    Если пользователь отправляет запросы чаще чем раз в THROTTLE_TIME,
    запрос блокируется и пользователю отправляется уведомление.
    """

    def __init__(self, redis: Redis) -> None:
        """
        Инициализация middleware.

        Args:
            redis: Redis клиент для хранения ключей троттлинга.
        """
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Вызов middleware.

        Args:
            handler: Обработчик для вызова.
            event: Событие Telegram.
            data: Данные события.

        Returns:
            Результат работы обработчика или None если запрос заблокирован.
        """
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        key = f"throttle:{user.id}"

        # Проверяем, есть ли ключ в Redis
        if await self.redis.exists(key):
            logger.debug(f"Throttling user {user.id}")
            # Пользователь отправляет слишком часто
            if isinstance(event, Message):
                await event.answer("⏳ Подождите немного...")
            elif isinstance(event, Update) and event.message:
                await event.message.answer("⏳ Подождите немного...")
            elif isinstance(event, CallbackQuery):
                await event.answer("⏳ Подождите немного...", show_alert=False)
            return

        # Устанавливаем ключ с TTL
        # Redis setex принимает TTL в секундах (целое число)
        await self.redis.setex(key, int(THROTTLE_TIME * 1000), "1")
        return await handler(event, data)
