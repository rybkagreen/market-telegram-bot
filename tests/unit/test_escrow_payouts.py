"""
Tests for escrow system, payouts, and refunds (Tasks 1-3).

Tests cover:
- PlacementRequest fund freezing
- Escrow fund release
- Failed placement refunds
- Payout requests

Note: v4.2 uses PlacementRequest instead of Campaign model.
"""

import random
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.core.services.billing_service import BillingService
from src.db.models.mailing_log import MailingLog, MailingStatus

billing_service = BillingService()
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User


def unique_telegram_id() -> int:
    """Generate unique telegram_id for test isolation."""
    return random.randint(100000000, 999999999)


class TestEscrowFreeze:
    """Tests for freeze_placement_funds()."""

    @pytest.mark.asyncio
    async def test_freeze_placement_funds_success(self, db_session, advertiser_test_data):
        """Test successful fund freezing."""
        # Create advertiser with sufficient balance_rub
        advertiser_data = advertiser_test_data.copy()
        advertiser_data["telegram_id"] = unique_telegram_id()
        advertiser_data["balance_rub"] = 1000
        advertiser = User(**advertiser_data)
        db_session.add(advertiser)
        await db_session.flush()

        # Create channel
        from src.db.models.telegram_chat import TelegramChat
        channel = TelegramChat(
            telegram_id=-1001234567890,
            title="Test Channel",
            username="test_channel",
            member_count=5000,
            owner_id=advertiser.id,
            is_active=True,
        )
        db_session.add(channel)
        await db_session.flush()

        # Create placement request
        placement = PlacementRequest(
            advertiser_id=advertiser.id,
            owner_id=advertiser.id,
            channel_id=channel.id,
            status=PlacementStatus.pending_owner,
            ad_text="Test ad text",
            proposed_price=Decimal("500"),
            final_price=Decimal("500"),
        )
        db_session.add(placement)
        await db_session.commit()

        # Freeze funds
        result = await billing_service.freeze_escrow_for_placement(
            db_session,
            placement.id,
            advertiser.id,
            placement.proposed_price,
        )

        assert result is not None
        assert isinstance(result, Transaction)
        assert result.amount == Decimal("500")
        assert result.type == TransactionType.escrow_freeze
        assert result.user_id == advertiser.id
        assert result.meta_json.get("type") == "escrow_freeze"
        assert result.meta_json.get("placement_id") == placement.id

    @pytest.mark.asyncio
    async def test_freeze_placement_funds_insufficient_balance_rub(self, db_session, advertiser_test_data):
        """Test fund freezing with insufficient balance_rub."""
        # Create advertiser with insufficient balance_rub
        advertiser_data = advertiser_test_data.copy()
        advertiser_data["telegram_id"] = unique_telegram_id()
        advertiser_data["balance_rub"] = 100
        advertiser = User(**advertiser_data)
        db_session.add(advertiser)
        await db_session.flush()

        # Create channel
        from src.db.models.telegram_chat import TelegramChat
        channel = TelegramChat(
            telegram_id=-1001234567890,
            title="Test Channel",
            username="test_channel",
            member_count=5000,
            owner_id=advertiser.id,
            is_active=True,
        )
        db_session.add(channel)
        await db_session.flush()

        # Create placement request
        placement = PlacementRequest(
            advertiser_id=advertiser.id,
            owner_id=advertiser.id,
            channel_id=channel.id,
            status=PlacementStatus.pending_owner,
            ad_text="Test ad text",
            proposed_price=Decimal("500"),
            final_price=Decimal("500"),
        )
        db_session.add(placement)
        await db_session.commit()

        # Try to freeze funds - should raise InsufficientFundsError
        from src.core.services.billing_service import InsufficientFundsError

        with pytest.raises(InsufficientFundsError):
            await billing_service.freeze_escrow_for_placement(
                db_session,
                placement.id,
                advertiser.id,
                placement.proposed_price,
            )


