"""BadgeRepository for Badge model operations."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.db.models.badge import Badge, UserBadge
from src.db.repositories.base import BaseRepository


class BadgeRepository(BaseRepository[Badge]):
    """Репозиторий для работы с достижениями."""

    model = Badge

    async def get_all_active(self) -> list[Badge]:
        """Получить все активные достижения."""
        result = await self.session.execute(
            select(Badge).where(Badge.is_active.is_(True)).order_by(Badge.sort_order)
        )
        return list(result.scalars().all())

    async def get_user_badges(self, user_id: int) -> list[UserBadge]:
        """Получить достижения пользователя."""
        result = await self.session.execute(
            select(UserBadge)
            .where(UserBadge.user_id == user_id)
            .options(selectinload(UserBadge.badge))
            .order_by(UserBadge.earned_at.desc())
        )
        return list(result.scalars().all())

    async def has_badge(self, user_id: int, badge_id: int) -> bool:
        """Проверить, есть ли достижение у пользователя."""
        result = await self.session.execute(
            select(func.count())
            .select_from(UserBadge)
            .where(UserBadge.user_id == user_id, UserBadge.badge_id == badge_id)
        )
        return (result.scalar_one() or 0) > 0

    async def award_badge(self, user_id: int, badge_id: int) -> UserBadge | None:
        """Выдать достижение пользователю."""
        if await self.has_badge(user_id, badge_id):
            return None
        user_badge = UserBadge(user_id=user_id, badge_id=badge_id, earned_at=datetime.now(UTC))
        self.session.add(user_badge)
        await self.session.flush()
        await self.session.refresh(user_badge)
        return user_badge

    async def get_recent_earners(self, badge_id: int, limit: int = 10) -> list[UserBadge]:
        """Получить последних получателей достижения."""
        result = await self.session.execute(
            select(UserBadge)
            .where(UserBadge.badge_id == badge_id)
            .options(selectinload(UserBadge.user))
            .order_by(UserBadge.earned_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
