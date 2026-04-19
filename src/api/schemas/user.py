"""
Canonical Pydantic schemas for User entity.

Single source of truth for UserResponse — imported by all routers.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class UserResponse(BaseModel):
    """Canonical user response for Mini App and Web Portal."""

    id: int
    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None
    plan: str
    plan_expires_at: datetime | None = None
    balance_rub: str
    earned_rub: str
    credits: int = 0
    advertiser_xp: int = 0
    advertiser_level: int = 1
    owner_xp: int = 0
    owner_level: int = 1
    referral_code: str | None = None
    is_admin: bool
    ai_generations_used: int = 0
    legal_status_completed: bool = False
    legal_profile_prompted_at: datetime | None = None
    legal_profile_skipped_at: datetime | None = None
    platform_rules_accepted_at: datetime | None = None
    privacy_policy_accepted_at: datetime | None = None
    has_legal_profile: bool = False

    model_config = {"from_attributes": True}

    @field_validator("balance_rub", "earned_rub", mode="before")
    @classmethod
    def convert_decimal(cls, v: object) -> object:
        if isinstance(v, Decimal):
            return str(v)
        return v
