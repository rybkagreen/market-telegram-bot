"""
Auth router для JWT авторизации.
"""

import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import get_current_user
from src.config.settings import settings
from src.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# JWT настройки
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 часа


def create_access_token(user_id: int, telegram_id: int) -> str:
    """
    Создать JWT access token.

    Args:
        user_id: ID пользователя в БД.
        telegram_id: Telegram ID.

    Returns:
        JWT токен.
    """
    expire = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(to_encode, settings.bot_token, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Расшифровать JWT токен.

    Args:
        token: JWT токен.

    Returns:
        Payload токена или None.
    """
    try:
        return jwt.decode(token, settings.bot_token, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class LoginRequest(BaseModel):
    """Запрос на авторизацию."""

    init_data: str


class LoginResponse(BaseModel):
    """Ответ с токенами."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRE_MINUTES * 60


class TokenRefreshRequest(BaseModel):
    """Запрос на обновление токена."""

    access_token: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Авторизация через Telegram initData.

    Args:
        request: Запрос с initData.

    Returns:
        Access token.
    """
    from src.api.dependencies import _validate_telegram_init_data
    from src.db.repositories.user_repo import UserRepository
    from src.db.session import async_session_factory

    # Валидируем initData
    data = _validate_telegram_init_data(request.init_data)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initData",
        )

    # Получаем user данные
    import json

    user_data = json.loads(data.get("user", "{}"))
    telegram_id = user_data.get("id")

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No telegram_id in initData",
        )

    # Получаем или создаём пользователя
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(int(telegram_id))

        if not user:
            # Создаём нового
            import uuid

            user = await user_repo.create(
                {
                    "telegram_id": int(telegram_id),
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "language_code": user_data.get("language_code", "ru"),
                    "referral_code": str(uuid.uuid4())[:8],
                }
            )

    # Создаём токен
    access_token = create_access_token(user.id, user.telegram_id)

    logger.info(f"User {user.telegram_id} logged in")

    return LoginResponse(
        access_token=access_token,
        expires_in=JWT_EXPIRE_MINUTES * 60,
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):  # noqa: B008
    """
    Получить текущего пользователя.

    Args:
        current_user: Текущий пользователь.

    Returns:
        Данные пользователя.
    """
    return {
        "id": current_user.id,
        "telegram_id": current_user.telegram_id,
        "username": current_user.username,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "balance": str(current_user.balance),
        "plan": current_user.plan.value,
        "is_banned": current_user.is_banned,
    }


@router.post("/refresh")
async def refresh_token(request: TokenRefreshRequest):
    """
    Обновить access token.

    Args:
        request: Старый токен.

    Returns:
        Новый токен.
    """
    payload = decode_access_token(request.access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = int(payload["sub"])
    telegram_id = int(payload["telegram_id"])

    new_token = create_access_token(user_id, telegram_id)

    return {"access_token": new_token, "token_type": "bearer"}
