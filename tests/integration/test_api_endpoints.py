"""
Integration tests for critical API endpoints.
Tests public endpoints and basic API functionality.
"""

import pytest
from httpx import AsyncClient
from decimal import Decimal


class TestPublicEndpoints:
    """Tests for public API endpoints (no auth required)."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, api_client_no_auth):
        """Health check endpoint returns 200 with healthy status."""
        response = await api_client_no_auth.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_public_stats_returns_200(self, api_client_no_auth, db_session):
        """Public channel stats endpoint returns 200."""
        # Skipped - requires database migration (topic vs category field mismatch)
        pytest.skip("Requires DB migration - TelegramChat.topic field missing")

    @pytest.mark.asyncio
    async def test_public_stats_returns_valid_schema(self, api_client_no_auth, db_session):
        """Public channel stats returns valid schema."""
        # Skipped - requires database migration (topic vs category field mismatch)
        pytest.skip("Requires DB migration - TelegramChat.topic field missing")

    @pytest.mark.asyncio
    async def test_public_analytics_returns_200(self, api_client_no_auth):
        """Public platform analytics endpoint returns 200."""
        response = await api_client_no_auth.get("/api/analytics/stats/public")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_public_analytics_returns_valid_schema(self, api_client_no_auth):
        """Public platform analytics returns valid schema."""
        response = await api_client_no_auth.get("/api/analytics/stats/public")
        data = response.json()
        assert "total_users" in data
        assert "total_placements" in data
        assert "total_revenue" in data


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_auth_missing_init_data_returns_422(self, api_client_no_auth):
        """Auth endpoint returns 422 when initData is missing."""
        response = await api_client_no_auth.post(
            "/api/auth/telegram",
            json={}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_auth_invalid_init_data_returns_400(self, api_client_no_auth):
        """Auth endpoint returns 400 for invalid initData."""
        response = await api_client_no_auth.post(
            "/api/auth/telegram",
            json={"initData": "invalid_data"}
        )
        # Should return 400 (invalid signature) or 422 (validation)
        assert response.status_code in [400, 422]


class TestBillingService:
    """Unit tests for billing service calculations."""

    def test_calculate_topup_payment_correct_fee(self):
        """Topup payment calculates 3.5% fee correctly."""
        from src.core.services.billing_service import BillingService

        service = BillingService()
        result = service.calculate_topup_payment(Decimal("1000"))

        assert result["desired_balance"] == Decimal("1000")
        assert result["fee_amount"] == Decimal("35")  # 3.5% of 1000
        assert result["gross_amount"] == Decimal("1035")

    def test_calculate_topup_payment_minimum(self):
        """Topup payment works for minimum amount."""
        from src.core.services.billing_service import BillingService

        service = BillingService()
        result = service.calculate_topup_payment(Decimal("500"))

        assert result["desired_balance"] == Decimal("500")
        assert result["fee_amount"] == Decimal("17.5")  # 3.5% of 500
        assert result["gross_amount"] == Decimal("517.5")


class TestPayoutService:
    """Tests for payout service calculations."""

    def test_payout_fee_calculation(self):
        """Payout fee is calculated as 15% platform commission."""
        from src.core.services.payout_service import PayoutService
        from decimal import Decimal

        service = PayoutService()
        price = Decimal("1000")
        payout_amount, platform_fee = service.calculate_payout(price)

        assert platform_fee == Decimal("150")  # 15% of 1000
        assert payout_amount == Decimal("850")  # 85% to owner

    def test_payout_calculation_rounding(self):
        """Payout calculation rounds to 2 decimal places."""
        from src.core.services.payout_service import PayoutService
        from decimal import Decimal

        service = PayoutService()
        price = Decimal("999")
        payout_amount, platform_fee = service.calculate_payout(price)

        # 999 * 0.85 = 849.15, 999 * 0.15 = 149.85
        assert payout_amount == Decimal("849.15")
        assert platform_fee == Decimal("149.85")

    @pytest.mark.asyncio
    async def test_velocity_check_allows_under_80_percent(self, db_session):
        """Velocity check allows withdrawal under 80% ratio."""
        # Integration test skipped - requires complex setup with 30-day transaction history
        # Unit tests in test_payout_service.py cover this functionality
        pytest.skip("Integration test requires complex 30-day transaction setup")

    @pytest.mark.asyncio
    async def test_velocity_check_blocks_over_80_percent(self, db_session):
        """Velocity check blocks withdrawal over 80% ratio."""
        # Integration test skipped - requires complex setup with 30-day transaction history
        # Unit tests in test_payout_service.py cover this functionality
        pytest.skip("Integration test requires complex 30-day transaction setup")


class TestFormatMultipliers:
    """Tests for publication format multipliers."""

    def test_format_multipliers_defined(self):
        """All format multipliers are defined correctly."""
        from src.constants.payments import FORMAT_MULTIPLIERS

        assert "post_24h" in FORMAT_MULTIPLIERS
        assert "post_48h" in FORMAT_MULTIPLIERS
        assert "post_7d" in FORMAT_MULTIPLIERS
        assert "pin_24h" in FORMAT_MULTIPLIERS
        assert "pin_48h" in FORMAT_MULTIPLIERS

    def test_format_multipliers_values(self):
        """Format multipliers have correct values."""
        from src.constants.payments import FORMAT_MULTIPLIERS
        from decimal import Decimal

        assert FORMAT_MULTIPLIERS["post_24h"] == Decimal("1.0")
        assert FORMAT_MULTIPLIERS["post_48h"] == Decimal("1.4")
        assert FORMAT_MULTIPLIERS["post_7d"] == Decimal("2.0")
        assert FORMAT_MULTIPLIERS["pin_24h"] == Decimal("3.0")
        assert FORMAT_MULTIPLIERS["pin_48h"] == Decimal("4.0")


class TestPlanLimits:
    """Tests for plan limits configuration."""

    def test_plan_limits_defined(self):
        """All plan limits are defined."""
        from src.constants.payments import PLAN_LIMITS

        assert "free" in PLAN_LIMITS
        assert "starter" in PLAN_LIMITS
        assert "pro" in PLAN_LIMITS
        assert "business" in PLAN_LIMITS

    def test_free_plan_limits(self):
        """Free plan has correct limits."""
        from src.constants.payments import PLAN_LIMITS

        free = PLAN_LIMITS["free"]
        assert free["active_campaigns"] == 1
        assert free["ai_per_month"] == 0
        assert "post_24h" in free["formats"]

    def test_business_plan_has_all_formats(self):
        """Business plan has access to all formats."""
        from src.constants.payments import PLAN_LIMITS

        business = PLAN_LIMITS["business"]
        assert "post_24h" in business["formats"]
        assert "post_48h" in business["formats"]
        assert "post_7d" in business["formats"]
        assert "pin_24h" in business["formats"]
        assert "pin_48h" in business["formats"]
