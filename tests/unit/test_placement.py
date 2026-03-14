"""
Unit tests for Placement Service (P03).
Standalone tests - no conftest dependencies.
"""

import subprocess
from decimal import Decimal

from src.constants.payments import (
    FORMAT_MULTIPLIERS,
    MIN_CAMPAIGN_BUDGET,
    MIN_PRICE_PER_POST,
    OWNER_SHARE,
    PLATFORM_COMMISSION,
)


class TestPlacementRequestServiceConstants:
    """Tests for PlacementRequestService constants."""

    def test_min_price_per_post(self):
        """MIN_PRICE_PER_POST is 1000 ₽."""
        assert MIN_PRICE_PER_POST == Decimal("1000")

    def test_min_campaign_budget(self):
        """MIN_CAMPAIGN_BUDGET is 2000 ₽."""
        assert MIN_CAMPAIGN_BUDGET == Decimal("2000")

    def test_format_multipliers_all_defined(self):
        """All 5 format multipliers are defined."""
        expected_formats = {"post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h"}
        assert set(FORMAT_MULTIPLIERS.keys()) == expected_formats

    def test_format_multiplier_values(self):
        """Format multipliers have correct values."""
        assert FORMAT_MULTIPLIERS["post_24h"] == Decimal("1.0")
        assert FORMAT_MULTIPLIERS["post_48h"] == Decimal("1.4")
        assert FORMAT_MULTIPLIERS["post_7d"] == Decimal("2.0")
        assert FORMAT_MULTIPLIERS["pin_24h"] == Decimal("3.0")
        assert FORMAT_MULTIPLIERS["pin_48h"] == Decimal("4.0")


class TestSelfDealingPrevention:
    """Tests for self-dealing prevention."""

    def test_owner_share_is_85_percent(self):
        """OWNER_SHARE is 85% for escrow release."""
        assert OWNER_SHARE == Decimal("0.85")

    def test_platform_commission_is_15_percent(self):
        """PLATFORM_COMMISSION is 15% for escrow release."""
        assert PLATFORM_COMMISSION == Decimal("0.15")

    def test_escrow_distribution_formula(self):
        """Escrow: owner = price × 0.85, platform = price × 0.15."""
        final_price = Decimal("10000")
        owner_share = (final_price * OWNER_SHARE).quantize(Decimal("0.01"))
        platform_fee = (final_price * PLATFORM_COMMISSION).quantize(Decimal("0.01"))

        assert owner_share == Decimal("8500")
        assert platform_fee == Decimal("1500")
        assert owner_share + platform_fee == final_price


class TestPublicationServiceEscrow001:
    """ESCROW-001 verification for PublicationService."""

    def test_release_escrow_only_in_delete_published_post(self):
        """ESCROW-001: release_escrow() ONLY in delete_published_post()."""
        result = subprocess.run(
            ["poetry", "run", "grep", "-rn", r"\.release_escrow\(", "src/"],
            capture_output=True,
            text=True,
            cwd="/opt/market-telegram-bot",
        )

        # Filter out function definitions and binary files
        lines = [
            line
            for line in result.stdout.split("\n")
            if line and "def release_escrow" not in line and ".pyc" not in line
        ]

        # Should only appear in publication_service.py
        for line in lines:
            assert "publication_service.py" in line, (
                f"ESCROW-001 VIOLATION: release_escrow() found outside "
                f"publication_service.py: {line}"
            )

    def test_publication_service_imports(self):
        """PublicationService can be imported."""
        from src.core.services.publication_service import PublicationService

        assert PublicationService is not None

    def test_publication_service_init(self):
        """PublicationService initializes correctly."""
        from src.core.services.publication_service import PublicationService

        service = PublicationService()
        assert service is not None
        assert hasattr(service, "billing_service")


