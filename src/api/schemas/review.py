"""Pydantic schemas for Review endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    """Запрос на создание отзыва."""

    placement_request_id: int
    rating: int = Field(..., ge=1, le=5, description="Оценка 1–5 звёзд")
    comment: str | None = Field(None, max_length=500, description="Текст отзыва")


class ReviewResponse(BaseModel):
    """Ответ с данными отзыва."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    placement_request_id: int
    reviewer_id: int
    reviewed_id: int
    rating: int
    comment: str | None = None
    created_at: datetime


class PlacementReviewsResponse(BaseModel):
    """Оба отзыва по placement: мой и встречный."""

    placement_request_id: int
    my_review: ReviewResponse | None = None
    their_review: ReviewResponse | None = None
