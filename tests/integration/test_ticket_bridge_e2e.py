"""
PF.3 — Phase 0 follow-up: end-to-end ticket-bridge happy path.

Phase 0 acceptance suite (`tests/unit/api/test_jwt_aud_claim.py` case 5)
verifies that the bridge endpoints return the expected response shape, but
does NOT verify that the resulting `access_token` is actually accepted by
`get_current_user` (the real auth dependency that web_portal-protected
endpoints use). This file closes that loop.

Flow under test:
  1. Mint a valid `aud="mini_app"` JWT for a fake user.
  2. POST /api/auth/exchange-miniapp-to-portal → 200 + ticket.
  3. POST /api/auth/consume-ticket → 200 + access_token (`aud="web_portal"`).
  4. Feed access_token back into `get_current_user` → returns the same user.

Step 4 is the gap relative to case 5. Together with cases 1/2 (which prove
that mini_app/web_portal JWTs are accepted by `get_current_user`), it
establishes the bridge produces a token usable by every endpoint
that depends on `get_current_user` — i.e. the entire authenticated API
surface.

Stand: ASGI in-process via httpx. Redis is stubbed (`FakeRedis`) so the
test runs without docker. Matches the unit-test fixtures intentionally —
the value-add over case 5 is step 4, not infrastructure.

NOTE: `tests/integration/conftest.py` defines testcontainers-backed
`db_session` fixture, but this test does not depend on it; only the
session-scoped `postgres_container` would fire if anything in this file
referenced `db_session` or `_schema_ready`. Nothing here does.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient

from src.api.auth_utils import create_jwt_token
from src.api.dependencies import get_current_user, get_redis
from src.api.main import app
from src.config.settings import settings


# ─── Minimal in-memory stubs ───────────────────────────────────────


class FakeRedis:
    """Covers only the Redis surface that `auth.py` exercises."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._ttl: dict[str, float] = {}

    async def setex(self, key: str, ttl: int, value: str | bytes) -> None:
        if isinstance(value, str):
            value = value.encode()
        self._store[key] = value
        self._ttl[key] = datetime.now(UTC).timestamp() + ttl

    async def incr(self, key: str) -> int:
        cur = int(self._store.get(key, b"0") or b"0") + 1
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


def _make_user(user_id: int = 4242) -> Any:
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


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def fake_user() -> Any:
    return _make_user()


@pytest_asyncio.fixture
async def stub_session_factory(monkeypatch: pytest.MonkeyPatch, fake_user: Any) -> Any:
    """Patch `async_session_factory` in dependencies.py to yield a session
    whose `execute(...)` returns `fake_user` for every query."""

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
    stub_session_factory: Any,  # noqa: ARG001 — activated for side-effect
    fake_redis: FakeRedis,
) -> AsyncIterator[AsyncClient]:
    """ASGI client with stubbed Redis dep."""

    async def _override_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ─── The test ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bridge_happy_path_token_authenticates(
    client: AsyncClient,
    stub_session_factory: Any,  # noqa: ARG001 — needed for step 4 dep call
    fake_user: Any,
) -> None:
    """4-step bridge happy path with end-to-end auth verification.

    Closes the gap left by `test_jwt_aud_claim.py::test_case5_*`:
    case 5 stops at "consume returns AuthTokenResponse"; here we feed the
    token back into the auth dependency and assert it resolves the same user.
    """
    # Step 1: mini_app JWT
    mini_token = create_jwt_token(
        fake_user.id, fake_user.telegram_id, "free", source="mini_app"
    )

    # Step 2: exchange → ticket
    r1 = await client.post(
        "/api/auth/exchange-miniapp-to-portal",
        headers={"Authorization": f"Bearer {mini_token}"},
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["ticket"]
    assert body1["portal_url"] == settings.web_portal_url
    assert body1["expires_in"] == settings.ticket_jwt_ttl_seconds

    # Step 3: consume → web_portal access_token
    r2 = await client.post("/api/auth/consume-ticket", json={"ticket": body1["ticket"]})
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["source"] == "web_portal"
    assert body2["token_type"] == "bearer"
    access_token = body2["access_token"]
    assert access_token

    # Step 4: token must authenticate against `get_current_user`
    request = MagicMock()
    request.state = type("S", (), {})()
    user = await get_current_user(request, _bearer(access_token))
    assert user.id == fake_user.id
    # Phase 1 §1.B.0b: dep wrote identity to request.state for AuditMiddleware
    assert request.state.user_id == fake_user.id
    assert request.state.user_aud == "web_portal"
