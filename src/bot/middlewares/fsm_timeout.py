"""
Middleware для автоматического сброса FSM состояния после timeout.

Если пользователь не активен в FSM диалоге больше FSM_TIMEOUT секунд,
состояние автоматически сбрасывается.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

# Timeout в секундах (5 минут)
FSM_TIMEOUT = 300


class FSMTimeoutMiddleware(BaseMiddleware):
    """
    Middleware проверяет время последнего сообщения в FSM диалоге.
    Если прошло больше FSM_TIMEOUT секунд — сбрасывает состояние.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state = data.get("state")
        if state is None:
            return await handler(event, data)

        # Проверяем текущее состояние
        current_state = await state.get_state()
        if not current_state or current_state == "-":
            return await handler(event, data)

        # Получаем данные FSM
        fsm_data = await state.get_data()
        last_activity = fsm_data.get("_last_activity")

        now = datetime.now(UTC).timestamp()

        if last_activity:
            elapsed = now - last_activity
            if elapsed > FSM_TIMEOUT:
                # Timeout истёк — сбрасываем состояние
                user = data.get("event_from_user")
                user_id = user.id if user else "unknown"
                logger.info(
                    f"FSM timeout for user {user_id}: "
                    f"{elapsed:.0f}s > {FSM_TIMEOUT}s (state: {current_state})"
                )
                await state.clear()
                return await handler(event, data)

        # Обновляем время активности
        await state.update_data(_last_activity=now)

        return await handler(event, data)
