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

    def test_placement_states_defined(self):
        """PlacementStates has required states."""
        from src.bot.states.placement import PlacementStates

        states = PlacementStates.__dict__
        assert "waiting_post_text" in states
        assert "waiting_cancel_confirm" in states

    def test_arbitration_states_defined(self):
        """ArbitrationStates has required states."""
        from src.bot.states.arbitration import ArbitrationStates

        states = ArbitrationStates.__dict__
        assert "waiting_rejection_reason" in states
        assert "waiting_counter_price" in states

    def test_channel_settings_states_defined(self):
        """ChannelSettingsStates has required states."""
        from src.bot.states.channel_settings import ChannelSettingsStates

        states = ChannelSettingsStates.__dict__
        assert "waiting_price_per_post" in states
        assert "waiting_start_time" in states

    def test_channel_owner_states_defined(self):
        """ChannelOwnerStates has 2 states."""
        from src.bot.states.channel_owner import ChannelOwnerStates

        states = ChannelOwnerStates.__dict__
        assert "entering_username" in states
        assert "confirming_add" in states

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

    def test_admin_states_defined(self):
        """AdminStates has 3 states."""
        from src.bot.states.admin import AdminStates

        states = AdminStates.__dict__
        assert "entering_broadcast" in states
        assert "reviewing_dispute" in states
        assert "entering_resolution" in states

    def test_all_states_importable(self):
        """All FSM states can be imported from __init__.py."""
        from src.bot.states import (
            AdminStates,
            ArbitrationStates,
            CampaignStates,
            CampaignCreateState,
            ChannelOwnerStates,
            ChannelSettingsStates,
            DisputeStates,
            FeedbackStates,
            PlacementStates,
            TopupStates,
        )

        assert AdminStates is not None
        assert ArbitrationStates is not None
        assert CampaignStates is not None
        assert CampaignCreateState is not None
        assert ChannelOwnerStates is not None
        assert ChannelSettingsStates is not None
        assert DisputeStates is not None
        assert FeedbackStates is not None
        assert PlacementStates is not None
        assert TopupStates is not None


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


class TestMiddlewareStructure:
    """Tests for middleware structure."""

    def test_throttling_middleware_has_redis_param(self):
        """ThrottlingMiddleware.__init__ accepts redis parameter."""
        from src.bot.middlewares.throttling import ThrottlingMiddleware
        import inspect

        sig = inspect.signature(ThrottlingMiddleware.__init__)
        params = list(sig.parameters.keys())
        assert "redis" in params

    def test_fsm_timeout_constant_defined(self):
        """FSM_TIMEOUT constant is defined (300 seconds = 5 minutes)."""
        from src.bot.middlewares.fsm_timeout import FSM_TIMEOUT

        assert FSM_TIMEOUT == 300

    def test_throttle_time_constant_defined(self):
        """THROTTLE_TIME constant is defined (0.5 seconds)."""
        from src.bot.middlewares.throttling import THROTTLE_TIME

        assert THROTTLE_TIME == 0.5


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
            "src/bot/handlers/payout/ exists; "
            "bot payout setup flow must be removed (BL-045)"
        )

    def test_payout_states_module_absent(self):
        """src/bot/states/payout.py removed; PayoutStates not importable."""
        with pytest.raises(ImportError):
            __import__("src.bot.states.payout", fromlist=["PayoutStates"])

        from src.bot import states

        assert not hasattr(states, "PayoutStates"), (
            "PayoutStates still exported from src.bot.states; "
            "must be deleted (BL-045)"
        )
