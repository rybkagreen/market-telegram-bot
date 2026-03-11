"""
Конфигурация и фикстуры для тестов.
"""

import asyncio
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import settings
from src.core.services.placement_request_service import PlacementRequestService
from src.core.services.reputation_service import ReputationService
from src.db.base import Base
from src.db.models.analytics import TelegramChat
from src.db.models.campaign import Campaign
from src.db.models.user import User
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo

# ────────────────────────────────────────────
# Event loop fixtures
# ────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.DefaultEventLoopPolicy:
    """Использовать asyncio для всей сессии."""
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
def event_loop(request: pytest.FixtureRequest) -> asyncio.AbstractEventLoop:
    """
    Create an instance of the event loop for the test session.

    This fixture has session scope to match test_engine scope.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ────────────────────────────────────────────
# Database fixtures
# ────────────────────────────────────────────


@pytest.fixture(scope="session")
def postgres_container() -> Any:
    """
    Создать PostgreSQL контейнер для тестов.

    Yields:
        PostgresContainer: Контейнер PostgreSQL.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> Any:
    """Движок для тестовой БД."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: Any) -> AsyncGenerator[AsyncSession]:
    """Сессия БД с автоматическим rollback после каждого теста."""
    async_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


# ────────────────────────────────────────────
# In-memory SQLite fixtures for unit tests
# ────────────────────────────────────────────


@pytest_asyncio.fixture
async def sqlite_engine() -> Any:
    """In-memory SQLite движок для unit-тестов."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def sqlite_session(sqlite_engine: Any) -> AsyncGenerator[AsyncSession]:
    """Сессия SQLite с автоматическим rollback."""
    async_session = async_sessionmaker(
        sqlite_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


# ────────────────────────────────────────────
# Redis fixture
# ────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Redis:
    """Redis клиент на тестовой БД (индекс 2)."""
    client = Redis.from_url("redis://localhost:6379/2", decode_responses=True)
    yield client
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def mock_redis() -> Any:
    """
    Мок Redis клиента для unit-тестов.

    Returns:
        MagicMock: Мок клиента.
    """
    from unittest.mock import AsyncMock, MagicMock

    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=None)
    redis_client.setex = AsyncMock()
    return redis_client


# ────────────────────────────────────────────
# API client fixture
# ────────────────────────────────────────────


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient]:
    """HTTP клиент для тестирования FastAPI."""
    from src.api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ────────────────────────────────────────────
# Bot mocks
# ────────────────────────────────────────────


@pytest.fixture
def mock_bot() -> Any:
    """
    Мок aiogram Bot.

    Returns:
        MagicMock: Мок бота.
    """
    from unittest.mock import AsyncMock, MagicMock

    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.session = AsyncMock()
    bot.session.close = AsyncMock()
    return bot


@pytest.fixture
def mock_anthropic_client() -> Any:
    """
    Мок Anthropic клиента.

    Returns:
        MagicMock: Мок клиента.
    """
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock()
    return client


@pytest.fixture
def mock_openai_client() -> Any:
    """
    Мок OpenAI клиента.

    Returns:
        MagicMock: Мок клиента.
    """
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client


# ────────────────────────────────────────────
# AI Service fixtures
# ────────────────────────────────────────────


@pytest.fixture
def mock_ai_service() -> Any:
    """
    Мок AI Service для тестов.

    Returns:
        MagicMock: Мок сервиса.
    """
    from unittest.mock import AsyncMock, MagicMock

    service = MagicMock()
    service.generate_ad_text = AsyncMock(return_value="Generated ad text")
    service.generate_ab_variants = AsyncMock(return_value=["Variant 1", "Variant 2"])
    service.improve_text = AsyncMock(return_value="Improved text")
    service.generate_hashtags = AsyncMock(return_value=["#tag1", "#tag2"])
    return service


# ────────────────────────────────────────────
# Test data helpers
# ────────────────────────────────────────────


@pytest.fixture
def user_test_data() -> dict[str, Any]:
    """Тестовые данные для пользователя."""
    return {
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "ru",
    }


