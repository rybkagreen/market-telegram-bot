"""
UserRepository for User model operations.
"""

from decimal import Decimal

from sqlalchemy import select

from src.db.models.user import User
from src.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Репозиторий для работы с пользователями.
    """

    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID."""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Получить пользователя по username."""
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, defaults: dict) -> tuple[User, bool]:
        """
        Получить или создать пользователя.

        Returns:
            (user, created) - пользователь и флаг был ли создан
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user, False

        user = User(telegram_id=telegram_id, **defaults)
        self.session.add(user)
        await self.session.flush()
        return user, True

    async def update_balance(self, user_id: int, delta: Decimal) -> None:
        """Обновить баланс пользователя (с блокировкой строки)."""
        result = await self.session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one()
        user.balance_rub += delta
        await self.session.flush()

    async def update_earned(self, user_id: int, delta: Decimal) -> None:
        """Обновить заработок пользователя (с блокировкой строки)."""
        result = await self.session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one()
        user.earned_rub += delta
        await self.session.flush()
