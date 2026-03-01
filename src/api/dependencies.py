"""
Зависимости FastAPI для авторизации и работы с БД.
"""

import hashlib
import hmac
import logging
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer

from src.config.settings import settings
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Security scheme для JWT
security = HTTPBearer(auto_error=False)

# Redis кэш для initData
INIT_DATA_CACHE_TTL = 600  # 10 минут


def _validate_telegram_init_data(init_data: str) -> dict[str, str] | None:
    """
    Валидировать Telegram initData через HMAC-SHA256.

    Args:
        init_data: Строка initData от Telegram WebApp.

    Returns:
        Распарсенные данные или None если невалидно.
    """
    try:
        # Парсим initData
        data = {}
        for pair in init_data.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                data[key] = value

        # Получаем hash для проверки
        received_hash = data.pop("hash", None)
        if not received_hash:
            logger.warning("No hash in initData")
            return None

        # Сортируем ключи и создаваем строку для проверки
        data_check_arr = sorted(f"{key}={value}" for key, value in data.items())
        data_check_string = "\n".join(data_check_arr)

        # Вычисляем HMAC-SHA256 с ключом из токена бота
        secret_key = hmac.new(
            b"WebAppData",
            settings.bot_token.encode(),
            hashlib.sha256,
        ).digest()

        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Сравниваем хэши
        if not hmac.compare_digest(computed_hash, received_hash):
            logger.warning("Invalid initData hash")
            return None

        return data

    except Exception as e:
        logger.error(f"Error validating initData: {e}")
        return None


async def _get_cached_user(telegram_id: int) -> User | None:
    """
    Получить пользователя из кэша Redis.

    Args:
        telegram_id: Telegram ID пользователя.

    Returns:
        Пользователь или None.
    """
    try:
        redis_client = redis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
        )
        cached = await redis_client.get(f"user:{telegram_id}")
        if cached:
            # Возвращаем заглушку - в реальности нужно десериализовать
            logger.info(f"User {telegram_id} found in cache")
        return None  # Пока не кэшируем пользователей
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def _cache_user(user: User) -> None:
    """
    Сохранить пользователя в кэш Redis.

    Args:
        user: Пользователь для кэширования.
    """
    try:
        redis_client = redis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
        )
        # Кэшируем на 10 минут
        await redis_client.setex(
            f"user:{user.telegram_id}",
            INIT_DATA_CACHE_TTL,
            str(user.id),
        )
    except Exception as e:
        logger.error(f"Cache set error: {e}")


async def get_current_user(
    x_init_data: Annotated[str | None, Header(alias="X-Init-Data")] = None,
) -> User:
    """
    Получить текущего пользователя из Telegram initData.

    Args:
        x_init_data: Telegram WebApp initData из заголовка.

    Returns:
        Пользователь из БД.

    Raises:
        HTTPException: Если initData невалиден или пользователь не найден.
    """
    if not x_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Init-Data header",
        )

    # Валидируем initData
    data = _validate_telegram_init_data(x_init_data)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initData",
        )

    # Получаем user из initData
    user_json = data.get("user")
    if not user_json:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user in initData",
        )

    import json

    try:
        user_data = json.loads(user_json)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user JSON in initData",
        ) from e

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No telegram_id in user data",
        )

    # Проверяем кэш
    cached_user = await _get_cached_user(telegram_id)
    if cached_user:
        return cached_user

    # Получаем или создаём пользователя в БД
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)

        if not user:
            # Создаём нового пользователя
            username = user_data.get("username")
            first_name = user_data.get("first_name")
            last_name = user_data.get("last_name")
            language_code = user_data.get("language_code", "ru")

            import uuid

            user = await user_repo.create(
                {
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "language_code": language_code,
                    "referral_code": str(uuid.uuid4())[:8],
                }
            )

        # Кэшируем
        await _cache_user(user)

        return user


async def get_db_session():
    """
    Получить сессию БД.

    Yields:
        AsyncSession SQLAlchemy.
    """
    async with async_session_factory() as session:
        yield session


# Type aliases для зависимостей
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[None, Depends(get_db_session)]
