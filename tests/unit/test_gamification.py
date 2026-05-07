"""
Tests for gamification system (Sprint 8).

Tests cover:
- Badge achievements
- Streak bonuses
- Badge service
"""

import pytest

from src.core.services.badge_service import badge_service
from src.db.models.user import User


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
