"""
FastAPI router для управления заявками на размещение (PlacementRequest).
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from src.api.dependencies import CurrentUser, get_db_session
from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementStatus
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepository
from src.db.session import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["placements"])

# =============================================================================
# Schemas
# =============================================================================


class PlacementAction(str, Enum):
    """Действия с заявкой."""

    accept = "accept"
    reject = "reject"
    counter = "counter"
    pay = "pay"
    cancel = "cancel"


class PlacementUpdateRequest(BaseModel):
    """Запрос на обновление заявки (action-based)."""

    action: PlacementAction = Field(..., description="Действие: accept|reject|counter|pay|cancel")
    price: int | None = Field(None, ge=100, description="Цена для counter/pay")
    schedule: datetime | None = Field(None, description="Дата публикации")
    comment: str | None = Field(None, max_length=500, description="Комментарий")
    reason_code: str | None = Field(None, description="Код причины для reject")
    reason_text: str | None = Field(None, description="Текст причины для reject")


class PlacementCreateRequest(BaseModel):
    """Запрос на создание заявки."""

    channel_id: int = Field(..., description="ID канала")
    proposed_price: int = Field(..., ge=100, description="Предложенная цена >= 100")
    post_text: str = Field(..., min_length=10, max_length=4096, description="Текст поста")
    media_file_id: str | None = Field(None, description="Telegram file_id медиа")
    scheduled_at: datetime = Field(..., description="Желаемая дата публикации UTC")
    # Test mode fields (admin only)
    is_test: bool = Field(
        default=False,
        description="Тестовая кампания (без оплаты, только для админов)",
    )
    test_label: str | None = Field(
        default=None,
        max_length=64,
        description="Пометка теста",
    )


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
    is_test: bool = False
    test_label: str | None = None
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
    channel_id: Annotated[int | None, Query(description="Фильтр по ID канала")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PlacementResponse]:
    """
    Список заявок текущего пользователя.

    Args:
        current_user: Текущий пользователь.
        session: Асинхронная сессия БД.
        role: Роль (advertiser или owner).
        status_filter: Фильтр по статусу.
        channel_id: Фильтр по ID канала (опционально).
        limit: Лимит записей.
        offset: Смещение.

    Returns:
        list[PlacementResponse]: Список заявок.
    """
    if role not in ("advertiser", "owner"):
        raise HTTPException(status_code=400, detail="Invalid role value")

    repo = PlacementRequestRepository(session)

    if role == "advertiser":
        status_enum = PlacementStatus(status_filter) if status_filter else None
        placements = await repo.get_by_advertiser(
            current_user.id, statuses=[status_enum] if status_enum else None
        )
        # Apply pagination manually
        placements = placements[offset:offset + limit] if limit else placements[offset:]
    else:
        placements = await repo.get_by_channel(
            current_user.id, statuses=None
        )
        # Apply pagination manually
        placements = placements[offset:offset + limit] if limit else placements[offset:]

    # Фильтр по channel_id если указан
    if channel_id is not None:
        placements = [p for p in placements if p.channel_id == channel_id]

    return placements


@router.post("/", response_model=PlacementResponse, status_code=status.HTTP_201_CREATED)
async def create_placement(
    request: PlacementCreateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """Создать заявку на размещение."""
    # Проверка на блокировку
    rep_repo = ReputationRepository(session)
    rep_score = await rep_repo.get_by_user(current_user.id)
    if rep_score and rep_score.is_advertiser_blocked:
        raise HTTPException(status_code=403, detail="Advertiser is blocked")

    # Проверка канала
    from src.db.models.telegram_chat import TelegramChat

    channel = await session.get(TelegramChat, request.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel.is_active:
        raise HTTPException(status_code=409, detail="Channel not accepting ads")

    # is_test может быть установлен только админом
    is_test = request.is_test and current_user.is_admin
    test_label = request.test_label if is_test else None

    # Создание заявки
    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
        billing_service=None,
    )

    try:
        placement = await service.create_request(
            advertiser_id=current_user.id,
            channel_id=request.channel_id,
            proposed_price=Decimal(str(request.proposed_price)),
            final_text=request.post_text,
            proposed_schedule=request.scheduled_at,
            is_test=is_test,
            test_label=test_label,
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
    repo = PlacementRequestRepository(session)
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
    from src.db.models.telegram_chat import TelegramChat

    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel or channel.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
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
    from src.db.models.telegram_chat import TelegramChat

    repo = PlacementRequestRepository(session)
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
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
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
    from src.db.models.telegram_chat import TelegramChat

    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel or channel.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not channel owner")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
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
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not placement advertiser")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
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
    repo = PlacementRequestRepository(session)
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
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
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
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not placement advertiser")

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
        billing_service=None,
    )

    try:
        result = await service.advertiser_cancel(placement_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


# =============================================================================
# Unified PATCH endpoint (P6)
# =============================================================================


@router.patch("/{placement_id}", response_model=PlacementResponse)
async def update_placement(
    placement_id: int,
    update_data: PlacementUpdateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """
    Обновить заявку через action-based интерфейс.

    Универсальный endpoint для всех действий с заявкой:
    - accept: Владелец принимает заявку
    - reject: Владелец отклоняет заявку
    - counter: Владелец делает контр-предложение
    - pay: Рекламодатель оплачивает заявку
    - cancel: Рекламодатель отменяет заявку

    Args:
        placement_id: ID заявки.
        update_data: Данные обновления (action, price, comment, etc.).
        current_user: Текущий пользователь.
        session: Асинхронная сессия БД.

    Returns:
        PlacementResponse: Обновлённая заявка.

    Raises:
        HTTPException 400: Некорректное действие или данные.
        HTTPException 403: Недостаточно прав.
        HTTPException 404: Заявка не найдена.
        HTTPException 409: Конфликт статуса.
    """
    from src.db.models.telegram_chat import TelegramChat

    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    # Проверка канала и владельца
    channel = await session.get(TelegramChat, placement.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    is_owner = channel.owner_id == current_user.id
    is_advertiser = placement.advertiser_id == current_user.id

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
        billing_service=None,
    )

    # Выполнение действия
    try:
        if update_data.action == PlacementAction.accept:
            # Владелец принимает заявку
            if not is_owner:
                raise HTTPException(status_code=403, detail="Only owner can accept placement")
            return await service.owner_accept(placement_id, current_user.id)

        elif update_data.action == PlacementAction.reject:
            # Владелец отклоняет заявку
            if not is_owner:
                raise HTTPException(status_code=403, detail="Only owner can reject placement")
            reason_text = update_data.reason_text or update_data.reason_code or "rejected"
            return await service.owner_reject(placement_id, current_user.id, reason_text)

        elif update_data.action == PlacementAction.counter:
            # Владелец делает контр-предложение
            if not is_owner:
                raise HTTPException(status_code=403, detail="Only owner can make counter offer")
            if update_data.price is None:
                raise HTTPException(status_code=400, detail="price required for counter action")
            return await service.owner_counter_offer(
                placement_id, current_user.id, Decimal(str(update_data.price))
            )

        elif update_data.action == PlacementAction.pay:
            # Рекламодатель оплачивает заявку
            if not is_advertiser:
                raise HTTPException(status_code=403, detail="Only advertiser can pay placement")
            if placement.status != PlacementStatus.pending_payment:
                raise HTTPException(status_code=409, detail="Placement not in pending_payment status")
            return await service.process_payment(placement_id, current_user.id)

        elif update_data.action == PlacementAction.cancel:
            # Рекламодатель отменяет заявку
            if not is_advertiser:
                raise HTTPException(status_code=403, detail="Only advertiser can cancel placement")
            return await service.advertiser_cancel(placement_id, current_user.id)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {update_data.action}")

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
