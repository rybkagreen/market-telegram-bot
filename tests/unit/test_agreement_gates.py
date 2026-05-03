"""Unit tests for supplementary-agreement gate-checker G07.

G07 is a Phase 4 pending marker — fixed-shape result, no repo
interactions. Pure mocked using MagicMock(spec=AsyncSession). No DB.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.services.gates.agreement_gates import check_g07
from src.db.models.placement_request import PlacementRequest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def _fake_placement(*, placement_id: int = 1) -> PlacementRequest:
    p = PlacementRequest()
    p.id = placement_id
    return p


# ============================================================================
# G07 — Supplementary agreement signed (Phase 4 pending marker)
# ============================================================================


async def test_g07_returns_phase4_marker(mock_session: MagicMock) -> None:
    """5b.7d ships G07 as Phase 4 pending marker (mirror G17/G18 PHASE5)."""
    placement = _fake_placement()

    result = await check_g07(mock_session, placement)

    assert result.gate == PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PHASE4_PENDING.value
    assert result.remediation_url is None


async def test_g07_does_not_call_repos(mock_session: MagicMock) -> None:
    """G07 marker must not touch session/repos — pure return."""
    placement = _fake_placement()

    await check_g07(mock_session, placement)

    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.flush.assert_not_called()
    mock_session.rollback.assert_not_called()


async def test_g07_marker_is_blocker(mock_session: MagicMock) -> None:
    """Phase 4 swap MUST block until then — explicit blocker=True assertion."""
    placement = _fake_placement()

    result = await check_g07(mock_session, placement)

    assert result.blocker is True
