"""
FastAPI роутер аналитики для Telegram Mini App.

Endpoints:
  GET /api/analytics/summary          — сводка: баланс, тариф, общая статистика
  GET /api/analytics/activity?days=7  — активность по дням для графика
  GET /api/analytics/top-chats        — топ чатов по успешности (PRO/BUSINESS)
  GET /api/analytics/advertiser       — аналитика рекламодателя (Mini App)
  GET /api/analytics/owner            — аналитика владельца (Mini App)
"""

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import IntEnum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import CurrentUser
from src.core.services.analytics_service import AnalyticsService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.user import User
from src.db.session import async_session_factory

Campaign = PlacementRequest  # alias for legacy references in topics/ai-insights endpoints

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analytics"])


# ─── Схемы ──────────────────────────────────────────────────────


class SummaryResponse(BaseModel):
    # Баланс и тариф
    balance_rub: Decimal
    plan: str
    plan_expires_at: str | None = None
    ai_generations_used: int
    ai_included: int

    # Статистика за всё время
    total_sent: int
    total_failed: int
    success_rate: float
    campaigns_count: int
    campaigns_active: int


class ActivityPoint(BaseModel):
    date: str  # "Пн", "Вт", "Ср" и т.д.
    sent: int
    failed: int


class ActivityResponse(BaseModel):
    points: list[ActivityPoint]
    total_sent: int
    period_days: int


class TopChatItem(BaseModel):
    username: str | None = None
    title: str
    member_count: int
    sent_count: int
    success_rate: float


class TopChatsResponse(BaseModel):
    chats: list[TopChatItem]


class CashflowDataPoint(BaseModel):
    """Точка графика cashflow — один день."""

    date: date
    income: Decimal
    expense: Decimal


class CashflowResponse(BaseModel):
    """Dual-line income/expense cashflow для PerformanceChart (§7.7)."""

    period_days: int
    total_income: Decimal
    total_expense: Decimal
    net: Decimal
    points: list[CashflowDataPoint]


# ─── Mini App Analytics Schemas ─────────────────────────────────


class MiniAppChannel(BaseModel):
    id: int
    username: str
    title: str | None = None
    member_count: int


class AdvertiserAnalyticsResponse(BaseModel):
    total_campaigns: int
    total_reach: int
    total_spent: str
    avg_ctr: float
    top_channels: list[dict]
    by_category: list[dict]


class OwnerAnalyticsResponse(BaseModel):
    total_earned: str
    total_publications: int
    avg_rating: float
    channel_count: int
    by_channel: list[dict]
    earnings_period: dict


# ─── Хелперы ────────────────────────────────────────────────────


def _get_included_ai(plan: str) -> int:
    """Количество включённых ИИ-генераций по тарифу."""
    return {"pro": 5, "business": 20}.get(plan, 0)


def _plan_label(plan) -> str:
    """Строковое значение тарифа."""
    return plan.value if hasattr(plan, "value") else str(plan)


# ─── Endpoints ──────────────────────────────────────────────────


@router.get("/summary")
async def get_summary(current_user: CurrentUser) -> SummaryResponse:
    """
    Сводная статистика пользователя.
    Используется Dashboard для первого экрана.
    """
    plan_str = _plan_label(current_user.plan)

    async with async_session_factory() as session:
        service = AnalyticsService()
        stats = await service.get_advertiser_stats(advertiser_id=current_user.id, session=session)

        active_result = await session.execute(
            select(func.count(PlacementRequest.id)).where(
                PlacementRequest.advertiser_id == current_user.id,
                PlacementRequest.status.in_([
                    PlacementStatus.pending_owner,
                    PlacementStatus.pending_payment,
                    PlacementStatus.escrow,
                ]),
            )
        )
        campaigns_active = active_result.scalar() or 0

    total_sent = stats.completed_placements
    total_failed = max(0, stats.total_placements - stats.completed_placements - campaigns_active)
    success_rate = (
        round(stats.completed_placements / stats.total_placements * 100, 1)
        if stats.total_placements > 0
        else 0.0
    )

    expires_str = None
    if current_user.plan_expires_at:
        expires_str = current_user.plan_expires_at.isoformat()

    return SummaryResponse(
        balance_rub=current_user.balance_rub,
        plan=plan_str,
        plan_expires_at=expires_str,
        ai_generations_used=current_user.ai_uses_count,
        ai_included=_get_included_ai(plan_str),
        total_sent=total_sent,
        total_failed=total_failed,
        success_rate=success_rate,
        campaigns_count=stats.total_placements,
        campaigns_active=campaigns_active,
    )


