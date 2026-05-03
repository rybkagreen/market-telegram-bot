"""Unit tests for pre-payout gate-checker functions G13/G14/G17/G18.

G13 reads placement.deleted_at directly (no repo). G14 reads Act via
ActRepository (mocked via monkeypatch). G17 and G18 are Phase 5 pending
markers — fixed-shape result, no repo interactions.

Pure mocked using MagicMock(spec=AsyncSession) + monkeypatch on repo
classes. No DB access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.services.gates.payout_gates import (
    check_g13,
    check_g14,
    check_g17,
    check_g18,
)
from src.db.models.act import Act
from src.db.models.placement_request import PlacementRequest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def _fake_placement(
    *,
    placement_id: int = 1,
    deleted_at: datetime | None = None,
) -> PlacementRequest:
    p = PlacementRequest()
    p.id = placement_id
    p.deleted_at = deleted_at
    return p


def _fake_act(
    *,
    placement_id: int = 1,
    sign_status: str = "draft",
) -> Act:
    a = Act()
    a.placement_request_id = placement_id
    a.sign_status = sign_status
    return a


def _patch_act_repo(monkeypatch: pytest.MonkeyPatch, act: Act | None) -> None:
    mock_repo = MagicMock()
    mock_repo.get_by_placement_request = AsyncMock(return_value=act)
    monkeypatch.setattr(
        "src.core.services.gates.payout_gates.ActRepository",
        lambda session: mock_repo,
    )


# ============================================================================
# G13 — Publication period elapsed (placement.deleted_at proxy)
# ============================================================================


async def test_g13_deleted_at_none_returns_blocker(mock_session: MagicMock) -> None:
    placement = _fake_placement(deleted_at=None)

    result = await check_g13(mock_session, placement)

    assert result.gate == PlacementGate.G13_PUBLICATION_PERIOD_ELAPSED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PUBLICATION_PERIOD_NOT_ELAPSED.value
    assert result.remediation_url is None


async def test_g13_deleted_at_set_returns_pass(mock_session: MagicMock) -> None:
    placement = _fake_placement(deleted_at=datetime.now(UTC))

    result = await check_g13(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None


async def test_g13_remediation_url_none_on_fail(mock_session: MagicMock) -> None:
    placement = _fake_placement(deleted_at=None)

    result = await check_g13(mock_session, placement)

    assert result.remediation_url is None


async def test_g13_does_not_call_repos(mock_session: MagicMock) -> None:
    """G13 reads placement.deleted_at in-memory; no DB / repo interaction."""
    placement = _fake_placement(deleted_at=datetime.now(UTC))

    await check_g13(mock_session, placement)

    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.flush.assert_not_called()
    mock_session.rollback.assert_not_called()


# ============================================================================
# G14 — Act generated (ActRepository.get_by_placement_request)
# ============================================================================


async def test_g14_no_act_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    _patch_act_repo(monkeypatch, act=None)

    result = await check_g14(mock_session, placement)

    assert result.gate == PlacementGate.G14_ACT_GENERATED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.ACT_NOT_GENERATED.value
    assert result.remediation_url is None


async def test_g14_act_exists_returns_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G14 only checks Act existence; G15 covers signing."""
    placement = _fake_placement()
    _patch_act_repo(monkeypatch, act=_fake_act(sign_status="draft"))

    result = await check_g14(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None


async def test_g14_act_signed_returns_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existence is the only G14 criterion — sign_status='signed' also passes."""
    placement = _fake_placement()
    _patch_act_repo(monkeypatch, act=_fake_act(sign_status="signed"))

    result = await check_g14(mock_session, placement)

    assert result.passed is True
    assert result.reason_code == GateReason.OK.value


async def test_g14_remediation_url_none_on_fail(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    _patch_act_repo(monkeypatch, act=None)

    result = await check_g14(mock_session, placement)

    assert result.remediation_url is None


# ============================================================================
# G17 — VAT obligation handled (Phase 5 pending marker)
# ============================================================================


async def test_g17_returns_phase5_marker(mock_session: MagicMock) -> None:
    """5b.6 ships G17 as Phase 5 pending marker (mirror G06)."""
    placement = _fake_placement()

    result = await check_g17(mock_session, placement)

    assert result.gate == PlacementGate.G17_VAT_OBLIGATION_HANDLED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PHASE5_PENDING.value
    assert result.remediation_url is None


async def test_g17_does_not_call_repos(mock_session: MagicMock) -> None:
    """G17 marker must not touch session/repos — pure return."""
    placement = _fake_placement()

    await check_g17(mock_session, placement)

    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.flush.assert_not_called()
    mock_session.rollback.assert_not_called()


async def test_g17_marker_is_blocker(mock_session: MagicMock) -> None:
    """Phase 5 swap MUST block until then — explicit blocker=True assertion."""
    placement = _fake_placement()

    result = await check_g17(mock_session, placement)

    assert result.blocker is True


# ============================================================================
# G18 — Payout reported to ORD (Phase 5 pending marker)
# ============================================================================


async def test_g18_returns_phase5_marker(mock_session: MagicMock) -> None:
    """5b.6 ships G18 as Phase 5 pending marker (mirror G06 / G17)."""
    placement = _fake_placement()

    result = await check_g18(mock_session, placement)

    assert result.gate == PlacementGate.G18_PAYOUT_REPORTED_TO_ORD
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PHASE5_PENDING.value
    assert result.remediation_url is None


async def test_g18_does_not_call_repos(mock_session: MagicMock) -> None:
    """G18 marker must not touch session/repos — pure return."""
    placement = _fake_placement()

    await check_g18(mock_session, placement)

    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.flush.assert_not_called()
    mock_session.rollback.assert_not_called()


async def test_g18_marker_is_blocker(mock_session: MagicMock) -> None:
    """Phase 5 swap MUST block until then — explicit blocker=True assertion."""
    placement = _fake_placement()

    result = await check_g18(mock_session, placement)

    assert result.blocker is True
