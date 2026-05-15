"""BL-107 Phase B.8 / BL-002 — bot factory base URL routing tests.

Verifies both Telegram SDKs honor `settings.telegram_api_base_url`:
 - aiogram: AiohttpSession.api becomes a TelegramAPIServer pointed at the URL
 - python-telegram-bot: Bot.base_url is rewritten to <override>/bot
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

import src.api.dependencies as api_deps
from src.bot.session_factory import new_bot

# ─── aiogram routing ──────────────────────────────────────────────────────


def test_aiogram_new_bot_default_session_when_no_override(monkeypatch):
    monkeypatch.setattr("src.bot.session_factory.settings.telegram_api_base_url", None)
    monkeypatch.setattr("src.bot.session_factory.settings.telegram_proxy", None)

    bot = new_bot(token="123:abc")
    # No custom session means aiogram constructs a default one with the
    # standard PRODUCTION api server.
    assert bot.session.api.base.startswith("https://api.telegram.org")


def test_aiogram_new_bot_routes_through_override_url(monkeypatch):
    monkeypatch.setattr(
        "src.bot.session_factory.settings.telegram_api_base_url",
        "http://telegram-stub:8081",
    )
    monkeypatch.setattr("src.bot.session_factory.settings.telegram_proxy", None)

    bot = new_bot(token="123:abc")
    session = bot.session
    assert isinstance(session, AiohttpSession)
    # Compare against the canonical TelegramAPIServer-derived URL.
    expected = TelegramAPIServer.from_base("http://telegram-stub:8081")
    assert session.api.base == expected.base
    assert "telegram-stub" in session.api.base


def test_aiogram_new_bot_combines_proxy_and_base_url(monkeypatch):
    monkeypatch.setattr(
        "src.bot.session_factory.settings.telegram_api_base_url",
        "http://telegram-stub:8081",
    )
    monkeypatch.setattr(
        "src.bot.session_factory.settings.telegram_proxy",
        "socks5://localhost:1080",
    )

    bot = new_bot(token="123:abc")
    session = bot.session
    assert isinstance(session, AiohttpSession)
    assert "telegram-stub" in session.api.base
    assert session.proxy == "socks5://localhost:1080"


# ─── python-telegram-bot routing ──────────────────────────────────────────


async def test_ptb_get_bot_default_base_url_when_no_override(monkeypatch):
    """python-telegram-bot's Bot.base_url is `<base>/bot<TOKEN>` — the library
    concatenates the token onto whatever base we pass. We assert on the prefix
    only, which is what our code controls."""
    monkeypatch.setattr(api_deps, "_bot_instance", None)
    monkeypatch.setattr("src.api.dependencies.settings.telegram_api_base_url", None)
    monkeypatch.setattr("src.api.dependencies.settings.telegram_proxy", None)

    with patch.object(api_deps.Bot, "initialize", new=AsyncMock(return_value=None)):
        bot = await api_deps.get_bot()

    assert bot.base_url.startswith("https://api.telegram.org/bot")
    assert bot.base_file_url.startswith("https://api.telegram.org/file/bot")


async def test_ptb_get_bot_rewrites_base_url_when_override_set(monkeypatch):
    monkeypatch.setattr(api_deps, "_bot_instance", None)
    monkeypatch.setattr(
        "src.api.dependencies.settings.telegram_api_base_url",
        "http://telegram-stub:8081",
    )
    monkeypatch.setattr("src.api.dependencies.settings.telegram_proxy", None)

    with patch.object(api_deps.Bot, "initialize", new=AsyncMock(return_value=None)):
        bot = await api_deps.get_bot()

    assert bot.base_url.startswith("http://telegram-stub:8081/bot")
    assert bot.base_file_url.startswith("http://telegram-stub:8081/file/bot")
    # api.telegram.org must NOT appear when override is active.
    assert "api.telegram.org" not in bot.base_url
    assert "api.telegram.org" not in bot.base_file_url


async def test_ptb_get_bot_trailing_slash_normalised(monkeypatch):
    monkeypatch.setattr(api_deps, "_bot_instance", None)
    monkeypatch.setattr(
        "src.api.dependencies.settings.telegram_api_base_url",
        "http://telegram-stub:8081/",
    )
    monkeypatch.setattr("src.api.dependencies.settings.telegram_proxy", None)

    with patch.object(api_deps.Bot, "initialize", new=AsyncMock(return_value=None)):
        bot = await api_deps.get_bot()

    # No double-slash after stripping trailing "/" — prefix is `<host>:<port>/bot<TOKEN>`.
    assert bot.base_url.startswith("http://telegram-stub:8081/bot")
    assert "/bot/" not in bot.base_url
    assert "//bot" not in bot.base_url.replace("http://", "")


@pytest.fixture(autouse=True)
def _reset_ptb_singleton():
    """Ensure the python-telegram-bot singleton is reset around each test."""
    api_deps._bot_instance = None
    yield
    api_deps._bot_instance = None
