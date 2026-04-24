"""Unit tests for the unified AI-insights service helpers.

Covers the deterministic pieces: rule-based fallback, JSON fence stripping,
payload sanitisation. Mistral wire-up is exercised via the endpoint test
(`tests/unit/api/test_analytics_insights.py`).
"""

from __future__ import annotations

from src.api.schemas.analytics import AIInsightsUnifiedResponse
from src.core.services.analytics_service import (
    _rules_advertiser,
    _rules_owner,
    _sanitize_mistral_payload,
    _strip_json_fence,
)

# ─── _strip_json_fence ─────────────────────────────────────────────


def test_strip_json_fence_plain() -> None:
    assert _strip_json_fence('{"a": 1}') == '{"a": 1}'


def test_strip_json_fence_json_prefix() -> None:
    assert _strip_json_fence('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_json_fence_plain_fence() -> None:
    assert _strip_json_fence('```\n{"a": 1}\n```') == '{"a": 1}'


# ─── _rules_advertiser ─────────────────────────────────────────────


def test_rules_advertiser_zero_state() -> None:
    result = _rules_advertiser({
        "total_placements": 0,
        "completed_placements": 0,
        "total_reach": 0,
        "total_clicks": 0,
        "avg_ctr": 0,
        "total_spent": "0",
        "top_channels": [],
    })
    assert "Кампаний ещё не было" in result["summary"]
    assert len(result["action_items"]) == 1
    assert result["action_items"][0]["cta_type"] == "create_campaign"
    assert result["channel_flags"] == []
    assert result["forecast"] is None


def test_rules_advertiser_with_top_channel() -> None:
    payload = {
        "total_placements": 12,
        "completed_placements": 10,
        "total_reach": 50_000,
        "total_clicks": 1000,
        "avg_ctr": 2.0,
        "total_spent": "6000",
        "top_channels": [
            {"channel_id": 101, "title": "Tech", "username": "tech", "total_reach": 30_000},
            {"channel_id": 102, "title": "Food", "username": "food", "total_reach": 15_000},
            {"channel_id": 103, "title": "News", "username": "news", "total_reach": 5_000},
        ],
    }
    result = _rules_advertiser(payload)
    assert "50000" in result["summary"] or "охват" in result["summary"]
    assert any(ai["cta_type"] == "create_campaign" for ai in result["action_items"])
    assert result["forecast"] is not None
    assert result["forecast"]["metric"] == "reach"
    flags = {f["channel_id"]: f["flag"] for f in result["channel_flags"]}
    assert flags[101] == "hot"
    assert flags[103] == "warn"


def test_rules_advertiser_low_ctr_triggers_optimize() -> None:
    result = _rules_advertiser({
        "total_placements": 10,
        "completed_placements": 8,
        "total_reach": 10_000,
        "total_clicks": 50,
        "avg_ctr": 0.5,
        "total_spent": "5000",
        "top_channels": [{"channel_id": 1, "title": "T", "username": "t", "total_reach": 10_000}],
    })
    kinds = [ai["kind"] for ai in result["action_items"]]
    assert "optimize" in kinds


def test_rules_advertiser_output_passes_schema() -> None:
    """Rule-based output must be a valid AIInsightsUnifiedResponse
    (after the role/ai_backend/generated_at wrapper is added)."""
    result = _rules_advertiser({
        "total_placements": 5,
        "completed_placements": 3,
        "total_reach": 10_000,
        "total_clicks": 100,
        "avg_ctr": 1.0,
        "total_spent": "2000",
        "top_channels": [],
    })
    model = AIInsightsUnifiedResponse.model_validate({
        **result,
        "role": "advertiser",
        "ai_backend": "rules",
        "generated_at": "2026-04-23T22:00:00+00:00",
        "cache_ttl_seconds": 900,
    })
    assert model.ai_backend == "rules"


# ─── _rules_owner ──────────────────────────────────────────────────


def test_rules_owner_no_channels() -> None:
    result = _rules_owner({
        "total_published": 0,
        "total_earned": "0",
        "avg_check": "0",
        "channels": [],
    })
    assert "Каналов ещё нет" in result["summary"]
    assert result["action_items"][0]["cta_type"] == "open_channel"


def test_rules_owner_with_channels() -> None:
    payload = {
        "total_published": 20,
        "total_earned": "12000",
        "avg_check": "600",
        "channels": [
            {
                "channel_id": 1,
                "title": "Top",
                "username": "top",
                "member_count": 10_000,
                "rating": 5.0,
                "publications": 15,
                "earned": "10000",
            },
            {
                "channel_id": 2,
                "title": "Idle",
                "username": "idle",
                "member_count": 3_000,
                "rating": 4.5,
                "publications": 0,
                "earned": "0",
            },
            {
                "channel_id": 3,
                "title": "Mid",
                "username": "mid",
                "member_count": 5_000,
                "rating": 3.5,
                "publications": 5,
                "earned": "2000",
            },
        ],
    }
    result = _rules_owner(payload)
    flags = {f["channel_id"]: f["flag"] for f in result["channel_flags"]}
    assert flags[1] == "hot"
    assert flags[2] == "idle"
    assert flags[3] == "warn"  # rating < 4.0
    assert result["forecast"] is not None
    assert result["forecast"]["metric"] == "earnings"


def test_rules_owner_output_passes_schema() -> None:
    result = _rules_owner({
        "total_published": 3,
        "total_earned": "1500",
        "avg_check": "500",
        "channels": [
            {
                "channel_id": 1,
                "title": "A",
                "username": "a",
                "member_count": 1000,
                "rating": 4.5,
                "publications": 3,
                "earned": "1500",
            }
        ],
    })
    model = AIInsightsUnifiedResponse.model_validate({
        **result,
        "role": "owner",
        "ai_backend": "rules",
        "generated_at": "2026-04-23T22:00:00+00:00",
        "cache_ttl_seconds": 900,
    })
    assert model.role == "owner"


# ─── _sanitize_mistral_payload ─────────────────────────────────────


def test_sanitize_mistral_valid_payload() -> None:
    raw = {
        "summary": "Кратко: всё хорошо.",
        "action_items": [
            {
                "kind": "scale",
                "title": "Больше бюджета",
                "description": "Перелейте часть в топ-канал",
                "impact_estimate": "+12%",
                "channel_id": 42,
                "cta_type": "create_campaign",
            }
        ],
        "forecast": {
            "period_days": 7,
            "metric": "reach",
            "expected_value": 12345,
            "confidence_pct": 70,
        },
        "anomalies": [],
        "channel_flags": [{"channel_id": 42, "flag": "hot", "reason": "Лидер"}],
    }
    sanitized = _sanitize_mistral_payload(raw)
    assert sanitized is not None
    assert sanitized["summary"].startswith("Кратко")
    assert sanitized["forecast"]["metric"] == "reach"
    assert sanitized["channel_flags"][0]["flag"] == "hot"


def test_sanitize_mistral_rejects_non_dict() -> None:
    assert _sanitize_mistral_payload("not a dict") is None
    assert _sanitize_mistral_payload([1, 2, 3]) is None


def test_sanitize_mistral_rejects_missing_summary() -> None:
    raw = {"action_items": [], "summary": "   "}
    assert _sanitize_mistral_payload(raw) is None


def test_sanitize_mistral_coerces_unknown_kind() -> None:
    raw = {
        "summary": "ok",
        "action_items": [
            {
                "kind": "totally-unknown-kind",
                "title": "T",
                "description": "D",
                "cta_type": "weird_cta",
            }
        ],
    }
    out = _sanitize_mistral_payload(raw)
    assert out is not None
    assert out["action_items"][0]["kind"] == "other"
    assert out["action_items"][0]["cta_type"] == "none"


def test_sanitize_mistral_drops_invalid_forecast() -> None:
    raw = {
        "summary": "ok",
        "forecast": {"metric": "banana"},
    }
    out = _sanitize_mistral_payload(raw)
    assert out is not None
    assert out["forecast"] is None
