"""Unit tests for supplementary-agreement gate-checker G07.

Phase 4 ships G07 with a real body — queries ContractRepo for the placement's
``supplementary_agreement`` rows, requires both advertiser+owner sides at
``contract_status='signed'``. Tests stub `exists_signed_supplementary_both_sides`
to cover three regimes:

* Both sides signed → passed=True, reason_code=OK
* Some side unsigned → passed=False, reason_code=SUPPLEMENTARY_NOT_SIGNED
* No ДС rows exist → passed=False, reason_code=SUPPLEMENTARY_NOT_SIGNED
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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


@pytest.fixture
def patch_repo(monkeypatch: pytest.MonkeyPatch):
    """Patch ContractRepo.exists_signed_supplementary_both_sides at import site."""

    def _set(return_value: bool) -> AsyncMock:
        mock = AsyncMock(return_value=return_value)
        monkeypatch.setattr(
            "src.core.services.gates.agreement_gates.ContractRepo",
            lambda session: MagicMock(exists_signed_supplementary_both_sides=mock),
        )
        return mock

    return _set


# ============================================================================
# G07 — Supplementary agreement signed (Phase 4 real body)
# ============================================================================


async def test_g07_passes_when_both_sides_signed(mock_session: MagicMock, patch_repo) -> None:
    """exists_signed_supplementary_both_sides=True → gate.passed=True, reason=OK."""
    repo_mock = patch_repo(True)
    placement = _fake_placement(placement_id=42)

    result = await check_g07(mock_session, placement)

    assert result.gate == PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED
    assert result.passed is True
    assert result.blocker is False
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None
    repo_mock.assert_awaited_once_with(42)


async def test_g07_fails_when_neither_side_signed(mock_session: MagicMock, patch_repo) -> None:
    """No ДС or all-unsigned → gate.passed=False, reason=SUPPLEMENTARY_NOT_SIGNED."""
    repo_mock = patch_repo(False)
    placement = _fake_placement(placement_id=43)

    result = await check_g07(mock_session, placement)

    assert result.gate == PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.SUPPLEMENTARY_NOT_SIGNED.value
    assert result.remediation_url == "/contracts/supplementary"
    repo_mock.assert_awaited_once_with(43)


async def test_g07_fails_when_only_one_side_signed(mock_session: MagicMock, patch_repo) -> None:
    """Only one of two sides signed → exists_signed_supplementary_both_sides=False
    → gate blocks with SUPPLEMENTARY_NOT_SIGNED. Repo encapsulates the count
    check; gate body simply trusts its boolean return."""
    repo_mock = patch_repo(False)
    placement = _fake_placement(placement_id=44)

    result = await check_g07(mock_session, placement)

    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.SUPPLEMENTARY_NOT_SIGNED.value
    repo_mock.assert_awaited_once_with(44)


async def test_g07_blocker_flag_inverts_with_passed(mock_session: MagicMock, patch_repo) -> None:
    """passed=True ⇒ blocker=False; passed=False ⇒ blocker=True."""
    patch_repo(True)
    result_ok = await check_g07(mock_session, _fake_placement(placement_id=50))
    assert result_ok.passed is True and result_ok.blocker is False

    patch_repo(False)
    result_fail = await check_g07(mock_session, _fake_placement(placement_id=51))
    assert result_fail.passed is False and result_fail.blocker is True
