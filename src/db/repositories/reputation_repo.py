"""ReputationRepo for reputation score operations."""

from datetime import datetime

from sqlalchemy import select

from src.db.models.reputation_history import ReputationHistory
from src.db.models.reputation_score import ReputationScore
from src.db.repositories.base import BaseRepository


class ReputationRepo(BaseRepository[ReputationScore]):
    """Репозиторий для работы с репутацией."""

    model = ReputationScore

    async def get_by_user(self, user_id: int) -> ReputationScore | None:
        """Получить репутацию пользователя."""
        return await self.session.get(ReputationScore, user_id)

    async def get_or_create(self, user_id: int) -> ReputationScore:
        """Получить или создать репутацию."""
        score = await self.get_by_user(user_id)
        if not score:
            score = ReputationScore(user_id=user_id)
            self.session.add(score)
            await self.session.flush()
        return score

    async def update_score(
        self,
        user_id: int,
        advertiser_score: float | None = None,
        owner_score: float | None = None,
    ) -> ReputationScore:
        """Обновить счёт репутации."""
        score = await self.get_or_create(user_id)
        if advertiser_score is not None:
            score.advertiser_score = advertiser_score
        if owner_score is not None:
            score.owner_score = owner_score
        await self.session.flush()
        return score

    async def set_block(
        self,
        user_id: int,
        role: str,
        blocked_until: datetime,
        violations_count: int,
    ) -> None:
        """Заблокировать пользователя."""
        score = await self.get_or_create(user_id)
        if role == "advertiser":
            score.is_advertiser_blocked = True
            score.advertiser_blocked_until = blocked_until
            score.advertiser_violations_count = violations_count
        else:
            score.is_owner_blocked = True
            score.owner_blocked_until = blocked_until
            score.owner_violations_count = violations_count
        await self.session.flush()

    async def get_history(
        self,
        user_id: int,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ReputationHistory]:
        """Возвращает записи истории репутации для user_id с пагинацией."""
        conditions = [ReputationHistory.user_id == user_id]
        if role is not None:
            conditions.append(ReputationHistory.role == role)
        result = await self.session.execute(
            select(ReputationHistory)
            .where(*conditions)
            .order_by(ReputationHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


ReputationRepository = ReputationRepo
