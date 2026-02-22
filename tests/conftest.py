"""
Конфигурация и фикстуры для тестов.
"""

import asyncio
from typing import Any, Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Создать event loop для сессии тестов.

    Yields:
        asyncio.AbstractEventLoop: Event loop.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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


@pytest.fixture
def mock_redis() -> Any:
    """
    Мок Redis клиента.

    Returns:
        MagicMock: Мок клиента.
    """
    from unittest.mock import AsyncMock, MagicMock

    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=None)
    redis_client.setex = AsyncMock()
    return redis_client
