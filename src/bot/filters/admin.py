"""
Кастомный фильтр для проверки прав администратора.
"""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from src.db.repositories.user_repo import UserRepository


class AdminFilter(BaseFilter):
    """
    Фильтр — проверяет is_admin флаг в БД.

    Использование:
        router.message.filter(AdminFilter())
        router.callback_query.filter(AdminFilter())

    Если пользователь не админ — фильтр молча возвращает False,
    handler не вызывается.
    """

    async def __call__(self, event: Message | CallbackQuery, data: dict) -> bool:
        """
        Проверить является ли пользователь администратором через БД.

        Args:
            event: Сообщение или callback query.
            data: Context data (должен содержать session).

        Returns:
            True если user.is_admin == True.
        """
        # Получить session из data dict
        session = data.get("session")
        if session is None:
            return False

        # Получить from_user
        user = event.from_user if hasattr(event, "from_user") else None
        if user is None:
            return False

        # Проверить в БД
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(user.id)
        if db_user is None:
            return False

        return db_user.is_admin
