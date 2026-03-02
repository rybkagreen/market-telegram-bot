"""
Точка входа Telegram бота.
"""

import logging

import sentry_sdk
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.bot.handlers import (
    admin,
    analytics,
    analytics_chats,
    billing,
    cabinet,
    campaign_analytics,  # AI-аналитика кампаний
    campaign_create_ai,  # Новый обработчик создания с AI
    campaigns,
    channels_db,  # База каналов
    feedback,
    models,
    notifications,
    start,
    templates,
)
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.config.settings import settings

logger = logging.getLogger(__name__)


def setup_sentry() -> None:
    """
    Инициализация Sentry для мониторинга ошибок.
    """
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if settings.is_production else 0.0,
            profiles_sample_rate=0.1 if settings.is_production else 0.0,
            send_default_pii=settings.is_production,
        )
        logger.info(f"Sentry initialized ({settings.environment})")
    else:
        logger.warning("Sentry DSN not configured — errors will not be tracked")


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

    # Регистрация роутеров — admin последним (у него глобальный фильтр)!
    dp.include_router(start.router)
    dp.include_router(cabinet.router)
    dp.include_router(campaigns.router)
    dp.include_router(campaign_analytics.router)  # AI-аналитика кампаний
    dp.include_router(campaign_create_ai.router)  # Создание кампании с AI
    dp.include_router(billing.router)
    dp.include_router(models.router)
    dp.include_router(notifications.router)
    dp.include_router(analytics.router)
    dp.include_router(analytics_chats.router)
    dp.include_router(channels_db.router)  # База каналов
    dp.include_router(templates.router)
    dp.include_router(feedback.router)
    dp.include_router(admin.router)

    return dp


async def main() -> None:
    """
    Основная функция запуска бота.

    Запускает polling для получения обновлений.
    """

    # Инициализация Sentry
    setup_sentry()

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

    # Устанавливаем команды бота
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start",   description="🏠 Главное меню"),
        BotCommand(command="app",     description="📱 Открыть Mini App"),
        BotCommand(command="cabinet", description="👤 Личный кабинет"),
        BotCommand(command="balance", description="💳 Баланс"),
        BotCommand(command="help",    description="ℹ️ Помощь"),
    ]
    await bot.set_my_commands(commands)
    logger.info(f"Bot commands set: {[c.command for c in commands]}")

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
