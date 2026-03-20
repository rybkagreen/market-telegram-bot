"""UserRepository for User model operations."""

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from src.config.settings import settings
from src.db.models.user import User
from src.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями."""

    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID."""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Получить пользователя по username."""
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    def _is_admin_id(self, telegram_id: int) -> bool:
        """Проверяет, входит ли telegram_id в ADMIN_IDS."""
        return telegram_id in settings.admin_ids

    async def get_or_create(self, telegram_id: int, defaults: dict) -> tuple[User, bool]:
        """Получить или создать пользователя. Автоматически устанавливает is_admin для ADMIN_IDS."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Обновляем is_admin если изменился ADMIN_IDS
            if self._is_admin_id(telegram_id) and not user.is_admin:
                user.is_admin = True
            return user, False
        # Создаём нового пользователя с is_admin=True если в ADMIN_IDS
        if self._is_admin_id(telegram_id):
            defaults = {**defaults, "is_admin": True}
        user = User(telegram_id=telegram_id, **defaults)
        self.session.add(user)
        await self.session.flush()
        return user, True

    async def update_balance(self, user_id: int, delta: Decimal) -> None:
        """Обновить баланс пользователя (с блокировкой строки)."""
        result = await self.session.execute(select(User).where(User.id == user_id).with_for_update())
        user = result.scalar_one()
        user.balance_rub += delta
        await self.session.flush()

    async def update_earned(self, user_id: int, delta: Decimal) -> None:
        """Обновить заработок пользователя (с блокировкой строки)."""
        result = await self.session.execute(select(User).where(User.id == user_id).with_for_update())
        user = result.scalar_one()
        user.earned_rub += delta
        await self.session.flush()

    async def create_or_update(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """
        Create or update user by telegram_id (upsert pattern).
        Автоматически устанавливает is_admin для ADMIN_IDS.

        Args:
            telegram_id: Telegram user ID.
            username: Telegram username (optional).
            first_name: Telegram first name (optional).
            last_name: Telegram last name (optional).

        Returns:
            User instance (existing or newly created).
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update existing user - only update changed fields
            update_data: dict[str, Any] = {}
            if username is not None and username != user.username:
                update_data["username"] = username
            if first_name is not None and first_name != user.first_name:
                update_data["first_name"] = first_name
            if last_name is not None and last_name != user.last_name:
                update_data["last_name"] = last_name
            # Обновляем is_admin если изменился ADMIN_IDS
            if self._is_admin_id(telegram_id) and not user.is_admin:
                update_data["is_admin"] = True
            if update_data:
                await self.update(user.id, update_data)
            return user
        else:
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name or "Unknown",
                last_name=last_name,
                is_admin=self._is_admin_id(telegram_id),
            )
            self.session.add(user)
            await self.session.flush()
            return user
