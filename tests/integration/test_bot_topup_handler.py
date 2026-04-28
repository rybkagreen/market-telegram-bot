"""Integration tests for bot topup_pay handler (Промт-15.5).

Verifies the bot handler routes through the canonical
YooKassaService.create_topup_payment — same entry point used by the
mini_app and web_portal POST /api/billing/topup endpoint.

Two scenarios:
- Happy path: handler calls create_topup_payment with caller's session,
  user.id, and desired_balance from FSM data, then renders payment URL.
- PaymentProviderError: handler renders graceful 503-style message that
  includes the provider request_id for support.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message

from src.core.services.billing_service import PaymentProviderError
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


def _unique_int() -> int:
    return uuid.uuid4().int % 2_000_000_000


async def _seed_user(session) -> User:
    user = User(
        telegram_id=_unique_int(),
        username=f"u_{_unique_int()}",
        first_name="Bot",
        balance_rub=Decimal("0"),
        earned_rub=Decimal("0"),
    )
    session.add(user)
    await session.flush()
    return user


def _make_callback(telegram_id: int) -> MagicMock:
    """Mock CallbackQuery with a Message-typed message attribute."""
    callback = MagicMock()
    # isinstance(callback.message, Message) must be True
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = telegram_id
    callback.answer = AsyncMock()
    return callback


def _make_state(amount: str) -> MagicMock:
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"amount": amount})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    return state


async def test_bot_topup_pay_uses_create_topup_payment(db_session) -> None:
    """Happy path: handler calls create_topup_payment with the right args."""
    from src.bot.handlers.billing.billing import topup_pay

    user = await _seed_user(db_session)
    callback = _make_callback(user.telegram_id)
    state = _make_state("100")

    fake_result = {
        "payment_id": "test-bot-pid-001",
        "payment_url": "https://yookassa.test/bot-url",
        "amount": "106.00",
        "credits": 100,
        "status": "pending",
    }

    with patch(
        "src.core.services.yookassa_service.YooKassaService.create_topup_payment",
        new=AsyncMock(return_value=fake_result),
    ) as mock_create:
        await topup_pay(callback, state, db_session)

    mock_create.assert_awaited_once()
    await_args = mock_create.await_args
    assert await_args is not None
    call_kwargs = await_args.kwargs
    assert call_kwargs["session"] is db_session
    assert call_kwargs["user_id"] == user.id
    assert call_kwargs["desired_balance"] == Decimal("100")

    # FSM advanced to waiting_payment with payment_id stored.
    state.update_data.assert_awaited_with(payment_id="test-bot-pid-001")
    state.set_state.assert_awaited_once()

    # User saw payment URL in the final message.
    final_call = callback.message.edit_text.await_args_list[-1]
    final_text = final_call.args[0] if final_call.args else final_call.kwargs.get("text", "")
    assert "106.00" in final_text


async def test_bot_topup_pay_handles_payment_provider_error(db_session) -> None:
    """PaymentProviderError → user sees graceful message + request_id."""
    from src.bot.handlers.billing.billing import topup_pay

    user = await _seed_user(db_session)
    callback = _make_callback(user.telegram_id)
    state = _make_state("100")

    err = PaymentProviderError(
        code="forbidden",
        description="Transaction forbidden.",
        request_id="bot-test-req-id-xyz",
    )

    with patch(
        "src.core.services.yookassa_service.YooKassaService.create_topup_payment",
        new=AsyncMock(side_effect=err),
    ):
        await topup_pay(callback, state, db_session)

    final_call = callback.message.edit_text.await_args_list[-1]
    final_text = final_call.args[0] if final_call.args else final_call.kwargs.get("text", "")
    assert "недоступен" in final_text
    assert "bot-test-req-id-xyz" in final_text

    # FSM not advanced when payment creation failed.
    state.set_state.assert_not_awaited()
