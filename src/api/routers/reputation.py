"""
FastAPI router для репутации пользователей (ReputationScore).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import CurrentUser, get_db_session
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reputation", tags=["reputation"])

# =============================================================================
# Schemas
# =============================================================================


class ReputationResponse(BaseModel):
    """Ответ с репутацией пользователя."""

    user_id: int
    advertiser_score: float
    owner_score: float
    is_advertiser_blocked: bool
    is_owner_blocked: bool
    advertiser_ban_until: str | None
    owner_ban_until: str | None
    advertiser_violations: int
    owner_violations: int
    updated_at: str

    model_config = {"from_attributes": True}


class PublicReputationResponse(BaseModel):
    """Публичная репутация (без ban-деталей)."""

    user_id: int
    advertiser_score: float
    owner_score: float
    advertiser_violations: int
    owner_violations: int

    model_config = {"from_attributes": True}


class ReputationHistoryEntry(BaseModel):
    """Запись истории репутации."""

    id: int
    user_id: int
    action: str
    delta: float
    score_before: float
    score_after: float
    role: str
    comment: str | None
    created_at: str

    model_config = {"from_attributes": True}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/me", response_model=ReputationResponse)
async def get_my_reputation(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> ReputationResponse:
    """Репутация текущего пользователя."""
    repo = ReputationRepo(session)
    rep_score = await repo.get_or_create(current_user.id)

    if not rep_score:
        raise HTTPException(status_code=404, detail="Reputation record not found")

    return ReputationResponse(
        user_id=rep_score.user_id,
        advertiser_score=rep_score.advertiser_score,
        owner_score=rep_score.owner_score,
        is_advertiser_blocked=rep_score.is_advertiser_blocked,
        is_owner_blocked=rep_score.is_owner_blocked,
        advertiser_ban_until=(
            rep_score.advertiser_blocked_until.isoformat() if rep_score.advertiser_blocked_until else None
        ),
        owner_ban_until=(
            rep_score.owner_blocked_until.isoformat() if rep_score.owner_blocked_until else None
        ),
        advertiser_violations=rep_score.advertiser_violations,
        owner_violations=rep_score.owner_violations,
        updated_at=rep_score.updated_at.isoformat(),
    )


@router.get("/me/history", response_model=list[ReputationHistoryEntry])
async def get_my_reputation_history(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    role: Annotated[str | None, Query(description="Фильтр по роли")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReputationHistoryEntry]:
    """История изменений репутации текущего пользователя."""
    repo = ReputationRepo(session)
    history = await repo.get_history(current_user.id, role=role, limit=limit, offset=offset)

    entries = []
    for h in history:
        # Получаем предыдущий score
        score_before = h.new_score - h.delta
        entries.append(
            ReputationHistoryEntry(
                id=h.id,
                user_id=h.user_id,
                action=h.action.value,
                delta=h.delta,
                score_before=score_before,
                score_after=h.new_score,
                role=h.role,
                comment=h.comment,
                created_at=h.created_at.isoformat(),
            )
        )

    return entries


@router.get("/{user_id}", response_model=PublicReputationResponse)
async def get_user_reputation(
    user_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PublicReputationResponse:
    """Публичная репутация пользователя."""
    from src.db.models.user import User

    # Проверка что пользователь существует
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo = ReputationRepo(session)
    rep_score = await repo.get_or_create(user_id)

    return PublicReputationResponse(
        user_id=rep_score.user_id,
        advertiser_score=rep_score.advertiser_score,
        owner_score=rep_score.owner_score,
        advertiser_violations=rep_score.advertiser_violations,
        owner_violations=rep_score.owner_violations,
    )


@router.get("/{user_id}/history", response_model=list[ReputationHistoryEntry])
async def get_user_reputation_history(
    user_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    role: Annotated[str | None, Query(description="Фильтр по роли")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReputationHistoryEntry]:
    """История репутации пользователя (только admin)."""
    # Проверка на админа
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    repo = ReputationRepo(session)
    history = await repo.get_history(user_id, role=role, limit=limit, offset=offset)

    entries = []
    for h in history:
        score_before = h.new_score - h.delta
        entries.append(
            ReputationHistoryEntry(
                id=h.id,
                user_id=h.user_id,
                action=h.action.value,
                delta=h.delta,
                score_before=score_before,
                score_after=h.new_score,
                role=h.role,
                comment=h.comment,
                created_at=h.created_at.isoformat(),
            )
        )

    return entries
