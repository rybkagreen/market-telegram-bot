"""
Tests for gamification system (Sprint 8).

Tests cover:
- Badge achievements
- Streak bonuses
- Badge service
"""

import pytest
from sqlalchemy import select

from src.core.services.badge_service import badge_service
from src.db.models.badge import UserBadge
from src.db.models.user import User


@pytest.mark.skip(reason="Badge model refactored in v4.3, only UserBadge exists")
class TestBadgeAchievementModel:
    """Tests for BadgeAchievement model."""

    @pytest.mark.asyncio
    async def test_badge_achievement_creation(self, db_session):
        """Test creating a badge achievement."""
        # Create badge
        badge = Badge(
            code="first_campaign",
            name="Первая кампания",
            description="Запуск первой рекламной кампании",
            icon_emoji="🚀",
            xp_reward=200,
            credits_reward=50,
            category=BadgeCategory.ADVERTISER,
            condition_type=BadgeConditionType.CAMPAIGNS_COUNT,
            condition_value=1,
        )
        db_session.add(badge)
        await db_session.flush()

        # Create achievement
        achievement = BadgeAchievement(
            badge_id=badge.id,
            achievement_type="campaign_count",
            threshold=1,
            description="Запуск первой кампании",
            is_active=True,
        )
        db_session.add(achievement)
        await db_session.commit()

        # Verify
        result = await db_session.execute(select(BadgeAchievement).where(BadgeAchievement.badge_id == badge.id))
        saved = result.scalar_one()

        assert saved is not None
        assert saved.achievement_type == "campaign_count"
        assert saved.threshold == 1
        assert saved.is_active is True


class TestBadgeService:
    """Tests for BadgeService."""

    @pytest.mark.asyncio
    async def test_get_or_create_mediakit_for_user(self, db_session, user_test_data):
        """Test getting user badges."""
        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Get badges (should be empty)
        badges = await badge_service.get_user_badges(user.id)

        assert isinstance(badges, list)
        assert len(badges) == 0


class TestStreakBonus:
    """Tests for streak bonus system."""

    @pytest.mark.asyncio
    async def test_streak_bonus_thresholds(self, db_session, user_test_data):
        """Test streak bonus thresholds."""
        from src.core.services.xp_service import xp_service

        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Test 7 days streak
        result = await xp_service.award_streak_bonus(user.id, 7)
        assert result["success"] is True
        assert result["xp_awarded"] == 50
        assert result["credits_awarded"] == 10

        # Test 14 days streak
        result = await xp_service.award_streak_bonus(user.id, 14)
        assert result["success"] is True
        assert result["xp_awarded"] == 100
        assert result["credits_awarded"] == 25

        # Test 30 days streak
        result = await xp_service.award_streak_bonus(user.id, 30)
        assert result["success"] is True
        assert result["xp_awarded"] == 300
        assert result["credits_awarded"] == 100

        # Test 100 days streak
        result = await xp_service.award_streak_bonus(user.id, 100)
        assert result["success"] is True
        assert result["xp_awarded"] == 1000
        assert result["credits_awarded"] == 500

    @pytest.mark.asyncio
    async def test_streak_bonus_below_threshold(self, db_session, user_test_data):
        """Test streak bonus below minimum threshold."""
        from src.core.services.xp_service import xp_service

        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Test 5 days (below 7 days threshold)
        result = await xp_service.award_streak_bonus(user.id, 5)
        assert result.get("skipped") is True


class TestCategorySubcategory:
    """Tests for category/subcategory classification."""

    @pytest.mark.asyncio
    async def test_classify_subcategory_it(self):
        """Test IT subcategory classification."""
        from src.utils.categories import classify_subcategory

        # Test programming
        subcat = classify_subcategory(
            title="Python Programming",
            description="Python programming tutorials and tips",
            topic="it",
        )
        assert subcat == "programming"

        # Test devops
        subcat = classify_subcategory(
            title="DevOps Channel",
            description="Docker, Kubernetes, CI/CD",
            topic="it",
        )
        assert subcat == "devops"

    @pytest.mark.asyncio
    async def test_classify_subcategory_business(self):
        """Test business subcategory classification."""
        from src.utils.categories import classify_subcategory

        # Test startup
        subcat = classify_subcategory(
            title="Startup News",
            description="Startup innovations and funding",
            topic="business",
        )
        assert subcat == "startup"

        # Test real estate
        subcat = classify_subcategory(
            title="Real Estate",
            description="Apartments, houses, mortgage",
            topic="business",
        )
        assert subcat == "real_estate"

    @pytest.mark.asyncio
    async def test_classify_subcategory_health(self):
        """Test health subcategory classification."""
        from src.utils.categories import classify_subcategory

        # Test medicine
        subcat = classify_subcategory(
            title="Health Channel",
            description="Medicine, doctors, treatment",
            topic="health",
        )
        assert subcat == "medicine"

        # Test fitness
        subcat = classify_subcategory(
            title="Fitness",
            description="Sport, workouts, gym",
            topic="health",
        )
        assert subcat == "fitness"

    @pytest.mark.asyncio
    async def test_classify_subcategory_russian_topic(self):
        """Test classification with Russian topic."""
        from src.utils.categories import classify_subcategory

        # Test Russian topic mapping
        subcat = classify_subcategory(
            title="Здоровье",
            description="Медицина, врачи, лечение",
            topic="здоровье",
        )
        assert subcat == "medicine"


class TestSubcategoriesFromDB:
    """Tests for get_subcategories_from_db."""

    @pytest.mark.asyncio
    async def test_get_subcategories_from_db(self):
        """Test getting subcategories from database."""
        from src.utils.categories import get_subcategories_from_db

        # Test IT subcategories
        subcats = await get_subcategories_from_db("it")
        assert subcats is not None
        assert "programming" in subcats
        assert "devops" in subcats

        # Test business subcategories
        subcats = await get_subcategories_from_db("business")
        assert subcats is not None
        assert "startup" in subcats
        assert "real_estate" in subcats
