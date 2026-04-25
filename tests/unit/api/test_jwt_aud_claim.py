"""
Acceptance tests for Phase 0 (env-constants-jwt-aud) — JWT `aud` claim
enforcement and the mini_app → web_portal ticket bridge.

Eight cases mandated by IMPLEMENTATION_PLAN_ACTIVE.md §0.C:

  1. mini_app JWT (aud="mini_app") in get_current_user → 200
  2. web_portal JWT (aud="web_portal") in get_current_user → 200
  3. legacy JWT without aud in get_current_user → 401
  4. mini_app JWT in get_current_user_from_web_portal → 403
  5. Full ticket flow: exchange → consume → web_portal token works → 200 each
  6. Expired ticket consumed → 401
  7. Replay: consume same ticket twice → 1st 200, 2nd 401
  8. Tampered: valid JWT with right aud but jti not in Redis → 401
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient

from src.api.auth_utils import create_jwt_token
from src.api.dependencies import (
    get_current_user,
    get_current_user_from_mini_app,
    get_current_user_from_web_portal,
    get_redis,
)
from src.api.main import app
from src.config.settings import settings

# ─── Fixtures ───────────────────────────────────────────────────


class FakeRedis:
    """Minimal in-memory Redis stub covering only what auth.py uses."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._ttl: dict[str, float] = {}

    async def setex(self, key: str, ttl: int, value: str | bytes) -> None:
        if isinstance(value, str):
            value = value.encode()
        self._store[key] = value
        self._ttl[key] = datetime.now(UTC).timestamp() + ttl

    async def incr(self, key: str) -> int:
        cur = int(self._store.get(key, b"0") or b"0")
        cur += 1
        self._store[key] = str(cur).encode()
        return cur

    async def expire(self, key: str, ttl: int) -> None:
        self._ttl[key] = datetime.now(UTC).timestamp() + ttl

    async def get(self, key: str) -> bytes | None:
        if key not in self._store:
            return None
        if self._ttl.get(key, float("inf")) < datetime.now(UTC).timestamp():
            self._store.pop(key, None)
            return None
        return self._store[key]

    async def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._store:
                self._store.pop(k, None)
                self._ttl.pop(k, None)
                n += 1
        return n


