"""Integration tests for ContractService — generate/sign/accept-rules across
all 4 owner_service templates, snapshot whitelist, dedup, missing-profile."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.contract_service import (
    _SNAPSHOT_WHITELIST,
    ContractService,
)
from src.core.services.legal_profile_service import LegalProfileService
from src.db.models.contract import Contract
from src.db.models.contract_signature import ContractSignature
from src.db.models.user import User

pytestmark = pytest.mark.asyncio

ALL_STATUSES = ["legal_entity", "individual_entrepreneur", "self_employed", "individual"]


async def _make_user(db_session: AsyncSession, telegram_id: int) -> User:
    user = User(
        telegram_id=telegram_id,
        username=f"u_{telegram_id}",
        first_name="Test",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ────────────────────────────────────────────
# Owner-service contract — one per status
# ────────────────────────────────────────────


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_generate_owner_service_contract_for_each_status(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_100 + ALL_STATUSES.index(status))
    await LegalProfileService(db_session).create_profile(user.id, legal_profile_data(status))
    await db_session.flush()

    svc = ContractService(db_session)
    contract = await svc.generate_contract(user.id, "owner_service")

    assert contract.user_id == user.id
    assert contract.contract_type == "owner_service"
    assert contract.contract_status == "pending"
    assert contract.template_version is not None
    # Snapshot exists and only contains whitelisted keys
    assert contract.legal_status_snapshot is not None
    snapshot_keys = set(contract.legal_status_snapshot.keys())
    assert snapshot_keys.issubset(_SNAPSHOT_WHITELIST), (
        f"Snapshot leaked keys outside whitelist for {status!r}: "
        f"{snapshot_keys - _SNAPSHOT_WHITELIST}"
    )


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_snapshot_never_contains_pii(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_200 + ALL_STATUSES.index(status))
    await LegalProfileService(db_session).create_profile(user.id, legal_profile_data(status))
    await db_session.flush()

    contract = await ContractService(db_session).generate_contract(user.id, "owner_service")

    snapshot = contract.legal_status_snapshot or {}
    pii_keys = {
        "bank_account",
        "bank_corr_account",
        "yoomoney_wallet",
        "passport_series",
        "passport_number",
        "passport_issued_by",
        "passport_issue_date",
        "inn_scan_file_id",
        "passport_scan_file_id",
        "self_employed_cert_file_id",
        "company_doc_file_id",
        "inn_hash",
    }
    leaked = pii_keys & set(snapshot.keys())
    assert not leaked, f"Contract.legal_status_snapshot leaked PII: {leaked}"


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_snapshot_records_expected_business_fields(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_300 + ALL_STATUSES.index(status))
    await LegalProfileService(db_session).create_profile(user.id, legal_profile_data(status))
    await db_session.flush()

    contract = await ContractService(db_session).generate_contract(user.id, "owner_service")
    snapshot = contract.legal_status_snapshot or {}

    # legal_status is always snapshotted
    assert snapshot.get("legal_status") == status
    # legal_name is present for every status
    assert snapshot.get("legal_name")


# ────────────────────────────────────────────
# Deduplication
# ────────────────────────────────────────────


async def test_generate_owner_service_is_idempotent(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_401)
    await LegalProfileService(db_session).create_profile(
        user.id, legal_profile_data("legal_entity")
    )
    await db_session.flush()

    svc = ContractService(db_session)
    c1 = await svc.generate_contract(user.id, "owner_service")
    c2 = await svc.generate_contract(user.id, "owner_service")

    assert c1.id == c2.id, "owner_service must dedup to a single contract per user"


async def test_generate_advertiser_campaign_creates_new_each_time(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_402)
    await LegalProfileService(db_session).create_profile(
        user.id, legal_profile_data("legal_entity")
    )
    await db_session.flush()

    svc = ContractService(db_session)
    # placement_request_id=None avoids FK constraints on placement_requests —
    # we're only exercising the dedup branch in contract_service.py:123.
    c1 = await svc.generate_contract(user.id, "advertiser_campaign", placement_request_id=None)
    c2 = await svc.generate_contract(user.id, "advertiser_campaign", placement_request_id=None)

    # Per contract_service.py:123 dedup is only for type-level contracts, not
    # advertiser_campaign — each call must yield a distinct row.
    assert c1.id != c2.id


# ────────────────────────────────────────────
# Missing LegalProfile (regression)
# ────────────────────────────────────────────


async def test_generate_without_legal_profile_does_not_crash(
    db_session: AsyncSession,
) -> None:
    """A user without a LegalProfile: the current service falls back to an
    empty snapshot and the minimal HTML template. We assert this behaviour
    exists so a regression that starts raising loudly is flagged.
    """
    user = await _make_user(db_session, telegram_id=970_000_500)

    contract = await ContractService(db_session).generate_contract(user.id, "owner_service")
    assert contract.user_id == user.id
    assert contract.legal_status_snapshot == {} or contract.legal_status_snapshot is None


# ────────────────────────────────────────────
# sign_contract
# ────────────────────────────────────────────


async def test_sign_contract_marks_signed_and_records_audit(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_601)
    await LegalProfileService(db_session).create_profile(
        user.id, legal_profile_data("legal_entity")
    )
    await db_session.flush()

    svc = ContractService(db_session)
    contract = await svc.generate_contract(user.id, "owner_service")

    signed = await svc.sign_contract(
        contract.id, user.id, method="button_accept", ip_address="127.0.0.1"
    )
    assert signed.contract_status == "signed"
    assert signed.signed_at is not None
    assert signed.signature_method == "button_accept"

    # Audit row recorded
    result = await db_session.execute(
        select(ContractSignature).where(ContractSignature.contract_id == contract.id)
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.user_id == user.id
    assert audit.document_hash  # SHA-256 hex populated


async def test_sign_contract_rejects_wrong_user(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    owner = await _make_user(db_session, telegram_id=970_000_701)
    await LegalProfileService(db_session).create_profile(
        owner.id, legal_profile_data("legal_entity")
    )
    intruder = await _make_user(db_session, telegram_id=970_000_702)
    await db_session.flush()

    svc = ContractService(db_session)
    contract = await svc.generate_contract(owner.id, "owner_service")

    with pytest.raises(PermissionError):
        await svc.sign_contract(contract.id, intruder.id, method="button_accept")


async def test_sign_contract_rejects_already_signed(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_801)
    await LegalProfileService(db_session).create_profile(
        user.id, legal_profile_data("legal_entity")
    )
    await db_session.flush()

    svc = ContractService(db_session)
    contract = await svc.generate_contract(user.id, "owner_service")
    await svc.sign_contract(contract.id, user.id, method="button_accept")

    with pytest.raises(ValueError, match="cannot sign"):
        await svc.sign_contract(contract.id, user.id, method="button_accept")


# ────────────────────────────────────────────
# accept_platform_rules
# ────────────────────────────────────────────


async def test_accept_platform_rules_creates_signed_contract(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, telegram_id=970_000_901)
    await db_session.flush()

    await ContractService(db_session).accept_platform_rules(user.id)
    await db_session.flush()

    result = await db_session.execute(
        select(Contract).where(
            Contract.user_id == user.id,
            Contract.contract_type == "platform_rules",
        )
    )
    contract = result.scalar_one_or_none()
    assert contract is not None
    assert contract.contract_status == "signed"
    assert contract.signed_at is not None

    # User audit timestamps set
    refreshed_user = await db_session.get(User, user.id)
    assert refreshed_user is not None
    assert refreshed_user.platform_rules_accepted_at is not None
    assert refreshed_user.privacy_policy_accepted_at is not None


async def test_accept_platform_rules_is_idempotent(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, telegram_id=970_000_902)
    await db_session.flush()

    svc = ContractService(db_session)
    await svc.accept_platform_rules(user.id)
    await svc.accept_platform_rules(user.id)
    await db_session.flush()

    result = await db_session.execute(
        select(Contract).where(
            Contract.user_id == user.id,
            Contract.contract_type == "platform_rules",
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1, "accept_platform_rules must dedup to one contract"


# needs_kep_warning is a pure static classifier — tests moved to
# tests/unit/test_contract_template_map.py to avoid the module-level
# `pytestmark = pytest.mark.asyncio` marking sync tests.
