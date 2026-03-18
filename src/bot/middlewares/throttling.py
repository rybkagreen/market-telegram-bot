"""ThrottlingMiddleware for rate limiting."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis

from src.config.settings import settings


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов. Использует Redis."""

    def __init__(self) -> None:
        self.redis = Redis.from_url(str(settings.redis_url))

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Awaitable:
        event_from_user = data.get("event_from_user")
        if event_from_user is None:
            return await handler(event, data)
        user_id = event_from_user.id

        key = f"throttle:{user_id}"
        acquired = await self.redis.set(key, 1, ex=1, nx=True)

        if not acquired:
            bot = data.get("bot")
            if bot:
                await bot.send_message(user_id, "⏳ Подождите немного.")
            return

        try:
            return await handler(event, data)
        finally:
            await self.redis.delete(key)
