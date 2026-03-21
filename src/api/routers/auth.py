"""
Auth router для JWT авторизации через Telegram initData.

POST /api/auth/telegram  — получить JWT по initData
GET  /api/auth/me        — данные текущего пользователя
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.auth_utils import create_jwt_token, validate_telegram_init_data
from src.api.dependencies import CurrentUser
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Схемы ──────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Запрос на авторизацию через Telegram initData."""

    init_data: str


class UserResponse(BaseModel):
    """Данные пользователя для Mini App."""

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    plan: str
    credits: int
    ai_generations_used: int

    model_config = {"from_attributes": True}


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

    plan_value = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
    logger.info(f"Mini App login: telegram_id={telegram_id}, plan={plan_value}")

    # Создаём JWT
    token = create_jwt_token(
        user_id=user.id,
        telegram_id=user.telegram_id,
        plan=plan_value,
    )

    return LoginResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            plan=plan_value,
            credits=user.credits,
            ai_generations_used=user.ai_uses_count,
        ),
    )


@router.post("/telegram", response_model=LoginResponse)
async def login_telegram_endpoint(body: LoginRequest) -> LoginResponse:
    """Авторизация через Telegram initData (алиас для mini app)."""
    return await _login_handler(body)


@router.get("/me", response_model=UserResponse)
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
        plan=plan_value,
        credits=current_user.credits,
        ai_generations_used=current_user.ai_uses_count,
    )
