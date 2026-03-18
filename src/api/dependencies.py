"""
Зависимости FastAPI для авторизации и работы с БД.
"""

import logging
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.auth_utils import decode_jwt_token
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository
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
        user = await UserRepository(session).get_by_id(user_id)

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
        yield session


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
