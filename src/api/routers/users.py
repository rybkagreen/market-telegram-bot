"""
FastAPI router для управления данными пользователя (Users).

Endpoints:
  GET /api/users/me          — данные текущего пользователя
  GET /api/users/me/stats    — статистика пользователя (репутация)
"""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_current_user, get_db_session
from src.db.models.user import User
from src.db.repositories.reputation_repo import ReputationRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])


# ─── Response Models ────────────────────────────────────────────


class UserResponse(BaseModel):
    """Данные пользователя для Mini App."""

    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    plan: str
    credits: int
    balance_rub: str
    earned_rub: str
    is_admin: bool
    legal_status_completed: bool = False
    legal_profile_prompted_at: datetime | None = None
    legal_profile_skipped_at: datetime | None = None
    platform_rules_accepted_at: datetime | None = None
    privacy_policy_accepted_at: datetime | None = None
    has_legal_profile: bool = False

    model_config = {"from_attributes": True}

    @field_validator("balance_rub", "earned_rub", mode="before")
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to string for JSON serialization."""
        from decimal import Decimal

        if isinstance(v, Decimal):
            return str(v)
        return v


class ReputationScoreResponse(BaseModel):
    """Данные репутации пользователя."""

    user_id: int
    advertiser_score: float
    owner_score: float
    is_advertiser_blocked: bool
    is_owner_blocked: bool
    advertiser_violations_count: int
    owner_violations_count: int

    model_config = {"from_attributes": True}


class UserStatsResponse(BaseModel):
    """Ответ статистики пользователя для Mini App."""

    reputation: ReputationScoreResponse

    model_config = {"from_attributes": True}


class ReferralItem(BaseModel):
    """Элемент списка рефералов."""

    id: int
    username: str | None = None
    first_name: str
    joined_at: str
    is_active: bool

    model_config = {"from_attributes": True}


class ReferralStatsResponse(BaseModel):
    """Реферальная статистика пользователя."""

    referral_code: str
    referral_link: str
    total_referrals: int
    active_referrals: int
    total_earned_credits: int
    referrals: list[ReferralItem]

    model_config = {"from_attributes": True}


# ─── Endpoints ──────────────────────────────────────────────────


@router.get("/me")
async def get_current_user_data(current_user: CurrentUser) -> UserResponse:
    """
    Получить данные текущего авторизованного пользователя.

    Используется для проверки токена и обновления данных на фронтенде.
    Возвращает основную информацию о пользователе: ID, Telegram ID,
    имя, тариф и баланс кредитов.

    Returns:
        UserResponse: Данные пользователя.
    """
    plan_value = (
        current_user.plan.value if hasattr(current_user.plan, "value") else str(current_user.plan)
    )
    return UserResponse(
        id=current_user.id,
        telegram_id=current_user.telegram_id,
        username=current_user.username,
        first_name=current_user.first_name,
        plan=plan_value,
        credits=current_user.credits,
        balance_rub=str(current_user.balance_rub),
        earned_rub=str(current_user.earned_rub),
        is_admin=current_user.is_admin,
        legal_status_completed=current_user.legal_status_completed,
        legal_profile_prompted_at=current_user.legal_profile_prompted_at,
        legal_profile_skipped_at=current_user.legal_profile_skipped_at,
        platform_rules_accepted_at=current_user.platform_rules_accepted_at,
        privacy_policy_accepted_at=current_user.privacy_policy_accepted_at,
        has_legal_profile=current_user.legal_profile is not None,
    )


@router.post("/skip-legal-prompt")
async def skip_legal_prompt(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Mark that the user skipped the legal profile prompt."""
    now = datetime.now(UTC)
    await session.execute(
        sa_update(User)
        .where(User.id == current_user.id)
        .values(legal_profile_prompted_at=now, legal_profile_skipped_at=now)
    )
    await session.commit()
    return {"success": True}


