"""
Unit-тесты PlacementRequestService.
"""

from decimal import Decimal

import pytest

from src.db.models.placement_request import PlacementStatus


class TestPlacementRequestService:
    """Тесты PlacementRequestService."""

    @pytest.mark.asyncio
    async def test_create_request_success(
        self,
        placement_request_service,
        advertiser_user,
        test_channel,
        test_campaign,
    ):
        """Advertiser создаёт заявку в активный канал."""
        placement = await placement_request_service.create_request(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Test ad text",
        )

        assert placement.status == PlacementStatus.PENDING_OWNER
        assert placement.proposed_price == Decimal("500.00")
        assert placement.advertiser_id == advertiser_user.id
        assert placement.expires_at is not None

    @pytest.mark.asyncio
    async def test_owner_accept(
        self,
        placement_request_service,
        advertiser_user,
        owner_user,
        test_channel,
        test_campaign,
    ):
        """Владелец принимает заявку → статус pending_payment."""
        placement = await placement_request_service.create_request(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Test ad text",
        )

        placement = await placement_request_service.owner_accept(
            placement_id=placement.id,
            owner_id=owner_user.id,
        )

        assert placement.status == PlacementStatus.PENDING_PAYMENT
        assert placement.final_price == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_owner_counter_offer(
        self,
        placement_request_service,
        advertiser_user,
        owner_user,
        test_channel,
        test_campaign,
    ):
        """Владелец делает контр-предложение → counter_offer_count += 1."""
        placement = await placement_request_service.create_request(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Test ad text",
        )

        placement = await placement_request_service.owner_counter_offer(
            placement_id=placement.id,
            owner_id=owner_user.id,
            proposed_price=Decimal("800.00"),
        )

        assert placement.status == PlacementStatus.COUNTER_OFFER
        assert placement.counter_offer_count == 1
        assert placement.final_price == Decimal("800.00")

    @pytest.mark.asyncio
    async def test_advertiser_accept_counter(
        self,
        placement_request_service,
        advertiser_user,
        owner_user,
        test_channel,
        test_campaign,
    ):
        """Рекламодатель принимает контр-предложение → pending_payment."""
        placement = await placement_request_service.create_request(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Test ad text",
        )

        placement = await placement_request_service.owner_counter_offer(
            placement_id=placement.id,
            owner_id=owner_user.id,
            proposed_price=Decimal("800.00"),
        )

        placement = await placement_request_service.advertiser_accept_counter(
            placement_id=placement.id,
            advertiser_id=advertiser_user.id,
        )

        assert placement.status == PlacementStatus.PENDING_PAYMENT
        assert placement.final_price == Decimal("800.00")
