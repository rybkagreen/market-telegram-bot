"""ActRepository — репозиторий для актов выполненных работ."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.models.act import Act
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ActRepository(BaseRepository[Act]):
    """Репозиторий для работы с актами выполненных работ."""

    model = Act

    async def get_by_placement_request(self, placement_request_id: int) -> Act | None:
        """Получить акт по ID заявки на размещение.

        Args:
            placement_request_id: ID заявки.

        Returns:
            Акт или None.
        """
        result = await self.session.execute(
            select(Act)
            .options(selectinload(Act.placement))
            .where(Act.placement_request_id == placement_request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_act_number(self, act_number: str) -> Act | None:
        """Получить акт по номеру.

        Args:
            act_number: Номер акта (напр. АКТ-2026-0001).

        Returns:
            Акт или None.
        """
        result = await self.session.execute(select(Act).where(Act.act_number == act_number))
        return result.scalar_one_or_none()

    async def list_by_placement_request(self, placement_request_id: int) -> list[Act]:
        """Получить все акты для заявки.

        Args:
            placement_request_id: ID заявки.

        Returns:
            Список актов.
        """
        result = await self.session.execute(
            select(Act)
            .where(Act.placement_request_id == placement_request_id)
            .order_by(Act.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_user(self, user_id: int, limit: int = 50) -> list[Act]:
        """Получить акты пользователя (как рекламодатель или владелец).

        Args:
            user_id: ID пользователя.
            limit: Максимальное количество.

        Returns:
            Список актов.
        """
        from src.db.models.placement_request import PlacementRequest

        result = await self.session.execute(
            select(Act)
            .join(PlacementRequest, Act.placement_request_id == PlacementRequest.id)
            .where(
                (PlacementRequest.advertiser_id == user_id) | (PlacementRequest.owner_id == user_id)
            )
            .order_by(Act.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_pending_signing(self, limit: int = 50) -> list[Act]:
        """Получить акты, ожидающие подписания.

        Args:
            limit: Максимальное количество.

        Returns:
            Список актов со статусом draft/pending.
        """
        result = await self.session.execute(
            select(Act)
            .where(Act.sign_status.in_(["draft", "pending"]))
            .order_by(Act.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
