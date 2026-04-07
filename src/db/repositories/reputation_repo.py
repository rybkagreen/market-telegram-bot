"""ReputationRepo for reputation score operations."""

from datetime import datetime

from sqlalchemy import func, select

from src.db.models.reputation_history import ReputationAction, ReputationHistory
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
            await self.session.refresh(score)
        return score

    async def update_score(
        self,
        user_id: int,
        advertiser_score: float | None = None,
        owner_score: float | None = None,
        role: str | None = None,
        new_score: float | None = None,
        delta: float | None = None,
    ) -> ReputationScore:
        """Обновить счёт репутации. Принимает либо advertiser_score/owner_score напрямую,
        либо role + new_score (для вызова из _apply_delta)."""
        score = await self.get_or_create(user_id)
        # Нормализуем: если передан role+new_score, переводим в advertiser_score/owner_score
        if role is not None and new_score is not None:
            if role == "advertiser":
                advertiser_score = new_score
            else:
                owner_score = new_score
        if advertiser_score is not None:
            score.advertiser_score = advertiser_score
        if owner_score is not None:
            score.owner_score = owner_score
        await self.session.flush()
        await self.session.refresh(score)
        return score

    async def add_history(
        self,
        user_id: int,
        action: ReputationAction,
        delta: float,
        new_score: float,
        role: str,
        score_before: float | None = None,
        placement_request_id: int | None = None,
        comment: str | None = None,
    ) -> ReputationHistory:
        """Записать событие в историю репутации."""
        entry = ReputationHistory(
            user_id=user_id,
            role=role,
            action=action,
            delta=delta,
            score_before=score_before if score_before is not None else new_score - delta,
            score_after=new_score,
            placement_request_id=placement_request_id,
            description=comment,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def increment_violations(self, user_id: int, role: str) -> None:
        """Увеличить счётчик нарушений."""
        score = await self.get_or_create(user_id)
        if role == "advertiser":
            score.advertiser_violations_count += 1
        else:
            score.owner_violations_count += 1
        await self.session.flush()

    async def set_block(
        self,
        user_id: int,
        role: str,
        blocked_until: datetime | None,
        violations_count: int | None = None,
        reason: str | None = None,
    ) -> None:
        """Заблокировать пользователя."""
        score = await self.get_or_create(user_id)
        if role == "advertiser":
            score.is_advertiser_blocked = True
            score.advertiser_blocked_until = blocked_until
            if violations_count is not None:
                score.advertiser_violations_count = violations_count
        else:
            score.is_owner_blocked = True
            score.owner_blocked_until = blocked_until
            if violations_count is not None:
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

    async def count_invalid_rejections_streak(self, owner_id: int) -> int:
        """Посчитать количество подряд идущих невалидных отказов."""
        result = await self.session.execute(
            select(func.count(ReputationHistory.id)).where(
                ReputationHistory.user_id == owner_id,
                ReputationHistory.role == "owner",
                ReputationHistory.action.in_(
                    [
                        ReputationAction.reject_invalid_1,
                        ReputationAction.reject_invalid_2,
                        ReputationAction.reject_invalid_3,
                    ]
                ),
            )
        )
        return result.scalar() or 0


ReputationRepository = ReputationRepo
