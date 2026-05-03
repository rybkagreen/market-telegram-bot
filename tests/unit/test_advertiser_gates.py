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
from src.core.services.gates.advertiser_gates import check_g01, check_g02, check_g03
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


# ============================================================================
# G02 — Framework contract signed
# ============================================================================


async def test_g02_unsigned_returns_blocker(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.ContractRepo",
        lambda session: mock_repo,
    )

    result = await check_g02(mock_session, placement)

    assert result.gate == PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED
    assert result.passed is False
    assert result.blocker is True
    assert result.reason_code == GateReason.FRAMEWORK_CONTRACT_UNSIGNED.value
    assert result.remediation_url == portal_routes.CONTRACTS


async def test_g02_signed_returns_pass(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.ContractRepo",
        lambda session: mock_repo,
    )

    result = await check_g02(mock_session, placement)

    assert result.passed is True
    assert result.blocker is True
    assert result.reason_code == GateReason.OK.value
    assert result.remediation_url is None


async def test_g02_calls_repo_with_advertiser_role(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify role='advertiser' passed (not 'owner' or default)."""
    mock_repo = MagicMock()
    mock_repo.has_signed_framework = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.ContractRepo",
        lambda session: mock_repo,
    )

    await check_g02(mock_session, placement)

    mock_repo.has_signed_framework.assert_awaited_once_with(
        user_id=42, role="advertiser"
    )


# ============================================================================
# G03 — Legal status compliant (interim — checksum-only)
# ============================================================================


async def test_g03_legal_profile_missing_is_informational(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _fake_user(legal_profile=None)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g03(mock_session, placement)

    assert result.passed is False
    assert result.blocker is False  # informational
    assert result.reason_code == GateReason.LEGAL_PROFILE_MISSING.value


async def test_g03_user_not_found_is_informational(
    mock_session: MagicMock, placement: PlacementRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g03(mock_session, placement)

    assert result.passed is False
    assert result.blocker is False
    assert result.reason_code == GateReason.LEGAL_PROFILE_MISSING.value


# Real Russian INN/OGRN test values (publicly known; validated checksums)
VALID_INN_LE = "7707083893"  # 10 digits
VALID_INN_INDIVIDUAL = "500100732259"  # 12 digits
VALID_OGRN = "1027700132195"  # 13 digits
VALID_OGRNIP = "304500116000157"  # 15 digits

INVALID_CHECKSUM_INN_10 = "7707083890"
INVALID_CHECKSUM_INN_12 = "500100732250"
INVALID_CHECKSUM_OGRN = "1027700132190"
INVALID_CHECKSUM_OGRNIP = "304500116000150"


@pytest.mark.parametrize(
    "legal_status, inn, ogrn, ogrnip, expected_passed, expected_reason",
    [
        # individual — INN optional
        ("individual", None, None, None, True, GateReason.OK.value),
        ("individual", VALID_INN_INDIVIDUAL, None, None, True, GateReason.OK.value),
        (
            "individual",
            INVALID_CHECKSUM_INN_12,
            None,
            None,
            False,
            GateReason.INN_CHECKSUM_INVALID.value,
        ),
        # self_employed
        ("self_employed", None, None, None, False, GateReason.INN_MISSING.value),
        ("self_employed", VALID_INN_INDIVIDUAL, None, None, True, GateReason.OK.value),
        (
            "self_employed",
            INVALID_CHECKSUM_INN_12,
            None,
            None,
            False,
            GateReason.INN_CHECKSUM_INVALID.value,
        ),
        # individual_entrepreneur
        ("individual_entrepreneur", None, None, None, False, GateReason.INN_MISSING.value),
        (
            "individual_entrepreneur",
            VALID_INN_INDIVIDUAL,
            None,
            None,
            False,
            GateReason.OGRNIP_MISSING.value,
        ),
        (
            "individual_entrepreneur",
            VALID_INN_INDIVIDUAL,
            None,
            VALID_OGRNIP,
            True,
            GateReason.OK.value,
        ),
        (
            "individual_entrepreneur",
            VALID_INN_INDIVIDUAL,
            None,
            INVALID_CHECKSUM_OGRNIP,
            False,
            GateReason.OGRNIP_CHECKSUM_INVALID.value,
        ),
        # legal_entity
        ("legal_entity", None, None, None, False, GateReason.INN_MISSING.value),
        ("legal_entity", VALID_INN_LE, None, None, False, GateReason.OGRN_MISSING.value),
        ("legal_entity", VALID_INN_LE, VALID_OGRN, None, True, GateReason.OK.value),
        (
            "legal_entity",
            VALID_INN_LE,
            INVALID_CHECKSUM_OGRN,
            None,
            False,
            GateReason.OGRN_CHECKSUM_INVALID.value,
        ),
        # Unknown status
        (
            "freelancer",
            VALID_INN_INDIVIDUAL,
            None,
            None,
            False,
            GateReason.UNKNOWN_LEGAL_STATUS.value,
        ),
    ],
    ids=[
        "individual_no_inn",
        "individual_with_valid_inn",
        "individual_with_invalid_inn_checksum",
        "se_no_inn",
        "se_valid_inn",
        "se_invalid_inn_checksum",
        "ie_no_inn",
        "ie_valid_inn_no_ogrnip",
        "ie_valid_all",
        "ie_invalid_ogrnip_checksum",
        "le_no_inn",
        "le_valid_inn_no_ogrn",
        "le_valid_all",
        "le_invalid_ogrn_checksum",
        "unknown_status_blocker",
    ],
)
async def test_g03_per_status_checksum_logic(
    mock_session: MagicMock,
    placement: PlacementRequest,
    monkeypatch: pytest.MonkeyPatch,
    legal_status: str,
    inn: str | None,
    ogrn: str | None,
    ogrnip: str | None,
    expected_passed: bool,
    expected_reason: str,
) -> None:
    profile = _fake_legal_profile(legal_status=legal_status, inn=inn, ogrn=ogrn, ogrnip=ogrnip)
    user = _fake_user(legal_profile=profile, completed=True)
    mock_repo = MagicMock()
    mock_repo.get_with_legal_profile = AsyncMock(return_value=user)
    monkeypatch.setattr(
        "src.core.services.gates.advertiser_gates.UserRepository",
        lambda session: mock_repo,
    )

    result = await check_g03(mock_session, placement)

    assert result.gate == PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT
    assert result.passed is expected_passed
    assert result.reason_code == expected_reason
