"""
Admin API router for platform management.

Endpoints:
  GET /api/admin/stats        — Platform statistics
  GET /api/admin/users        — List users with pagination
  GET /api/admin/users/{id}   — User details
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import AdminUser, get_db_session
from src.api.schemas.admin import (
    AdminContractListResponse,
    FinancialStats,
    PlatformStatsResponse,
    UserAdminResponse,
    UserListAdminResponse,
)
from src.db.models.contract import Contract
from src.db.models.dispute import PlacementDispute
from src.db.models.feedback import UserFeedback
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


async def _get_user_stats(session: AsyncSession) -> dict:
    """Fetch user counts: total, active, admins."""
    total = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
    active = (
        await session.execute(select(func.count()).select_from(User).where(User.is_active))
    ).scalar() or 0
    admins = (
        await session.execute(select(func.count()).select_from(User).where(User.is_admin))
    ).scalar() or 0
    return {"total": total, "active": active, "admins": admins}


async def _get_feedback_stats(session: AsyncSession) -> dict:
    """Fetch feedback counts by status."""
    base = select(func.count()).select_from(UserFeedback)
    total = (await session.execute(base)).scalar() or 0
    new = (await session.execute(base.where(UserFeedback.status == "NEW"))).scalar() or 0
    in_progress = (
        await session.execute(base.where(UserFeedback.status == "IN_PROGRESS"))
    ).scalar() or 0
    resolved = (await session.execute(base.where(UserFeedback.status == "RESOLVED"))).scalar() or 0
    rejected = (await session.execute(base.where(UserFeedback.status == "REJECTED"))).scalar() or 0
    return {
        "total": total,
        "new": new,
        "in_progress": in_progress,
        "resolved": resolved,
        "rejected": rejected,
    }


async def _get_dispute_stats(session: AsyncSession) -> dict:
    """Fetch dispute counts by status."""
    base = select(func.count()).select_from(PlacementDispute)
    total = (await session.execute(base)).scalar() or 0
    open_ = (await session.execute(base.where(PlacementDispute.status == "open"))).scalar() or 0
    owner_explained = (
        await session.execute(base.where(PlacementDispute.status == "owner_explained"))
    ).scalar() or 0
    resolved = (
        await session.execute(base.where(PlacementDispute.status == "resolved"))
    ).scalar() or 0
    return {
        "total": total,
        "open": open_,
        "owner_explained": owner_explained,
        "resolved": resolved,
    }


async def _get_placement_stats(session: AsyncSession) -> dict:
    """Fetch placement counts by status group."""
    base = select(func.count()).select_from(PlacementRequest)
    total = (await session.execute(base)).scalar() or 0
    pending = (
        await session.execute(base.where(PlacementRequest.status == PlacementStatus.pending_owner))
    ).scalar() or 0
    active = (
        await session.execute(
            base.where(
                PlacementRequest.status.in_([PlacementStatus.escrow, PlacementStatus.published])
            )
        )
    ).scalar() or 0
    completed = (
        await session.execute(base.where(PlacementRequest.status == PlacementStatus.published))
    ).scalar() or 0
    cancelled = (
        await session.execute(
            base.where(
                PlacementRequest.status.in_(
                    [PlacementStatus.cancelled, PlacementStatus.refunded, PlacementStatus.failed]
                )
            )
        )
    ).scalar() or 0
    return {
        "total": total,
        "pending": pending,
        "active": active,
        "completed": completed,
        "cancelled": cancelled,
    }


async def _get_financial_stats(session: AsyncSession) -> dict:
    """Fetch financial totals from the platform account."""
    from src.db.models.platform_account import PlatformAccount

    pa = await session.get(PlatformAccount, 1)
    total_topups = pa.total_topups if pa else Decimal("0")
    total_payouts = pa.total_payouts if pa else Decimal("0")
    net_balance = total_topups - total_payouts
    return {
        "total_topups": str(total_topups),
        "total_payouts": str(total_payouts),
        "net_balance": str(net_balance),
        "escrow_reserved": str(pa.escrow_reserved if pa else Decimal("0")),
        "payout_reserved": str(pa.payout_reserved if pa else Decimal("0")),
        "profit_accumulated": str(pa.profit_accumulated if pa else Decimal("0")),
        # backward-compat aliases
        "total_revenue": str(total_topups),
        "pending_payouts": str(pa.payout_reserved if pa else Decimal("0")),
    }


@router.get("/stats")
async def get_platform_stats(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
    logger.info(
        f"[ADMIN_STATS] Request received from admin user #{admin_user.id} ({admin_user.username})"
    )
    logger.info(f"[ADMIN_STATS] User is_admin={admin_user.is_admin}")

    users = await _get_user_stats(session)
    feedback = await _get_feedback_stats(session)
    disputes = await _get_dispute_stats(session)
    placements = await _get_placement_stats(session)
    financial = await _get_financial_stats(session)

    logger.info(f"Admin {admin_user.id} retrieved platform statistics")

    return PlatformStatsResponse(
        users=users,
        feedback=feedback,
        disputes=disputes,
        placements=placements,
        financial=FinancialStats.model_validate(financial),
    )


@router.get("/users", responses={400: {"description": "Invalid role filter"}})
async def get_all_users(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    role: str | None = None,
    limit: int = 50,
    offset: int = 0,
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
        placements_count_query = (
            select(func.count())
            .select_from(PlacementRequest)
            .where(PlacementRequest.advertiser_id == u.id)
        )
        total_placements = (await session.execute(placements_count_query)).scalar() or 0

        # Count user's channels
        channels_count_query = (
            select(func.count()).select_from(TelegramChat).where(TelegramChat.owner_id == u.id)
        )
        total_channels = (await session.execute(channels_count_query)).scalar() or 0

        # Count user's feedback
        feedback_count_query = (
            select(func.count()).select_from(UserFeedback).where(UserFeedback.user_id == u.id)
        )
        total_feedback = (await session.execute(feedback_count_query)).scalar() or 0

        # Count user's disputes
        disputes_count_query = (
            select(func.count())
            .select_from(PlacementDispute)
            .where((PlacementDispute.advertiser_id == u.id) | (PlacementDispute.owner_id == u.id))
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


# ─── Legal Profile Admin Endpoints (Gap 6) ──────────────────────────────────


@router.get("/legal-profiles")
async def list_legal_profiles(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    is_verified: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List legal profiles with optional is_verified filter (admin only)."""
    from sqlalchemy import select

    from src.db.models.legal_profile import LegalProfile
    from src.db.repositories.audit_log_repo import AuditLogRepo

    q = select(LegalProfile)
    if is_verified is not None:
        q = q.where(LegalProfile.is_verified == is_verified)
    q = q.limit(min(limit, 200)).offset(offset)
    result = await session.execute(q)
    profiles = list(result.scalars().all())

    audit = AuditLogRepo(session)
    await audit.log(
        action="ADMIN_READ",
        resource_type="legal_profile",
        user_id=admin_user.id,
        extra={"count": len(profiles)},
    )
    await session.commit()

    return {
        "items": [
            {
                "user_id": p.user_id,
                "legal_status": p.legal_status,
                "legal_name": p.legal_name,
                "inn": "***" if p.inn else None,
                "is_verified": p.is_verified,
                "verified_at": p.verified_at.isoformat() if p.verified_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in profiles
        ],
        "total": len(profiles),
    }


@router.post("/legal-profiles/{user_id}/verify")
async def verify_legal_profile(
    user_id: int,
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Verify a user's legal profile (admin only)."""
    from datetime import UTC

    from sqlalchemy import update as sa_update

    from src.db.models.legal_profile import LegalProfile
    from src.db.repositories.audit_log_repo import AuditLogRepo

    now = datetime.now(UTC)
    await session.execute(
        sa_update(LegalProfile)
        .where(LegalProfile.user_id == user_id)
        .values(is_verified=True, verified_at=now)
    )
    audit = AuditLogRepo(session)
    await audit.log(
        action="ADMIN_WRITE",
        resource_type="legal_profile",
        user_id=admin_user.id,
        target_user_id=user_id,
        extra={"action": "verify"},
    )
    await session.commit()
    logger.info(f"Admin {admin_user.id} verified legal profile for user {user_id}")
    return {"success": True, "verified": True}


@router.post("/legal-profiles/{user_id}/unverify")
async def unverify_legal_profile(
    user_id: int,
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Unverify a user's legal profile (admin only)."""
    from sqlalchemy import update as sa_update

    from src.db.models.legal_profile import LegalProfile
    from src.db.repositories.audit_log_repo import AuditLogRepo

    await session.execute(
        sa_update(LegalProfile)
        .where(LegalProfile.user_id == user_id)
        .values(is_verified=False, verified_at=None)
    )
    audit = AuditLogRepo(session)
    await audit.log(
        action="ADMIN_WRITE",
        resource_type="legal_profile",
        user_id=admin_user.id,
        target_user_id=user_id,
        extra={"action": "unverify"},
    )
    await session.commit()
    logger.info(f"Admin {admin_user.id} unverified legal profile for user {user_id}")
    return {"success": True, "verified": False}


# ─── Audit Log Admin Endpoint (Gap 7) ────────────────────────────────────────


@router.get("/audit-logs")
async def list_audit_logs(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: int | None = None,
    target_user_id: int | None = None,
    resource_type: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """List audit logs with optional filters (admin only)."""
    from sqlalchemy import select

    from src.db.models.audit_log import AuditLog

    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if user_id is not None:
        q = q.where(AuditLog.user_id == user_id)
    if target_user_id is not None:
        q = q.where(AuditLog.target_user_id == target_user_id)
    if resource_type is not None:
        q = q.where(AuditLog.resource_type == resource_type)
    if action is not None:
        q = q.where(AuditLog.action == action)
    if date_from is not None:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        q = q.where(AuditLog.created_at <= date_to)
    q = q.limit(min(limit, 500)).offset(offset)

    result = await session.execute(q)
    logs = list(result.scalars().all())

    return {
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "target_user_id": log.target_user_id,
                "ip_address": log.ip_address,
                "extra": log.extra,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }


# ─── Platform Settings (legal requisites for contracts) ──────────────────────


@router.get("/platform-settings")
async def get_platform_settings(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Get platform legal requisites (admin only)."""
    from src.db.models.platform_account import PlatformAccount

    account = await session.get(PlatformAccount, 1)
    if not account:
        return {
            "legal_name": None,
            "inn": None,
            "kpp": None,
            "ogrn": None,
            "address": None,
            "bank_name": None,
            "bank_account": None,
            "bank_bik": None,
            "bank_corr_account": None,
        }
    return {
        "legal_name": account.legal_name,
        "inn": account.inn,
        "kpp": account.kpp,
        "ogrn": account.ogrn,
        "address": account.address,
        "bank_name": account.bank_name,
        "bank_account": account.bank_account,
        "bank_bik": account.bank_bik,
        "bank_corr_account": account.bank_corr_account,
    }


@router.put("/platform-settings", responses={400: {"description": "No valid fields provided"}})
async def update_platform_settings(
    payload: dict,
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Update platform legal requisites (admin only)."""
    from sqlalchemy import update as sa_update

    from src.db.models.platform_account import PlatformAccount
    from src.db.repositories.audit_log_repo import AuditLogRepo

    allowed = {
        "legal_name",
        "inn",
        "kpp",
        "ogrn",
        "address",
        "bank_name",
        "bank_account",
        "bank_bik",
        "bank_corr_account",
    }
    values = {k: v for k, v in payload.items() if k in allowed}
    if not values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields provided"
        )

    await session.execute(
        sa_update(PlatformAccount).where(PlatformAccount.id == 1).values(**values)
    )
    audit = AuditLogRepo(session)
    await audit.log(
        action="ADMIN_WRITE",
        resource_type="platform_account",
        user_id=admin_user.id,
        extra={"fields_updated": list(values.keys())},
    )
    await session.commit()
    logger.info(f"Admin {admin_user.id} updated platform settings: {list(values.keys())}")
    return {"success": True}


@router.get("/users/{user_id}", responses={404: {"description": "User not found"}})
async def get_user_details(
    user_id: int,
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
    placements_count_query = (
        select(func.count())
        .select_from(PlacementRequest)
        .where(PlacementRequest.advertiser_id == user_id)
    )
    total_placements = (await session.execute(placements_count_query)).scalar() or 0

    # Count user's channels
    channels_count_query = (
        select(func.count()).select_from(TelegramChat).where(TelegramChat.owner_id == user_id)
    )
    total_channels = (await session.execute(channels_count_query)).scalar() or 0

    # Count user's feedback
    feedback_count_query = (
        select(func.count()).select_from(UserFeedback).where(UserFeedback.user_id == user_id)
    )
    total_feedback = (await session.execute(feedback_count_query)).scalar() or 0

    # Count user's disputes
    disputes_count_query = (
        select(func.count())
        .select_from(PlacementDispute)
        .where((PlacementDispute.advertiser_id == user_id) | (PlacementDispute.owner_id == user_id))
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


# ─── Balance Top-Up ─────────────────────────────────────────────────────────


class BalanceTopUpRequest(BaseModel):
    amount: float = Field(..., gt=0, le=1_000_000, description="Сумма пополнения в рублях")
    note: str = Field("", max_length=500, description="Примечание администратора")


@router.post(
    "/users/{user_id}/balance",
    responses={404: {"description": "User not found"}, 400: {"description": "Invalid amount"}},
)
async def topup_user_balance(
    user_id: int,
    body: BalanceTopUpRequest,
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserAdminResponse:
    """Зачислить рубли на баланс пользователя (только для администраторов)."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    repo = UserRepository(session)
    await repo.update_balance(user_id, Decimal(str(body.amount)))

    await session.refresh(user)

    logger.info(
        f"Admin #{admin_user.id} topped up balance for user #{user_id}: "
        f"+{body.amount} RUB. Note: {body.note!r}"
    )

    from src.db.models.reputation_score import ReputationScore

    rep_result = await session.execute(
        select(ReputationScore.advertiser_score).where(ReputationScore.user_id == user_id)
    )
    reputation_score = rep_result.scalar_one_or_none()

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
        total_placements=0,
        total_channels=0,
        total_feedback=0,
        total_disputes=0,
        reputation_score=float(reputation_score) if reputation_score else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ─── Tax Summary & KUDiR Export (Sprint B.1) ────────────────────────────────


@router.get("/tax/summary", responses={404: {"description": "Quarter not found"}})
async def get_tax_summary(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    year: int,
    quarter: int,
) -> dict:
    """Получить налоговую сводку за квартал (JSON)."""
    from src.core.services.tax_aggregation_service import TaxAggregationService

    try:
        summary = await TaxAggregationService.get_quarterly_summary(session, year, quarter)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Сериализуем Decimal и datetime для JSON
    serializable = {
        **summary,
        "usn_revenue": str(summary["usn_revenue"]),
        "vat_accumulated": str(summary["vat_accumulated"]),
        "ndfl_withheld": str(summary["ndfl_withheld"]),
        "total_income": str(summary["total_income"]),
        "tax_6percent": str(summary["tax_6percent"]),
        "kudir_entries": [
            {
                "entry_number": e["entry_number"],
                "operation_date": e["operation_date"].isoformat() if e["operation_date"] else None,
                "description": e["description"],
                "income_amount": str(e["income_amount"]),
            }
            for e in summary["kudir_entries"]
        ],
    }
    logger.info(f"Admin {admin_user.id} retrieved tax summary for {year}-Q{quarter}")
    return serializable


@router.get(
    "/tax/kudir/{year}/{quarter}/pdf",
    responses={
        404: {"description": "Quarter not found"},
        500: {"description": "PDF generation failed"},
    },
)
async def export_kudir_pdf(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    year: int,
    quarter: int,
):
    """Экспорт КУДиР в PDF за квартал."""
    from fastapi.responses import StreamingResponse

    from src.core.services.kudir_export_service import KudirExportService

    pdf_bytes = await KudirExportService.generate_kudir_pdf(session, year, quarter)

    logger.info(f"Admin {admin_user.id} exported KUDiR PDF for {year}-Q{quarter}")
    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="kudir_{year}_Q{quarter}.pdf"'},
    )


@router.get(
    "/tax/kudir/{year}/{quarter}/csv",
    responses={404: {"description": "Quarter not found"}},
)
async def export_kudir_csv(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    year: int,
    quarter: int,
):
    """Экспорт КУДиР в CSV за квартал (разделитель ;)."""
    from io import StringIO

    from fastapi.responses import StreamingResponse

    from src.core.services.kudir_export_service import KudirExportService

    csv_content = await KudirExportService.generate_kudir_csv(session, year, quarter)

    logger.info(f"Admin {admin_user.id} exported KUDiR CSV for {year}-Q{quarter}")
    return StreamingResponse(
        StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="kudir_{year}_Q{quarter}.csv"'},
    )


# ─── Admin Contracts ──────────────────────────────────────────────────


@router.get("/contracts", response_model=AdminContractListResponse)
async def list_all_contracts(
    admin_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
) -> AdminContractListResponse:
    """List all platform contracts with pagination (admin only)."""
    from src.api.schemas.admin import AdminContractItem

    base = select(Contract)
    if status_filter:
        base = base.where(Contract.contract_status == status_filter)

    # Count total
    count_q = select(func.count()).select_from(Contract)
    if status_filter:
        count_q = count_q.where(Contract.contract_status == status_filter)
    total = (await session.execute(count_q)).scalar() or 0

    # Fetch paginated items
    result = await session.execute(
        base.order_by(Contract.created_at.desc()).offset(offset).limit(limit)
    )
    contracts = list(result.scalars().all())

    items = [
        AdminContractItem.model_validate(c)
        for c in contracts
    ]

    logger.info(
        "Admin %s listed contracts: limit=%d, offset=%d, status=%s, total=%d",
        admin_user.id,
        limit,
        offset,
        status_filter,
        total,
    )
    return AdminContractListResponse(items=items, total=total, limit=limit, offset=offset)
