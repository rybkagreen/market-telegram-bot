"""
FastAPI роутер аналитики для Telegram Mini App.

Endpoints:
  GET /api/analytics/summary          — сводка: баланс, тариф, общая статистика
  GET /api/analytics/activity?days=7  — активность по дням для графика
  GET /api/analytics/top-chats        — топ чатов по успешности (PRO/BUSINESS)
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select

from src.api.dependencies import CurrentUser
from src.db.models.analytics import TelegramChat
from src.db.models.campaign import Campaign
from src.db.models.mailing_log import MailingLog
from src.db.models.user import User
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analytics"])


# ─── Схемы ──────────────────────────────────────────────────────


class SummaryResponse(BaseModel):
    # Баланс и тариф
    credits: int
    plan: str
    plan_expires_at: str | None
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
    username: str | None
    title: str
    member_count: int
    sent_count: int
    success_rate: float


class TopChatsResponse(BaseModel):
    chats: list[TopChatItem]


# ─── Хелперы ────────────────────────────────────────────────────


def _get_included_ai(plan: str) -> int:
    """Количество включённых ИИ-генераций по тарифу."""
    return {"pro": 5, "business": 20}.get(plan, 0)


def _plan_label(plan) -> str:
    """Строковое значение тарифа."""
    return plan.value if hasattr(plan, "value") else str(plan)


# ─── Endpoints ──────────────────────────────────────────────────


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(current_user: CurrentUser) -> SummaryResponse:
    """
    Сводная статистика пользователя.
    Используется Dashboard для первого экрана.
    """
    plan_str = _plan_label(current_user.plan)

    async with async_session_factory() as session:
        # Считаем кампании
        campaigns_result = await session.execute(
            select(
                func.count(Campaign.id).label("total"),
                func.count(Campaign.id)
                .filter(Campaign.status.in_(["running", "queued"]))
                .label("active"),
            ).where(Campaign.user_id == current_user.id)
        )
        camp_row = campaigns_result.one()

        # Считаем отправки из логов
        logs_result = await session.execute(
            select(
                func.count(MailingLog.id).label("total"),
                func.count(MailingLog.id).filter(MailingLog.status == "sent").label("sent"),
                func.count(MailingLog.id).filter(MailingLog.status == "failed").label("failed"),
            )
            .join(Campaign)
            .where(Campaign.user_id == current_user.id)
        )
        log_row = logs_result.one()

    total_sent = log_row.sent or 0
    total_failed = log_row.failed or 0
    total_logs = log_row.total or 0
    success_rate = round(total_sent / total_logs * 100, 1) if total_logs > 0 else 0.0

    expires_str = None
    if current_user.plan_expires_at:
        expires_str = current_user.plan_expires_at.isoformat()

    return SummaryResponse(
        credits=current_user.credits,
        plan=plan_str,
        plan_expires_at=expires_str,
        ai_generations_used=current_user.ai_generations_used,
        ai_included=_get_included_ai(plan_str),
        total_sent=total_sent,
        total_failed=total_failed,
        success_rate=success_rate,
        campaigns_count=camp_row.total or 0,
        campaigns_active=camp_row.active or 0,
    )


@router.get("/activity", response_model=ActivityResponse)
async def get_activity(
    current_user: CurrentUser,
    days: int = Query(default=7, ge=1, le=90),
) -> ActivityResponse:
    """
    Активность по дням для графика на Dashboard.
    Возвращает последние N дней.
    """
    since = datetime.now(UTC) - timedelta(days=days)

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                func.date(MailingLog.sent_at).label("day"),
                func.count(MailingLog.id).label("total"),
                func.count(MailingLog.id).filter(MailingLog.status == "sent").label("sent"),
                func.count(MailingLog.id).filter(MailingLog.status == "failed").label("failed"),
            )
            .join(Campaign)
            .where(
                Campaign.user_id == current_user.id,
                MailingLog.sent_at >= since,
            )
            .group_by(func.date(MailingLog.sent_at))
            .order_by(func.date(MailingLog.sent_at))
        )
        rows = result.all()

    # Строим полный список дней (даже пустых)
    day_labels_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    data_by_day = {str(row.day): (row.sent or 0, row.failed or 0) for row in rows}

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


@router.get("/top-chats", response_model=TopChatsResponse)
async def get_top_chats(
    current_user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=20),
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
        result = await session.execute(
            select(
                TelegramChat.username,
                TelegramChat.title,
                TelegramChat.member_count,
                func.count(MailingLog.id).label("sent_count"),
                (
                    func.count(MailingLog.id).filter(MailingLog.status == "sent")
                    * 100.0
                    / func.nullif(func.count(MailingLog.id), 0)
                ).label("success_rate"),
            )
            .join(MailingLog, MailingLog.chat_id == TelegramChat.id)
            .join(Campaign, Campaign.id == MailingLog.campaign_id)
            .where(Campaign.user_id == current_user.id)
            .group_by(TelegramChat.id)
            .having(func.count(MailingLog.id) >= 3)
            .order_by(
                (
                    func.count(MailingLog.id).filter(MailingLog.status == "sent")
                    * 100.0
                    / func.nullif(func.count(MailingLog.id), 0)
                ).desc()
            )
            .limit(limit)
        )
        rows = result.all()

    return TopChatsResponse(
        chats=[
            TopChatItem(
                username=row.username,
                title=row.title or "Без названия",
                member_count=row.member_count or 0,
                sent_count=row.sent_count or 0,
                success_rate=round(row.success_rate or 0, 1),
            )
            for row in rows
        ]
    )


# ─── Тематики кампаний ───────────────────────────────────────────


class TopicItem(BaseModel):
    topic: str
    count: int
    percentage: float


class TopicsResponse(BaseModel):
    topics: list[TopicItem]


@router.get("/topics", response_model=TopicsResponse)
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
            select(Campaign.filters_json).where(
                Campaign.user_id == current_user.id,
                Campaign.status == "done",
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


@router.get("/campaigns/{campaign_id}/ai-insights", response_model=AIInsightsResponse)
async def get_campaign_ai_insights(
    campaign_id: int,
    current_user: CurrentUser,
) -> AIInsightsResponse:
    """
    AI-аналитика конкретной кампании через OpenRouter.
    Доступна только для PRO и BUSINESS тарифов.
    Списывает 1 ИИ-генерацию из лимита пользователя.
    """
    from sqlalchemy import update

    from src.core.services.campaign_analytics_ai import campaign_analytics_ai
    from src.db.models.campaign import Campaign

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
    if current_user.ai_generations_used >= limit and plan_str != "business":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"AI generation limit reached ({current_user.ai_generations_used}/{limit})",
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
    if campaign.user_id != current_user.id:
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

    # Получаем статистику кампании
    async with async_session_factory() as session:
        logs_result = await session.execute(
            select(
                func.count(MailingLog.id).label("total"),
                func.count(MailingLog.id).filter(MailingLog.status == "sent").label("sent"),
                func.count(MailingLog.id).filter(MailingLog.status == "failed").label("failed"),
                func.min(MailingLog.sent_at).label("started_at"),
            ).where(MailingLog.campaign_id == campaign_id)
        )
        log_row = logs_result.one()

    total_sent = log_row.sent or 0
    total_failed = log_row.failed or 0
    total_logs = log_row.total or 0
    success_rate = round(total_sent / total_logs * 100, 1) if total_logs > 0 else 0.0

    campaign_data = {
        "title": campaign.title or "Без названия",
        "sent": total_sent,
        "failed": total_failed,
        "success_rate": success_rate,
        "topics": (campaign.filters_json or {}).get("topics", []),
        "date": log_row.started_at.strftime("%d.%m.%Y") if log_row.started_at else "",
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
            .values(ai_generations_used=current_user.ai_generations_used + 1)
        )
        await session.commit()

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


# ─── Публичная статистика (Спринт 0) ───────────────────────────


class PlatformStatsResponse(BaseModel):
    """Публичная статистика платформы (Спринт 0)."""

    active_channels: int
    total_reach: int
    campaigns_launched: int
    campaigns_completed: int
    avg_channel_rating: float
    total_payouts: float


@router.get("/stats/public", response_model=PlatformStatsResponse)
async def get_public_stats() -> PlatformStatsResponse:
    """
    Публичная статистика платформы — доступна без авторизации.
    Используется для Mini App дашборда и лендинга.
    """
    from src.core.services.analytics_service import analytics_service

    stats = await analytics_service.get_platform_stats()

    return PlatformStatsResponse(
        active_channels=stats.active_channels,
        total_reach=stats.total_reach,
        campaigns_launched=stats.campaigns_launched,
        campaigns_completed=stats.campaigns_completed,
        avg_channel_rating=stats.avg_channel_rating,
        total_payouts=float(stats.total_payouts),
    )


# ─── CTR-трекинг (Спринт 2) ────────────────────────────────────


@router.get("/r/{short_code}")
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
