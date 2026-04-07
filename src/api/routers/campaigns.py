"""
Campaigns router для управления рекламными кампаниями.
"""

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import CurrentUser
from src.db.models.placement_request import PlacementRequest as Campaign
from src.db.models.placement_request import PlacementStatus as CampaignStatus
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()

CAMPAIGN_NOT_FOUND = "Campaign not found"
ACCESS_DENIED = "Access denied"

CampaignStatusLiteral = Literal[
    "draft", "queued", "running", "done", "error", "paused", "cancelled"
]


# === Pydantic схемы ===


class CampaignFiltersInput(BaseModel):
    """Фильтры таргетинга для кампании."""

    topics: list[str] | None = None
    min_members: int = 0
    max_members: int = 1000000
    blacklist: list[int] | None = None


class CampaignCreate(BaseModel):
    """Создание кампании."""

    title: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1, max_length=5000)
    topic: str | None = Field(None, max_length=100)
    ai_description: str | None = None
    filters: CampaignFiltersInput | None = None
    scheduled_at: str | None = None


class CampaignUpdate(BaseModel):
    """Обновление кампании."""

    title: str | None = Field(None, min_length=1, max_length=255)
    text: str | None = Field(None, min_length=1, max_length=5000)
    filters_json: dict[str, Any] | None = None
    scheduled_at: str | None = None


class CampaignResponse(BaseModel):
    """Ответ с данными кампании."""

    id: int
    title: str
    text: str
    status: str
    filters_json: dict[str, Any] | None = None
    scheduled_at: str | None = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Список кампаний с пагинацией."""

    placement_requests: list[CampaignResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# === Эндпоинты ===


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_placement_request(
    placement_request_data: CampaignCreate,
    current_user: CurrentUser,
):
    """
    Создать новую рекламную кампанию.

    Args:
        placement_request_data: Данные кампании.
        current_user: Текущий пользователь.

    Returns:
        Созданная кампания.
    """
    async with async_session_factory() as session:
        placement_repo = PlacementRequestRepository(session)

        # Создаём кампанию со статусом draft
        placement_request = await placement_repo.create(
            {
                "advertiser_id": current_user.id,
                "ad_text": placement_request_data.text,
                "status": CampaignStatus.pending_owner,
            }
        )

        logger.info(f"Campaign {placement_request.id} created by user {current_user.id}")

        return placement_request


@router.get("", response_model=CampaignListResponse)
async def get_placement_requests(  # noqa: B008
    current_user: CurrentUser,
    status: Annotated[CampaignStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    Получить список кампаний пользователя.

    Args:
        current_user: Текущий пользователь.
        status: Фильтр по статусу.
        page: Номер страницы.
        page_size: Размер страницы.

    Returns:
        Список кампаний с пагинацией.
    """
    async with async_session_factory() as session:
        placement_repo = PlacementRequestRepository(session)

        statuses = [status] if status else None
        all_placements = await placement_repo.get_by_advertiser(
            advertiser_id=current_user.id,
            statuses=statuses,
        )
        total = len(all_placements)
        offset = (page - 1) * page_size
        placement_requests = all_placements[offset : offset + page_size]

        has_more = (page * page_size) < total

        return CampaignListResponse(
            placement_requests=[CampaignResponse.model_validate(c) for c in placement_requests],
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )


@router.get(
    "/{placement_request_id}",
    response_model=CampaignResponse,
    responses={404: {"description": "Not found"}, 403: {"description": "Forbidden"}},
)
async def get_placement_request(
    placement_request_id: int,
    current_user: CurrentUser,
):
    """
    Получить кампанию по ID.

    Args:
        placement_request_id: ID кампании.
        current_user: Текущий пользователь.

    Returns:
        Данные кампании.
    """
    async with async_session_factory() as session:
        placement_repo = PlacementRequestRepository(session)
        placement_request = await placement_repo.get_by_id(placement_request_id)

        if not placement_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CAMPAIGN_NOT_FOUND,
            )

        # Проверяем принадлежность
        if placement_request.advertiser_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ACCESS_DENIED,
            )

        return placement_request


