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
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementStatus
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepository
from src.db.repositories.telegram_chat_repo import TelegramChatRepository

logger = logging.getLogger(__name__)

PLACEMENT_NOT_FOUND = "Placement not found"
NOT_CHANNEL_OWNER = "Not channel owner"
NOT_PLACEMENT_ADVERTISER = "Not placement advertiser"

router = APIRouter(tags=["placements"])


# ---------------------------------------------------------------------------
# Action helpers for update_placement (reduce cognitive complexity)
# ---------------------------------------------------------------------------


async def _action_accept(
    service: "PlacementRequestService",
    placement_id: int,
    user_id: int,
    is_owner: bool,
) -> "PlacementResponse":
    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can accept placement")
    result = await service.owner_accept(placement_id, user_id)
    return PlacementResponse.model_validate(result)


async def _action_reject(
    service: "PlacementRequestService",
    placement_id: int,
    user_id: int,
    is_owner: bool,
    update_data: "PlacementUpdateRequest",
) -> "PlacementResponse":
    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can reject placement")
    reason_text = update_data.reason_text or update_data.reason_code or "rejected"
    result = await service.owner_reject(placement_id, user_id, reason_text)
    return PlacementResponse.model_validate(result)


async def _action_counter(
    service: "PlacementRequestService",
    placement_id: int,
    user_id: int,
    is_owner: bool,
    update_data: "PlacementUpdateRequest",
) -> "PlacementResponse":
    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can make counter offer")
    if update_data.price is None:
        raise HTTPException(status_code=400, detail="price required for counter action")
    result = await service.owner_counter_offer(
        placement_id, user_id, Decimal(str(update_data.price))
    )
    return PlacementResponse.model_validate(result)


async def _action_pay(
    service: "PlacementRequestService",
    placement_id: int,
    user_id: int,
    is_advertiser: bool,
    placement_status: PlacementStatus,
) -> "PlacementResponse":
    if not is_advertiser:
        raise HTTPException(status_code=403, detail="Only advertiser can pay placement")
    if placement_status != PlacementStatus.pending_payment:
        raise HTTPException(status_code=409, detail="Placement not in pending_payment status")
    result = await service.process_payment(placement_id, user_id)
    return PlacementResponse.model_validate(result)


async def _action_cancel(
    service: "PlacementRequestService",
    placement_id: int,
    user_id: int,
    is_advertiser: bool,
) -> "PlacementResponse":
    if not is_advertiser:
        raise HTTPException(status_code=403, detail="Only advertiser can cancel placement")
    result = await service.advertiser_cancel(placement_id, user_id)
    return PlacementResponse.model_validate(result)

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

    model_config = {"populate_by_name": True}

    channel_id: int = Field(..., description="ID канала")
    proposed_price: int = Field(..., ge=100, description="Предложенная цена >= 100")
    post_text: str = Field(
        ..., min_length=10, max_length=4096, description="Текст поста",
        validation_alias="ad_text",
    )
    publication_format: str | None = Field(None, description="Формат публикации")
    media_file_id: str | None = Field(None, description="Telegram file_id медиа")
    scheduled_at: datetime = Field(
        ..., description="Желаемая дата публикации UTC",
        validation_alias="proposed_schedule",
    )
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
    publication_format: str
    proposed_price: Decimal
    final_price: Decimal | None = None
    ad_text: str
    proposed_schedule: datetime | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None
    counter_offer_count: int
    is_test: bool = False
    test_label: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


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


