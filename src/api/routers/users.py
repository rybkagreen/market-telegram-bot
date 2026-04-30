"""
FastAPI router для управления данными пользователя (Users).

Endpoints:
  GET /api/users/me          — данные текущего пользователя
  GET /api/users/me/stats    — статистика пользователя (репутация)
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.api.schemas.user import UserResponse
from src.db.repositories.reputation_repo import ReputationRepository
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])


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


AttentionSeverity = Literal["danger", "warning", "info", "success"]
AttentionType = Literal[
    "legal_profile_incomplete",
    "placement_pending_approval",
    "new_topup_success",
    "channel_verified",
    "contract_sign_required",
    "payout_ready",
    "dispute_requires_response",
]


class AttentionItem(BaseModel):
    """Элемент attention-feed — требует внимания пользователя."""

    type: AttentionType
    severity: AttentionSeverity
    title: str
    subtitle: str | None = None
    url: str | None = None
    created_at: datetime


class AttentionFeedResponse(BaseModel):
    """Агрегат для NotificationsCard (§7.9) — требует внимания."""

    items: list[AttentionItem]
    total: int  # count of danger+warning items (для red-dot в Topbar)


class ReferralItem(BaseModel):
    """Элемент списка рефералов.

    PII-safe: NO first_name/last_name (BL-050). Display layer renders
    `@username` if present else anonymized `User #{id}`.
    """

    id: int
    username: str | None = None
    created_at: str
    is_active: bool

    model_config = {"from_attributes": True}


class ReferralStatsResponse(BaseModel):
    """Реферальная статистика пользователя."""

    referral_code: str
    referral_link: str
    total_referrals: int
    active_referrals: int
    total_earned_rub: Decimal
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
        last_name=current_user.last_name,
        plan=plan_value,
        plan_expires_at=current_user.plan_expires_at,
        balance_rub=str(current_user.balance_rub),
        earned_rub=str(current_user.earned_rub),
        credits=current_user.credits,
        advertiser_xp=current_user.advertiser_xp,
        advertiser_level=current_user.advertiser_level,
        owner_xp=current_user.owner_xp,
        owner_level=current_user.owner_level,
        referral_code=current_user.referral_code,
        is_admin=current_user.is_admin,
        ai_generations_used=current_user.ai_uses_count,
        legal_status_completed=current_user.legal_status_completed,
        legal_profile_prompted_at=current_user.legal_profile_prompted_at,
        legal_profile_skipped_at=current_user.legal_profile_skipped_at,
        platform_rules_accepted_at=current_user.platform_rules_accepted_at,
        privacy_policy_accepted_at=current_user.privacy_policy_accepted_at,
        has_legal_profile=current_user.legal_profile is not None,
    )


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


class NeedsAcceptRulesResponse(BaseModel):
    """Reply for GET /api/users/needs-accept-rules — boolean version-aware flag."""

    needs_accept: bool

    model_config = {"frozen": True}


@router.get("/needs-accept-rules", response_model=NeedsAcceptRulesResponse)
async def needs_accept_rules(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NeedsAcceptRulesResponse:
    """True if user must (re-)accept platform rules at current CONTRACT_TEMPLATE_VERSION.

    Returns True when (a) no prior signed acceptance OR (b) stored
    template_version != current CONTRACT_TEMPLATE_VERSION (forced re-accept on
    version bump). Both audiences (mini_app + web_portal) — non-PII boolean
    flag, mirrors the carve-out for POST /api/contracts/accept-rules.
    """
    from src.core.services.contract_service import ContractService

    svc = ContractService(session)
    needs = await svc.needs_accept_rules(current_user.id)
    return NeedsAcceptRulesResponse(needs_accept=needs)


@router.get("/me/attention")
async def get_attention_feed(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AttentionFeedResponse:
    """
    Агрегат требующих внимания событий для NotificationsCard (§7.9).

    Сортировка: severity (danger > warning > info > success), потом created_at desc.
    `total` — количество danger+warning, используется как red-dot в Topbar bell.

    ВАЖНО: Этот эндпоинт должен быть объявлен ДО `/me/referrals` — строгий
    static-path-before-/{id} паттерн из project_fastapi_route_ordering.md.
    """
    from src.core.services.user_attention_service import (
        build_attention_feed,
        count_attention_dots,
    )

    feed_items = await build_attention_feed(current_user, session)
    return AttentionFeedResponse(
        items=[
            AttentionItem(
                type=it.type,
                severity=it.severity,
                title=it.title,
                subtitle=it.subtitle,
                url=it.url,
                created_at=it.created_at,
            )
            for it in feed_items
        ],
        total=count_attention_dots(feed_items),
    )


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
    user_repo = UserRepository(session)

    # Получаем рефералов (пользователи у которых referred_by_id == current_user.id)
    referral_users = await user_repo.get_referrals(current_user.id, limit=20)

    # Подсчёт общего количества
    total_referrals = await user_repo.count_referrals(current_user.id)

    # Active referrals — те кто совершил хотя бы одну оплату (есть запись в YookassaPayment со status=succeeded)
    active_referrals = await user_repo.count_active_referrals(current_user.id)

    # Total earned rub — сумма desired_balance из успешных платежей рефералов
    total_earned_rub = await user_repo.sum_referral_earnings(current_user.id)

    # Формируем ссылку (используем заглушку для bot_username, если не настроено)
    bot_username = "RekHarborBot"  # Default, can be overridden via settings
    referral_link = f"https://t.me/{bot_username}?start={current_user.referral_code}"

    # Формируем список рефералов
    referrals = []
    for ref in referral_users:
        # Проверяем активность (была ли оплата)
        is_active = await user_repo.has_successful_payment(ref.id)

        referrals.append(
            ReferralItem(
                id=ref.id,
                username=ref.username,
                created_at=ref.created_at.isoformat() if ref.created_at else "",
                is_active=is_active,
            )
        )

    return ReferralStatsResponse(
        referral_code=current_user.referral_code or "",
        referral_link=referral_link,
        total_referrals=total_referrals,
        active_referrals=active_referrals,
        total_earned_rub=total_earned_rub,
        referrals=referrals,
    )
