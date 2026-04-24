"""
Concurrency regression test for `PayoutService.approve_request` /
`reject_request` (FIX_PLAN_06_followups/plan-02, 2026-04-21).

Pre-fix layout used three sequential sessions (status check / financial
move / admin_id stamp), letting two parallel admins both pass the
status check and double-debit `PlatformAccount.payout_reserved`.

This suite drives `asyncio.gather()` against multiple concurrent calls
on the same `payout_id` and verifies the post-state — exactly one
success, the rest raise `"already finalized"`, and the reserve / refund
accounting is moved exactly once.

Without `SELECT … FOR UPDATE` on `PayoutRequest`, the assertions on
`payout_reserved` / `earned_rub` would fail on the first race attempt.

Uses **Pattern C** (engine-bound factory + TRUNCATE) deliberately.
The SAVEPOINT pattern (`test_payout_lifecycle.py`, Pattern B) would
serialize all gathered coroutines on the single connection and the
race could never trigger. See `tests/integration/README.md` for the
decision tree.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.exceptions import PayoutAlreadyFinalizedError
from src.core.services import payout_service as payout_service_module
from src.db import session as session_module
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.platform_account import PlatformAccount
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


def _unique_int() -> int:
    """32-bit positive int unique within the process."""
    return uuid.uuid4().int % 2_000_000_000


@pytest_asyncio.fixture
async def bound_factory(test_engine: Any) -> AsyncGenerator[Any]:
    """Bind `async_session_factory` to the testcontainer engine."""
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    with (
        patch.object(session_module, "async_session_factory", factory),
        patch.object(payout_service_module, "async_session_factory", factory),
    ):
        yield factory


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_after_test(test_engine: Any, bound_factory: Any) -> AsyncGenerator[None]:
    yield
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE transactions, payout_requests, platform_account, "
                "users RESTART IDENTITY CASCADE"
            )
        )


async def _seed_pending_payout(factory: Any) -> tuple[int, int, int, Decimal]:
    """Создать admin + owner + PlatformAccount(reserved=gross) + PayoutRequest(pending).

    Returns: (admin_id, owner_id, payout_id, gross).
    """
    gross = Decimal("1000.00")
    fee = Decimal("15.00")
    net = Decimal("985.00")

    async with factory() as session:
        admin = User(
            telegram_id=_unique_int(),
            username=f"admin_{_unique_int()}",
            first_name="Admin",
            is_admin=True,
            balance_rub=Decimal("0"),
        )
        owner = User(
            telegram_id=_unique_int(),
            username=f"owner_{_unique_int()}",
            first_name="Owner",
            balance_rub=Decimal("0"),
            earned_rub=Decimal("0"),
        )
        session.add_all([admin, owner])
        await session.flush()

        platform = PlatformAccount(
            id=1,
            escrow_reserved=Decimal("0"),
            payout_reserved=gross,
            profit_accumulated=fee,
            total_topups=Decimal("0"),
            total_payouts=Decimal("0"),
        )
        session.add(platform)

        payout = PayoutRequest(
            owner_id=owner.id,
            gross_amount=gross,
            fee_amount=fee,
            net_amount=net,
            status=PayoutStatus.pending,
            requisites=f"REQ-{uuid.uuid4().hex[:12]}",
        )
        session.add(payout)
        await session.commit()

        return admin.id, owner.id, payout.id, gross


class TestConcurrentApprove:
    """Without FOR UPDATE this class would catch a double-debit on the
    first attempt — `payout_reserved` would land at `-gross` instead of `0`."""

    async def test_three_concurrent_approves_yield_one_success(
        self, bound_factory: Any
    ) -> None:
        from src.core.services.payout_service import payout_service

        admin_id, _owner_id, payout_id, gross = await _seed_pending_payout(bound_factory)

        async def _approve() -> str | tuple[str, str]:
            try:
                await payout_service.approve_request(payout_id, admin_id)
                return "ok"
            except PayoutAlreadyFinalizedError as e:
                return ("err", str(e))

        results = await asyncio.gather(_approve(), _approve(), _approve())
        successes = [r for r in results if r == "ok"]
        failures = [r for r in results if isinstance(r, tuple)]

        assert len(successes) == 1, f"Expected exactly 1 success, got {results}"
        assert len(failures) == 2, f"Expected 2 failures, got {results}"
        assert all(
            isinstance(r, tuple) and "already finalized" in r[1] for r in failures
        ), f"Unexpected failure messages: {failures}"

        async with bound_factory() as session:
            payout = await session.get(PayoutRequest, payout_id)
            assert payout is not None
            assert payout.status == PayoutStatus.paid
            assert payout.admin_id == admin_id

            platform = await session.get(PlatformAccount, 1)
            assert platform is not None
            # Critical invariant: reserve dropped by `gross` exactly once.
            # Pre-fix: two threads would both hit complete_payout and the
            # reserve would land at -gross (1000 ₽ lost from the platform's
            # accounting view).
            assert platform.payout_reserved == Decimal("0"), (
                f"payout_reserved drifted: expected 0, got {platform.payout_reserved}; "
                f"likely concurrent approve double-debit"
            )

    async def test_concurrent_approve_then_reject_one_wins(
        self, bound_factory: Any
    ) -> None:
        """approve and reject hit the same payout simultaneously — exactly one wins,
        and finance state is consistent with whichever did."""
        from src.core.services.payout_service import payout_service

        admin_id, owner_id, payout_id, gross = await _seed_pending_payout(bound_factory)

        async def _approve() -> str:
            try:
                await payout_service.approve_request(payout_id, admin_id)
                return "approved"
            except PayoutAlreadyFinalizedError:
                return "approve-blocked"

        async def _reject() -> str:
            try:
                await payout_service.reject_request(
                    payout_id, admin_id, reason="Concurrent reject test"
                )
                return "rejected"
            except PayoutAlreadyFinalizedError:
                return "reject-blocked"

        results = await asyncio.gather(_approve(), _reject())
        winners = [r for r in results if r in ("approved", "rejected")]
        losers = [r for r in results if r in ("approve-blocked", "reject-blocked")]

        assert len(winners) == 1, f"Expected 1 winner, got {results}"
        assert len(losers) == 1, f"Expected 1 loser, got {results}"

        async with bound_factory() as session:
            payout = await session.get(PayoutRequest, payout_id)
            assert payout is not None
            platform = await session.get(PlatformAccount, 1)
            assert platform is not None
            owner = await session.get(User, owner_id)
            assert owner is not None

            if winners[0] == "approved":
                assert payout.status == PayoutStatus.paid
                assert platform.payout_reserved == Decimal("0")
                assert owner.earned_rub == Decimal("0")
            else:
                assert payout.status == PayoutStatus.rejected
                assert platform.payout_reserved == Decimal("0")
                assert owner.earned_rub == gross


class TestConcurrentReject:
    async def test_three_concurrent_rejects_yield_one_success(
        self, bound_factory: Any
    ) -> None:
        from src.core.services.payout_service import payout_service

        admin_id, owner_id, payout_id, gross = await _seed_pending_payout(bound_factory)

        async def _reject() -> str | tuple[str, str]:
            try:
                await payout_service.reject_request(
                    payout_id, admin_id, reason="Test reject race"
                )
                return "ok"
            except PayoutAlreadyFinalizedError as e:
                return ("err", str(e))

        results = await asyncio.gather(_reject(), _reject(), _reject())
        successes = [r for r in results if r == "ok"]
        failures = [r for r in results if isinstance(r, tuple)]

        assert len(successes) == 1, f"Expected exactly 1 success, got {results}"
        assert len(failures) == 2

        async with bound_factory() as session:
            payout = await session.get(PayoutRequest, payout_id)
            assert payout is not None
            assert payout.status == PayoutStatus.rejected

            platform = await session.get(PlatformAccount, 1)
            assert platform is not None
            # Reserve refunded exactly once.
            assert platform.payout_reserved == Decimal("0")

            owner = await session.get(User, owner_id)
            assert owner is not None
            # Owner's earned_rub credited exactly `gross`, not `2*gross` or `3*gross`.
            assert owner.earned_rub == gross, (
                f"earned_rub drifted: expected {gross}, got {owner.earned_rub}; "
                f"likely concurrent reject double-refund"
            )
