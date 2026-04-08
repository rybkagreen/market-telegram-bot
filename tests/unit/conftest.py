# tests/unit/conftest.py
"""
Unit test fixtures and mocks.
Apply mocks before any test modules are imported.
"""

import asyncio

# Import aiogram eagerly so its uvloop.EventLoopPolicy() install happens NOW,
# before we override with DefaultEventLoopPolicy. Without this, aiogram would
# install uvloop policy inside the first fixture call, wiping the active loop.
try:
    import aiogram as _aiogram  # noqa: F401
except Exception:
    pass

# Restore standard asyncio policy so pytest-asyncio can manage event loops correctly.
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch


class MockAsyncSessionContextManager:
    """Mock async context manager for database sessions."""

    def __init__(self, session: Any) -> None:
        self.session = session

    async def __aenter__(self) -> Any:
        return self.session

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        return None


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """In-memory SQLite session — only test-relevant tables, no JSONB columns."""
    from src.db.models.channel_mediakit import ChannelMediakit  # noqa: F401
    from src.db.models.telegram_chat import TelegramChat  # noqa: F401
    from src.db.models.user import User  # noqa: F401
    from src.db.base import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    needed_tables = ["users", "telegram_chats", "channel_mediakits"]
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[Base.metadata.tables[t] for t in needed_tables],
            )
        )

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(
                sync_conn,
                tables=[Base.metadata.tables[t] for t in needed_tables],
            )
        )
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def mock_async_session_factory(db_session: AsyncSession) -> AsyncGenerator[AsyncSession]:
    """Wire async_session_factory to the test's SQLite db_session."""
    context_manager = MockAsyncSessionContextManager(db_session)

    def session_factory() -> MockAsyncSessionContextManager:
        return context_manager

    with patch("src.db.session.async_session_factory", session_factory):
        yield db_session


@pytest.fixture
def chat_test_data() -> dict[str, Any]:
    """Override: exclude member_count so tests can set it explicitly without duplicate-kwarg error."""
    return {
        "telegram_id": -1001234567890,
        "title": "Test Channel",
        "username": "test_channel",
        "topic": "business",
    }


@pytest.fixture(autouse=True)
def mock_send_banner() -> Any:
    """Mock send_banner_with_menu for all unit tests."""
    with patch("src.bot.handlers.shared.start.send_banner_with_menu", create=True):
        yield
