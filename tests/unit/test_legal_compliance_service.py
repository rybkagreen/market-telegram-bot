"""Unit tests for LegalComplianceService resolution layer.

Resolution methods (gates_for_transition, gates_for_user_role) are pure —
they don't touch self._session. Tests use MagicMock(spec=AsyncSession)
to instantiate the service; no DB, no async fixtures, no testcontainer.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.core.services.legal_compliance_service import (
    _TRANSITION_GATES,
    LegalComplianceService,
)
from src.core.services.placement_transition_service import _ALLOW_LIST
from src.db.models.placement_request import PlacementStatus
from src.db.models.user import User


@pytest.fixture
def service() -> LegalComplianceService:
    """LegalComplianceService with mocked session — resolution doesn't use session."""
    return LegalComplianceService(session=MagicMock(spec=AsyncSession))


# ============================================================================
# gates_for_transition — table lookup
# ============================================================================


@pytest.mark.parametrize(
    "from_status, to_status, expected_gates",
    [
        # No-gate transitions (15)
        (PlacementStatus.pending_owner, PlacementStatus.counter_offer, set()),
        (PlacementStatus.pending_owner, PlacementStatus.cancelled, set()),
        (PlacementStatus.counter_offer, PlacementStatus.pending_owner, set()),
        (PlacementStatus.counter_offer, PlacementStatus.cancelled, set()),
        (PlacementStatus.pending_payment, PlacementStatus.escrow, set()),
        (PlacementStatus.pending_payment, PlacementStatus.cancelled, set()),
        (PlacementStatus.escrow, PlacementStatus.failed, set()),
        (PlacementStatus.escrow, PlacementStatus.failed_permissions, set()),
        (PlacementStatus.escrow, PlacementStatus.refunded, set()),
        (PlacementStatus.escrow, PlacementStatus.cancelled, set()),
        (PlacementStatus.published, PlacementStatus.failed, set()),
        (PlacementStatus.published, PlacementStatus.refunded, set()),
        (PlacementStatus.published, PlacementStatus.cancelled, set()),
        (PlacementStatus.failed, PlacementStatus.refunded, set()),
        (PlacementStatus.failed_permissions, PlacementStatus.refunded, set()),
        # Pre-escrow (G07 = Phase 4 stub but in resolution table)
        (
            PlacementStatus.pending_owner,
            PlacementStatus.pending_payment,
            {PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED},
        ),
        (
            PlacementStatus.counter_offer,
            PlacementStatus.pending_payment,
            {PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED},
        ),
        # Pre-publication
        (
            PlacementStatus.escrow,
            PlacementStatus.published,
            {
                PlacementGate.G08_ERID_REGISTERED,
                PlacementGate.G09_ORD_CONTRACT_REPORTED,
                PlacementGate.G10_PLACEMENT_TEXT_MARKED,
            },
        ),
        # Post-publication
        (
            PlacementStatus.published,
            PlacementStatus.completed,
            {
                PlacementGate.G11_PUBLICATION_VERIFIED,
                PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD,
            },
        ),
    ],
)
def test_gates_for_transition_returns_expected(
    service: LegalComplianceService,
    from_status: PlacementStatus,
    to_status: PlacementStatus,
    expected_gates: set[PlacementGate],
) -> None:
    result = service.gates_for_transition(from_status, to_status)
    assert set(result) == expected_gates


@pytest.mark.parametrize(
    "from_status, to_status",
    [
        # Not in allow-list at all
        (PlacementStatus.pending_owner, PlacementStatus.published),
        # Self-transition (no rule for it)
        (PlacementStatus.escrow, PlacementStatus.escrow),
        # Terminal trying to leave
        (PlacementStatus.completed, PlacementStatus.published),
    ],
)
def test_gates_for_transition_unknown_pair_raises(
    service: LegalComplianceService,
    from_status: PlacementStatus,
    to_status: PlacementStatus,
) -> None:
    with pytest.raises(ValueError, match="not in the gates resolution table"):
        service.gates_for_transition(from_status, to_status)


