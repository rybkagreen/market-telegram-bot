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


# ─── Helper: every query-param regression must only ever be a 4xx ─────


def _not_500(resp: httpx.Response) -> None:
    assert resp.status_code < 500, (
        f"Router must never 500 on a bad query param — got "
        f"{resp.status_code}: {resp.text[:200]}"
    )


# ─── /api/campaigns ?status= (CampaignStatus Enum) ────────────────────
#
# The router types it as `Annotated[CampaignStatus | None, Query()]`.
# FastAPI's Enum coercion returns 422 for unknown members — never 500.


@pytest.mark.parametrize(
    "bad_status",
    ["active", "completed", "", "null", "DROP TABLE users;--"],
)
async def test_campaigns_invalid_status_is_not_500(
    advertiser_client: httpx.AsyncClient, bad_status: str
) -> None:
    resp = await advertiser_client.get(
        "/api/campaigns", params={"status": bad_status}
    )
    _not_500(resp)
    assert resp.status_code in {200, 422}, resp.text


@pytest.mark.parametrize(
    "concrete_status",
    ["pending_owner", "escrow", "published", "cancelled"],
)
async def test_campaigns_valid_status_200(
    advertiser_client: httpx.AsyncClient, concrete_status: str
) -> None:
    resp = await advertiser_client.get(
        "/api/campaigns", params={"status": concrete_status}
    )
    assert resp.status_code == 200, resp.text


# ─── /api/campaigns/list ?status= (CampaignStatusLiteral) ─────────────
#
# Router types it as `Literal["draft","queued",...]`. Alien strings
# must fail with 422, not 500 — even though the literal values don't
# match actual PlacementStatus (an inherited quirk).


@pytest.mark.parametrize(
    "bad_status",
    ["pending_owner", "whatever", "", "escrow"],
)
async def test_campaigns_list_invalid_status_is_not_500(
    advertiser_client: httpx.AsyncClient, bad_status: str
) -> None:
    resp = await advertiser_client.get(
        "/api/campaigns/list", params={"status": bad_status}
    )
    _not_500(resp)


# ─── /api/admin/payouts ?status= (PayoutStatusSchema Enum) ────────────


@pytest.mark.parametrize(
    "bad_status",
    ["active", "anything", "", "pending_review; DROP"],
)
async def test_admin_payouts_invalid_status_is_not_500(
    admin_client: httpx.AsyncClient, bad_status: str
) -> None:
    resp = await admin_client.get(
        "/api/admin/payouts", params={"status": bad_status}
    )
    _not_500(resp)


# ─── /api/admin/contracts ?status_filter= (str, passed to SQL) ────────
#
# Router types it as `str | None` and compares directly to
# Contract.contract_status. It must not 500 on any input; unknown
# values are silently filtered out (0 matches) — acceptable for now.


@pytest.mark.parametrize("bad", ["", "whatever", "'OR 1=1--"])
async def test_admin_contracts_bad_status_is_not_500(
    admin_client: httpx.AsyncClient, bad: str
) -> None:
    resp = await admin_client.get(
        "/api/admin/contracts", params={"status_filter": bad}
    )
    _not_500(resp)
    assert resp.status_code in {200, 422}


# ─── /api/disputes/ ?status_filter= (str, repo try/except) ────────────
#
# Repo swallows ValueError and returns all — not a 500. Pin behaviour.


@pytest.mark.parametrize(
    "status",
    ["open", "resolved", "closed", "all", "garbage", "", "OWNER_EXPLAINED"],
)
async def test_disputes_any_status_is_not_500(
    advertiser_client: httpx.AsyncClient, status: str
) -> None:
    resp = await advertiser_client.get(
        "/api/disputes/", params={"status_filter": status}
    )
    _not_500(resp)


# ─── /api/disputes/admin/disputes ?status= (router try/except → 400) ──


