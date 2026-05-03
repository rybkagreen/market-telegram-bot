"""Unit tests for X-Idempotency-Key keying in POST /api/payouts/ (5b.7b).

Tests use direct function calls (not httpx transport) — mirrors
test_billing_hotfix_bundle.py:166 pattern. Mocks session methods to drive
EXISTS-check / flush / rollback paths deterministically without a real DB.

Coverage:

* EXISTS-fast-path hit (same key → returns existing PayoutRequest)
* UUID4 fallback when no header (distinct keys)
* Race-past-EXISTS handler distinguishes idempotency_key UNIQUE from
  other IntegrityErrors (Marina Q5=(б) strict distinguish)
* Constructed key shape + header value plumbing

CL-1 note: router uses ``session.flush()`` (not ``commit()``); tests mock
``flush`` accordingly. ``get_db_session``'s autocommit is outside test
scope.
"""

from __future__ import annotations

import re
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from src.api.routers.payouts import create_payout
from src.api.schemas.payout import PayoutCreate
from src.db.models.payout import (
    IDEMPOTENCY_KEY_CONSTRAINT_NAME,
    PayoutRequest,
    PayoutStatus,
)
from src.db.models.user import User


def _make_integrity_error(constraint_name: str | None) -> IntegrityError:
    """IntegrityError shaped like asyncpg's (orig.diag.constraint_name)."""
    diag = MagicMock()
    diag.constraint_name = constraint_name
    orig = MagicMock()
    orig.diag = diag
    err = IntegrityError("statement", {}, orig)
    err.orig = orig
    return err


def _fake_user(user_id: int = 42, earned: Decimal = Decimal("10000")) -> User:
    u = User()
    u.id = user_id
    u.telegram_id = 999_000_000 + user_id
    u.earned_rub = earned
    return u


