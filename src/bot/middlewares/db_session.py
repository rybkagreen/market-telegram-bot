"""
Middleware для инжектирования AsyncSession в handler.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.db.session import async_session_factory


class DBSessionMiddleware(BaseMiddleware):
    """
    Middleware для инжектирования AsyncSession в handler data.

    Usage в handler:
        async def handler(message: Message, session: AsyncSession):
            # session доступен
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            return await handler(event, data)
