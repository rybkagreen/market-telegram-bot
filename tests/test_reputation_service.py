"""
Unit-тесты ReputationService.
"""


import pytest

from src.db.models.reputation_history import ReputationAction


class TestReputationService:
    """Тесты ReputationService."""

    @pytest.mark.asyncio
    async def test_on_publication(
        self,
        reputation_service,
        advertiser_user,
    ):
        """Успешная публикация → +1 к репутации."""
        await reputation_service.on_publication(
            advertiser_id=advertiser_user.id,
            owner_id=advertiser_user.id,
            placement_request_id=1,
        )

        rep_score = await reputation_service.reputation_repo.get_by_user(advertiser_user.id)
        assert rep_score.advertiser_score == 6.0
        assert rep_score.owner_score == 6.0

    @pytest.mark.asyncio
    async def test_on_cancel_before(
        self,
        reputation_service,
        advertiser_user,
    ):
        """Отмена до подтверждения → -5 к репутации."""
        await reputation_service.on_advertiser_cancel(
            advertiser_id=advertiser_user.id,
            placement_request_id=1,
            after_confirmation=False,
        )

        rep_score = await reputation_service.reputation_repo.get_by_user(advertiser_user.id)
        assert rep_score.advertiser_score == 0.0  # 5.0 - 5.0 = 0.0 (clamp to min)

    @pytest.mark.asyncio
    async def test_on_invalid_rejection_streak_1(
        self,
        reputation_service,
        owner_user,
    ):
        """Первый невалидный отказ → -10 к репутации."""
        await reputation_service.on_invalid_rejection(
            owner_id=owner_user.id,
            placement_request_id=1,
        )

        rep_score = await reputation_service.reputation_repo.get_by_user(owner_user.id)
        assert rep_score.owner_score == 0.0  # 5.0 - 10.0 = -5.0 (clamp to 0.0)

    @pytest.mark.asyncio
    async def test_history_recorded(
        self,
        reputation_service,
        advertiser_user,
    ):
        """История изменений записывается."""
        await reputation_service.on_publication(
            advertiser_id=advertiser_user.id,
            owner_id=advertiser_user.id,
            placement_request_id=1,
        )

        history = await reputation_service.reputation_repo.get_history(advertiser_user.id)
        assert len(history) >= 1
        assert history[0].action == ReputationAction.PUBLICATION
        assert history[0].delta == 1.0
