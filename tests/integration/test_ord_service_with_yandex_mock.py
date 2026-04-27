"""Integration test: OrdService.register_creative end-to-end through
YandexOrdProvider with httpx.MockTransport.

Exercises the full 4-step registration chain (organization → platform →
contract → creative) and verifies the OrdRegistration row + placement.erid
are populated correctly."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.legal_profile_service import LegalProfileService
from src.core.services.ord_service import OrdService
from src.core.services.yandex_ord_provider import YandexOrdProvider
from src.db.models.ord_registration import OrdRegistration
from src.db.models.placement_request import (
    PlacementRequest,
    PlacementStatus,
    PublicationFormat,
)
from src.db.models.telegram_chat import TelegramChat
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User

pytestmark = pytest.mark.asyncio

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "yandex_ord"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _make_provider(handler) -> YandexOrdProvider:
    provider = YandexOrdProvider(
        api_key="test-key",
        base_url="https://api.ord.yandex.net",
        rekharbor_org_id="rekharbor-main",
        rekharbor_inn="7707123456",
    )
    provider._client = httpx.AsyncClient(
        base_url="https://api.ord.yandex.net",
        headers={"Authorization": "Bearer test-key"},
        transport=httpx.MockTransport(handler),
    )
    return provider


# ────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────


@pytest.fixture
def ord_mock_handler() -> list[httpx.Request]:
    """Dispatches each endpoint to its matching success fixture and returns
    a list that collects all recorded requests (one per endpoint hit)."""

    recorded: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        recorded.append(req)
        path = req.url.path
        if path == "/api/v7/organization":
            return httpx.Response(200, json=_load("register_organization_success.json"))
        if path == "/api/v7/platforms":
            return httpx.Response(200, json=_load("register_platform_success.json"))
        if path == "/api/v7/contract":
            return httpx.Response(200, json=_load("register_contract_success.json"))
        if path == "/api/v7/creative":
            return httpx.Response(200, json=_load("register_creative_success.json"))
        if path == "/api/v7/statistics":
            return httpx.Response(200, json=_load("report_publication_success.json"))
        if path == "/api/v7/status":
            return httpx.Response(200, json=_load("status_erir_confirmed.json"))
        return httpx.Response(404, json={"error": {"message": f"No mock for {path}"}})

    handler._recorded = recorded  # type: ignore[attr-defined]
    return handler


async def _seed_placement(
    db_session: AsyncSession, legal_profile_data
) -> PlacementRequest:
    """Seed an advertiser + owner + channel + placement_request."""
    advertiser = User(telegram_id=990_000_001, username="adv", first_name="Adv")
    owner = User(telegram_id=990_000_002, username="own", first_name="Own")
    db_session.add_all([advertiser, owner])
    await db_session.flush()
    await db_session.refresh(advertiser)
    await db_session.refresh(owner)

    await LegalProfileService(db_session).create_profile(
        advertiser.id, legal_profile_data("legal_entity")
    )
    await db_session.flush()

    channel = TelegramChat(
        telegram_id=-1001_234_567_890,
        title="Test Channel",
        username="test_channel",
        owner_user_id=owner.id,
    )
    db_session.add(channel)
    await db_session.flush()
    await db_session.refresh(channel)

    # INV-1 (placement_escrow_integrity): status='escrow' requires
    # escrow_transaction_id IS NOT NULL. Seed an escrow_freeze tx first.
    escrow_tx = Transaction(
        user_id=advertiser.id,
        type=TransactionType.escrow_freeze,
        amount=Decimal("1000"),
    )
    db_session.add(escrow_tx)
    await db_session.flush()

    placement = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        status=PlacementStatus.escrow,
        publication_format=PublicationFormat.post_24h,
        ad_text="Buy our widget today!",
        proposed_price=Decimal("1000"),
        final_price=Decimal("1000"),
        escrow_transaction_id=escrow_tx.id,
    )
    db_session.add(placement)
    await db_session.flush()
    await db_session.refresh(placement)
    return placement


# ────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────


async def test_register_creative_hits_all_four_endpoints(
    db_session: AsyncSession,
    legal_profile_data,
    ord_mock_handler,
) -> None:
    placement = await _seed_placement(db_session, legal_profile_data)

    provider = _make_provider(ord_mock_handler)
    service = OrdService(db_session, provider=provider)

    registration = await service.register_creative(
        placement_request_id=placement.id,
        ad_text="Buy our widget today!",
        media_type="photo",
    )

    # All 4 endpoints hit in order
    paths = [r.url.path for r in ord_mock_handler._recorded]
    assert paths == [
        "/api/v7/organization",
        "/api/v7/platforms",
        "/api/v7/contract",
        "/api/v7/creative",
    ]

    # Registration row populated from fixtures
    assert registration.status == "token_received"
    assert registration.erid == "kra23abc-erid-token-xyz789"
    assert registration.advertiser_ord_id == f"org-{placement.advertiser_id}"
    assert registration.platform_ord_id == f"platform-{placement.channel_id}"
    assert registration.contract_ord_id == f"contract-{placement.id}"


async def test_register_creative_updates_placement_erid(
    db_session: AsyncSession,
    legal_profile_data,
    ord_mock_handler,
) -> None:
    placement = await _seed_placement(db_session, legal_profile_data)

    provider = _make_provider(ord_mock_handler)
    await OrdService(db_session, provider=provider).register_creative(
        placement_request_id=placement.id,
        ad_text="Ad text",
        media_type="photo",
    )

    # placement.erid is written after register_creative
    refreshed = await db_session.execute(
        select(PlacementRequest).where(PlacementRequest.id == placement.id)
    )
    updated = refreshed.scalar_one()
    assert updated.erid == "kra23abc-erid-token-xyz789"


async def test_register_creative_is_idempotent(
    db_session: AsyncSession,
    legal_profile_data,
    ord_mock_handler,
) -> None:
    placement = await _seed_placement(db_session, legal_profile_data)
    provider = _make_provider(ord_mock_handler)
    svc = OrdService(db_session, provider=provider)

    r1 = await svc.register_creative(placement.id, "Ad", "photo")
    # Second call returns the same registration without hitting the provider
    # a second time (per ord_service.py:99-101).
    call_count_before = len(ord_mock_handler._recorded)
    r2 = await svc.register_creative(placement.id, "Ad", "photo")
    call_count_after = len(ord_mock_handler._recorded)

    assert r1.id == r2.id
    assert call_count_after == call_count_before


async def test_register_creative_media_type_affects_creative_form(
    db_session: AsyncSession,
    legal_profile_data,
    ord_mock_handler,
) -> None:
    placement = await _seed_placement(db_session, legal_profile_data)
    provider = _make_provider(ord_mock_handler)

    await OrdService(db_session, provider=provider).register_creative(
        placement.id, "Ad", "video"
    )

    creative_req = next(
        r for r in ord_mock_handler._recorded if r.url.path == "/api/v7/creative"
    )
    body = json.loads(creative_req.content)
    assert body["form"] == "text_video_block"


async def test_register_creative_writes_advertiser_inn_into_payload(
    db_session: AsyncSession,
    legal_profile_data,
    ord_mock_handler,
) -> None:
    placement = await _seed_placement(db_session, legal_profile_data)
    provider = _make_provider(ord_mock_handler)

    await OrdService(db_session, provider=provider).register_creative(
        placement.id, "Ad", "photo"
    )

    org_req = next(
        r for r in ord_mock_handler._recorded if r.url.path == "/api/v7/organization"
    )
    body = json.loads(org_req.content)
    # Advertiser's INN from LegalProfile ended up in the org-registration payload
    from tests.conftest import VALID_INN10

    assert body["inn"] == VALID_INN10


async def test_register_creative_missing_placement_raises(
    db_session: AsyncSession,
    legal_profile_data,
    ord_mock_handler,
) -> None:
    provider = _make_provider(ord_mock_handler)
    with pytest.raises(ValueError, match="not found"):
        await OrdService(db_session, provider=provider).register_creative(
            placement_request_id=999_999,
            ad_text="Ad",
            media_type="photo",
        )


async def test_registration_row_persists_in_db(
    db_session: AsyncSession,
    legal_profile_data,
    ord_mock_handler,
) -> None:
    placement = await _seed_placement(db_session, legal_profile_data)
    provider = _make_provider(ord_mock_handler)
    await OrdService(db_session, provider=provider).register_creative(
        placement.id, "Ad", "photo"
    )

    result = await db_session.execute(
        select(OrdRegistration).where(OrdRegistration.placement_request_id == placement.id)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.erid == "kra23abc-erid-token-xyz789"
    assert row.status == "token_received"
    assert row.token_received_at is not None