async def test_admin_disputes_invalid_status_returns_400(
    admin_client: httpx.AsyncClient,
) -> None:
    resp = await admin_client.get(
        "/api/disputes/admin/disputes", params={"status": "nope"}
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.parametrize(
    "valid_status", ["open", "owner_explained", "resolved", "all"]
)
async def test_admin_disputes_valid_status_200(
    admin_client: httpx.AsyncClient, valid_status: str
) -> None:
    resp = await admin_client.get(
        "/api/disputes/admin/disputes", params={"status": valid_status}
    )
    assert resp.status_code == 200, resp.text


# ─── /api/feedback/admin/ ?status_filter= (router try/except → 400) ───


async def test_admin_feedback_invalid_status_returns_400(
    admin_client: httpx.AsyncClient,
) -> None:
    resp = await admin_client.get(
        "/api/feedback/admin/", params={"status_filter": "bogus"}
    )
    assert resp.status_code == 400, resp.text


# ─── /api/analytics/cashflow ?days= (IntEnum: 7/30/90) ────────────────


@pytest.mark.parametrize("valid_days", [7, 30, 90])
async def test_cashflow_valid_days_200(
    advertiser_client: httpx.AsyncClient, valid_days: int
) -> None:
    resp = await advertiser_client.get(
        "/api/analytics/cashflow", params={"days": valid_days}
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize("bad_days", ["abc", -1, 0, 14, 365])
async def test_cashflow_invalid_days_is_not_500(
    advertiser_client: httpx.AsyncClient, bad_days: int | str
) -> None:
    resp = await advertiser_client.get(
        "/api/analytics/cashflow", params={"days": bad_days}
    )
    _not_500(resp)
    assert resp.status_code == 422, resp.text


# ─── /api/analytics/summary ?days= (int Query ge=1 le=90) ─────────────


@pytest.mark.parametrize("bad_days", [0, 91, -5, "notanint"])
async def test_analytics_summary_bad_days_is_not_500(
    advertiser_client: httpx.AsyncClient, bad_days: int | str
) -> None:
    resp = await advertiser_client.get(
        "/api/analytics/summary", params={"days": bad_days}
    )
    _not_500(resp)
    assert resp.status_code == 422


# ─── /api/channels/compare/preview ?ids= (CSV of ints, try/except) ────


@pytest.mark.parametrize("bad", ["abc", "1,two", "", "1,,2", "1; 2"])
async def test_channels_compare_preview_bad_ids_is_not_500(
    advertiser_client: httpx.AsyncClient, bad: str
) -> None:
    resp = await advertiser_client.get(
        "/api/channels/compare/preview", params={"ids": bad}
    )
    _not_500(resp)
    # Either a 400 (csv parse) or 422 (empty required) — never 500.
    assert resp.status_code in {400, 422}


# ─── /api/reputation/* ?role= (free-text string passed to repo) ───────


@pytest.mark.parametrize(
    "role", ["advertiser", "owner", "nonsense", "", "Advertiser"]
)
async def test_reputation_any_role_is_not_500(
    advertiser_client: httpx.AsyncClient, role: str
) -> None:
    resp = await advertiser_client.get(
        "/api/reputation/leaderboard", params={"role": role}
    )
    _not_500(resp)


# ─── Pagination guards that apply to every paginated list endpoint ────


PAGINATED_PATHS: list[tuple[str, dict[str, str]]] = [
    ("/api/placements/", {"view": "advertiser"}),
    ("/api/campaigns", {}),
    ("/api/campaigns/list", {}),
    ("/api/reputation/leaderboard", {}),
]


@pytest.mark.parametrize("path,extra", PAGINATED_PATHS)
async def test_pagination_limit_out_of_bounds_never_500(
    advertiser_client: httpx.AsyncClient, path: str, extra: dict[str, str]
) -> None:
    for limit in ("abc", -1, 0, 10000):
        resp = await advertiser_client.get(path, params={**extra, "limit": limit})
        _not_500(resp)