class TestEscrowRelease:
    """Tests for release_escrow_funds()."""

    @pytest.mark.asyncio
    async def test_release_escrow_funds_success(self, db_session, owner_test_data):
        """Test successful escrow release."""
        # Create platform account (singleton id=1)
        from src.db.models.platform_account import PlatformAccount
        platform_account = PlatformAccount(id=1)
        db_session.add(platform_account)
        await db_session.flush()

        # Create owner user
        owner_data = owner_test_data.copy()
        owner_data["telegram_id"] = unique_telegram_id()
        owner_data["balance_rub"] = 0
        owner = User(**owner_data)
        db_session.add(owner)
        await db_session.flush()

        # Create channel
        from src.db.models.telegram_chat import TelegramChat
        channel = TelegramChat(
            telegram_id=-1009876543210,
            title="Test Channel",
            username="test_channel",
            member_count=10000,
            owner_id=owner.id,
            is_active=True,
        )
        db_session.add(channel)
        await db_session.flush()

        # Create placement request
        placement_request = PlacementRequest(
            advertiser_id=owner.id,
            owner_id=owner.id,
            channel_id=channel.id,
            status=PlacementStatus.escrow,
            ad_text="Test ad text",
            proposed_price=Decimal("500"),
            final_price=Decimal("500"),
        )
        db_session.add(placement_request)
        await db_session.flush()

        # Create mailing
        mailing = MailingLog(
            placement_request_id=placement_request.id,
            chat_id=channel.id,
            chat_telegram_id=channel.telegram_id,
            status=MailingStatus.sent,
            cost=500,
        )
        db_session.add(mailing)
        await db_session.commit()

        # Release escrow
        await billing_service.release_escrow(
            db_session,
            placement_request.id,
            placement_request.final_price,
            placement_request.advertiser_id,
            placement_request.owner_id,
        )

        # Verify mailing status changed to PAID
        await db_session.refresh(mailing)
        assert mailing.status == MailingStatus.paid

        # Owner net = price × OWNER_SHARE_RATE × (1 - SERVICE_FEE_RATE)
        # 500 × 0.80 = 400 gross; service_fee = 400 × 0.015 = 6.00;
        # owner_net = 400 - 6 = 394 (78.8% effective).
        await db_session.refresh(owner)
        assert owner.earned_rub == Decimal("394.00")

        # Verify transaction created
        result = await db_session.execute(
            select(Transaction).where(
                Transaction.user_id == owner.id,
                Transaction.type == TransactionType.escrow_release,
            )
        )
        transaction = result.scalar_one()
        assert transaction.amount == Decimal("394.00")
        assert transaction.meta_json.get("type") == "escrow_release"

    @pytest.mark.asyncio
    async def test_release_escrow_funds_idempotency(self, db_session, owner_test_data):
        """Test that release_escrow_funds is idempotent."""
        # Create platform account (singleton id=1)
        from src.db.models.platform_account import PlatformAccount
        platform_account = PlatformAccount(id=1)
        db_session.add(platform_account)
        await db_session.flush()

        # Create owner user
        owner_data = owner_test_data.copy()
        owner_data["telegram_id"] = unique_telegram_id()
        owner_data["balance_rub"] = 0
        owner = User(**owner_data)
        db_session.add(owner)
        await db_session.flush()

        # Create channel
        from src.db.models.telegram_chat import TelegramChat
        channel = TelegramChat(
            telegram_id=-1009876543210,
            title="Test Channel",
            username="test_channel",
            member_count=10000,
            owner_id=owner.id,
            is_active=True,
        )
        db_session.add(channel)
        await db_session.flush()

        # Create placement request
        placement_request = PlacementRequest(
            advertiser_id=owner.id,
            owner_id=owner.id,
            channel_id=channel.id,
            status=PlacementStatus.escrow,
            ad_text="Test ad text",
            proposed_price=Decimal("500"),
            final_price=Decimal("500"),
        )
        db_session.add(placement_request)
        await db_session.flush()

        # Create mailing
        mailing = MailingLog(
            placement_request_id=placement_request.id,
            chat_id=channel.id,
            chat_telegram_id=channel.telegram_id,
            status=MailingStatus.sent,
            cost=500,
        )
        db_session.add(mailing)
        await db_session.commit()

        # First release
        await billing_service.release_escrow(
            db_session,
            placement_request.id,
            placement_request.final_price,
            placement_request.advertiser_id,
            placement_request.owner_id,
        )

        # Second release (should be no-op due to idempotency)
        await billing_service.release_escrow(
            db_session,
            placement_request.id,
            placement_request.final_price,
            placement_request.advertiser_id,
            placement_request.owner_id,
        )

        # Verify owner received earned_rub only once (78.8% of 500 = 394, not 788)
        await db_session.refresh(owner)
        assert owner.earned_rub == Decimal("394.00")