def _make_user(user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.telegram_id = 100_000 + user_id
    user.is_active = True
    user.is_admin = False
    plan = MagicMock()
    plan.value = "free"
    user.plan = plan
    user.legal_profile = None
    return user


@pytest.fixture
def fake_user() -> Any:
    return _make_user()


@pytest_asyncio.fixture
async def stub_session_factory(monkeypatch: pytest.MonkeyPatch, fake_user: Any) -> Any:
    """Patch `async_session_factory` inside dependencies.py to yield a session
    whose `execute(...)` returns our fake user."""

    class _Result:
        def __init__(self, user: Any) -> None:
            self._user = user

        def scalar_one_or_none(self) -> Any:
            return self._user

    class _Session:
        def __init__(self, user: Any) -> None:
            self._user = user

        async def execute(self, _stmt: Any) -> Any:
            return _Result(self._user)

    @asynccontextmanager
    async def _factory() -> AsyncIterator[_Session]:
        yield _Session(fake_user)

    monkeypatch.setattr("src.api.dependencies.async_session_factory", _factory)
    return _factory


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture
async def client(
    stub_session_factory: Any,  # noqa: ARG001 (fixture activated for side-effect)
    fake_redis: FakeRedis,
    fake_user: Any,
) -> AsyncIterator[AsyncClient]:
    """ASGI test client with stubbed Redis dep and DB-via-monkeypatch."""

    async def _override_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ─── Helpers ────────────────────────────────────────────────────


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _req() -> Any:
    """Lightweight Request stub with a fresh `state` namespace.

    The auth dep writes `user_id` / `user_aud` to `request.state` (Phase 1
    §1.B.0b, PF.4). Using a real namespace object instead of MagicMock so
    `request.state.user_id` materialises as a real attribute (MagicMock
    auto-creates attrs on access, which masks bugs where state writes don't
    happen).
    """
    request = MagicMock()
    request.state = type("S", (), {})()
    return request


def _legacy_token_without_aud(user_id: int = 42) -> str:
    """Simulate a token issued before Phase 0 — no `aud` claim."""
    payload = {
        "sub": str(user_id),
        "tg": 100_000 + user_id,
        "plan": "free",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ─── Cases 1-4: aud enforcement on dependencies ────────────────


@pytest.mark.asyncio
async def test_case1_mini_app_jwt_accepted_by_get_current_user(
    stub_session_factory: Any,  # noqa: ARG001
    fake_user: Any,
) -> None:
    """Case 1: mini_app JWT in get_current_user → returns user."""
    token = create_jwt_token(fake_user.id, fake_user.telegram_id, "free", source="mini_app")
    user = await get_current_user(_req(), _bearer(token))
    assert user.id == fake_user.id


@pytest.mark.asyncio
async def test_case2_web_portal_jwt_accepted_by_get_current_user(
    stub_session_factory: Any,  # noqa: ARG001
    fake_user: Any,
) -> None:
    """Case 2: web_portal JWT in get_current_user → returns user."""
    token = create_jwt_token(fake_user.id, fake_user.telegram_id, "free", source="web_portal")
    user = await get_current_user(_req(), _bearer(token))
    assert user.id == fake_user.id


@pytest.mark.asyncio
async def test_case3_legacy_jwt_without_aud_rejected_with_426() -> None:
    """Case 3: legacy aud-less JWT → 426 Upgrade Required + WWW-Authenticate.

    Phase 1 §1.B.0a (PF.2 decision): the aud-less branch ships 426 instead of
    401. Semantically the token is cryptographically valid; only the claim
    format is obsolete. RFC 7231 §6.5.15 426 communicates that precisely.
    """
    token = _legacy_token_without_aud()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_req(), _bearer(token))
    assert exc.value.status_code == 426
    assert "audience" in exc.value.detail.lower()
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_case4_mini_app_jwt_rejected_by_web_portal_dep_with_403(
    stub_session_factory: Any,  # noqa: ARG001
    fake_user: Any,
) -> None:
    """Case 4: mini_app JWT in get_current_user_from_web_portal → 403."""
    token = create_jwt_token(fake_user.id, fake_user.telegram_id, "free", source="mini_app")
    with pytest.raises(HTTPException) as exc:
        await get_current_user_from_web_portal(_req(), _bearer(token))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_web_portal_jwt_rejected_by_mini_app_dep_with_403(
    stub_session_factory: Any,  # noqa: ARG001
    fake_user: Any,
) -> None:
    """Symmetric guard: web_portal JWT in get_current_user_from_mini_app → 403."""
    token = create_jwt_token(fake_user.id, fake_user.telegram_id, "free", source="web_portal")
    with pytest.raises(HTTPException) as exc:
        await get_current_user_from_mini_app(_req(), _bearer(token))
    assert exc.value.status_code == 403


# ─── Phase 1 §1.B.0b: request.state contract (PF.4) ────────────


@pytest.mark.asyncio
async def test_resolve_writes_user_id_and_aud_to_request_state_mini_app(
    stub_session_factory: Any,  # noqa: ARG001
    fake_user: Any,
) -> None:
    """Phase 1 §1.B.0b: dep writes request.state.user_id + user_aud (PF.4).

    `AuditMiddleware` reads these fields without re-decoding the JWT.
    Contract: after a successful auth, both are populated. mini_app token →
    user_aud == "mini_app".
    """
    token = create_jwt_token(fake_user.id, fake_user.telegram_id, "free", source="mini_app")
    request = _req()
    user = await get_current_user(request, _bearer(token))
    assert user.id == fake_user.id
    assert request.state.user_id == fake_user.id
    assert request.state.user_aud == "mini_app"


@pytest.mark.asyncio
async def test_resolve_writes_user_aud_web_portal(
    stub_session_factory: Any,  # noqa: ARG001
    fake_user: Any,
) -> None:
    """web_portal token → user_aud == "web_portal" on request.state."""
    token = create_jwt_token(fake_user.id, fake_user.telegram_id, "free", source="web_portal")
    request = _req()
    user = await get_current_user_from_web_portal(request, _bearer(token))
    assert user.id == fake_user.id
    assert request.state.user_aud == "web_portal"


# ─── Cases 5-8: ticket bridge ──────────────────────────────────


@pytest.mark.asyncio
async def test_case5_full_ticket_flow_returns_web_portal_token(
    client: AsyncClient,
    fake_user: Any,
) -> None:
    """Case 5: exchange → consume → AuthTokenResponse with source=web_portal."""
    mini_token = create_jwt_token(
        fake_user.id, fake_user.telegram_id, "free", source="mini_app"
    )
    r1 = await client.post(
        "/api/auth/exchange-miniapp-to-portal",
        headers={"Authorization": f"Bearer {mini_token}"},
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert "ticket" in body1
    assert body1["portal_url"] == settings.web_portal_url
    assert body1["expires_in"] == settings.ticket_jwt_ttl_seconds

    r2 = await client.post("/api/auth/consume-ticket", json={"ticket": body1["ticket"]})
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["source"] == "web_portal"
    assert body2["token_type"] == "bearer"
    assert body2["access_token"]


@pytest.mark.asyncio
async def test_case6_expired_ticket_consumed_returns_401(
    client: AsyncClient,
    fake_redis: FakeRedis,
    fake_user: Any,
) -> None:
    """Case 6: ticket past its `exp` → 401 (regardless of jti presence)."""
    expired_payload = {
        "sub": str(fake_user.id),
        "tg": fake_user.telegram_id,
        "plan": "free",
        "jti": "deadbeef-dead-beef-dead-beefdeadbeef",
        "aud": "web_portal",
        "exp": datetime.now(UTC) - timedelta(seconds=10),
        "iat": datetime.now(UTC) - timedelta(seconds=600),
    }
    expired = pyjwt.encode(
        expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    # Even if jti is present in Redis, expired token must be rejected first.
    await fake_redis.setex(
        f"auth:ticket:jti:{expired_payload['jti']}",
        300,
        json.dumps({"user_id": fake_user.id, "issued_at": "x", "ip": "x"}),
    )
    r = await client.post("/api/auth/consume-ticket", json={"ticket": expired})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_case7_replay_consume_same_ticket_twice_first_ok_second_401(
    client: AsyncClient,
    fake_user: Any,
) -> None:
    """Case 7: 1st consume → 200, 2nd consume of same ticket → 401."""
    mini_token = create_jwt_token(
        fake_user.id, fake_user.telegram_id, "free", source="mini_app"
    )
    r_exchange = await client.post(
        "/api/auth/exchange-miniapp-to-portal",
        headers={"Authorization": f"Bearer {mini_token}"},
    )
    ticket = r_exchange.json()["ticket"]

    r_first = await client.post("/api/auth/consume-ticket", json={"ticket": ticket})
    assert r_first.status_code == 200, r_first.text

    r_second = await client.post("/api/auth/consume-ticket", json={"ticket": ticket})
    assert r_second.status_code == 401
    assert "consumed" in r_second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_case8_tampered_ticket_with_valid_aud_but_missing_jti_returns_401(
    client: AsyncClient,
    fake_user: Any,
) -> None:
    """Case 8: ticket has correct signature/aud but jti is not in Redis →
    401 (replay-after-flush or hand-crafted token without exchange)."""
    forged_payload = {
        "sub": str(fake_user.id),
        "tg": fake_user.telegram_id,
        "plan": "free",
        "jti": "forged00-0000-0000-0000-000000000000",
        "aud": "web_portal",
        "exp": datetime.now(UTC) + timedelta(seconds=300),
        "iat": datetime.now(UTC),
    }
    forged = pyjwt.encode(forged_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    r = await client.post("/api/auth/consume-ticket", json={"ticket": forged})
    assert r.status_code == 401
    assert "consumed" in r.json()["detail"].lower()
