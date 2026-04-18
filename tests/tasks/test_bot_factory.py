"""Tests for src/tasks/_bot_factory.py singleton Bot factory."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# ─── helpers ───────────────────────────────────────────────────────────────────


def _reset_factory() -> None:
    """Reset the module-level _bot singleton between tests."""
    import src.tasks._bot_factory as factory
    factory._bot = None


# ─── tests ─────────────────────────────────────────────────────────────────────


class TestGetBotSingleton:
    def setup_method(self):
        _reset_factory()

    def teardown_method(self):
        _reset_factory()

    def test_get_bot_returns_singleton(self):
        """Two calls to get_bot() must return the same object."""
        with patch("src.tasks._bot_factory.Bot") as mock_bot:
            mock_instance = MagicMock()
            mock_bot.return_value = mock_instance

            from src.tasks._bot_factory import get_bot
            first = get_bot()
            second = get_bot()

            assert first is second
            assert mock_bot.call_count == 1

    def test_init_bot_idempotent(self):
        """Calling init_bot() twice must not create a second Bot."""
        with patch("src.tasks._bot_factory.Bot") as mock_bot:
            mock_instance = MagicMock()
            mock_bot.return_value = mock_instance

            from src.tasks._bot_factory import init_bot
            init_bot()
            init_bot()

            assert mock_bot.call_count == 1

    def test_close_bot_clears_instance(self):
        """After close_bot(), get_bot() must create a fresh instance."""
        with patch("src.tasks._bot_factory.Bot") as mock_bot:
            mock_instance = MagicMock()
            mock_instance.session = MagicMock()
            mock_instance.session.close = AsyncMock()
            mock_bot.return_value = mock_instance

            from src.tasks._bot_factory import close_bot, get_bot, init_bot

            init_bot()
            asyncio.run(close_bot())

            # After close, _bot is None
            import src.tasks._bot_factory as factory
            assert factory._bot is None

            # get_bot() creates a new instance
            get_bot()
            assert mock_bot.call_count == 2

    def test_get_bot_initializes_if_none(self):
        """get_bot() with no prior init_bot() call must still return a Bot."""
        with patch("src.tasks._bot_factory.Bot") as mock_bot:
            mock_instance = MagicMock()
            mock_bot.return_value = mock_instance

            from src.tasks._bot_factory import get_bot
            result = get_bot()

            assert result is mock_instance
            assert mock_bot.call_count == 1
