"""
FastAPI router для управления заявками на размещение (PlacementRequest).
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from src.api.dependencies import CurrentUser, get_db_session
from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementStatus
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/placements", tags=["placements"])

# =============================================================================
# Schemas
# =============================================================================


class PlacementCreateRequest(BaseModel):
    """Запрос на создание заявки."""

    channel_id: int = Field(..., description="ID канала")
    proposed_price: int = Field(..., ge=100, description="Предложенная цена >= 100")
    post_text: str = Field(..., min_length=10, max_length=4096, description="Текст поста")
    media_file_id: str | None = Field(None, description="Telegram file_id медиа")
    scheduled_at: datetime = Field(..., description="Желаемая дата публикации UTC")


class PlacementResponse(BaseModel):
    """Ответ с данными заявки."""

    id: int
    advertiser_id: int
    channel_id: int
    status: str
    proposed_price: Decimal
    final_price: Decimal | None
    post_text: str
    media_file_id: str | None
    scheduled_at: datetime | None
    published_at: datetime | None
    expires_at: datetime
    counter_offer_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CounterOfferRequest(BaseModel):
    """Запрос на контр-предложение."""

    counter_price: int = Field(..., ge=100, description="Цена >= 100")
    counter_comment: str | None = Field(None, max_length=500, description="Комментарий")


class RejectRequest(BaseModel):
    """Запрос на отклонение."""

    reason_code: str = Field(..., description="Код причины")
    reason_text: str | None = Field(None, description="Текст для code=other")

    @field_validator("reason_text")
    @classmethod
    def validate_other_reason(cls, v: str | None, info) -> str | None:
        """Валидация текста для other причины."""
        # Проверка будет выполнена в сервисе
        return v


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=list[PlacementResponse])
async def list_placements(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    role: Annotated[str, Query(description="Роль: advertiser или owner")] = "advertiser",
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PlacementResponse]:
    """Список заявок текущего пользователя."""
    if role not in ("advertiser", "owner"):
        raise HTTPException(status_code=400, detail="Invalid role value")

    repo = PlacementRequestRepo(session)

    if role == "advertiser":
        status_enum = PlacementStatus(status_filter) if status_filter else None
        placements = await repo.get_by_advertiser(
            current_user.id, status=status_enum, limit=limit, offset=offset
        )
    else:
        placements = await repo.get_by_channel(
            current_user.id, status=None, limit=limit, offset=offset
        )

    return placements


@router.post("/", response_model=PlacementResponse, status_code=status.HTTP_201_CREATED)
async def create_placement(
    request: PlacementCreateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Создать заявку на размещение."""
    # Проверка на блокировку
    rep_repo = ReputationRepo(session)
    rep_score = await rep_repo.get_by_user(current_user.id)
    if rep_score and rep_score.is_advertiser_blocked:
        raise HTTPException(status_code=403, detail="Advertiser is blocked")

    # Проверка канала
    from src.db.models.analytics import TelegramChat

    channel = await session.get(TelegramChat, request.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel.is_active:
        raise HTTPException(status_code=409, detail="Channel not accepting ads")

    # Создание заявки
    from src.db.repositories.campaign_repo import CampaignRepo

    campaign_repo = CampaignRepo(session)
    campaign = await campaign_repo.create(
        advertiser_id=current_user.id,
        title=f"Placement #{request.channel_id}",
        text=request.post_text,
        status="draft",
    )

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        placement = await service.create_request(
            advertiser_id=current_user.id,
            campaign_id=campaign.id,
            channel_id=request.channel_id,
            proposed_price=Decimal(str(request.proposed_price)),
            final_text=request.post_text,
            proposed_schedule=request.scheduled_at,
        )
        return placement
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{placement_id}", response_model=PlacementResponse)
async def get_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Получить заявку по ID."""
    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied — not your placement")

    return placement


@router.post("/{placement_id}/accept", response_model=PlacementResponse)
async def accept_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Владелец принимает заявку."""
    from src.db.models.analytics import TelegramChat

    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel or channel.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        result = await service.owner_accept(placement_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/{placement_id}/reject", response_model=PlacementResponse)
async def reject_placement(
    placement_id: int,
    request: RejectRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Владелец отклоняет заявку."""
    from src.db.models.analytics import TelegramChat

    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel or channel.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    # Формируем финальную причину
    reason_text = request.reason_text
    if request.reason_code == "other" and not reason_text:
        raise HTTPException(status_code=422, detail="reason_text required for 'other' code")

    final_reason = reason_text or request.reason_code

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        result = await service.owner_reject(placement_id, current_user.id, final_reason)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/{placement_id}/counter", response_model=PlacementResponse)
async def counter_offer(
    placement_id: int,
    request: CounterOfferRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Владелец делает контр-предложение."""
    from src.db.models.analytics import TelegramChat

    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel or channel.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        result = await service.owner_counter_offer(
            placement_id, current_user.id, Decimal(str(request.counter_price))
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/{placement_id}/accept-counter", response_model=PlacementResponse)
async def accept_counter_offer(
    placement_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Рекламодатель принимает контр-предложение."""
    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not placement advertiser")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        result = await service.advertiser_accept_counter(placement_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/{placement_id}/pay", response_model=PlacementResponse)
async def pay_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Рекламодатель оплачивает → эскроу."""
    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not placement advertiser")

    if placement.status != PlacementStatus.PENDING_PAYMENT:
        raise HTTPException(status_code=409, detail="Placement not in pending_payment status")

    # Проверка баланса
    if current_user.credits < (placement.final_price or placement.proposed_price):
        raise HTTPException(status_code=400, detail="Insufficient credits")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        result = await service.process_payment(placement_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.delete("/{placement_id}", response_model=PlacementResponse)
async def cancel_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Рекламодатель отменяет заявку."""
    repo = PlacementRequestRepo(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not placement advertiser")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepo(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepo(session),
        billing_service=None,
    )

    try:
        result = await service.advertiser_cancel(placement_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
