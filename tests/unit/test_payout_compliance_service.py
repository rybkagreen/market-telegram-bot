"""Unit tests for PayoutComplianceService skeleton (5b.7b).

The service ships in skeleton form: dispatcher logic is real, registries
are empty. Phase 5 populates registries (no method-body changes for the
wired dispatchers). Tests verify:

* dispatcher logic is real (monkeypatch a registry entry → check_gate
  routes correctly), proving Phase 5 only needs to populate registries
* empty registries raise ValueError / NotImplementedError as designed
* check_gates_for_payout_create raises NotImplementedError (Phase 5
  decides dispatch path — see service docstring)

Resolution methods don't touch self._session — tests use
MagicMock(spec=AsyncSession). No DB, no async fixtures, no testcontainer.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.core.services import payout_compliance_service as pcs_module
from src.core.services.payout_compliance_service import PayoutComplianceService
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.user import User


@pytest.fixture
def service() -> PayoutComplianceService:
    """PayoutComplianceService with mocked session — resolution doesn't use session."""
    return PayoutComplianceService(session=MagicMock(spec=AsyncSession))


def _fake_payout(status: PayoutStatus = PayoutStatus.pending) -> PayoutRequest:
    p = PayoutRequest()
    p.id = 1
    p.owner_id = 42
    p.status = status
    return p


def _fake_user(user_id: int = 42) -> User:
    u = User()
    u.id = user_id
    return u


def _ok_result(gate: PlacementGate) -> GateResult:
    return GateResult(gate=gate, passed=True, blocker=True, reason_code="ok")


# ============================================================================
# Skeleton smoke
# ============================================================================


def test_init_accepts_session() -> None:
    """Smoke: constructor accepts AsyncSession mock without error."""
    session = MagicMock(spec=AsyncSession)
    svc = PayoutComplianceService(session=session)
    assert svc._session is session


# ============================================================================
# Empty-registry semantics
# ============================================================================


def test_gates_for_payout_transition_empty_table_raises_value_error(
    service: PayoutComplianceService,
) -> None:
    """Every transition lookup raises until Phase 5 fills _PAYOUT_TRANSITION_GATES."""
    with pytest.raises(ValueError, match="not in the gates resolution table"):
        service.gates_for_payout_transition(PayoutStatus.pending, PayoutStatus.processing)


def test_gates_for_payout_create_empty_table_raises_value_error(
    service: PayoutComplianceService,
) -> None:
    """Role lookup raises until Phase 5 fills _PAYOUT_CREATE_GATES."""
    with pytest.raises(ValueError, match="not in the gates resolution table"):
        service.gates_for_payout_create(role="owner")


@pytest.mark.asyncio
async def test_check_gate_unmapped_gate_raises_not_implemented(
    service: PayoutComplianceService,
) -> None:
    """Empty _PAYOUT_GATE_CHECKERS → every check_gate raises NotImplementedError."""
    payout = _fake_payout()
    with pytest.raises(NotImplementedError, match="No payout gate-checker"):
        await service.check_gate(PlacementGate.G13_PUBLICATION_PERIOD_ELAPSED, payout)


@pytest.mark.asyncio
async def test_check_gates_for_payout_transition_propagates_value_error(
    service: PayoutComplianceService,
) -> None:
    """Empty resolution table → inner gates_for_payout_transition's ValueError surfaces."""
    payout = _fake_payout(status=PayoutStatus.pending)
    with pytest.raises(ValueError, match="not in the gates resolution table"):
        await service.check_gates_for_payout_transition(payout, PayoutStatus.processing)


@pytest.mark.asyncio
async def test_check_gates_for_payout_create_raises_not_implemented(
    service: PayoutComplianceService,
) -> None:
    """check_gates_for_payout_create raises by design — Phase 5 chooses dispatch path."""
    user = _fake_user()
    with pytest.raises(NotImplementedError, match="lands in Phase 5"):
        await service.check_gates_for_payout_create(user, role="owner")


# ============================================================================
# Dispatcher logic is REAL — Phase 5 only populates registries
# ============================================================================


@pytest.mark.asyncio
async def test_dispatch_after_monkeypatch_registry(
    service: PayoutComplianceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Monkeypatch a checker into _PAYOUT_GATE_CHECKERS → check_gate routes correctly.

    Proves the dispatch logic ships as permanent code (Option A skeleton).
    Phase 5 only needs to populate the registry; no method-body changes.
    """
    payout = _fake_payout()
    expected = _ok_result(PlacementGate.G13_PUBLICATION_PERIOD_ELAPSED)
    mock_checker = AsyncMock(return_value=expected)
    monkeypatch.setitem(
        pcs_module._PAYOUT_GATE_CHECKERS,
        PlacementGate.G13_PUBLICATION_PERIOD_ELAPSED,
        mock_checker,
    )

    result = await service.check_gate(PlacementGate.G13_PUBLICATION_PERIOD_ELAPSED, payout)

    assert result is expected
    mock_checker.assert_awaited_once_with(service._session, payout)
