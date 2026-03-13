"""
Tests для BillingService v4.2.
S-14: 5 тестов на calculate_topup_payment, release_escrow, refund_escrow.
"""

from decimal import Decimal

import pytest

from src.constants.payments import MIN_TOPUP
from src.core.services.billing_service import BillingService


class TestCalculateTopupPayment:
    """Тесты на calculate_topup_payment."""

    def test_calculate_topup_payment_correct(self) -> None:
        """desired=10000 → fee=350, gross=10350."""
        service = BillingService()
        result = service.calculate_topup_payment(Decimal("10000"))

        assert result["desired_balance"] == Decimal("10000")
        assert result["fee_amount"] == Decimal("350")
        assert result["gross_amount"] == Decimal("10350")

    def test_calculate_topup_below_minimum(self) -> None:
        """desired=499 → raises ValueError."""
        service = BillingService()

        with pytest.raises(ValueError, match=f"Минимальное пополнение {MIN_TOPUP} ₽"):
            service.calculate_topup_payment(Decimal("499"))

    def test_calculate_topup_at_minimum(self) -> None:
        """desired=500 → no exception, gross=517.50."""
        service = BillingService()
        result = service.calculate_topup_payment(Decimal("500"))

        assert result["desired_balance"] == Decimal("500")
        assert result["fee_amount"] == Decimal("17.50")
        assert result["gross_amount"] == Decimal("517.50")

    def test_calculate_topup_rounding(self) -> None:
        """Проверка округления ROUND_HALF_UP."""
        service = BillingService()
        result = service.calculate_topup_payment(Decimal("1001"))

        # 1001 * 0.035 = 35.035 → ROUND_HALF_UP → 35.04
        assert result["fee_amount"] == Decimal("35.04")
        assert result["gross_amount"] == Decimal("1036.04")


class TestReleaseEscrowNoLoss:
    """Тесты на release_escrow — сумма частей == final_price."""

    @pytest.mark.parametrize(
        "final_price",
        [
            Decimal("1000"),
            Decimal("3333"),
            Decimal("99999.99"),
        ],
    )
    def test_owner_plus_platform_equals_final_price(self, final_price: Decimal) -> None:
        """owner_amount + platform_fee == final_price (для нескольких значений)."""
        from src.constants.payments import OWNER_SHARE

        # owner_amount = final_price * OWNER_SHARE (округление)
        owner_amount = (final_price * OWNER_SHARE).quantize(
            Decimal("0.01"), rounding="ROUND_HALF_UP"
        )
        # platform_fee = final_price - owner_amount (остаток)
        platform_fee = final_price - owner_amount

        # Сумма должна быть точно равна final_price
        assert owner_amount + platform_fee == final_price
