"""Main bot entry point."""

import asyncio
import logging

import sentry_sdk
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo  # добавлено
from sentry_sdk.integrations.asyncio import AsyncioIntegration

from src.bot.handlers import main_router
from src.bot.middlewares.db_session import DBSessionMiddleware
from src.bot.middlewares.fsm_timeout import FSMTimeoutMiddleware
from src.bot.middlewares.role_check import RoleCheckMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.config.settings import settings

logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=0.05,
        integrations=[AsyncioIntegration()],
        send_default_pii=False,
    )

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)


async def main() -> None:
    """Запуск бота."""

    # Устанавливаем Menu Button для открытия Mini App
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🚀 Открыть приложение",
            web_app=WebAppInfo(url="https://app.rekharbor.ru/")
        )
    )

    storage = RedisStorage.from_url(str(settings.redis_url))
    dp = Dispatcher(storage=storage)

    dp.update.middleware(DBSessionMiddleware())
    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(RoleCheckMiddleware())
    dp.update.middleware(FSMTimeoutMiddleware())

    dp.include_router(main_router)

    logger.info("Starting bot @%s", (await bot.get_me()).username)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(main())
