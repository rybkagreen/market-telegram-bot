"""Unit tests for bot handler accept_request — Phase 3c gate-block UX.

Verifies the bot-side handling of TransitionBlockedError raised by
PlacementTransitionService.transition (Phase 3c). Three branches:

* Happy path: transition succeeds → confirmation message edited.
* Marker-only block: TransitionBlockedError with all reason_code in
  {phase4_pending, phase5_pending} → "временно недоступно" message.
* Real-fail block: TransitionBlockedError with non-marker reason_code →
  full remediation list rendered.

Mocks the AsyncSession and TransitionBlockedError-raising transition;
isolates the handler's exception-handling branch.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.handlers.owner.arbitration import accept_request
from src.core.exceptions import TransitionBlockedError
from src.db.models.placement_request import PlacementRequest, PlacementStatus

pytestmark = pytest.mark.asyncio


def _make_callback(request_id: int = 42) -> MagicMock:
    cb = MagicMock()
    cb.data = f"own:accept:{request_id}"
    cb.from_user = MagicMock(id=100_001)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    cb.bot = MagicMock()
    return cb


def _make_placement(request_id: int = 42) -> PlacementRequest:
    placement = PlacementRequest(
        advertiser_id=10,
        owner_id=20,
        channel_id=30,
        proposed_price=Decimal("1000"),
        ad_text="Test ad text for accept_request unit test.",
        status=PlacementStatus.pending_owner,
    )
    placement.id = request_id
    placement.final_price = None
    placement.final_schedule = None
    placement.counter_price = None
    placement.counter_schedule = None
    return placement


def _make_session(placement: PlacementRequest) -> MagicMock:
    session = MagicMock()

    async def _get(model, _id):
        if model is PlacementRequest:
            return placement
        return None

    session.get = AsyncMock(side_effect=_get)
    return session


@pytest.fixture(autouse=True)
def _patch_isinstance(monkeypatch: pytest.MonkeyPatch) -> None:
    """``isinstance(callback.message, Message)`` early-return guard; bypass."""
    import src.bot.handlers.owner.arbitration as mod

    monkeypatch.setattr(mod, "isinstance", lambda obj, cls: True, raising=False)


@pytest.fixture(autouse=True)
def _patch_notify_advertiser_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress notify_advertiser_accepted to keep test isolated."""
    import src.bot.handlers.owner.arbitration as mod

    monkeypatch.setattr(mod, "notify_advertiser_accepted", AsyncMock())


async def test_owner_accept_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transition succeeds → confirmation message rendered, no answer with error."""
    placement = _make_placement()
    session = _make_session(placement)
    callback = _make_callback()

    transition_mock = AsyncMock()
    monkeypatch.setattr(
        "src.bot.handlers.owner.arbitration.PlacementTransitionService",
        lambda s: MagicMock(transition=transition_mock),
    )

    await accept_request(callback, session)

    transition_mock.assert_called_once()
    callback.message.edit_text.assert_called_once()
    edit_args = callback.message.edit_text.call_args[0][0]
    assert "принята" in edit_args
    callback.message.answer.assert_not_called()


async def test_owner_accept_marker_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Marker-only block → "временно недоступно" message via answer()."""
    placement = _make_placement()
    session = _make_session(placement)
    callback = _make_callback()

    blocked_exc = TransitionBlockedError(
        "blocked",
        extra={
            "from": "pending_owner",
            "to": "pending_payment",
            "blockers": [
                {
                    "gate": "G07_SUPPLEMENTARY_AGREEMENT_SIGNED",
                    "reason_code": "phase4_pending",
                    "remediation_url": None,
                    "remediation_data": None,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.arbitration.PlacementTransitionService",
        lambda s: MagicMock(transition=AsyncMock(side_effect=blocked_exc)),
    )

    await accept_request(callback, session)

    callback.message.answer.assert_called_once()
    msg = callback.message.answer.call_args[0][0]
    assert "временно недоступно" in msg
    assert "G07" not in msg  # markers don't expose gate names
    callback.message.edit_text.assert_not_called()


async def test_owner_accept_real_fail_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real-fail block → remediation list rendered with gate names."""
    placement = _make_placement()
    session = _make_session(placement)
    callback = _make_callback()

    blocked_exc = TransitionBlockedError(
        "blocked",
        extra={
            "from": "pending_owner",
            "to": "pending_payment",
            "blockers": [
                {
                    "gate": "G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED",
                    "reason_code": "framework_contract_unsigned",
                    "remediation_url": "https://example.com/sign",
                    "remediation_data": None,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.arbitration.PlacementTransitionService",
        lambda s: MagicMock(transition=AsyncMock(side_effect=blocked_exc)),
    )

    await accept_request(callback, session)

    callback.message.answer.assert_called_once()
    msg = callback.message.answer.call_args[0][0]
    assert "G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED" in msg
    assert "https://example.com/sign" in msg
    callback.message.edit_text.assert_not_called()
