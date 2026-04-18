"""Bot singleton factory for Celery workers.

One Bot instance per worker process, created on worker_process_init
and closed on worker_process_shutdown via Celery lifecycle hooks in celery_app.py.
All tasks obtain the instance via get_bot(); they must NOT close the session.
"""

import logging
import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config.settings import settings

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def init_bot() -> None:
    """Create the process-level Bot instance. Idempotent."""
    global _bot
    if _bot is not None:
        return
    _bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.info("Bot initialized for worker PID=%s", os.getpid())


def get_bot() -> Bot:
    """Return the shared Bot instance, initializing it if needed."""
    global _bot
    if _bot is None:
        init_bot()
    return _bot  # type: ignore[return-value]


async def close_bot() -> None:
    """Close the Bot session. Called from worker_process_shutdown hook."""
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None
        logger.info("Bot session closed for worker PID=%s", os.getpid())
