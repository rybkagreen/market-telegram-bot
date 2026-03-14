"""
DBSessionMiddleware for database session management.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.db.session import async_session_factory


class DBSessionMiddleware(BaseMiddleware):
    """
    Middleware для управления сессией БД.

    Добавляет session в data handler'а.
    """

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Awaitable:
        async with async_session_factory() as session:
            data["session"] = session
            return await handler(event, data)
