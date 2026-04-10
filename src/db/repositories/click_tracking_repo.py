"""ClickTrackingRepository for ClickTracking model operations."""

from datetime import UTC, datetime

from sqlalchemy import func, select, update

from src.db.models.click_tracking import ClickTracking
from src.db.repositories.base import BaseRepository


class ClickTrackingRepository(BaseRepository[ClickTracking]):
    """Репозиторий для работы с трекингом кликов."""

    model = ClickTracking

    async def get_by_campaign(self, campaign_id: int) -> list[ClickTracking]:
        """Получить все трекинг-записи кампании."""
        result = await self.session.execute(
            select(ClickTracking)
            .where(ClickTracking.campaign_id == campaign_id)
            .order_by(ClickTracking.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_placement(self, placement_request_id: int) -> ClickTracking | None:
        """Получить трекинг-запись размещения."""
        result = await self.session.execute(
            select(ClickTracking).where(ClickTracking.placement_request_id == placement_request_id)
        )
        return result.scalar_one_or_none()

    async def increment_clicks(self, tracking_id: int) -> int:
        """Увеличить счётчик кликов."""
        stmt = (
            update(ClickTracking)
            .where(ClickTracking.id == tracking_id)
            .values(
                click_count=ClickTracking.click_count + 1,
                last_clicked_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_total_clicks_for_campaign(self, campaign_id: int) -> int:
        """Получить общее количество кликов по кампании."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(ClickTracking.click_count), 0)).where(
                ClickTracking.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0)

    async def get_total_unique_for_campaign(self, campaign_id: int) -> int:
        """Получить количество уникальных кликов по кампании."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(ClickTracking.unique_clicks), 0)).where(
                ClickTracking.campaign_id == campaign_id
            )
        )
        return int(result.scalar_one() or 0)
