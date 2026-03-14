"""
FSMTimeoutMiddleware for FSM session timeout.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis

from src.config.settings import settings


class FSMTimeoutMiddleware(BaseMiddleware):
    """
    Middleware для таймаута FSM сессий.

    Если пользователь в FSM и last_activity > 300 секунд — очищает состояние.
    Обновляет Redis key 'fsm_activity:{user_id}' с TTL=600.
    """

    FSM_TIMEOUT_SECONDS = 300
    REDIS_TTL_SECONDS = 600

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

        state = data.get("state")
        if not state:
            return await handler(event, data)

        # Check if user is in FSM
        current_state = await state.get_state()
        if current_state is None:
            # Not in FSM, just call handler
            return await handler(event, data)

        # Check last activity
        redis_key = f"fsm_activity:{user_id}"
        last_activity_raw = await self.redis.get(redis_key)

        now = datetime.utcnow()
        now_timestamp = now.timestamp()

        if last_activity_raw:
            last_activity = float(last_activity_raw.decode())
            elapsed = now_timestamp - last_activity

            if elapsed > self.FSM_TIMEOUT_SECONDS:
                # Session expired
                await state.clear()
                if hasattr(event, "answer") and callable(event.answer):
                    await event.answer("⏱ Сессия истекла. Начните заново с /start")
                return

        # Update last activity
        await self.redis.set(redis_key, now_timestamp, ex=self.REDIS_TTL_SECONDS)

        return await handler(event, data)
