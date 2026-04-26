"""T1-3 fix integration tests — expires_at must be +24h across both
counter_offer and pending_payment paths in service and bot layers.

Surfaced by PHASE2_RESEARCH_2026-04-26.md Tier-1 objection T1-3:
- service path counter_offer was +3h, bot path was +24h for same status.
- service path accept(→pending_payment) did NOT refresh expires_at, so the
  prior counter_offer deadline clamped the payment window.

Phase 2 will subsume this into PlacementTransitionService._sync_status_timestamps;
these tests pin the chosen canonical 24h until that lands.
"""

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepo


def _make_service(session: AsyncSession) -> PlacementRequestService:
    return PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )


async def _seed_actors(session: AsyncSession) -> tuple[User, User, TelegramChat]:
    """Inline actor seeding — conftest fixtures use removed `current_role` field."""
    advertiser = User(telegram_id=910001, first_name="Adv", username="adv_t13")
    owner = User(telegram_id=910002, first_name="Own", username="own_t13")
    session.add_all([advertiser, owner])
    await session.flush()
    channel = TelegramChat(
        telegram_id=-100910003,
        title="T1-3 Channel",
        username="t13_channel",
        owner_id=owner.id,
        member_count=1000,
    )
    session.add(channel)
    await session.commit()
    await session.refresh(advertiser)
    await session.refresh(owner)
    await session.refresh(channel)
    return advertiser, owner, channel


@pytest.mark.asyncio
async def test_service_counter_offer_sets_expires_at_24h(
    db_session: AsyncSession,
) -> None:
    """T1-3 fix: service path owner_counter_offer must set expires_at to +24h."""
    advertiser, owner, channel = await _seed_actors(db_session)
    placement = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        proposed_price=Decimal("1000.00"),
        ad_text="Test ad text for counter offer expires_at",
        status=PlacementStatus.pending_owner,
    )
    db_session.add(placement)
    await db_session.commit()
    await db_session.refresh(placement)

    service = _make_service(db_session)

    before = datetime.now(UTC)
    result = await service.owner_counter_offer(
        placement_id=placement.id,
        owner_id=owner.id,
        proposed_price=Decimal("1500.00"),
    )
    after = datetime.now(UTC)

    assert result is not None
    assert result.status == PlacementStatus.counter_offer
    assert result.expires_at is not None
    # tight bracket around now+24h
    assert before + timedelta(hours=24) - timedelta(seconds=1) <= result.expires_at
    assert result.expires_at <= after + timedelta(hours=24) + timedelta(seconds=1)
    # negative assertion: definitely not the old +3h value
    assert result.expires_at - before > timedelta(hours=23, minutes=59)


@pytest.mark.asyncio
async def test_service_advertiser_accept_counter_refreshes_expires_at_to_24h(
    db_session: AsyncSession,
) -> None:
    """T1-3 fix: transitioning counter_offer → pending_payment must refresh
    expires_at to now()+24h, not retain a stale value from counter_offer."""
    advertiser, owner, channel = await _seed_actors(db_session)
    stale = datetime.now(UTC) - timedelta(hours=1)
    placement = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        proposed_price=Decimal("1000.00"),
        ad_text="Test ad text for accept_counter expires_at",
        status=PlacementStatus.counter_offer,
        counter_price=Decimal("1500.00"),
        expires_at=stale,
    )
    db_session.add(placement)
    await db_session.commit()
    await db_session.refresh(placement)

    service = _make_service(db_session)

    before = datetime.now(UTC)
    result = await service.advertiser_accept_counter(
        placement_id=placement.id,
        advertiser_id=advertiser.id,
    )
    after = datetime.now(UTC)

    assert result is not None
    assert result.status == PlacementStatus.pending_payment
    assert result.expires_at is not None
    assert result.expires_at != stale
    assert before + timedelta(hours=24) - timedelta(seconds=1) <= result.expires_at
    assert result.expires_at <= after + timedelta(hours=24) + timedelta(seconds=1)


def test_bot_arbitration_uses_24h_regression_guard() -> None:
    """T1-3 source-text guard: bot/handlers/owner/arbitration.py must keep using
    +24h for both the accept path (line 208 today) and _send_counter_offer
    (line 503 today). Guards against silent regression to +3h or other values
    until Phase 2's PlacementTransitionService takes over the timestamp logic.
    """
    src_path = Path(__file__).resolve().parents[2] / "src/bot/handlers/owner/arbitration.py"
    text = src_path.read_text(encoding="utf-8")
    matches = re.findall(
        r"req\.expires_at\s*=\s*datetime\.now\(UTC\)\s*\+\s*timedelta\(hours=(\d+)\)",
        text,
    )
    assert len(matches) >= 2, (
        "expected ≥2 expires_at assignments in arbitration.py "
        "(accept handler + _send_counter_offer); found "
        f"{len(matches)}: {matches}"
    )
    for hours_literal in matches:
        assert int(hours_literal) == 24, (
            f"bot-path expires_at delta is {hours_literal}h — expected 24h "
            "(T1-3: counter_offer / pending_payment both use +24h)"
        )
