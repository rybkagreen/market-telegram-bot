"""
Role / auth boundary sweep across the router surface.

For each router we pick a single representative GET path and verify:
  1. unauthenticated → 401 (or 403 — both treated as "rejected")
  2. authenticated advertiser → 200 (or a documented 403/404 for
     non-owner/non-admin paths)

This is a coarse net: it doesn't exhaustively test every endpoint, but it
pins the contract that (a) auth middleware is wired on every router, and
(b) nothing returns 500 for an ordinary GET with a logged-in user.
"""

from __future__ import annotations

import httpx
import pytest


pytestmark = pytest.mark.asyncio


# ─── Paths open to unauthenticated users (intentionally public) ───────
# Pricing page, category dropdown on login, public referral stats, etc.
# These are documented open endpoints; inclusion here pins the contract
# (so accidentally gating them with auth fails the test loudly).
PUBLIC_GETS: list[str] = [
    "/api/billing/plans",
    "/api/categories/",
]


# ─── Paths that any authenticated user may GET (200 expected) ───────
COMMON_AUTHENTICATED_GETS: list[str] = [
    "/api/auth/me",
    "/api/users/me",
    "/api/billing/balance",
    "/api/billing/history",
    "/api/billing/frozen",
    "/api/placements/",
    "/api/channels/",
    "/api/channels/recommended",
    "/api/disputes/",
    "/api/reputation/me",
    "/api/acts/mine",
    "/api/legal-profile/me",
    "/api/analytics/summary",
    "/api/analytics/activity",
    "/api/analytics/cashflow",
]


# ─── Paths that require admin (403 for non-admin) ───────────────────
# Admin router is mounted with prefix="/api" and its APIRouter uses
# prefix="/admin", so every admin path is `/api/admin/…`. Collisions with
# user-scoped routers are avoided by this namespacing — we test here that
# the namespacing is actually enforced.
ADMIN_ONLY_GETS: list[str] = [
    "/api/admin/stats",
    "/api/admin/users",
    "/api/admin/audit-logs",
    "/api/admin/platform-settings",
    "/api/admin/contracts",
    "/api/admin/payouts",
    "/api/admin/tax/summary",
    "/api/admin/disputes",
    "/api/admin/legal-profiles",
]


@pytest.mark.parametrize("path", PUBLIC_GETS)
async def test_public_paths_serve_unauthenticated(
    anonymous_client: httpx.AsyncClient, path: str
) -> None:
    resp = await anonymous_client.get(path)
    assert resp.status_code == 200, (
        f"Intentionally-public GET {path} should serve unauthenticated "
        f"(got {resp.status_code}: {resp.text[:200]})"
    )


@pytest.mark.parametrize("path", COMMON_AUTHENTICATED_GETS)
async def test_common_paths_reject_unauthenticated(
    anonymous_client: httpx.AsyncClient, path: str
) -> None:
    resp = await anonymous_client.get(path)
    # 401 is the canonical unauthenticated response; some routers use 403
    # via a 'require current user' dependency. Either is acceptable as long
    # as it's NOT 200 (would mean no auth) and NOT 500 (would mean crash).
    assert resp.status_code in (401, 403), (
        f"GET {path} unauthenticated: expected 401/403, got {resp.status_code}: {resp.text[:200]}"
    )


@pytest.mark.parametrize("path", COMMON_AUTHENTICATED_GETS)
async def test_common_paths_ok_for_advertiser(
    advertiser_client: httpx.AsyncClient, path: str
) -> None:
    resp = await advertiser_client.get(path)
    # 200 is the happy path. Tolerate 404 on paths that legitimately 404
    # when the advertiser has no relevant entity (e.g. /legal-profile/me
    # before the advertiser filled legal data). Reject 500 regardless.
    assert resp.status_code != 500, (
        f"GET {path} as advertiser returned 500 — backend bug.\n"
        f"Body: {resp.text[:500]}"
    )
    assert resp.status_code in (200, 204, 404), (
        f"GET {path} as advertiser: unexpected {resp.status_code}: {resp.text[:200]}"
    )


@pytest.mark.parametrize("path", ADMIN_ONLY_GETS)
async def test_admin_paths_reject_non_admin(
    advertiser_client: httpx.AsyncClient, path: str
) -> None:
    resp = await advertiser_client.get(path)
    # Non-admin accessing admin routes → 403 (forbidden), or 401/404
    # depending on dependency style. Never 200 (privilege escalation)
    # and never 500 (crash).
    assert resp.status_code != 200, (
        f"Privilege escalation: advertiser got 200 on admin path {path}"
    )
    assert resp.status_code != 500, (
        f"Admin path {path} crashed with 500: {resp.text[:200]}"
    )
    assert resp.status_code in (401, 403, 404), (
        f"Admin path {path} as advertiser: {resp.status_code}: {resp.text[:200]}"
    )


@pytest.mark.parametrize("path", ADMIN_ONLY_GETS)
async def test_admin_paths_accept_admin(
    admin_client: httpx.AsyncClient, path: str
) -> None:
    resp = await admin_client.get(path)
    assert resp.status_code != 500, (
        f"GET {path} as admin returned 500: {resp.text[:500]}"
    )
    # Accept 200/204 (happy paths), 404 (empty datasets), and 422 (endpoints
    # with required query params we didn't supply — confirms handler lives).
    # Reject 401/403 (admin auth should work) and 500 (crash).
    assert resp.status_code in (200, 204, 404, 422), (
        f"GET {path} as admin: unexpected {resp.status_code}: {resp.text[:200]}"
    )
