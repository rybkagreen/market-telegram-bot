"""
Pydantic схемы для диспутов (PlacementDispute).

Используются в API роутере /api/disputes для валидации
входящих данных и форматирования ответов.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DisputeReason(str, Enum):
    """Причины споров."""

    post_removed_early = "post_removed_early"
    bot_kicked = "bot_kicked"
    advertiser_complaint = "advertiser_complaint"


class DisputeStatus(str, Enum):
    """Статусы споров."""

    open = "open"
    owner_explained = "owner_explained"
    resolved = "resolved"


class DisputeResolution(str, Enum):
    """Резолюции споров."""

    owner_fault = "owner_fault"
    advertiser_fault = "advertiser_fault"
    technical = "technical"
    partial = "partial"


class DisputeCreate(BaseModel):
    """Схема создания диспута."""

    placement_id: int = Field(..., description="ID заявки на размещение")
    reason: DisputeReason = Field(..., description="Причина спора")
    comment: str = Field(..., min_length=10, max_length=2000, description="Комментарий рекламодателя")


class DisputeUpdate(BaseModel):
    """Схема обновления диспута (ответ владельца)."""

    owner_comment: str = Field(..., min_length=10, max_length=2000, description="Объяснение владельца")


class DisputeResponse(BaseModel):
    """Ответ с данными диспута."""

    id: int
    placement_request_id: int
    advertiser_id: int
    owner_id: int
    reason: DisputeReason
    status: DisputeStatus
    owner_explanation: str | None
    advertiser_comment: str | None
    resolution: DisputeResolution | None
    resolution_comment: str | None
    admin_id: int | None
    resolved_at: datetime | None
    advertiser_refund_pct: float | None
    owner_payout_pct: float | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
