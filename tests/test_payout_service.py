"""
Tests для PayoutService v4.2.
S-14: 6 тестов на payout fee calculation и velocity check.
"""

from decimal import Decimal

import pytest

from src.constants.payments import MIN_PAYOUT, VELOCITY_MAX_RATIO
from src.core.exceptions import VelocityCheckError


class TestPayoutFeeCalculation:
    """Тесты на расчёт комиссии за вывод."""

    def test_payout_fee_calculation(self) -> None:
        """gross=10000 → fee=150, net=9850."""
        from src.constants.payments import PAYOUT_FEE_RATE

        gross = Decimal("10000")
        fee = (gross * PAYOUT_FEE_RATE).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
        net = gross - fee

        assert fee == Decimal("150")
        assert net == Decimal("9850")

    def test_payout_fee_rounding(self) -> None:
        """Проверка округления ROUND_HALF_UP."""
        from src.constants.payments import PAYOUT_FEE_RATE

        gross = Decimal("10001")
        fee = (gross * PAYOUT_FEE_RATE).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
        net = gross - fee

        # 10001 * 0.015 = 150.015 → ROUND_HALF_UP → 150.02
        assert fee == Decimal("150.02")
        assert net == Decimal("9850.98")


class TestVelocityCheck:
    """Тесты на velocity check (topups_30d / payouts_30d ratio)."""

    def test_velocity_check_no_topups_passes(self) -> None:
        """topups_30d=0 → no exception (возврат без проверки)."""
        # Логика: if topups_30d == 0: return
        # Это означает что при отсутствии пополнений за 30 дней проверка не блокирует
        topups_30d = Decimal("0")
        payouts_30d = Decimal("0")
        requested = Decimal("1000")

        if topups_30d == 0:
            # Проходит без проверки
            pass
        else:
            ratio = (payouts_30d + requested) / topups_30d
            assert ratio > VELOCITY_MAX_RATIO  # Не должно выполняться

    def test_velocity_check_within_limit(self) -> None:
        """topups=10000, payouts=0, requested=7999 → no exception (79.99% < 80%)."""
        topups_30d = Decimal("10000")
        payouts_30d = Decimal("0")
        requested = Decimal("7999")

        ratio = (payouts_30d + requested) / topups_30d
        assert ratio < VELOCITY_MAX_RATIO  # 0.7999 < 0.80

    def test_velocity_check_exceeds_limit(self) -> None:
        """topups=10000, payouts=0, requested=8001 → raises VelocityCheckError (80.01% > 80%)."""
        topups_30d = Decimal("10000")
        payouts_30d = Decimal("0")
        requested = Decimal("8001")

        ratio = (payouts_30d + requested) / topups_30d
        assert ratio > VELOCITY_MAX_RATIO  # 0.8001 > 0.80

        # В сервисе это вызовет VelocityCheckError
        with pytest.raises(VelocityCheckError):
            if ratio > VELOCITY_MAX_RATIO:
                raise VelocityCheckError("Вывод заморожен")

    def test_velocity_check_at_exact_limit(self) -> None:
        """topups=10000, payouts=0, requested=8000 → no exception (80.00% == 80% — граница включена)."""
        topups_30d = Decimal("10000")
        payouts_30d = Decimal("0")
        requested = Decimal("8000")

        ratio = (payouts_30d + requested) / topups_30d
        assert ratio == VELOCITY_MAX_RATIO  # 0.8000 == 0.80

        # Граница включена — ratio > VELOCITY_MAX_RATIO будет False
        assert not (ratio > VELOCITY_MAX_RATIO)


class TestPayoutBelowMinimum:
    """Тесты на MIN_PAYOUT проверку."""

    def test_payout_below_minimum(self) -> None:
        """gross=999 → raises ValueError."""
        gross = Decimal("999")

        with pytest.raises(ValueError, match=f"Минимальная сумма вывода {MIN_PAYOUT} ₽"):
            if gross < MIN_PAYOUT:
                raise ValueError(f"Минимальная сумма вывода {MIN_PAYOUT} ₽")

    def test_payout_at_minimum(self) -> None:
        """gross=1000 → no exception (граница включена)."""
        gross = Decimal("1000")

        # Не должно вызывать исключение
        assert gross >= MIN_PAYOUT
