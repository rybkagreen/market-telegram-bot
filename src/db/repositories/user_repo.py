"""UserRepository for User model operations."""

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from src.config.settings import settings
from src.db.models.user import User
from src.db.models.yookassa_payment import YookassaPayment
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

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        """Получить пользователя по referral_code."""
        result = await self.session.execute(select(User).where(User.referral_code == referral_code))
        return result.scalar_one_or_none()

    async def get_all_admins(self) -> list[User]:
        """Получить всех администраторов платформы."""
        result = await self.session.execute(select(User).where(User.is_admin).order_by(User.id))
        return list(result.scalars().all())

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
        await self.session.refresh(user)
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

    async def get_total_balance_sum(self) -> Decimal:
        """Получить сумму balance_rub всех пользователей."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(User.balance_rub), Decimal("0")))
        )
        return result.scalar_one() or Decimal("0")

    async def get_total_earned_sum(self) -> Decimal:
        """Получить сумму earned_rub всех пользователей."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(User.earned_rub), Decimal("0")))
        )
        return result.scalar_one() or Decimal("0")

    def _build_update_fields(
        self,
        user: User,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> dict[str, Any]:
        """Build dict of fields that need updating for an existing user."""
        data: dict[str, Any] = {}
        if username is not None and username != user.username:
            data["username"] = username
        if first_name is not None and first_name != user.first_name:
            data["first_name"] = first_name
        if last_name is not None and last_name != user.last_name:
            data["last_name"] = last_name
        if self._is_admin_id(telegram_id) and not user.is_admin:
            data["is_admin"] = True
        return data

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
            update_data = self._build_update_fields(
                user, telegram_id, username, first_name, last_name
            )
            if update_data:
                await self.update(user.id, update_data)
            return user

        # Create new user
        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name or "Unknown",
            last_name=last_name,
            is_admin=self._is_admin_id(telegram_id),
            referral_code=f"ref_{telegram_id}",
        )
        self.session.add(new_user)
        await self.session.flush()
        await self.session.refresh(new_user)
        return new_user

    async def update_balance_rub(self, user_id: int, delta: Decimal) -> User | None:
        """Атомарно обновляет поле balance_rub пользователя на delta (может быть отрицательным)."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.balance_rub += delta
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def count_referrals(self, user_id: int) -> int:
        """Посчитать количество рефералов пользователя."""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.referred_by_id == user_id)
        )
        return result.scalar_one() or 0

    async def get_referrals(self, user_id: int, limit: int = 20, offset: int = 0) -> list[User]:
        """Получить список рефералов пользователя (по referred_by_id)."""
        result = await self.session.execute(
            select(User)
            .where(User.referred_by_id == user_id)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_active_referrals(self, user_id: int) -> int:
        """Посчитать активных рефералов (тех, у кого есть succeeded платёж)."""
        result = await self.session.execute(
            select(func.count(User.id))
            .join(YookassaPayment, User.id == YookassaPayment.user_id)
            .where(
                User.referred_by_id == user_id,
                YookassaPayment.status == "succeeded",
            )
        )
        return result.scalar_one() or 0

    async def sum_referral_earnings(self, user_id: int) -> Decimal:
        """Получить сумму desired_balance от успешных платежей рефералов."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(YookassaPayment.desired_balance), Decimal("0")))
            .join(User, User.id == YookassaPayment.user_id)
            .where(
                User.referred_by_id == user_id,
                YookassaPayment.status == "succeeded",
            )
        )
        return result.scalar_one() or Decimal("0")

    async def has_successful_payment(self, user_id: int) -> bool:
        """Проверить, есть ли у пользователя хотя бы один успешный платёж."""
        result = await self.session.execute(
            select(YookassaPayment.id)
            .where(
                YookassaPayment.user_id == user_id,
                YookassaPayment.status == "succeeded",
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
