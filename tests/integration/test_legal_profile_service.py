"""Tests for LegalProfileService — CRUD and completeness across all 4 legal statuses.

Lives under tests/unit/ (per project convention), but requires the real
testcontainer/DATABASE_URL Postgres via `db_session` because LegalProfile uses
JSONB-adjacent encrypted columns that are awkward on SQLite.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security.field_encryption import HashableEncryptedString
from src.core.services.legal_profile_service import LegalProfileService
from src.db.models.legal_profile import LegalProfile
from src.db.models.user import User

pytestmark = pytest.mark.asyncio

ALL_STATUSES = ["legal_entity", "individual_entrepreneur", "self_employed", "individual"]


async def _make_user(db_session: AsyncSession, telegram_id: int) -> User:
    user = User(
        telegram_id=telegram_id,
        username=f"u_{telegram_id}",
        first_name="Test",
        balance_rub=Decimal("0"),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ────────────────────────────────────────────
# CRUD по 4 статусам
# ────────────────────────────────────────────


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_create_profile_persists_required_fields(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_100 + ALL_STATUSES.index(status))
    svc = LegalProfileService(db_session)
    data = legal_profile_data(status)

    profile = await svc.create_profile(user.id, data)
    await db_session.flush()

    assert profile.user_id == user.id
    assert profile.legal_status == status
    # legal_name is required for every status
    assert profile.legal_name == data["legal_name"]


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_check_completeness_true_on_full_data(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_200 + ALL_STATUSES.index(status))
    svc = LegalProfileService(db_session)
    await svc.create_profile(user.id, legal_profile_data(status))
    await db_session.flush()

    # user.legal_status_completed is flipped by check_completeness inside create_profile
    user_fresh = await db_session.get(User, user.id)
    assert user_fresh is not None
    assert user_fresh.legal_status_completed is True


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_check_completeness_false_on_missing_field(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_300 + ALL_STATUSES.index(status))
    svc = LegalProfileService(db_session)
    data = legal_profile_data(status)
    # Remove one required field
    fields_map = await svc.get_required_fields(status)
    required = fields_map["fields"]
    # Drop the first required field from the payload
    dropped = required[0]
    if dropped in data:
        del data[dropped]

    await svc.create_profile(user.id, data)
    await db_session.flush()

    user_fresh = await db_session.get(User, user.id)
    assert user_fresh is not None
    assert user_fresh.legal_status_completed is False


async def test_auto_tax_regime_self_employed(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_401)
    svc = LegalProfileService(db_session)
    data = legal_profile_data("self_employed")
    # Even if caller did not set tax_regime, service forces "npd"
    data.pop("tax_regime", None)
    profile = await svc.create_profile(user.id, data)
    assert profile.tax_regime == "npd"


async def test_auto_tax_regime_individual(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_402)
    svc = LegalProfileService(db_session)
    data = legal_profile_data("individual")
    profile = await svc.create_profile(user.id, data)
    assert profile.tax_regime == "ndfl"


async def test_inn_hash_is_populated(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_403)
    svc = LegalProfileService(db_session)
    data = legal_profile_data("legal_entity")
    profile = await svc.create_profile(user.id, data)
    assert profile.inn_hash is not None
    # inn_hash is HMAC-SHA256 hex → 64 chars
    assert len(profile.inn_hash) == 64
    # Hash must match what HashableEncryptedString.hash_value would produce
    assert profile.inn_hash == HashableEncryptedString.hash_value(data["inn"])


async def test_encrypted_fields_round_trip(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    """bank_account / passport_* / inn are stored encrypted but read back plaintext."""
    user = await _make_user(db_session, telegram_id=950_000_404)
    svc = LegalProfileService(db_session)
    data = legal_profile_data("legal_entity")
    await svc.create_profile(user.id, data)
    await db_session.flush()

    # Re-fetch from DB via fresh query to force decryption path
    result = await db_session.execute(
        select(LegalProfile).where(LegalProfile.user_id == user.id)
    )
    fetched = result.scalar_one()
    assert fetched.inn == data["inn"]
    assert fetched.bank_account == data["bank_account"]
    assert fetched.bank_corr_account == data["bank_corr_account"]


async def test_update_profile_recomputes_inn_hash(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_405)
    svc = LegalProfileService(db_session)
    data = legal_profile_data("legal_entity")
    await svc.create_profile(user.id, data)
    await db_session.flush()

    # Switch to a different valid INN — hash should change
    from tests.conftest import make_valid_inn10

    new_inn = make_valid_inn10("500100732")  # different prefix
    profile = await svc.update_profile(user.id, {"inn": new_inn})
    assert profile.inn == new_inn
    assert profile.inn_hash == HashableEncryptedString.hash_value(new_inn)


# ────────────────────────────────────────────
# upload_scan
# ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("scan_type", "field"),
    [
        ("inn", "inn_scan_file_id"),
        ("passport", "passport_scan_file_id"),
        ("self_employed_cert", "self_employed_cert_file_id"),
        ("company_doc", "company_doc_file_id"),
    ],
)
async def test_upload_scan_sets_file_id(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    scan_type: str,
    field: str,
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_500 + hash(scan_type) % 1000)
    svc = LegalProfileService(db_session)
    await svc.create_profile(user.id, legal_profile_data("legal_entity"))

    await svc.upload_scan(user.id, scan_type, "TELEGRAM_FILE_ID_123")
    await db_session.flush()

    result = await db_session.execute(
        select(LegalProfile).where(LegalProfile.user_id == user.id)
    )
    profile = result.scalar_one()
    assert getattr(profile, field) == "TELEGRAM_FILE_ID_123"


async def test_upload_scan_unknown_type_raises(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_599)
    svc = LegalProfileService(db_session)
    await svc.create_profile(user.id, legal_profile_data("legal_entity"))

    with pytest.raises(ValueError, match="Unknown scan_type"):
        await svc.upload_scan(user.id, "driver_license", "FILE_ID")


# ────────────────────────────────────────────
# get_required_fields
# ────────────────────────────────────────────


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_required_fields_returns_nonempty_for_known_status(
    db_session: AsyncSession, status: str
) -> None:
    svc = LegalProfileService(db_session)
    result = await svc.get_required_fields(status)
    assert len(result["fields"]) > 0
    assert "show_bank_details" in result
    assert "show_passport" in result
    assert "show_yoomoney" in result


async def test_required_fields_specific_flags(db_session: AsyncSession) -> None:
    svc = LegalProfileService(db_session)

    legal = await svc.get_required_fields("legal_entity")
    assert legal["show_bank_details"] is True
    assert legal["show_passport"] is False
    assert legal["show_yoomoney"] is False

    se = await svc.get_required_fields("self_employed")
    assert se["show_bank_details"] is False
    assert se["show_yoomoney"] is True

    ind = await svc.get_required_fields("individual")
    assert ind["show_passport"] is True
    assert ind["show_bank_details"] is False

    ie = await svc.get_required_fields("individual_entrepreneur")
    assert ie["show_bank_details"] is True
    assert ie["tax_regime_required"] is True


# ────────────────────────────────────────────
# Regression / known gap
# ────────────────────────────────────────────


async def test_unknown_legal_status_is_rejected(db_session: AsyncSession) -> None:
    """Regression for the 2026-04-21 xfail gap: unknown legal_status must raise."""
    user = await _make_user(db_session, telegram_id=950_000_600)
    svc = LegalProfileService(db_session)

    with pytest.raises(ValueError, match="Unknown legal_status"):
        await svc.create_profile(user.id, {"legal_status": "foobar", "legal_name": "?"})


async def test_missing_legal_status_is_rejected(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, telegram_id=950_000_601)
    svc = LegalProfileService(db_session)

    with pytest.raises(ValueError, match="legal_status is required"):
        await svc.create_profile(user.id, {"legal_name": "X"})


async def test_get_required_fields_rejects_unknown(db_session: AsyncSession) -> None:
    svc = LegalProfileService(db_session)
    with pytest.raises(ValueError, match="Unknown legal_status"):
        await svc.get_required_fields("foobar")


async def test_update_profile_rejects_change_to_unknown_status(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_602)
    svc = LegalProfileService(db_session)
    await svc.create_profile(user.id, legal_profile_data("legal_entity"))
    await db_session.flush()

    with pytest.raises(ValueError, match="Unknown legal_status"):
        await svc.update_profile(user.id, {"legal_status": "foobar"})


async def test_create_profile_rejects_mismatched_documents(
    db_session: AsyncSession,
) -> None:
    """self_employed + OGRNIP combination must be rejected at service layer."""
    user = await _make_user(db_session, telegram_id=950_000_603)
    svc = LegalProfileService(db_session)

    from tests.conftest import VALID_INN12, VALID_OGRNIP

    with pytest.raises(ValueError, match="ОГРНИП"):
        await svc.create_profile(
            user.id,
            {
                "legal_status": "self_employed",
                "legal_name": "Test",
                "inn": VALID_INN12,
                "ogrnip": VALID_OGRNIP,
            },
        )


# ────────────────────────────────────────────
# calculate_tax
# ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("status", "expected_tax"),
    [
        ("legal_entity", Decimal("0")),
        ("individual_entrepreneur", Decimal("0")),
        ("self_employed", Decimal("0")),
    ],
)
async def test_calculate_tax_zero_for_nontax_withholding_statuses(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
    expected_tax: Decimal,
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_700 + ALL_STATUSES.index(status))
    svc = LegalProfileService(db_session)
    await svc.create_profile(user.id, legal_profile_data(status))
    await db_session.flush()

    result = await svc.calculate_tax(user.id, Decimal("10000"))
    assert result["tax"] == expected_tax
    assert result["gross"] == Decimal("10000")
    assert result["net"] == Decimal("10000")


async def test_calculate_tax_ndfl_for_individual(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=950_000_799)
    svc = LegalProfileService(db_session)
    await svc.create_profile(user.id, legal_profile_data("individual"))
    await db_session.flush()

    result = await svc.calculate_tax(user.id, Decimal("10000"))
    # NDFL is 13% → 1300; net = 8700
    assert result["tax"] == Decimal("1300.00")
    assert result["net"] == Decimal("8700.00")


async def test_calculate_tax_without_profile(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, telegram_id=950_000_800)
    svc = LegalProfileService(db_session)

    result = await svc.calculate_tax(user.id, Decimal("5000"))
    assert result["tax"] == Decimal("0")
    assert result["net"] == Decimal("5000")
    assert "Заполните" in result["tax_note"]
