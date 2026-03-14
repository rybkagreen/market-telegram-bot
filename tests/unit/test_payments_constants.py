"""
Unit tests for payment constants (P01).
Standalone tests - no conftest dependencies.
"""

import pytest
from decimal import Decimal

# Import directly from constants module (no app context needed)
from src.constants.payments import (
    calculate_topup_payment,
    calculate_payout,
    get_format_price,
    is_format_allowed_for_plan,
    FORMAT_MULTIPLIERS,
    PLAN_LIMITS,
    YOOKASSA_FEE_RATE,
    PAYOUT_FEE_RATE,
    OWNER_SHARE,
    PLATFORM_COMMISSION,
)


class TestCalculateTopupPayment:
    """Tests for calculate_topup_payment function."""

    def test_topup_10000(self):
        """Topup 10000 ₽ → gross=10350, fee=350."""
        result = calculate_topup_payment(Decimal("10000"))
        assert result["desired_balance"] == Decimal("10000")
        assert result["fee_amount"] == Decimal("350")
        assert result["gross_amount"] == Decimal("10350")

    def test_topup_500_minimum(self):
        """Topup minimum 500 ₽ → gross=517.50, fee=17.50."""
        result = calculate_topup_payment(Decimal("500"))
        assert result["desired_balance"] == Decimal("500")
        assert result["fee_amount"] == Decimal("17.50")
        assert result["gross_amount"] == Decimal("517.50")

    def test_topup_1000(self):
        """Topup 1000 ₽ → gross=1035, fee=35."""
        result = calculate_topup_payment(Decimal("1000"))
        assert result["desired_balance"] == Decimal("1000")
        assert result["fee_amount"] == Decimal("35")
        assert result["gross_amount"] == Decimal("1035")

    def test_topup_300000_maximum(self):
        """Topup maximum 300000 ₽ → gross=310500, fee=10500."""
        result = calculate_topup_payment(Decimal("300000"))
        assert result["desired_balance"] == Decimal("300000")
        assert result["fee_amount"] == Decimal("10500")
        assert result["gross_amount"] == Decimal("310500")

    def test_fee_rate_is_3_5_percent(self):
        """Verify YOOKASSA_FEE_RATE is 3.5%."""
        assert YOOKASSA_FEE_RATE == Decimal("0.035")


class TestCalculatePayout:
    """Tests for calculate_payout function."""

    def test_payout_10000(self):
        """Payout 10000 ₽ → fee=150, net=9850."""
        result = calculate_payout(Decimal("10000"))
        assert result["gross"] == Decimal("10000")
        assert result["fee"] == Decimal("150")
        assert result["net"] == Decimal("9850")

    def test_payout_1000_minimum(self):
        """Payout minimum 1000 ₽ → fee=15, net=985."""
        result = calculate_payout(Decimal("1000"))
        assert result["gross"] == Decimal("1000")
        assert result["fee"] == Decimal("15")
        assert result["net"] == Decimal("985")

    def test_payout_fee_rate_is_1_5_percent(self):
        """Verify PAYOUT_FEE_RATE is 1.5%."""
        assert PAYOUT_FEE_RATE == Decimal("0.015")


class TestGetFormatPrice:
    """Tests for get_format_price function."""

    def test_post_24h_base_multiplier(self):
        """post_24h has 1.0× multiplier (base)."""
        assert get_format_price(Decimal("1000"), "post_24h") == Decimal("1000")

    def test_post_48h_multiplier(self):
        """post_48h has 1.4× multiplier."""
        assert get_format_price(Decimal("1000"), "post_48h") == Decimal("1400")

    def test_post_7d_multiplier(self):
        """post_7d has 2.0× multiplier."""
        assert get_format_price(Decimal("1000"), "post_7d") == Decimal("2000")

    def test_pin_24h_multiplier(self):
        """pin_24h has 3.0× multiplier."""
        assert get_format_price(Decimal("1000"), "pin_24h") == Decimal("3000")

    def test_pin_48h_multiplier(self):
        """pin_48h has 4.0× multiplier."""
        assert get_format_price(Decimal("1000"), "pin_48h") == Decimal("4000")

    def test_format_multipliers_complete(self):
        """All 5 formats have multipliers defined."""
        expected_formats = {"post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h"}
        assert set(FORMAT_MULTIPLIERS.keys()) == expected_formats


class TestIsFormatAllowedForPlan:
    """Tests for is_format_allowed_for_plan function."""

    def test_free_plan_only_post_24h(self):
        """Free plan only allows post_24h."""
        assert is_format_allowed_for_plan("free", "post_24h") is True
        assert is_format_allowed_for_plan("free", "post_48h") is False
        assert is_format_allowed_for_plan("free", "pin_24h") is False

    def test_starter_plan_formats(self):
        """Starter plan allows post_24h and post_48h."""
        assert is_format_allowed_for_plan("starter", "post_24h") is True
        assert is_format_allowed_for_plan("starter", "post_48h") is True
        assert is_format_allowed_for_plan("starter", "post_7d") is False

    def test_pro_plan_formats(self):
        """Pro plan allows post_24h, post_48h, post_7d."""
        assert is_format_allowed_for_plan("pro", "post_24h") is True
        assert is_format_allowed_for_plan("pro", "post_48h") is True
        assert is_format_allowed_for_plan("pro", "post_7d") is True
        assert is_format_allowed_for_plan("pro", "pin_24h") is False

    def test_business_plan_all_formats(self):
        """Business plan allows all 5 formats."""
        for fmt in ["post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h"]:
            assert is_format_allowed_for_plan("business", fmt) is True

    def test_plan_limits_uses_business_key(self):
        """PLAN-001: PLAN_LIMITS uses 'business' key (NOT 'agency')."""
        assert "business" in PLAN_LIMITS
        assert "agency" not in PLAN_LIMITS


class TestPlanLimits:
    """Tests for PLAN_LIMITS structure."""

    def test_all_plans_defined(self):
        """All 4 plans are defined."""
        expected_plans = {"free", "starter", "pro", "business"}
        assert set(PLAN_LIMITS.keys()) == expected_plans

    def test_plan_structure(self):
        """Each plan has active_campaigns, ai_per_month, formats."""
        for plan, limits in PLAN_LIMITS.items():
            assert "active_campaigns" in limits
            assert "ai_per_month" in limits
            assert "formats" in limits
            assert isinstance(limits["formats"], list)

    def test_business_unlimited(self):
        """Business plan has unlimited campaigns and AI."""
        assert PLAN_LIMITS["business"]["active_campaigns"] == -1
        assert PLAN_LIMITS["business"]["ai_per_month"] == -1
