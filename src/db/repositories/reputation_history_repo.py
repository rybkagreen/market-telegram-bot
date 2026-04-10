"""ReputationHistoryRepository for ReputationHistory model operations."""

from sqlalchemy import select

from src.db.models.reputation_history import ReputationHistory
from src.db.repositories.base import BaseRepository


class ReputationHistoryRepository(BaseRepository[ReputationHistory]):
    """Репозиторий для работы с историей репутации."""

    model = ReputationHistory

    async def get_by_user_id(self, user_id: int) -> list[ReputationHistory]:
        """Получить всю историю репутации пользователя."""
        result = await self.session.execute(
            select(ReputationHistory)
            .where(ReputationHistory.user_id == user_id)
            .order_by(ReputationHistory.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_batch(self, histories: list[ReputationHistory]) -> None:
        """Массовое добавление записей истории репутации."""
        self.session.add_all(histories)
        await self.session.flush()
        for h in histories:
            await self.session.refresh(h)
