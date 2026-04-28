"""Fee constants — single source of truth.

Any fee/percentage anywhere in the codebase MUST import from here.
AST lint (test_no_hardcoded_fees) enforces this.

Changes here are LEGAL CONTRACT CHANGES:
- Bump CONTRACT_TEMPLATE_VERSION when modifying.
- Update legal templates to match.
- Re-acceptance flow triggers automatically.

References:
- Промт 15.7 (this file).
- PLAN_centralized_fee_model_consistency.md.
- BILLING_REWRITE_PLAN_2026-04-28.md.
"""

from decimal import Decimal

# ==================== TOPUP ====================

# YooKassa pass-through fee. Platform earns 0 on topup.
# User pays desired_balance × (1 + YOOKASSA_FEE_RATE).
YOOKASSA_FEE_RATE = Decimal("0.035")


# ==================== PLACEMENT SUCCESSFUL RELEASE ====================

# Split of placement_price on successful escrow release (after publication).
# Sums must == 1.00 — enforced by test_fee_constants_consistency.
PLATFORM_COMMISSION_RATE = Decimal("0.20")
OWNER_SHARE_RATE = Decimal("0.80")

# Service fee — withheld from owner share at escrow release.
# Effective owner net = OWNER_SHARE_RATE × (1 - SERVICE_FEE_RATE) = 0.788.
# Platform gross = PLATFORM_COMMISSION_RATE + OWNER_SHARE_RATE × SERVICE_FEE_RATE = 0.212.
SERVICE_FEE_RATE = Decimal("0.015")


# ==================== ADVERTISER CANCEL POST-ESCROW PRE-PUBLISH ====================

# Pre-escrow cancel: 100% advertiser refund (no constants needed — full sum).
# Post-publish cancel: 0% refund (treated as completed service).
# Post-escrow pre-publish split — sums must == 1.00.
CANCEL_REFUND_ADVERTISER_RATE = Decimal("0.50")
CANCEL_REFUND_OWNER_RATE = Decimal("0.40")
CANCEL_REFUND_PLATFORM_RATE = Decimal("0.10")


# ==================== TAX (independent — not user-charged fees) ====================

# Self-employed contractor (НПД) tax obligations — paid BY the contractor,
# not charged on top of placement_price.
NPD_RATE_FROM_INDIVIDUAL = Decimal("0.04")  # 4% if customer = ФЛ
NPD_RATE_FROM_LEGAL = Decimal("0.06")       # 6% if customer = ИП/ООО

# Platform's УСН obligations — paid BY platform from its own commission,
# NOT charged to user. Recorded for accounting only.
PLATFORM_USN_RATE = Decimal("0.06")


# ==================== DERIVED RATES & DISPLAY HELPERS ====================
#
# Effective rates MUST be derived from the gross constants above — никаких
# hardcoded "0.788" / "0.212" / "78,8%" / "21,2%" в коде. AST-линт
# `tests/unit/test_no_hardcoded_fees.py` блокирует литералы.

OWNER_NET_RATE = OWNER_SHARE_RATE * (Decimal("1") - SERVICE_FEE_RATE)
PLATFORM_TOTAL_RATE = Decimal("1") - OWNER_NET_RATE


def format_rate_pct(
    rate: Decimal | float, fraction_digits: int = 1, comma: bool = True
) -> str:
    """Format a fraction (0.788) as a localised percent string ("78,8%").

    `comma=True` uses RU decimal comma; `False` keeps the dot.
    """
    pct = Decimal(str(rate)) * Decimal("100")
    quant = Decimal("1") if fraction_digits <= 0 else Decimal("0." + "0" * fraction_digits)
    formatted = f"{pct.quantize(quant):.{max(fraction_digits, 0)}f}"
    if comma:
        formatted = formatted.replace(".", ",")
    return f"{formatted}%"