@router.get("/activity")
async def get_activity(
    current_user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> ActivityResponse:
    """
    Активность по дням для графика на Dashboard.
    Возвращает последние N дней.
    """
    from sqlalchemy import func, select

    # Используем данные из PlacementRequest.last_published_at
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.date_trunc("day", PlacementRequest.last_published_at).label("day"),
                func.sum(PlacementRequest.sent_count).label("sent"),
                func.sum(PlacementRequest.failed_count).label("failed"),
            )
            .where(
                PlacementRequest.advertiser_id == current_user.id,
                PlacementRequest.last_published_at.isnot(None),
                PlacementRequest.last_published_at >= datetime.now(UTC) - timedelta(days=days),
            )
            .group_by("day")
            .order_by("day")
        )
        rows = result.all()

    # Маппинг результатов по дням
    day_labels_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    data_by_day: dict = {}
    for row in rows:
        if row.day:
            day_str = str(row.day.date())
            data_by_day[day_str] = (int(row.sent or 0), int(row.failed or 0))

    points = []
    total_sent = 0
    for i in range(days):
        day = (datetime.now(UTC) - timedelta(days=days - 1 - i)).date()
        day_str = str(day)
        sent, failed = data_by_day.get(day_str, (0, 0))

        # Короткая метка: для 7 дней — "Пн", для 30+ дней — "01.03"
        label = day_labels_ru[day.weekday()] if days <= 7 else day.strftime("%d.%m")
        points.append(ActivityPoint(date=label, sent=sent, failed=failed))
        total_sent += sent

    return ActivityResponse(
        points=points,
        total_sent=total_sent,
        period_days=days,
    )


# Типы транзакций — направление движения средств по балансу пользователя.
# amount всегда положителен; знак определяется типом.
_INCOME_TX_TYPES = {
    "topup",
    "bonus",
    "admin_credit",
    "escrow_release",
    "refund_full",
    "refund_partial",
    "refund",
    "owner_cancel_compensation",
    "failed_permissions_refund",
    "gamification_bonus",
}
_EXPENSE_TX_TYPES = {
    "spend",
    "escrow_freeze",
    "payout",
    "payout_fee",
    "platform_fee",
    "cancel_penalty",
    "commission",
    "ndfl_withholding",
}


class CashflowPeriod(IntEnum):
    """
    Период для графика cashflow. IntEnum вместо Literal[7,30,90] —
    FastAPI коэрсит query-string в int→enum автоматически, а
    Pydantic 2 Literal в strict-режиме не коэрсит "30" в 30.
    """

    SEVEN_DAYS = 7
    THIRTY_DAYS = 30
    NINETY_DAYS = 90


