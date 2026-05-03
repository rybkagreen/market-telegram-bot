"""Unit tests for advertiser-side gate-checker functions G01-G03.

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
from src.core.services.gates.advertiser_gates import check_g01
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
    p.advertiser_id = 42
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
# G01 — Advertiser legal profile complete
# ============================================================================


async def test_g01_user_not_found_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g01(mock_session, placement)

    assert result.gate == PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.USER_NOT_FOUND.value
    assert result.remediation_url is None


async def test_g01_legal_profile_missing_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(legal_profile=None, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g01(mock_session, placement)

    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.LEGAL_PROFILE_MISSING.value
    assert result.remediation_url == portal_routes.LEGAL_PROFILE


async def test_g01_legal_profile_incomplete_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _fake_legal_profile(legal_status="legal_entity")
    user = _fake_user(legal_profile=profile, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g01(mock_session, placement)

    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.LEGAL_PROFILE_INCOMPLETE.value
    assert result.remediation_url == portal_routes.LEGAL_PROFILE


async def test_g01_complete_returns_pass(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _fake_legal_profile(legal_status="legal_entity", inn="7707083893")
    user = _fake_user(legal_profile=profile, completed=True)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g01(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None


async def test_g01_remediation_url_points_to_legal_profile(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(legal_profile=None, completed=False)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g01(mock_session, placement)

    assert result.remediation_url == "/legal-profile"
