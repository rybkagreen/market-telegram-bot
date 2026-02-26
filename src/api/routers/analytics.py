"""
Analytics router для получения статистики и аналитики.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.api.dependencies import CurrentUser
from src.core.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter()


# === Pydantic схемы ===


class CampaignStatsResponse(BaseModel):
    """Статистика кампании."""

    total_sent: int
    total_failed: int
    total_skipped: int
    total_pending: int
    success_rate: float
    total_cost: str
    reach_estimate: int


class UserSummaryResponse(BaseModel):
    """Сводка пользователя."""

    total_campaigns: int
    active_campaigns: int
    completed_campaigns: int
    total_spent: str
    avg_success_rate: float
    total_chats_reached: int


class ChatPerformanceResponse(BaseModel):
    """Эффективность чата."""

    chat_telegram_id: int
    chat_title: str
    total_sent: int
    success_rate: float
    avg_rating: float


class DailyStatResponse(BaseModel):
    """Ежедневная статистика."""

    date: str
    total: int
    sent: int
    failed: int
    total_cost: float


class ComparisonReportResponse(BaseModel):
    """Сравнение кампаний."""

    campaigns: list[dict]
    summary: dict


# === Эндпоинты ===


@router.get("/campaign/{campaign_id}", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    campaign_id: int,
    current_user: CurrentUser,
):
    """
    Получить статистику кампании.

    Args:
        campaign_id: ID кампании.
        current_user: Текущий пользователь.

    Returns:
        Статистика кампании.
    """
    from src.db.repositories.campaign_repo import CampaignRepository
    from src.db.session import async_session_factory

    # Проверяем принадлежность кампании
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        if campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    # Получаем статистику
    stats = await analytics_service.get_campaign_stats(campaign_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign stats not found",
        )

    return CampaignStatsResponse(
        total_sent=stats.total_sent,
        total_failed=stats.total_failed,
        total_skipped=stats.total_skipped,
        total_pending=stats.total_pending,
        success_rate=stats.success_rate,
        total_cost=str(stats.total_cost),
        reach_estimate=stats.reach_estimate,
    )


@router.get("/summary", response_model=UserSummaryResponse)
async def get_user_summary(
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365),
):
    """
    Получить сводную аналитику пользователя.

    Args:
        current_user: Текущий пользователь.
        days: Период в днях.

    Returns:
        Сводка пользователя.
    """
    summary = await analytics_service.get_user_summary(
        user_id=current_user.id,
        days=days,
    )

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User summary not found",
        )

    return UserSummaryResponse(
        total_campaigns=summary.total_campaigns,
        active_campaigns=summary.active_campaigns,
        completed_campaigns=summary.completed_campaigns,
        total_spent=str(summary.total_spent),
        avg_success_rate=summary.avg_success_rate,
        total_chats_reached=summary.total_chats_reached,
    )


@router.get("/top-chats", response_model=list[ChatPerformanceResponse])
async def get_top_chats(
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=100),
):
    """
    Получить лучшие чаты по эффективности.

    Args:
        current_user: Текущий пользователь.
        limit: Количество чатов.

    Returns:
        Список лучших чатов.
    """
    top_chats = await analytics_service.get_top_performing_chats(
        user_id=current_user.id,
        limit=limit,
    )

    return [
        ChatPerformanceResponse(
            chat_telegram_id=chat.chat_telegram_id,
            chat_title=chat.chat_title,
            total_sent=chat.total_sent,
            success_rate=chat.success_rate,
            avg_rating=chat.avg_rating,
        )
        for chat in top_chats
    ]


@router.get("/daily", response_model=list[DailyStatResponse])
async def get_daily_stats(
    current_user: CurrentUser,
    days: int = Query(7, ge=1, le=90),
):
    """
    Получить ежедневную статистику.

    Args:
        current_user: Текущий пользователь.
        days: Количество дней.

    Returns:
        Список статистик по дням.
    """
    daily_stats = await analytics_service.get_daily_stats(
        user_id=current_user.id,
        days=days,
    )

    return [
        DailyStatResponse(
            date=stat["date"],
            total=stat["total"],
            sent=stat["sent"],
            failed=stat["failed"],
            total_cost=stat["total_cost"],
        )
        for stat in daily_stats
    ]


@router.post("/compare", response_model=ComparisonReportResponse)
async def compare_campaigns(
    campaign_ids: list[int],
    current_user: CurrentUser,
):
    """
    Сравнить несколько кампаний.

    Args:
        campaign_ids: Список ID кампаний.
        current_user: Текущий пользователь.

    Returns:
        Сравнительный отчёт.
    """
    if len(campaign_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 campaign IDs required",
        )

    # Проверяем принадлежность всех кампаний
    from src.db.repositories.campaign_repo import CampaignRepository
    from src.db.session import async_session_factory

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)

        for campaign_id in campaign_ids:
            campaign = await campaign_repo.get_by_id(campaign_id)
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Campaign {campaign_id} not found",
                )
            if campaign.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to campaign {campaign_id}",
                )

    # Получаем сравнение
    report = await analytics_service.compare_campaigns(campaign_ids)

    return ComparisonReportResponse(**report)
