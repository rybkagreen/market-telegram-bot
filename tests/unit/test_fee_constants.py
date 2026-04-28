"""Regression: fee constants must satisfy invariants.

If any constant changes, this test verifies the math still adds up
before deploy.
"""

from decimal import Decimal

from src.constants.fees import (
    CANCEL_REFUND_ADVERTISER_RATE,
    CANCEL_REFUND_OWNER_RATE,
    CANCEL_REFUND_PLATFORM_RATE,
    OWNER_SHARE_RATE,
    PLATFORM_COMMISSION_RATE,
    SERVICE_FEE_RATE,
    YOOKASSA_FEE_RATE,
)


def test_placement_split_sums_to_one() -> None:
    """20% + 80% = 100%."""
    assert PLATFORM_COMMISSION_RATE + OWNER_SHARE_RATE == Decimal("1.00")


def test_cancel_splits_sum_to_one() -> None:
    """50% + 40% + 10% = 100%."""
    assert (
        CANCEL_REFUND_ADVERTISER_RATE
        + CANCEL_REFUND_OWNER_RATE
        + CANCEL_REFUND_PLATFORM_RATE
    ) == Decimal("1.00")


def test_owner_net_rate_computation() -> None:
    """Owner net = 80% × (1 - 1.5%) = 78.8%."""
    expected_owner_net = Decimal("0.788")
    actual = (OWNER_SHARE_RATE * (Decimal("1") - SERVICE_FEE_RATE)).quantize(
        Decimal("0.001")
    )
    assert actual == expected_owner_net


def test_platform_total_rate_computation() -> None:
    """Platform total = 20% + 80% × 1.5% = 21.2%."""
    expected_platform_total = Decimal("0.212")
    actual = (
        PLATFORM_COMMISSION_RATE + OWNER_SHARE_RATE * SERVICE_FEE_RATE
    ).quantize(Decimal("0.001"))
    assert actual == expected_platform_total


def test_owner_plus_platform_equals_one() -> None:
    """Owner net + platform total = 100% (no money lost on rounding at constant level)."""
    owner_net_rate = OWNER_SHARE_RATE * (Decimal("1") - SERVICE_FEE_RATE)
    platform_total_rate = (
        PLATFORM_COMMISSION_RATE + OWNER_SHARE_RATE * SERVICE_FEE_RATE
    )
    assert (owner_net_rate + platform_total_rate).quantize(
        Decimal("0.001")
    ) == Decimal("1.000")


def test_topup_fee_rate_correct() -> None:
    """3.5% YooKassa pass-through."""
    assert YOOKASSA_FEE_RATE == Decimal("0.035")


def test_release_escrow_split_on_1000_rub() -> None:
    """Concrete trace: 1000 ₽ placement → owner 788 ₽, platform 212 ₽."""
    final_price = Decimal("1000.00")

    owner_gross = (final_price * OWNER_SHARE_RATE).quantize(Decimal("0.01"))
    service_fee = (owner_gross * SERVICE_FEE_RATE).quantize(Decimal("0.01"))
    owner_net = owner_gross - service_fee

    platform_commission = (final_price * PLATFORM_COMMISSION_RATE).quantize(
        Decimal("0.01")
    )
    platform_total = platform_commission + service_fee

    assert owner_net == Decimal("788.00")
    assert platform_total == Decimal("212.00")
    assert owner_net + platform_total == final_price


def test_cancel_split_on_1000_rub() -> None:
    """Concrete trace: 1000 ₽ post-escrow cancel → 500/400/100."""
    final_price = Decimal("1000.00")

    advertiser = (final_price * CANCEL_REFUND_ADVERTISER_RATE).quantize(
        Decimal("0.01")
    )
    owner = (final_price * CANCEL_REFUND_OWNER_RATE).quantize(Decimal("0.01"))
    platform = (final_price * CANCEL_REFUND_PLATFORM_RATE).quantize(
        Decimal("0.01")
    )

    assert advertiser == Decimal("500.00")
    assert owner == Decimal("400.00")
    assert platform == Decimal("100.00")
    assert advertiser + owner + platform == final_price
