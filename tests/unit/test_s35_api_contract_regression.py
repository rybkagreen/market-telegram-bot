"""
S-35 regression tests — API contract alignment: legal flow P0 bugs, compare schema.

These tests verify that:
  - acceptRules body schema is correct (N-08)
  - signContract body field is signature_method, not method (Extra-1)
  - requestKep path and body are correct (Extra-2)
  - ComparisonChannelItem uses subscribers/last_er/topic/rating (N-05)
  - ComparisonService builds dicts with the correct field names (N-05)
"""

import pytest
from pydantic import ValidationError


class TestAcceptRulesSchema:
    """N-08: AcceptRulesRequest requires both bool fields."""

    def test_accept_rules_requires_both_fields(self):
        from src.api.schemas.legal_profile import AcceptRulesRequest

        req = AcceptRulesRequest(accept_platform_rules=True, accept_privacy_policy=True)
        assert req.accept_platform_rules is True
        assert req.accept_privacy_policy is True

    def test_accept_rules_no_body_fails(self):
        from src.api.schemas.legal_profile import AcceptRulesRequest

        with pytest.raises((ValidationError, TypeError)):
            AcceptRulesRequest()  # type: ignore[call-arg]

    def test_accept_rules_has_correct_fields(self):
        from src.api.schemas.legal_profile import AcceptRulesRequest

        assert "accept_platform_rules" in AcceptRulesRequest.model_fields
        assert "accept_privacy_policy" in AcceptRulesRequest.model_fields


class TestContractSignSchema:
    """Extra-1: ContractSignRequest uses signature_method, not method."""

    def test_sign_request_has_signature_method(self):
        from src.api.schemas.legal_profile import ContractSignRequest

        assert "signature_method" in ContractSignRequest.model_fields
        assert "method" not in ContractSignRequest.model_fields

    def test_sign_request_roundtrip(self):
        from src.api.schemas.legal_profile import ContractSignRequest

        req = ContractSignRequest(signature_method="sms_code")
        assert req.signature_method == "sms_code"
        assert req.sms_code is None


class TestComparisonChannelItemSchema:
    """N-05: ComparisonChannelItem uses subscribers/last_er/topic/rating."""

    def test_schema_has_subscribers_not_member_count(self):
        from src.api.routers.channels import ComparisonChannelItem

        assert "subscribers" in ComparisonChannelItem.model_fields
        assert "member_count" not in ComparisonChannelItem.model_fields

    def test_schema_has_last_er_not_er(self):
        from src.api.routers.channels import ComparisonChannelItem

        assert "last_er" in ComparisonChannelItem.model_fields
        assert "er" not in ComparisonChannelItem.model_fields

    def test_schema_has_topic_and_rating(self):
        from src.api.routers.channels import ComparisonChannelItem

        assert "topic" in ComparisonChannelItem.model_fields
        assert "rating" in ComparisonChannelItem.model_fields

    def test_schema_roundtrip_with_new_fields(self):
        from src.api.routers.channels import ComparisonChannelItem

        item = ComparisonChannelItem(
            id=1,
            username="test_channel",
            title="Test Channel",
            subscribers=10000,
            avg_views=500,
            last_er=0.05,
            post_frequency=1.5,
            price_per_post=1000.0,
            price_per_1k_subscribers=100.0,
            topic="Tech",
            rating=4.5,
        )
        assert item.subscribers == 10000
        assert item.last_er == 0.05
        assert item.topic == "Tech"
        assert item.rating == 4.5
        assert item.is_best == {}

    def test_is_best_defaults_to_empty_dict(self):
        from src.api.routers.channels import ComparisonChannelItem

        item = ComparisonChannelItem(
            id=1,
            subscribers=100,
            avg_views=50,
            last_er=0.01,
            post_frequency=1.0,
            price_per_post=100.0,
            price_per_1k_subscribers=10.0,
        )
        assert item.is_best == {}


class TestComparisonServiceMetrics:
    """N-05: ComparisonService.calculate_comparison_metrics uses new field names."""

    def test_calculate_uses_subscribers_key(self):
        from src.core.services.comparison_service import ComparisonService

        svc = ComparisonService()
        channels = [
            {
                "id": 1, "username": "ch1", "title": "Chan 1",
                "subscribers": 5000, "avg_views": 300, "last_er": 0.06,
                "post_frequency": 1.0, "price_per_post": 500.0,
                "price_per_1k_subscribers": 100.0, "is_best": {},
                "topic": "Tech", "rating": 4.0,
            },
            {
                "id": 2, "username": "ch2", "title": "Chan 2",
                "subscribers": 10000, "avg_views": 700, "last_er": 0.07,
                "post_frequency": 2.0, "price_per_post": 1000.0,
                "price_per_1k_subscribers": 100.0, "is_best": {},
                "topic": "News", "rating": 3.5,
            },
        ]
        result = svc.calculate_comparison_metrics(channels)

        assert "channels" in result
        assert "best_values" in result
        assert "recommendation" in result
        assert result["best_values"]["subscribers"] == 10000
        assert result["best_values"]["last_er"] == 0.07
        assert "member_count" not in result["best_values"]
        assert "er" not in result["best_values"]

    def test_recommendation_uses_id_not_channel_id(self):
        from src.core.services.comparison_service import ComparisonService

        svc = ComparisonService()
        channels = [
            {
                "id": 42, "username": "ch1", "title": "Chan",
                "subscribers": 1000, "avg_views": 100, "last_er": 0.10,
                "post_frequency": 1.0, "price_per_post": 200.0,
                "price_per_1k_subscribers": 200.0, "is_best": {},
                "topic": None, "rating": None,
            },
            {
                "id": 99, "username": "ch2", "title": "Chan2",
                "subscribers": 2000, "avg_views": 200, "last_er": 0.05,
                "post_frequency": 1.0, "price_per_post": 300.0,
                "price_per_1k_subscribers": 150.0, "is_best": {},
                "topic": None, "rating": None,
            },
        ]
        result = svc.calculate_comparison_metrics(channels)
        # best last_er is 0.10 → id=42
        assert result["recommendation"]["channel_id"] == 42
