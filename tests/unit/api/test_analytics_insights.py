"""Unit tests for GET /api/analytics/ai-insights.

The service layer (Mistral + Redis + rule-based fallback) is covered in
``tests/unit/services/test_analytics_insights_service.py``. These tests
exercise the HTTP contract: routing, query-param validation, response shape,
and fallthrough into the rule-based branch when Mistral is not configured.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_current_user, get_db_session
from src.api.main import app
from src.db.models.user import User


@pytest.fixture
def advertiser_user() -> User:
    return User(
        id=9001,
        telegram_id=333_333_333,
        username="adv_ai",
        first_name="Adv",
        is_active=True,
    )


async def _stub_session_dep() -> AsyncGenerator[Any]:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    yield session


@pytest_asyncio.fixture
async def client_as_advertiser(advertiser_user: User) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_db_session] = _stub_session_dep

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


_SAMPLE_RULES_PAYLOAD: dict[str, Any] = {
    "role": "advertiser",
    "summary": "Всё стабильно: 10 кампаний, CTR 2%.",
    "action_items": [
        {
            "kind": "scale",
            "title": "Увеличьте бюджет в топ-канале",
            "description": "Канал «Tech» показал лучший CTR.",
            "impact_estimate": "+15% охвата",
            "channel_id": 101,
            "cta_type": "create_campaign",
        }
    ],
    "forecast": {
        "period_days": 7,
        "metric": "reach",
        "expected_value": "8000",
        "confidence_pct": 55,
    },
    "anomalies": [],
    "channel_flags": [{"channel_id": 101, "flag": "hot", "reason": "Лидер по охвату"}],
    "ai_backend": "rules",
    "generated_at": datetime.now(UTC).isoformat(),
    "cache_ttl_seconds": 900,
}


async def test_ai_insights_default_role_advertiser(client_as_advertiser: AsyncClient) -> None:
    with patch(
        "src.core.services.analytics_service.AnalyticsService.generate_unified_insights",
        new=AsyncMock(return_value=_SAMPLE_RULES_PAYLOAD),
    ) as mock_method:
        response = await client_as_advertiser.get("/api/analytics/ai-insights")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "advertiser"
    assert body["ai_backend"] == "rules"
    assert len(body["action_items"]) == 1
    assert body["action_items"][0]["cta_type"] == "create_campaign"
    assert body["forecast"]["metric"] == "reach"
    mock_method.assert_called_once()
    kwargs = mock_method.call_args.kwargs
    assert kwargs["role"] == "advertiser"
    assert kwargs["force_refresh"] is False


async def test_ai_insights_role_owner(client_as_advertiser: AsyncClient) -> None:
    owner_payload = {
        **_SAMPLE_RULES_PAYLOAD,
        "role": "owner",
        "summary": "5 каналов, 20 публикаций.",
    }
    with patch(
        "src.core.services.analytics_service.AnalyticsService.generate_unified_insights",
        new=AsyncMock(return_value=owner_payload),
    ):
        response = await client_as_advertiser.get("/api/analytics/ai-insights?role=owner")

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "owner"


async def test_ai_insights_invalid_role_rejected(client_as_advertiser: AsyncClient) -> None:
    response = await client_as_advertiser.get("/api/analytics/ai-insights?role=banana")
    assert response.status_code == 422


async def test_ai_insights_nocache_forwarded(client_as_advertiser: AsyncClient) -> None:
    with patch(
        "src.core.services.analytics_service.AnalyticsService.generate_unified_insights",
        new=AsyncMock(return_value=_SAMPLE_RULES_PAYLOAD),
    ) as mock_method:
        response = await client_as_advertiser.get("/api/analytics/ai-insights?nocache=true")

    assert response.status_code == 200
    kwargs = mock_method.call_args.kwargs
    assert kwargs["force_refresh"] is True


async def test_ai_insights_rules_backend_badge_preserved(client_as_advertiser: AsyncClient) -> None:
    """When service falls back to rules the router must surface ai_backend=rules."""
    with patch(
        "src.core.services.analytics_service.AnalyticsService.generate_unified_insights",
        new=AsyncMock(return_value=_SAMPLE_RULES_PAYLOAD),
    ):
        response = await client_as_advertiser.get("/api/analytics/ai-insights")

    assert response.status_code == 200
    assert response.json()["ai_backend"] == "rules"
