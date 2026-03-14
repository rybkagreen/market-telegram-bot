"""
ThrottlingMiddleware for rate limiting.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis

from src.config.settings import settings


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов.

    Использует Redis. Ключ: 'throttle:{user_id}'. TTL=0.5 секунды.
    """

    def __init__(self) -> None:
        self.redis = Redis.from_url(settings.REDIS_URL)

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Awaitable:
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)

        key = f"throttle:{user_id}"

        # Try to set key with NX (only if not exists)
        acquired = await self.redis.set(key, 1, ex=0.5, nx=True)

        if not acquired:
            # Rate limited
            if hasattr(event, "answer") and callable(event.answer):
                await event.answer("⏳ Подождите немного.")
            return

        try:
            return await handler(event, data)
        finally:
            # Clean up key after handler completes
            await self.redis.delete(key)
