"""Bot lifecycle helpers for Celery workers.

Two flavours of access, deliberately separated:

1. `get_bot()` — long-lived singleton created in worker_process_init and
   closed in worker_process_shutdown. Safe ONLY when the worker has a
   persistent event loop (not the case for Celery prefork + asyncio.run).

2. `ephemeral_bot()` — async context manager that creates a fresh Bot
   bound to the current event loop and closes it on exit. REQUIRED for
   sync Celery tasks that use `asyncio.run(...)`: every call spins up a
   new loop, and aiogram's aiohttp session is loop-bound — reusing the
   singleton across loops raises `RuntimeError('Event loop is closed')`.

Rule of thumb:
 - `asyncio.run(...)` task → `async with ephemeral_bot() as bot: ...`
 - long-lived polling loop (bot/main.py) → `get_bot()`
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot

from src.bot.session_factory import new_bot

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def init_bot() -> None:
    """Create the process-level Bot instance. Idempotent."""
    global _bot
    if _bot is not None:
        return
    _bot = new_bot()
    logger.info("Bot initialized for worker PID=%s", os.getpid())


def get_bot() -> Bot:
    """Return the shared Bot instance, initializing it if needed.

    WARNING: unsafe for use inside `asyncio.run(...)`. Use
    `ephemeral_bot()` from sync Celery tasks to avoid loop-bound
    aiohttp sessions surviving across loops.
    """
    global _bot
    if _bot is None:
        init_bot()
    return _bot  # type: ignore[return-value]


@asynccontextmanager
async def ephemeral_bot() -> AsyncIterator[Bot]:
    """Short-lived Bot tied to the current event loop.

    Use from any coroutine run via `asyncio.run(...)` — e.g. a Celery
    sync task body that wraps async work. The Bot is created inside
    this loop and guaranteed to be closed before the loop exits, so
    the aiohttp session never leaks into a subsequent invocation.
    """
    bot = new_bot()
    try:
        yield bot
    finally:
        await bot.session.close()


async def close_bot() -> None:
    """Close the Bot session. Called from worker_process_shutdown hook."""
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None
        logger.info("Bot session closed for worker PID=%s", os.getpid())
