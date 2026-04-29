"""Regression: bot user-cancel handler passes the scenario whose split matches its UI text.

Background — Промт 15.10. The handler `camp_cancel_after_escrow`
(src/bot/handlers/placement/placement.py) advertises "Возврат 50%" in its
buttons and confirmation message, and computes `refund = price *
CANCEL_REFUND_ADVERTISER_RATE`. It must therefore pass scenario=
"after_confirmation" to BillingService.refund_escrow — that scenario
applies the 50/40/10 split. Passing "after_escrow_before_confirmation"
gave the user a silent 100% refund (auto-cancel paths still use that
scenario for owner-fault refunds, which is correct for them).
"""

import inspect


def test_bot_user_cancel_handler_uses_after_confirmation_scenario() -> None:
    from src.bot.handlers.placement import placement as bot_placement

    source = inspect.getsource(bot_placement.camp_cancel_after_escrow)

    assert 'scenario="after_confirmation"' in source, (
        "Bot user-cancel handler must pass scenario='after_confirmation' "
        "(50/40/10 split) — UI promises 'Возврат 50%'. See Промт 15.10."
    )
    assert 'scenario="after_escrow_before_confirmation"' not in source, (
        "Bot user-cancel handler must NOT pass "
        "scenario='after_escrow_before_confirmation' (100% refund) — that "
        "scenario is reserved for system-initiated cancels (publish failure, "
        "SLA timeout, stuck escrow recovery) where owner is at fault."
    )


def test_bot_user_cancel_ui_text_matches_50_percent() -> None:
    from src.bot.handlers.placement import placement as bot_placement

    source = inspect.getsource(bot_placement)

    assert "возврат 50%" in source.lower(), (
        "Bot UI must continue to promise 50% refund (consistent with "
        "after_confirmation scenario). If UI text changes, update the "
        "scenario string accordingly."
    )


def test_auto_cancel_tasks_still_use_full_refund_scenario() -> None:
    """System-initiated cancels in placement_tasks.py keep 100% refund."""
    from src.tasks import placement_tasks

    source = inspect.getsource(placement_tasks)

    assert 'scenario="after_escrow_before_confirmation"' in source, (
        "Auto-cancel tasks (publish failure, SLA timeout, stuck escrow) must "
        "keep scenario='after_escrow_before_confirmation' to refund 100% "
        "to the advertiser when the owner is at fault."
    )


def test_disputes_partial_still_uses_after_confirmation() -> None:
    """Dispute 'partial' verdict keeps 50/40/10 via after_confirmation."""
    from src.api.routers import disputes

    source = inspect.getsource(disputes)

    assert 'scenario="after_confirmation"' in source, (
        "Dispute 'partial' verdict must continue to use after_confirmation "
        "(50/40/10) — admin-resolved partial split."
    )
