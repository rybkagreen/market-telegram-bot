"""Unit-level tests for PlacementTransitionService.

Phase 2 § 2.B.1 commit 4/4.

Tests live in tests/integration/ for testcontainer DB access. The service
appends rows to placement_status_history and reads PlacementRequest from
a real session — sqlite/mock backings would not exercise the JSONB
column or the FK CASCADE behavior.

Service-level isolation: no callers integrated yet (§ 2.B.2 work).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.schemas.transition_metadata import TransitionMetadata
from src.core.services.placement_transition_service import (
    InvalidTransitionError,
    PlacementTransitionService,
    TransitionInvariantError,
)
from src.db.models.placement_request import (
    PlacementRequest,
    PlacementStatus,
    PublicationFormat,
)
from src.db.models.placement_status_history import PlacementStatusHistory
from src.db.models.telegram_chat import TelegramChat
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User


async def _seed_placement(
    db_session: AsyncSession,
    *,
    telegram_id_offset: int = 0,
    status: PlacementStatus = PlacementStatus.pending_owner,
    with_escrow_tx: bool = False,
) -> PlacementRequest:
    """Seed minimal users + channel + placement.

    Each call uses a unique telegram_id range to avoid collisions when a
    test seeds multiple placements.
    """
    advertiser = User(
        telegram_id=920_000_001 + telegram_id_offset,
        first_name="Adv",
        username=f"adv_{telegram_id_offset}",
    )
    owner = User(
        telegram_id=920_000_002 + telegram_id_offset,
        first_name="Own",
        username=f"own_{telegram_id_offset}",
    )
    db_session.add_all([advertiser, owner])
    await db_session.flush()

    channel = TelegramChat(
        telegram_id=-1_009_200_000 - telegram_id_offset,
        title=f"Channel {telegram_id_offset}",
        username=f"ch_{telegram_id_offset}",
        owner_id=owner.id,
        member_count=1000,
    )
    db_session.add(channel)
    await db_session.flush()

    escrow_tx_id: int | None = None
    if with_escrow_tx:
        escrow_tx = Transaction(
            user_id=advertiser.id,
            type=TransactionType.escrow_freeze,
            amount=Decimal("1500"),
        )
        db_session.add(escrow_tx)
        await db_session.flush()
        escrow_tx_id = escrow_tx.id

    placement = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        status=status,
        publication_format=PublicationFormat.post_24h,
        ad_text="Test ad text for transition service.",
        proposed_price=Decimal("1500"),
        final_price=Decimal("1500") if with_escrow_tx else None,
        escrow_transaction_id=escrow_tx_id,
    )
    db_session.add(placement)
    await db_session.flush()
    return placement


@pytest.fixture
def service(db_session: AsyncSession) -> PlacementTransitionService:
    return PlacementTransitionService(db_session)


class TestOrganicTransition:
    async def test_allowed_transition_succeeds(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """pending_owner -> counter_offer is in allow-list."""
        placement = await _seed_placement(db_session)

        history = await service.transition(
            placement=placement,
            to_status=PlacementStatus.counter_offer,
            actor_user_id=placement.advertiser_id,
            reason="user_action",
            trigger="api",
        )

        assert placement.status == PlacementStatus.counter_offer
        assert history.from_status == PlacementStatus.pending_owner
        assert history.to_status == PlacementStatus.counter_offer
        assert history.reason == "user_action"

    async def test_disallowed_transition_raises(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """pending_owner -> escrow is not in the allow-list."""
        placement = await _seed_placement(db_session, telegram_id_offset=10)

        with pytest.raises(InvalidTransitionError):
            await service.transition(
                placement=placement,
                to_status=PlacementStatus.escrow,
                actor_user_id=None,
                reason="system_event",
                trigger="system",
            )

    async def test_terminal_status_blocks_further_transitions(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """completed status is terminal — no further transitions allowed."""
        placement = await _seed_placement(
            db_session,
            telegram_id_offset=20,
            status=PlacementStatus.completed,
        )

        with pytest.raises(InvalidTransitionError):
            await service.transition(
                placement=placement,
                to_status=PlacementStatus.cancelled,
                actor_user_id=None,
                reason="user_action",
                trigger="api",
            )


class TestAdminOverride:
    async def test_admin_override_bypasses_allow_list(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """Admin can transition pending_owner -> escrow with override reason
        provided escrow_transaction_id is set (INV-1)."""
        placement = await _seed_placement(
            db_session,
            telegram_id_offset=30,
            with_escrow_tx=True,
        )
        admin = User(telegram_id=920_999_999, first_name="Admin", username="admin1")
        db_session.add(admin)
        await db_session.flush()

        history = await service.transition_admin_override(
            placement=placement,
            to_status=PlacementStatus.escrow,
            actor_user_id=admin.id,
            reason="manual_intervention",
            admin_override_reason="manual_data_repair",
        )

        assert placement.status == PlacementStatus.escrow
        assert history.actor_user_id == admin.id
        assert history.metadata_json["admin_override_reason"] == "manual_data_repair"
        assert history.metadata_json["from_admin_id"] == admin.id

    async def test_admin_override_still_enforces_invariants(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """INV-1 cannot be bypassed by admin override (no escrow_transaction_id)."""
        placement = await _seed_placement(db_session, telegram_id_offset=40)
        admin = User(telegram_id=920_999_998, first_name="Admin", username="admin2")
        db_session.add(admin)
        await db_session.flush()

        with pytest.raises(TransitionInvariantError):
            await service.transition_admin_override(
                placement=placement,
                to_status=PlacementStatus.escrow,
                actor_user_id=admin.id,
                reason="force_escrow",
                admin_override_reason="manual_data_repair",
            )


class TestHistoryAppend:
    async def test_history_row_persists(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        placement = await _seed_placement(db_session, telegram_id_offset=50)
        await service.transition(
            placement=placement,
            to_status=PlacementStatus.counter_offer,
            actor_user_id=placement.advertiser_id,
            reason="user_action",
            trigger="api",
        )
        await db_session.flush()

        result = await db_session.execute(
            select(PlacementStatusHistory).where(
                PlacementStatusHistory.placement_id == placement.id
            )
        )
        rows = list(result.scalars())
        assert len(rows) == 1
        assert rows[0].metadata_json["trigger"] == "api"

    async def test_ping_pong_creates_multiple_rows(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """Decision 10: NOT UNIQUE on (placement_id, status) — multiple
        entries for same status are legal."""
        placement = await _seed_placement(db_session, telegram_id_offset=60)
        await service.transition(
            placement=placement,
            to_status=PlacementStatus.counter_offer,
            actor_user_id=None,
            reason="ping",
            trigger="api",
        )
        await service.transition(
            placement=placement,
            to_status=PlacementStatus.pending_owner,
            actor_user_id=None,
            reason="pong",
            trigger="api",
        )
        await service.transition(
            placement=placement,
            to_status=PlacementStatus.counter_offer,
            actor_user_id=None,
            reason="ping2",
            trigger="api",
        )
        await db_session.flush()

        result = await db_session.execute(
            select(PlacementStatusHistory)
            .where(PlacementStatusHistory.placement_id == placement.id)
            .where(PlacementStatusHistory.to_status == PlacementStatus.counter_offer)
        )
        rows = list(result.scalars())
        assert len(rows) == 2  # ping-pong


class TestTimestampSync:
    async def test_counter_offer_sets_expires_at_24h(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """Decision 4: counter_offer sets expires_at to +24h."""
        placement = await _seed_placement(db_session, telegram_id_offset=70)

        before = datetime.now(UTC)
        await service.transition(
            placement=placement,
            to_status=PlacementStatus.counter_offer,
            actor_user_id=None,
            reason="test",
            trigger="api",
        )
        await db_session.flush()

        assert placement.expires_at is not None
        delta = placement.expires_at - before
        assert timedelta(hours=23, minutes=59) < delta < timedelta(hours=24, minutes=1)


class TestMetadataValidation:
    def test_pii_field_rejected(self) -> None:
        """extra='forbid' rejects unknown fields, including PII like telegram_id."""
        with pytest.raises(ValidationError):
            TransitionMetadata(
                from_status=PlacementStatus.pending_owner,
                to_status=PlacementStatus.counter_offer,
                trigger="api",
                telegram_id=12345,  # type: ignore[call-arg]  # forbidden — extra field
            )
