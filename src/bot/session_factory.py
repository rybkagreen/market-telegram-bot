"""Single entry point for aiogram Bot instantiation.

Per CLAUDE.md INV-3: `Bot()` is created only in this module and in
`src/tasks/_bot_factory.py` (which delegates here). Applies SOCKS5/HTTP
proxy from `settings.telegram_proxy` automatically — callers never
pass a session.

BL-107 Phase B.8 / BL-002 — if `settings.telegram_api_base_url` is set, the
session is built against that base URL via TelegramAPIServer instead of
api.telegram.org. Production guard against this is enforced at startup by
Settings._validate_telegram_api_base_url; this factory trusts the setting.
"""

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode

from src.config.settings import settings


def new_bot(token: str | None = None) -> Bot:
    """Return a new aiogram Bot bound to the current event loop.

    If `settings.telegram_proxy` is set, the bot uses an AiohttpSession
    routed through that proxy. If `settings.telegram_api_base_url` is set
    (test infrastructure), the session targets that base URL instead of
    api.telegram.org. Both options compose: proxy + base_url are honored
    together for advanced test setups.

    Args:
        token: Override token. Defaults to `settings.bot_token`.
    """
    kwargs: dict = {
        "token": token or settings.bot_token,
        "default": DefaultBotProperties(parse_mode=ParseMode.HTML),
    }

    session_kwargs: dict = {}
    if settings.telegram_proxy:
        session_kwargs["proxy"] = settings.telegram_proxy
    if settings.telegram_api_base_url:
        session_kwargs["api"] = TelegramAPIServer.from_base(settings.telegram_api_base_url)

    if session_kwargs:
        kwargs["session"] = AiohttpSession(**session_kwargs)

    return Bot(**kwargs)
