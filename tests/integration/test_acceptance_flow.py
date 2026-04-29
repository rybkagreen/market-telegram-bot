"""Integration: re-acceptance loop activates at CONTRACT_TEMPLATE_VERSION mismatch.

Promt 15.9 — verifies ContractService.needs_accept_rules + accept_platform_rules
across the four states: never accepted, accepted current, accepted older, and
the version-bump simulation.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.legal import CONTRACT_TEMPLATE_VERSION
from src.core.services.contract_service import ContractService
from src.db.models.contract import Contract
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession, suffix: str) -> User:
    """Inline user factory — the integration db_session rolls back per test."""
    user = User(
        telegram_id=int(f"99{abs(hash(suffix)) % 10**8}"),
        first_name=f"Acceptance {suffix}",
        referral_code=f"acc_{suffix}",
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _seed_acceptance(
    session: AsyncSession,
    user_id: int,
    template_version: str,
    *,
    signed_at: datetime | None = None,
    contract_status: str = "signed",
) -> None:
    await session.execute(
        insert(Contract).values(
            user_id=user_id,
            contract_type="platform_rules",
            contract_status=contract_status,
            signed_at=signed_at or datetime.now(UTC),
            signature_method="button_accept",
            template_version=template_version,
        )
    )
    await session.flush()


async def test_needs_accept_rules_true_for_new_user(db_session: AsyncSession) -> None:
    """No prior Contract row → needs_accept_rules returns True."""
    user = await _make_user(db_session, "new")
    service = ContractService(db_session)

    assert await service.needs_accept_rules(user.id) is True


async def test_needs_accept_rules_false_for_current_version(db_session: AsyncSession) -> None:
    """Acceptance row at CONTRACT_TEMPLATE_VERSION → returns False."""
    user = await _make_user(db_session, "current")
    await _seed_acceptance(db_session, user.id, CONTRACT_TEMPLATE_VERSION)
    service = ContractService(db_session)

    assert await service.needs_accept_rules(user.id) is False


async def test_needs_accept_rules_true_for_old_version(db_session: AsyncSession) -> None:
    """Acceptance row at older template_version → forced re-accept."""
    user = await _make_user(db_session, "old")
    old_version = "1.0"
    assert old_version != CONTRACT_TEMPLATE_VERSION, (
        "Test premise broken: CONTRACT_TEMPLATE_VERSION must differ from '1.0'"
    )
    await _seed_acceptance(db_session, user.id, old_version)
    service = ContractService(db_session)

    assert await service.needs_accept_rules(user.id) is True


async def test_accept_platform_rules_atomic_update(db_session: AsyncSession) -> None:
    """accept_platform_rules creates Contract row (current version) AND syncs User cache."""
    user = await _make_user(db_session, "atomic")
    service = ContractService(db_session)

    await service.accept_platform_rules(user.id)
    await db_session.flush()

    contract_row = (
        await db_session.execute(
            select(Contract).where(
                Contract.user_id == user.id,
                Contract.contract_type == "platform_rules",
            )
        )
    ).scalar_one()
    refreshed_user = (
        await db_session.execute(select(User).where(User.id == user.id))
    ).scalar_one()

    assert contract_row.template_version == CONTRACT_TEMPLATE_VERSION
    assert contract_row.contract_status == "signed"
    assert refreshed_user.platform_rules_accepted_at is not None
    assert refreshed_user.platform_rules_accepted_at == contract_row.signed_at


async def test_version_bump_forces_re_accept(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User accepted current version, then constant bumps → needs_accept becomes True."""
    user = await _make_user(db_session, "bump")
    await _seed_acceptance(db_session, user.id, CONTRACT_TEMPLATE_VERSION)
    service = ContractService(db_session)

    assert await service.needs_accept_rules(user.id) is False

    bumped_version = f"{CONTRACT_TEMPLATE_VERSION}+next"
    monkeypatch.setattr(
        "src.core.services.contract_service.CONTRACT_TEMPLATE_VERSION",
        bumped_version,
    )

    assert await service.needs_accept_rules(user.id) is True

    await service.accept_platform_rules(user.id)
    await db_session.flush()
    contract_row = (
        await db_session.execute(
            select(Contract).where(
                Contract.user_id == user.id,
                Contract.contract_type == "platform_rules",
            )
        )
    ).scalar_one()
    assert contract_row.template_version == bumped_version
    assert await service.needs_accept_rules(user.id) is False
