"""
Auth endpoint: Login via one-time code from Telegram bot.

Flow:
1. User sends /login to the bot
2. Bot generates 6-digit code, stores in Redis (TTL 5 min)
3. User enters code on web portal
4. Backend validates code in Redis, creates/updates user, returns JWT
"""

import logging

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from src.api.auth_utils import create_jwt_token
from src.api.dependencies import RedisClient
from src.core.middleware.rate_limit import limiter
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


def _limit(rate: str):
    """Safe limiter decorator — no-op if limiter not yet initialized."""
    def decorator(fn):
        if limiter is None:
            return fn
        return limiter.limit(rate)(fn)
    return decorator


class LoginCodeRequest(BaseModel):
    code: str


class LoginCodeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@_limit("10/hour")
@router.post("/login-code")
async def login_with_code(
    request: Request,
    body: LoginCodeRequest,
    redis: RedisClient,
) -> LoginCodeResponse:
    """
    Авторизация по одноразовому коду из Telegram-бота.

    Принимает 6-значный код, ищет в Redis, получает telegram_id,
    создаёт/обновляет пользователя, возвращает JWT.

    Rate limited: 10 requests per hour per IP.

    Errors:
        400: код невалиден или истёк
        429: превышен лимит попыток
        500: ошибка БД или Redis
    """
    code = body.code.strip()
    if not code or len(code) != 6 or not code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код должен состоять из 6 цифр",
        )

    redis_key = f"login_code:{code}"
    try:
        telegram_id_raw = await redis.get(redis_key)
        if not telegram_id_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный или просроченный код. Отправьте /login боту для получения нового.",
            )

        if isinstance(telegram_id_raw, bytes):
            telegram_id_raw = telegram_id_raw.decode()
        telegram_id = int(telegram_id_raw)
        # Delete code immediately (one-time use)
        await redis.delete(redis_key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат кода",
        ) from None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis error during login-code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера авторизации",
        ) from e

    # Find or create user
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)
        if user:
            update_data = user_repo._build_update_fields(
                user, telegram_id, user.username, user.first_name, user.last_name
            )
            if update_data:
                await user_repo.update(user.id, update_data)
        else:
            user = await user_repo.create_or_update(
                telegram_id=telegram_id,
                username=None,
                first_name="Web User",
                last_name=None,
            )
        await session.commit()

    plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)

    token = create_jwt_token(
        user_id=user.id,
        telegram_id=user.telegram_id,
        plan=plan_value,
    )

    logger.info(f"Login code auth: telegram_id={telegram_id}, plan={plan_value}")

    return LoginCodeResponse(
        access_token=token,
        user={
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "plan": plan_value,
            "credits": user.credits,
            "ai_generations_used": user.ai_uses_count,
        },
    )
