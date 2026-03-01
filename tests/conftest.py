"""
Конфигурация и фикстуры для тестов.
"""

import asyncio
from collections.abc import AsyncGenerator
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
from src.db.base import Base

# ────────────────────────────────────────────
# Event loop fixtures
# ────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.DefaultEventLoopPolicy:
    """Использовать asyncio для всей сессии."""
    return asyncio.DefaultEventLoopPolicy()


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
