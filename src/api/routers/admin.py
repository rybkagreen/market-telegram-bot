"""
Admin API router for platform management.

Endpoints:
  GET /api/admin/stats        — Platform statistics
  GET /api/admin/users        — List users with pagination
  GET /api/admin/users/{id}   — User details
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import AdminUser, get_db_session
from src.api.schemas.admin import (
    PlatformStatsResponse,
    UserAdminResponse,
    UserListAdminResponse,
)
from src.db.models.dispute import PlacementDispute
from src.db.models.feedback import UserFeedback
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    admin_user: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> PlatformStatsResponse:
    """
    Get overall platform statistics (admin only).

    Returns statistics about:
    - Users (total, active, admins)
    - Feedback (total, new, resolved)
    - Disputes (total, open, resolved)
    - Placements (total, active, completed)
    - Financial (revenue, payouts, pending)

    Args:
        admin_user: Current admin user
        session: DB session

    Returns:
        PlatformStatsResponse with all statistics
    """
    logger.info(f"[ADMIN_STATS] Request received from admin user #{admin_user.id} ({admin_user.username})")
    logger.info(f"[ADMIN_STATS] User is_admin={admin_user.is_admin}")

    # Users statistics
    total_users = await session.execute(select(func.count()).select_from(User))
    total_users_count = total_users.scalar() or 0

    active_users_query = select(func.count()).select_from(User).where(
        User.is_active
    )
    active_users_result = await session.execute(active_users_query)
    active_users_count = active_users_result.scalar() or 0

    admin_users_query = select(func.count()).select_from(User).where(
        User.is_admin
    )
    admin_users_result = await session.execute(admin_users_query)
    admin_users_count = admin_users_result.scalar() or 0

    # Feedback statistics
    feedback_total_query = select(func.count()).select_from(UserFeedback)
    feedback_total = (await session.execute(feedback_total_query)).scalar() or 0

    feedback_new_query = select(func.count()).select_from(UserFeedback).where(
        UserFeedback.status == "NEW"
    )
    feedback_new = (await session.execute(feedback_new_query)).scalar() or 0

    feedback_in_progress_query = select(func.count()).select_from(UserFeedback).where(
        UserFeedback.status == "IN_PROGRESS"
    )
    feedback_in_progress = (await session.execute(feedback_in_progress_query)).scalar() or 0

    feedback_resolved_query = select(func.count()).select_from(UserFeedback).where(
        UserFeedback.status == "RESOLVED"
    )
    feedback_resolved = (await session.execute(feedback_resolved_query)).scalar() or 0

    feedback_rejected_query = select(func.count()).select_from(UserFeedback).where(
        UserFeedback.status == "REJECTED"
    )
    feedback_rejected = (await session.execute(feedback_rejected_query)).scalar() or 0

    # Disputes statistics
    disputes_total_query = select(func.count()).select_from(PlacementDispute)
    disputes_total = (await session.execute(disputes_total_query)).scalar() or 0

    disputes_open_query = select(func.count()).select_from(PlacementDispute).where(
        PlacementDispute.status == "open"
    )
    disputes_open = (await session.execute(disputes_open_query)).scalar() or 0

    disputes_owner_explained_query = select(func.count()).select_from(PlacementDispute).where(
        PlacementDispute.status == "owner_explained"
    )
    disputes_owner_explained = (await session.execute(disputes_owner_explained_query)).scalar() or 0

    disputes_resolved_query = select(func.count()).select_from(PlacementDispute).where(
        PlacementDispute.status == "resolved"
    )
    disputes_resolved = (await session.execute(disputes_resolved_query)).scalar() or 0

    # Placements statistics
    placements_total_query = select(func.count()).select_from(PlacementRequest)
    placements_total = (await session.execute(placements_total_query)).scalar() or 0

    placements_pending_query = select(func.count()).select_from(PlacementRequest).where(
        PlacementRequest.status == PlacementStatus.pending_owner
    )
    placements_pending = (await session.execute(placements_pending_query)).scalar() or 0

    placements_active_query = select(func.count()).select_from(PlacementRequest).where(
        PlacementRequest.status.in_(
            [PlacementStatus.escrow, PlacementStatus.published]
        )
    )
    placements_active = (await session.execute(placements_active_query)).scalar() or 0

    placements_completed_query = select(func.count()).select_from(PlacementRequest).where(
        PlacementRequest.status == PlacementStatus.published
    )
    placements_completed = (await session.execute(placements_completed_query)).scalar() or 0

    placements_cancelled_query = select(func.count()).select_from(PlacementRequest).where(
        PlacementRequest.status.in_(
            [PlacementStatus.cancelled, PlacementStatus.refunded, PlacementStatus.failed]
        )
    )
    placements_cancelled = (await session.execute(placements_cancelled_query)).scalar() or 0

    # Financial statistics
    from src.db.models.platform_account import PlatformAccount

    platform_account = await session.get(PlatformAccount, 1)
    total_revenue = str(platform_account.total_topups) if platform_account else "0.00"
    total_payouts = str(platform_account.total_payouts) if platform_account else "0.00"
    pending_payouts = str(platform_account.payout_reserved) if platform_account else "0.00"
    escrow_reserved = str(platform_account.escrow_reserved) if platform_account else "0.00"

    logger.info(f"Admin {admin_user.id} retrieved platform statistics")

    return PlatformStatsResponse(
        users={
            "total": total_users_count,
            "active": active_users_count,
            "admins": admin_users_count,
        },
        feedback={
            "total": feedback_total,
            "new": feedback_new,
            "in_progress": feedback_in_progress,
            "resolved": feedback_resolved,
            "rejected": feedback_rejected,
        },
        disputes={
            "total": disputes_total,
            "open": disputes_open,
            "owner_explained": disputes_owner_explained,
            "resolved": disputes_resolved,
        },
        placements={
            "total": placements_total,
            "pending": placements_pending,
            "active": placements_active,
            "completed": placements_completed,
            "cancelled": placements_cancelled,
        },
        financial={
            "total_revenue": total_revenue,
            "total_payouts": total_payouts,
            "pending_payouts": pending_payouts,
            "escrow_reserved": escrow_reserved,
        },
    )

    logger.info(f"[ADMIN_STATS] Statistics returned successfully for user #{admin_user.id}")


@router.get("/users", response_model=UserListAdminResponse)
async def get_all_users(
    admin_user: AdminUser,
    role: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> UserListAdminResponse:
    """
    Get list of users with pagination (admin only).

    Args:
        role: Filter by role (advertiser, owner, both)
        limit: Max items to return (1-200)
        offset: Offset for pagination
        admin_user: Current admin user
        session: DB session

    Returns:
        UserListAdminResponse with items and total count
    """
    # Validate limit
    if limit < 1:
        limit = 1
    elif limit > 200:
        limit = 200

    # Build query
    query = select(User)

    # Apply role filter
    if role:
        if role not in ["advertiser", "owner", "both"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}. Must be one of: advertiser, owner, both",
            )
        query = query.where(User.current_role == role)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    users = result.scalars().all()

    # Build response
    items = []
    for u in users:
        # Count user's placements
        placements_count_query = select(func.count()).select_from(PlacementRequest).where(
            PlacementRequest.advertiser_id == u.id
        )
        total_placements = (await session.execute(placements_count_query)).scalar() or 0

        # Count user's channels
        channels_count_query = select(func.count()).select_from(TelegramChat).where(
            TelegramChat.owner_id == u.id
        )
        total_channels = (await session.execute(channels_count_query)).scalar() or 0

        # Count user's feedback
        feedback_count_query = select(func.count()).select_from(UserFeedback).where(
            UserFeedback.user_id == u.id
        )
        total_feedback = (await session.execute(feedback_count_query)).scalar() or 0

        # Count user's disputes
        disputes_count_query = select(func.count()).select_from(PlacementDispute).where(
            (PlacementDispute.advertiser_id == u.id) | (PlacementDispute.owner_id == u.id)
        )
        total_disputes = (await session.execute(disputes_count_query)).scalar() or 0

        # Get reputation score
        from src.db.models.reputation_score import ReputationScore

        rep_score_query = select(ReputationScore.advertiser_score).where(
            ReputationScore.user_id == u.id
        )
        rep_result = await session.execute(rep_score_query)
        reputation_score = rep_result.scalar_one_or_none()

        items.append(
            UserAdminResponse(
                id=u.id,
                telegram_id=u.telegram_id,
                username=u.username,
                first_name=u.first_name,
                last_name=u.last_name,
                role=u.current_role,
                plan=u.plan,
                plan_expires_at=u.plan_expires_at,
                balance_rub=str(u.balance_rub),
                earned_rub=str(u.earned_rub),
                credits=u.credits,
                is_admin=u.is_admin,
                advertiser_xp=u.advertiser_xp,
                advertiser_level=u.advertiser_level,
                owner_xp=u.owner_xp,
                owner_level=u.owner_level,
                total_placements=total_placements,
                total_channels=total_channels,
                total_feedback=total_feedback,
                total_disputes=total_disputes,
                reputation_score=float(reputation_score) if reputation_score else None,
                created_at=u.created_at,
                updated_at=u.updated_at,
            )
        )

    logger.info(f"Admin {admin_user.id} retrieved users list (limit={limit}, offset={offset})")

    return UserListAdminResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=UserAdminResponse)
async def get_user_details(
    user_id: int,
    admin_user: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> UserAdminResponse:
    """
    Get detailed user information (admin only).

    Args:
        user_id: User ID
        admin_user: Current admin user
        session: DB session

    Returns:
        UserAdminResponse with full user details

    Raises:
        HTTPException 404: User not found
    """
    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Count user's placements
    placements_count_query = select(func.count()).select_from(PlacementRequest).where(
        PlacementRequest.advertiser_id == user_id
    )
    total_placements = (await session.execute(placements_count_query)).scalar() or 0

    # Count user's channels
    channels_count_query = select(func.count()).select_from(TelegramChat).where(
        TelegramChat.owner_id == user_id
    )
    total_channels = (await session.execute(channels_count_query)).scalar() or 0

    # Count user's feedback
    feedback_count_query = select(func.count()).select_from(UserFeedback).where(
        UserFeedback.user_id == user_id
    )
    total_feedback = (await session.execute(feedback_count_query)).scalar() or 0

    # Count user's disputes
    disputes_count_query = select(func.count()).select_from(PlacementDispute).where(
        (PlacementDispute.advertiser_id == user_id) | (PlacementDispute.owner_id == user_id)
    )
    total_disputes = (await session.execute(disputes_count_query)).scalar() or 0

    # Get reputation score
    from src.db.models.reputation_score import ReputationScore

    rep_score_query = select(ReputationScore.advertiser_score).where(
        ReputationScore.user_id == user_id
    )
    rep_result = await session.execute(rep_score_query)
    reputation_score = rep_result.scalar_one_or_none()

    logger.info(f"Admin {admin_user.id} retrieved details for user #{user_id}")

    return UserAdminResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.current_role,
        plan=user.plan,
        plan_expires_at=user.plan_expires_at,
        balance_rub=str(user.balance_rub),
        earned_rub=str(user.earned_rub),
        credits=user.credits,
        is_admin=user.is_admin,
        advertiser_xp=user.advertiser_xp,
        advertiser_level=user.advertiser_level,
        owner_xp=user.owner_xp,
        owner_level=user.owner_level,
        total_placements=total_placements,
        total_channels=total_channels,
        total_feedback=total_feedback,
        total_disputes=total_disputes,
        reputation_score=float(reputation_score) if reputation_score else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
