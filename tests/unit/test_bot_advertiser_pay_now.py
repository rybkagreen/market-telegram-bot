"""Unit tests for bot handler camp_counter_accept — Phase 3c gate-block UX.

Verifies the advertiser-side handling of TransitionBlockedError raised
by PlacementTransitionService.transition (Phase 3c). Three branches:

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

from src.bot.handlers.advertiser.campaigns import camp_counter_accept
from src.core.exceptions import TransitionBlockedError
from src.db.models.placement_request import PlacementRequest, PlacementStatus

pytestmark = pytest.mark.asyncio


def _make_callback(request_id: int = 99) -> MagicMock:
    cb = MagicMock()
    cb.data = f"camp:counter:accept:{request_id}"
    cb.from_user = MagicMock(id=200_002)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    cb.bot = MagicMock()
    return cb


def _make_placement(request_id: int = 99) -> PlacementRequest:
    placement = PlacementRequest(
        advertiser_id=11,
        owner_id=21,
        channel_id=31,
        proposed_price=Decimal("2000"),
        ad_text="Test ad text for camp_counter_accept unit test.",
        status=PlacementStatus.counter_offer,
    )
    placement.id = request_id
    placement.final_price = None
    placement.final_schedule = None
    placement.counter_price = Decimal("2500")
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
    import src.bot.handlers.advertiser.campaigns as mod

    monkeypatch.setattr(mod, "isinstance", lambda obj, cls: True, raising=False)


@pytest.fixture(autouse=True)
def _patch_supplementary_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 4 hook: bypass ДС generation in unit tests (deferred-import bind)."""
    monkeypatch.setattr(
        "src.core.services.supplementary_agreement_service.SupplementaryAgreementService",
        lambda s: MagicMock(generate_for_placement=AsyncMock()),
    )


async def test_advertiser_pay_now_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transition succeeds → confirmation message edited with price."""
    placement = _make_placement()
    session = _make_session(placement)
    callback = _make_callback()

    transition_mock = AsyncMock()
    monkeypatch.setattr(
        "src.core.services.placement_transition_service.PlacementTransitionService",
        lambda s: MagicMock(transition=transition_mock),
    )

    await camp_counter_accept(callback, session)

    transition_mock.assert_called_once()
    callback.message.edit_text.assert_called_once()
    edit_args = callback.message.edit_text.call_args[0][0]
    assert "Условия приняты" in edit_args
    callback.message.answer.assert_not_called()


async def test_advertiser_pay_now_marker_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Marker-only block → "временно недоступно" message via answer()."""
    placement = _make_placement()
    session = _make_session(placement)
    callback = _make_callback()

    blocked_exc = TransitionBlockedError(
        "blocked",
        extra={
            "from": "counter_offer",
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
        "src.core.services.placement_transition_service.PlacementTransitionService",
        lambda s: MagicMock(transition=AsyncMock(side_effect=blocked_exc)),
    )

    await camp_counter_accept(callback, session)

    callback.message.answer.assert_called_once()
    msg = callback.message.answer.call_args[0][0]
    assert "временно недоступно" in msg
    assert "G07" not in msg
    callback.message.edit_text.assert_not_called()


async def test_advertiser_pay_now_real_fail_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real-fail block → remediation list rendered with gate names."""
    placement = _make_placement()
    session = _make_session(placement)
    callback = _make_callback()

    blocked_exc = TransitionBlockedError(
        "blocked",
        extra={
            "from": "counter_offer",
            "to": "pending_payment",
            "blockers": [
                {
                    "gate": "G01_ADVERTISER_LEGAL_PROFILE_COMPLETE",
                    "reason_code": "legal_profile_missing",
                    "remediation_url": "https://example.com/profile",
                    "remediation_data": None,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "src.core.services.placement_transition_service.PlacementTransitionService",
        lambda s: MagicMock(transition=AsyncMock(side_effect=blocked_exc)),
    )

    await camp_counter_accept(callback, session)

    callback.message.answer.assert_called_once()
    msg = callback.message.answer.call_args[0][0]
    assert "G01_ADVERTISER_LEGAL_PROFILE_COMPLETE" in msg
    assert "https://example.com/profile" in msg
    callback.message.edit_text.assert_not_called()
