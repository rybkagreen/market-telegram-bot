"""Feedback API router."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_admin_user, get_current_user, get_db_session
from src.api.schemas.admin import (
    FeedbackAdminResponse,
    FeedbackListAdminResponse,
    FeedbackRespondRequest,
    FeedbackStatusUpdateRequest,
)
from src.api.schemas.feedback import FeedbackCreate, FeedbackListResponse, FeedbackResponse
from src.db.models.feedback import FeedbackStatus, UserFeedback
from src.db.models.user import User
from src.db.repositories.feedback_repo import FeedbackRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    body: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    """Create new feedback from user."""
    from src.db.session import async_session_factory

    repo = FeedbackRepository(session)
    feedback = await repo.create_feedback(
        user_id=current_user.id,
        text=body.text,
    )

    # Уведомить админов (PHASE-4)
    # Отправляем уведомление в фоне (не блокируем ответ)
    try:
        async with async_session_factory() as notif_session:
            # Получаем telegram_id пользователя для уведомления
            from src.db.repositories.user_repo import UserRepository
            user_repo = UserRepository(notif_session)
            user = await user_repo.get_by_id(current_user.id)
            if user:
                # Note: notify_admins_new_feedback требует Bot объект, который не доступен в API
                # Уведомление будет отправлено через Celery task (см. tasks/feedback_tasks.py)
                logger.info(f"Feedback #{feedback.id} created by user {current_user.id}")
    except Exception as e:
        logger.warning(f"Failed to log feedback notification: {e}")

    return FeedbackResponse.model_validate(feedback)


@router.get("/", response_model=FeedbackListResponse)
async def get_my_feedback(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackListResponse:
    """Get current user's feedback history."""
    repo = FeedbackRepository(session)
    feedbacks = await repo.get_by_user_id(user_id=current_user.id)

    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(f) for f in feedbacks],
        total=len(feedbacks),
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    """Get specific feedback by ID."""
    repo = FeedbackRepository(session)
    feedback = await repo.get_by_id(feedback_id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    # Проверка что feedback принадлежит пользователю
    if feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return FeedbackResponse.model_validate(feedback)


# ═══════════════════════════════════════════════════════════════
# Admin Endpoints (PHASE-2)
# ═══════════════════════════════════════════════════════════════


@router.get("/admin/", response_model=FeedbackListAdminResponse)
async def get_all_feedback(
    status_filter: str = "all",
    limit: int = 20,
    offset: int = 0,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackListAdminResponse:
    """
    Get all feedback with pagination and filtering (admin only).

    Args:
        status_filter: Filter by status (new, in_progress, resolved, rejected, all)
        limit: Max items to return (1-100)
        offset: Offset for pagination
        admin_user: Current admin user
        session: DB session

    Returns:
        FeedbackListAdminResponse with items and total count
    """
    # Validate limit
    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    # Build query
    query = select(UserFeedback)

    # Apply status filter
    if status_filter != "all":
        try:
            status_enum = FeedbackStatus(status_filter.upper())
            query = query.where(UserFeedback.status == status_enum)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Must be one of: new, in_progress, resolved, rejected, all",
            ) from err

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(UserFeedback.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    feedbacks = result.scalars().all()

    # Build response with responder info
    items = []
    for fb in feedbacks:
        responder_username = None
        if fb.responder:
            responder_username = fb.responder.username

        items.append(
            FeedbackAdminResponse(
                id=fb.id,
                user_id=fb.user_id,
                username=fb.user.username if fb.user else None,
                text=fb.text,
                status=fb.status,  # type: ignore
                admin_response=fb.admin_response,
                responder_username=responder_username,
                responder_id=fb.responded_by_id,
                created_at=fb.created_at,
                responded_at=fb.responded_at,
            )
        )

    return FeedbackListAdminResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/admin/{feedback_id}", response_model=FeedbackAdminResponse)
async def get_feedback_admin(
    feedback_id: int,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackAdminResponse:
    """
    Get specific feedback details (admin only).

    Args:
        feedback_id: Feedback ID
        admin_user: Current admin user
        session: DB session

    Returns:
        FeedbackAdminResponse

    Raises:
        HTTPException 404: Feedback not found
    """
    repo = FeedbackRepository(session)
    feedback = await repo.get_by_id(feedback_id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    responder_username = feedback.responder.username if feedback.responder else None

    return FeedbackAdminResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        username=feedback.user.username if feedback.user else None,
        text=feedback.text,
        status=feedback.status,  # type: ignore
        admin_response=feedback.admin_response,
        responder_username=responder_username,
        responder_id=feedback.responded_by_id,
        created_at=feedback.created_at,
        responded_at=feedback.responded_at,
    )


@router.post("/admin/{feedback_id}/respond", response_model=FeedbackAdminResponse)
async def respond_to_feedback(
    feedback_id: int,
    body: FeedbackRespondRequest,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackAdminResponse:
    """
    Send response to feedback (admin only).

    Args:
        feedback_id: Feedback ID
        body: Response text and status
        admin_user: Current admin user
        session: DB session

    Returns:
        FeedbackAdminResponse with updated data

    Raises:
        HTTPException 404: Feedback not found
    """
    repo = FeedbackRepository(session)
    feedback = await repo.get_by_id(feedback_id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    # Update feedback
    feedback.admin_response = body.response_text
    feedback.status = FeedbackStatus(body.status.upper())
    feedback.responded_by_id = admin_user.id
    feedback.responded_at = datetime.now(UTC)

    await session.flush()
    await session.refresh(feedback)

    responder_username = feedback.responder.username if feedback.responder else None

    logger.info(f"Admin {admin_user.id} responded to feedback #{feedback_id}")

    return FeedbackAdminResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        username=feedback.user.username if feedback.user else None,
        text=feedback.text,
        status=feedback.status,  # type: ignore
        admin_response=feedback.admin_response,
        responder_username=responder_username,
        responder_id=feedback.responded_by_id,
        created_at=feedback.created_at,
        responded_at=feedback.responded_at,
    )


@router.patch("/admin/{feedback_id}/status", response_model=FeedbackAdminResponse)
async def update_feedback_status(
    feedback_id: int,
    body: FeedbackStatusUpdateRequest,
    *,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackAdminResponse:
    """
    Update feedback status without response (admin only).

    Args:
        feedback_id: Feedback ID
        body: New status
        admin_user: Current admin user
        session: DB session

    Returns:
        FeedbackAdminResponse with updated status

    Raises:
        HTTPException 404: Feedback not found
    """
    repo = FeedbackRepository(session)
    feedback = await repo.get_by_id(feedback_id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    # Update status only
    feedback.status = FeedbackStatus(body.status.upper())

    await session.flush()
    await session.refresh(feedback)

    responder_username = feedback.responder.username if feedback.responder else None

    logger.info(f"Admin {admin_user.id} updated status of feedback #{feedback_id} to {body.status}")

    return FeedbackAdminResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        username=feedback.user.username if feedback.user else None,
        text=feedback.text,
        status=feedback.status,  # type: ignore
        admin_response=feedback.admin_response,
        responder_username=responder_username,
        responder_id=feedback.responded_by_id,
        created_at=feedback.created_at,
        responded_at=feedback.responded_at,
    )
