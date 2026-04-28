"""Integration tests for YookassaService.create_topup_payment (Промт-15).

Covers:
- Happy path: SDK Payment.create returns successful payment → YookassaPayment
  row + pending Transaction row both persisted via caller's session.
- SDK ForbiddenError → PaymentProviderError raised, no DB rows created.
- User not found → ValueError raised, SDK never called, no DB rows.
- POST /topup endpoint hits YooKassaService.create_topup_payment.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from yookassa.domain.exceptions import ForbiddenError

from src.core.services.billing_service import PaymentProviderError
from src.core.services.yookassa_service import YooKassaService
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User
from src.db.models.yookassa_payment import YookassaPayment

pytestmark = pytest.mark.asyncio


def _unique_int() -> int:
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


def _configure_yookassa_settings(monkeypatch) -> None:
    from src.config.settings import settings as app_settings

    monkeypatch.setattr(app_settings, "yookassa_shop_id", "test-shop", raising=False)
    monkeypatch.setattr(
        app_settings, "yookassa_secret_key", "test-secret", raising=False
    )
    monkeypatch.setattr(
        app_settings,
        "yookassa_return_url",
        "https://test.example.com/return",
        raising=False,
    )


async def test_create_topup_payment_persists_records_via_caller_session(
    db_session, monkeypatch
):
    """Happy path: SDK succeeds → YookassaPayment + Transaction persisted."""
    _configure_yookassa_settings(monkeypatch)
    user = await _seed_user(db_session, balance=Decimal("0"))

    fake_yk_payment = MagicMock()
    fake_yk_payment.id = "test-payment-15-001"
    fake_yk_payment.confirmation.confirmation_url = "https://yookassa.test/confirm"

    with patch(
        "src.core.services.yookassa_service.Payment.create",
        return_value=fake_yk_payment,
    ):
        result = await YooKassaService().create_topup_payment(
            session=db_session,
            user_id=user.id,
            desired_balance=Decimal("100.00"),
        )

    assert result["payment_id"] == "test-payment-15-001"
    assert result["payment_url"] == "https://yookassa.test/confirm"
    assert result["status"] == "pending"
    # gross = 100 + (100 * YOOKASSA_FEE_RATE=0.035) = 103.50.
    # Промт 15.7: switched from PLATFORM_TAX_RATE 6% to YOOKASSA_FEE_RATE 3.5%.
    assert result["amount"] == "103.50"
    assert result["credits"] == 100

    yk = (
        await db_session.execute(
            select(YookassaPayment).where(
                YookassaPayment.payment_id == "test-payment-15-001"
            )
        )
    ).scalar_one()
    assert yk.user_id == user.id
    assert yk.desired_balance == Decimal("100.00")
    assert yk.fee_amount == Decimal("3.50")
    assert yk.gross_amount == Decimal("103.50")
    assert yk.status == "pending"
    assert yk.payment_url == "https://yookassa.test/confirm"

    tx = (
        await db_session.execute(
            select(Transaction).where(
                Transaction.yookassa_payment_id == "test-payment-15-001"
            )
        )
    ).scalar_one()
    assert tx.type == TransactionType.topup
    assert tx.user_id == user.id
    assert tx.amount == Decimal("103.50")


async def test_create_topup_payment_translates_forbidden_to_provider_error(
    db_session, monkeypatch
):
    """SDK ForbiddenError → PaymentProviderError, no DB rows persisted."""
    _configure_yookassa_settings(monkeypatch)
    user = await _seed_user(db_session, balance=Decimal("0"))

    fake_response = {
        "type": "error",
        "code": "forbidden",
        "description": "Transaction forbidden.",
        "request_id": "test-req-15-fail",
    }

    with patch(
        "src.core.services.yookassa_service.Payment.create",
        side_effect=ForbiddenError(fake_response),
    ), pytest.raises(PaymentProviderError) as exc_info:
        await YooKassaService().create_topup_payment(
            session=db_session,
            user_id=user.id,
            desired_balance=Decimal("100.00"),
        )

    assert exc_info.value.code == "forbidden"
    assert exc_info.value.request_id == "test-req-15-fail"

    yk_rows = (
        await db_session.execute(
            select(YookassaPayment).where(YookassaPayment.user_id == user.id)
        )
    ).scalars().all()
    assert yk_rows == []

    tx_rows = (
        await db_session.execute(
            select(Transaction).where(Transaction.user_id == user.id)
        )
    ).scalars().all()
    assert tx_rows == []


async def test_create_topup_payment_user_not_found(db_session, monkeypatch):
    """Non-existent user → ValueError, SDK never called, no DB rows."""
    _configure_yookassa_settings(monkeypatch)

    with patch(
        "src.core.services.yookassa_service.Payment.create"
    ) as sdk_mock, pytest.raises(ValueError, match="not found"):
        await YooKassaService().create_topup_payment(
            session=db_session,
            user_id=999_999_999,
            desired_balance=Decimal("100.00"),
        )

    sdk_mock.assert_not_called()


async def test_topup_endpoint_calls_create_topup_payment(db_session, monkeypatch):
    """POST /topup endpoint calls YooKassaService.create_topup_payment.

    Verifies endpoint signature accepts session via DI and forwards to the
    new service method, returning its dict shape unchanged.
    """
    _configure_yookassa_settings(monkeypatch)
    user = await _seed_user(db_session, balance=Decimal("0"))

    fake_result = {
        "payment_id": "test-pid-endpoint",
        "payment_url": "https://yookassa.test/endpoint-url",
        "amount": "1035.00",
        "credits": 1000,
        "status": "pending",
    }

    captured: dict = {}

    async def _fake_create_topup(self, session, *, user_id, desired_balance):
        captured["user_id"] = user_id
        captured["desired_balance"] = desired_balance
        captured["session_is_callers"] = session is db_session
        return fake_result

    from src.api.routers.billing import TopupRequest, create_unified_topup
    from src.core.services import yookassa_service as yk_module

    monkeypatch.setattr(
        yk_module.YooKassaService, "create_topup_payment", _fake_create_topup
    )

    fake_user = MagicMock()
    fake_user.id = user.id

    body = TopupRequest(desired_amount=1000, method="yookassa")
    response = await create_unified_topup(
        body=body, current_user=fake_user, session=db_session
    )

    assert response.payment_id == "test-pid-endpoint"
    assert response.payment_url == "https://yookassa.test/endpoint-url"
    assert response.status == "pending"
    assert captured["user_id"] == user.id
    assert captured["desired_balance"] == Decimal("1000")
    assert captured["session_is_callers"] is True
