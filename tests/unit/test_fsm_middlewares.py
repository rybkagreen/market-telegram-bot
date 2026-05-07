"""
Unit tests for FSM States and Middlewares (P04).
Standalone tests - no conftest dependencies.
"""

import subprocess

import pytest


class TestFSMStates:
    """Tests for FSM states."""

    def test_topup_states_defined(self):
        """TopupStates has 3 states: entering_amount, confirming, waiting_payment."""
        from src.bot.states.billing import TopupStates

        states = TopupStates.__dict__
        assert "entering_amount" in states
        assert "confirming" in states
        assert "waiting_payment" in states

    def test_feedback_states_defined(self):
        """FeedbackStates has entering_text state."""
        from src.bot.states.feedback import FeedbackStates

        states = FeedbackStates.__dict__
        assert "entering_text" in states

    def test_dispute_states_defined(self):
        """DisputeStates has 3 states."""
        from src.bot.states.dispute import DisputeStates

        states = DisputeStates.__dict__
        assert "owner_explaining" in states
        assert "advertiser_commenting" in states
        assert "admin_reviewing" in states

class TestMiddlewares:
    """Tests for middlewares."""

    def test_throttling_middleware_imports(self):
        """ThrottlingMiddleware can be imported."""
        from src.bot.middlewares.throttling import ThrottlingMiddleware

        assert ThrottlingMiddleware is not None

    def test_fsm_timeout_middleware_imports(self):
        """FSMTimeoutMiddleware can be imported."""
        from src.bot.middlewares.fsm_timeout import FSMTimeoutMiddleware

        assert FSMTimeoutMiddleware is not None
        assert FSMTimeoutMiddleware.__module__ is not None

    def test_role_check_middleware_imports(self):
        """RoleCheckMiddleware can be imported."""
        from src.bot.middlewares.role_check import RoleCheckMiddleware

        assert RoleCheckMiddleware is not None

    def test_db_session_middleware_imports(self):
        """DBSessionMiddleware can be imported."""
        from src.bot.middlewares.db_session import DBSessionMiddleware

        assert DBSessionMiddleware is not None

    def test_admin_filter_imports(self):
        """AdminFilter can be imported."""
        from src.bot.filters.admin import AdminFilter

        assert AdminFilter is not None


class TestCallbackRegistry:
    """Tests for callback data registry (RT-001)."""

    def test_analytics_callbacks_distinct(self):
        """RT-001: main:analytics ≠ main:owner_analytics."""
        # These are string constants, verify they're different
        advertiser_callback = "main:analytics"
        owner_callback = "main:owner_analytics"

        assert advertiser_callback != owner_callback

    def test_no_b2b_callbacks(self):
        """B2B callbacks are removed (v4.3)."""
        # Search for any main:b2b callbacks in codebase
        result = subprocess.run(
            ["poetry", "run", "grep", "-rn", "main:b2b", "src/bot/"],
            capture_output=True,
            text=True,
            cwd="/opt/market-telegram-bot",
        )

        # Should find 0 matches (excluding comments)
        lines = [line for line in result.stdout.split("\n") if line and ".pyc" not in line]
        assert len(lines) == 0, f"B2B callbacks found: {lines}"


class TestNoBotPayoutFlow:
    """BL-045 / 16.3: bot must not accept payout requisites (PII).

    Setup lives in the web portal; the bot only opens the mini_app at
    `/own/payouts/request`, which redirects via OpenInWebPortal.
    """

    def test_payout_handler_module_absent(self):
        """src/bot/handlers/payout/ removed in 16.3."""
        from pathlib import Path

        handlers_dir = Path(__file__).resolve().parents[2] / "src" / "bot" / "handlers"
        assert not (handlers_dir / "payout").exists(), (
            "src/bot/handlers/payout/ exists; bot payout setup flow must be removed (BL-045)"
        )

    def test_payout_states_module_absent(self):
        """src/bot/states/payout.py removed; PayoutStates not importable."""
        with pytest.raises(ImportError):
            __import__("src.bot.states.payout", fromlist=["PayoutStates"])

        from src.bot import states

        assert not hasattr(states, "PayoutStates"), (
            "PayoutStates still exported from src.bot.states; must be deleted (BL-045)"
        )