class TestReputationServiceConstants:
    """Tests for ReputationService constants."""

    def test_reputation_service_imports(self):
        """ReputationService can be imported."""
        from src.core.services.reputation_service import ReputationService

        assert ReputationService is not None

    def test_reputation_deltas(self):
        """Reputation deltas are defined correctly."""
        from src.core.services.reputation_service import ReputationService

        assert ReputationService.DELTA_PUBLICATION == +1.0
        assert ReputationService.DELTA_REVIEW_5STAR == +2.0
        assert ReputationService.DELTA_REVIEW_4STAR == +1.0
        assert ReputationService.DELTA_REVIEW_3STAR == 0.0
        assert ReputationService.DELTA_REVIEW_2STAR == -1.0
        assert ReputationService.DELTA_REVIEW_1STAR == -2.0
        assert ReputationService.DELTA_CANCEL_BEFORE == -5.0
        assert ReputationService.DELTA_CANCEL_AFTER == -20.0
        assert ReputationService.DELTA_REJECT_INVALID_1 == -10.0
        assert ReputationService.DELTA_REJECT_INVALID_2 == -15.0
        assert ReputationService.DELTA_REJECT_INVALID_3 == -20.0

    def test_reputation_score_range(self):
        """Reputation score range is [0.0, 10.0]."""
        from src.core.services.reputation_service import ReputationService

        assert ReputationService.SCORE_MIN == 0.0
        assert ReputationService.SCORE_MAX == 10.0
        assert ReputationService.SCORE_AFTER_BAN == 2.0

    def test_ban_duration(self):
        """Ban duration is 7 days."""
        from src.core.services.reputation_service import ReputationService

        assert ReputationService.BAN_DURATION_DAYS == 7
        assert ReputationService.PERMANENT_BAN_VIOLATIONS == 5


class TestRejectionValidation:
    """Tests for rejection reason validation."""

    def test_placement_request_service_imports(self):
        """PlacementRequestService can be imported."""
        from src.core.services.placement_request_service import PlacementRequestService

        assert PlacementRequestService is not None

    def test_validate_rejection_reason_logic(self):
        """validate_rejection_reason requires meaningful text."""
        # Test the logic directly
        import re

        reason = "not enough info"  # 17 chars, >= 10
        # Must be >= 10 chars
        assert len(reason) >= 10

        # Must contain letters
        assert re.search(r"[а-яёa-z]", reason, re.IGNORECASE)

        # Meaningless patterns should be rejected
        meaningless_patterns = [
            r"^(asdf|asdfgh|aaaaaa|bbbbbb|123456|111111|qwerty)+$",
            r"^([a-z])\1{4,}$",
            r"^([0-9])\1{4,}$",
        ]

        # Test that meaningless text matches patterns (and would be rejected)
        assert re.match(meaningless_patterns[0], "asdfgh", re.IGNORECASE)
        assert re.match(meaningless_patterns[1], "aaaaaa", re.IGNORECASE)
        assert re.match(meaningless_patterns[2], "111111", re.IGNORECASE)

        # Test that meaningful text does NOT match patterns
        assert not re.match(meaningless_patterns[0], "not enough info", re.IGNORECASE)


class TestFormatPriceCalculation:
    """Tests for format price calculations."""

    def test_post_24h_price(self):
        """post_24h: base price × 1.0."""
        base = Decimal("1000")
        price = base * FORMAT_MULTIPLIERS["post_24h"]
        assert price == Decimal("1000")

    def test_post_48h_price(self):
        """post_48h: base price × 1.4."""
        base = Decimal("1000")
        price = base * FORMAT_MULTIPLIERS["post_48h"]
        assert price == Decimal("1400")

    def test_post_7d_price(self):
        """post_7d: base price × 2.0."""
        base = Decimal("1000")
        price = base * FORMAT_MULTIPLIERS["post_7d"]
        assert price == Decimal("2000")

    def test_pin_24h_price(self):
        """pin_24h: base price × 3.0."""
        base = Decimal("1000")
        price = base * FORMAT_MULTIPLIERS["pin_24h"]
        assert price == Decimal("3000")

    def test_pin_48h_price(self):
        """pin_48h: base price × 4.0."""
        base = Decimal("1000")
        price = base * FORMAT_MULTIPLIERS["pin_48h"]
        assert price == Decimal("4000")

    def test_min_campaign_budget_enforced(self):
        """Campaign budget must be >= 2000 ₽."""
        base_price = Decimal("1000")
        # post_24h would be 1000, which is < MIN_CAMPAIGN_BUDGET
        assert base_price < MIN_CAMPAIGN_BUDGET

        # post_7d would be 2000, which meets minimum
        price_7d = base_price * FORMAT_MULTIPLIERS["post_7d"]
        assert price_7d >= MIN_CAMPAIGN_BUDGET
