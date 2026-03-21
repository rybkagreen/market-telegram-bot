"""FSMTimeoutMiddleware for FSM session timeout."""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis

from src.config.settings import settings

logger = logging.getLogger(__name__)


class FSMTimeoutMiddleware(BaseMiddleware):
    """
    Middleware для таймаута FSM сессий.

    Если пользователь в FSM и last_activity > 300 секунд — очищает состояние.
    Обновляет Redis key 'fsm_activity:{user_id}' с TTL=600.
    """

    FSM_TIMEOUT_SECONDS = 300
    REDIS_TTL_SECONDS = 600

    def __init__(self) -> None:
        self.redis = Redis.from_url(str(settings.redis_url))

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event_from_user = data.get("event_from_user")
        user_id = event_from_user.id if event_from_user else None
        if not user_id:
            return await handler(event, data)

        state = data.get("state")
        if not state:
            return await handler(event, data)

        current_state = await state.get_state()
        if current_state is None:
            return await handler(event, data)

        redis_key = f"fsm_activity:{user_id}"
        last_activity_raw = await self.redis.get(redis_key)

        now = datetime.utcnow()
        now_timestamp = now.timestamp()

        if last_activity_raw:
            last_activity = float(last_activity_raw.decode())
            elapsed = now_timestamp - last_activity

            if elapsed > self.FSM_TIMEOUT_SECONDS:
                await state.clear()
                bot = data.get("bot")
                if bot:
                    try:
                        await bot.send_message(user_id, "⏱ Сессия истекла. Начните заново с /start")
                    except Exception as e:
                        logger.warning(f"Cannot send FSM timeout message to {user_id}: {e}")
                return None

        await self.redis.set(redis_key, now_timestamp, ex=self.REDIS_TTL_SECONDS)
        return await handler(event, data)
