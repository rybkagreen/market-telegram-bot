"""
AdminFilter for admin-only handlers.
"""

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from src.db.repositories.user_repo import UserRepository


class AdminFilter(BaseFilter):
    """
    Фильтр для администраторов.

    Проверяет is_admin=True в БД.
    """

    async def __call__(
        self,
        event: Message | CallbackQuery,
        session: Any,
    ) -> bool:
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return False

        user = await UserRepository(session).get_by_telegram_id(user_id)
        return user is not None and user.is_admin
