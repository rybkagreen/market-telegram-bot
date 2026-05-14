"""BL-107 Phase B.2 — G19 gate framework tests.

Pure unit tests, no DB connection required. Tests:

* ``_check_g19_core`` short-circuit precedence (Phase B.2 design — 5 cases)
* ``check_g19`` placement-side wrapper reads TelegramChat correctly
* ``check_g19_channel_add`` channel-context wrapper reads ChannelAddContext
* Registry registration: _GATE_CHECKERS, _CHANNEL_CONTEXT_GATE_CHECKERS, _CHANNEL_ADD_GATES
* Orchestration: LegalComplianceService.check_gates_for_channel_add returns G19 result

Mocks: AsyncMock(AsyncSession) — pure-logic bodies don't touch session.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.channel_add_context import ChannelAddContext
from src.core.services.gates.owner_gates import (
    _check_g19_core,
    check_g19,
    check_g19_channel_add,
)
from src.core.services.legal_compliance_service import (
    _CHANNEL_ADD_GATES,
    _CHANNEL_CONTEXT_GATE_CHECKERS,
    _GATE_CHECKERS,
    LegalComplianceService,
)

# ─── Pure logic — _check_g19_core ─────────────────────────────────────────


class TestCheckG19Core:
    """Short-circuit precedence (Phase B.2 design)."""

    def test_below_threshold_passes(self):
        """member_count < 10_000 → regulation not applicable, passed=True."""
        result = _check_g19_core(
            member_count=5_000,
            is_test=False,
            is_blogger_registry_verified=False,
            blogger_registry_application_number=None,
        )
        assert result.passed is True
        assert result.blocker is False
        assert result.reason_code == GateReason.OK.value
        assert result.gate == PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED

    def test_test_channel_exempt_even_above_threshold(self):
        """is_test=True → admin carve-out, passed=True даже above threshold."""
        result = _check_g19_core(
            member_count=50_000,
            is_test=True,
            is_blogger_registry_verified=False,
            blogger_registry_application_number=None,
        )
        assert result.passed is True
        assert result.blocker is False
        assert result.reason_code == GateReason.OK.value

    def test_verified_passes(self):
        """is_blogger_registry_verified=True → pass."""
        result = _check_g19_core(
            member_count=15_000,
            is_test=False,
            is_blogger_registry_verified=True,
            blogger_registry_application_number=None,
        )
        assert result.passed is True
        assert result.blocker is False
        assert result.reason_code == GateReason.OK.value

    def test_pending_review_blocks_with_specific_reason(self):
        """application_number submitted, not yet verified → PENDING_REVIEW."""
        result = _check_g19_core(
            member_count=15_000,
            is_test=False,
            is_blogger_registry_verified=False,
            blogger_registry_application_number="GU-2026-12345",
        )
        assert result.passed is False
        assert result.blocker is True
        assert result.reason_code == GateReason.BLOGGER_REGISTRY_PENDING_REVIEW.value
        assert result.remediation_url is None  # Phase B.5 populates

    def test_default_fail_not_verified(self):
        """≥10k, no verification, no application → BLOGGER_REGISTRY_NOT_VERIFIED."""
        result = _check_g19_core(
            member_count=15_000,
            is_test=False,
            is_blogger_registry_verified=False,
            blogger_registry_application_number=None,
        )
        assert result.passed is False
        assert result.blocker is True
        assert result.reason_code == GateReason.BLOGGER_REGISTRY_NOT_VERIFIED.value
        assert result.remediation_url is None  # Phase B.5 populates

    def test_boundary_below_threshold(self):
        """member_count = 9_999 (strict <) → pass."""
        result = _check_g19_core(
            member_count=9_999,
            is_test=False,
            is_blogger_registry_verified=False,
            blogger_registry_application_number=None,
        )
        assert result.passed is True

    def test_boundary_at_threshold_fails_when_unverified(self):
        """member_count = 10_000 (boundary) → threshold check applies, fails."""
        result = _check_g19_core(
            member_count=10_000,
            is_test=False,
            is_blogger_registry_verified=False,
            blogger_registry_application_number=None,
        )
        assert result.passed is False
        assert result.reason_code == GateReason.BLOGGER_REGISTRY_NOT_VERIFIED.value

    def test_precedence_test_beats_unverified(self):
        """is_test=True wins даже если application_number set (admin carve-out)."""
        result = _check_g19_core(
            member_count=15_000,
            is_test=True,
            is_blogger_registry_verified=False,
            blogger_registry_application_number="GU-12345",
        )
        assert result.passed is True


# ─── Placement-side wrapper — check_g19 ───────────────────────────────────


class TestCheckG19PlacementSide:
    """check_g19(session, placement) reads TelegramChat fields correctly."""

    @pytest.mark.asyncio
    async def test_reads_channel_state_unverified_above_threshold(self):
        session = AsyncMock(spec=AsyncSession)
        channel = MagicMock()
        channel.member_count = 20_000
        channel.is_test = False
        channel.is_blogger_registry_verified = False
        channel.blogger_registry_application_number = None
        session.get_one = AsyncMock(return_value=channel)
        placement = MagicMock()

        result = await check_g19(session, placement)

        assert result.passed is False
        assert result.reason_code == GateReason.BLOGGER_REGISTRY_NOT_VERIFIED.value

    @pytest.mark.asyncio
    async def test_reads_channel_state_verified(self):
        session = AsyncMock(spec=AsyncSession)
        channel = MagicMock()
        channel.member_count = 20_000
        channel.is_test = False
        channel.is_blogger_registry_verified = True
        channel.blogger_registry_application_number = None
        session.get_one = AsyncMock(return_value=channel)
        placement = MagicMock()

        result = await check_g19(session, placement)

        assert result.passed is True
        assert result.reason_code == GateReason.OK.value

    @pytest.mark.asyncio
    async def test_test_channel_passes(self):
        session = AsyncMock(spec=AsyncSession)
        channel = MagicMock()
        channel.member_count = 100_000
        channel.is_test = True
        channel.is_blogger_registry_verified = False
        channel.blogger_registry_application_number = None
        session.get_one = AsyncMock(return_value=channel)
        placement = MagicMock()

        result = await check_g19(session, placement)

        assert result.passed is True


# ─── Channel-context wrapper — check_g19_channel_add ──────────────────────


class TestCheckG19ChannelAdd:
    """check_g19_channel_add(session, user, channel_data) reads ChannelAddContext."""

    @pytest.mark.asyncio
    async def test_unverified_above_threshold_blocks(self):
        session = AsyncMock(spec=AsyncSession)
        user = MagicMock()
        channel_data = ChannelAddContext(
            telegram_id=-100123,
            username="big_channel",
            member_count=25_000,
        )

        result = await check_g19_channel_add(session, user, channel_data)

        assert result.passed is False
        assert result.reason_code == GateReason.BLOGGER_REGISTRY_NOT_VERIFIED.value

    @pytest.mark.asyncio
    async def test_below_threshold_passes(self):
        session = AsyncMock(spec=AsyncSession)
        user = MagicMock()
        channel_data = ChannelAddContext(
            telegram_id=-100456,
            username="small_channel",
            member_count=2_000,
        )

        result = await check_g19_channel_add(session, user, channel_data)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_verified_passes(self):
        session = AsyncMock(spec=AsyncSession)
        user = MagicMock()
        channel_data = ChannelAddContext(
            telegram_id=-100789,
            username="verified_channel",
            member_count=50_000,
            is_blogger_registry_verified=True,
        )

        result = await check_g19_channel_add(session, user, channel_data)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_pending_review(self):
        session = AsyncMock(spec=AsyncSession)
        user = MagicMock()
        channel_data = ChannelAddContext(
            telegram_id=-100123,
            username="pending_channel",
            member_count=15_000,
            blogger_registry_application_number="GU-2026-99",
        )

        result = await check_g19_channel_add(session, user, channel_data)

        assert result.passed is False
        assert result.reason_code == GateReason.BLOGGER_REGISTRY_PENDING_REVIEW.value


# ─── Registry registration ────────────────────────────────────────────────


class TestRegistryRegistration:
    """G19 registered в _GATE_CHECKERS + _CHANNEL_CONTEXT_GATE_CHECKERS + _CHANNEL_ADD_GATES."""

    def test_g19_in_placement_side_registry(self):
        assert PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED in _GATE_CHECKERS
        assert _GATE_CHECKERS[PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED] is check_g19

    def test_g19_in_channel_context_registry(self):
        assert PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED in _CHANNEL_CONTEXT_GATE_CHECKERS
        assert (
            _CHANNEL_CONTEXT_GATE_CHECKERS[PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED]
            is check_g19_channel_add
        )

    def test_g19_in_channel_add_gates_set(self):
        assert PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED in _CHANNEL_ADD_GATES

    def test_channel_add_gates_initial_size_one(self):
        """Phase B.2 initial: {G19} only. Future per-channel gates extend."""
        assert len(_CHANNEL_ADD_GATES) == 1


# ─── Orchestration — LegalComplianceService.check_gates_for_channel_add ──


class TestCheckGatesForChannelAdd:
    @pytest.mark.asyncio
    async def test_returns_list_with_g19_result(self):
        session = AsyncMock(spec=AsyncSession)
        service = LegalComplianceService(session)
        user = MagicMock()
        channel_data = ChannelAddContext(
            telegram_id=-100123,
            username="test",
            member_count=50_000,
        )

        results = await service.check_gates_for_channel_add(user, channel_data)

        assert len(results) == 1
        assert results[0].gate == PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED
        assert results[0].passed is False
        assert results[0].reason_code == GateReason.BLOGGER_REGISTRY_NOT_VERIFIED.value

    @pytest.mark.asyncio
    async def test_passes_when_verified(self):
        session = AsyncMock(spec=AsyncSession)
        service = LegalComplianceService(session)
        user = MagicMock()
        channel_data = ChannelAddContext(
            telegram_id=-100123,
            username="test",
            member_count=50_000,
            is_blogger_registry_verified=True,
        )

        results = await service.check_gates_for_channel_add(user, channel_data)

        assert len(results) == 1
        assert results[0].passed is True

    @pytest.mark.asyncio
    async def test_passes_when_below_threshold(self):
        session = AsyncMock(spec=AsyncSession)
        service = LegalComplianceService(session)
        user = MagicMock()
        channel_data = ChannelAddContext(
            telegram_id=-100123,
            username="test",
            member_count=3_000,
        )

        results = await service.check_gates_for_channel_add(user, channel_data)

        assert len(results) == 1
        assert results[0].passed is True
