"""
Точка входа Telegram бота.
"""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.bot.handlers import (
    analytics,
    billing,
    cabinet,
    campaigns,
    notifications,
    start,
    templates,
)
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.config.settings import settings

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """
    Создать экземпляр бота.

    Returns:
        Bot: Экземпляр бота с настройками по умолчанию.
    """
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(redis: Redis) -> Dispatcher:
    """
    Создать диспетчер с хранилищем и роутерами.

    Args:
        redis: Redis клиент для FSM storage.

    Returns:
        Dispatcher: Настроенный диспетчер.
    """
    storage = RedisStorage(redis)
    dp = Dispatcher(storage=storage)

    # Регистрация middleware
    dp.message.middleware(ThrottlingMiddleware(redis))
    dp.callback_query.middleware(ThrottlingMiddleware(redis))

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(cabinet.router)
    dp.include_router(campaigns.router)
    dp.include_router(billing.router)
    dp.include_router(notifications.router)
    dp.include_router(analytics.router)
    dp.include_router(templates.router)

    return dp


async def main() -> None:
    """
    Основная функция запуска бота.

    Запускает polling для получения обновлений.
    """
    import asyncio

    # Создаем Redis клиент
    redis = Redis.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
    )

    # Создаем бота и диспетчер
    bot = create_bot()
    dp = create_dispatcher(redis)

    # Получаем username бота
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot username: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to get bot username: {e}")

    logger.info("Starting bot in polling mode...")

    try:
        # Запускаем polling
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        # Закрываем сессии
        await bot.session.close()
        await redis.aclose()
        logger.info("Bot stopped")


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(main())