def _fake_existing_payout(idempotency_key: str, payout_id: int = 7) -> PayoutRequest:
    """PayoutRequest pre-populated as if returned from the DB."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return PayoutRequest(
        id=payout_id,
        owner_id=42,
        gross_amount=Decimal("1000"),
        fee_amount=Decimal("15"),
        net_amount=Decimal("985"),
        status=PayoutStatus.pending,
        requisites="40802810000000000001",
        idempotency_key=idempotency_key,
        created_at=now,
        updated_at=now,
    )


def _stub_session_for_create(
    *,
    user: User,
    existing_active: PayoutRequest | None = None,
    existing_idempotent: PayoutRequest | None = None,
    flush_side_effect: BaseException | None = None,
    post_rollback_existing: PayoutRequest | None = None,
) -> MagicMock:
    """Build a session mock matching the create_payout call sequence.

    Call order in router (post-pre-checks):
      1. payout_repo.get_active_for_owner → existing_active (None means no active)
      2. user_repo.get_by_id → user
      3. session.execute(EXISTS query) → existing_idempotent
      4. session.add(payout)
      5. session.flush()
        (a) raises → session.rollback() then session.execute(re-read)
        (b) succeeds → session.refresh(payout)
    """
    session = MagicMock()
    session.added_payouts = []  # tests inspect this for constructed-key assertions

    def _add(payout: PayoutRequest) -> None:
        session.added_payouts.append(payout)

    async def _flush() -> None:
        # Real session.flush would assign the auto-increment PK; emulate that.
        if flush_side_effect is not None:
            raise flush_side_effect
        if session.added_payouts:
            session.added_payouts[-1].id = 12345

    async def _refresh(payout: PayoutRequest) -> None:
        # Real session.refresh re-loads from DB; emulate timestamp population.
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        if payout.created_at is None:
            payout.created_at = now
        if payout.updated_at is None:
            payout.updated_at = now

    session.add = MagicMock(side_effect=_add)
    session.refresh = AsyncMock(side_effect=_refresh)
    session.rollback = AsyncMock()
    session.flush = AsyncMock(side_effect=_flush)

    # Build session.execute return-values queue.
    execute_returns: list[MagicMock] = []
    # Step 1 — payout_repo.get_active_for_owner uses session.execute internally.
    active_result = MagicMock()
    active_result.scalar_one_or_none = MagicMock(return_value=existing_active)
    active_result.scalars = MagicMock(
        return_value=MagicMock(first=MagicMock(return_value=existing_active))
    )
    execute_returns.append(active_result)
    # Step 2 — user_repo.get_by_id uses session.get (separate mock below).
    # Step 3 — EXISTS-check (router-side select).
    exists_result = MagicMock()
    exists_result.scalar_one_or_none = MagicMock(return_value=existing_idempotent)
    execute_returns.append(exists_result)
    # Step 5a — re-read after rollback (only used if flush raises).
    if post_rollback_existing is not None:
        re_read_result = MagicMock()
        re_read_result.scalar_one = MagicMock(return_value=post_rollback_existing)
        execute_returns.append(re_read_result)

    session.execute = AsyncMock(side_effect=execute_returns)
    session.get = AsyncMock(return_value=user)
    return session


# ============================================================================
# 1. EXISTS-fast-path hit
# ============================================================================


@pytest.mark.asyncio
async def test_create_payout_with_header_returns_existing_on_replay() -> None:
    """Same X-Idempotency-Key header → EXISTS-check returns existing payout."""
    user = _fake_user()
    expected_key = f"payout_request:owner={user.id}:nonce=replay-key-123"
    existing = _fake_existing_payout(idempotency_key=expected_key, payout_id=99)

    session = _stub_session_for_create(user=user, existing_idempotent=existing)
    body = PayoutCreate(amount=Decimal("1000"), payment_details="40802810000000000001")

    response = await create_payout(
        payout_data=body,
        current_user=user,
        session=session,
        x_idempotency_key="replay-key-123",
    )

    assert response.id == 99
    # No new row constructed.
    session.add.assert_not_called()
    session.flush.assert_not_called()


# ============================================================================
# 2. UUID4 fallback when no header
# ============================================================================


@pytest.mark.asyncio
async def test_create_payout_no_header_generates_unique_key() -> None:
    """Two POSTs without header → distinct constructed keys."""
    user = _fake_user()
    body = PayoutCreate(amount=Decimal("1000"), payment_details="40802810000000000001")

    captured_keys: list[str] = []
    for _ in range(2):
        session = _stub_session_for_create(user=user)
        await create_payout(
            payout_data=body, current_user=user, session=session, x_idempotency_key=None
        )
        captured_keys.append(session.added_payouts[-1].idempotency_key or "")

    assert captured_keys[0] != captured_keys[1]
    for k in captured_keys:
        assert k.startswith(f"payout_request:owner={user.id}:nonce=")


# ============================================================================
# 3. Race-past-EXISTS — UNIQUE(idempotency_key) handled idempotently
# ============================================================================


@pytest.mark.asyncio
async def test_create_payout_idempotency_key_unique_constraint_handles_race() -> None:
    """flush() raises IntegrityError on idempotency_key UNIQUE → re-read existing."""
    user = _fake_user()
    expected_key_prefix = f"payout_request:owner={user.id}:nonce="
    existing = _fake_existing_payout(
        idempotency_key=expected_key_prefix + "racewinner", payout_id=77
    )

    session = _stub_session_for_create(
        user=user,
        flush_side_effect=_make_integrity_error(IDEMPOTENCY_KEY_CONSTRAINT_NAME),
        post_rollback_existing=existing,
    )

    body = PayoutCreate(amount=Decimal("1000"), payment_details="40802810000000000001")
    response = await create_payout(
        payout_data=body, current_user=user, session=session, x_idempotency_key="anything"
    )

    assert response.id == 77
    session.rollback.assert_awaited_once()


# ============================================================================
# 4. Other IntegrityError — re-raise (no idempotent re-read)
# ============================================================================


@pytest.mark.asyncio
async def test_create_payout_other_integrity_error_re_raises_does_not_re_read() -> None:
    """flush() raises IntegrityError for a non-idempotency constraint → re-raise."""
    user = _fake_user()
    session = _stub_session_for_create(
        user=user,
        flush_side_effect=_make_integrity_error("fk_payout_requests_owner_id"),
    )

    body = PayoutCreate(amount=Decimal("1000"), payment_details="40802810000000000001")
    with pytest.raises(IntegrityError):
        await create_payout(
            payout_data=body, current_user=user, session=session, x_idempotency_key=None
        )

    session.rollback.assert_awaited_once()
    # Two execute calls expected: get_active_for_owner + EXISTS-check. NO post-rollback re-read.
    assert session.execute.await_count == 2


# ============================================================================
# 5. Constructed key shape
# ============================================================================


@pytest.mark.asyncio
async def test_create_payout_idempotency_key_format() -> None:
    """Constructed key matches payout_request:owner=<id>:nonce=<32-char-hex>."""
    user = _fake_user(user_id=314)
    body = PayoutCreate(amount=Decimal("1000"), payment_details="40802810000000000001")
    session = _stub_session_for_create(user=user)

    await create_payout(
        payout_data=body, current_user=user, session=session, x_idempotency_key=None
    )

    assert len(session.added_payouts) == 1
    key = session.added_payouts[-1].idempotency_key
    assert re.fullmatch(r"payout_request:owner=314:nonce=[0-9a-f]{32}", key or ""), key


# ============================================================================
# 6. Header value plumbed into key
# ============================================================================


@pytest.mark.asyncio
async def test_create_payout_header_value_used_in_key() -> None:
    """Header value abc123 → constructed key contains nonce=abc123."""
    user = _fake_user(user_id=271)
    body = PayoutCreate(amount=Decimal("1000"), payment_details="40802810000000000001")
    session = _stub_session_for_create(user=user)

    await create_payout(
        payout_data=body,
        current_user=user,
        session=session,
        x_idempotency_key="abc123",
    )

    assert len(session.added_payouts) == 1
    assert session.added_payouts[-1].idempotency_key == "payout_request:owner=271:nonce=abc123"
