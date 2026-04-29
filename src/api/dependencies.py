"""
Зависимости FastAPI для авторизации и работы с БД.
"""

import logging
from typing import Annotated

import jwt as pyjwt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select as sa_select
from sqlalchemy.orm import selectinload
from telegram import Bot

from src.api.auth_utils import JwtSource, decode_jwt_token
from src.config.settings import settings
from src.db.models.user import User
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Security scheme для JWT
bearer_scheme = HTTPBearer(auto_error=False)


_ALLOWED_AUDIENCES: list[JwtSource] = ["mini_app", "web_portal"]


async def _resolve_user_for_audience(
    credentials: HTTPAuthorizationCredentials | None,
    audience: JwtSource | list[JwtSource],
    *,
    audience_mismatch_status: int = status.HTTP_403_FORBIDDEN,
    request: Request | None = None,
) -> User:
    """
    Decode JWT с обязательной проверкой audience и вернуть active User.

    Все три фронтенд-dependencies (`get_current_user`,
    `get_current_user_from_web_portal`, `get_current_user_from_mini_app`)
    делегируют сюда — отличаются только разрешённым набором audience и
    тем, какой статус возвращать при aud-несовпадении.

    `request` опционален: когда вызвано через FastAPI DI — FastAPI
    автоинжектит, и мы пишем `request.state.user_id` + `user_aud`, чтобы
    `AuditMiddleware` мог читать их без повторного декода JWT (PF.4).
    Прямые вызовы из тестов передают `request=None` — стейт не пишется.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_jwt_token(credentials.credentials, audience=audience)
        user_id = int(payload["sub"])
        token_aud = payload.get("aud")
    except pyjwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from e
    except pyjwt.InvalidAudienceError as e:
        raise HTTPException(
            status_code=audience_mismatch_status,
            detail="Invalid token audience",
        ) from e
    except pyjwt.MissingRequiredClaimError as e:
        # Legacy aud-less token — pre-Phase-0 format. RFC 7231 §6.5.15 426
        # Upgrade Required signals "your token format is obsolete, re-authenticate".
        # WWW-Authenticate parity with the missing-credentials branch (line 44-49).
        raise HTTPException(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            detail="Invalid token: missing audience claim",
            headers={"WWW-Authenticate": "Bearer"},
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

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if request is not None:
        # PF.4: surface verified identity on request.state so AuditMiddleware
        # can read it without re-decoding the JWT (the previous pattern decoded
        # without signature verification — code smell, see git history).
        request.state.user_id = user.id
        request.state.user_aud = token_aud

    return user


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    Dependency: получить текущего пользователя из JWT токена (mini_app или web_portal).

    Принимает оба источника. Для аудит-чувствительных эндпоинтов
    (`/api/legal-profile/*`, документы, реквизиты) использовать
    `get_current_user_from_web_portal` — он жёстко режет mini_app токены.

    Raises:
        HTTPException 401: токен отсутствует, невалиден, истёк, или
            юзер удалён.
        HTTPException 426: legacy aud-less токен (до Phase 0).
    """
    return await _resolve_user_for_audience(
        credentials,
        _ALLOWED_AUDIENCES,
        audience_mismatch_status=status.HTTP_401_UNAUTHORIZED,
        request=request,
    )


async def get_current_user_from_web_portal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    Dependency: только web_portal-токены. mini_app JWT → 403.

    Use case: эндпоинты, обрабатывающие ПД (ФЗ-152) — паспорт, ИНН,
    выписки, реквизиты. mini_app категорически не должен видеть ПД,
    поэтому даже валидный mini_app-токен отбивается на этом уровне.
    """
    return await _resolve_user_for_audience(
        credentials,
        "web_portal",
        audience_mismatch_status=status.HTTP_403_FORBIDDEN,
        request=request,
    )


async def get_current_user_from_mini_app(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    Dependency: только mini_app-токены. web_portal JWT → 403.

    Use case: бридж `exchange-miniapp-to-portal`, который преобразует
    mini_app-сессию в краткоживущий ticket. Принимать web_portal-токен
    здесь не имеет смысла (у юзера уже есть портальная сессия).
    """
    return await _resolve_user_for_audience(
        credentials,
        "mini_app",
        audience_mismatch_status=status.HTTP_403_FORBIDDEN,
        request=request,
    )


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
    current_user: User = Depends(get_current_user_from_web_portal),
) -> User:
    """
    Dependency: проверить что текущий пользователь является администратором.

    Wraps `get_current_user_from_web_portal` (16.1, BL-049): admin endpoints
    обрабатывают ПД (legal-profiles, users, platform-settings, payouts) и
    должны быть pinned к web_portal-only — mini_app JWT возвращает 403 на
    audience-несовпадении до проверки is_admin (ФЗ-152).

    Использование:
        @router.get("/admin/stats")
        async def get_stats(admin: Annotated[User, Depends(get_current_admin_user)]):
            return {"admin_id": admin.id}

    Args:
        current_user: Текущий пользователь из get_current_user_from_web_portal

    Returns:
        Пользователь если is_admin = True

    Raises:
        HTTPException 403: mini_app JWT (audience mismatch) либо
            пользователь не является администратором.
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
