"""
Tests для констант финансовой модели.
S-14: Регрессионная защита HOTFIX (PLAN_LIMITS['business']).
"""

from decimal import Decimal

from src.constants.fees import (
    OWNER_SHARE_RATE,
    PLATFORM_COMMISSION_RATE,
    PLATFORM_USN_RATE,
    YOOKASSA_FEE_RATE,
)
from src.constants.payments import (
    FORMAT_DURATIONS_SECONDS,
    FORMAT_MULTIPLIERS,
    MIN_CAMPAIGN_BUDGET,
    MIN_PAYOUT,
    MIN_PRICE_PER_POST,
    MIN_TOPUP,
    PAYOUT_FEE_RATE,
    PLAN_LIMITS,
    VELOCITY_MAX_RATIO,
    VELOCITY_WINDOW_DAYS,
)


def test_platform_commission_value() -> None:
    """PLATFORM_COMMISSION_RATE == 0.20 (20%)."""
    assert PLATFORM_COMMISSION_RATE == Decimal("0.20")


def test_owner_share_value() -> None:
    """OWNER_SHARE_RATE == 0.80 (80%)."""
    assert OWNER_SHARE_RATE == Decimal("0.80")


def test_commission_plus_share_equals_one() -> None:
    """PLATFORM_COMMISSION_RATE + OWNER_SHARE_RATE == 1.00 (без потерь)."""
    assert PLATFORM_COMMISSION_RATE + OWNER_SHARE_RATE == Decimal("1.00")


def test_yookassa_fee_rate() -> None:
    """YOOKASSA_FEE_RATE == 0.035 (3.5%)."""
    assert YOOKASSA_FEE_RATE == Decimal("0.035")


def test_platform_usn_rate() -> None:
    """PLATFORM_USN_RATE == 0.06 (УСН 6%, paid by platform from commission)."""
    assert PLATFORM_USN_RATE == Decimal("0.06")


def test_payout_fee_rate() -> None:
    """PAYOUT_FEE_RATE == 0.015 (1.5%)."""
    assert PAYOUT_FEE_RATE == Decimal("0.015")


def test_velocity_max_ratio() -> None:
    """VELOCITY_MAX_RATIO == 0.80 (80%)."""
    assert VELOCITY_MAX_RATIO == Decimal("0.80")


def test_velocity_window_days() -> None:
    """VELOCITY_WINDOW_DAYS == 30."""
    assert VELOCITY_WINDOW_DAYS == 30


def test_min_topup() -> None:
    """MIN_TOPUP == 500."""
    assert MIN_TOPUP == Decimal("500")


def test_min_payout() -> None:
    """MIN_PAYOUT == 1000."""
    assert MIN_PAYOUT == Decimal("1000")


def test_min_campaign_budget() -> None:
    """MIN_CAMPAIGN_BUDGET == 2000."""
    assert MIN_CAMPAIGN_BUDGET == Decimal("2000")


def test_min_price_per_post() -> None:
    """MIN_PRICE_PER_POST == 1000."""
    assert MIN_PRICE_PER_POST == Decimal("1000")


def test_plan_limits_has_business_key() -> None:
    """HOTFIX проверка: 'business' in PLAN_LIMITS."""
    assert "business" in PLAN_LIMITS


def test_plan_limits_no_agency_key() -> None:
    """HOTFIX проверка: 'agency' not in PLAN_LIMITS."""
    assert "agency" not in PLAN_LIMITS


def test_format_multipliers_count() -> None:
    """FORMAT_MULTIPLIERS содержит 5 форматов."""
    assert len(FORMAT_MULTIPLIERS) == 5


def test_format_multipliers_keys() -> None:
    """FORMAT_MULTIPLIERS ключи: post_24h, post_48h, post_7d, pin_24h, pin_48h."""
    expected_keys = {"post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h"}
    assert set(FORMAT_MULTIPLIERS.keys()) == expected_keys


def test_format_multipliers_values() -> None:
    """FORMAT_MULTIPLIERS значения: 1.0, 1.4, 2.0, 3.0, 4.0."""
    assert FORMAT_MULTIPLIERS["post_24h"] == Decimal("1.0")
    assert FORMAT_MULTIPLIERS["post_48h"] == Decimal("1.4")
    assert FORMAT_MULTIPLIERS["post_7d"] == Decimal("2.0")
    assert FORMAT_MULTIPLIERS["pin_24h"] == Decimal("3.0")
    assert FORMAT_MULTIPLIERS["pin_48h"] == Decimal("4.0")


def test_format_durations_seconds() -> None:
    """FORMAT_DURATIONS_SECONDS содержит 5 форматов."""
    assert len(FORMAT_DURATIONS_SECONDS) == 5
    assert FORMAT_DURATIONS_SECONDS["post_24h"] == 86400
    assert FORMAT_DURATIONS_SECONDS["post_48h"] == 172800
    assert FORMAT_DURATIONS_SECONDS["post_7d"] == 604800