@router.get("/me/stats", responses={404: {"description": "Reputation record not found"}})
async def get_current_user_stats(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserStatsResponse:
    """
    Получить статистику репутации текущего пользователя.

    Возвращает данные о репутации пользователя в обеих ролях:
    рекламодателя и владельца канала. Включает информацию о блокировках
    и количестве нарушений.

    Args:
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        UserStatsResponse: Данные репутации пользователя (wrapped в { reputation: ... }).

    Raises:
        HTTPException 404: Если запись о репутации не найдена.
    """
    repo = ReputationRepository(session)
    rep_score = await repo.get_or_create(current_user.id)

    if not rep_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reputation record not found",
        )

    return UserStatsResponse(
        reputation=ReputationScoreResponse(
            user_id=rep_score.user_id,
            advertiser_score=rep_score.advertiser_score,
            owner_score=rep_score.owner_score,
            is_advertiser_blocked=rep_score.is_advertiser_blocked,
            is_owner_blocked=rep_score.is_owner_blocked,
            advertiser_violations_count=rep_score.advertiser_violations_count,
            owner_violations_count=rep_score.owner_violations_count,
        )
    )


@router.get("/needs-accept-rules")
async def needs_accept_rules(current_user: CurrentUser) -> dict:
    """Check if user needs to accept platform rules (152-ФЗ compliance)."""
    needs_accept = (
        current_user.platform_rules_accepted_at is None
        or current_user.privacy_policy_accepted_at is None
    )
    return {"needs_accept": needs_accept}


@router.get("/me/referrals")
async def get_my_referrals(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReferralStatsResponse:
    """
    Реферальная статистика и код текущего пользователя.

    Возвращает реферальный код, ссылку, общую статистику и список рефералов.

    Args:
        current_user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        ReferralStatsResponse: Реферальная статистика пользователя.
    """
    from sqlalchemy import func, select

    from src.db.models.user import User
    from src.db.models.yookassa_payment import YookassaPayment

    # Получаем рефералов (пользователи у которых referred_by_id == current_user.id)
    referrals_query = (
        select(User)
        .where(User.referred_by_id == current_user.id)
        .order_by(User.created_at.desc())
        .limit(20)
    )
    result = await session.execute(referrals_query)
    referral_users = list(result.scalars().all())

    # Подсчёт общего количества
    count_query = select(func.count()).select_from(User).where(User.referred_by_id == current_user.id)
    total_result = await session.execute(count_query)
    total_referrals = total_result.scalar() or 0

    # Active referrals — те кто совершил хотя бы одну оплату (есть запись в YookassaPayment со status=succeeded)
    active_query = (
        select(func.count(User.id))
        .join(YookassaPayment, User.id == YookassaPayment.user_id)
        .where(
            User.referred_by_id == current_user.id,
            YookassaPayment.status == "succeeded",
        )
    )
    active_result = await session.execute(active_query)
    active_referrals = active_result.scalar() or 0

    # Total earned credits — сумма desired_balance из успешных платежей рефералов
    earned_query = (
        select(func.sum(YookassaPayment.desired_balance))
        .join(User, User.id == YookassaPayment.user_id)
        .where(
            User.referred_by_id == current_user.id,
            YookassaPayment.status == "succeeded",
        )
    )
    earned_result = await session.execute(earned_query)
    total_earned_credits = int(earned_result.scalar() or 0)

    # Формируем ссылку (используем заглушку для bot_username, если не настроено)
    bot_username = "RekHarborBot"  # Default, can be overridden via settings
    referral_link = f"https://t.me/{bot_username}?start={current_user.referral_code}"

    # Формируем список рефералов
    referrals = []
    for ref in referral_users:
        # Проверяем активность (была ли оплата)
        payment_check = await session.execute(
            select(YookassaPayment.id)
            .where(
                YookassaPayment.user_id == ref.id,
                YookassaPayment.status == "succeeded",
            )
            .limit(1)
        )
        is_active = payment_check.scalar_one_or_none() is not None

        referrals.append(
            ReferralItem(
                id=ref.id,
                username=ref.username,
                first_name=ref.first_name,
                joined_at=ref.created_at.isoformat() if ref.created_at else "",
                is_active=is_active,
            )
        )

    return ReferralStatsResponse(
        referral_code=current_user.referral_code or "",
        referral_link=referral_link,
        total_referrals=total_referrals,
        active_referrals=active_referrals,
        total_earned_credits=total_earned_credits,
        referrals=referrals,
    )