@router.patch(
    "/{placement_request_id}",
    response_model=CampaignResponse,
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
        400: {"description": "Bad request"},
    },
)
async def update_placement_request(
    placement_request_id: int,
    placement_request_data: CampaignUpdate,
    current_user: CurrentUser,
):
    """
    Обновить кампанию.

    Args:
        placement_request_id: ID кампании.
        placement_request_data: Данные для обновления.
        current_user: Текущий пользователь.

    Returns:
        Обновлённая кампания.
    """
    async with async_session_factory() as session:
        placement_repo = PlacementRequestRepository(session)
        placement_request = await placement_repo.get_by_id(placement_request_id)

        if not placement_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CAMPAIGN_NOT_FOUND,
            )

        if placement_request.advertiser_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ACCESS_DENIED,
            )

        # Можно обновлять только draft кампании
        if placement_request.status != CampaignStatus.pending_owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only update draft placement_requests",
            )

        # Обновляем
        update_data = placement_request_data.model_dump(exclude_unset=True)
        updated = await placement_repo.update(placement_request_id, update_data)

        return updated


@router.delete(
    "/{placement_request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Not found"}, 403: {"description": "Forbidden"}},
)
async def delete_placement_request(
    placement_request_id: int,
    current_user: CurrentUser,
):
    """
    Удалить кампанию.

    Args:
        placement_request_id: ID кампании.
        current_user: Текущий пользователь.
    """
    async with async_session_factory() as session:
        placement_repo = PlacementRequestRepository(session)
        placement_request = await placement_repo.get_by_id(placement_request_id)

        if not placement_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CAMPAIGN_NOT_FOUND,
            )

        if placement_request.advertiser_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ACCESS_DENIED,
            )

        await placement_repo.delete(placement_request_id)


@router.post(
    "/{placement_request_id}/start",
    responses={404: {"description": "Not found"}, 403: {"description": "Forbidden"}},
)
async def start_placement_request(
    placement_request_id: int,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Запустить кампанию.

    Args:
        placement_request_id: ID кампании.
        current_user: Текущий пользователь.

    Returns:
        Статус операции.
    """
    async with async_session_factory() as session:
        placement_repo = PlacementRequestRepository(session)
        placement_request = await placement_repo.get_by_id(placement_request_id)

        if not placement_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CAMPAIGN_NOT_FOUND,
            )

        if placement_request.advertiser_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ACCESS_DENIED,
            )

        # Обновляем статус
        await placement_repo.update_status(placement_request_id, CampaignStatus.pending_payment)

        logger.info(f"Campaign {placement_request_id} started by user {current_user.id}")

        return {"status": "queued", "placement_request_id": placement_request_id}


@router.post(
    "/{placement_request_id}/cancel",
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
        400: {"description": "Bad request"},
    },
)
async def cancel_placement_request(
    placement_request_id: int,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Отменить кампанию.

    Args:
        placement_request_id: ID кампании.
        current_user: Текущий пользователь.

    Returns:
        Статус операции.
    """
    async with async_session_factory() as session:
        placement_repo = PlacementRequestRepository(session)
        placement_request = await placement_repo.get_by_id(placement_request_id)

        if not placement_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CAMPAIGN_NOT_FOUND,
            )

        if placement_request.advertiser_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ACCESS_DENIED,
            )

        # Можно отменить только queued или running
        if placement_request.status not in [CampaignStatus.pending_payment, CampaignStatus.escrow]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel placement_request with status {placement_request.status.value}",
            )

        await placement_repo.update_status(
            placement_request_id,
            CampaignStatus.cancelled,
        )

        logger.info(f"Campaign {placement_request_id} cancelled by user {current_user.id}")

        return {"status": "cancelled", "placement_request_id": placement_request_id}


# ─── Mini App API ───────────────────────────────────────────────


class CampaignItem(BaseModel):
    """Краткая информация о кампании для списка."""

    id: int
    title: str
    status: str
    created_at: str
    sent_count: int
    target_count: int | None = None
    error_msg: str | None = None


class CampaignsListResponse(BaseModel):
    """Список кампаний для Mini App."""

    items: list[CampaignItem]
    total: int
    page: int
    pages: int


class CampaignStats(BaseModel):
    """Детальная статистика кампании."""

    placement_request_id: int
    title: str
    status: str
    total_logs: int
    sent: int
    failed: int
    skipped: int
    success_rate: float
    started_at: str | None = None
    finished_at: str | None = None


