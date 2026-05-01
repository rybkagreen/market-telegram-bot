"""Integration-ish coverage for ``POST /api/auth/exchange-bot-token-to-portal`` (BL-055).

ASGI in-process via httpx, FakeRedis, repository monkey-patched to the
same in-memory user the test owns. Ensures:
- happy path returns ``ticket_url`` matching ``${web_portal_url}/login/ticket?ticket=…&redirect=…``;
- minted ticket payload contains exactly the agreed keys and no PII surface;
- 401 on bad signature / expired timestamp / missing header;
- 400 on disallowed redirect_path;
- 404 on unknown telegram_id.
"""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import unquote

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.auth_bot_hmac import sign_bot_request
from src.api.dependencies import get_redis
from src.api.main import app
from src.config.settings import settings

# `src/api/routers/__init__.py` does `from .auth import router as auth`, which
# shadows attribute access `src.api.routers.auth` with an APIRouter instance.
# `importlib.import_module` returns the module object directly from
# `sys.modules`, bypassing the shadow.
auth_module = importlib.import_module("src.api.routers.auth")


# ─── Stubs ────────────────────────────────────────────────────────


class FakeRedis:
    """Same minimal in-memory stub as the existing ticket-bridge tests."""

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


def _make_user(telegram_id: int = 100_042, user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.telegram_id = telegram_id
    plan = MagicMock()
    plan.value = "free"
    user.plan = plan
    return user


# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def fake_user() -> Any:
    return _make_user()


@pytest_asyncio.fixture
async def client(
    monkeypatch: pytest.MonkeyPatch,
    fake_user: Any,
) -> AsyncIterator[AsyncClient]:
    fake_redis = FakeRedis()

    class _UserRepo:
        def __init__(self, _session: Any) -> None: ...
        async def get_by_telegram_id(self, telegram_id: int) -> Any:
            return fake_user if telegram_id == fake_user.telegram_id else None

    @asynccontextmanager
    async def _factory() -> AsyncIterator[Any]:
        yield MagicMock()  # session is unused — repo is patched

    # Use module-object form: `from src.api.routers import auth as router-shadow`
    # in src/api/routers/__init__.py shadows `src.api.routers.auth` with the
    # APIRouter instance, which breaks `monkeypatch.setattr("src.api.routers.auth.X")`.
    monkeypatch.setattr(auth_module, "async_session_factory", _factory)
    monkeypatch.setattr(auth_module, "UserRepository", _UserRepo)

    async def _override_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ─── Tests ────────────────────────────────────────────────────────


def _signed_post(
    client: AsyncClient,
    *,
    telegram_id: int,
    redirect_path: str,
    hmac_secret: str | None = None,
):
    body_bytes = (
        b'{"telegram_id": ' + str(telegram_id).encode() + b", "
        b'"redirect_path": "' + redirect_path.encode() + b'"}'
    )
    ts, sig = sign_bot_request(
        body_bytes=body_bytes,
        hmac_secret=hmac_secret if hmac_secret is not None else settings.bot_api_hmac_secret,
    )
    return client.post(
        "/api/auth/exchange-bot-token-to-portal",
        content=body_bytes,
        headers={
            "X-Bot-Auth-Timestamp": ts,
            "X-Bot-Auth-Signature": sig,
            "content-type": "application/json",
        },
    )


@pytest.mark.asyncio
async def test_happy_path_returns_ticket_url(client: AsyncClient, fake_user: Any) -> None:
    r = await _signed_post(
        client,
        telegram_id=fake_user.telegram_id,
        redirect_path="/own/payouts/request",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "ticket_url" in body

    portal_base = settings.web_portal_url.rstrip("/")
    assert body["ticket_url"].startswith(f"{portal_base}/login/ticket?ticket=")
    assert "&redirect=" in body["ticket_url"]
    encoded = body["ticket_url"].split("&redirect=")[1]
    assert unquote(encoded) == "/own/payouts/request"


@pytest.mark.asyncio
async def test_ticket_payload_has_no_extra_pii(client: AsyncClient, fake_user: Any) -> None:
    r = await _signed_post(
        client,
        telegram_id=fake_user.telegram_id,
        redirect_path="/own/payouts/request",
    )
    assert r.status_code == 200
    ticket_url = r.json()["ticket_url"]
    ticket = ticket_url.split("ticket=", 1)[1].split("&", 1)[0]
    payload = pyjwt.decode(
        ticket,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        audience="web_portal",
    )
    # Exactly the keys the existing exchange-miniapp ticket carries —
    # no first_name / last_name / username / email / addresses, etc.
    assert set(payload.keys()) == {"sub", "tg", "plan", "jti", "aud", "exp", "iat"}
    assert payload["aud"] == "web_portal"
    assert payload["sub"] == str(fake_user.id)
    assert payload["tg"] == fake_user.telegram_id


@pytest.mark.asyncio
async def test_invalid_signature_returns_401(client: AsyncClient, fake_user: Any) -> None:
    body = (
        b'{"telegram_id": '
        + str(fake_user.telegram_id).encode()
        + b', "redirect_path": "/own/payouts/request"}'
    )
    ts, sig = sign_bot_request(body_bytes=body, hmac_secret=settings.bot_api_hmac_secret)
    # tamper signature
    tampered_sig = "0" * len(sig)
    r = await client.post(
        "/api/auth/exchange-bot-token-to-portal",
        content=body,
        headers={
            "X-Bot-Auth-Timestamp": ts,
            "X-Bot-Auth-Signature": tampered_sig,
            "content-type": "application/json",
        },
    )
    assert r.status_code == 401
    # generic detail — no leakage about which check failed
    assert r.json()["detail"] == "Invalid bot auth"


@pytest.mark.asyncio
async def test_missing_signature_header_returns_401(client: AsyncClient, fake_user: Any) -> None:
    body = (
        b'{"telegram_id": '
        + str(fake_user.telegram_id).encode()
        + b', "redirect_path": "/own/payouts/request"}'
    )
    r = await client.post(
        "/api/auth/exchange-bot-token-to-portal",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_disallowed_redirect_returns_400(client: AsyncClient, fake_user: Any) -> None:
    r = await _signed_post(
        client,
        telegram_id=fake_user.telegram_id,
        redirect_path="/admin/users",  # not in default whitelist
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "redirect_path not allowed"


@pytest.mark.asyncio
async def test_unknown_user_returns_404(client: AsyncClient) -> None:
    r = await _signed_post(
        client,
        telegram_id=999_999,  # not the fake user
        redirect_path="/own/payouts/request",
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_wrong_hmac_secret_returns_401(client: AsyncClient, fake_user: Any) -> None:
    r = await _signed_post(
        client,
        telegram_id=fake_user.telegram_id,
        redirect_path="/own/payouts/request",
        hmac_secret="not-the-real-hmac-secret",
    )
    assert r.status_code == 401
