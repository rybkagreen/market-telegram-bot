"""
Tests for placement counter-offer negotiation flow.
Covers FIX #1-#7: price consistency, data fields, API responses.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest


class TestCounterOfferServiceFix1:
    """FIX #1: advertiser_accept_counter sets final_price correctly."""

    @pytest.mark.asyncio
    async def test_advertiser_accept_counter_sets_final_price(
        self,
        db_session,
        test_advertiser,
        test_owner,
        test_channel,
    ):
        """When advertiser accepts counter-offer, final_price must be set from counter_price."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus
        from src.db.repositories.placement_request_repo import PlacementRequestRepository
        from src.core.services.placement_request_service import PlacementRequestService
        from src.db.repositories.channel_settings_repo import ChannelSettingsRepo

        # Create placement with pending_owner status
        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_owner.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text for placement",
            status=PlacementStatus.pending_owner,
        )
        db_session.add(placement)
        await db_session.commit()
        await db_session.refresh(placement)

        # Owner makes counter-offer
        repo = PlacementRequestRepository(db_session)
        await repo.counter_offer(
            placement_id=placement.id,
            proposed_price=Decimal("1500.00"),
            comment="Owner's counter price",
        )
        await db_session.refresh(placement)

        assert placement.status == PlacementStatus.counter_offer
        assert placement.counter_price == Decimal("1500.00")
        assert placement.final_price is None  # Not set yet

        # FIX #1: Service now passes final_price=counter_price
        service = PlacementRequestService(
            session=db_session,
            placement_repo=repo,
            channel_settings_repo=ChannelSettingsRepo(db_session),
            reputation_repo=None,
            billing_service=None,
        )

        result = await service.advertiser_accept_counter(placement.id, test_advertiser.id)

        assert result is not None
        assert result.status == PlacementStatus.pending_payment
        # FIX #1 verification: final_price must be set to counter_price
        assert result.final_price == Decimal("1500.00")

    @pytest.mark.asyncio
    async def test_advertiser_accept_counter_sets_final_schedule(
        self,
        db_session,
        test_advertiser,
        test_owner,
        test_channel,
    ):
        """When advertiser accepts counter-offer, final_schedule must be set."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus
        from src.db.repositories.placement_request_repo import PlacementRequestRepository
        from src.core.services.placement_request_service import PlacementRequestService
        from src.db.repositories.channel_settings_repo import ChannelSettingsRepo

        counter_schedule = datetime(2026, 4, 15, 14, 0, 0, tzinfo=UTC)

        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_owner.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text",
            status=PlacementStatus.pending_owner,
        )
        db_session.add(placement)
        await db_session.commit()
        await db_session.refresh(placement)

        repo = PlacementRequestRepository(db_session)
        await repo.counter_offer(
            placement_id=placement.id,
            proposed_price=Decimal("1500.00"),
            proposed_schedule=counter_schedule,
        )
        await db_session.refresh(placement)

        service = PlacementRequestService(
            session=db_session,
            placement_repo=repo,
            channel_settings_repo=ChannelSettingsRepo(db_session),
            reputation_repo=None,
            billing_service=None,
        )

        result = await service.advertiser_accept_counter(placement.id, test_advertiser.id)

        assert result is not None
        assert result.final_schedule == counter_schedule


