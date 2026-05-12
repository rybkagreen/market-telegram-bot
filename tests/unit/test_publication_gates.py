"""Unit tests for pre-publication gate-checker functions G08-G10.

G08 / G09 read OrdRegistration via OrdRegistrationRepo (mocked via
monkeypatch). G10 reads placement.erid directly — no repo interaction.

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
from src.core.services.gates.publication_gates import check_g08, check_g09, check_g10
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
        "src.core.services.gates.publication_gates.OrdRegistrationRepo",
        lambda session: mock_repo,
    )


# ============================================================================
# G08 — ERID registered
# ============================================================================


async def test_g08_no_registration_row_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-stub provider: missing OrdRegistration must block (Phase 6.B.3)."""
    monkeypatch.setattr("src.core.services.gates.publication_gates.settings.ord_provider", "yandex")
    placement = _fake_placement()
    _patch_repo(monkeypatch, registration=None)

    result = await check_g08(mock_session, placement)

    assert result.gate == PlacementGate.G08_ERID_REGISTERED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.ERID_NOT_REGISTERED.value
    assert result.remediation_url is None


async def test_g08_row_exists_erid_none_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-stub provider: registration row без erid must block."""
    monkeypatch.setattr("src.core.services.gates.publication_gates.settings.ord_provider", "yandex")
    placement = _fake_placement()
    registration = _fake_ord_registration(erid=None)
    _patch_repo(monkeypatch, registration=registration)

    result = await check_g08(mock_session, placement)

    assert result.passed is False
    assert result.reason_code == GateReason.ERID_NOT_REGISTERED.value


async def test_g08_erid_set_returns_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    registration = _fake_ord_registration(erid="STUB-ERID-1-9999")
    _patch_repo(monkeypatch, registration=registration)

    result = await check_g08(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value


async def test_g08_remediation_url_none_on_fail(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-stub provider: failure path must surface no remediation URL."""
    monkeypatch.setattr("src.core.services.gates.publication_gates.settings.ord_provider", "yandex")
    placement = _fake_placement()
    _patch_repo(monkeypatch, registration=None)

    result = await check_g08(mock_session, placement)

    assert result.remediation_url is None


async def test_g08_stub_provider_short_circuits_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stub provider: G08 passes без erid (Phase 6.B.3 deterministic alignment)."""
    placement = _fake_placement(erid=None)
    # Repo not patched — gate must not consult it under stub.
    result = await check_g08(mock_session, placement)

    assert result.gate == PlacementGate.G08_ERID_REGISTERED
    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value


# ============================================================================
# G09 — ORD contract reported
# ============================================================================


async def test_g09_no_registration_row_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    _patch_repo(monkeypatch, registration=None)

    result = await check_g09(mock_session, placement)

    assert result.gate == PlacementGate.G09_ORD_CONTRACT_REPORTED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.ORD_CONTRACT_NOT_REPORTED.value


async def test_g09_row_exists_contract_ord_id_none_returns_blocker(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    registration = _fake_ord_registration(contract_ord_id=None)
    _patch_repo(monkeypatch, registration=registration)

    result = await check_g09(mock_session, placement)

    assert result.passed is False
    assert result.reason_code == GateReason.ORD_CONTRACT_NOT_REPORTED.value


async def test_g09_contract_ord_id_set_returns_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    registration = _fake_ord_registration(contract_ord_id="STUB-CONTRACT-42")
    _patch_repo(monkeypatch, registration=registration)

    result = await check_g09(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value


async def test_g09_remediation_url_none_on_fail(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    placement = _fake_placement()
    _patch_repo(monkeypatch, registration=None)

    result = await check_g09(mock_session, placement)

    assert result.remediation_url is None


# ============================================================================
# G10 — Placement text marked (rendering precondition)
# ============================================================================


async def test_g10_erid_none_returns_blocker(mock_session: MagicMock) -> None:
    placement = _fake_placement(erid=None)

    result = await check_g10(mock_session, placement)

    assert result.gate == PlacementGate.G10_PLACEMENT_TEXT_MARKED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PLACEMENT_TEXT_NOT_MARKED.value
    assert result.remediation_url is None


async def test_g10_erid_set_returns_pass(mock_session: MagicMock) -> None:
    placement = _fake_placement(erid="STUB-ERID-1-9999")

    result = await check_g10(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value


async def test_g10_does_not_call_repos(mock_session: MagicMock) -> None:
    """G10 reads placement.erid in-memory; no DB / repo interaction."""
    placement = _fake_placement(erid="STUB-ERID-1-9999")

    await check_g10(mock_session, placement)

    mock_session.execute.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.flush.assert_not_called()
    mock_session.rollback.assert_not_called()
