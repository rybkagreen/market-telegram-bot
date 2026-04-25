"""
Auth router для JWT авторизации через Telegram initData.

POST /api/auth/telegram                   — JWT по initData (mini_app)
POST /api/auth/exchange-miniapp-to-portal — обменять mini_app JWT на ticket
POST /api/auth/consume-ticket             — обменять ticket на web_portal JWT
GET  /api/auth/me                         — данные текущего пользователя
"""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt as pyjwt
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from src.api.auth_utils import create_jwt_token, validate_telegram_init_data
from src.api.dependencies import (
    CurrentUser,
    get_current_user_from_mini_app,
    get_redis,
)
from src.api.schemas.auth import AuthTokenResponse, TicketResponse
from src.api.schemas.user import UserResponse
from src.config.settings import settings
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Bridge helpers ────────────────────────────────────────────


def _client_ip(request: Request) -> str:
    """Extract real client IP from proxy chain — see CLAUDE.md proxy chain note.

    Order: X-Forwarded-For (first hop) → X-Real-IP → request.client.host.
    nginx/conf.d/default.conf sets both upstream headers on every /api/* block.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"


_TICKET_RATE_IP_LIMIT = 10
_TICKET_RATE_IP_WINDOW_S = 60
_TICKET_FAIL_USER_LIMIT = 5
_TICKET_FAIL_USER_WINDOW_S = 300


async def _check_ip_rate_limit(redis: aioredis.Redis, ip: str) -> None:
    """Manual Redis INCR+EXPIRE — 10 req/min/IP. 11th → 429."""
    key = f"auth:ticket:rate:ip:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _TICKET_RATE_IP_WINDOW_S)
    if count > _TICKET_RATE_IP_LIMIT:
        logger.warning(
            "ticket_consume_ip_rate_limit_exceeded",
            extra={"event": "ticket_consume_ip_rate_limit", "ip": ip, "count": count},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )


async def _check_user_fail_limit(redis: aioredis.Redis, user_id: int, ip: str) -> None:
    """Pre-check: 5 fails/5min/user → 6th = 429 + WARN log."""
    key = f"auth:ticket:rate:user:{user_id}:fail"
    raw = await redis.get(key)
    if raw is None:
        return
    count = int(raw)
    if count >= _TICKET_FAIL_USER_LIMIT:
        logger.warning(
            "ticket_consume_user_blocked",
            extra={
                "event": "ticket_consume_user_blocked",
                "user_id": user_id,
                "ip": ip,
                "count": count,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts",
        )


async def _record_user_fail(redis: aioredis.Redis, user_id: int) -> None:
    key = f"auth:ticket:rate:user:{user_id}:fail"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _TICKET_FAIL_USER_WINDOW_S)


# ─── Схемы ──────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Запрос на авторизацию через Telegram initData."""

    init_data: str


