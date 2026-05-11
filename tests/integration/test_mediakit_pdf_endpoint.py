"""Integration tests for GET /api/channels/{channel_id}/mediakit/pdf (BL-078 B.3)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.main import app
from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession) -> User:
    user = User(telegram_id=8000000001, username="pdf_owner", first_name="Owner")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(telegram_id=8000000002, username="pdf_other", first_name="Other")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def channel(db_session: AsyncSession, owner_user: User) -> TelegramChat:
    chat = TelegramChat(
        telegram_id=-1009000000001,
        username="pdf_channel",
        title="PDF Channel",
        owner_id=owner_user.id,
        member_count=5000,
        avg_views=300,
        last_er=0.06,
    )
    db_session.add(chat)
    await db_session.flush()
    await db_session.refresh(chat)
    mediakit = ChannelMediakit(
        channel_id=chat.id,
        owner_user_id=owner_user.id,
    )
    db_session.add(mediakit)
    await db_session.flush()
    return chat


def _build_authed_client_factory(db_session: AsyncSession):
    """Return a factory that yields an AsyncClient authenticated as a given user."""

    async def _factory(as_user: User | None) -> AsyncGenerator[AsyncClient]:
        async def _session_override() -> AsyncGenerator[AsyncSession]:
            try:
                yield db_session
            except Exception:
                await db_session.rollback()
                raise

        async def _user_override() -> User:
            assert as_user is not None
            return as_user

        app.dependency_overrides[get_db_session] = _session_override
        if as_user is not None:
            app.dependency_overrides[get_current_user] = _user_override
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client
        finally:
            app.dependency_overrides.pop(get_db_session, None)
            app.dependency_overrides.pop(get_current_user, None)

    return _factory


@pytest_asyncio.fixture
async def owner_client(db_session: AsyncSession, owner_user: User) -> AsyncGenerator[AsyncClient]:
    factory = _build_authed_client_factory(db_session)
    async for client in factory(owner_user):
        yield client


@pytest_asyncio.fixture
async def other_client(db_session: AsyncSession, other_user: User) -> AsyncGenerator[AsyncClient]:
    factory = _build_authed_client_factory(db_session)
    async for client in factory(other_user):
        yield client


@pytest_asyncio.fixture
async def anon_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def _session_override() -> AsyncGenerator[AsyncSession]:
        try:
            yield db_session
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = _session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


async def test_mediakit_pdf_unauthenticated_rejected(
    anon_client: AsyncClient, channel: TelegramChat
) -> None:
    r = await anon_client.get(f"/api/channels/{channel.id}/mediakit/pdf")
    assert r.status_code in (401, 403), r.text


async def test_mediakit_pdf_non_owner_returns_403(
    other_client: AsyncClient, channel: TelegramChat
) -> None:
    r = await other_client.get(f"/api/channels/{channel.id}/mediakit/pdf")
    assert r.status_code == 403, r.text
    assert "Not channel owner" in r.text


async def test_mediakit_pdf_owner_returns_pdf_200(
    owner_client: AsyncClient, channel: TelegramChat
) -> None:
    r = await owner_client.get(f"/api/channels/{channel.id}/mediakit/pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    disposition = r.headers["content-disposition"]
    assert "attachment" in disposition
    assert f"mediakit_{channel.id}.pdf" in disposition


async def test_mediakit_pdf_owner_response_body_nonempty(
    owner_client: AsyncClient, channel: TelegramChat
) -> None:
    r = await owner_client.get(f"/api/channels/{channel.id}/mediakit/pdf")
    assert r.status_code == 200
    body = r.content
    assert len(body) > 0
    assert body.startswith(b"%PDF")


async def test_mediakit_pdf_owner_increments_counters(
    owner_client: AsyncClient,
    channel: TelegramChat,
    db_session: AsyncSession,
) -> None:
    r = await owner_client.get(f"/api/channels/{channel.id}/mediakit/pdf")
    assert r.status_code == 200

    result = await db_session.execute(
        select(ChannelMediakit).where(ChannelMediakit.channel_id == channel.id)
    )
    mediakit = result.scalar_one()
    assert mediakit.views_count == 1
    assert mediakit.downloads_count == 1

    r2 = await owner_client.get(f"/api/channels/{channel.id}/mediakit/pdf")
    assert r2.status_code == 200
    await db_session.refresh(mediakit)
    assert mediakit.views_count == 2
    assert mediakit.downloads_count == 2
