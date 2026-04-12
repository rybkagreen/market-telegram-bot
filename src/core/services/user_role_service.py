"""UserRoleService — legacy stub (role management removed in v4.5).

Retained for backward compatibility with any remaining imports.
All methods are no-ops or return safe defaults.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User


@dataclass
class UserContext:
    """Контекст пользователя (без role — роль определяется flow)."""

    balance_rub: Decimal
    earned_rub: Decimal
    plan: str


class UserRoleService:
    """Сервис-заглушка. Роль определяется маршрутом (/adv, /own), не полем в БД."""

    async def get_user_context(self, user_id: int, session: AsyncSession) -> UserContext:
        """Получить контекст пользователя."""
        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return UserContext(
            balance_rub=user.balance_rub,
            earned_rub=user.earned_rub,
            plan=user.plan,
        )
