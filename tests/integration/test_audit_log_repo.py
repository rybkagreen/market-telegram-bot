"""Tests for AuditLogRepo SAVEPOINT contract.

These tests lock the contract introduced in T1.2.3.2: audit insert failure
(DBAPI or Python-level exception) MUST roll back at SAVEPOINT boundary,
leaving the parent session transaction state healthy and commitable.

Real DB trigger uses over-long ``resource_type`` (varchar(50)) — independent
of the widened ``action`` column (varchar(64)), so the test remains
meaningful regardless of future action vocabulary growth.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.audit_log import AuditLog
from src.db.models.user import User
from src.db.repositories.audit_log_repo import AuditLogRepo

pytestmark = pytest.mark.asyncio


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


async def test_log_real_db_failure_does_not_poison_parent_tx(
    db_session: AsyncSession,
) -> None:
    """Over-long resource_type triggers StringDataRightTruncationError inside
    SAVEPOINT — repo must swallow, parent tx must survive intact."""
    user = await _make_user(db_session, telegram_id=970_000_001)
    repo = AuditLogRepo(db_session)

    over_long = "X" * 60  # varchar(50) → DB-level truncation error

    # Contract 1: .log() does NOT raise (fire-and-forget public contract)
    await repo.log(
        action="t123_real_db_fail",
        resource_type=over_long,
        user_id=user.id,
    )

    # Contract 2: parent tx survives — follow-up SELECT must not hit
    # InFailedSQLTransactionError (the C13/C19 regression assertion).
    result = await db_session.execute(select(User).where(User.id == user.id))
    assert result.scalar_one().id == user.id

    # Contract 3: parent tx is commitable — no lingering DBAPI tx poisoning.
    await db_session.commit()

    # Contract 4: failed audit row absent — SAVEPOINT genuinely rolled back
    # (not merely Python exception swallow).
    audit_rows = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "t123_real_db_fail")
    )
    assert list(audit_rows.scalars()) == []


async def test_log_mocked_python_exception_does_not_poison_parent_tx(
    db_session: AsyncSession,
) -> None:
    """Patched session.execute raises RuntimeError on audit insert —
    Python-level exception path must also rollback at SAVEPOINT boundary."""
    user = await _make_user(db_session, telegram_id=970_000_002)
    repo = AuditLogRepo(db_session)

    boom = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(db_session, "execute", new=boom):
        # Contract 1: .log() does NOT raise even with Python-level exception.
        await repo.log(
            action="t123_mock_py_exc",
            resource_type="legal_profile",
            user_id=user.id,
        )

    # Contract 2: parent tx survives — patch reverted, real execute back.
    result = await db_session.execute(select(User).where(User.id == user.id))
    assert result.scalar_one().id == user.id

    # Contract 3: parent commitable.
    await db_session.commit()

    # Contract 4: failed audit row absent.
    audit_rows = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "t123_mock_py_exc")
    )
    assert list(audit_rows.scalars()) == []


async def test_log_happy_path_round_trip(db_session: AsyncSession) -> None:
    """Sanity: successful .log() persists the row in the same session."""
    user = await _make_user(db_session, telegram_id=970_000_003)
    repo = AuditLogRepo(db_session)

    await repo.log(
        action="t123_happy_path",
        resource_type="legal_profile",
        user_id=user.id,
        resource_id=42,
        extra={"hello": "world"},
    )

    audit_rows = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "t123_happy_path")
    )
    rows = list(audit_rows.scalars())
    assert len(rows) == 1
    assert rows[0].user_id == user.id
    assert rows[0].resource_id == 42
    assert rows[0].extra == {"hello": "world"}


async def test_log_warning_emitted_on_failure(
    db_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failure path emits logger.warning with exc_info=True
    (observability contract — operators must see audit failures in logs)."""
    user = await _make_user(db_session, telegram_id=970_000_004)
    repo = AuditLogRepo(db_session)

    over_long = "Y" * 60

    with caplog.at_level(logging.WARNING, logger="src.db.repositories.audit_log_repo"):
        await repo.log(
            action="t123_warning_capture",
            resource_type=over_long,
            user_id=user.id,
        )

    matching = [r for r in caplog.records if "Audit log write failed" in r.message]
    assert len(matching) >= 1, f"Expected warning record, got {[r.message for r in caplog.records]}"
    assert matching[0].exc_info is not None
