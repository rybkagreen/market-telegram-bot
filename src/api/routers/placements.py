"""
FastAPI router для управления заявками на размещение (PlacementRequest).
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import CurrentUser, get_db_session
from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepository
from src.db.repositories.telegram_chat_repo import TelegramChatRepository

logger = logging.getLogger(__name__)

PLACEMENT_NOT_FOUND = "Placement not found"

router = APIRouter(tags=["placements"])


# ---------------------------------------------------------------------------
# Action helpers for update_placement (reduce cognitive complexity)
# ---------------------------------------------------------------------------


async def _action_accept(
    service: PlacementRequestService,
    placement_id: int,
    user_id: int,
    is_owner: bool,
) -> PlacementResponse:
    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can accept placement")
    result = await service.owner_accept(placement_id, user_id)
    return PlacementResponse.model_validate(result)


async def _action_reject(
    service: PlacementRequestService,
    placement_id: int,
    user_id: int,
    is_owner: bool,
    update_data: PlacementUpdateRequest,
) -> PlacementResponse:
    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can reject placement")
    reason_text = update_data.reason_text or update_data.reason_code or "rejected"
    result = await service.owner_reject(placement_id, user_id, reason_text)
    return PlacementResponse.model_validate(result)


async def _action_counter(
    service: PlacementRequestService,
    placement_id: int,
    user_id: int,
    is_owner: bool,
    update_data: PlacementUpdateRequest,
) -> PlacementResponse:
    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can make counter offer")
    if update_data.price is None:
        raise HTTPException(status_code=400, detail="price required for counter action")
    result = await service.owner_counter_offer(
        placement_id, user_id, Decimal(str(update_data.price))
    )
    return PlacementResponse.model_validate(result)


async def _action_pay(
    service: PlacementRequestService,
    placement_id: int,
    user_id: int,
    is_advertiser: bool,
    placement_status: PlacementStatus,
) -> PlacementResponse:
    if not is_advertiser:
        raise HTTPException(status_code=403, detail="Only advertiser can pay placement")
    if placement_status != PlacementStatus.pending_payment:
        raise HTTPException(status_code=409, detail="Placement not in pending_payment status")
    result = await service.process_payment(placement_id, user_id)
    return PlacementResponse.model_validate(result)


async def _action_cancel(
    service: PlacementRequestService,
    placement_id: int,
    user_id: int,
    is_advertiser: bool,
) -> PlacementResponse:
    if not is_advertiser:
        raise HTTPException(status_code=403, detail="Only advertiser can cancel placement")
    result = await service.advertiser_cancel(placement_id, user_id)
    return PlacementResponse.model_validate(result)


async def _action_accept_counter(
    service: PlacementRequestService,
    placement_id: int,
    user_id: int,
    is_advertiser: bool,
    placement_status: PlacementStatus,
) -> PlacementResponse:
    if not is_advertiser:
        raise HTTPException(status_code=403, detail="Only advertiser can accept counter offer")
    if placement_status != PlacementStatus.counter_offer:
        raise HTTPException(status_code=409, detail="Placement not in counter_offer status")
    result = await service.advertiser_accept_counter(placement_id, user_id)
    return PlacementResponse.model_validate(result)


async def _action_counter_reply(
    service: PlacementRequestService,
    placement_id: int,
    user_id: int,
    is_advertiser: bool,
    update_data: PlacementUpdateRequest,
) -> PlacementResponse:
    """FIX #20: Advertiser makes counter-offer to owner's counter-offer."""
    if not is_advertiser:
        raise HTTPException(status_code=403, detail="Only advertiser can reply to counter offer")
    if update_data.price is None:
        raise HTTPException(status_code=400, detail="price required for counter-reply action")
    result = await service.advertiser_counter_offer(
        placement_id, user_id, Decimal(str(update_data.price)), update_data.comment
    )
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
    accept_counter = "accept-counter"
    counter_reply = "counter-reply"  # FIX #20: Advertiser counter-offer to owner's counter


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
    proposed_price: Decimal = Field(..., ge=100, description="Предложенная цена >= 100")
    post_text: str = Field(
        ...,
        min_length=10,
        max_length=4096,
        description="Текст поста",
        validation_alias="ad_text",
    )
    publication_format: str | None = Field(None, description="Формат публикации")
    media_file_id: str | None = Field(None, description="Telegram file_id медиа")
    scheduled_at: datetime = Field(
        ...,
        description="Желаемая дата публикации UTC",
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


class ChannelRef(BaseModel):
    """Минимальная информация о канале для ответа."""

    id: int
    username: str | None = None
    title: str

    model_config = {"from_attributes": True}


class PlacementResponse(BaseModel):
    """Ответ с данными заявки."""

    id: int
    advertiser_id: int
    owner_id: int
    channel_id: int
    channel: ChannelRef | None = None
    status: str
    publication_format: str
    proposed_price: Decimal
    final_price: Decimal | None = None
    final_schedule: datetime | None = None
    ad_text: str
    proposed_schedule: datetime | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None
    scheduled_delete_at: datetime | None = None
    deleted_at: datetime | None = None
    counter_offer_count: int
    counter_price: Decimal | None = None
    counter_schedule: datetime | None = None
    counter_comment: str | None = None
    advertiser_counter_price: Decimal | None = None
    advertiser_counter_schedule: datetime | None = None
    advertiser_counter_comment: str | None = None
    rejection_reason: str | None = None
    clicks_count: int = 0
    published_reach: int | None = None
    tracking_short_code: str | None = None
    has_dispute: bool = False
    dispute_status: str | None = None
    erid: str | None = None
    is_test: bool = False
    test_label: str | None = None
    media_type: str = "none"
    video_file_id: str | None = None
    video_url: str | None = None
    video_thumbnail_file_id: str | None = None
    video_duration: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# =============================================================================
# Endpoints
# =============================================================================


_STATUS_ALIASES: dict[str, list[PlacementStatus]] = {
    "active": [
        PlacementStatus.pending_owner,
        PlacementStatus.counter_offer,
        PlacementStatus.pending_payment,
        PlacementStatus.escrow,
    ],
    "completed": [PlacementStatus.published],
    "cancelled": [
        PlacementStatus.cancelled,
        PlacementStatus.refunded,
        PlacementStatus.failed,
        PlacementStatus.failed_permissions,
    ],
}


def _resolve_status_filter(raw: str | None) -> list[PlacementStatus] | None:
    if not raw:
        return None
    if raw in _STATUS_ALIASES:
        return _STATUS_ALIASES[raw]
    try:
        return [PlacementStatus(raw)]
    except ValueError as exc:
        valid = ", ".join(sorted([*(s.value for s in PlacementStatus), *_STATUS_ALIASES]))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status={raw!r}. Expected one of: {valid}",
        ) from exc


