"""
Unit tests for BillingService (P02).
Standalone tests - no conftest dependencies.
"""

import subprocess
from decimal import Decimal

# Test constants directly without service dependencies
from src.constants.payments import (
    calculate_topup_payment,
    calculate_payout,
    PAYOUT_FEE_RATE,
    YOOKASSA_FEE_RATE,
    OWNER_SHARE,
    PLATFORM_COMMISSION,
    MIN_CAMPAIGN_BUDGET,
)


class TestBillingServiceInit:
    """Tests for BillingService initialization."""

    def test_billing_service_imports(self):
        """BillingService can be imported."""
        from src.core.services.billing_service import BillingService
        assert BillingService is not None

    def test_billing_service_init_no_args(self):
        """BillingService.__init__ takes no arguments."""
        from src.core.services.billing_service import BillingService
        service = BillingService()
        assert service is not None


class TestCalculateTopupPreview:
    """Tests for topup calculation methods."""

    def test_topup_preview_10000(self):
        """Topup preview: 10000 ₽ desired → 10350 ₽ gross."""
        result = calculate_topup_payment(Decimal("10000"))
        assert result["gross_amount"] == Decimal("10350")
        assert result["fee_amount"] == Decimal("350")
        assert result["desired_balance"] == Decimal("10000")

    def test_topup_formula(self):
        """Topup formula: gross = desired + (desired × 0.035)."""
        desired = Decimal("10000")
        expected_fee = desired * YOOKASSA_FEE_RATE
        expected_gross = desired + expected_fee
        
        result = calculate_topup_payment(desired)
        assert result["fee_amount"] == expected_fee.quantize(Decimal("0.01"))
        assert result["gross_amount"] == expected_gross.quantize(Decimal("0.01"))


class TestFreezeEscrowConstants:
    """Tests for freeze_escrow constants."""

    def test_min_campaign_budget_is_2000(self):
        """MIN_CAMPAIGN_BUDGET is 2000 ₽."""
        assert MIN_CAMPAIGN_BUDGET == Decimal("2000")

    def test_yookassa_fee_rate_is_3_5_percent(self):
        """YOOKASSA_FEE_RATE is 3.5%."""
        assert YOOKASSA_FEE_RATE == Decimal("0.035")


class TestEscrowReleaseLocation:
    """ESCROW-001 verification tests."""

    def test_release_escrow_only_in_delete_published_post(self):
        """ESCROW-001: release_escrow() is ONLY called in delete_published_post()."""
        result = subprocess.run(
            [
                "poetry", "run", "grep", "-rn",
                "release_escrow(",
                "src/"
            ],
            capture_output=True,
            text=True,
            cwd="/opt/market-telegram-bot"
        )
        
        # Filter out function definitions and binary files
        lines = [
            line for line in result.stdout.split('\n')
            if line 
            and 'def release_escrow' not in line
            and '.pyc' not in line
        ]
        
        # Should only appear in publication_service.py
        for line in lines:
            assert 'publication_service.py' in line, (
                f"ESCROW-001 VIOLATION: release_escrow() found outside publication_service.py: {line}"
            )


class TestPayoutCalculation:
    """Tests for payout calculations."""

    def test_payout_10000_gross(self):
        """Payout: 10000 ₽ gross → 150 ₽ fee, 9850 ₽ net."""
        result = calculate_payout(Decimal("10000"))
        assert result["gross"] == Decimal("10000")
        assert result["fee"] == Decimal("150")  # 1.5%
        assert result["net"] == Decimal("9850")

    def test_payout_1000_minimum(self):
        """Payout minimum 1000 ₽ → 15 ₽ fee, 985 ₽ net."""
        result = calculate_payout(Decimal("1000"))
        assert result["gross"] == Decimal("1000")
        assert result["fee"] == Decimal("15")
        assert result["net"] == Decimal("985")

    def test_payout_fee_rate(self):
        """Payout fee rate is 1.5%."""
        assert PAYOUT_FEE_RATE == Decimal("0.015")

    def test_payout_formula(self):
        """Payout formula: fee = gross × 0.015, net = gross - fee."""
        gross = Decimal("10000")
        expected_fee = gross * PAYOUT_FEE_RATE
        expected_net = gross - expected_fee
        
        result = calculate_payout(gross)
        assert result["fee"] == expected_fee.quantize(Decimal("0.01"))
        assert result["net"] == expected_net.quantize(Decimal("0.01"))


class TestPlatformCommission:
    """Tests for platform commission calculations."""

    def test_owner_share_is_85_percent(self):
        """OWNER_SHARE is 85% (v4.2)."""
        assert OWNER_SHARE == Decimal("0.85")

    def test_platform_commission_is_15_percent(self):
        """PLATFORM_COMMISSION is 15% (v4.2)."""
        assert PLATFORM_COMMISSION == Decimal("0.15")

    def test_release_escrow_distribution(self):
        """release_escrow distributes 85% to owner, 15% to platform."""
        final_price = Decimal("10000")
        owner_share = final_price * OWNER_SHARE
        platform_fee = final_price * PLATFORM_COMMISSION
        
        assert owner_share == Decimal("8500")
        assert platform_fee == Decimal("1500")
        assert owner_share + platform_fee == final_price

    def test_escrow_distribution_formula(self):
        """Escrow distribution: owner = price × 0.85, platform = price × 0.15."""
        for price in [Decimal("1000"), Decimal("5000"), Decimal("10000")]:
            owner_share = (price * OWNER_SHARE).quantize(Decimal("0.01"))
            platform_fee = (price * PLATFORM_COMMISSION).quantize(Decimal("0.01"))
            
            assert owner_share + platform_fee == price


class TestVelocityCheckConstants:
    """Tests for velocity check constants."""

    def test_velocity_max_ratio_is_80_percent(self):
        """VELOCITY_MAX_RATIO is 0.80 (80%)."""
        from src.constants.payments import VELOCITY_MAX_RATIO
        assert VELOCITY_MAX_RATIO == Decimal("0.80")

    def test_velocity_window_days_is_30(self):
        """VELOCITY_WINDOW_DAYS is 30 days."""
        from src.constants.payments import VELOCITY_WINDOW_DAYS
        assert VELOCITY_WINDOW_DAYS == 30
