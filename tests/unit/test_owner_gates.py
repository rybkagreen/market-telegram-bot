"""Unit tests for owner-side gate-checker functions G04-G06.

Symmetric mirror of tests/unit/test_advertiser_gates.py with
placement.owner_id (instead of advertiser_id) and role="owner" (instead
of "advertiser"). G06 is a Phase 5 marker — fixed-shape result, no repo
interactions.

Pure mocked using MagicMock(spec=AsyncSession) + monkeypatch on repo
classes. No DB access.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import portal_routes
from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.services.gates.owner_gates import (
    check_g04,
    check_g04_user,
    check_g05,
    check_g05_user,
    check_g06,
    check_g06_user,
)
from src.db.models.legal_profile import LegalProfile
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def placement() -> PlacementRequest:
    p = PlacementRequest()
    p.id = 1
    p.owner_id = 42
    return p


def _fake_user(
    *,
    user_id: int = 42,
    legal_profile: LegalProfile | None = None,
    completed: bool = False,
) -> User:
    u = User()
    u.id = user_id
    u.legal_status_completed = completed
    u.legal_profile = legal_profile
    return u


def _fake_legal_profile(
    *,
    legal_status: str = "individual",
    inn: str | None = None,
    ogrn: str | None = None,
    ogrnip: str | None = None,
) -> LegalProfile:
    p = LegalProfile()
    p.legal_status = legal_status
    p.inn = inn
    p.ogrn = ogrn
    p.ogrnip = ogrnip
    return p


# ============================================================================
# G04 — Owner legal profile complete
# ============================================================================


async def test_g04_user_not_found_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g04(mock_session, placement)

    assert result.gate == PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.USER_NOT_FOUND.value
    assert result.remediation_url is None


async def test_g04_legal_profile_missing_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(legal_profile=None, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g04(mock_session, placement)

    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.LEGAL_PROFILE_MISSING.value
    assert result.remediation_url == portal_routes.LEGAL_PROFILE


async def test_g04_legal_profile_incomplete_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _fake_legal_profile(legal_status="legal_entity")
    user = _fake_user(legal_profile=profile, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g04(mock_session, placement)

    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.LEGAL_PROFILE_INCOMPLETE.value
    assert result.remediation_url == portal_routes.LEGAL_PROFILE


async def test_g04_complete_returns_pass(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _fake_legal_profile(legal_status="legal_entity", inn="7707083893")
    user = _fake_user(legal_profile=profile, completed=True)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g04(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None


async def test_g04_remediation_url_points_to_legal_profile(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(legal_profile=None, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g04(mock_session, placement)

    assert result.remediation_url == "/legal-profile"


# ============================================================================
# G05 — Owner framework contract signed
# ============================================================================


async def test_g05_unsigned_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.ContractRepo",
        lambda session: mock_repo,
    )

    result = await check_g05(mock_session, placement)

    assert result.gate == PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.FRAMEWORK_CONTRACT_UNSIGNED.value
    assert result.remediation_url == portal_routes.CONTRACTS


async def test_g05_signed_returns_pass(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.ContractRepo",
        lambda session: mock_repo,
    )

    result = await check_g05(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None


async def test_g05_calls_repo_with_owner_role(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify role='owner' passed (not 'advertiser' or default)."""
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.ContractRepo",
        lambda session: mock_repo,
    )

    await check_g05(mock_session, placement)

    mock_repo.has_signed_framework.assert_awaited_once_with(user_id=42, role="owner")


# ============================================================================
# G06 — Owner payout method valid (5b.7a real-now lookup)
# ============================================================================


def _patch_payout_repo(
    monkeypatch: pytest.MonkeyPatch,
    *,
    valid_return: object | None,
    by_owner_return: list[object],
) -> MagicMock:
    mock_repo = MagicMock()
    mock_repo.get_valid_for_owner = AsyncMock(return_value=valid_return)
    mock_repo.get_by_owner = AsyncMock(return_value=by_owner_return)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.PayoutRepository",
        lambda session: mock_repo,
    )
    return mock_repo


