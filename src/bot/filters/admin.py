"""
Кастомный фильтр для проверки прав администратора.
"""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from src.config.settings import settings


class AdminFilter(BaseFilter):
    """
    Фильтр — пропускает только пользователей из ADMIN_IDS.

    Использование:
        router.message.filter(AdminFilter())
        router.callback_query.filter(AdminFilter())

    Если пользователь не админ — фильтр молча возвращает False,
    handler не вызывается.
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        """
        Проверить является ли пользователь администратором.

        Args:
            event: Сообщение или callback query.

        Returns:
            True если пользователь в ADMIN_IDS.
        """
        user = event.from_user if hasattr(event, "from_user") else None
        if user is None:
            return False
        return user.id in settings.admin_ids
