"""Regression tests for billing hotfix bundle (Промт-12).

Each test guards against re-introduction of one of the hotfix'd bugs:

- CRIT-1 — `Transaction(payment_id=...)` was an invalid kwarg; the model
  field is `yookassa_payment_id`. Every YooKassa webhook crashed with
  TypeError, so production topups silently failed.
- CRIT-2 — `platform_account_repo.release_from_escrow` decremented
  `payout_reserved` instead of `escrow_reserved`. Each successful
  publication produced silent ledger drift.
- Admin audit gap — `POST /admin/users/{uid}/balance` updated balance
  without writing any Transaction record. Silent admin top-ups left no
  audit trail.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from src.api.routers.admin import BalanceTopUpRequest, topup_user_balance
from src.core.services.billing_service import BillingService
from src.db.models.platform_account import PlatformAccount
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User
from src.db.repositories.platform_account_repo import PlatformAccountRepository

pytestmark = pytest.mark.asyncio


def _unique_int() -> int:
    """32-bit positive int unique within the test process."""
    return uuid.uuid4().int % 2_000_000_000


async def _seed_user(session, *, balance: Decimal = Decimal("0")) -> User:
    user = User(
        telegram_id=_unique_int(),
        username=f"u_{_unique_int()}",
        first_name="Test",
        balance_rub=balance,
        earned_rub=Decimal("0"),
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_platform_account(
    session,
    *,
    escrow: Decimal = Decimal("0"),
    payout: Decimal = Decimal("0"),
    profit: Decimal = Decimal("0"),
) -> PlatformAccount:
    """Insert the singleton PlatformAccount row (id=1) with explicit balances."""
    pa = PlatformAccount(
        id=1,
        escrow_reserved=escrow,
        payout_reserved=payout,
        profit_accumulated=profit,
        total_topups=Decimal("0"),
        total_payouts=Decimal("0"),
    )
    session.add(pa)
    await session.flush()
    return pa


async def test_topup_webhook_writes_transaction_with_yookassa_payment_id(
    db_session,
):
    """Regression: CRIT-1 — Transaction(payment_id=...) was an invalid kwarg.

    Verify that processing a YooKassa webhook successfully creates a
    Transaction row with `yookassa_payment_id` populated and credits
    the user's balance with `desired_balance` (not `gross_amount`).
    """
    user = await _seed_user(db_session, balance=Decimal("100.00"))
    await _seed_platform_account(db_session)

    service = BillingService()
    payment_id = f"yk-{uuid.uuid4().hex[:16]}"
    desired_balance = Decimal("500.00")
    gross_amount = Decimal("510.00")  # 2% YooKassa fee

    await service.process_topup_webhook(
        session=db_session,
        payment_id=payment_id,
        gross_amount=gross_amount,
        metadata={
            "desired_balance": str(desired_balance),
            "user_id": str(user.id),
        },
    )
    await db_session.flush()

    result = await db_session.execute(
        select(Transaction).where(Transaction.yookassa_payment_id == payment_id)
    )
    txn = result.scalar_one()

    assert txn.user_id == user.id
    assert txn.type == TransactionType.topup
    assert txn.amount == desired_balance
    assert txn.yookassa_payment_id == payment_id
    assert txn.payment_status == "succeeded"

    await db_session.refresh(user)
    assert user.balance_rub == Decimal("600.00")  # 100 + 500 (desired, not gross)


async def test_release_from_escrow_decrements_escrow_reserved(db_session):
    """Regression: CRIT-2 — release_from_escrow decremented the wrong field.

    Verify that release_from_escrow decrements `escrow_reserved` (was
    erroneously `payout_reserved` before the fix) and accumulates the
    platform fee in `profit_accumulated`. `payout_reserved` belongs to
    the payout pipeline and must not be touched here.
    """
    await _seed_platform_account(
        db_session,
        escrow=Decimal("1000.00"),
        payout=Decimal("500.00"),
        profit=Decimal("0.00"),
    )

    repo = PlatformAccountRepository(db_session)
    final_price = Decimal("200.00")
    platform_fee = Decimal("30.00")

    await repo.release_from_escrow(db_session, final_price, platform_fee)
    await db_session.flush()

    pa = await db_session.get(PlatformAccount, 1)
    assert pa is not None
    assert pa.escrow_reserved == Decimal("800.00")  # 1000 - 200
    assert pa.payout_reserved == Decimal("500.00")  # untouched
    assert pa.profit_accumulated == Decimal("30.00")  # +platform_fee


async def test_admin_topup_creates_transaction_record(db_session):
    """Regression: admin top-ups were silent (0 Transaction records).

    Calling the topup_user_balance endpoint must:
    - credit the user's balance,
    - write a Transaction(type=topup) row tagged with
      `meta_json.method == "admin_topup"` and the admin id,
    - persist a stable `idempotency_key` (auto-generated when no
      X-Idempotency-Key header is supplied).
    """
    target = await _seed_user(db_session, balance=Decimal("0"))
    admin = MagicMock()
    admin.id = 9999

    body = BalanceTopUpRequest(amount=250.0, note="manual credit for support")

    response = await topup_user_balance(
        user_id=target.id,
        body=body,
        admin_user=admin,
        session=db_session,
        x_idempotency_key=None,
    )
    await db_session.flush()

    assert response.id == target.id
    assert Decimal(str(response.balance_rub)) == Decimal("250.00")

    await db_session.refresh(target)
    assert target.balance_rub == Decimal("250.00")

    rows = (
        await db_session.execute(
            select(Transaction).where(Transaction.user_id == target.id)
        )
    ).scalars().all()
    assert len(rows) == 1

    txn = rows[0]
    assert txn.type == TransactionType.topup
    assert txn.amount == Decimal("250.00")
    assert txn.meta_json is not None
    assert txn.meta_json.get("method") == "admin_topup"
    assert txn.meta_json.get("admin_id") == 9999
    assert txn.meta_json.get("note") == "manual credit for support"
    assert txn.idempotency_key is not None
    assert txn.idempotency_key.startswith("admin_topup:admin=9999:user=")
    assert txn.balance_before == Decimal("0.00")
    assert txn.balance_after == Decimal("250.00")


async def test_admin_topup_idempotent(db_session):
    """Same X-Idempotency-Key → exactly one Transaction, single credit."""
    target = await _seed_user(db_session, balance=Decimal("0"))
    admin = MagicMock()
    admin.id = 1234

    idem_key = f"admin_topup:test:{uuid.uuid4()}"
    body = BalanceTopUpRequest(amount=300.0, note="dup-protection")

    first = await topup_user_balance(
        user_id=target.id,
        body=body,
        admin_user=admin,
        session=db_session,
        x_idempotency_key=idem_key,
    )
    await db_session.flush()
    assert Decimal(str(first.balance_rub)) == Decimal("300.00")

    second = await topup_user_balance(
        user_id=target.id,
        body=body,
        admin_user=admin,
        session=db_session,
        x_idempotency_key=idem_key,
    )
    await db_session.flush()
    assert Decimal(str(second.balance_rub)) == Decimal("300.00")  # NOT 600

    await db_session.refresh(target)
    assert target.balance_rub == Decimal("300.00")  # credited only once

    rows = (
        await db_session.execute(
            select(Transaction).where(Transaction.user_id == target.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].idempotency_key == idem_key
