"""
Integration-тесты API /api/v1/placements.
"""

from decimal import Decimal

import pytest


class TestAPIPlacements:
    """Тесты API placements."""

    @pytest.mark.asyncio
    async def test_create_placement_201(
        self,
        api_client_with_auth,
        test_channel,
        test_campaign,
    ):
        """Создание заявки → 201."""
        response = await api_client_with_auth.post(
            "/api/v1/placements/",
            json={
                "channel_id": test_channel.id,
                "proposed_price": 500,
                "post_text": "Test ad text for placement",
                "scheduled_at": "2026-03-15T10:00:00Z",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending_owner"

    @pytest.mark.asyncio
    async def test_create_placement_422_short_text(
        self,
        api_client_with_auth,
        test_channel,
        test_campaign,
    ):
        """Текст короче 10 символов → 422."""
        response = await api_client_with_auth.post(
            "/api/v1/placements/",
            json={
                "channel_id": test_channel.id,
                "proposed_price": 500,
                "post_text": "Short",  # 5 символов
                "scheduled_at": "2026-03-15T10:00:00Z",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_placement_422_low_price(
        self,
        api_client_with_auth,
        test_channel,
        test_campaign,
    ):
        """Цена меньше 100 → 422."""
        response = await api_client_with_auth.post(
            "/api/v1/placements/",
            json={
                "channel_id": test_channel.id,
                "proposed_price": 50,  # < 100
                "post_text": "Test ad text for placement",
                "scheduled_at": "2026-03-15T10:00:00Z",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_placements(
        self,
        api_client_with_auth,
        test_channel,
        test_campaign,
        advertiser_user,
        db_session,
    ):
        """Список заявок → 200."""
        from src.db.repositories.placement_request_repo import PlacementRequestRepo

        # Создаём заявку через репо
        repo = PlacementRequestRepo(db_session)
        await repo.create(
            advertiser_id=advertiser_user.id,
            campaign_id=test_campaign.id,
            channel_id=test_channel.id,
            proposed_price=Decimal("500.00"),
            final_text="Test text",
        )

        response = await api_client_with_auth.get("/api/v1/placements/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
