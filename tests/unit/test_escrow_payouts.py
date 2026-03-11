"""
Tests for escrow system, payouts, and refunds (Tasks 1-3).

Tests cover:
- Campaign fund freezing
- Escrow fund release
- Failed placement refunds
- Payout requests
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from src.core.services.billing_service import billing_service
from src.db.models.campaign import Campaign, CampaignStatus
from src.db.models.mailing_log import MailingLog, MailingStatus
from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User


class TestEscrowFreeze:
    """Tests for freeze_campaign_funds()."""

    @pytest.mark.asyncio
    async def test_freeze_campaign_funds_success(self, db_session, user_test_data):
        """Test successful fund freezing."""
        # Create user with sufficient credits
        user = User(**user_test_data, credits=1000)
        db_session.add(user)
        await db_session.flush()

        # Create campaign
        campaign = Campaign(
            user_id=user.id,
            title="Test Campaign",
            text="Test text",
            status=CampaignStatus.DRAFT,
            cost=500,
        )
        db_session.add(campaign)
        await db_session.commit()

        # Freeze funds
        result = await billing_service.freeze_campaign_funds(campaign.id)

        assert result is True

        # Verify campaign status changed to QUEUED
        await db_session.refresh(campaign)
        assert campaign.status == CampaignStatus.QUEUED

        # Verify user credits decreased
        await db_session.refresh(user)
        assert user.credits == 500

        # Verify transaction created
        result = await db_session.execute(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.SPEND,
            )
        )
        transaction = result.scalar_one()
        assert transaction.amount == Decimal("500")
        assert transaction.meta_json["type"] == "escrow_freeze"

    @pytest.mark.asyncio
    async def test_freeze_campaign_funds_insufficient_credits(self, db_session, user_test_data):
        """Test fund freezing with insufficient credits."""
        # Create user with insufficient credits
        user = User(**user_test_data, credits=100)
        db_session.add(user)
        await db_session.flush()

        # Create campaign
        campaign = Campaign(
            user_id=user.id,
            title="Test Campaign",
            text="Test text",
            status=CampaignStatus.DRAFT,
            cost=500,
        )
        db_session.add(campaign)
        await db_session.commit()

        # Try to freeze funds
        result = await billing_service.freeze_campaign_funds(campaign.id)

        assert result is False

        # Verify campaign status unchanged
        await db_session.refresh(campaign)
        assert campaign.status == CampaignStatus.DRAFT

        # Verify user credits unchanged
        await db_session.refresh(user)
        assert user.credits == 100


class TestEscrowRelease:
    """Tests for release_escrow_funds()."""

    @pytest.mark.asyncio
    async def test_release_escrow_funds_success(self, db_session, user_test_data):
        """Test successful escrow release."""
        # Create owner user
        owner = User(**user_test_data, credits=0)
        db_session.add(owner)
        await db_session.flush()

        # Create chat
        from src.db.models.analytics import TelegramChat

        chat = TelegramChat(
            username="test_channel",
            title="Test Channel",
            member_count=10000,
            topic="it",
            owner_user_id=owner.id,
            is_active=True,
            price_per_post=500,
        )
        db_session.add(chat)
        await db_session.flush()

        # Create placement
        placement = MailingLog(
            campaign_id=1,
            chat_id=chat.id,
            chat_telegram_id=chat.telegram_id,
            status=MailingStatus.SENT,
            cost=500,
        )
        db_session.add(placement)
        await db_session.commit()

        # Release escrow
        result = await billing_service.release_escrow_funds(placement.id)

        assert result is True

        # Verify placement status changed to PAID
        await db_session.refresh(placement)
        assert placement.status == MailingStatus.PAID

        # Verify owner received 80% (400 credits)
        await db_session.refresh(owner)
        assert owner.credits == 400

        # Verify transaction created
        result = await db_session.execute(
            select(Transaction).where(
                Transaction.user_id == owner.id,
                Transaction.type == TransactionType.BONUS,
            )
        )
        transaction = result.scalar_one()
        assert transaction.amount == Decimal("400")
        assert transaction.meta_json["type"] == "escrow_release"

    @pytest.mark.asyncio
    async def test_release_escrow_funds_idempotency(self, db_session, user_test_data):
        """Test that release_escrow_funds is idempotent."""
        # Create owner user
        owner = User(**user_test_data, credits=0)
        db_session.add(owner)
        await db_session.flush()

        # Create chat
        from src.db.models.analytics import TelegramChat

        chat = TelegramChat(
            username="test_channel",
            title="Test Channel",
            member_count=10000,
            topic="it",
            owner_user_id=owner.id,
            is_active=True,
            price_per_post=500,
        )
        db_session.add(chat)
        await db_session.flush()

        # Create placement
        placement = MailingLog(
            campaign_id=1,
            chat_id=chat.id,
            chat_telegram_id=chat.telegram_id,
            status=MailingStatus.SENT,
            cost=500,
        )
        db_session.add(placement)
        await db_session.commit()

        # First release
        result1 = await billing_service.release_escrow_funds(placement.id)
        assert result1 is True

        # Second release (should be no-op)
        result2 = await billing_service.release_escrow_funds(placement.id)
        assert result2 is True

        # Verify owner received credits only once
        await db_session.refresh(owner)
        assert owner.credits == 400  # Not 800


class TestRefundFailedPlacement:
    """Tests for refund_failed_placement()."""

    @pytest.mark.asyncio
    async def test_refund_failed_placement_success(self, db_session, user_test_data):
        """Test successful refund for failed placement."""
        # Create advertiser user
        advertiser = User(**user_test_data, credits=500)
        db_session.add(advertiser)
        await db_session.flush()

        # Create campaign
        campaign = Campaign(
            user_id=advertiser.id,
            title="Test Campaign",
            text="Test text",
            status=CampaignStatus.RUNNING,
            cost=500,
        )
        db_session.add(campaign)
        await db_session.flush()

        # Create failed placement
        placement = MailingLog(
            campaign_id=campaign.id,
            chat_id=1,
            chat_telegram_id=-1001234567890,
            status=MailingStatus.FAILED,
            cost=500,
        )
        db_session.add(placement)
        await db_session.commit()

        # Refund
        result = await billing_service.refund_failed_placement(placement.id)

        assert result is True

        # Verify advertiser received refund
        await db_session.refresh(advertiser)
        assert advertiser.credits == 1000  # 500 + 500 refund

        # Verify transaction created
        result = await db_session.execute(
            select(Transaction).where(
                Transaction.user_id == advertiser.id,
                Transaction.type == TransactionType.REFUND,
            )
        )
        transaction = result.scalar_one()
        assert transaction.amount == Decimal("500")
        assert transaction.meta_json["type"] == "refund"

    @pytest.mark.asyncio
    async def test_refund_failed_placement_only_failed_status(self, db_session, user_test_data):
        """Test refund only works for FAILED status."""
        # Create advertiser user
        advertiser = User(**user_test_data, credits=500)
        db_session.add(advertiser)
        await db_session.flush()

        # Create campaign
        campaign = Campaign(
            user_id=advertiser.id,
            title="Test Campaign",
            text="Test text",
            status=CampaignStatus.RUNNING,
            cost=500,
        )
        db_session.add(campaign)
        await db_session.flush()

        # Create SENT placement (not FAILED)
        placement = MailingLog(
            campaign_id=campaign.id,
            chat_id=1,
            chat_telegram_id=-1001234567890,
            status=MailingStatus.SENT,
            cost=500,
        )
        db_session.add(placement)
        await db_session.commit()

        # Try to refund (should fail)
        result = await billing_service.refund_failed_placement(placement.id)

        assert result is False


class TestPayoutRequest:
    """Tests for payout request flow."""

    @pytest.mark.asyncio
    async def test_payout_creation(self, db_session, user_test_data):
        """Test creating a payout."""
        # Create owner user
        owner = User(**user_test_data, credits=0)
        db_session.add(owner)
        await db_session.flush()

        # Create chat
        from src.db.models.analytics import TelegramChat

        chat = TelegramChat(
            username="test_channel",
            title="Test Channel",
            member_count=10000,
            topic="it",
            owner_user_id=owner.id,
            is_active=True,
        )
        db_session.add(chat)
        await db_session.flush()

        # Create placement (already paid)
        placement = MailingLog(
            campaign_id=1,
            chat_id=chat.id,
            chat_telegram_id=chat.telegram_id,
            status=MailingStatus.PAID,
            cost=500,
        )
        db_session.add(placement)
        await db_session.flush()

        # Create payout
        payout = Payout(
            owner_id=owner.id,
            channel_id=chat.id,
            placement_id=placement.id,
            amount=Decimal("400"),  # 80% of 500
            platform_fee=Decimal("100"),
            currency=PayoutCurrency.RUB,
            status=PayoutStatus.PENDING,
            wallet_address="TxxxxxxxxxxxxxxxxxxxxxxxxxxxxB",
        )
        db_session.add(payout)
        await db_session.commit()

        # Verify payout created
        result = await db_session.execute(select(Payout).where(Payout.owner_id == owner.id))
        payouts = list(result.scalars().all())

        assert len(payouts) == 1
        assert payouts[0].amount == Decimal("400")
        assert payouts[0].status == PayoutStatus.PENDING
