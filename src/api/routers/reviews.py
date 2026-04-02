"""FastAPI router для отзывов о размещениях (Reviews)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.api.schemas.review import PlacementReviewsResponse, ReviewCreate, ReviewResponse
from src.core.services.reputation_service import ReputationService
from src.core.services.review_service import ReviewService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.repositories.review_repo import ReviewRepo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reviews"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_review(
    body: ReviewCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReviewResponse:
    """
    Оставить отзыв о размещении.

    Доступно только участникам placement (advertiser или owner).
    Placement должен быть в статусе published.
    Один отзыв от одного участника на одно размещение.
    """
    placement = await session.get(PlacementRequest, body.placement_request_id)
    if not placement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placement not found")

    if placement.status != PlacementStatus.published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviews are only allowed for published placements",
        )

    # Определяем роль текущего пользователя
    if current_user.id == placement.advertiser_id:
        reviewer_role = "advertiser"
        reviewed_id = placement.owner_id
    elif current_user.id == placement.owner_id:
        reviewer_role = "owner"
        reviewed_id = placement.advertiser_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this placement",
        )

    # Проверяем дубль
    review_repo = ReviewRepo(session)
    existing = await review_repo.get_by_placement_and_reviewer(
        body.placement_request_id, current_user.id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a review for this placement",
        )

    # Создаём отзыв
    review = await review_repo.create_review(
        placement_request_id=body.placement_request_id,
        reviewer_id=current_user.id,
        reviewed_id=reviewed_id,
        rating=body.rating,
        comment=body.comment,
    )

    # Начисляем изменение репутации reviewed_id
    rep_service = ReputationService(
        session=session,
        reputation_repo=ReputationRepo(session),
    )
    await rep_service.on_review(
        reviewer_id=current_user.id,
        reviewed_id=reviewed_id,
        reviewer_role=reviewer_role,
        stars=body.rating,
        placement_request_id=body.placement_request_id,
    )

    # Пересчитываем рейтинг канала
    review_service = ReviewService()
    await review_service.recalculate_channel_rating(placement.channel_id, session)

    return ReviewResponse.model_validate(review)


@router.get("/{placement_request_id}")
async def get_placement_reviews(
    placement_request_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementReviewsResponse:
    """
    Получить отзывы по placement.

    Возвращает my_review (отзыв текущего пользователя) и their_review (встречный).
    Доступно только участникам placement.
    """
    placement = await session.get(PlacementRequest, placement_request_id)
    if not placement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placement not found")

    if current_user.id not in (placement.advertiser_id, placement.owner_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this placement",
        )

    review_repo = ReviewRepo(session)
    reviews = await review_repo.get_by_placement(placement_request_id)

    my_review = next((r for r in reviews if r.reviewer_id == current_user.id), None)
    their_review = next((r for r in reviews if r.reviewer_id != current_user.id), None)

    return PlacementReviewsResponse(
        placement_request_id=placement_request_id,
        my_review=ReviewResponse.model_validate(my_review) if my_review else None,
        their_review=ReviewResponse.model_validate(their_review) if their_review else None,
    )
