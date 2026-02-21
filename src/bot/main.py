from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage

from src.config import settings
from src.bot.handlers.start import router as start_router
from src.bot.handlers.cabinet import router as cabinet_router
from src.bot.handlers.campaigns import router as campaigns_router


def create_dispatcher(storage: RedisStorage) -> Dispatcher:
    """Создание диспетчера с подключенными роутерами."""
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(cabinet_router)
    dp.include_router(campaigns_router)
    
    return dp


def create_bot() -> Bot:
    """Создание бота с настройками по умолчанию."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