def test_table_keys_match_allow_list() -> None:
    """Critical invariant: _TRANSITION_GATES keys exactly mirror _ALLOW_LIST.

    If this fails, either:
    - A new transition was added to _ALLOW_LIST without a corresponding
      gates entry (silent missing-precondition bug)
    - A transition was removed from _ALLOW_LIST but the gates entry remains
      (dead entry)
    """
    expected_pairs = {(from_s, to_s) for from_s, allowed in _ALLOW_LIST.items() for to_s in allowed}
    actual_pairs = set(_TRANSITION_GATES.keys())
    missing = expected_pairs - actual_pairs
    extra = actual_pairs - expected_pairs
    assert not missing, f"Allow-list pairs missing from gates table: {missing}"
    assert not extra, f"Gates table has stale pairs not in allow-list: {extra}"


# ============================================================================
# gates_for_user_role — role lookup
# ============================================================================


def test_gates_for_user_role_owner_returns_g04_g05_g06(
    service: LegalComplianceService,
) -> None:
    result = service.gates_for_user_role("owner")
    assert set(result) == {
        PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
        PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
        PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
    }


def test_gates_for_user_role_advertiser_returns_g01_g02_g03(
    service: LegalComplianceService,
) -> None:
    result = service.gates_for_user_role("advertiser")
    assert set(result) == {
        PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
        PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED,
        PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT,
    }


@pytest.mark.parametrize("bad_role", ["admin", "random"])
def test_gates_for_user_role_unknown_raises(
    service: LegalComplianceService,
    bad_role: str,
) -> None:
    with pytest.raises(ValueError, match="Unknown role"):
        service.gates_for_user_role(bad_role)  # type: ignore[arg-type]


# ============================================================================
# 5b.7a — check_gate_for_user / check_gates_for_user_role dispatchers
# ============================================================================


def _fake_user(user_id: int = 42) -> User:
    u = User()
    u.id = user_id
    return u


def _ok_result(gate: PlacementGate) -> GateResult:
    return GateResult(gate=gate, passed=True, blocker=True, reason_code="ok")


@pytest.mark.asyncio
async def test_check_gate_for_user_owner_g04_dispatches(
    service: LegalComplianceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G04 dispatch routes to the owner_gates.check_g04_user implementation."""
    user = _fake_user()
    expected = _ok_result(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE)
    mock_checker = AsyncMock(return_value=expected)
    monkeypatch.setitem(
        __import__(
            "src.core.services.legal_compliance_service", fromlist=["_USER_GATE_CHECKERS"]
        )._USER_GATE_CHECKERS,
        PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
        mock_checker,
    )

    result = await service.check_gate_for_user(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE, user)

    assert result is expected
    mock_checker.assert_awaited_once_with(service._session, user)


@pytest.mark.asyncio
async def test_check_gate_for_user_unknown_gate_raises(
    service: LegalComplianceService,
) -> None:
    """Gates not in _USER_GATE_CHECKERS raise NotImplementedError.

    G07-G18 operate on placement state and have no user-side semantic.
    """
    user = _fake_user()
    with pytest.raises(NotImplementedError, match="No user-role gate-checker"):
        await service.check_gate_for_user(PlacementGate.G08_ERID_REGISTERED, user)


@pytest.mark.asyncio
async def test_check_gates_for_user_role_owner_returns_three_results(
    service: LegalComplianceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner role evaluates G04+G05+G06 — three gate results in order."""
    user = _fake_user()
    target_module = __import__(
        "src.core.services.legal_compliance_service", fromlist=["_USER_GATE_CHECKERS"]
    )
    for gate in (
        PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
        PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
        PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
    ):
        monkeypatch.setitem(
            target_module._USER_GATE_CHECKERS,
            gate,
            AsyncMock(return_value=_ok_result(gate)),
        )

    results = await service.check_gates_for_user_role(user, role="owner")

    assert len(results) == 3
    assert {r.gate for r in results} == {
        PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
        PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
        PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
    }


@pytest.mark.asyncio
async def test_check_gates_for_user_role_advertiser_returns_three_results(
    service: LegalComplianceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Advertiser role evaluates G01+G02+G03."""
    user = _fake_user()
    target_module = __import__(
        "src.core.services.legal_compliance_service", fromlist=["_USER_GATE_CHECKERS"]
    )
    for gate in (
        PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
        PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED,
        PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT,
    ):
        monkeypatch.setitem(
            target_module._USER_GATE_CHECKERS,
            gate,
            AsyncMock(return_value=_ok_result(gate)),
        )

    results = await service.check_gates_for_user_role(user, role="advertiser")

    assert len(results) == 3
    assert {r.gate for r in results} == {
        PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
        PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED,
        PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT,
    }