@pytest.fixture
def campaign_test_data() -> dict[str, Any]:
    """Тестовые данные для кампании."""
    return {
        "title": "Test Campaign",
        "text": "Test ad text for campaign",
        "ai_description": "AI generated description",
        "filters_json": {"topics": ["business"], "min_members": 1000},
    }


@pytest.fixture
def chat_test_data() -> dict[str, Any]:
    """Тестовые данные для чата."""
    return {
        "telegram_id": -1001234567890,
        "title": "Test Channel",
        "username": "test_channel",
        "member_count": 5000,
        "topic": "business",
    }


# =============================================================================
# FIXTURES ДЛЯ PLACEMENT/ARBITRATION/REPUTATION ТЕСТОВ
# =============================================================================


@pytest.fixture
def advertiser_test_data() -> dict[str, Any]:
    """Тестовые данные для рекламодателя."""
    return {
        "telegram_id": 111111111,
        "username": "advertiser",
        "first_name": "Advertiser",
        "role": "advertiser",
        "credits": Decimal("5000.00"),
    }


@pytest.fixture
def owner_test_data() -> dict[str, Any]:
    """Тестовые данные для владельца канала."""
    return {
        "telegram_id": 222222222,
        "username": "owner",
        "first_name": "Owner",
        "role": "owner",
        "credits": Decimal("1000.00"),
    }


@pytest.fixture
def channel_test_data() -> dict[str, Any]:
    """Тестовые данные для канала."""
    return {
        "telegram_id": -1009876543210,
        "title": "Test Channel",
        "username": "test_channel",
        "member_count": 5000,
        "is_active": True,
    }


@pytest_asyncio.fixture
async def advertiser_user(db_session: AsyncSession, advertiser_test_data: dict) -> User:
    """Создать тестового рекламодателя."""
    from src.db.models.user import User

    user = User(**advertiser_test_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession, owner_test_data: dict) -> User:
    """Создать тестового владельца."""
    from src.db.models.user import User

    user = User(**owner_test_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_channel(
    db_session: AsyncSession,
    channel_test_data: dict,
    owner_user: User,
) -> TelegramChat:
    """Создать тестовый канал."""
    from src.db.models.analytics import TelegramChat

    channel = TelegramChat(**channel_test_data, owner_user_id=owner_user.id)
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def test_campaign(db_session: AsyncSession, advertiser_user: User) -> Campaign:
    """Создать тестовую кампанию."""
    from src.db.models.campaign import Campaign, CampaignStatus

    campaign = Campaign(
        advertiser_id=advertiser_user.id,
        title="Test Campaign",
        text="Test ad text",
        status=CampaignStatus.DRAFT,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


@pytest_asyncio.fixture
async def placement_request_service(db_session: AsyncSession) -> PlacementRequestService:
    """Создать PlacementRequestService для тестов."""

    return PlacementRequestService(
        session=db_session,
        placement_repo=PlacementRequestRepo(db_session),
        channel_settings_repo=ChannelSettingsRepo(db_session),
        reputation_repo=ReputationRepo(db_session),
        billing_service=None,
    )


@pytest_asyncio.fixture
async def reputation_service(db_session: AsyncSession) -> ReputationService:
    """Создать ReputationService для тестов."""

    return ReputationService(
        session=db_session,
        reputation_repo=ReputationRepo(db_session),
    )


@pytest_asyncio.fixture
async def channel_settings_repo(db_session: AsyncSession) -> ChannelSettingsRepo:
    """Создать ChannelSettingsRepo для тестов."""

    return ChannelSettingsRepo(db_session)


@pytest_asyncio.fixture
async def placement_request_repo(db_session: AsyncSession) -> PlacementRequestRepo:
    """Создать PlacementRequestRepo для тестов."""

    return PlacementRequestRepo(db_session)


@pytest_asyncio.fixture
async def reputation_repo(db_session: AsyncSession) -> ReputationRepo:
    """Создать ReputationRepo для тестов."""

    return ReputationRepo(db_session)


@pytest_asyncio.fixture
async def api_client_with_auth(advertiser_user: User) -> AsyncGenerator[AsyncClient]:
    """HTTP клиент с авторизацией через JWT."""
    from src.api.auth_utils import create_access_token
    from src.api.main import app

    token = create_access_token(advertiser_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        yield client
