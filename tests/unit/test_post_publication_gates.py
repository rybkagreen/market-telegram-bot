"""Unit tests for post-publication gate-checker functions G11-G12.

G11 reads placement.message_id directly (no repo). G12 reads
OrdRegistration via OrdRegistrationRepo (mocked via monkeypatch).

Pure mocked using MagicMock(spec=AsyncSession) + monkeypatch on repo
classes. No DB access.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.services.gates.post_publication_gates import check_g11, check_g12
from src.db.models.ord_registration import OrdRegistration
from src.db.models.placement_request import PlacementRequest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def _fake_placement(
    *,
    placement_id: int = 1,
    erid: str | None = "STUB-ERID-1-1234567890",
    ad_text: str = "test ad",
    message_id: int | None = None,
) -> PlacementRequest:
    p = PlacementRequest()
    p.id = placement_id
    p.erid = erid
    p.ad_text = ad_text
    p.message_id = message_id
    return p


def _fake_ord_registration(
    *,
    placement_id: int = 1,
    erid: str | None = "STUB-ERID-1-1234567890",
    status: str = "token_received",
    contract_ord_id: str | None = "STUB-CONTRACT-1",
    reported_at: datetime | None = None,
) -> OrdRegistration:
    r = OrdRegistration()
    r.placement_request_id = placement_id
    r.erid = erid
    r.status = status
    r.contract_ord_id = contract_ord_id
    r.reported_at = reported_at
    return r


def _patch_repo(monkeypatch: pytest.MonkeyPatch, registration: OrdRegistration | None) -> None:
    mock_repo = MagicMock()
    mock_repo.get_by_placement = AsyncMock(return_value=registration)
    monkeypatch.setattr(
        "src.core.services.gates.post_publication_gates.OrdRegistrationRepo",
        lambda session: mock_repo,
    )


# ============================================================================
# G11 — Publication verified (message_id proxy per Marina Q1=(b))
# ============================================================================


async def test_g11_message_id_none_returns_blocker(mock_session: MagicMock) -> None:
    placement = _fake_placement(message_id=None)

    result = await check_g11(mock_session, placement)

    assert result.gate == PlacementGate.G11_PUBLICATION_VERIFIED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PUBLICATION_NOT_VERIFIED.value
    assert result.remediation_url is None


async def test_g11_message_id_set_returns_pass(mock_session: MagicMock) -> None:
    placement = _fake_placement(message_id=12345)

    result = await check_g11(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value


async def test_g11_remediation_url_none_on_fail(mock_session: MagicMock) -> None:
    placement = _fake_placement(message_id=None)

    result = await check_g11(mock_session, placement)

    assert result.remediation_url is None


async def test_g11_does_not_call_repos(mock_session: MagicMock) -> None:
    """G11 reads placement.message_id in-memory; no DB / repo interaction."""
    placement = _fake_placement(message_id=12345)

    await check_g11(mock_session, placement)

    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.flush.assert_not_called()
    mock_session.rollback.assert_not_called()


# ============================================================================
# G12 — Publication reported to ORD (status == "reported")
# ============================================================================


async def test_g12_no_registration_row_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    _patch_repo(monkeypatch, registration=None)

    result = await check_g12(mock_session, placement)

    assert result.gate == PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PUBLICATION_NOT_REPORTED_TO_ORD.value


async def test_g12_status_token_received_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    registration = _fake_ord_registration(status="token_received")
    _patch_repo(monkeypatch, registration=registration)

    result = await check_g12(mock_session, placement)

    assert result.passed is False
    assert result.reason_code == GateReason.PUBLICATION_NOT_REPORTED_TO_ORD.value


async def test_g12_status_erir_confirmed_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    registration = _fake_ord_registration(status="erir_confirmed")
    _patch_repo(monkeypatch, registration=registration)

    result = await check_g12(mock_session, placement)

    assert result.passed is False
    assert result.reason_code == GateReason.PUBLICATION_NOT_REPORTED_TO_ORD.value


async def test_g12_status_reported_returns_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    registration = _fake_ord_registration(status="reported")
    _patch_repo(monkeypatch, registration=registration)

    result = await check_g12(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value


async def test_g12_remediation_url_none_on_fail(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    _patch_repo(monkeypatch, registration=None)

    result = await check_g12(mock_session, placement)

    assert result.remediation_url is None
