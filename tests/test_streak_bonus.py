"""
Tests for streak bonus system + xp_service S-48 Pattern 1 commit semantics.

Split from tests/unit/test_gamification.py::TestStreakBonus per Marina Q5=(b).
"""

import pytest

from src.core.services.xp_service import xp_service
from src.db.models.user import User


class TestStreakBonus:
    """Tests for streak bonus system."""

    @pytest.mark.asyncio
    async def test_streak_bonus_thresholds(self, db_session, user_test_data, monkeypatch):
        """Test streak bonus thresholds."""
        from src.core.services import badge_service as badge_service_module

        # badge_service.award_badge is Pattern 2 (opens own session via
        # async_session_factory) — out of scope for Q6=(i') xp_service
        # refactor. Mock to avoid real-PG attempt for 30+/100+ thresholds.
        async def _mock_award_badge(user_id: int, badge_code: str) -> dict:
            return {"success": True, "badge_code": badge_code}

        monkeypatch.setattr(badge_service_module.badge_service, "award_badge", _mock_award_badge)

        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        result = await xp_service.award_streak_bonus(db_session, user.id, 7)
        assert result["success"] is True
        assert result["xp_awarded"] == 50
        assert result["balance_rub_awarded"] == 10

        result = await xp_service.award_streak_bonus(db_session, user.id, 14)
        assert result["success"] is True
        assert result["xp_awarded"] == 100
        assert result["balance_rub_awarded"] == 25

        result = await xp_service.award_streak_bonus(db_session, user.id, 30)
        assert result["success"] is True
        assert result["xp_awarded"] == 300
        assert result["balance_rub_awarded"] == 100

        result = await xp_service.award_streak_bonus(db_session, user.id, 100)
        assert result["success"] is True
        assert result["xp_awarded"] == 1000
        assert result["balance_rub_awarded"] == 500

    @pytest.mark.asyncio
    async def test_streak_bonus_below_threshold(self, db_session, user_test_data):
        """Test streak bonus below minimum threshold."""
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        result = await xp_service.award_streak_bonus(db_session, user.id, 5)
        assert result.get("skipped") is True


class TestXpServicePattern1:
    """Regression tests for xp_service S-48 Pattern 1 commit semantics.

    Documents that xp_service does NOT own session lifecycle: writes are
    visible after caller commits, no implicit rollback from missing
    internal commit, no internal session.begin() collision.
    """

    @pytest.mark.asyncio
    async def test_add_advertiser_xp_persists_after_commit(self, db_session, advertiser_test_data):
        """add_advertiser_xp writes persist after caller commit (Pattern 1)."""
        from sqlalchemy import select

        user = User(**advertiser_test_data)
        db_session.add(user)
        await db_session.flush()
        user_id = user.id

        new_level, leveled_up = await xp_service.add_advertiser_xp(
            db_session, user_id=user_id, amount=150
        )
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.id == user_id))
        refreshed = result.scalar_one()
        assert refreshed.advertiser_xp == 150
        assert new_level == 2
        assert leveled_up is True

    @pytest.mark.asyncio
    async def test_add_owner_xp_persists_after_commit(self, db_session, owner_test_data):
        """add_owner_xp writes persist after caller commit (Pattern 1)."""
        from sqlalchemy import select

        user = User(**owner_test_data)
        db_session.add(user)
        await db_session.flush()
        user_id = user.id

        new_level, leveled_up = await xp_service.add_owner_xp(
            db_session, user_id=user_id, amount=350
        )
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.id == user_id))
        refreshed = result.scalar_one()
        assert refreshed.owner_xp == 350
        assert new_level == 3
        assert leveled_up is True

    @pytest.mark.asyncio
    async def test_add_xp_pattern1_no_internal_session_begin(self, db_session, user_test_data):
        """add_xp does not open internal transaction — works on autobegun session."""
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Calling add_xp on already-active session must not raise
        # 'A transaction is already begun on this Session.'
        event = await xp_service.add_xp(db_session, user_id=user.id, amount=50, reason="test")
        assert event is None  # below level threshold, no level-up event
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_award_streak_bonus_pattern1_no_internal_commit(self, db_session, user_test_data):
        """award_streak_bonus does not commit internally — caller controls."""
        from sqlalchemy import select

        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()
        user_id = user.id

        result = await xp_service.award_streak_bonus(db_session, user_id, 7)
        assert result["success"] is True

        # Without caller commit, rollback drops the writes.
        await db_session.rollback()
        # Re-create user (rollback wiped) and verify award still works
        # — no leftover uncommitted state from previous call.
        user2 = User(**user_test_data)
        db_session.add(user2)
        await db_session.flush()

        result2 = await xp_service.award_streak_bonus(db_session, user2.id, 14)
        assert result2["success"] is True

        await db_session.commit()
        check = await db_session.execute(select(User).where(User.id == user2.id))
        assert check.scalar_one().advertiser_xp == 100
