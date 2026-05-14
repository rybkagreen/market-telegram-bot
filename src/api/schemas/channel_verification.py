"""
Pydantic схемы для BL-107 Phase B.5a — manual evidence review.

Used by:
- Owner submit endpoint: POST /api/channels/{id}/submit-registry-evidence
- Admin endpoints: /api/admin/channel-verifications/...

ФЗ-303 blogger registry compliance:
- Owner submits Госуслуги application_number when @Trustchannelbot path не reachable.
- Admin reviews + verifies или rejects.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ChannelVerificationSubmitRequest(BaseModel):
    """Owner submits blogger registry evidence для admin review."""

    model_config = ConfigDict(extra="forbid")

    application_number: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Номер заявления на Госуслугах (Реестр блогеров)",
        examples=["A-2026-04-12345"],
    )
    registry_url: HttpUrl | None = Field(
        default=None,
        description="Опциональная ссылка на запись в реестре",
        examples=["https://rkn.gov.ru/blogger-registry/A-2026-04-12345"],
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Дополнительные комментарии для администратора",
    )


class ChannelVerificationSubmitResponse(BaseModel):
    """Submission accepted, pending admin review."""

    status: Literal["pending_review"] = Field(default="pending_review")
    channel_id: int
    application_number: str
    submitted_at: datetime


class ChannelVerificationListItem(BaseModel):
    """One channel в admin review queue."""

    channel_id: int
    channel_username: str | None
    channel_title: str | None
    member_count: int
    owner_id: int
    owner_username: str | None
    application_number: str
    submitted_at: datetime
    status: Literal["pending_review", "verified"]


class ChannelVerificationListResponse(BaseModel):
    """Paginated list of channels awaiting/completed verification."""

    items: list[ChannelVerificationListItem]
    total: int
    limit: int
    offset: int


class ChannelVerificationHistoryEntry(BaseModel):
    """One audit log entry для history view."""

    action: str
    actor_user_id: int | None
    created_at: datetime
    extra: dict | None = None


class ChannelVerificationDetailResponse(BaseModel):
    """Full detail view of one channel verification."""

    channel_id: int
    channel_username: str | None
    channel_title: str | None
    member_count: int
    owner_id: int
    owner_username: str | None
    is_blogger_registry_verified: bool
    blogger_registry_verified_at: datetime | None
    blogger_registry_verification_method: str | None
    blogger_registry_verified_by_admin_id: int | None
    application_number: str | None
    member_count_at_verification: int | None
    last_blogger_registry_check_at: datetime | None
    history: list[ChannelVerificationHistoryEntry]


class ChannelVerificationVerifyRequest(BaseModel):
    """Admin approves manual evidence."""

    model_config = ConfigDict(extra="forbid")

    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Внутренние заметки администратора",
    )


class ChannelVerificationVerifyResponse(BaseModel):
    """Verification recorded."""

    channel_id: int
    is_blogger_registry_verified: Literal[True]
    blogger_registry_verified_at: datetime
    blogger_registry_verification_method: Literal["manual_evidence"]
    blogger_registry_verified_by_admin_id: int


class ChannelVerificationRejectRequest(BaseModel):
    """Admin rejects manual evidence."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Причина отказа (видна владельцу канала)",
    )
    internal_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Внутренние заметки администратора (не отправляются владельцу)",
    )


class ChannelVerificationRejectResponse(BaseModel):
    """Rejection recorded."""

    channel_id: int
    rejected_at: datetime
    reason: str
