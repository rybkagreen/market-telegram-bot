"""Main bot entry point."""

import asyncio
import logging

import sentry_sdk
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo
from sentry_sdk.integrations.asyncio import AsyncioIntegration

from src.bot.handlers import main_router
from src.bot.middlewares.db_session import DBSessionMiddleware
from src.bot.middlewares.fsm_timeout import FSMTimeoutMiddleware
from src.bot.middlewares.role_check import RoleCheckMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.config.settings import settings

logger = logging.getLogger(__name__)

BOT_STARTUP_MAX_RETRIES = 5
BOT_STARTUP_BACKOFF = 3  # seconds: 3, 6, 12, 24, 48

# Module-level bot instance for access from services/handlers
bot: Bot | None = None

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=0.05,
        integrations=[AsyncioIntegration()],
        send_default_pii=False,
        shutdown_timeout=2,  # Don't block on exit
        debug=False,  # Disable verbose retry logging in production
    )


async def _create_bot() -> Bot:
    """Create Bot with proxy if configured."""
    if settings.telegram_proxy:
        from aiogram.client.session.aiohttp import AiohttpSession

        session = AiohttpSession(proxy=settings.telegram_proxy)
        return Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            session=session,
        )
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def main() -> None:
    """Запуск бота с retry логикой."""
    global bot
    bot = await _create_bot()

    storage = RedisStorage.from_url(str(settings.redis_url))
    dp = Dispatcher(storage=storage)

    dp.update.middleware(DBSessionMiddleware())
    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(RoleCheckMiddleware())
    dp.update.middleware(FSMTimeoutMiddleware())

    dp.include_router(main_router)

    # ─── Startup with retry ───────────────────────────────────────
    for attempt in range(1, BOT_STARTUP_MAX_RETRIES + 1):
        try:
            me = await bot.get_me()
            logger.info("Bot authenticated: @%s", me.username)

            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url="https://app.rekharbor.ru/"),
                )
            )
            logger.info("Menu button set")
            break
        except TelegramNetworkError as e:
            if attempt == BOT_STARTUP_MAX_RETRIES:
                logger.critical(
                    "Failed to connect to Telegram API after %d attempts: %s",
                    BOT_STARTUP_MAX_RETRIES,
                    e,
                )
                raise
            delay = BOT_STARTUP_BACKOFF * (2 ** (attempt - 1))
            logger.warning(
                "Telegram API unavailable (attempt %d/%d), retrying in %ds: %s",
                attempt,
                BOT_STARTUP_MAX_RETRIES,
                delay,
                e,
            )
            await asyncio.sleep(delay)

    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(main())