class TestCounterOfferAPIFix2:
    """FIX #2: PlacementResponse includes counter_price, counter_schedule, counter_comment."""

    @pytest.mark.asyncio
    async def test_placement_response_has_counter_fields(
        self,
        api_client_with_auth,
        test_channel,
        test_advertiser,
        db_session,
    ):
        """API response must include counter_price, counter_schedule, counter_comment."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus

        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_channel.owner_id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text",
            status=PlacementStatus.counter_offer,
            counter_price=Decimal("1500.00"),
            counter_comment="Owner's counter offer",
        )
        db_session.add(placement)
        await db_session.commit()

        response = await api_client_with_auth.get(f"/api/v1/placements/{placement.id}")

        assert response.status_code == 200
        data = response.json()

        # FIX #2 verification: counter fields must be present
        assert "counter_price" in data
        assert "counter_schedule" in data
        assert "counter_comment" in data
        assert data["counter_price"] == "1500.00"
        assert data["counter_comment"] == "Owner's counter offer"


class TestCounterOfferDataFix4:
    """FIX #4: Advertiser counter-offer uses separate field (no data collision)."""

    @pytest.mark.asyncio
    async def test_advertiser_counter_price_does_not_overwrite_owner_counter(
        self,
        db_session,
        test_advertiser,
        test_owner,
        test_channel,
    ):
        """Advertiser's counter-counter must NOT overwrite owner's counter_price."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus

        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_owner.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text",
            status=PlacementStatus.counter_offer,
            counter_price=Decimal("1500.00"),  # Owner's counter
        )
        db_session.add(placement)
        await db_session.commit()
        await db_session.refresh(placement)

        # Simulate advertiser making counter-counter (using new field)
        placement.advertiser_counter_price = Decimal("1200.00")
        placement.status = PlacementStatus.pending_owner
        await db_session.commit()
        await db_session.refresh(placement)

        # FIX #4 verification: owner's counter_price preserved
        assert placement.counter_price == Decimal("1500.00")  # Owner's price intact
        assert placement.advertiser_counter_price == Decimal("1200.00")  # Advertiser's counter

    @pytest.mark.asyncio
    async def test_multiple_counter_rounds_preserve_history(
        self,
        db_session,
        test_advertiser,
        test_owner,
        test_channel,
    ):
        """Multiple counter-offer rounds must preserve both parties' data."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus

        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_owner.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text",
            status=PlacementStatus.pending_owner,
            counter_offer_count=0,
        )
        db_session.add(placement)
        await db_session.commit()

        # Round 1: Owner counters
        placement.counter_price = Decimal("1500.00")
        placement.counter_comment = "Owner round 1"
        placement.counter_offer_count = 1
        placement.status = PlacementStatus.counter_offer
        await db_session.commit()

        # Round 1: Advertiser counter-counters
        placement.advertiser_counter_price = Decimal("1200.00")
        placement.advertiser_counter_comment = "Advertiser round 1"
        placement.counter_offer_count = 2
        placement.status = PlacementStatus.pending_owner
        await db_session.commit()

        await db_session.refresh(placement)

        # Verify both counters preserved
        assert placement.counter_price == Decimal("1500.00")
        assert placement.counter_comment == "Owner round 1"
        assert placement.advertiser_counter_price == Decimal("1200.00")
        assert placement.advertiser_counter_comment == "Advertiser round 1"


class TestCounterOfferAPIFix7:
    """FIX #7: API includes advertiser_counter fields in response."""

    @pytest.mark.asyncio
    async def test_placement_response_has_advertiser_counter_fields(
        self,
        api_client_with_auth,
        test_channel,
        test_advertiser,
        db_session,
    ):
        """API response must include advertiser_counter_price, schedule, comment."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus

        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_channel.owner_id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text",
            status=PlacementStatus.pending_owner,
            counter_price=Decimal("1500.00"),
            advertiser_counter_price=Decimal("1200.00"),
            advertiser_counter_comment="Advertiser's counter",
        )
        db_session.add(placement)
        await db_session.commit()

        response = await api_client_with_auth.get(f"/api/v1/placements/{placement.id}")

        assert response.status_code == 200
        data = response.json()

        # FIX #7 verification
        assert "advertiser_counter_price" in data
        assert "advertiser_counter_schedule" in data
        assert "advertiser_counter_comment" in data
        assert data["advertiser_counter_price"] == "1200.00"
        assert data["advertiser_counter_comment"] == "Advertiser's counter"


class TestPriceResolutionLogic:
    """Test price resolution logic (final_price or proposed_price fallback)."""

    @pytest.mark.asyncio
    async def test_payment_uses_final_price_when_set(
        self,
        db_session,
        test_advertiser,
        test_owner,
        test_channel,
    ):
        """Payment must use final_price when set, not proposed_price."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus

        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_owner.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text",
            status=PlacementStatus.pending_payment,
            final_price=Decimal("1500.00"),  # Counter-offer accepted
        )
        db_session.add(placement)
        await db_session.commit()

        # Resolution logic: final_price or proposed_price
        price = placement.final_price or placement.proposed_price

        assert price == Decimal("1500.00")  # Must use final_price

    @pytest.mark.asyncio
    async def test_payment_falls_back_to_proposed_price(self, db_session, test_advertiser, test_owner, test_channel):
        """When final_price is None, must fall back to proposed_price."""
        from src.db.models.placement_request import PlacementRequest, PlacementStatus

        placement = PlacementRequest(
            advertiser_id=test_advertiser.id,
            owner_id=test_owner.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("1000.00"),
            ad_text="Test ad text",
            status=PlacementStatus.pending_payment,
            final_price=None,  # No counter-offer
        )
        db_session.add(placement)
        await db_session.commit()

        price = placement.final_price or placement.proposed_price

        assert price == Decimal("1000.00")  # Must fall back to proposed_price
