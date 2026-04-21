"""
FastAPI router для управления спорами (Disputes).

Endpoints:
  GET  /api/disputes/         — список диспутов текущего пользователя (пагинированный)
  POST /api/disputes/         — создать диспут
  GET  /api/disputes/{id}     — детали диспута
  PATCH /api/disputes/{id}    — ответить на диспут (владелец)
  GET  /api/disputes/evidence/{placement_id} — доказательная база
  GET  /api/disputes/admin/disputes    — список всех диспутов (admin)
  POST /api/disputes/admin/disputes/{id}/resolve — решить диспут с финансами (admin)
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_current_admin_user, get_db_session
from src.api.schemas.admin import (
    DisputeAdminResponse,
    DisputeListAdminResponse,
    DisputeResolveRequest,
)
from src.api.schemas.dispute import (
    DisputeCreate,
    DisputeListResponse,
    DisputeResolution,
    DisputeResponse,
    DisputeStatus,
    DisputeUpdate,
)
from src.core.services.billing_service import billing_service
from src.db.models.dispute import DisputeStatus as ModelDisputeStatus
from src.db.models.dispute import PlacementDispute
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.repositories.dispute_repo import DisputeRepository
from src.db.repositories.publication_log_repo import PublicationLogRepo

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


@router.get("/")
async def get_my_disputes(
    status_filter: str = "all",
    limit: int = 20,
    offset: int = 0,
    *,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DisputeListResponse:
    """
    Получить список всех диспутов текущего пользователя с пагинацией.

    Возвращает диспуты где пользователь является рекламодателем
    или владельцем канала.

    Args:
        status_filter: Фильтр по статусу (open, owner_explained, resolved, closed, all)
        limit: Макс. количество записей (1-100)
        offset: Смещение для пагинации
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        DisputeListResponse: Пагинированный список диспутов.
    """
    # Validate limit
    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    repo = DisputeRepository(session)
    disputes, total = await repo.get_by_user_paginated(
        current_user.id, status_filter, limit, offset
    )

    return DisputeListResponse(
        items=[DisputeResponse.model_validate(d) for d in disputes],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{dispute_id}",
    responses={404: {"description": "Not found"}, 403: {"description": "Forbidden"}},
)
async def get_dispute(
    dispute_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
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


@router.get(
    "/by-placement/{placement_request_id}",
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
    },
)
async def get_dispute_by_placement(
    placement_request_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DisputeResponse | None:
    """
    Получить диспут по ID размещения.
    Доступно только рекламодателю или владельцу канала из размещения.
    Возвращает null, если диспут не существует.
    """
    placement = await _get_placement_or_404(placement_request_id, session, current_user)
    repo = DisputeRepository(session)
    dispute = await repo.get_by_placement(placement.id)
    if dispute is None:
        return None
    return DisputeResponse.model_validate(dispute)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
        409: {"description": "Conflict"},
    },
)
async def create_dispute(
    dispute_data: DisputeCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
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

    # Только рекламодатель может открыть спор по своему размещению
    if placement.advertiser_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the advertiser can open a dispute",
        )

    # Спор можно открыть только для опубликованного размещения
    if placement.status != PlacementStatus.published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute can only be opened for published placements",
        )

    # Окно открытия спора — 48 часов с момента публикации
    if placement.published_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Placement has no published_at timestamp",
        )
    now_utc = datetime.now(UTC)
    published_at = placement.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    window_seconds = (now_utc - published_at).total_seconds()
    if window_seconds > 48 * 3600:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute window of 48 hours has expired",
        )

    # Проверяем что диспут ещё не создан для этой заявки
    repo = DisputeRepository(session)
    existing_dispute = await repo.get_by_placement(dispute_data.placement_id)
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
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Конфликт данных: запись уже существует или нарушено ограничение",
        ) from e
    await session.refresh(dispute)

    logger.info(f"Dispute {dispute.id} created for placement {dispute_data.placement_id}")

    return DisputeResponse.model_validate(dispute)


@router.patch(
    "/{dispute_id}",
    responses={404: {"description": "Not found"}, 403: {"description": "Forbidden"}},
)
async def update_dispute(
    dispute_id: int,
    update_data: DisputeUpdate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
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

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Конфликт данных: запись уже существует или нарушено ограничение",
        ) from e
    await session.refresh(dispute)

    logger.info(f"Dispute {dispute.id} updated by owner {current_user.id}")

    return DisputeResponse.model_validate(dispute)


# ─── Evidence endpoint ──────────────────────────────────────────


class PublicationEventResponse(BaseModel):
    id: int
    event_type: str
    message_id: int | None = None
    post_url: str | None = None
    erid: str | None = None
    detected_at: datetime
    extra: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class EvidenceSummary(BaseModel):
    published_at: datetime | None = None
    deleted_at: datetime | None = None
    deletion_type: str | None = None  # "by_bot" | "early_by_owner" | None
    erid_present: bool
    total_duration_minutes: int


class EvidenceResponse(BaseModel):
    placement_id: int
    channel_id: int | None = None
    events: list[PublicationEventResponse]
    summary: EvidenceSummary


@router.get(
    "/evidence/{placement_request_id}",
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
    },
)
async def get_placement_evidence(  # NOSONAR: python:S3776
    placement_request_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EvidenceResponse:
    """
    Получить доказательную базу публикации для заявки.

    Доступно рекламодателю (владельцу кампании), владельцу канала или администратору.

    Args:
        placement_request_id: ID заявки.
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        EvidenceResponse: хронологический лог событий + сводка.

    Raises:
        HTTPException 404: Заявка не найдена.
        HTTPException 403: Нет доступа.
    """
    placement = await session.get(PlacementRequest, placement_request_id)
    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement request not found",
        )

    # Access check: advertiser, channel owner, or admin
    is_admin = current_user.is_admin
    is_advertiser = placement.advertiser_id == current_user.id
    is_channel_owner = False
    if placement.channel_id:
        channel = await session.get(TelegramChat, placement.channel_id)
        is_channel_owner = channel is not None and channel.owner_id == current_user.id

    if not (is_admin or is_advertiser or is_channel_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied — not your placement",
        )

    pub_log_repo = PublicationLogRepo(session)
    logs = await pub_log_repo.get_evidence(placement_request_id)

    # Build summary
    published_at: datetime | None = None
    deleted_at: datetime | None = None
    deletion_type: str | None = None
    erid_present = False

    for entry in logs:
        if entry.event_type == "published" and published_at is None:
            published_at = entry.detected_at
        if entry.event_type in ("erid_ok",):
            erid_present = True
        if entry.event_type == "deleted_by_bot" and deleted_at is None:
            deleted_at = entry.detected_at
            deletion_type = "by_bot"
        if entry.event_type == "deleted_early" and deleted_at is None:
            deleted_at = entry.detected_at
            deletion_type = "early_by_owner"

    total_duration_minutes = 0
    if published_at and deleted_at:
        delta = deleted_at - published_at
        total_duration_minutes = max(0, int(delta.total_seconds() / 60))

    channel_id: int | None = None
    if logs:
        channel_id = logs[0].channel_id

    summary = EvidenceSummary(
        published_at=published_at,
        deleted_at=deleted_at,
        deletion_type=deletion_type,
        erid_present=erid_present,
        total_duration_minutes=total_duration_minutes,
    )

    events = [PublicationEventResponse.model_validate(e) for e in logs]

    return EvidenceResponse(
        placement_id=placement_request_id,
        channel_id=channel_id,
        events=events,
        summary=summary,
    )


# ═══════════════════════════════════════════════════════════════
# Admin Endpoints (PHASE-2)
# ═══════════════════════════════════════════════════════════════


@router.get("/admin/disputes", responses={400: {"description": "Bad request"}})
async def get_all_disputes_admin(
    status_filter: Annotated[str, Query(alias="status")] = "all",
    limit: int = 20,
    offset: int = 0,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
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

    repo = DisputeRepository(session)

    # Apply status filter
    status_enum: ModelDisputeStatus | None = None
    if status_filter != "all":
        try:
            status_enum = ModelDisputeStatus(status_filter.lower())
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Must be one of: open, owner_explained, resolved, all",
            ) from err

    disputes, total = await repo.get_all_paginated(status_enum, limit, offset)

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


@router.post(
    "/admin/disputes/{dispute_id}/resolve",
    responses={404: {"description": "Not found"}, 400: {"description": "Bad request"}},
)
async def resolve_dispute_admin(
    dispute_id: int,
    body: DisputeResolveRequest,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DisputeAdminResponse:
    """
    Resolve a dispute with financial operations (admin only).

    Financial logic mirrors the Telegram bot handler:
    - owner_fault / technical → refund_escrow(scenario="before_escrow") → 100% advertiser
    - advertiser_fault → release_escrow() → 85% owner
    - partial → refund_escrow(scenario="after_confirmation") → ~50/50 split

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
        advertiser_refund_pct = (
            float(body.custom_split_percent) if body.custom_split_percent else 50.0
        )
        owner_payout_pct = 100.0 - advertiser_refund_pct

    # ── Financial operations (mirrors Telegram bot handler) ──
    placement = await session.get(PlacementRequest, dispute.placement_request_id)
    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement request not found",
        )

    price = placement.final_price if placement.final_price is not None else placement.proposed_price
    new_status: PlacementStatus = PlacementStatus.refunded

    try:
        if body.resolution in ("owner_fault", "technical"):
            # 100% refund to advertiser
            await billing_service.refund_escrow(
                session=session,
                placement_id=placement.id,
                final_price=price,
                advertiser_id=placement.advertiser_id,
                owner_id=placement.owner_id,
                scenario="before_escrow",
            )
            new_status = PlacementStatus.refunded

        elif body.resolution == "advertiser_fault":
            # 85% to owner
            await billing_service.release_escrow(
                session=session,
                placement_id=placement.id,
                final_price=price,
                advertiser_id=placement.advertiser_id,
                owner_id=placement.owner_id,
            )
            new_status = PlacementStatus.published

        elif body.resolution == "partial":
            # ~50/50 split
            await billing_service.refund_escrow(
                session=session,
                placement_id=placement.id,
                final_price=price,
                advertiser_id=placement.advertiser_id,
                owner_id=placement.owner_id,
                scenario="after_confirmation",
            )
            new_status = PlacementStatus.refunded

    except Exception as exc:
        logger.error("Dispute resolve billing error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial operation failed: {exc}",
        ) from exc

    # Update dispute
    dispute.status = DisputeStatus.resolved
    dispute.resolution = DisputeResolution(body.resolution)
    dispute.resolution_comment = body.admin_comment
    dispute.admin_id = admin_user.id
    dispute.resolved_at = datetime.now(UTC)
    dispute.advertiser_refund_pct = advertiser_refund_pct
    dispute.owner_payout_pct = owner_payout_pct

    # Update placement status
    placement.status = new_status

    await session.commit()
    await session.refresh(dispute)

    advertiser_username = dispute.advertiser.username if dispute.advertiser else None
    owner_username = dispute.owner.username if dispute.owner else None

    logger.info(
        f"Admin {admin_user.id} resolved dispute #{dispute_id} "
        f"with resolution={body.resolution}, advertiser_refund={advertiser_refund_pct}%, "
        f"placement_status={new_status.value}"
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
