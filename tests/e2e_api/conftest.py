"""
E2E API contract tests — run **inside** docker-compose.test.yml against the
real nginx-test → api-test stack. Shares seed data with the Playwright suite.

Unlike tests/conftest.py (which uses ASGITransport for in-process unit tests),
this config assumes a live HTTP server. Execution of these tests against the
host api / prod is meaningless — they always talk to BASE_URL (set by the
compose service to http://nginx-test).

All fixtures are test-scoped and cheap; no DB setup/teardown happens here —
seed-test already produced the deterministic fixture set.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

# Seeded telegram_ids — must match scripts/e2e/seed_e2e.py
ROLE_IDS: dict[str, int] = {
    "advertiser": 9001,
    "owner": 9002,
    "admin": 9003,
}

# Default to Docker service name; a developer running pytest locally can
# override e.g. `BASE_URL=http://127.0.0.1:8081` after `make test-e2e-up`.
BASE_URL = os.environ.get("BASE_URL", "http://nginx-test")


async def _login_and_client(role: str, *, source: str = "web_portal") -> httpx.AsyncClient:
    """Call /api/auth/e2e-login to get a JWT, build an authenticated client.

    `source` selects the JWT `aud` claim. web_portal is the safe default
    because (a) all `get_current_user_from_web_portal` /
    `get_current_admin_user` endpoints reject mini_app aud, and (b) the
    generic `get_current_user` dep accepts both. The only mini_app-only
    endpoint is `/api/auth/exchange-miniapp-to-portal`, which no pytest
    fixture-based test hits (see auth_e2e.py:26 default and the
    `get_current_user_from_mini_app` audit in src/api/dependencies.py:178).
    """
    telegram_id = ROLE_IDS[role]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as bootstrap:
        resp = await bootstrap.post(
            "/api/auth/e2e-login",
            json={"telegram_id": telegram_id, "source": source},
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]

    client = httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=10.0,
        headers={"Authorization": f"Bearer {token}"},
    )
    return client


@pytest_asyncio.fixture
async def anonymous_client() -> AsyncIterator[httpx.AsyncClient]:
    """Unauthenticated client — asserts 401 on protected endpoints."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest_asyncio.fixture
async def advertiser_client() -> AsyncIterator[httpx.AsyncClient]:
    client = await _login_and_client("advertiser")
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def owner_client() -> AsyncIterator[httpx.AsyncClient]:
    client = await _login_and_client("owner")
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def admin_client() -> AsyncIterator[httpx.AsyncClient]:
    client = await _login_and_client("admin")
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def base_url() -> str:
    return BASE_URL