@router.get("/cashflow")
async def get_cashflow(
    current_user: CurrentUser,
    days: Annotated[
        CashflowPeriod, Query(description="Период: 7/30/90 дней")
    ] = CashflowPeriod.THIRTY_DAYS,
) -> CashflowResponse:
    """
    Dual-line income/expense cashflow для PerformanceChart (§7.7).

    Группирует Transactions пользователя по дате и классифицирует по типу:
    income (topup/refund/bonus/...) vs expense (spend/escrow_freeze/payout/...).

    Zero-fill: пропущенные дни заполнены (0, 0), чтобы длина points == days
    и ось X графика оставалась равномерной.
    """
    from src.db.models.transaction import Transaction, TransactionType

    since_dt = datetime.now(UTC) - timedelta(days=days)
    since_date = since_dt.date()

    income_types = [TransactionType(t) for t in _INCOME_TX_TYPES]
    expense_types = [TransactionType(t) for t in _EXPENSE_TX_TYPES]

    day_col = func.date(Transaction.created_at).label("day")

    async with async_session_factory() as session:
        result = await session.execute(
            select(day_col, Transaction.type, func.sum(Transaction.amount))
            .where(
                Transaction.user_id == current_user.id,
                Transaction.created_at >= since_dt,
                Transaction.is_reversed.is_(False),
            )
            .group_by(day_col, Transaction.type)
            .order_by(day_col)
        )
        rows = result.all()

    by_day: dict[date, tuple[Decimal, Decimal]] = {}
    for day, tx_type, total in rows:
        if day is None:
            continue
        day_date = day if isinstance(day, date) else date.fromisoformat(str(day))
        income, expense = by_day.get(day_date, (Decimal("0"), Decimal("0")))
        amount = Decimal(str(total or 0))
        if tx_type in income_types:
            income += amount
        elif tx_type in expense_types:
            expense += amount
        by_day[day_date] = (income, expense)

    points: list[CashflowDataPoint] = []
    total_income = Decimal("0")
    total_expense = Decimal("0")
    for i in range(days):
        d = since_date + timedelta(days=i + 1)  # first point = since+1 day
        income, expense = by_day.get(d, (Decimal("0"), Decimal("0")))
        points.append(CashflowDataPoint(date=d, income=income, expense=expense))
        total_income += income
        total_expense += expense

    return CashflowResponse(
        period_days=days,
        total_income=total_income,
        total_expense=total_expense,
        net=total_income - total_expense,
        points=points,
    )


