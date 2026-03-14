"""
Reputation Repository для работы с репутацией пользователей.
Расширяет BaseRepository специфичными методами для ReputationScore и ReputationHistory.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.reputation_history import ReputationAction, ReputationHistory
from src.db.models.reputation_score import ReputationScore
from src.db.repositories.base import BaseRepository


class ReputationRepo(BaseRepository[ReputationScore]):
    """
    Репозиторий для работы с репутацией пользователей.
    """

    model = ReputationScore

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_by_user(self, user_id: int) -> ReputationScore | None:
        """
        Получить репутацию пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Репутация пользователя или None.
        """
        return await self.session.get(self.model, user_id)

    async def get_or_create(self, user_id: int) -> ReputationScore:
        """
        Получить или создать с дефолтным score=5.0.

        Args:
            user_id: ID пользователя.

        Returns:
            Репутация пользователя.
        """
        score = await self.get_by_user(user_id)

        if score is not None:
            return score

        # Создаём с дефолтными значениями
        attributes = {
            "user_id": user_id,
            "advertiser_score": 5.0,
            "owner_score": 5.0,
            "advertiser_violations": 0,
            "owner_violations": 0,
            "is_advertiser_blocked": False,
            "is_owner_blocked": False,
        }

        return await self.create(attributes)

    async def update_score(
        self,
        user_id: int,
        role: str,  # "advertiser" или "owner"
        delta: float,
        new_score: float,
    ) -> ReputationScore | None:
        """
        Обновить advertiser_score или owner_score в зависимости от role.
        Обновить updated_at.

        Args:
            user_id: ID пользователя.
            role: Роль ("advertiser" или "owner").
            delta: Изменение score.
            new_score: Новое значение score.

        Returns:
            Обновленная репутация или None.
        """
        score = await self.get_by_user(user_id)
        if score is None:
            return None

        if role == "advertiser":
            score.advertiser_score = new_score
        elif role == "owner":
            score.owner_score = new_score

        score.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(score)
        return score

    async def set_block(
        self,
        user_id: int,
        role: str,
        blocked_until: datetime | None,
        reason: str | None = None,
    ) -> ReputationScore | None:
        """
        Установить блокировку по роли.
        blocked_until=None → снять блокировку (is_*_blocked=False).

        Args:
            user_id: ID пользователя.
            role: Роль ("advertiser" или "owner").
            blocked_until: До какой даты заблокирован.
            reason: Причина блокировки.

        Returns:
            Обновленная репутация или None.
        """
        score = await self.get_by_user(user_id)
        if score is None:
            return None

        if role == "advertiser":
            if blocked_until is None:
                score.is_advertiser_blocked = False
                score.advertiser_blocked_until = None
            else:
                score.is_advertiser_blocked = True
                score.advertiser_blocked_until = blocked_until
        elif role == "owner":
            if blocked_until is None:
                score.is_owner_blocked = False
                score.owner_blocked_until = None
            else:
                score.is_owner_blocked = True
                score.owner_blocked_until = blocked_until

        if reason is not None:
            score.block_reason = reason

        score.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(score)
        return score

    async def increment_violations(self, user_id: int, role: str) -> ReputationScore | None:
        """
        advertiser_violations += 1 или owner_violations += 1.

        Args:
            user_id: ID пользователя.
            role: Роль ("advertiser" или "owner").

        Returns:
            Обновленная репутация или None.
        """
        score = await self.get_by_user(user_id)
        if score is None:
            return None

        if role == "advertiser":
            score.advertiser_violations += 1
        elif role == "owner":
            score.owner_violations += 1

        score.updated_at = datetime.now(UTC)

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
        placement_request_id: int | None = None,
        comment: str | None = None,
    ) -> ReputationHistory:
        """
        Добавить запись в историю репутации.

        Args:
            user_id: ID пользователя.
            action: Тип события.
            delta: Изменение score.
            new_score: Новое значение score.
            role: Роль ("advertiser" или "owner").
            placement_request_id: ID заявки (опционально).
            comment: Комментарий.

        Returns:
            Запись в истории.
        """
        attributes = {
            "user_id": user_id,
            "action": action,
            "delta": delta,
            "new_score": new_score,
            "role": role,
            "placement_request_id": placement_request_id,
            "comment": comment,
        }

        history = ReputationHistory(**attributes)
        self.session.add(history)
        await self.session.flush()
        await self.session.refresh(history)
        return history

    async def get_history(
        self,
        user_id: int,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ReputationHistory]:
        """
        История репутации. Опционально фильтр по роли.

        Args:
            user_id: ID пользователя.
            role: Фильтр по роли.
            limit: Максимальное количество записей.
            offset: Смещение.

        Returns:
            Список записей истории.
        """
        filters = [ReputationHistory.user_id == user_id]
        if role is not None:
            filters.append(ReputationHistory.role == role)

        query = (
            select(ReputationHistory)
            .where(*filters)
            .order_by(ReputationHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(ReputationHistory.placement_request))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_users_with_expired_blocks(self) -> list[ReputationScore]:
        """
        Пользователи у которых истёк срок блокировки (blocked_until < now()).
        Используется Celery-задачей для авто-разблокировки и сброса до 2.0.

        Returns:
            Список репутаций с истёкшей блокировкой.
        """
        now = datetime.now(UTC)

        query = select(self.model).where(
            or_(
                and_(
                    self.model.is_advertiser_blocked,
                    self.model.advertiser_blocked_until < now,
                ),
                and_(
                    self.model.is_owner_blocked,
                    self.model.owner_blocked_until < now,
                ),
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_invalid_rejections_streak(self, user_id: int) -> int:
        """
        Количество последовательных reject_invalid_* записей в истории.
        Используется для правила '3 невалидных отказа подряд → бан'.

        Args:
            user_id: ID пользователя.

        Returns:
            Количество последовательных нарушений.
        """
        # Получаем последние записи истории для owner
        query = (
            select(ReputationHistory)
            .where(
                ReputationHistory.user_id == user_id,
                ReputationHistory.role == "owner",
                ReputationHistory.action.in_(
                    [
                        ReputationAction.REJECT_INVALID_1,
                        ReputationAction.REJECT_INVALID_2,
                        ReputationAction.REJECT_INVALID_3,
                    ]
                ),
            )
            .order_by(ReputationHistory.created_at.desc())
            .limit(10)
        )
        result = await self.session.execute(query)
        history_list = list(result.scalars().all())

        if not history_list:
            return 0

        # Считаем последовательные
        streak = 0
        for record in history_list:
            if record.action in [
                ReputationAction.REJECT_INVALID_1,
                ReputationAction.REJECT_INVALID_2,
                ReputationAction.REJECT_INVALID_3,
            ]:
                streak += 1
            else:
                break

        return streak


# Импортируем or_ для get_users_with_expired_blocks
from sqlalchemy import or_  # noqa: E402