@router.get("/")
async def list_placements(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
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

    return [PlacementResponse.model_validate(p) for p in placements]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def create_placement(
    request: PlacementCreateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Создать заявку на размещение."""
    # Проверка на блокировку
    rep_repo = ReputationRepository(session)
    rep_score = await rep_repo.get_by_user(current_user.id)
    if rep_score and rep_score.is_advertiser_blocked:
        raise HTTPException(status_code=403, detail="Advertiser is blocked")

    # Проверка канала
    channel_repo = TelegramChatRepository(session)
    channel = await channel_repo.get_by_id(request.channel_id)
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
            publication_format=request.publication_format,
        )
        return PlacementResponse.model_validate(placement)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{placement_id}",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Получить заявку по ID."""
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied — not your placement")

    return PlacementResponse.model_validate(placement)


@router.post(
    "/{placement_id}/accept",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def accept_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Владелец принимает заявку."""
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    channel_repo = TelegramChatRepository(session)
    channel = await channel_repo.get_by_id(placement.channel_id)
    if not channel or channel.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail=NOT_CHANNEL_OWNER)

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
        billing_service=None,
    )

    try:
        result = await service.owner_accept(placement_id, current_user.id)
        return PlacementResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post(
    "/{placement_id}/reject",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def reject_placement(
    placement_id: int,
    request: RejectRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Владелец отклоняет заявку."""
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    channel_repo = TelegramChatRepository(session)
    channel = await channel_repo.get_by_id(placement.channel_id)
    if not channel or channel.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail=NOT_CHANNEL_OWNER)

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
        return PlacementResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post(
    "/{placement_id}/counter",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def counter_offer(
    placement_id: int,
    request: CounterOfferRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Владелец делает контр-предложение."""
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    channel_repo = TelegramChatRepository(session)
    channel = await channel_repo.get_by_id(placement.channel_id)
    if not channel or channel.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail=NOT_CHANNEL_OWNER)

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
        return PlacementResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post(
    "/{placement_id}/accept-counter",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def accept_counter_offer(
    placement_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Рекламодатель принимает контр-предложение."""
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail=NOT_PLACEMENT_ADVERTISER)

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
        billing_service=None,
    )

    try:
        result = await service.advertiser_accept_counter(placement_id, current_user.id)
        return PlacementResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post(
    "/{placement_id}/pay",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def pay_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Рекламодатель оплачивает → эскроу."""
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail=NOT_PLACEMENT_ADVERTISER)

    if placement.status != PlacementStatus.pending_payment:
        raise HTTPException(status_code=409, detail="Placement not in pending_payment status")

    # Проверка баланса (для не-тестовых кампаний)
    if not placement.is_test and current_user.credits < (placement.final_price or placement.proposed_price):
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
        return PlacementResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.delete(
    "/{placement_id}",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def cancel_placement(
    placement_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementResponse:
    """Рекламодатель отменяет заявку."""
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    if placement.advertiser_id != current_user.id:
        raise HTTPException(status_code=403, detail=NOT_PLACEMENT_ADVERTISER)

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
        billing_service=None,
    )

    try:
        result = await service.advertiser_cancel(placement_id, current_user.id)
        return PlacementResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


# =============================================================================
# Unified PATCH endpoint (P6)
# =============================================================================


@router.patch(
    "/{placement_id}",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def update_placement(
    placement_id: int,
    update_data: PlacementUpdateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
    repo = PlacementRequestRepository(session)
    placement = await repo.get_by_id(placement_id)

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    # Проверка канала и владельца
    channel_repo = TelegramChatRepository(session)
    channel = await channel_repo.get_by_id(placement.channel_id)
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
    _action_dispatch = {
        PlacementAction.accept: lambda: _action_accept(service, placement_id, current_user.id, is_owner),
        PlacementAction.reject: lambda: _action_reject(service, placement_id, current_user.id, is_owner, update_data),
        PlacementAction.counter: lambda: _action_counter(service, placement_id, current_user.id, is_owner, update_data),
        PlacementAction.pay: lambda: _action_pay(service, placement_id, current_user.id, is_advertiser, placement.status),
        PlacementAction.cancel: lambda: _action_cancel(service, placement_id, current_user.id, is_advertiser),
    }
    handler = _action_dispatch.get(update_data.action)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {update_data.action}")
    try:
        return await handler()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
