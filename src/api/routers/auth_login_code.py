"""
Auth endpoint: Login via one-time code from Telegram bot.

Flow:
1. User sends /login to the bot
2. Bot generates 6-digit code, stores in Redis (TTL 5 min)
3. User enters code on web portal
4. Backend validates code in Redis, creates/updates user, returns JWT
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.auth_utils import create_jwt_token
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginCodeRequest(BaseModel):
    code: str


class LoginCodeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login-code", response_model=LoginCodeResponse)
async def login_with_code(body: LoginCodeRequest) -> LoginCodeResponse:
    """
    Авторизация по одноразовому коду из Telegram-бота.

    Принимает 6-значный код, ищет в Redis, получает telegram_id,
    создаёт/обновляет пользователя, возвращает JWT.

    Errors:
        400: код невалиден или истёк
        500: ошибка БД
    """
    import redis.asyncio as aioredis

    from src.config.settings import settings

    code = body.code.strip()
    if not code or len(code) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код должен состоять из 6 цифр",
        )

    redis_key = f"login_code:{code}"
    r = aioredis.from_url(str(settings.redis_url))

    try:
        telegram_id_raw = await r.get(redis_key)
        if not telegram_id_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный или просроченный код. Отправьте /login боту для получения нового.",
            )

        telegram_id = int(telegram_id_raw.decode() if isinstance(telegram_id_raw, bytes) else telegram_id_raw)
        # Delete code immediately (one-time use)
        await r.delete(redis_key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат кода",
        ) from None
    except Exception as e:
        logger.error(f"Redis error during login-code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера авторизации",
        ) from e
    finally:
        await r.aclose()  # type: ignore[attr-defined]

    # Find or create user
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)
        if user:
            # Update user info
            update_data = user_repo._build_update_fields(
                user, telegram_id, user.username, user.first_name, user.last_name
            )
            if update_data:
                await user_repo.update(user.id, update_data)
        else:
            # Create new user
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