@router.get("/top-chats", responses={403: {"description": "PRO/BUSINESS plans only"}})
async def get_top_chats(
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> TopChatsResponse:
    """
    Топ чатов по успешности рассылки.
    Доступно только для PRO и BUSINESS.
    """
    plan_str = _plan_label(current_user.plan)
    if plan_str not in ("pro", "business"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Top chats available for PRO and BUSINESS plans only",
        )

    async with async_session_factory() as session:
        service = AnalyticsService()
        channels = await service.get_top_channels_by_reach(
            advertiser_id=current_user.id, session=session, limit=limit
        )

    return TopChatsResponse(
        chats=[
            TopChatItem(
                username=ch["username"],
                title=ch["title"] or "Без названия",
                member_count=0,
                sent_count=ch["total_reach"],
                success_rate=0.0,
            )
            for ch in channels
        ]
    )


# ─── Тематики кампаний ───────────────────────────────────────────


class TopicItem(BaseModel):
    topic: str
    count: int
    percentage: float


class TopicsResponse(BaseModel):
    topics: list[TopicItem]


@router.get("/topics", responses={403: {"description": "PRO/BUSINESS plans only"}})
async def get_topics_distribution(
    current_user: CurrentUser,
) -> TopicsResponse:
    """
    Распределение кампаний по тематикам.
    Используется для DonutChart на странице Analytics.
    Доступно только PRO и BUSINESS.
    """
    plan_str = _plan_label(current_user.plan)
    if plan_str not in ("pro", "business"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics available for PRO and BUSINESS only",
        )

    from collections import Counter

    async with async_session_factory() as session:
        # Берём тематики из filters_json кампаний пользователя
        result = await session.execute(
            select(Campaign.filters_json).where(  # type: ignore[attr-defined]
                Campaign.advertiser_id == current_user.id,
                Campaign.status == PlacementStatus.published,
            )
        )
        rows = result.scalars().all()

    # Подсчитываем тематики из JSON фильтров
    topic_counter: Counter = Counter()

    for filters_json in rows:
        if not filters_json:
            continue
        topics = filters_json.get("topics", [])
        if isinstance(topics, list):
            for t in topics:
                if t:
                    topic_counter[t] += 1

    # Если нет данных — возвращаем пустой список
    if not topic_counter:
        return TopicsResponse(topics=[])

    total = sum(topic_counter.values())
    topics_list = [
        TopicItem(
            topic=topic,
            count=count,
            percentage=round(count / total * 100, 1),
        )
        for topic, count in topic_counter.most_common(8)
    ]

    return TopicsResponse(topics=topics_list)


# ─── AI-аналитика кампаний ──────────────────────────────────────


class AIInsightsResponse(BaseModel):
    campaign_id: int
    plan: str
    insights: list[str]
    recommendations: list[str]
    performance_grade: str
    forecast: str | None = None
    ab_test_suggestion: str | None = None
    generated_at: str


@router.get(
    "/campaigns/{campaign_id}/ai-insights",
    responses={
        403: {"description": "PRO/BUSINESS plans only or not your campaign"},
        404: {"description": "Campaign not found"},
        400: {"description": "Campaign not completed"},
        429: {"description": "AI generation limit reached"},
        409: {"description": "Data conflict"},
    },
)
async def get_campaign_ai_insights(
    campaign_id: int,
    current_user: CurrentUser,
) -> AIInsightsResponse:
    """
    AI-аналитика конкретной кампании через Mistral AI.
    Доступна только для PRO и BUSINESS тарифов.
    Списывает 1 ИИ-генерацию из лимита пользователя.
    """
    from sqlalchemy import update

    from src.core.services.campaign_analytics_ai import campaign_analytics_ai

    plan_str = _plan_label(current_user.plan)

    # Проверка тарифа
    if plan_str not in ("pro", "business"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI insights available for PRO and BUSINESS plans only",
        )

    # Проверка лимита генераций
    ai_limits = {"pro": 5, "business": 20}
    limit = ai_limits.get(plan_str, 0)
    if current_user.ai_uses_count >= limit and plan_str != "business":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"AI generation limit reached ({current_user.ai_uses_count}/{limit})",
        )

    # Получаем данные кампании
    async with async_session_factory() as session:
        campaign = await session.get(Campaign, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Проверка что кампания принадлежит пользователю
    if campaign.advertiser_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only analyze your own campaigns",
        )

    camp_status = (
        campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status)
    )
    if camp_status != "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI insights available only for completed campaigns",
        )

    # MailingLog removed — use zero stats
    total_sent = 0
    total_failed = 0
    success_rate = 0.0

    campaign_data = {
        "title": getattr(campaign, "title", None) or campaign.ad_text[:50] or "Без названия",
        "sent": total_sent,
        "failed": total_failed,
        "success_rate": success_rate,
        "topics": (getattr(campaign, "filters_json", None) or {}).get("topics", []),
        "date": "",
    }

    # Вызываем AI
    result = await campaign_analytics_ai.generate_campaign_insights(
        campaign_data=campaign_data,
        plan=plan_str,
    )

    # Списываем генерацию
    async with async_session_factory() as session:
        await session.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(ai_uses_count=current_user.ai_uses_count + 1)
        )
        try:
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Конфликт данных: запись уже существует или нарушено ограничение",
            ) from e

    return AIInsightsResponse(
        campaign_id=campaign_id,
        plan=plan_str,
        insights=result.get("insights", []),
        recommendations=result.get("recommendations", []),
        performance_grade=result.get("performance_grade", "N/A"),
        forecast=result.get("forecast"),
        ab_test_suggestion=result.get("ab_test_suggestion"),
        generated_at=datetime.now(UTC).isoformat(),
    )


# ─── Mini App Analytics Endpoints ──────────────────────────────


