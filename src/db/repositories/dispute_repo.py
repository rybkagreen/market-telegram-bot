"""DisputeRepository for PlacementDispute model operations."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.db.models.dispute import DisputeStatus, PlacementDispute
from src.db.repositories.base import BaseRepository


class DisputeRepository(BaseRepository[PlacementDispute]):
    """Репозиторий для работы со спорами."""

    model = PlacementDispute

    async def get_open(self) -> list[PlacementDispute]:
        """Получить все открытые споры."""
        result = await self.session.execute(
            select(PlacementDispute)
            .where(PlacementDispute.status.in_([DisputeStatus.open, DisputeStatus.owner_explained]))
            .order_by(PlacementDispute.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_placement(self, placement_request_id: int) -> PlacementDispute | None:
        """Получить спор по заявке."""
        result = await self.session.execute(
            select(PlacementDispute)
            .where(PlacementDispute.placement_request_id == placement_request_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int) -> list[PlacementDispute]:
        """Получить споры пользователя (как рекламодателя или владельца)."""
        result = await self.session.execute(
            select(PlacementDispute)
            .where(
                or_(PlacementDispute.advertiser_id == user_id, PlacementDispute.owner_id == user_id)
            )
            .order_by(PlacementDispute.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_paginated(
        self,
        user_id: int,
        status_filter: str = "all",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PlacementDispute], int]:
        """
        Получить споры пользователя с пагинацией и фильтрацией по статусу.

        Returns:
            (disputes, total_count)
        """
        base_query = select(PlacementDispute).where(
            or_(PlacementDispute.advertiser_id == user_id, PlacementDispute.owner_id == user_id)
        )

        if status_filter != "all":
            try:
                status_enum = DisputeStatus(status_filter.lower())
                base_query = base_query.where(PlacementDispute.status == status_enum)
            except ValueError:
                pass  # invalid filter — return all

        # Total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Paginated results
        query = base_query.order_by(PlacementDispute.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        disputes = list(result.scalars().all())

        return disputes, total

    async def get_all_paginated(
        self,
        status_filter: DisputeStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PlacementDispute], int]:
        """
        Получить все споры с пагинацией и опциональным фильтром по статусу (admin).

        Returns:
            (disputes, total_count)
        """
        base_query = select(PlacementDispute)

        if status_filter is not None:
            base_query = base_query.where(PlacementDispute.status == status_filter)

        # Total count — count on the unloaded query (no eager joins)
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Paginated results with eager-load of advertiser/owner to avoid
        # async lazy-load (MissingGreenlet → 500) when router accesses
        # d.advertiser.username / d.owner.username.
        query = (
            base_query.options(
                selectinload(PlacementDispute.advertiser),
                selectinload(PlacementDispute.owner),
            )
            .order_by(PlacementDispute.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        disputes = list(result.scalars().all())

        return disputes, total
