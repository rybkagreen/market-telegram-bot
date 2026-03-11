"""
Unit-тесты PlacementRequestRepo.
"""

from decimal import Decimal

import pytest

from src.db.models.placement_request import PlacementStatus


class TestPlacementRequestRepo:
    """Тесты PlacementRequestRepo."""

    @pytest.mark.asyncio
    async def test_get_by_advertiser_filters_status(
        self,
        placement_request_repo,
        advertiser_user,
        test_channel,
        test_campaign,
    ):
        """Фильтр по статусу работает корректно."""
        # Создаём 3 заявки разных статусов
        p1 = await placement_request_repo.create(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Text 1",
        )

        p2 = await placement_request_repo.create(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Text 2",
        )
        await placement_request_repo.update_status(p2.id, PlacementStatus.ESCROW)

        p3 = await placement_request_repo.create(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Text 3",
        )
        await placement_request_repo.update_status(p3.id, PlacementStatus.CANCELLED)

        # Получаем только pending_owner
        result = await placement_request_repo.get_by_advertiser(
            advertiser_user.id,
            status=PlacementStatus.PENDING_OWNER,
        )

        assert len(result) == 1
        assert result[0].id == p1.id

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        placement_request_repo,
        advertiser_user,
        test_channel,
        test_campaign,
    ):
        """Пагинация работает корректно."""
        # Создаём 5 заявок
        for i in range(5):
            await placement_request_repo.create(
                advertiser_id=advertiser_user.id,
                campaign_id=test_campaign.id,
                channel_id=test_channel.id,
                proposed_price=Decimal("500.00"),
                final_text=f"Text {i}",
            )

        # Получаем первые 3
        result = await placement_request_repo.get_by_advertiser(
            advertiser_user.id,
            limit=3,
            offset=0,
        )

        assert len(result) == 3
