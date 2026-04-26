"""End-to-end smoke test for the placement ↔ ORD ↔ Contract integration
points. This file deliberately stays narrow: the counter-offer state
machine is covered by `tests/test_counter_offer_flow.py`, escrow
idempotency by `tests/test_billing_service_idempotency.py`, and the ORD
provider chain by `tests/integration/test_ord_service_with_yandex_mock.py`.

Here we verify the *wiring* between those subsystems:
  1. An advertiser with a LegalProfile can generate their campaign contract.
  2. OrdService.register_creative writes erid onto placement_request.
  3. Once reported to ORD, OrdRegistration.status advances to "reported".
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.contract_service import ContractService
from src.core.services.legal_profile_service import LegalProfileService
from src.core.services.ord_service import OrdService
from src.core.services.stub_ord_provider import StubOrdProvider
from src.db.models.contract import Contract
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


async def _seed(
    db_session: AsyncSession, legal_profile_data: Callable[[str], dict[str, Any]]
) -> tuple[User, User, TelegramChat, PlacementRequest]:
    advertiser = User(telegram_id=991_000_001, username="adv1", first_name="A")
    owner = User(telegram_id=991_000_002, username="own1", first_name="O")
    db_session.add_all([advertiser, owner])
    await db_session.flush()
    await db_session.refresh(advertiser)
    await db_session.refresh(owner)

    await LegalProfileService(db_session).create_profile(
        advertiser.id, legal_profile_data("legal_entity")
    )
    await LegalProfileService(db_session).create_profile(
        owner.id, legal_profile_data("individual_entrepreneur")
    )
    await db_session.flush()

    channel = TelegramChat(
        telegram_id=-1001_555_666_777,
        title="Integration Channel",
        username="integration_ch",
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
        amount=Decimal("1500"),
    )
    db_session.add(escrow_tx)
    await db_session.flush()

    placement = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        status=PlacementStatus.escrow,
        publication_format=PublicationFormat.post_24h,
        ad_text="Buy our product — only for testing.",
        proposed_price=Decimal("1500"),
        final_price=Decimal("1500"),
        escrow_transaction_id=escrow_tx.id,
    )
    db_session.add(placement)
    await db_session.flush()
    await db_session.refresh(placement)
    return advertiser, owner, channel, placement


# ────────────────────────────────────────────
# Contract generation for advertiser campaign
# ────────────────────────────────────────────


async def test_advertiser_campaign_contract_bound_to_placement(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    advertiser, _, _, placement = await _seed(db_session, legal_profile_data)

    contract = await ContractService(db_session).generate_contract(
        user_id=advertiser.id,
        contract_type="advertiser_campaign",
        placement_request_id=placement.id,
    )
    assert contract.placement_request_id == placement.id
    assert contract.user_id == advertiser.id
    # Snapshot contains the LLC's business data (tests/integration/test_contract_service.py
    # covers the whitelist — here we just assert the placement link).
    assert contract.legal_status_snapshot is not None


# ────────────────────────────────────────────
# ORD registration via Stub provider
# ────────────────────────────────────────────


async def test_stub_ord_registration_populates_erid_on_placement(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    _, _, _, placement = await _seed(db_session, legal_profile_data)

    service = OrdService(db_session, provider=StubOrdProvider())
    registration = await service.register_creative(
        placement_request_id=placement.id,
        ad_text=placement.ad_text,
        media_type="none",
    )

    assert registration.erid is not None
    assert registration.erid.startswith("STUB-ERID-")
    assert registration.status == "token_received"

    # placement.erid reflects the registration
    refreshed = await db_session.execute(
        select(PlacementRequest).where(PlacementRequest.id == placement.id)
    )
    updated = refreshed.scalar_one()
    assert updated.erid == registration.erid


async def test_report_publication_marks_registration_reported(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    _, _, _, placement = await _seed(db_session, legal_profile_data)
    service = OrdService(db_session, provider=StubOrdProvider())

    await service.register_creative(
        placement_request_id=placement.id,
        ad_text=placement.ad_text,
        media_type="none",
    )

    published_at = datetime.now(UTC)
    await service.report_publication(
        placement_request_id=placement.id,
        published_at=published_at,
    )

    result = await db_session.execute(
        select(OrdRegistration).where(OrdRegistration.placement_request_id == placement.id)
    )
    registration = result.scalar_one()
    assert registration.status == "reported"
    assert registration.reported_at is not None


async def test_report_publication_without_registration_is_noop(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    _, _, _, placement = await _seed(db_session, legal_profile_data)
    service = OrdService(db_session, provider=StubOrdProvider())

    # No register_creative call first — report must not raise.
    await service.report_publication(
        placement_request_id=placement.id,
        published_at=datetime.now(UTC),
    )

    result = await db_session.execute(
        select(OrdRegistration).where(OrdRegistration.placement_request_id == placement.id)
    )
    assert result.scalar_one_or_none() is None


# ────────────────────────────────────────────
# Cross-cutting: both contract + ORD land together
# ────────────────────────────────────────────


async def test_end_to_end_wiring_smoke(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    """Smoke test: advertiser can reach the point where both a contract row
    and an ORD registration exist for the same placement, with the correct
    foreign keys populated."""
    advertiser, _, _, placement = await _seed(db_session, legal_profile_data)

    contract = await ContractService(db_session).generate_contract(
        advertiser.id, "advertiser_campaign", placement.id
    )
    registration = await OrdService(db_session, provider=StubOrdProvider()).register_creative(
        placement.id, placement.ad_text, "none"
    )

    # Re-query both — wiring intact
    cresult = await db_session.execute(select(Contract).where(Contract.id == contract.id))
    rresult = await db_session.execute(
        select(OrdRegistration).where(OrdRegistration.id == registration.id)
    )
    c = cresult.scalar_one()
    r = rresult.scalar_one()

    assert c.placement_request_id == placement.id
    assert c.user_id == advertiser.id
    assert r.placement_request_id == placement.id
    assert r.erid == registration.erid
