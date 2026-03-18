"""DisputeRepository for PlacementDispute model operations."""


from sqlalchemy import or_, select

from src.db.models.dispute import DisputeStatus, PlacementDispute
from src.db.repositories.base import BaseRepository


class DisputeRepository(BaseRepository[PlacementDispute]):
    """Репозиторий для работы со спорами."""

    model = PlacementDispute

    async def get_open(self) -> list[PlacementDispute]:
        """Получить все открытые споры."""
        result = await self.session.execute(
            select(PlacementDispute).where(
                PlacementDispute.status.in_([DisputeStatus.open, DisputeStatus.owner_explained])
            ).order_by(PlacementDispute.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_placement(self, placement_request_id: int) -> PlacementDispute | None:
        """Получить спор по заявке."""
        result = await self.session.execute(
            select(PlacementDispute).where(PlacementDispute.placement_request_id == placement_request_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int) -> list[PlacementDispute]:
        """Получить споры пользователя (как рекламодателя или владельца)."""
        result = await self.session.execute(
            select(PlacementDispute).where(
                or_(PlacementDispute.advertiser_id == user_id, PlacementDispute.owner_id == user_id)
            ).order_by(PlacementDispute.created_at.desc())
        )
        return list(result.scalars().all())
