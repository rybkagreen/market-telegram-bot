"""
FastAPI router для управления спорами (Disputes).

Endpoints:
  GET  /api/disputes/         — список диспутов текущего пользователя
  POST /api/disputes/         — создать диспут
  GET  /api/disputes/{id}     — детали диспута
  PATCH /api/disputes/{id}    — ответить на диспут (владелец)
  GET  /api/admin/disputes    — список всех диспутов (admin)
  POST /api/admin/disputes/{id}/resolve — решить диспут (admin)
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_current_admin_user, get_db_session
from src.db.models.user import User
from src.api.schemas.admin import (
    DisputeAdminResponse,
    DisputeListAdminResponse,
    DisputeResolveRequest,
)
from src.api.schemas.dispute import (
    DisputeCreate,
    DisputeReason,
    DisputeResolution,
    DisputeResponse,
    DisputeStatus,
    DisputeUpdate,
)
from src.db.models.dispute import PlacementDispute
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User
from src.db.repositories.dispute_repo import DisputeRepository
from src.db.repositories.placement_request_repo import PlacementRequestRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Disputes"])


# ─── Helpers ────────────────────────────────────────────────────


async def _get_dispute_or_404(
    dispute_id: int,
    session: AsyncSession,
    current_user: CurrentUser,
) -> PlacementDispute:
    """
    Получить диспут по ID или вернуть 404.
    Проверяет что пользователь является участником диспута.
    """
    dispute = await session.get(PlacementDispute, dispute_id)
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found",
        )

    # Проверка что пользователь — участник (advertiser или owner)
    if dispute.advertiser_id != current_user.id and dispute.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied — not a party to this dispute",
        )

    return dispute


async def _get_placement_or_404(
    placement_id: int,
    session: AsyncSession,
    current_user: CurrentUser,
) -> PlacementRequest:
    """
    Получить заявку по ID или вернуть 404.
    Проверяет что пользователь является рекламодателем или владельцем.
    """
    placement = await session.get(PlacementRequest, placement_id)
    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement request not found",
        )

    # Проверка что пользователь — рекламодатель или владелец канала
    if placement.advertiser_id != current_user.id and placement.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied — not your placement request",
        )

    return placement


# ─── Endpoints ──────────────────────────────────────────────────


@router.get("/", response_model=list[DisputeResponse])
async def get_my_disputes(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[DisputeResponse]:
    """
    Получить список всех диспутов текущего пользователя.

    Возвращает диспуты где пользователь является рекламодателем
    или владельцем канала.

    Args:
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        list[DisputeResponse]: Список диспутов пользователя.
    """
    repo = DisputeRepository(session)
    disputes = await repo.get_by_user(current_user.id)

    return [DisputeResponse.model_validate(d) for d in disputes]


@router.get("/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(
    dispute_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> DisputeResponse:
    """
    Получить детали конкретного диспута.

    Args:
        dispute_id: ID диспута.
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        DisputeResponse: Данные диспута.

    Raises:
        HTTPException 404: Диспут не найден.
        HTTPException 403: Пользователь не является участником диспута.
    """
    dispute = await _get_dispute_or_404(dispute_id, session, current_user)
    return DisputeResponse.model_validate(dispute)


@router.post("/", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def create_dispute(
    dispute_data: DisputeCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> DisputeResponse:
    """
    Создать новый диспут по заявке на размещение.

    Доступно только рекламодателю или владельцу канала из заявки.
    Статус диспута устанавливается в 'open'.

    Args:
        dispute_data: Данные для создания диспута.
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        DisputeResponse: Созданный диспут.

    Raises:
        HTTPException 404: Заявка не найдена.
        HTTPException 403: Пользователь не имеет доступа к заявке.
        HTTPException 409: Диспут уже существует для этой заявки.
    """
    # Проверяем что заявка существует и принадлежит пользователю
    placement = await _get_placement_or_404(dispute_data.placement_id, session, current_user)

    # Проверяем что диспут ещё не создан для этой заявки
    existing_dispute = await session.get(PlacementDispute, placement.id)
    if existing_dispute:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute already exists for this placement",
        )

    # Создаём диспут
    dispute = PlacementDispute(
        placement_request_id=dispute_data.placement_id,
        advertiser_id=placement.advertiser_id,
        owner_id=placement.owner_id,
        reason=dispute_data.reason,
        advertiser_comment=dispute_data.comment,
        status=DisputeStatus.open,
    )

    session.add(dispute)
    await session.commit()
    await session.refresh(dispute)

    logger.info(f"Dispute {dispute.id} created for placement {dispute_data.placement_id}")

    return DisputeResponse.model_validate(dispute)


@router.patch("/{dispute_id}", response_model=DisputeResponse)
async def update_dispute(
    dispute_id: int,
    update_data: DisputeUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> DisputeResponse:
    """
    Ответить на диспут (добавить объяснение владельца).

    Доступно только владельцу канала из диспута.
    Обновляет поле owner_explanation и меняет статус на 'owner_explained'.

    Args:
        dispute_id: ID диспута.
        update_data: Данные для обновления (owner_comment).
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        DisputeResponse: Обновлённый диспут.

    Raises:
        HTTPException 404: Диспут не найден.
        HTTPException 403: Пользователь не является владельцем из диспута.
    """
    dispute = await _get_dispute_or_404(dispute_id, session, current_user)

    # Проверка что пользователь — владелец из диспута
    if dispute.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied — only owner can provide explanation",
        )

    # Обновляем диспут
    dispute.owner_explanation = update_data.owner_comment
    dispute.status = DisputeStatus.owner_explained

    await session.commit()
    await session.refresh(dispute)

    logger.info(f"Dispute {dispute.id} updated by owner {current_user.id}")

    return DisputeResponse.model_validate(dispute)


# ═══════════════════════════════════════════════════════════════
# Admin Endpoints (PHASE-2)
# ═══════════════════════════════════════════════════════════════


@router.get("/admin/disputes", response_model=DisputeListAdminResponse)
async def get_all_disputes_admin(
    status_filter: str = "open",
    limit: int = 20,
    offset: int = 0,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: AsyncSession = Depends(get_db_session),
) -> DisputeListAdminResponse:
    """
    Get all disputes with pagination and filtering (admin only).

    Args:
        status_filter: Filter by status (open, owner_explained, resolved, all)
        limit: Max items to return (1-100)
        offset: Offset for pagination
        admin_user: Current admin user
        session: DB session

    Returns:
        DisputeListAdminResponse with items and total count
    """
    # Validate limit
    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    # Build query
    query = select(PlacementDispute)

    # Apply status filter
    if status_filter != "all":
        try:
            status_enum = DisputeStatus(status_filter.lower())
            query = query.where(PlacementDispute.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Must be one of: open, owner_explained, resolved, all",
            )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(PlacementDispute.created_at.asc()).limit(limit).offset(offset)
    result = await session.execute(query)
    disputes = result.scalars().all()

    # Build response with usernames
    items = []
    for d in disputes:
        advertiser_username = d.advertiser.username if d.advertiser else None
        owner_username = d.owner.username if d.owner else None

        items.append(
            DisputeAdminResponse(
                id=d.id,
                placement_request_id=d.placement_request_id,
                advertiser_id=d.advertiser_id,
                owner_id=d.owner_id,
                advertiser_username=advertiser_username,
                owner_username=owner_username,
                reason=d.reason.value,
                status=d.status.value,
                owner_explanation=d.owner_explanation,
                advertiser_comment=d.advertiser_comment,
                resolution=d.resolution.value if d.resolution else None,
                resolution_comment=d.resolution_comment,
                admin_id=d.admin_id,
                resolved_at=d.resolved_at,
                advertiser_refund_pct=d.advertiser_refund_pct,
                owner_payout_pct=d.owner_payout_pct,
                expires_at=d.expires_at,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )

    return DisputeListAdminResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/admin/disputes/{dispute_id}/resolve", response_model=DisputeAdminResponse)
async def resolve_dispute_admin(
    dispute_id: int,
    body: DisputeResolveRequest,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: AsyncSession = Depends(get_db_session),
) -> DisputeAdminResponse:
    """
    Resolve a dispute (admin only).

    Args:
        dispute_id: Dispute ID
        body: Resolution data (resolution, admin_comment, custom_split_percent)
        admin_user: Current admin user
        session: DB session

    Returns:
        DisputeAdminResponse with resolution data

    Raises:
        HTTPException 404: Dispute not found
        HTTPException 400: Invalid resolution data
    """
    dispute = await session.get(PlacementDispute, dispute_id)

    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found",
        )

    # Validate custom_split_percent for partial resolution
    if body.resolution == "partial" and body.custom_split_percent is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="custom_split_percent is required for resolution=partial",
        )

    # Calculate refund/payout percentages based on resolution
    advertiser_refund_pct: float | None = None
    owner_payout_pct: float | None = None

    if body.resolution == "owner_fault":
        advertiser_refund_pct = 100.0
        owner_payout_pct = 0.0
    elif body.resolution == "advertiser_fault":
        advertiser_refund_pct = 0.0
        owner_payout_pct = 100.0
    elif body.resolution == "technical":
        advertiser_refund_pct = 100.0
        owner_payout_pct = 100.0
    elif body.resolution == "partial":
        advertiser_refund_pct = float(body.custom_split_percent) if body.custom_split_percent else 50.0
        owner_payout_pct = 100.0 - advertiser_refund_pct

    # Update dispute
    dispute.status = DisputeStatus.resolved
    dispute.resolution = DisputeResolution(body.resolution)
    dispute.resolution_comment = body.admin_comment
    dispute.admin_id = admin_user.id
    dispute.resolved_at = datetime.now(timezone.utc)
    dispute.advertiser_refund_pct = advertiser_refund_pct
    dispute.owner_payout_pct = owner_payout_pct

    await session.flush()
    await session.refresh(dispute)

    advertiser_username = dispute.advertiser.username if dispute.advertiser else None
    owner_username = dispute.owner.username if dispute.owner else None

    logger.info(
        f"Admin {admin_user.id} resolved dispute #{dispute_id} "
        f"with resolution={body.resolution}, advertiser_refund={advertiser_refund_pct}%"
    )

    return DisputeAdminResponse(
        id=dispute.id,
        placement_request_id=dispute.placement_request_id,
        advertiser_id=dispute.advertiser_id,
        owner_id=dispute.owner_id,
        advertiser_username=advertiser_username,
        owner_username=owner_username,
        reason=dispute.reason.value,
        status=dispute.status.value,
        owner_explanation=dispute.owner_explanation,
        advertiser_comment=dispute.advertiser_comment,
        resolution=dispute.resolution.value if dispute.resolution else None,
        resolution_comment=dispute.resolution_comment,
        admin_id=dispute.admin_id,
        resolved_at=dispute.resolved_at,
        advertiser_refund_pct=dispute.advertiser_refund_pct,
        owner_payout_pct=dispute.owner_payout_pct,
        expires_at=dispute.expires_at,
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
    )
