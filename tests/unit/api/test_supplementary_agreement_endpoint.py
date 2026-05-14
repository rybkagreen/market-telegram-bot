"""Unit tests for GET /api/placements/{id}/supplementary-agreements (PROMPT 28 Step 8).

Coverage:
* 200 — advertiser is participant → returns both sides (advertiser + owner).
* 200 — owner is participant → returns both sides regardless of requesting role.
* 200 — both_signed=True when both contracts are status='signed'.
* 403 — non-participant (neither advertiser nor channel owner) → access denied.
* 404 — placement not found.
* 404 — placement exists but ДС pair not yet generated (one or both sides missing).

Repositories patched at router import sites; no DB hit.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_current_user, get_db_session
from src.api.main import app
from src.db.models.contract import Contract
from src.db.models.placement_request import PlacementStatus
from src.db.models.user import User


@pytest.fixture
def advertiser_user() -> User:
    return User(
        id=8001,
        telegram_id=111_111_111,
        username="advertiser",
        first_name="Advertiser",
        is_active=True,
    )


@pytest.fixture
def owner_user() -> User:
    return User(
        id=7001,
        telegram_id=222_222_222,
        username="owner",
        first_name="Owner",
        is_active=True,
    )


@pytest.fixture
def stranger_user() -> User:
    return User(
        id=9999,
        telegram_id=999_999_999,
        username="stranger",
        first_name="Stranger",
        is_active=True,
    )


async def _stub_session_dep() -> AsyncGenerator[Any]:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    yield session


def _make_placement(
    *,
    placement_id: int = 4242,
    advertiser_id: int = 8001,
    owner_id: int = 7001,
    channel_id: int = 501,
    status: PlacementStatus = PlacementStatus.pending_owner,
) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=placement_id,
        advertiser_id=advertiser_id,
        owner_id=owner_id,
        channel_id=channel_id,
        channel=SimpleNamespace(id=channel_id, owner_id=owner_id, title="ch", username="ch"),
        status=status.value,
        publication_format="post_24h",
        proposed_price=Decimal("1500"),
        final_price=None,
        final_schedule=None,
        ad_text="stub",
        proposed_schedule=now,
        published_at=None,
        expires_at=None,
        scheduled_delete_at=None,
        deleted_at=None,
        counter_offer_count=0,
        counter_price=None,
        counter_schedule=None,
        counter_comment=None,
        advertiser_counter_price=None,
        advertiser_counter_schedule=None,
        advertiser_counter_comment=None,
        rejection_reason=None,
        clicks_count=0,
        published_reach=None,
        tracking_short_code=None,
        has_dispute=False,
        dispute_status=None,
        erid=None,
        is_test=False,
        test_label=None,
        media_type="none",
        video_file_id=None,
        video_url=None,
        video_thumbnail_file_id=None,
        video_duration=None,
        created_at=now,
        updated_at=now,
    )


def _make_supplementary_contract(
    *,
    contract_id: int,
    user_id: int,
    role: str,
    placement_id: int = 4242,
    status: str = "draft",
) -> Contract:
    c = Contract()
    c.id = contract_id
    c.user_id = user_id
    c.contract_type = "supplementary_agreement"
    c.contract_status = status
    c.placement_id = placement_id
    c.parent_contract_id = 50
    c.template_version = "1.2"
    c.signature_method = None
    c.signed_at = None
    c.expires_at = None
    c.pdf_file_path = (
        f"/data/contracts/supplementary_agreements/sup_agreement_{contract_id}_{role}.pdf"
    )
    c.kep_requested = False
    c.kep_request_email = None
    c.role = role
    c.created_at = datetime.now(UTC)
    c.updated_at = datetime.now(UTC)
    return c


@pytest_asyncio.fixture
async def client_as_advertiser(advertiser_user: User) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_db_session] = _stub_session_dep
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_as_owner(owner_user: User) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: owner_user
    app.dependency_overrides[get_db_session] = _stub_session_dep
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_as_stranger(stranger_user: User) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: stranger_user
    app.dependency_overrides[get_db_session] = _stub_session_dep
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _stub_db_session_with_execute(placement: Any) -> Any:
    """Override get_db_session to yield a session whose .execute returns the placement."""
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=placement)

    async def _dep() -> AsyncGenerator[Any]:
        session = MagicMock()
        session.execute = AsyncMock(return_value=execute_result)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        yield session

    return _dep


# ────────────────────────────────────────────────────────────────────────
# Happy path — both roles see the pair
# ────────────────────────────────────────────────────────────────────────


pytestmark = pytest.mark.asyncio


async def test_get_supplementary_returns_paired_for_advertiser(
    advertiser_user: User,
    owner_user: User,
) -> None:
    placement = _make_placement()
    adv_contract = _make_supplementary_contract(
        contract_id=11, user_id=advertiser_user.id, role="advertiser"
    )
    own_contract = _make_supplementary_contract(contract_id=12, user_id=owner_user.id, role="owner")

    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_db_session] = _stub_db_session_with_execute(placement)
    try:
        repo_mock = MagicMock()
        repo_mock.list_supplementary_for_placement = AsyncMock(
            return_value=[adv_contract, own_contract]
        )
        with patch("src.api.routers.placements.ContractRepo", return_value=repo_mock):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/placements/{placement.id}/supplementary-agreements")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["advertiser"]["id"] == 11
        assert body["advertiser"]["role"] == "advertiser"
        assert body["owner"]["id"] == 12
        assert body["owner"]["role"] == "owner"
        assert body["both_signed"] is False
    finally:
        app.dependency_overrides.clear()


async def test_get_supplementary_returns_paired_for_owner(
    advertiser_user: User,
    owner_user: User,
) -> None:
    placement = _make_placement()
    adv_contract = _make_supplementary_contract(
        contract_id=11, user_id=advertiser_user.id, role="advertiser"
    )
    own_contract = _make_supplementary_contract(contract_id=12, user_id=owner_user.id, role="owner")

    app.dependency_overrides[get_current_user] = lambda: owner_user
    app.dependency_overrides[get_db_session] = _stub_db_session_with_execute(placement)
    try:
        repo_mock = MagicMock()
        repo_mock.list_supplementary_for_placement = AsyncMock(
            return_value=[adv_contract, own_contract]
        )
        with patch("src.api.routers.placements.ContractRepo", return_value=repo_mock):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/placements/{placement.id}/supplementary-agreements")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Owner sees the same paired structure — advertiser-side + owner-side
        assert body["advertiser"]["role"] == "advertiser"
        assert body["owner"]["role"] == "owner"
    finally:
        app.dependency_overrides.clear()


async def test_both_signed_flag_reflects_signed_status_on_both_sides(
    advertiser_user: User,
    owner_user: User,
) -> None:
    placement = _make_placement()
    adv_contract = _make_supplementary_contract(
        contract_id=11, user_id=advertiser_user.id, role="advertiser", status="signed"
    )
    own_contract = _make_supplementary_contract(
        contract_id=12, user_id=owner_user.id, role="owner", status="signed"
    )

    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_db_session] = _stub_db_session_with_execute(placement)
    try:
        repo_mock = MagicMock()
        repo_mock.list_supplementary_for_placement = AsyncMock(
            return_value=[adv_contract, own_contract]
        )
        with patch("src.api.routers.placements.ContractRepo", return_value=repo_mock):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/placements/{placement.id}/supplementary-agreements")
        assert resp.status_code == 200, resp.text
        assert resp.json()["both_signed"] is True
    finally:
        app.dependency_overrides.clear()


# ────────────────────────────────────────────────────────────────────────
# Permission — 403 for non-participant
# ────────────────────────────────────────────────────────────────────────


async def test_get_supplementary_403_for_non_participant(stranger_user: User) -> None:
    placement = _make_placement(advertiser_id=8001, owner_id=7001)
    # stranger is neither advertiser nor channel owner

    app.dependency_overrides[get_current_user] = lambda: stranger_user
    app.dependency_overrides[get_db_session] = _stub_db_session_with_execute(placement)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/placements/{placement.id}/supplementary-agreements")
        assert resp.status_code == 403, resp.text
    finally:
        app.dependency_overrides.clear()


# ────────────────────────────────────────────────────────────────────────
# 404 — placement missing or ДС not generated
# ────────────────────────────────────────────────────────────────────────


async def test_get_supplementary_404_when_placement_missing(advertiser_user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    # session.execute returns None scalar — placement not found
    app.dependency_overrides[get_db_session] = _stub_db_session_with_execute(None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/placements/999999/supplementary-agreements")
        assert resp.status_code == 404, resp.text
        assert "Placement" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


async def test_get_supplementary_404_when_ds_not_generated(advertiser_user: User) -> None:
    """Placement exists, but ContractRepo returns no rows — endpoint 404s
    with explanatory detail (caller may poll)."""
    placement = _make_placement()
    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_db_session] = _stub_db_session_with_execute(placement)
    try:
        repo_mock = MagicMock()
        repo_mock.list_supplementary_for_placement = AsyncMock(return_value=[])
        with patch("src.api.routers.placements.ContractRepo", return_value=repo_mock):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/placements/{placement.id}/supplementary-agreements")
        assert resp.status_code == 404, resp.text
        assert "Supplementary" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


async def test_get_supplementary_404_when_only_one_side_generated(
    advertiser_user: User,
) -> None:
    """Transient state — only advertiser side exists. Endpoint refuses to
    return half-pair; caller polls until owner side also generated."""
    placement = _make_placement()
    only_adv = _make_supplementary_contract(
        contract_id=11, user_id=advertiser_user.id, role="advertiser"
    )

    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_db_session] = _stub_db_session_with_execute(placement)
    try:
        repo_mock = MagicMock()
        repo_mock.list_supplementary_for_placement = AsyncMock(return_value=[only_adv])
        with patch("src.api.routers.placements.ContractRepo", return_value=repo_mock):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/placements/{placement.id}/supplementary-agreements")
        assert resp.status_code == 404, resp.text
    finally:
        app.dependency_overrides.clear()