@router.get("/advertiser")
async def get_advertiser_analytics(
    current_user: CurrentUser,
) -> AdvertiserAnalyticsResponse:  # NOSONAR: python:S3776
    """
    Аналитика рекламодателя для Mini App.
    Возвращает данные о кампаниях, охвате, CTR и топ каналах.
    """
    async with async_session_factory() as session:
        # Получаем общую статистику по кампаниям рекламодателя
        # Используем published статус как завершённый (published = размещено и завершено)
        placements_result = await session.execute(
            select(
                func.count(PlacementRequest.id).label("total_campaigns"),
                func.sum(PlacementRequest.final_price).label("total_spent"),
                func.sum(PlacementRequest.clicks_count).label("total_clicks"),
                func.sum(PlacementRequest.published_reach).label("total_reach"),
            ).where(
                PlacementRequest.advertiser_id == current_user.id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        placement_stats = placements_result.first()

        total_campaigns = placement_stats.total_campaigns if placement_stats else 0
        total_reach = (placement_stats.total_reach or 0) if placement_stats else 0
        total_spent = str(
            (placement_stats.total_spent or Decimal("0")) if placement_stats else Decimal("0")
        )
        total_clicks = (placement_stats.total_clicks or 0) if placement_stats else 0

        # Рассчитываем CTR
        avg_ctr = round((total_clicks / total_reach * 100), 2) if total_reach > 0 else 0.0

        # Топ каналов по охвату
        top_channels_result = await session.execute(
            select(
                PlacementRequest.channel_id,
                func.sum(PlacementRequest.published_reach).label("reach"),
            )
            .where(
                PlacementRequest.advertiser_id == current_user.id,
                PlacementRequest.status == PlacementStatus.published,
            )
            .group_by(PlacementRequest.channel_id)
            .order_by(func.sum(PlacementRequest.published_reach).desc())
            .limit(5)
        )
        top_channels_rows = top_channels_result.all()

        # Получаем данные каналов
        top_channels = []
        for channel_row in top_channels_rows:
            from src.db.models.telegram_chat import TelegramChat

            channel = await session.get(TelegramChat, channel_row.channel_id)
            if channel:
                # Рассчитываем CTR для канала
                channel_placements = await session.execute(
                    select(
                        func.sum(PlacementRequest.clicks_count).label("clicks"),
                        func.sum(PlacementRequest.published_reach).label("reach"),
                    ).where(
                        PlacementRequest.channel_id == channel_row.channel_id,
                        PlacementRequest.advertiser_id == current_user.id,
                    )
                )
                channel_stats = channel_placements.first()
                channel_ctr = (
                    round((channel_stats.clicks or 0) / (channel_stats.reach or 1) * 100, 2)
                    if channel_stats and channel_stats.reach
                    else 0.0
                )

                top_channels.append({
                    "channel": {
                        "id": channel.id,
                        "username": channel.username,
                        "title": channel.title,
                        "member_count": channel.member_count,
                    },
                    "reach": channel_row.reach or 0,
                    "ctr": channel_ctr,
                })

        # Распределение по категориям (заглушка, пока нет данных)
        by_category: list[dict] = []

    return AdvertiserAnalyticsResponse(
        total_campaigns=total_campaigns,
        total_reach=total_reach,
        total_spent=total_spent,
        avg_ctr=avg_ctr,
        top_channels=top_channels,
        by_category=by_category,
    )


@router.get("/owner")
async def get_owner_analytics(current_user: CurrentUser) -> OwnerAnalyticsResponse:
    """
    Аналитика владельца канала для Mini App.
    Возвращает данные о заработке, публикациях и рейтинге.
    """
    from src.db.models.telegram_chat import TelegramChat

    async with async_session_factory() as session:
        # Получаем все каналы владельца
        channels_result = await session.execute(
            select(TelegramChat).where(TelegramChat.owner_id == current_user.id)
        )
        channels = channels_result.scalars().all()

        # Общая статистика по публикациям
        placements_result = await session.execute(
            select(
                func.count(PlacementRequest.id).label("total_publications"),
                func.sum(PlacementRequest.final_price).label("total_earned"),
            ).where(
                PlacementRequest.owner_id == current_user.id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        placement_stats = placements_result.first()

        total_publications = (placement_stats.total_publications or 0) if placement_stats else 0
        total_earned = str(
            (placement_stats.total_earned or Decimal("0")) if placement_stats else Decimal("0")
        )

        # Средний рейтинг (заглушка — используем рейтинг каналов)
        if channels:
            avg_rating = round(sum(ch.rating for ch in channels) / len(channels), 1)
        else:
            avg_rating = 0.0

        # Заработок по каналам
        by_channel = []
        for channel in channels:
            channel_placements = await session.execute(
                select(
                    func.count(PlacementRequest.id).label("publications"),
                    func.sum(PlacementRequest.final_price).label("earned"),
                ).where(
                    PlacementRequest.channel_id == channel.id,
                    PlacementRequest.owner_id == current_user.id,
                    PlacementRequest.status == PlacementStatus.published,
                )
            )
            channel_stats = channel_placements.first()
            by_channel.append({
                "channel": {
                    "id": channel.id,
                    "username": channel.username,
                    "title": channel.title,
                    "member_count": channel.member_count,
                },
                "earned": str(
                    (channel_stats.earned or Decimal("0")) if channel_stats else Decimal("0")
                ),
                "publications": (channel_stats.publications or 0) if channel_stats else 0,
            })

        # Заработок за период (сегодня, неделя, месяц)
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=now.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        async def get_period_earnings(start_date: datetime) -> Decimal:
            result = await session.execute(
                select(func.sum(PlacementRequest.final_price)).where(
                    PlacementRequest.owner_id == current_user.id,
                    PlacementRequest.status == PlacementStatus.published,
                    PlacementRequest.published_at >= start_date,
                )
            )
            return result.scalar() or Decimal("0")

        earnings_period = {
            "today": str(await get_period_earnings(today_start)),
            "week": str(await get_period_earnings(week_start)),
            "month": str(await get_period_earnings(month_start)),
            "total": total_earned,
        }

    return OwnerAnalyticsResponse(
        total_earned=total_earned,
        total_publications=total_publications,
        avg_rating=avg_rating,
        channel_count=len(channels),
        by_channel=by_channel,
        earnings_period=earnings_period,
    )


# ─── Публичная статистика (Спринт 0) ───────────────────────────


class PlatformStatsResponse(BaseModel):
    """Публичная статистика платформы (Спринт 0)."""

    total_users: int
    total_placements: int
    total_revenue: float


@router.get("/stats/public")
async def get_public_stats() -> PlatformStatsResponse:
    """
    Публичная статистика платформы — доступна без авторизации.
    Используется для Mini App дашборда и лендинга.
    """
    from src.core.services.analytics_service import AnalyticsService

    analytics_service = AnalyticsService()
    stats = await analytics_service.get_public_stats()

    return PlatformStatsResponse(
        total_users=stats.total_users,
        total_placements=stats.total_placements,
        total_revenue=float(stats.total_revenue),
    )


# ─── CTR-трекинг (Спринт 2) ────────────────────────────────────


@router.get("/r/{short_code}", responses={404: {"description": "Short link not found"}})
async def redirect_short_link(short_code: str):
    """
    Редирект по короткой ссылке с подсчётом кликов.
    Используется для CTR-трекинга кампаний.
    """
    from fastapi import Response

    from src.core.services.link_tracking_service import link_tracking_service

    original_url = await link_tracking_service.track_click(short_code)

    if not original_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )

    # Редирект на исходную ссылку
    return Response(
        status_code=302,
        headers={"Location": original_url},
        content=f"<html><head><meta http-equiv='refresh' content='0;url={original_url}'></head></html>",
        media_type="text/html",
    )
