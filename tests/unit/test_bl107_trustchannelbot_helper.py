"""BL-107 Phase B.3 — Trustchannelbot verification helper tests.

Pure unit tests с AsyncMock(spec=TelegramAdminLister). No live Telegram API.

Covers:
* ``resolve_trustchannelbot_id`` env override / cache hit / cache miss / API failure / concurrent
* ``verify_trustchannelbot_admin`` admin found / not found / empty list / malformed admin / exception propagation
* ``TrustchannelbotResolutionError`` raised на API failure
* ``_reset_cache_for_testing`` clears module cache
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.settings import settings
from src.utils.telegram import verify_blogger_registry as vbr
from src.utils.telegram.verify_blogger_registry import (
    TelegramAdminLister,
    TrustchannelbotResolutionError,
    _reset_cache_for_testing,
    resolve_trustchannelbot_id,
    verify_trustchannelbot_admin,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear module cache между tests so each test sees clean state."""
    _reset_cache_for_testing()
    yield
    _reset_cache_for_testing()


def _make_admin(user_id: int) -> Any:
    """Build a ChatMember-shaped mock с .user.id attribute."""
    admin = MagicMock()
    admin.user.id = user_id
    return admin


# ─── resolve_trustchannelbot_id ────────────────────────────────────────────


class TestResolveTrustchannelbotId:
    @pytest.mark.asyncio
    async def test_env_override_returns_directly_no_bot_call(self, monkeypatch):
        """settings.rkn_trustchannelbot_id set → no bot.get_chat call."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", 7654321)
        bot = AsyncMock(spec=TelegramAdminLister)

        result = await resolve_trustchannelbot_id(bot)

        assert result == 7654321
        bot.get_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_bot_and_caches(self, monkeypatch):
        """Cache miss → bot.get_chat → cached → second call no bot."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", None)
        bot = AsyncMock(spec=TelegramAdminLister)
        chat = MagicMock()
        chat.id = 1111111
        bot.get_chat.return_value = chat

        first = await resolve_trustchannelbot_id(bot)
        second = await resolve_trustchannelbot_id(bot)

        assert first == 1111111
        assert second == 1111111
        bot.get_chat.assert_called_once_with(settings.rkn_trustchannelbot_username)

    @pytest.mark.asyncio
    async def test_api_failure_raises_resolution_error(self, monkeypatch):
        """bot.get_chat raises → TrustchannelbotResolutionError, cache empty."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", None)
        bot = AsyncMock(spec=TelegramAdminLister)
        bot.get_chat.side_effect = RuntimeError("Telegram API timeout")

        with pytest.raises(TrustchannelbotResolutionError) as exc_info:
            await resolve_trustchannelbot_id(bot)

        assert "Cannot resolve" in str(exc_info.value)
        assert vbr._TRUSTCHANNELBOT_ID_CACHE is None

    @pytest.mark.asyncio
    async def test_concurrent_calls_dedupe_via_lock(self, monkeypatch):
        """N parallel cache-miss callers → only 1 bot.get_chat invocation."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", None)
        bot = AsyncMock(spec=TelegramAdminLister)
        chat = MagicMock()
        chat.id = 2222222

        async def slow_get_chat(_username):
            await asyncio.sleep(0.01)
            return chat

        bot.get_chat.side_effect = slow_get_chat

        results = await asyncio.gather(*(resolve_trustchannelbot_id(bot) for _ in range(10)))

        assert all(r == 2222222 for r in results)
        assert bot.get_chat.call_count == 1


# ─── verify_trustchannelbot_admin ──────────────────────────────────────────


class TestVerifyTrustchannelbotAdmin:
    @pytest.mark.asyncio
    async def test_returns_true_when_trustchannelbot_in_admins(self, monkeypatch):
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", 999)
        bot = AsyncMock(spec=TelegramAdminLister)
        bot.get_chat_administrators.return_value = [
            _make_admin(100),
            _make_admin(999),
            _make_admin(200),
        ]

        result = await verify_trustchannelbot_admin(bot, -1001234567)

        assert result is True
        bot.get_chat_administrators.assert_called_once_with(-1001234567)

    @pytest.mark.asyncio
    async def test_returns_false_when_trustchannelbot_not_in_admins(self, monkeypatch):
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", 999)
        bot = AsyncMock(spec=TelegramAdminLister)
        bot.get_chat_administrators.return_value = [
            _make_admin(100),
            _make_admin(200),
            _make_admin(300),
        ]

        result = await verify_trustchannelbot_admin(bot, -1001234567)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_empty_admin_list(self, monkeypatch):
        """Empty admins (channel deleted / bot has no permission) → False, no raise."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", 999)
        bot = AsyncMock(spec=TelegramAdminLister)
        bot.get_chat_administrators.return_value = []

        result = await verify_trustchannelbot_admin(bot, -1001234567)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_admin_missing_user_attribute(self, monkeypatch):
        """Admin object без .user attribute → skip safely (no AttributeError)."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", 999)
        bot = AsyncMock(spec=TelegramAdminLister)
        # Use a simple object без .user attribute — getattr returns None default
        admin_no_user = type("AdminNoUser", (), {})()
        bot.get_chat_administrators.return_value = [admin_no_user]

        result = await verify_trustchannelbot_admin(bot, -1001234567)

        assert result is False

    @pytest.mark.asyncio
    async def test_propagates_resolution_error(self, monkeypatch):
        """resolve_trustchannelbot_id failure → TrustchannelbotResolutionError propagates."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", None)
        bot = AsyncMock(spec=TelegramAdminLister)
        bot.get_chat.side_effect = RuntimeError("API down")

        with pytest.raises(TrustchannelbotResolutionError):
            await verify_trustchannelbot_admin(bot, -1001234567)

        bot.get_chat_administrators.assert_not_called()

    @pytest.mark.asyncio
    async def test_propagates_get_admins_exception(self, monkeypatch):
        """get_chat_administrators exception propagates (not wrapped)."""
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", 999)
        bot = AsyncMock(spec=TelegramAdminLister)
        bot.get_chat_administrators.side_effect = RuntimeError("Chat not found")

        with pytest.raises(RuntimeError, match="Chat not found"):
            await verify_trustchannelbot_admin(bot, -1001234567)


# ─── Cache reset helper ────────────────────────────────────────────────────


class TestResetCacheHelper:
    @pytest.mark.asyncio
    async def test_reset_clears_cache(self, monkeypatch):
        monkeypatch.setattr(settings, "rkn_trustchannelbot_id", None)
        bot = AsyncMock(spec=TelegramAdminLister)
        chat = MagicMock()
        chat.id = 5555555
        bot.get_chat.return_value = chat

        await resolve_trustchannelbot_id(bot)
        assert vbr._TRUSTCHANNELBOT_ID_CACHE == 5555555

        _reset_cache_for_testing()
        assert vbr._TRUSTCHANNELBOT_ID_CACHE is None

        # Next call re-fetches
        chat2 = MagicMock()
        chat2.id = 6666666
        bot.get_chat.return_value = chat2
        result = await resolve_trustchannelbot_id(bot)
        assert result == 6666666
        assert bot.get_chat.call_count == 2
