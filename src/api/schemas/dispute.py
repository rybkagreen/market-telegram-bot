"""
Pydantic схемы для диспутов (PlacementDispute).

Используются в API роутере /api/disputes для валидации
входящих данных и форматирования ответов.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DisputeReason(str, Enum):
    """Причины споров.

    Объединены значения из Telegram-бота (legacy) и фронтенда (mini_app/web_portal).
    """

    # Legacy (Telegram bot)
    post_removed_early = "post_removed_early"
    bot_kicked = "bot_kicked"
    advertiser_complaint = "advertiser_complaint"

    # Frontend (mini_app / web_portal)
    not_published = "not_published"
    wrong_time = "wrong_time"
    wrong_text = "wrong_text"
    early_deletion = "early_deletion"
    other = "other"


class DisputeStatus(str, Enum):
    """Статусы споров."""

    open = "open"
    owner_explained = "owner_explained"
    resolved = "resolved"
    closed = "closed"


class DisputeResolution(str, Enum):
    """Резолюции споров.

    Объединены значения из Telegram-бота (financial) и фронтенда (display).
    """

    # Telegram bot — финансовые резолюции
    owner_fault = "owner_fault"
    advertiser_fault = "advertiser_fault"
    technical = "technical"
    partial = "partial"

    # Frontend — отображаемые резолюции
    full_refund = "full_refund"
    partial_refund = "partial_refund"
    no_refund = "no_refund"
    warning = "warning"


class DisputeCreate(BaseModel):
    """Схема создания диспута."""

    placement_id: int = Field(..., description="ID заявки на размещение")
    reason: DisputeReason = Field(..., description="Причина спора")
    comment: str = Field(
        ..., min_length=10, max_length=2000, description="Комментарий рекламодателя"
    )


class DisputeUpdate(BaseModel):
    """Схема обновления диспута (ответ владельца)."""

    owner_comment: str = Field(
        ..., min_length=10, max_length=2000, description="Объяснение владельца"
    )


class DisputeResponse(BaseModel):
    """Ответ с данными диспута."""

    id: int
    placement_request_id: int
    advertiser_id: int
    owner_id: int
    reason: DisputeReason
    status: DisputeStatus
    owner_explanation: str | None = None
    advertiser_comment: str | None = None
    resolution: DisputeResolution | None = None
    resolution_comment: str | None = None
    admin_id: int | None = None
    resolved_at: datetime | None = None
    advertiser_refund_pct: float | None = None
    owner_payout_pct: float | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DisputeListResponse(BaseModel):
    """Пагинированный список диспутов пользователя."""

    items: list[DisputeResponse]
    total: int
    limit: int
    offset: int
