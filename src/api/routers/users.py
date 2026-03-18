"""
FastAPI router для управления данными пользователя (Users).

Endpoints:
  GET /api/users/me          — данные текущего пользователя
  GET /api/users/me/stats    — статистика пользователя (репутация)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.db.repositories.reputation_repo import ReputationRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])


# ─── Response Models ────────────────────────────────────────────


class UserResponse(BaseModel):
    """Данные пользователя для Mini App."""

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    plan: str
    credits: int
    balance_rub: str
    earned_rub: str
    is_admin: bool

    model_config = {"from_attributes": True}

    @field_validator("balance_rub", "earned_rub", mode="before")
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to string for JSON serialization."""
        from decimal import Decimal

        if isinstance(v, Decimal):
            return str(v)
        return v


class ReputationScoreResponse(BaseModel):
    """Данные репутации пользователя."""

    user_id: int
    advertiser_score: float
    owner_score: float
    is_advertiser_blocked: bool
    is_owner_blocked: bool
    advertiser_violations_count: int
    owner_violations_count: int

    model_config = {"from_attributes": True}


class UserStatsResponse(BaseModel):
    """Ответ статистики пользователя для Mini App."""

    reputation: ReputationScoreResponse

    model_config = {"from_attributes": True}


# ─── Endpoints ──────────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def get_current_user_data(current_user: CurrentUser) -> UserResponse:
    """
    Получить данные текущего авторизованного пользователя.

    Используется для проверки токена и обновления данных на фронтенде.
    Возвращает основную информацию о пользователе: ID, Telegram ID,
    имя, тариф и баланс кредитов.

    Returns:
        UserResponse: Данные пользователя.
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
        balance_rub=str(current_user.balance_rub),
        earned_rub=str(current_user.earned_rub),
        is_admin=current_user.is_admin,
    )


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_current_user_stats(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> UserStatsResponse:
    """
    Получить статистику репутации текущего пользователя.

    Возвращает данные о репутации пользователя в обеих ролях:
    рекламодателя и владельца канала. Включает информацию о блокировках
    и количестве нарушений.

    Args:
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        UserStatsResponse: Данные репутации пользователя (wrapped в { reputation: ... }).

    Raises:
        HTTPException 404: Если запись о репутации не найдена.
    """
    repo = ReputationRepository(session)
    rep_score = await repo.get_or_create(current_user.id)

    if not rep_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reputation record not found",
        )

    return UserStatsResponse(
        reputation=ReputationScoreResponse(
            user_id=rep_score.user_id,
            advertiser_score=rep_score.advertiser_score,
            owner_score=rep_score.owner_score,
            is_advertiser_blocked=rep_score.is_advertiser_blocked,
            is_owner_blocked=rep_score.is_owner_blocked,
            advertiser_violations_count=rep_score.advertiser_violations_count,
            owner_violations_count=rep_score.owner_violations_count,
        )
    )
