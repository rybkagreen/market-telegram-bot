"""
Tests for channel mediakit and comparison (Sprint 9-10).

Tests cover:
- Channel mediakit model
- Mediakit service
- Channel comparison service
- PDF generation
"""

import pytest
from sqlalchemy import select

from src.core.services.comparison_service import comparison_service
from src.core.services.mediakit_service import mediakit_service
from src.db.models.telegram_chat import TelegramChat
from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.user import User


class TestChannelMediakitModel:
    """Tests for ChannelMediakit model."""

    @pytest.mark.asyncio
    async def test_mediatkit_creation(self, db_session, user_test_data, chat_test_data):
        """Test creating a channel mediakit."""
        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Create chat
        chat = TelegramChat(**chat_test_data, owner_user_id=user.id)
        db_session.add(chat)
        await db_session.flush()

        # Create mediakit
        mediakit = ChannelMediakit(
            channel_id=chat.id,
            owner_user_id=user.id,
            custom_description="Custom channel description",
            logo_file_id="AgACAgIAAxkBAAIC",
            theme_color="#1a73e8",
            is_public=True,
        )
        db_session.add(mediakit)
        await db_session.commit()

        # Verify
        result = await db_session.execute(select(ChannelMediakit).where(ChannelMediakit.channel_id == chat.id))
        saved = result.scalar_one()

        assert saved is not None
        assert saved.custom_description == "Custom channel description"
        assert saved.theme_color == "#1a73e8"
        assert saved.is_public is True


class TestMediakitService:
    """Tests for MediakitService."""

    @pytest.mark.asyncio
    async def test_get_or_create_mediatkit(self, db_session, user_test_data, chat_test_data):
        """Test get or create mediakit."""
        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Create chat
        chat = TelegramChat(**chat_test_data, owner_user_id=user.id)
        db_session.add(chat)
        await db_session.flush()

        # Get or create mediakit
        mediakit = await mediakit_service.get_or_create_mediakit(chat.id)

        assert mediakit is not None
        assert mediakit.channel_id == chat.id
        assert mediakit.owner_user_id == user.id

    @pytest.mark.asyncio
    async def test_update_mediatkit(self, db_session, user_test_data, chat_test_data):
        """Test updating mediakit."""
        # Create user and chat
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        chat = TelegramChat(**chat_test_data, owner_user_id=user.id)
        db_session.add(chat)
        await db_session.flush()

        # Create mediakit
        mediakit = await mediakit_service.get_or_create_mediakit(chat.id)

        # Update
        updates = {
            "custom_description": "Updated description",
            "theme_color": "#ff0000",
            "is_public": False,
        }
        updated = await mediakit_service.update_mediakit(mediakit.id, user.id, updates)

        assert updated.custom_description == "Updated description"
        assert updated.theme_color == "#ff0000"
        assert updated.is_public is False

    @pytest.mark.asyncio
    async def test_get_mediatkit_data(self, db_session, user_test_data, chat_test_data):
        """Test getting mediakit data."""
        # Create user and chat
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        chat = TelegramChat(
            **chat_test_data,
            owner_user_id=user.id,
            member_count=10000,
            last_avg_views=1500,
            last_er=15.0,
            last_post_frequency=2.5,
            price_per_post=500,
        )
        db_session.add(chat)
        await db_session.flush()

        # Get mediakit data
        data = await mediakit_service.get_mediakit_data(chat.id)

        assert "channel" in data
        assert "mediakit" in data
        assert "metrics" in data
        assert "price" in data

        assert data["metrics"]["subscribers"] == 10000
        assert data["metrics"]["avg_views"] == 1500
        assert data["metrics"]["er"] == 15.0