async def test_g06_no_payout_records_passes_pre_setup(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner without any PayoutRequest passes — pre-payout-setup channel-add valid."""
    _patch_payout_repo(monkeypatch, valid_return=None, by_owner_return=[])

    result = await check_g06(mock_session, placement)

    assert result.gate == PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID
    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None


async def test_g06_valid_payout_method_passes(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner with at least one valid PayoutRequest passes."""
    valid_payout = MagicMock()
    _patch_payout_repo(monkeypatch, valid_return=valid_payout, by_owner_return=[valid_payout])

    result = await check_g06(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value


async def test_g06_payout_records_but_none_valid_fails(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner attempted payout setup but all records invalid → FAIL."""
    invalid_payout = MagicMock()
    _patch_payout_repo(monkeypatch, valid_return=None, by_owner_return=[invalid_payout])

    result = await check_g06(mock_session, placement)

    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PAYOUT_METHOD_INVALID.value
    assert result.remediation_url is None


async def test_g06_skips_get_by_owner_when_valid_found(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When get_valid_for_owner returns non-None, skip the secondary count query."""
    valid_payout = MagicMock()
    repo = _patch_payout_repo(monkeypatch, valid_return=valid_payout, by_owner_return=[])

    await check_g06(mock_session, placement)

    repo.get_valid_for_owner.assert_awaited_once_with(placement.owner_id)
    repo.get_by_owner.assert_not_called()


# ============================================================================
# 5b.7a — User-side variants (check_g04_user / check_g05_user / check_g06_user)
# ============================================================================


async def test_check_g04_user_complete_returns_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User-side G04 variant: same semantics as placement-side."""
    profile = _fake_legal_profile(legal_status="legal_entity", inn="7707083893")
    user = _fake_user(legal_profile=profile, completed=True)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g04_user(mock_session, user)

    assert result.passed is True
    assert result.reason_code == GateReason.OK.value


async def test_check_g04_user_missing_profile_fails(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(legal_profile=None, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g04_user(mock_session, user)

    assert result.passed is False
    assert result.reason_code == GateReason.LEGAL_PROFILE_MISSING.value
    assert result.remediation_url == portal_routes.LEGAL_PROFILE


async def test_check_g04_user_passes_user_id_to_repo(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify user-side variant uses user.id, not placement.owner_id."""
    user = _fake_user(user_id=999, legal_profile=None, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.UserRepository",
        lambda session: mock_repo,
    )

    await check_g04_user(mock_session, user)

    mock_repo.get_with_legal_profile.assert_awaited_once_with(999)


async def test_check_g05_user_signed_returns_pass(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(user_id=42)
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.ContractRepo",
        lambda session: mock_repo,
    )

    result = await check_g05_user(mock_session, user)

    assert result.passed is True
    assert result.reason_code == GateReason.OK.value


async def test_check_g05_user_passes_owner_role(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G05 user-side must call repo with role='owner'."""
    user = _fake_user(user_id=42)
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.core.services.gates.owner_gates.ContractRepo",
        lambda session: mock_repo,
    )

    await check_g05_user(mock_session, user)

    mock_repo.has_signed_framework.assert_awaited_once_with(user_id=42, role="owner")


async def test_check_g06_user_no_payout_method_passes(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User-side G06: pre-setup owner passes (channel-add valid)."""
    user = _fake_user(user_id=42)
    _patch_payout_repo(monkeypatch, valid_return=None, by_owner_return=[])

    result = await check_g06_user(mock_session, user)

    assert result.passed is True
    assert result.reason_code == GateReason.OK.value


async def test_check_g06_user_valid_method_passes(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(user_id=42)
    valid_payout = MagicMock()
    _patch_payout_repo(monkeypatch, valid_return=valid_payout, by_owner_return=[valid_payout])

    result = await check_g06_user(mock_session, user)

    assert result.passed is True
    assert result.reason_code == GateReason.OK.value


async def test_check_g06_user_invalid_method_fails(
    mock_session: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User-side G06: post-setup with all-invalid records → FAIL."""
    user = _fake_user(user_id=42)
    invalid_payout = MagicMock()
    _patch_payout_repo(monkeypatch, valid_return=None, by_owner_return=[invalid_payout])

    result = await check_g06_user(mock_session, user)

    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.PAYOUT_METHOD_INVALID.value
    assert result.remediation_url is None
