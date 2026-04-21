"""
Query-parameter coercion regression tests.

These guard the exact bug class that surfaced in the S-47 post-merge smoke:
a frontend sends a string query value (e.g. status=active), FastAPI's
signature coerces it into a strict Literal/Enum, and the enum call raises
ValueError → 500 because the handler never caught it.

Every API param whose domain is bigger than the Python-side enum (aliases,
UI groupings) must either accept the alias or return 400 with a useful
message. Never 500.
"""

from __future__ import annotations

import httpx
import pytest


pytestmark = pytest.mark.asyncio


# ─── /api/placements/ ?status= ───────────────────────────────────────


@pytest.mark.parametrize("alias", ["active", "completed", "cancelled"])
async def test_placements_status_aliases_accepted(
    advertiser_client: httpx.AsyncClient, alias: str
) -> None:
    """Frontend-only aliases must not 500 the backend."""
    resp = await advertiser_client.get(
        "/api/placements/", params={"view": "advertiser", "status": alias}
    )
    assert resp.status_code == 200, (
        f"status={alias!r} should be accepted, got {resp.status_code}: {resp.text}"
    )
    assert isinstance(resp.json(), list)


@pytest.mark.parametrize(
    "concrete_status",
    [
        "pending_owner",
        "counter_offer",
        "pending_payment",
        "escrow",
        "published",
        "cancelled",
        "refunded",
        "failed",
        "failed_permissions",
    ],
)
async def test_placements_status_concrete_values_accepted(
    advertiser_client: httpx.AsyncClient, concrete_status: str
) -> None:
    """Literal PlacementStatus enum members must continue to work."""
    resp = await advertiser_client.get(
        "/api/placements/", params={"view": "advertiser", "status": concrete_status}
    )
    assert resp.status_code == 200, resp.text


async def test_placements_invalid_status_returns_400_not_500(
    advertiser_client: httpx.AsyncClient,
) -> None:
    resp = await advertiser_client.get(
        "/api/placements/",
        params={"view": "advertiser", "status": "not-a-status-at-all"},
    )
    assert resp.status_code == 400, (
        f"Unknown status must be 400, got {resp.status_code}: {resp.text}"
    )
    # Error message should include the allowed values to aid debugging.
    body = resp.json()
    detail = body.get("detail", "")
    assert "active" in detail or "pending_owner" in detail, (
        f"Error message must list allowed values, got: {detail!r}"
    )


# ─── /api/placements/ ?view= ─────────────────────────────────────────


@pytest.mark.parametrize("view", ["advertiser", "owner"])
async def test_placements_view_valid(
    advertiser_client: httpx.AsyncClient, view: str
) -> None:
    resp = await advertiser_client.get("/api/placements/", params={"view": view})
    assert resp.status_code == 200


async def test_placements_no_view_returns_union(
    advertiser_client: httpx.AsyncClient,
) -> None:
    # No view = UNION of advertiser+owner queries.
    resp = await advertiser_client.get("/api/placements/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_placements_invalid_view_returns_400(
    advertiser_client: httpx.AsyncClient,
) -> None:
    resp = await advertiser_client.get(
        "/api/placements/", params={"view": "bogus"}
    )
    assert resp.status_code == 400, resp.text


# ─── Pagination guards ───────────────────────────────────────────────


async def test_placements_limit_out_of_range_returns_422(
    advertiser_client: httpx.AsyncClient,
) -> None:
    # Annotated[int, Query(ge=1, le=100)] — 0 and 101 must fail validation
    # cleanly. 422 is FastAPI's standard for query validation errors.
    r_zero = await advertiser_client.get("/api/placements/", params={"limit": 0})
    assert r_zero.status_code == 422, r_zero.text
    r_big = await advertiser_client.get("/api/placements/", params={"limit": 101})
    assert r_big.status_code == 422, r_big.text


async def test_placements_limit_non_integer_returns_422(
    advertiser_client: httpx.AsyncClient,
) -> None:
    resp = await advertiser_client.get(
        "/api/placements/", params={"limit": "abc"}
    )
    assert resp.status_code == 422, resp.text


async def test_placements_offset_negative_returns_422(
    advertiser_client: httpx.AsyncClient,
) -> None:
    resp = await advertiser_client.get(
        "/api/placements/", params={"offset": -1}
    )
    assert resp.status_code == 422, resp.text
