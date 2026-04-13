"""
Зависимости FastAPI для авторизации и работы с БД.
"""

import logging
from typing import Annotated

import jwt as pyjwt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from telegram import Bot

from src.api.auth_utils import decode_jwt_token
from src.config.settings import settings
from src.db.models.legal_profile import LegalProfile
from src.db.models.user import User
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Security scheme для JWT
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    Dependency: получить текущего пользователя из JWT токена.

    Использование:
        @router.get("/me")
        async def me(user: Annotated[User, Depends(get_current_user)]):
            return user

    Args:
        credentials: JWT токен из заголовка Authorization

    Returns:
        Пользователь из БД

    Raises:
        HTTPException 401: токен отсутствует, невалиден или истёк
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_jwt_token(credentials.credentials)
        user_id = int(payload["sub"])
    except pyjwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from e
    except (pyjwt.InvalidTokenError, KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from e

    async with async_session_factory() as session:
        result = await session.execute(
            sa_select(User).where(User.id == user_id).options(selectinload(User.legal_profile))
        )
        user = result.scalar_one_or_none()

    # ИЗМЕНЕНО (2026-03-17): is_banned → is_active (поле is_banned не существует в модели User)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_db_session():
    """
    Получить сессию БД.

    Yields:
        AsyncSession SQLAlchemy.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Type aliases для зависимостей
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[None, Depends(get_db_session)]


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency: проверить что текущий пользователь является администратором.

    Использование:
        @router.get("/admin/stats")
        async def get_stats(admin: Annotated[User, Depends(get_current_admin_user)]):
            return {"admin_id": admin.id}

    Args:
        current_user: Текущий пользователь из get_current_user

    Returns:
        Пользователь если is_admin = True

    Raises:
        HTTPException 403: Пользователь не является администратором
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden — admin access required",
        )
    return current_user


AdminUser = Annotated[User, Depends(get_current_admin_user)]


# ─── Redis ─────────────────────────────────────────────────────

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    Получить shared Redis connection pool.
    Создаёт пул при первом вызове, переиспользует далее.
    """
    global _redis_pool
    if _redis_pool is None or _redis_pool.connection_pool is None:
        _redis_pool = aioredis.from_url(
            str(settings.redis_url),
            max_connections=10,
            decode_responses=False,
        )
    return _redis_pool


async def close_redis_pool():
    """Закрыть Redis пул при shutdown (вызывается из lifespan)."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]


# ─── Telegram Bot singleton ────────────────────────────────────

_bot_instance: Bot | None = None


async def get_bot() -> Bot:
    """
    Получить shared экземпляр Telegram Bot (singleton).
    Создаётся и инициализируется один раз, переиспользуется далее.
    Если задан TELEGRAM_PROXY, все запросы идут через него (SOCKS5/HTTP).
    """
    global _bot_instance
    if _bot_instance is None:
        if settings.telegram_proxy:
            from telegram.request import HTTPXRequest

            request = HTTPXRequest(proxy=settings.telegram_proxy)
            _bot_instance = Bot(token=settings.bot_token, request=request)
        else:
            _bot_instance = Bot(token=settings.bot_token)
        await _bot_instance.initialize()
    return _bot_instance


async def close_bot() -> None:
    """Закрыть Bot при shutdown (вызывается из lifespan)."""
    global _bot_instance
    if _bot_instance is not None:
        await _bot_instance.shutdown()
        _bot_instance = None


# ─── Legal Profile Verification ────────────────────────────────

async def require_verified_legal_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> LegalProfile:
    """3-level check: exists → is_completed → is_verified.

    Participant check (advertiser_id/owner_id) happens separately
    in each router AFTER this dependency fires.
    """
    # Lazy import inside function body to avoid circular dependency
    from src.db.repositories.legal_profile_repo import LegalProfileRepo

    repo = LegalProfileRepo(session)
    profile = await repo.get_by_user_id(current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "legal_profile_missing",
                "message": "Необходимо заполнить юридический профиль",
                "redirect": "/legal-profile",
            },
        )

    if not profile.is_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "legal_profile_incomplete",
                "message": "Юридический профиль заполнен не полностью",
                "redirect": "/legal-profile",
            },
        )

    if not profile.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "legal_profile_not_verified",
                "message": "Юридический профиль ожидает верификации администратором",
                "redirect": "/legal-profile/view",
            },
        )

    return profile
