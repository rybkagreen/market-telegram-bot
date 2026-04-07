"""
FastAPI router для репутации пользователей (ReputationScore).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.db.models.reputation_history import ReputationHistory
from src.db.repositories.reputation_repo import ReputationRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reputation"])

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
    advertiser_ban_until: str | None = None
    owner_ban_until: str | None = None
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
    comment: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class ReputationAdminHistoryItem(BaseModel):
    """Запись истории репутации для админ-панели."""

    id: int
    user_id: int
    username: str | None = None
    role: str
    action: str
    delta: float
    score_before: float
    score_after: float
    created_at: str

    model_config = {"from_attributes": True}


class ReputationAdminHistoryResponse(BaseModel):
    """Ответ истории репутации для администратора с пагинацией."""

    items: list[ReputationAdminHistoryItem]
    total: int
    page: int
    pages: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/me", responses={404: {"description": "Not found"}})
async def get_my_reputation(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReputationResponse:
    """Репутация текущего пользователя."""
    repo = ReputationRepository(session)
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
            rep_score.advertiser_blocked_until.isoformat()
            if rep_score.advertiser_blocked_until
            else None
        ),
        owner_ban_until=(
            rep_score.owner_blocked_until.isoformat() if rep_score.owner_blocked_until else None
        ),
        advertiser_violations=rep_score.advertiser_violations_count,
        owner_violations=rep_score.owner_violations_count,
        updated_at=rep_score.updated_at.isoformat(),
    )


@router.get("/me/history")
async def get_my_reputation_history(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    role: Annotated[str | None, Query(description="Фильтр по роли")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReputationHistoryEntry]:
    """История изменений репутации текущего пользователя."""
    repo = ReputationRepository(session)
    history = await repo.get_history(current_user.id, role=role, limit=limit, offset=offset)

    entries = []
    for h in history:
        entries.append(
            ReputationHistoryEntry(
                id=h.id,
                user_id=h.user_id,
                action=h.action.value,
                delta=h.delta,
                score_before=h.score_before,
                score_after=h.score_after,
                role=h.role,
                comment=h.description,
                created_at=h.created_at.isoformat(),
            )
        )

    return entries


@router.get("/{user_id}", responses={404: {"description": "Not found"}})
async def get_user_reputation(
    user_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PublicReputationResponse:
    """Публичная репутация пользователя."""
    from src.db.models.user import User

    # Проверка что пользователь существует
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo = ReputationRepository(session)
    rep_score = await repo.get_or_create(user_id)

    return PublicReputationResponse(
        user_id=rep_score.user_id,
        advertiser_score=rep_score.advertiser_score,
        owner_score=rep_score.owner_score,
        advertiser_violations=rep_score.advertiser_violations_count,
        owner_violations=rep_score.owner_violations_count,
    )


@router.get("/{user_id}/history", responses={403: {"description": "Forbidden"}})
async def get_user_reputation_history(
    user_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    role: Annotated[str | None, Query(description="Фильтр по роли")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReputationHistoryEntry]:
    """История репутации пользователя (только admin)."""
    # Проверка на админа
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    repo = ReputationRepository(session)
    history = await repo.get_history(user_id, role=role, limit=limit, offset=offset)

    entries = []
    for h in history:
        entries.append(
            ReputationHistoryEntry(
                id=h.id,
                user_id=h.user_id,
                action=h.action.value,
                delta=h.delta,
                score_before=h.score_before,
                score_after=h.score_after,
                role=h.role,
                comment=h.description,
                created_at=h.created_at.isoformat(),
            )
        )

    return entries


@router.get("/admin/history", responses={403: {"description": "Forbidden"}})
async def get_admin_reputation_history(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[int | None, Query(description="Фильтр по пользователю")] = None,
    role: Annotated[str | None, Query(description="Фильтр по роли (advertiser|owner)")] = None,
    page: Annotated[int, Query(ge=1, le=100)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ReputationAdminHistoryResponse:
    """
    История репутации всех пользователей для администратора.

    Args:
        current_user: Текущий пользователь (требуется admin).
        session: Асинхронная сессия БД.
        user_id: Фильтр по ID пользователя (опционально).
        role: Фильтр по роли advertiser|owner (опционально).
        page: Номер страницы (default: 1).
        limit: Количество записей (default: 50, max: 100).

    Returns:
        ReputationAdminHistoryResponse: История с пагинацией.

    Raises:
        HTTPException 403: Если пользователь не администратор.
    """
    # Проверка на админа
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    from sqlalchemy import func, select

    from src.db.models.user import User

    # Построение запроса с JOIN к users для получения username
    conditions = []
    if user_id is not None:
        conditions.append(ReputationHistory.user_id == user_id)
    if role is not None:
        conditions.append(ReputationHistory.role == role)

    # Подсчёт общего количества
    count_query = select(func.count()).select_from(ReputationHistory)
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Запрос данных с пагинацией и JOIN к users
    query = (
        select(ReputationHistory, User.username)
        .join(User, ReputationHistory.user_id == User.id)
        .where(*conditions)
        if conditions
        else select(ReputationHistory, User.username).join(
            User, ReputationHistory.user_id == User.id
        )
    )
    query = (
        query.order_by(ReputationHistory.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )

    result = await session.execute(query)
    rows = result.all()

    items = []
    for h, username in rows:
        items.append(
            ReputationAdminHistoryItem(
                id=h.id,
                user_id=h.user_id,
                username=username,
                role=h.role,
                action=h.action.value,
                delta=h.delta,
                score_before=h.score_before,
                score_after=h.score_after,
                created_at=h.created_at.isoformat(),
            )
        )

    pages = (total + limit - 1) // limit if total > 0 else 1

    return ReputationAdminHistoryResponse(
        items=items,
        total=total,
        page=page,
        pages=pages,
    )