@router.get("/list", response_model=CampaignsListResponse)
async def list_placement_requests_mini_app(
    current_user: CurrentUser,
    status_filter: Annotated[CampaignStatusLiteral | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """
    Список кампаний пользователя для Mini App.
    """
    async with async_session_factory() as session:
        # Базовый запрос
        base_q = select(Campaign).where(Campaign.advertiser_id == current_user.id)
        count_q = select(func.count(Campaign.id)).where(Campaign.advertiser_id == current_user.id)

        if status_filter:
            base_q = base_q.where(Campaign.status == status_filter)
            count_q = count_q.where(Campaign.status == status_filter)

        # Считаем total
        total_result = await session.execute(count_q)
        total = total_result.scalar() or 0

        # Получаем страницу
        offset = (page - 1) * limit
        result = await session.execute(
            base_q.order_by(Campaign.created_at.desc()).offset(offset).limit(limit)
        )
        placement_requests = result.scalars().all()

        # Используем агрегированные данные из PlacementRequest
        items = []
        for camp in placement_requests:
            sent_count = camp.sent_count or 0

            items.append(
                CampaignItem(
                    id=camp.id,
                    title=camp.ad_text[:50] if camp.ad_text else "Без названия",
                    status=camp.status.value if hasattr(camp.status, "value") else str(camp.status),
                    created_at=camp.created_at.isoformat() if camp.created_at else "",
                    sent_count=sent_count,
                    target_count=None,
                    error_msg=getattr(camp, "error_message", None),
                )
            )

    pages = max(1, (total + limit - 1) // limit)
    return CampaignsListResponse(items=items, total=total, page=page, pages=pages)


@router.get(
    "/{placement_request_id}/stats",
    response_model=CampaignStats,
    responses={404: {"description": "Not found"}},
)
async def get_placement_request_stats(
    placement_request_id: int,
    current_user: CurrentUser,
):
    """Детальная статистика по одной кампании."""
    async with async_session_factory() as session:
        # Проверяем что кампания принадлежит пользователю
        result = await session.execute(
            select(Campaign).where(
                Campaign.id == placement_request_id,
                Campaign.advertiser_id == current_user.id,
            )
        )
        placement_request = result.scalar_one_or_none()
        if not placement_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CAMPAIGN_NOT_FOUND,
            )

    # Возвращаем реальные данные из агрегированных полей PlacementRequest
    camp_status = (
        placement_request.status.value
        if hasattr(placement_request.status, "value")
        else str(placement_request.status)
    )

    total_sent = placement_request.sent_count or 0
    total_failed = placement_request.failed_count or 0
    total = total_sent + total_failed

    return CampaignStats(
        placement_request_id=placement_request.id,
        title=placement_request.ad_text[:50] if placement_request.ad_text else "Без названия",
        status=camp_status,
        total_logs=total,
        sent=total_sent,
        failed=total_failed,
        skipped=0,
        success_rate=round(total_sent / total * 100, 1) if total > 0 else 0.0,
        started_at=placement_request.last_published_at.isoformat()
        if placement_request.last_published_at
        else None,
        finished_at=None,
    )


# ─── Дублировать кампанию ────────────────────────────────────────


class DuplicateResponse(BaseModel):
    id: int
    title: str


@router.post("/{placement_request_id}/duplicate", responses={404: {"description": "Not found"}})
async def duplicate_placement_request(
    placement_request_id: int,
    current_user: CurrentUser,
) -> DuplicateResponse:
    """
    Создать копию кампании в статусе 'draft'.
    Копируется: title, text, filters_json.
    Не копируется: статус, логи, scheduled_at.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Campaign).where(
                Campaign.id == placement_request_id,
                Campaign.advertiser_id == current_user.id,
            )
        )
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CAMPAIGN_NOT_FOUND,
            )

        new_ad_text = source.ad_text

        new_placement_request = Campaign(
            advertiser_id=current_user.id,
            ad_text=new_ad_text,
            status=CampaignStatus.pending_owner,
        )
        session.add(new_placement_request)
        try:
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Конфликт данных: запись уже существует или нарушено ограничение",
            ) from e
        await session.refresh(new_placement_request)

    return DuplicateResponse(
        id=new_placement_request.id, title=new_ad_text[:50] if new_ad_text else ""
    )
