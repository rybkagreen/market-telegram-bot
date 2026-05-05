"""Unit-level tests for PlacementTransitionService.

Phase 2 § 2.B.1 commit 4/4.
Phase 3c (2026-05-04) appends ``TestGateEnforcement`` covering
LegalComplianceService gate dispatch wired into ``transition()``.

Tests live in tests/integration/ for testcontainer DB access. The service
appends rows to placement_status_history and reads PlacementRequest from
a real session — sqlite/mock backings would not exercise the JSONB
column or the FK CASCADE behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import TransitionBlockedError
from src.core.schemas.transition_metadata import TransitionMetadata
from src.core.services.placement_transition_service import (
    InvalidTransitionError,
    PlacementTransitionService,
    TransitionInvariantError,
)
from src.db.models.audit_log import AuditLog
from src.db.models.ord_registration import OrdRegistration
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


# ============================================================================
# Phase 3c — Gate enforcement tests (TestGateEnforcement)
#
# Wires LegalComplianceService.check_gates_for_transition into transition()
# body. G07 PHASE4_PENDING marker actively blocks pending_owner|counter_offer
# → pending_payment until Phase 4 ships G07 real body.
# ============================================================================


class TestGateEnforcement:
    async def test_g07_marker_blocks_pending_payment_transition(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """pending_owner → pending_payment fires G07 PHASE4_PENDING marker."""
        placement = await _seed_placement(db_session, telegram_id_offset=300)

        with pytest.raises(TransitionBlockedError) as exc_info:
            await service.transition(
                placement=placement,
                to_status=PlacementStatus.pending_payment,
                actor_user_id=placement.owner_id,
                reason="user_action",
                trigger="api",
            )

        blockers = exc_info.value.extra["blockers"]
        assert len(blockers) == 1
        assert blockers[0]["gate"] == "G07_SUPPLEMENTARY_AGREEMENT_SIGNED"
        assert blockers[0]["reason_code"] == "phase4_pending"
        assert exc_info.value.extra["from"] == "pending_owner"
        assert exc_info.value.extra["to"] == "pending_payment"

    async def test_gate_empty_transition_passes_through(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """pending_owner → counter_offer has empty gate set; transitions cleanly."""
        placement = await _seed_placement(db_session, telegram_id_offset=310)

        history = await service.transition(
            placement=placement,
            to_status=PlacementStatus.counter_offer,
            actor_user_id=placement.advertiser_id,
            reason="user_action",
            trigger="api",
        )

        assert placement.status == PlacementStatus.counter_offer
        assert history.to_status == PlacementStatus.counter_offer

    async def test_admin_override_bypasses_gates(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """transition_admin_override does NOT consult gates — even for G07 transitions."""
        placement = await _seed_placement(db_session, telegram_id_offset=320)
        admin = User(telegram_id=920_900_001, first_name="Admin", username="admin320")
        db_session.add(admin)
        await db_session.flush()

        history = await service.transition_admin_override(
            placement=placement,
            to_status=PlacementStatus.pending_payment,
            actor_user_id=admin.id,
            reason="manual_recovery",
            admin_override_reason="manual_data_repair",
        )

        assert placement.status == PlacementStatus.pending_payment
        assert history.to_status == PlacementStatus.pending_payment

    async def test_bypass_gates_flag_skips_check(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """transition(..., bypass_gates=True) skips gate evaluation entirely."""
        placement = await _seed_placement(db_session, telegram_id_offset=330)

        history = await service.transition(
            placement=placement,
            to_status=PlacementStatus.pending_payment,
            actor_user_id=None,
            reason="system",
            trigger="api",
            bypass_gates=True,
        )

        assert placement.status == PlacementStatus.pending_payment
        assert history.to_status == PlacementStatus.pending_payment

    async def test_blockers_audit_log_written(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """Failed gate writes AuditLog row with action='transition_blocked'."""
        placement = await _seed_placement(db_session, telegram_id_offset=340)

        with pytest.raises(TransitionBlockedError):
            await service.transition(
                placement=placement,
                to_status=PlacementStatus.pending_payment,
                actor_user_id=placement.owner_id,
                reason="user_action",
                trigger="api",
            )

        audit_rows = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "transition_blocked")
        )
        rows = list(audit_rows.scalars())
        assert len(rows) == 1
        assert rows[0].resource_type == "placement"
        assert rows[0].resource_id == placement.id
        assert rows[0].user_id == placement.owner_id
        assert rows[0].extra["from"] == "pending_owner"
        assert rows[0].extra["to"] == "pending_payment"
        assert "G07_SUPPLEMENTARY_AGREEMENT_SIGNED" in rows[0].extra["blockers"]

    async def test_failed_transition_no_status_mutation(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """When TransitionBlockedError raised, placement.status is NOT mutated."""
        placement = await _seed_placement(db_session, telegram_id_offset=350)
        original_status = placement.status

        with pytest.raises(TransitionBlockedError):
            await service.transition(
                placement=placement,
                to_status=PlacementStatus.pending_payment,
                actor_user_id=placement.owner_id,
                reason="user_action",
                trigger="api",
            )

        assert placement.status == original_status == PlacementStatus.pending_owner

    async def test_failed_transition_no_history_row(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """When TransitionBlockedError raised, no PlacementStatusHistory row appended."""
        placement = await _seed_placement(db_session, telegram_id_offset=360)

        with pytest.raises(TransitionBlockedError):
            await service.transition(
                placement=placement,
                to_status=PlacementStatus.pending_payment,
                actor_user_id=placement.owner_id,
                reason="user_action",
                trigger="api",
            )

        result = await db_session.execute(
            select(PlacementStatusHistory).where(
                PlacementStatusHistory.placement_id == placement.id
            )
        )
        rows = list(result.scalars())
        assert rows == []

    async def test_multi_blocker_collect_all(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """escrow → published evaluates G08+G09+G10 — all failed gates collected."""
        placement = await _seed_placement(
            db_session,
            telegram_id_offset=370,
            status=PlacementStatus.escrow,
            with_escrow_tx=True,
        )

        with pytest.raises(TransitionBlockedError) as exc_info:
            await service.transition(
                placement=placement,
                to_status=PlacementStatus.published,
                actor_user_id=None,
                reason="publication_success",
                trigger="celery_signal",
            )

        blocker_gates = {b["gate"] for b in exc_info.value.extra["blockers"]}
        assert blocker_gates == {
            "G08_ERID_REGISTERED",
            "G09_ORD_CONTRACT_REPORTED",
            "G10_PLACEMENT_TEXT_MARKED",
        }
        # Real reason codes (not phase4_pending markers) — G08/G09/G10 ship real bodies.
        for b in exc_info.value.extra["blockers"]:
            assert b["reason_code"] != "phase4_pending"

    async def test_publication_side_g08_g09_g10_pass_with_full_seed(
        self,
        service: PlacementTransitionService,
        db_session: AsyncSession,
    ) -> None:
        """escrow → published passes when ORD registration + erid set."""
        placement = await _seed_placement(
            db_session,
            telegram_id_offset=380,
            status=PlacementStatus.escrow,
            with_escrow_tx=True,
        )
        # Set placement.erid (G10) and seed OrdRegistration with erid (G08) +
        # contract_ord_id (G09) so all three pre-publication gates pass.
        placement.erid = "test_erid_380"
        ord_reg = OrdRegistration(
            placement_request_id=placement.id,
            erid="test_erid_380",
            contract_ord_id="test_contract_ord_380",
        )
        db_session.add(ord_reg)
        await db_session.flush()

        history = await service.transition(
            placement=placement,
            to_status=PlacementStatus.published,
            actor_user_id=None,
            reason="publication_success",
            trigger="celery_signal",
        )

        assert placement.status == PlacementStatus.published
        assert history.to_status == PlacementStatus.published
