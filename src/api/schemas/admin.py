"""
Admin API schemas for RekHarborBot.

Contains Pydantic models for admin panel endpoints:
- Feedback management
- Disputes resolution
- User management
- Platform statistics
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════
# Feedback Schemas
# ═══════════════════════════════════════════════════════════════


class FeedbackAdminResponse(BaseModel):
    """Schema for feedback response in admin panel."""

    id: int
    user_id: int
    username: Optional[str] = None
    text: str
    status: str  # "new", "in_progress", "resolved", "rejected"
    admin_response: Optional[str] = None
    responder_username: Optional[str] = None
    responder_id: Optional[int] = None
    created_at: datetime
    responded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FeedbackListAdminResponse(BaseModel):
    """Schema for feedback list response in admin panel."""

    items: list[FeedbackAdminResponse]
    total: int
    limit: int
    offset: int


class FeedbackRespondRequest(BaseModel):
    """Schema for responding to feedback."""

    response_text: str = Field(..., min_length=10, max_length=2048, description="Admin response text")
    status: str = Field(default="resolved", pattern="^(in_progress|resolved|rejected)$")


class FeedbackStatusUpdateRequest(BaseModel):
    """Schema for updating feedback status."""

    status: str = Field(..., pattern="^(new|in_progress|resolved|rejected)$")


# ═══════════════════════════════════════════════════════════════
# Dispute Schemas
# ═══════════════════════════════════════════════════════════════


class DisputeAdminResponse(BaseModel):
    """Schema for dispute response in admin panel."""

    id: int
    placement_request_id: int
    advertiser_id: int
    owner_id: int
    advertiser_username: Optional[str] = None
    owner_username: Optional[str] = None
    reason: str  # "post_removed_early", "bot_kicked", "advertiser_complaint"
    status: str  # "open", "owner_explained", "resolved"
    owner_explanation: Optional[str] = None
    advertiser_comment: Optional[str] = None
    resolution: Optional[str] = None  # "owner_fault", "advertiser_fault", "technical", "partial"
    resolution_comment: Optional[str] = None
    admin_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    advertiser_refund_pct: Optional[float] = None
    owner_payout_pct: Optional[float] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DisputeListAdminResponse(BaseModel):
    """Schema for dispute list response in admin panel."""

    items: list[DisputeAdminResponse]
    total: int
    limit: int
    offset: int


class DisputeResolveRequest(BaseModel):
    """Schema for resolving a dispute."""

    resolution: str = Field(..., pattern="^(owner_fault|advertiser_fault|technical|partial)$")
    admin_comment: Optional[str] = Field(default=None, max_length=1024)
    custom_split_percent: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("custom_split_percent")
    @classmethod
    def validate_partial_resolution(cls, v: Optional[int], info) -> Optional[int]:
        """Validate that custom_split_percent is provided for partial resolution."""
        # Note: We can't access 'resolution' here directly in field_validator
        # Validation will be done in the endpoint
        return v


# ═══════════════════════════════════════════════════════════════
# User Schemas
# ═══════════════════════════════════════════════════════════════


class UserAdminResponse(BaseModel):
    """Schema for user response in admin panel."""

    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    role: str  # "advertiser", "owner", "both"
    plan: str  # "free", "starter", "pro", "business"
    plan_expires_at: Optional[datetime] = None
    balance_rub: str
    earned_rub: str
    credits: int
    is_admin: bool
    advertiser_xp: int
    advertiser_level: int
    owner_xp: int
    owner_level: int
    total_placements: int = 0
    total_channels: int = 0
    total_feedback: int = 0
    total_disputes: int = 0
    reputation_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListAdminResponse(BaseModel):
    """Schema for user list response in admin panel."""

    items: list[UserAdminResponse]
    total: int
    limit: int
    offset: int


# ═══════════════════════════════════════════════════════════════
# Statistics Schemas
# ═══════════════════════════════════════════════════════════════


class PlatformStatsResponse(BaseModel):
    """Schema for platform statistics response."""

    users: dict[str, int]  # total, active, admins
    feedback: dict[str, int]  # total, new, in_progress, resolved, rejected
    disputes: dict[str, int]  # total, open, owner_explained, resolved
    placements: dict[str, int]  # total, pending, active, completed, cancelled
    financial: dict[str, str]  # total_revenue, total_payouts, pending_payouts, escrow_reserved