class TestRefundFailedPlacement:
    """Tests for refund_failed_placement()."""

    @pytest.mark.asyncio
    async def test_refund_failed_placement_success(self, db_session, advertiser_test_data):
        """Test successful refund for failed placement."""
        # Create advertiser user
        advertiser_data = advertiser_test_data.copy()
        advertiser_data["telegram_id"] = unique_telegram_id()
        advertiser_data["balance_rub"] = 500
        advertiser = User(**advertiser_data)
        db_session.add(advertiser)
        await db_session.flush()

        # Create channel
        from src.db.models.telegram_chat import TelegramChat
        channel = TelegramChat(
            telegram_id=-1001234567890,
            title="Test Channel",
            username="test_channel",
            member_count=5000,
            owner_id=advertiser.id,
            is_active=True,
        )
        db_session.add(channel)
        await db_session.flush()

        # Create placement request in escrow status
        placement_request = PlacementRequest(
            advertiser_id=advertiser.id,
            owner_id=advertiser.id,
            channel_id=channel.id,
            status=PlacementStatus.escrow,
            ad_text="Test ad text",
            proposed_price=Decimal("500"),
            final_price=Decimal("500"),
        )
        db_session.add(placement_request)
        await db_session.flush()

        # Create failed mailing log
        mailing = MailingLog(
            placement_request_id=placement_request.id,
            chat_id=channel.id,
            chat_telegram_id=channel.telegram_id,
            status=MailingStatus.failed,
            cost=500,
        )
        db_session.add(mailing)
        await db_session.commit()

        # Refund
        result = await billing_service.refund_failed_placement(db_session, mailing.id)

        assert result is True

        # Commit the transaction
        await db_session.commit()

        # Verify advertiser received refund to balance_rub
        await db_session.refresh(advertiser)
        assert advertiser.balance_rub == Decimal("500")  # Refunded to balance_rub

        # Verify transaction created
        result = await db_session.execute(
            select(Transaction).where(
                Transaction.user_id == advertiser.id,
                Transaction.type == TransactionType.refund_full,
            )
        )
        transaction = result.scalar_one()
        assert transaction.amount == Decimal("500")
        assert transaction.meta_json["type"] == "refund"

    @pytest.mark.asyncio
    async def test_refund_failed_placement_only_failed_status(self, db_session, advertiser_test_data):
        """Test refund only works for FAILED status."""
        # Create advertiser user
        advertiser_data = advertiser_test_data.copy()
        advertiser_data["telegram_id"] = unique_telegram_id()
        advertiser_data["balance_rub"] = 500
        advertiser = User(**advertiser_data)
        db_session.add(advertiser)
        await db_session.flush()

        # Create channel
        from src.db.models.telegram_chat import TelegramChat
        channel = TelegramChat(
            telegram_id=-1001234567890,
            title="Test Channel",
            username="test_channel",
            member_count=5000,
            owner_id=advertiser.id,
            is_active=True,
        )
        db_session.add(channel)
        await db_session.flush()

        # Create placement request
        placement_request = PlacementRequest(
            advertiser_id=advertiser.id,
            owner_id=advertiser.id,
            channel_id=channel.id,
            status=PlacementStatus.escrow,
            ad_text="Test ad text",
            proposed_price=Decimal("500"),
            final_price=Decimal("500"),
        )
        db_session.add(placement_request)
        await db_session.flush()

        # Create SENT mailing (not FAILED)
        mailing = MailingLog(
            placement_request_id=placement_request.id,
            chat_id=channel.id,
            chat_telegram_id=channel.telegram_id,
            status=MailingStatus.sent,
            cost=500,
        )
        db_session.add(mailing)
        await db_session.commit()

        # Try to refund (should fail)
        result = await billing_service.refund_failed_placement(db_session, mailing.id)

        assert result is False


class TestPayoutRequest:
    """Tests for payout request flow."""

    @pytest.mark.asyncio
    async def test_payout_creation(self, db_session, owner_test_data):
        """Test creating a payout."""
        # Create owner user
        owner_data = owner_test_data.copy()
        owner_data["telegram_id"] = unique_telegram_id()
        owner_data["balance_rub"] = 0
        owner = User(**owner_data)
        db_session.add(owner)
        await db_session.flush()

        # Create channel
        from src.db.models.telegram_chat import TelegramChat
        channel = TelegramChat(
            telegram_id=-1009876543210,
            title="Test Channel",
            username="test_channel",
            member_count=10000,
            owner_id=owner.id,
            is_active=True,
        )
        db_session.add(channel)
        await db_session.flush()

        # Create placement request
        placement_request = PlacementRequest(
            advertiser_id=owner.id,
            owner_id=owner.id,
            channel_id=channel.id,
            status=PlacementStatus.published,
            ad_text="Test ad text",
            proposed_price=Decimal("500"),
            final_price=Decimal("500"),
        )
        db_session.add(placement_request)
        await db_session.flush()

        # Create mailing (already paid)
        mailing = MailingLog(
            placement_request_id=placement_request.id,
            chat_id=channel.id,
            chat_telegram_id=channel.telegram_id,
            status=MailingStatus.paid,
            cost=500,
        )
        db_session.add(mailing)
        await db_session.flush()

        # Create payout request
        payout = PayoutRequest(
            owner_id=owner.id,
            gross_amount=Decimal("500"),
            fee_amount=Decimal("75"),  # 15% platform fee
            net_amount=Decimal("425"),  # 85% to owner
            status=PayoutStatus.pending,
            requisites="TxxxxxxxxxxxxxxxxxxxxxxxxxxxxB",
        )
        db_session.add(payout)
        await db_session.commit()

        # Verify payout request created
        result = await db_session.execute(select(PayoutRequest).where(PayoutRequest.owner_id == owner.id))
        payouts = list(result.scalars().all())

        assert len(payouts) == 1
        assert payouts[0].gross_amount == Decimal("500")
        assert payouts[0].status == PayoutStatus.pending
