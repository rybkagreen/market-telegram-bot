"""Integration tests for /api/legal-profile endpoints (all 4 legal statuses)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_from_web_portal, get_db_session
from src.api.main import app
from src.db.models.user import User
from tests.conftest import VALID_INN10, VALID_INN12

pytestmark = pytest.mark.asyncio

ALL_STATUSES = ["legal_entity", "individual_entrepreneur", "self_employed", "individual"]


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(telegram_id=960_000_001, username="api_user", first_name="API")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def authed_client(
    db_session: AsyncSession, test_user: User
) -> AsyncGenerator[AsyncClient]:
    """httpx client with dependency_overrides wired to the per-test DB session
    and a synthetic authenticated user."""

    async def _session_override() -> AsyncGenerator[AsyncSession]:
        try:
            yield db_session
        except Exception:
            # match production get_db_session behaviour
            await db_session.rollback()
            raise

    async def _user_override() -> User:
        return test_user

    app.dependency_overrides[get_db_session] = _session_override
    app.dependency_overrides[get_current_user_from_web_portal] = _user_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user_from_web_portal, None)


# ────────────────────────────────────────────
# GET /me
# ────────────────────────────────────────────


async def test_get_me_returns_null_when_no_profile(authed_client: AsyncClient) -> None:
    r = await authed_client.get("/api/legal-profile/me")
    assert r.status_code == 200
    assert r.json() is None


# ────────────────────────────────────────────
# POST / (create) — all 4 statuses
# ────────────────────────────────────────────


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_create_profile_returns_201_for_all_statuses(
    authed_client: AsyncClient,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    payload = _json_safe(legal_profile_data(status))
    r = await authed_client.post("/api/legal-profile", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["legal_status"] == status
    assert body["legal_name"] == payload["legal_name"]


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_create_profile_then_get_me_masks_bank_account(
    authed_client: AsyncClient,
    legal_profile_data: Callable[[str], dict[str, Any]],
    status: str,
) -> None:
    payload = _json_safe(legal_profile_data(status))
    await authed_client.post("/api/legal-profile", json=payload)
    r = await authed_client.get("/api/legal-profile/me")
    assert r.status_code == 200
    body = r.json()

    if "bank_account" in payload and payload["bank_account"]:
        returned = body["bank_account"]
        assert returned is not None
        # Must be masked — only last 4 digits visible
        assert returned.startswith("****")
        assert returned.endswith(payload["bank_account"][-4:])


# ────────────────────────────────────────────
# PATCH /
# ────────────────────────────────────────────


async def test_patch_updates_profile(
    authed_client: AsyncClient,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    await authed_client.post(
        "/api/legal-profile", json=_json_safe(legal_profile_data("legal_entity"))
    )
    r = await authed_client.patch("/api/legal-profile", json={"legal_name": "ООО «Новое»"})
    assert r.status_code == 200
    assert r.json()["legal_name"] == "ООО «Новое»"


# ────────────────────────────────────────────
# /validate-inn
# ────────────────────────────────────────────


async def test_validate_inn_valid_10(authed_client: AsyncClient) -> None:
    r = await authed_client.post("/api/legal-profile/validate-inn", json={"inn": VALID_INN10})
    assert r.status_code == 200
    assert r.json() == {"valid": True, "type": "10-digit"}


async def test_validate_inn_valid_12(authed_client: AsyncClient) -> None:
    r = await authed_client.post("/api/legal-profile/validate-inn", json={"inn": VALID_INN12})
    assert r.status_code == 200
    assert r.json() == {"valid": True, "type": "12-digit"}


async def test_validate_inn_invalid_checksum(authed_client: AsyncClient) -> None:
    broken = VALID_INN10[:-1] + ("0" if VALID_INN10[-1] != "0" else "1")
    r = await authed_client.post("/api/legal-profile/validate-inn", json={"inn": broken})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False


async def test_validate_inn_non_numeric(authed_client: AsyncClient) -> None:
    r = await authed_client.post(
        "/api/legal-profile/validate-inn", json={"inn": "7707X83893"}
    )
    assert r.status_code == 200
    assert r.json() == {"valid": False, "type": "invalid"}


# ────────────────────────────────────────────
# /required-fields
# ────────────────────────────────────────────


@pytest.mark.parametrize("status", ALL_STATUSES)
async def test_required_fields_per_status(
    authed_client: AsyncClient, status: str
) -> None:
    r = await authed_client.get(
        "/api/legal-profile/required-fields", params={"legal_status": status}
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["fields"], list)
    assert len(body["fields"]) > 0
    assert isinstance(body["scans"], list)

    # Type-specific flag expectations
    if status == "legal_entity":
        assert body["show_bank_details"] is True
        assert body["show_passport"] is False
    elif status == "individual_entrepreneur":
        assert body["show_bank_details"] is True
        assert body["tax_regime_required"] is True
    elif status == "self_employed":
        assert body["show_yoomoney"] is True
        assert body["show_bank_details"] is False
    elif status == "individual":
        assert body["show_passport"] is True


# ────────────────────────────────────────────
# /validate-entity — cross-validation INN type vs legal_status
# ────────────────────────────────────────────


async def test_validate_entity_legal_entity_matches_10_digit_inn(
    authed_client: AsyncClient,
) -> None:
    """legal_entity with 10-digit INN + OGRN passes cross-validation."""
    from tests.conftest import VALID_OGRN

    r = await authed_client.post(
        "/api/legal-profile/validate-entity",
        json={
            "inn": VALID_INN10,
            "legal_status": "legal_entity",
            "ogrn": VALID_OGRN,
        },
    )
    assert r.status_code == 200
    assert r.json()["is_valid"] is True


async def test_validate_entity_legal_entity_missing_ogrn_is_rejected(
    authed_client: AsyncClient,
) -> None:
    """INN length matches, but OGRN is required for legal_entity."""
    r = await authed_client.post(
        "/api/legal-profile/validate-entity",
        json={"inn": VALID_INN10, "legal_status": "legal_entity"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is False
    assert any("ОГРН" in e["message"] for e in body["errors"])


async def test_validate_entity_legal_entity_rejects_12_digit_inn(
    authed_client: AsyncClient,
) -> None:
    r = await authed_client.post(
        "/api/legal-profile/validate-entity",
        json={"inn": VALID_INN12, "legal_status": "legal_entity"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is False
    assert any(e["field"] == "inn" for e in body["errors"])


async def test_validate_entity_self_employed_without_ogrnip_passes(
    authed_client: AsyncClient,
) -> None:
    """self_employed with 12-digit INN and no OGRNIP is valid."""
    r = await authed_client.post(
        "/api/legal-profile/validate-entity",
        json={"inn": VALID_INN12, "legal_status": "self_employed"},
    )
    assert r.status_code == 200
    assert r.json()["is_valid"] is True


async def test_validate_entity_self_employed_with_ogrnip_is_rejected(
    authed_client: AsyncClient,
) -> None:
    """Regression for the 2026-04-21 gap: self_employed + OGRNIP → is_valid=False."""
    from tests.conftest import VALID_OGRNIP

    r = await authed_client.post(
        "/api/legal-profile/validate-entity",
        json={
            "inn": VALID_INN12,
            "legal_status": "self_employed",
            "ogrnip": VALID_OGRNIP,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is False
    assert any(e["field"] == "ogrnip" for e in body["errors"])


# ────────────────────────────────────────────
# /scan
# ────────────────────────────────────────────


async def test_scan_upload_updates_file_id(
    authed_client: AsyncClient,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    await authed_client.post(
        "/api/legal-profile", json=_json_safe(legal_profile_data("legal_entity"))
    )
    r = await authed_client.post(
        "/api/legal-profile/scan",
        json={"scan_type": "inn", "file_id": "TELEGRAM_FILE_123"},
    )
    assert r.status_code == 200
    assert r.json() == {"success": True}

    me = await authed_client.get("/api/legal-profile/me")
    assert me.json()["has_inn_scan"] is True


async def test_scan_upload_rejects_unknown_type(authed_client: AsyncClient) -> None:
    r = await authed_client.post(
        "/api/legal-profile/scan",
        json={"scan_type": "driver_license", "file_id": "F"},
    )
    # Pydantic Literal validation returns 422 before hitting the service
    assert r.status_code == 422


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────


def _json_safe(data: dict[str, Any]) -> dict[str, Any]:
    """Serialise dates to ISO strings so httpx.post(json=...) accepts them."""
    import datetime as _dt

    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, _dt.date):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
