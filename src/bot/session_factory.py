"""Single entry point for aiogram Bot instantiation.

Per CLAUDE.md INV-3: `Bot()` is created only in this module and in
`src/tasks/_bot_factory.py` (which delegates here). Applies SOCKS5/HTTP
proxy from `settings.telegram_proxy` automatically — callers never
pass a session.
"""

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from src.config.settings import settings


def new_bot(token: str | None = None) -> Bot:
    """Return a new aiogram Bot bound to the current event loop.

    If `settings.telegram_proxy` is set, the bot uses an AiohttpSession
    routed through that proxy. Otherwise a default session is created.

    Args:
        token: Override token. Defaults to `settings.bot_token`.
    """
    kwargs: dict = {
        "token": token or settings.bot_token,
        "default": DefaultBotProperties(parse_mode=ParseMode.HTML),
    }
    if settings.telegram_proxy:
        kwargs["session"] = AiohttpSession(proxy=settings.telegram_proxy)
    return Bot(**kwargs)
