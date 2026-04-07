"""UserRoleService for user role management."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User


@dataclass
class UserContext:
    """Контекст пользователя для проверки прав."""

    role: str
    balance_rub: Decimal
    earned_rub: Decimal
    plan: str


class UserRoleService:
    """Сервис определения и управления ролью пользователя."""

    async def get_role(self, user_id: int, session: AsyncSession) -> str:
        """Получить роль пользователя."""
        user = await session.get(User, user_id)
        if not user:
            return "new"
        return user.current_role

    async def set_role(self, user_id: int, role: str, session: AsyncSession) -> None:
        """Установить роль пользователя."""
        valid_roles = {"new", "advertiser", "owner", "both"}
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        user.current_role = role
        await session.flush()

    async def get_user_context(self, user_id: int, session: AsyncSession) -> UserContext:
        """Получить контекст пользователя."""
        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return UserContext(
            role=user.current_role,
            balance_rub=user.balance_rub,
            earned_rub=user.earned_rub,
            plan=user.plan,
        )