class LoginResponse(BaseModel):
    """Ответ с JWT токеном."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Endpoints ──────────────────────────────────────────────────


async def _login_handler(body: LoginRequest) -> LoginResponse:
    """
    Авторизация через Telegram initData.

    Принимает initData из window.Telegram.WebApp.initData,
    проверяет подпись, создаёт или обновляет пользователя,
    возвращает JWT токен.

    Errors:
        400: initData невалидна или устарела (> 1 часа)
        500: ошибка БД
    """
    # Валидируем initData
    try:
        tg_data = validate_telegram_init_data(body.init_data)
    except ValueError as e:
        logger.warning(f"Invalid initData: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Telegram data: {e}",
        ) from e

    tg_user = tg_data["user"]
    telegram_id = tg_user.get("id")

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing user.id in initData",
        )

    # Находим или создаём пользователя в БД
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.create_or_update(
            telegram_id=int(telegram_id),
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
        )
        await session.commit()

    plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    logger.info(f"Mini App login: telegram_id={telegram_id}, plan={plan_value}")

    # Создаём JWT (mini_app source)
    token = create_jwt_token(
        user_id=user.id,
        telegram_id=user.telegram_id,
        plan=plan_value,
        source="mini_app",
    )

    return LoginResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            plan=plan_value,
            plan_expires_at=user.plan_expires_at,
            balance_rub=str(user.balance_rub),
            earned_rub=str(user.earned_rub),
            credits=user.credits,
            advertiser_xp=user.advertiser_xp,
            advertiser_level=user.advertiser_level,
            owner_xp=user.owner_xp,
            owner_level=user.owner_level,
            referral_code=user.referral_code,
            is_admin=user.is_admin,
            ai_generations_used=user.ai_uses_count,
            legal_status_completed=user.legal_status_completed,
            legal_profile_prompted_at=user.legal_profile_prompted_at,
            legal_profile_skipped_at=user.legal_profile_skipped_at,
            platform_rules_accepted_at=user.platform_rules_accepted_at,
            privacy_policy_accepted_at=user.privacy_policy_accepted_at,
            has_legal_profile=user.legal_profile is not None,
        ),
    )


@router.post("/telegram")
async def login_telegram_endpoint(body: LoginRequest) -> LoginResponse:
    """Авторизация через Telegram initData (алиас для mini app)."""
    return await _login_handler(body)


@router.post("/exchange-miniapp-to-portal")
async def exchange_miniapp_to_portal(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user_from_mini_app)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> TicketResponse:
    """
    Обменять mini_app JWT на короткоживущий ticket для входа на веб-портал.

    Flow:
      1. Frontend mini_app вызывает с действующим mini_app JWT в Authorization.
      2. Бэкенд генерирует jti = uuid4(), подписывает ticket-JWT с aud="web_portal"
         и exp = now + ticket_jwt_ttl_seconds.
      3. В Redis сохраняется `auth:ticket:jti:{jti}` →
         JSON {user_id, issued_at, ip}, TTL = ticket_jwt_ttl_seconds.
      4. Возвращается TicketResponse — frontend перенаправляет юзера на
         {portal_url}/login?ticket={ticket}&redirect={target}.

    Безопасность:
      - aud="web_portal" — ticket НЕ принимается обычными mini_app dependencies.
      - jti в Redis — one-shot consume, защита от replay.
      - Короткий TTL (по умолчанию 300с) ограничивает окно атаки.
    """
    jti = str(uuid.uuid4())
    issued_at = datetime.now(UTC)
    expire = issued_at + timedelta(seconds=settings.ticket_jwt_ttl_seconds)
    ip = _client_ip(request)
    plan_value = (
        current_user.plan.value if hasattr(current_user.plan, "value") else str(current_user.plan)
    )

    payload = {
        "sub": str(current_user.id),
        "tg": current_user.telegram_id,
        "plan": plan_value,
        "jti": jti,
        "aud": "web_portal",
        "exp": expire,
        "iat": issued_at,
    }
    ticket = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    await redis.setex(
        f"auth:ticket:jti:{jti}",
        settings.ticket_jwt_ttl_seconds,
        json.dumps(
            {
                "user_id": current_user.id,
                "issued_at": issued_at.isoformat(),
                "ip": ip,
            }
        ),
    )

    logger.info(
        "ticket_issued",
        extra={
            "event": "ticket_issued",
            "user_id": current_user.id,
            "jti_prefix": jti[:8],
            "ip": ip,
        },
    )

    return TicketResponse(
        ticket=ticket,
        portal_url=settings.web_portal_url,
        expires_in=settings.ticket_jwt_ttl_seconds,
    )


class ConsumeTicketRequest(BaseModel):
    ticket: str


@router.post("/consume-ticket")
async def consume_ticket(
    request: Request,
    body: ConsumeTicketRequest,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> AuthTokenResponse:
    """
    Обменять ticket-JWT на полноценный web_portal access-token.

    Безопасность:
      - 10 запросов / минута / IP — `auth:ticket:rate:ip:{ip}`.
      - 5 неудачных попыток / 5 минут / user_id — `auth:ticket:rate:user:{id}:fail`.
      - Любая ошибка декодирования / валидации aud / отсутствие jti в Redis → 401
        + structured WARN-лог `event=ticket_consume_failed`.
      - jti удаляется атомарно (`redis.delete`) — replay невозможен.
    """
    ip = _client_ip(request)
    await _check_ip_rate_limit(redis, ip)

    jti_prefix = "n/a"
    user_id: int | None = None

    try:
        payload = pyjwt.decode(
            body.ticket,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="web_portal",
        )
        jti = payload.get("jti")
        if not isinstance(jti, str) or not jti:
            raise ValueError("missing jti")
        jti_prefix = jti[:8]
        user_id = int(payload["sub"])
        plan_value = payload.get("plan", "free")
        telegram_id = int(payload.get("tg", 0))
    except pyjwt.ExpiredSignatureError as e:
        logger.warning(
            "ticket_consume_failed",
            extra={
                "event": "ticket_consume_failed",
                "reason": "expired",
                "ip": ip,
                "jti_prefix": jti_prefix,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ticket expired",
        ) from e
    except (pyjwt.InvalidTokenError, KeyError, ValueError) as e:
        logger.warning(
            "ticket_consume_failed",
            extra={
                "event": "ticket_consume_failed",
                "reason": str(e) or type(e).__name__,
                "ip": ip,
                "jti_prefix": jti_prefix,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ticket",
        ) from e

    # User-level pre-check (block 6th try after 5 fails in 5 min)
    await _check_user_fail_limit(redis, user_id, ip)

    # One-shot consume: delete returns count of removed keys (0 → already used / Redis flushed)
    deleted = await redis.delete(f"auth:ticket:jti:{jti}")
    if not deleted:
        await _record_user_fail(redis, user_id)
        logger.warning(
            "ticket_consume_failed",
            extra={
                "event": "ticket_consume_failed",
                "reason": "jti not found (replay or redis flush)",
                "ip": ip,
                "jti_prefix": jti_prefix,
                "user_id": user_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ticket already consumed",
        )

    new_token = create_jwt_token(
        user_id=user_id,
        telegram_id=telegram_id,
        plan=plan_value,
        source="web_portal",
    )

    logger.info(
        "ticket_consumed",
        extra={
            "event": "ticket_consumed",
            "user_id": user_id,
            "jti_prefix": jti_prefix,
            "ip": ip,
        },
    )

    return AuthTokenResponse(
        access_token=new_token,
        source="web_portal",
    )


@router.get("/me")
async def get_me(current_user: CurrentUser) -> UserResponse:
    """
    Получить данные текущего авторизованного пользователя.

    Используется для проверки токена и обновления данных на фронтенде.
    """
    plan_value = (
        current_user.plan.value if hasattr(current_user.plan, "value") else str(current_user.plan)
    )
    return UserResponse(
        id=current_user.id,
        telegram_id=current_user.telegram_id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        plan=plan_value,
        plan_expires_at=current_user.plan_expires_at,
        balance_rub=str(current_user.balance_rub),
        earned_rub=str(current_user.earned_rub),
        credits=current_user.credits,
        advertiser_xp=current_user.advertiser_xp,
        advertiser_level=current_user.advertiser_level,
        owner_xp=current_user.owner_xp,
        owner_level=current_user.owner_level,
        referral_code=current_user.referral_code,
        is_admin=current_user.is_admin,
        ai_generations_used=current_user.ai_uses_count,
        legal_status_completed=current_user.legal_status_completed,
        legal_profile_prompted_at=current_user.legal_profile_prompted_at,
        legal_profile_skipped_at=current_user.legal_profile_skipped_at,
        platform_rules_accepted_at=current_user.platform_rules_accepted_at,
        privacy_policy_accepted_at=current_user.privacy_policy_accepted_at,
        has_legal_profile=current_user.legal_profile is not None,
    )
