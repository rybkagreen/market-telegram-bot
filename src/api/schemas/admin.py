"""
Admin API schemas for RekHarborBot.

Contains Pydantic models for admin panel endpoints:
- Feedback management
- Disputes resolution
- User management
- Platform statistics
- Contract listing (admin)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ═══════════════════════════════════════════════════════════════
# Feedback Schemas
# ═══════════════════════════════════════════════════════════════


class FeedbackAdminResponse(BaseModel):
    """Schema for feedback response in admin panel."""

    id: int
    user_id: int
    username: str | None = None
    text: str
    status: str  # "new", "in_progress", "resolved", "rejected"
    admin_response: str | None = None
    responder_username: str | None = None
    responder_id: int | None = None
    created_at: datetime
    responded_at: datetime | None = None

    model_config = {"from_attributes": True}


class FeedbackListAdminResponse(BaseModel):
    """Schema for feedback list response in admin panel."""

    items: list[FeedbackAdminResponse]
    total: int
    limit: int
    offset: int


class FeedbackRespondRequest(BaseModel):
    """Schema for responding to feedback."""

    model_config = ConfigDict(extra="forbid")
    response_text: str = Field(
        ..., min_length=10, max_length=2048, description="Admin response text"
    )
    status: str = Field(default="resolved", pattern="^(in_progress|resolved|rejected)$")


class FeedbackStatusUpdateRequest(BaseModel):
    """Schema for updating feedback status."""

    model_config = ConfigDict(extra="forbid")
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
    advertiser_username: str | None = None
    owner_username: str | None = None
    reason: str  # "post_removed_early", "bot_kicked", "advertiser_complaint"
    status: str  # "open", "owner_explained", "resolved"
    owner_explanation: str | None = None
    advertiser_comment: str | None = None
    resolution: str | None = None  # "owner_fault", "advertiser_fault", "technical", "partial"
    resolution_comment: str | None = None
    admin_id: int | None = None
    resolved_at: datetime | None = None
    advertiser_refund_pct: float | None = None
    owner_payout_pct: float | None = None
    expires_at: datetime | None = None
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

    model_config = ConfigDict(extra="forbid")
    resolution: str = Field(..., pattern="^(owner_fault|advertiser_fault|technical|partial)$")
    admin_comment: str | None = Field(default=None, max_length=1024)
    custom_split_percent: int | None = Field(default=None, ge=0, le=100)

    @field_validator("custom_split_percent")
    @classmethod
    def validate_partial_resolution(cls, v: int | None, info) -> int | None:
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
    username: str | None = None
    first_name: str
    last_name: str | None = None
    role: str  # "advertiser", "owner", "both"
    plan: str  # "free", "starter", "pro", "business"
    plan_expires_at: datetime | None = None
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
    reputation_score: float | None = None
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


class FinancialStats(BaseModel):
    """Platform financial balance breakdown."""

    total_topups: str  # Всего внесено пользователями
    total_payouts: str  # Всего выведено владельцам
    net_balance: str  # total_topups − total_payouts (реальный оборот)
    escrow_reserved: str  # Сейчас заблокировано в эскроу
    payout_reserved: str  # Зарезервировано под вывод (pending payouts)
    profit_accumulated: str  # Накопленная комиссия платформы
    # backward-compat aliases
    total_revenue: str
    pending_payouts: str


class PlatformStatsResponse(BaseModel):
    """Schema for platform statistics response."""

    users: dict[str, int]
    feedback: dict[str, int]
    disputes: dict[str, int]
    placements: dict[str, int]
    financial: FinancialStats


# ═══════════════════════════════════════════════════════════════
# Contract Schemas (Admin)
# ═══════════════════════════════════════════════════════════════


class AdminContractItem(BaseModel):
    """Single contract item for admin listing — no sensitive fields."""

    id: int
    user_id: int
    contract_type: str  # "owner_service", "advertiser_campaign", etc.
    contract_status: str  # "draft", "pending", "signed", "expired", "cancelled"
    signed_at: datetime | None = None
    created_at: datetime
    template_version: str

    model_config = {"from_attributes": True}


class AdminContractListResponse(BaseModel):
    """Paginated list of all platform contracts (admin only)."""

    items: list[AdminContractItem]
    total: int
    limit: int
    offset: int
