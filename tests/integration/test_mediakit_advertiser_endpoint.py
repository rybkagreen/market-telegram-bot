"""Integration tests for GET /api/channels/{channel_id}/mediakit (B.5.1).

Advertiser-readable counterpart to the B.2 owner-only PDF endpoint. Mirrors
the PDF endpoint fixture/override pattern, but exercises the JSON path and
its privacy gate (is_published=False → 404, не 403).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.main import app
from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession) -> User:
    user = User(telegram_id=8100000001, username="adv_owner", first_name="Owner")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def advertiser_user(db_session: AsyncSession) -> User:
    user = User(telegram_id=8100000002, username="adv_user", first_name="Advertiser")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def channel_with_published_mediakit(
    db_session: AsyncSession, owner_user: User
) -> tuple[TelegramChat, ChannelMediakit]:
    chat = TelegramChat(
        telegram_id=-1009100000001,
        username="adv_pub_channel",
        title="Published Channel",
        owner_id=owner_user.id,
        member_count=4000,
        avg_views=250,
        last_er=0.05,
    )
    db_session.add(chat)
    await db_session.flush()
    await db_session.refresh(chat)
    mediakit = ChannelMediakit(
        channel_id=chat.id,
        owner_user_id=owner_user.id,
        description="Канал про IT",
        audience_description="Backend-разработчики 25-40",
        logo_file_id="AgACAgIAAxkBAAIPub",
        theme_color="#1a73e8",
        avg_post_reach=320,
        is_published=True,
    )
    db_session.add(mediakit)
    await db_session.flush()
    await db_session.refresh(mediakit)
    return chat, mediakit


@pytest_asyncio.fixture
async def channel_with_unpublished_mediakit(
    db_session: AsyncSession, owner_user: User
) -> tuple[TelegramChat, ChannelMediakit]:
    chat = TelegramChat(
        telegram_id=-1009100000002,
        username="adv_draft_channel",
        title="Draft Channel",
        owner_id=owner_user.id,
        member_count=1000,
    )
    db_session.add(chat)
    await db_session.flush()
    await db_session.refresh(chat)
    mediakit = ChannelMediakit(
        channel_id=chat.id,
        owner_user_id=owner_user.id,
        description="Не опубликовано",
        is_published=False,
    )
    db_session.add(mediakit)
    await db_session.flush()
    await db_session.refresh(mediakit)
    return chat, mediakit


@pytest_asyncio.fixture
async def channel_without_mediakit(db_session: AsyncSession, owner_user: User) -> TelegramChat:
    chat = TelegramChat(
        telegram_id=-1009100000003,
        username="adv_bare_channel",
        title="Bare Channel",
        owner_id=owner_user.id,
        member_count=500,
    )
    db_session.add(chat)
    await db_session.flush()
    await db_session.refresh(chat)
    return chat


def _build_authed_client_factory(db_session: AsyncSession):
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
async def advertiser_client(
    db_session: AsyncSession, advertiser_user: User
) -> AsyncGenerator[AsyncClient]:
    factory = _build_authed_client_factory(db_session)
    async for client in factory(advertiser_user):
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


async def test_published_mediakit_returns_200_with_advertiser_fields(
    advertiser_client: AsyncClient,
    channel_with_published_mediakit: tuple[TelegramChat, ChannelMediakit],
) -> None:
    chat, mediakit = channel_with_published_mediakit
    r = await advertiser_client.get(f"/api/channels/{chat.id}/mediakit")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["description"] == mediakit.description
    assert data["audience_description"] == mediakit.audience_description
    assert data["logo_file_id"] == mediakit.logo_file_id
    assert data["theme_color"] == mediakit.theme_color
    assert data["avg_post_reach"] == mediakit.avg_post_reach
    assert "updated_at" in data
    # leak prevention
    assert "is_published" not in data
    assert "owner_user_id" not in data
    assert "views_count" not in data
    assert "downloads_count" not in data


async def test_unpublished_mediakit_returns_404(
    advertiser_client: AsyncClient,
    channel_with_unpublished_mediakit: tuple[TelegramChat, ChannelMediakit],
) -> None:
    chat, _ = channel_with_unpublished_mediakit
    r = await advertiser_client.get(f"/api/channels/{chat.id}/mediakit")
    assert r.status_code == 404, r.text


async def test_nonexistent_channel_returns_404(
    advertiser_client: AsyncClient,
) -> None:
    r = await advertiser_client.get("/api/channels/999999/mediakit")
    assert r.status_code == 404, r.text


async def test_channel_without_mediakit_returns_404(
    advertiser_client: AsyncClient,
    channel_without_mediakit: TelegramChat,
) -> None:
    r = await advertiser_client.get(f"/api/channels/{channel_without_mediakit.id}/mediakit")
    assert r.status_code == 404, r.text


async def test_unauthenticated_rejected(
    anon_client: AsyncClient,
    channel_with_published_mediakit: tuple[TelegramChat, ChannelMediakit],
) -> None:
    chat, _ = channel_with_published_mediakit
    r = await anon_client.get(f"/api/channels/{chat.id}/mediakit")
    assert r.status_code in (401, 403), r.text
