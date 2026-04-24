"""Pydantic schemas for analytics endpoints.

Holds the unified AI insights contract consumed by the new `/analytics` screen
in both `web_portal` and `mini_app`. Existing analytics schemas
(`AdvertiserAnalyticsResponse`, `OwnerAnalyticsResponse`, `CashflowResponse`,
etc.) continue to live in `src/api/routers/analytics.py` alongside the
endpoints that own them.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

InsightsRole = Literal["advertiser", "owner"]


class InsightsActionItem(BaseModel):
    """One recommended action produced by the AI or rule-based engine."""

    kind: Literal["reallocate", "pause", "scale", "experiment", "optimize", "other"]
    title: str
    description: str
    impact_estimate: str | None = None
    channel_id: int | None = None
    cta_type: Literal["create_campaign", "open_channel", "open_placement", "none"] = "none"


class InsightsForecast(BaseModel):
    """Forecasted metric for the next period."""

    period_days: int
    metric: Literal["earnings", "spend", "reach", "ctr"]
    expected_value: Decimal
    confidence_pct: int = Field(ge=0, le=100)


class InsightsAnomaly(BaseModel):
    """Detected anomaly in user performance."""

    kind: Literal[
        "ctr_drop",
        "ctr_spike",
        "reach_drop",
        "earnings_drop",
        "inactive_channel",
        "other",
    ]
    channel_id: int | None = None
    severity: Literal["low", "medium", "high"]
    description: str


class InsightsChannelFlag(BaseModel):
    """AI-assigned flag for a channel — renders as badge in the deep-dive table."""

    channel_id: int
    flag: Literal["hot", "warn", "idle", "neutral"]
    reason: str


class AIInsightsUnifiedResponse(BaseModel):
    """Unified AI analytics response for the new `/analytics` screen.

    `ai_backend` is `"mistral"` when the narrative came from the LLM and
    `"rules"` when the deterministic fallback produced it (missing API key,
    timeout, invalid JSON, etc). The frontend surfaces this as a small badge.
    """

    role: InsightsRole
    summary: str
    action_items: list[InsightsActionItem] = Field(default_factory=list)
    forecast: InsightsForecast | None = None
    anomalies: list[InsightsAnomaly] = Field(default_factory=list)
    channel_flags: list[InsightsChannelFlag] = Field(default_factory=list)
    ai_backend: Literal["mistral", "rules"]
    generated_at: datetime
    cache_ttl_seconds: int = 900
