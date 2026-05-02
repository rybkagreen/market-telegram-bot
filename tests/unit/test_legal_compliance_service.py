"""Unit tests for LegalComplianceService resolution layer.

Resolution methods (gates_for_transition, gates_for_user_role) are pure —
they don't touch self._session. Tests use MagicMock(spec=AsyncSession)
to instantiate the service; no DB, no async fixtures, no testcontainer.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.services.legal_compliance_service import (
    _TRANSITION_GATES,
    LegalComplianceService,
)
from src.core.services.placement_transition_service import _ALLOW_LIST
from src.db.models.placement_request import PlacementStatus


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
    expected_pairs = {
        (from_s, to_s)
        for from_s, allowed in _ALLOW_LIST.items()
        for to_s in allowed
    }
    actual_pairs = set(_TRANSITION_GATES.keys())
    missing = expected_pairs - actual_pairs
    extra = actual_pairs - expected_pairs
    assert not missing, f"Allow-list pairs missing from gates table: {missing}"
    assert not extra, f"Gates table has stale pairs not in allow-list: {extra}"
