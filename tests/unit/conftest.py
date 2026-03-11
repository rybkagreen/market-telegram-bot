# tests/unit/conftest.py
"""
Unit test fixtures and mocks.
Apply mocks before any test modules are imported.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockAsyncSessionContextManager:
    """Mock async context manager for database sessions."""
    
    def __init__(self, session):
        self.session = session
    
    async def __aenter__(self):
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture(autouse=True)
def mock_async_session_factory():
    """Mock async_session_factory for all unit tests."""
    # Create the session mock - use MagicMock with AsyncMock for async methods
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.get = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    # Create context manager wrapper
    context_manager = MockAsyncSessionContextManager(mock_session)
    
    # async_session_factory() is a sync function that returns an async context manager
    def session_factory():
        return context_manager
    
    with patch("src.db.session.async_session_factory", session_factory):
        yield mock_session


@pytest.fixture(autouse=True)
def mock_send_banner():
    """Mock send_banner_with_menu for all unit tests."""
    with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
        yield