class TestComparisonService:
    """Tests for ComparisonService."""

    @pytest.mark.asyncio
    async def test_get_channels_for_comparison(self, db_session, user_test_data):
        """Test getting channels for comparison."""
        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Create test channels
        channels_data = [
            {"username": "channel1", "title": "Channel 1", "member_count": 10000, "topic": "it"},
            {"username": "channel2", "title": "Channel 2", "member_count": 15000, "topic": "it"},
            {"username": "channel3", "title": "Channel 3", "member_count": 8000, "topic": "it"},
        ]

        channel_ids = []
        for ch_data in channels_data:
            chat = TelegramChat(**ch_data, owner_user_id=user.id, is_active=True)
            db_session.add(chat)
            await db_session.flush()
            channel_ids.append(chat.id)

        # Get channels for comparison
        channels = await comparison_service.get_channels_for_comparison(channel_ids)

        assert len(channels) == 3
        assert channels[0]["member_count"] == 10000
        assert channels[1]["member_count"] == 15000
        assert channels[2]["member_count"] == 8000

    @pytest.mark.asyncio
    async def test_calculate_comparison_metrics(self, db_session, user_test_data):
        """Test calculating comparison metrics."""
        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Create test channels with different metrics
        channels_data = [
            {
                "username": "channel1",
                "title": "Channel 1",
                "member_count": 10000,
                "topic": "it",
                "last_avg_views": 1500,
                "last_er": 15.0,
                "last_post_frequency": 2.0,
                "price_per_post": 500,
            },
            {
                "username": "channel2",
                "title": "Channel 2",
                "member_count": 15000,
                "topic": "it",
                "last_avg_views": 2000,
                "last_er": 13.3,
                "last_post_frequency": 3.0,
                "price_per_post": 700,
            },
        ]

        channel_ids = []
        for ch_data in channels_data:
            chat = TelegramChat(**ch_data, owner_user_id=user.id, is_active=True)
            db_session.add(chat)
            await db_session.flush()
            channel_ids.append(chat.id)

        # Get channels and calculate metrics
        channels = await comparison_service.get_channels_for_comparison(channel_ids)
        comparison = comparison_service.calculate_comparison_metrics(channels)

        assert "channels" in comparison
        assert "best_values" in comparison
        assert "recommendation" in comparison

        # Check best values
        assert comparison["best_values"]["member_count"] == 15000
        assert comparison["best_values"]["avg_views"] == 2000
        assert comparison["best_values"]["er"] == 15.0

        # Check recommendation (should be channel with best ER)
        assert comparison["recommendation"]["channel_id"] == channel_ids[0]

    @pytest.mark.asyncio
    async def test_price_per_1k_subscribers_calculation(self, db_session, user_test_data):
        """Test price per 1k subscribers calculation."""
        # Create user
        user = User(**user_test_data)
        db_session.add(user)
        await db_session.flush()

        # Create test channel
        chat = TelegramChat(
            username="channel1",
            title="Channel 1",
            member_count=10000,
            topic="it",
            owner_user_id=user.id,
            is_active=True,
            price_per_post=500,
        )
        db_session.add(chat)
        await db_session.flush()

        # Get channels and calculate metrics
        channels = await comparison_service.get_channels_for_comparison([chat.id])
        comparison = comparison_service.calculate_comparison_metrics(channels)

        # Price per 1k = 500 / (10000 / 1000) = 50
        assert comparison["channels"][0]["price_per_1k_subscribers"] == 50.0


class TestPDFGeneration:
    """Tests for PDF generation."""

    @pytest.mark.asyncio
    async def test_generate_mediatkit_pdf(self):
        """Test generating mediakit PDF."""
        from src.utils.mediakit_pdf import generate_mediakit_pdf

        # Test data
        mediakit_data = {
            "channel": {
                "id": 1,
                "username": "test_channel",
                "title": "Test Channel",
                "member_count": 10000,
            },
            "mediakit": {
                "custom_description": "Test description",
                "theme_color": "#1a73e8",
                "is_public": True,
                "show_metrics": {
                    "subscribers": True,
                    "avg_views": True,
                    "er": True,
                },
            },
            "metrics": {
                "subscribers": 10000,
                "avg_views": 1500,
                "er": 15.0,
                "post_frequency": 2.5,
            },
            "price": {
                "amount": 500,
                "currency": "кр",
            },
            "reviews": {
                "average_rating": 4.5,
                "count": 10,
            },
        }

        # Generate PDF
        pdf_bytes = generate_mediakit_pdf(mediakit_data)

        # Verify PDF is generated
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")  # PDF magic bytes