@router.get("/")
async def list_placements(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    view: Annotated[str | None, Query(description="Контекст: advertiser или owner")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    channel_id: Annotated[int | None, Query(description="Фильтр по ID канала")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PlacementResponse]:
    """
    Список заявок текущего пользователя.

    Args:
        view: Контекст — "advertiser" (заявки пользователя как рекламодателя)
              или "owner" (заявки на каналах пользователя).
              Без view — UNION обоих.
        status_filter: Фильтр по статусу — либо concrete PlacementStatus value,
              либо алиас "active" / "completed" / "cancelled".
        channel_id: Фильтр по ID канала.
        limit: Лимит записей.
        offset: Смещение.
    """
    if view not in (None, "advertiser", "owner"):
        raise HTTPException(status_code=400, detail="Invalid view value")

    statuses = _resolve_status_filter(status_filter)
    repo = PlacementRequestRepository(session)

    if view == "advertiser":
        placements = await repo.get_by_advertiser(current_user.id, statuses=statuses)
    elif view == "owner":
        placements = await repo.get_by_owner(current_user.id, statuses=statuses)
    else:
        # UNION
        adv_placements = await repo.get_by_advertiser(current_user.id, statuses=statuses)
        own_placements = await repo.get_by_owner(current_user.id, statuses=statuses)
        seen: dict[int, PlacementRequest] = {}
        for p in adv_placements + own_placements:
            if p.id not in seen:
                seen[p.id] = p
        placements = list(seen.values())
        placements.sort(key=lambda p: p.created_at, reverse=True)

    # Apply pagination
    placements = placements[offset : offset + limit] if limit else placements[offset:]

    # Filter by channel_id if specified
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

    # Проверка даты публикации: минимум — следующий день (не тест)
    if not is_test:
        tomorrow_midnight = (datetime.now(UTC) + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sched = request.scheduled_at
        # Убедиться что datetime aware
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=UTC)
        if sched < tomorrow_midnight:
            raise HTTPException(
                status_code=400,
                detail="Publication must be scheduled for at least tomorrow (next day after today)",
            )

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
            proposed_price=request.proposed_price,
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
    result = await session.execute(
        select(PlacementRequest)
        .options(
            selectinload(PlacementRequest.channel),
            selectinload(PlacementRequest.disputes),
        )
        .where(PlacementRequest.id == placement_id)
    )
    placement = result.scalar_one_or_none()

    if not placement:
        raise HTTPException(status_code=404, detail=PLACEMENT_NOT_FOUND)

    # Проверка: рекламодатель ИЛИ владелец канала
    channel = placement.channel
    is_owner = channel and channel.owner_id == current_user.id
    is_advertiser = placement.advertiser_id == current_user.id

    if not is_owner and not is_advertiser:
        raise HTTPException(status_code=403, detail="Access denied")

    return PlacementResponse.model_validate(placement)


# =============================================================================
# Unified PATCH endpoint (replaces legacy POST/DELETE action endpoints)
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

    # Import BillingService for payment actions
    from src.core.services.billing_service import BillingService

    service = PlacementRequestService(
        session=session,
        placement_repo=PlacementRequestRepository(session),
        channel_settings_repo=ChannelSettingsRepo(session),
        reputation_repo=ReputationRepository(session),
        billing_service=BillingService(),
    )

    # Выполнение действия
    _action_dispatch = {
        PlacementAction.accept: lambda: _action_accept(
            service, placement_id, current_user.id, is_owner
        ),
        PlacementAction.reject: lambda: _action_reject(
            service, placement_id, current_user.id, is_owner, update_data
        ),
        PlacementAction.counter: lambda: _action_counter(
            service, placement_id, current_user.id, is_owner, update_data
        ),
        PlacementAction.pay: lambda: _action_pay(
            service, placement_id, current_user.id, is_advertiser, placement.status
        ),
        PlacementAction.cancel: lambda: _action_cancel(
            service, placement_id, current_user.id, is_advertiser
        ),
        PlacementAction.accept_counter: lambda: _action_accept_counter(
            service, placement_id, current_user.id, is_advertiser, placement.status
        ),
        PlacementAction.counter_reply: lambda: _action_counter_reply(
            service, placement_id, current_user.id, is_advertiser, update_data
        ),
    }
    handler = _action_dispatch.get(update_data.action)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {update_data.action}")
    try:
        result = await handler()
        await session.commit()
        return result
    except HTTPException:
        await session.rollback()
        raise
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        await session.rollback()
        logger.exception(
            "Unexpected error in update_placement placement_id=%s action=%s: %s",
            placement_id,
            update_data.action,
            e,
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e
