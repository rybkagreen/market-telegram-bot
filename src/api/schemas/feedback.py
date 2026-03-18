"""Feedback schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""

    text: str = Field(..., min_length=10, max_length=1024, description="Feedback text")


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""

    id: int
    user_id: int
    text: str
    status: str
    admin_response: str | None
    created_at: datetime
    responded_at: datetime | None

    model_config = {"from_attributes": True}


class FeedbackListResponse(BaseModel):
    """Schema for feedback list."""

    items: list[FeedbackResponse]
    total: int
