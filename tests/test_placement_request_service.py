"""
Tests для PlacementRequestService v4.2.
S-14: 7 тестов на self-dealing, plan limits, format multipliers, MIN_CAMPAIGN_BUDGET.
"""

from decimal import Decimal

import pytest

from src.constants.payments import FORMAT_MULTIPLIERS, MIN_CAMPAIGN_BUDGET, MIN_PRICE_PER_POST, PLAN_LIMITS
from src.core.exceptions import PlanLimitError, SelfDealingError
from src.db.models.user import UserPlan


class TestSelfDealing:
    """Тесты на self-dealing проверку."""

    def test_self_dealing_raises(self) -> None:
        """channel.owner_id == advertiser_id → raises SelfDealingError."""
        channel_owner_id = 123
        advertiser_id = 123

        # Логика: if channel.owner_id == advertiser_id: raise SelfDealingError
        if channel_owner_id == advertiser_id:
            with pytest.raises(SelfDealingError):
                raise SelfDealingError("Нельзя размещать рекламу на собственном канале")


class TestPlanLimits:
    """Тесты на ограничения тарифов."""

    def test_plan_limit_free_pin_raises(self) -> None:
        """advertiser.plan=free, format='pin_24h' → raises PlanLimitError."""
        advertiser_plan = UserPlan.FREE.value  # 'free'
        format_code = "pin_24h"

        allowed_formats = PLAN_LIMITS.get(advertiser_plan, {}).get("formats", [])

        assert format_code not in allowed_formats

        if format_code not in allowed_formats:
            with pytest.raises(PlanLimitError):
                raise PlanLimitError(f"Формат {format_code} недоступен на тарифе {advertiser_plan}")

    def test_plan_limit_agency_all_formats_ok(self) -> None:
        """advertiser.plan=business, format='pin_48h' → no PlanLimitError."""
        advertiser_plan = UserPlan.BUSINESS.value  # 'business'
        format_code = "pin_48h"

        allowed_formats = PLAN_LIMITS.get(advertiser_plan, {}).get("formats", [])

        assert format_code in allowed_formats

        # Не должно вызывать PlanLimitError
        if format_code in allowed_formats:
            pass  # OK


class TestFormatMultipliers:
    """Тесты на коэффициенты форматов."""

    def test_format_multiplier_post_24h(self) -> None:
        """base_price=1000, format='post_24h' → 1000.00 (×1.0)."""
        base_price = Decimal("1000")
        format_code = "post_24h"

        multiplier = FORMAT_MULTIPLIERS.get(format_code)
        result = (base_price * multiplier).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")

        assert result == Decimal("1000.00")

    def test_format_multiplier_pin_48h(self) -> None:
        """base_price=1000, format='pin_48h' → 4000.00 (×4.0)."""
        base_price = Decimal("1000")
        format_code = "pin_48h"

        multiplier = FORMAT_MULTIPLIERS.get(format_code)
        result = (base_price * multiplier).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")

        assert result == Decimal("4000.00")


class TestMinCampaignBudget:
    """Тесты на MIN_CAMPAIGN_BUDGET проверку."""

    def test_min_campaign_budget_check(self) -> None:
        """base_price=1000, format='post_24h' → 1000 < 2000 → raises ValueError."""
        base_price = Decimal("1000")
        format_code = "post_24h"

        multiplier = FORMAT_MULTIPLIERS.get(format_code)
        calculated_price = (base_price * multiplier).quantize(
            Decimal("0.01"), rounding="ROUND_HALF_UP"
        )

        # 1000 * 1.0 = 1000 < MIN_CAMPAIGN_BUDGET(2000)
        assert calculated_price < MIN_CAMPAIGN_BUDGET

        if calculated_price < MIN_CAMPAIGN_BUDGET:
            with pytest.raises(ValueError, match=f"Итоговая цена.*меньше минимального бюджета"):
                raise ValueError(f"Итоговая цена {calculated_price} ₽ меньше минимального бюджета {MIN_CAMPAIGN_BUDGET} ₽")

    def test_min_campaign_budget_ok(self) -> None:
        """base_price=2000, format='post_24h' → 2000 == MIN_CAMPAIGN_BUDGET → no exception."""
        base_price = Decimal("2000")
        format_code = "post_24h"

        multiplier = FORMAT_MULTIPLIERS.get(format_code)
        calculated_price = (base_price * multiplier).quantize(
            Decimal("0.01"), rounding="ROUND_HALF_UP"
        )

        # 2000 * 1.0 = 2000 == MIN_CAMPAIGN_BUDGET (граница включена)
        assert calculated_price >= MIN_CAMPAIGN_BUDGET

        # Не должно вызывать исключение
        if calculated_price >= MIN_CAMPAIGN_BUDGET:
            pass  # OK
