"""CampaignRepository for Campaign model operations."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.db.models.campaign import Campaign
from src.db.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    """Репозиторий для работы с кампаниями."""

    model = Campaign

    async def get_by_advertiser(self, advertiser_id: int) -> list[Campaign]:
        """Получить все кампании рекламодателя."""
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.advertiser_id == advertiser_id)
            .options(selectinload(Campaign.placement_requests))
            .order_by(Campaign.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_for_advertiser(self, advertiser_id: int) -> list[Campaign]:
        """Получить активные кампании рекламодателя."""
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.advertiser_id == advertiser_id, Campaign.is_active.is_(True))
            .options(selectinload(Campaign.placement_requests))
            .order_by(Campaign.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_count_for_advertiser(self, advertiser_id: int) -> int:
        """Получить количество активных кампаний рекламодателя."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Campaign)
            .where(Campaign.advertiser_id == advertiser_id, Campaign.is_active.is_(True))
        )
        return result.scalar_one() or 0

    async def get_with_placements(self, campaign_id: int) -> Campaign | None:
        """Получить кампанию с размещениями."""
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .options(selectinload(Campaign.placement_requests))
        )
        return result.scalar_one_or_none()

    async def deactivate(self, campaign_id: int) -> bool:
        """Деактивировать кампанию."""
        campaign = await self.get_by_id(campaign_id)
        if campaign is None:
            return False
        campaign.is_active = False
        await self.session.flush()
        await self.session.refresh(campaign)
        return True
