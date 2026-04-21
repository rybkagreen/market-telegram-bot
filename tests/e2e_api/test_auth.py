"""Auth / session contract tests."""

from __future__ import annotations

import httpx
import pytest


pytestmark = pytest.mark.asyncio


async def test_me_without_token_returns_401(anonymous_client: httpx.AsyncClient) -> None:
    resp = await anonymous_client.get("/api/auth/me")
    assert resp.status_code == 401, resp.text


async def test_me_with_token_returns_current_user(
    advertiser_client: httpx.AsyncClient,
) -> None:
    resp = await advertiser_client.get("/api/auth/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Fields that every TS consumer relies on — never drop without a
    # coordinated frontend change.
    for required in ("id", "telegram_id", "first_name", "plan", "balance_rub"):
        assert required in body, f"missing {required!r} in /auth/me response"
    assert body["telegram_id"] == 9001


async def test_e2e_login_returns_same_user_for_same_telegram_id(
    anonymous_client: httpx.AsyncClient,
) -> None:
    r1 = await anonymous_client.post(
        "/api/auth/e2e-login", json={"telegram_id": 9001}
    )
    r2 = await anonymous_client.post(
        "/api/auth/e2e-login", json={"telegram_id": 9001}
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    # User id must be stable (seed produced one row per telegram_id).
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]


async def test_e2e_login_unknown_telegram_id_returns_404(
    anonymous_client: httpx.AsyncClient,
) -> None:
    resp = await anonymous_client.post(
        "/api/auth/e2e-login", json={"telegram_id": 999_999}
    )
    # Test-only endpoint returns 404 instead of silently creating a user.
    assert resp.status_code == 404, resp.text


async def test_admin_flag_present_on_admin_account(
    admin_client: httpx.AsyncClient,
) -> None:
    resp = await admin_client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    # Matches seed: tg=9003 is_admin=True
    assert body.get("is_admin") is True, f"expected admin flag, got: {body}"


async def test_advertiser_is_not_admin(advertiser_client: httpx.AsyncClient) -> None:
    resp = await advertiser_client.get("/api/auth/me")
    assert resp.status_code == 200
    # A leaky admin flag on non-admin accounts is a privilege-escalation risk.
    assert resp.json().get("is_admin") in (False, None)
