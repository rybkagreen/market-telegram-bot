"""
Acceptance tests for Phase 0 — manual Redis INCR+EXPIRE rate-limits on
POST /api/auth/consume-ticket. Two cases per IMPLEMENTATION_PLAN_ACTIVE.md §0.C:

  1. 11th request from one IP within 60s → 429
  2. 6 failed consume-ticket attempts for one user_id within 5min → 429
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_redis
from src.api.main import app
from src.config.settings import settings

# Reuse the in-memory Redis stub from the aud-claim suite.
from tests.unit.api.test_jwt_aud_claim import FakeRedis, _make_user


@pytest_asyncio.fixture
async def stub_session_factory(monkeypatch: pytest.MonkeyPatch) -> Any:
    fake_user = _make_user()

    class _Result:
        def scalar_one_or_none(self) -> Any:
            return fake_user

    class _Session:
        async def execute(self, _stmt: Any) -> Any:
            return _Result()

    @asynccontextmanager
    async def _factory() -> AsyncIterator[_Session]:
        yield _Session()

    monkeypatch.setattr("src.api.dependencies.async_session_factory", _factory)
    return _factory


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture
async def client(
    stub_session_factory: Any,  # noqa: ARG001 (activates the patch)
    fake_redis: FakeRedis,
) -> AsyncIterator[AsyncClient]:
    async def _override_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _forged_ticket(user_id: int = 42) -> str:
    """Valid signature + aud, but its jti is not in Redis — guaranteed
    to land in the user-fail counter path on consume."""
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tg": 100_000 + user_id,
        "plan": "free",
        "jti": f"miss-{user_id:08d}",
        "aud": "web_portal",
        "exp": datetime.now(UTC) + timedelta(seconds=300),
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ─── Case 1: per-IP rate-limit ────────────────────────────────


@pytest.mark.asyncio
async def test_eleventh_consume_from_same_ip_in_one_minute_returns_429(
    client: AsyncClient,
) -> None:
    """10 requests from one IP within the 60s window are accepted (with
    401 — invalid ticket); the 11th hits the IP rate-limit and returns 429
    BEFORE token decoding."""
    headers = {"x-real-ip": "203.0.113.42"}
    junk = "not-a-real-jwt"

    for i in range(10):
        r = await client.post(
            "/api/auth/consume-ticket", json={"ticket": junk}, headers=headers
        )
        assert r.status_code == 401, f"call {i} unexpectedly returned {r.status_code}"

    r11 = await client.post(
        "/api/auth/consume-ticket", json={"ticket": junk}, headers=headers
    )
    assert r11.status_code == 429, r11.text
    assert "too many requests" in r11.json()["detail"].lower()


# ─── Case 2: per-user fail rate-limit ─────────────────────────


@pytest.mark.asyncio
async def test_sixth_failed_consume_for_same_user_in_five_minutes_returns_429(
    client: AsyncClient,
) -> None:
    """5 failed consumes for the same user are recorded; the 6th attempt
    (still within the 5-min window) returns 429 + WARN log."""
    user_id = 7777

    # Spread requests across distinct IPs so the per-IP limit (10/min) does
    # NOT trigger before the user-fail limit (5/5min). Each IP gets ≤1 hit.
    for i in range(5):
        ip = f"198.51.100.{i + 1}"
        r = await client.post(
            "/api/auth/consume-ticket",
            json={"ticket": _forged_ticket(user_id)},
            headers={"x-real-ip": ip},
        )
        # First five should land on "Ticket already consumed" — 401.
        assert r.status_code == 401, f"call {i} unexpectedly returned {r.status_code}"

    r6 = await client.post(
        "/api/auth/consume-ticket",
        json={"ticket": _forged_ticket(user_id)},
        headers={"x-real-ip": "198.51.100.99"},
    )
    assert r6.status_code == 429, r6.text
    assert "too many failed attempts" in r6.json()["detail"].lower()
