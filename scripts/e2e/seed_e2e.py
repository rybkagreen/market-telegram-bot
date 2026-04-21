#!/usr/bin/env python3
"""
Seed deterministic test data for Playwright E2E suite.

Idempotent: safe to re-run. Uses fixed telegram_ids so Playwright fixture can
look them up by known values.

Users created:
    9001 — advertiser (plan=free, 500 RUB balance)
    9002 — owner (plan=free, owns test channel)
    9003 — admin (is_admin=True)

Entities created:
    - Test channel owned by 9002 with baseline mediakit
    - One pending PlacementRequest from 9001 → 9002's channel
    - One escrow PlacementRequest (published) for analytics/tx-history coverage

Run inside the api-test container:
    docker compose -f docker-compose.test.yml exec api-test \\
        poetry run python /app/scripts/e2e/seed_e2e.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, "/app")

from sqlalchemy import select

from src.db.models.placement_request import (
    PlacementRequest,
    PlacementStatus,
    PublicationFormat,
)
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.session import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("seed_e2e")

ADVERTISER_TG = 9001
OWNER_TG = 9002
ADMIN_TG = 9003


async def _upsert_user(
    session,
    *,
    telegram_id: int,
    first_name: str,
    username: str,
    is_admin: bool = False,
    balance: Decimal = Decimal("0"),
) -> User:
    q = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = q.scalar_one_or_none()
    if user:
        user.first_name = first_name
        user.username = username
        user.is_admin = is_admin
        user.balance_rub = balance
        user.platform_rules_accepted_at = datetime.now(UTC)
        user.privacy_policy_accepted_at = datetime.now(UTC)
        user.terms_accepted_at = datetime.now(UTC)
        log.info("updated user telegram_id=%s", telegram_id)
        return user

    user = User(
        telegram_id=telegram_id,
        first_name=first_name,
        username=username,
        is_admin=is_admin,
        balance_rub=balance,
        plan="free",
        referral_code=f"E2E{telegram_id}",
        platform_rules_accepted_at=datetime.now(UTC),
        privacy_policy_accepted_at=datetime.now(UTC),
        terms_accepted_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()
    log.info("created user telegram_id=%s id=%s", telegram_id, user.id)
    return user


async def _upsert_channel(session, owner: User) -> TelegramChat:
    q = await session.execute(select(TelegramChat).where(TelegramChat.username == "e2e_test_channel"))
    chat = q.scalar_one_or_none()
    if chat:
        chat.owner_id = owner.id
        log.info("updated channel @e2e_test_channel")
        return chat

    chat = TelegramChat(
        telegram_id=-1009001002001,
        username="e2e_test_channel",
        title="E2E Test Channel",
        member_count=1000,
        topic="IT",
        owner_id=owner.id,
    )
    session.add(chat)
    await session.flush()
    log.info("created channel @e2e_test_channel id=%s", chat.id)
    return chat


async def _upsert_placement(
    session,
    *,
    advertiser: User,
    owner: User,
    channel: TelegramChat,
    status: PlacementStatus,
    price: Decimal,
) -> PlacementRequest:
    q = await session.execute(
        select(PlacementRequest).where(
            PlacementRequest.advertiser_id == advertiser.id,
            PlacementRequest.channel_id == channel.id,
            PlacementRequest.status == status,
        )
    )
    existing = q.scalar_one_or_none()
    if existing:
        log.info("placement already exists status=%s id=%s", status.value, existing.id)
        return existing

    now = datetime.now(UTC)
    placement = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        ad_text=f"E2E test ad placeholder — status={status.value}",
        proposed_price=price,
        status=status,
        publication_format=PublicationFormat.post_24h,
        proposed_schedule=now + timedelta(days=1),
    )
    if status == PlacementStatus.published:
        placement.final_price = price
        placement.final_schedule = now + timedelta(days=1)
        placement.published_at = now
    session.add(placement)
    await session.flush()
    log.info("created placement status=%s id=%s", status.value, placement.id)
    return placement


async def main() -> None:
    async with async_session_factory() as session:
        advertiser = await _upsert_user(
            session,
            telegram_id=ADVERTISER_TG,
            first_name="E2E Advertiser",
            username="e2e_advertiser",
            balance=Decimal("5000.00"),
        )
        owner = await _upsert_user(
            session,
            telegram_id=OWNER_TG,
            first_name="E2E Owner",
            username="e2e_owner",
        )
        await _upsert_user(
            session,
            telegram_id=ADMIN_TG,
            first_name="E2E Admin",
            username="e2e_admin",
            is_admin=True,
        )
        channel = await _upsert_channel(session, owner)
        await _upsert_placement(
            session,
            advertiser=advertiser,
            owner=owner,
            channel=channel,
            status=PlacementStatus.pending_owner,
            price=Decimal("1000.00"),
        )
        await _upsert_placement(
            session,
            advertiser=advertiser,
            owner=owner,
            channel=channel,
            status=PlacementStatus.published,
            price=Decimal("1500.00"),
        )
        await session.commit()
    log.info("seed complete")


if __name__ == "__main__":
    asyncio.run(main())
