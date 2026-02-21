"""
Асинхронные сессии SQLAlchemy для работы с базой данных.
Использует asyncpg драйвер для PostgreSQL.
"""

from collections.abc import AsyncGenerator
from typing import Final

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import settings

# Пул соединений: оптимальные настройки для production
POOL_SIZE: Final[int] = 20
MAX_OVERFLOW: Final[int] = 10
POOL_TIMEOUT: Final[int] = 30
POOL_RECYCLE: Final[int] = 1800  # 30 минут
POOL_PRE_PING: Final[bool] = True  # Проверка соединения перед использованием

# Создаем асинхронный движок
async_engine = create_async_engine(
    str(settings.database_url),
    echo=settings.debug,  # Логирование SQL запросов в debug режиме
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=POOL_PRE_PING,
    pool_use_lifo=True,  # LIFO для лучшего использования соединений
)

# Фабрика сессий
async_session_factory: Final = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Не истекать объекты после коммита
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """
    Dependency для получения сессии БД.
    Используется в FastAPI и других местах.

    Usage:
        async with get_session() as session:
            # работа с session
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session_no_commit() -> AsyncGenerator[AsyncSession]:
    """
    Dependency для получения сессии БД без автоматического коммита.
    Коммит должен быть вызван явно.

    Usage:
        async with get_session_no_commit() as session:
            # работа с session
            await session.commit()
    """
    session = async_session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """
    Инициализация базы данных.
    Создает все таблицы, если они не существуют.
    """
    from src.db.base import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """
    Освобождение ресурсов базы данных.
    Вызывается при остановке приложения.
    """
    await async_engine.dispose()
