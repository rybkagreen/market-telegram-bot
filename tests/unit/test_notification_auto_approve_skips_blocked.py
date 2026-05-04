"""Unit tests for auto_approve_placements Celery task — Phase 3c gate-block.

Verifies the Celery beat task auto_approve_24h handles TransitionBlockedError
raised by PlacementTransitionService.transition (Phase 3c). Three branches:

* Marker-only: all blockers reason_code in {phase4_pending, phase5_pending}
  → skipped_marker_count incremented; debug log emitted; iteration continues.
* Real-fail: any blocker with non-marker reason_code →
  skipped_real_fail_count incremented; warning log emitted.
* Iteration continues across placements: blocked + happy_path placements
  in the same beat run produce expected counts.

Mocks: async_session_factory, session.execute (placements iterator),
PlacementTransitionService.transition.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import TransitionBlockedError
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.tasks.notification_tasks import auto_approve_placements


def _make_placement(placement_id: int, channel_id: int = 99) -> PlacementRequest:
    placement = PlacementRequest(
        advertiser_id=1,
        owner_id=2,
        channel_id=channel_id,
        proposed_price=Decimal("500"),
        ad_text="ad",
        status=PlacementStatus.pending_owner,
    )
    placement.id = placement_id
    return placement


def _patch_session_factory(
    monkeypatch: pytest.MonkeyPatch, placements: list[PlacementRequest]
) -> MagicMock:
    """Replace async_session_factory with a stub yielding a session whose
    execute() returns the given placements."""
    session = MagicMock()
    session.commit = AsyncMock()

    scalars = MagicMock()
    scalars.all = MagicMock(return_value=placements)
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    session.execute = AsyncMock(return_value=result)

    @asynccontextmanager
    async def _factory():
        yield session

    monkeypatch.setattr("src.tasks.notification_tasks.async_session_factory", _factory)
    return session


def _make_transition_blocked(reason_code: str, gate: str = "G07_X") -> TransitionBlockedError:
    return TransitionBlockedError(
        "blocked",
        extra={
            "from": "pending_owner",
            "to": "pending_payment",
            "blockers": [
                {
                    "gate": gate,
                    "reason_code": reason_code,
                    "remediation_url": None,
                    "remediation_data": None,
                }
            ],
        },
    )


def test_auto_approve_marker_only_blockers_debug_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """All-marker blocker → skipped_marker_count++ and debug log."""
    placement = _make_placement(101)
    _patch_session_factory(monkeypatch, [placement])

    blocked_exc = _make_transition_blocked(
        reason_code="phase4_pending", gate="G07_SUPPLEMENTARY_AGREEMENT_SIGNED"
    )
    monkeypatch.setattr(
        "src.core.services.placement_transition_service.PlacementTransitionService",
        lambda s: MagicMock(transition=AsyncMock(side_effect=blocked_exc)),
    )

    with caplog.at_level(logging.DEBUG, logger="src.tasks.notification_tasks"):
        result = auto_approve_placements()

    assert result["status"] == "ok"
    assert result["skipped_marker"] == 1
    assert result["skipped_real_fail"] == 0
    assert result["approved"] == 0
    debug_lines = [
        rec.getMessage()
        for rec in caplog.records
        if rec.levelno == logging.DEBUG and "all-marker blockers" in rec.getMessage()
    ]
    assert any("placement 101" in line for line in debug_lines)


def test_auto_approve_real_fail_warning_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Non-marker blocker → skipped_real_fail_count++ and warning log."""
    placement = _make_placement(202)
    _patch_session_factory(monkeypatch, [placement])

    blocked_exc = _make_transition_blocked(
        reason_code="framework_contract_unsigned",
        gate="G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED",
    )
    monkeypatch.setattr(
        "src.core.services.placement_transition_service.PlacementTransitionService",
        lambda s: MagicMock(transition=AsyncMock(side_effect=blocked_exc)),
    )

    with caplog.at_level(logging.WARNING, logger="src.tasks.notification_tasks"):
        result = auto_approve_placements()

    assert result["status"] == "ok"
    assert result["skipped_marker"] == 0
    assert result["skipped_real_fail"] == 1
    assert result["approved"] == 0
    warning_lines = [
        rec.getMessage()
        for rec in caplog.records
        if rec.levelno == logging.WARNING and "real-fail blockers" in rec.getMessage()
    ]
    assert any("placement 202" in line for line in warning_lines)


def test_auto_approve_continues_iteration_after_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Beat task continues processing remaining placements after one is blocked."""
    p1 = _make_placement(301)
    p2 = _make_placement(302)
    p3 = _make_placement(303)
    _patch_session_factory(monkeypatch, [p1, p2, p3])

    # p1 marker-blocked, p2 succeeds, p3 real-fail-blocked.
    transition_call = AsyncMock()

    async def _transition_side_effect(**kwargs):
        placement = kwargs["placement"]
        if placement.id == 301:
            raise _make_transition_blocked(reason_code="phase4_pending")
        if placement.id == 302:
            return MagicMock()
        if placement.id == 303:
            raise _make_transition_blocked(
                reason_code="framework_contract_unsigned",
                gate="G02_X",
            )
        raise AssertionError(f"unexpected placement {placement.id}")

    transition_call.side_effect = _transition_side_effect
    monkeypatch.setattr(
        "src.core.services.placement_transition_service.PlacementTransitionService",
        lambda s: MagicMock(transition=transition_call),
    )

    result = auto_approve_placements()

    assert result["status"] == "ok"
    assert result["approved"] == 1
    assert result["skipped_marker"] == 1
    assert result["skipped_real_fail"] == 1
    assert result["failed"] == 0
    assert transition_call.call_count == 3
