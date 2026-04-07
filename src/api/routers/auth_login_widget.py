"""
Auth router для Telegram Login Widget.

POST /api/auth/telegram-login-widget — получить JWT по данным Login Widget
"""

import logging

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from src.api.auth_utils import create_jwt_token, validate_telegram_login_widget
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


# ─── Схемы ──────────────────────────────────────────────────────


class LoginWidgetRequest(BaseModel):
    """Запрос на авторизацию через Telegram Login Widget."""

    id: int
    auth_date: int
    hash: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


class LoginWidgetResponse(BaseModel):
    """Ответ с JWT токеном."""

    access_token: str
    token_type: str = "bearer"
    user: dict


# ─── Endpoints ──────────────────────────────────────────────────


@_limit("5/minute")
@router.post("/telegram-login-widget", response_model=LoginWidgetResponse)
async def login_telegram_login_widget(
    request: Request, body: LoginWidgetRequest
) -> LoginWidgetResponse:
    """
    Авторизация через Telegram Login Widget.

    Принимает данные от Login Widget (id, auth_date, hash, first_name, username, photo_url),
    проверяет HMAC-SHA256 подпись, создаёт или обновляет пользователя,
    возвращает JWT токен.

    Rate limited: 5 requests per minute per IP.

    Errors:
        400: данные невалидны или устарели (> 24 часа)
        500: ошибка БД
    """
    # Валидируем подпись Login Widget
    try:
        widget_data = validate_telegram_login_widget(body.model_dump())
    except ValueError as e:
        logger.warning(f"Invalid login widget data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Telegram Login Widget data: {e}",
        ) from e

    telegram_id = widget_data["telegram_id"]

    # Находим или создаём пользователя в БД
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.create_or_update(
            telegram_id=telegram_id,
            username=widget_data.get("username"),
            first_name=widget_data.get("first_name", ""),
            last_name=widget_data.get("last_name"),
        )
        await session.commit()

    plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    logger.info(f"Login Widget auth: telegram_id={telegram_id}, plan={plan_value}")

    # Создаём JWT (тот же формат что и для Mini App — совместим)
    token = create_jwt_token(
        user_id=user.id,
        telegram_id=user.telegram_id,
        plan=plan_value,
    )

    return LoginWidgetResponse(
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
