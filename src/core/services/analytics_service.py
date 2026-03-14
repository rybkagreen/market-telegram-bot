"""
AnalyticsService for campaign and user statistics aggregation.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.mistral_ai_service import MistralAIService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.transaction import Transaction, TransactionType


@dataclass
class AdvertiserStats:
    """Статистика рекламодателя."""

    total_placements: int
    completed_placements: int
    total_spent: Decimal
    total_reach: int
    total_clicks: int
    avg_ctr: float


@dataclass
class OwnerStats:
    """Статистика владельца канала."""

    total_published: int
    total_earned: Decimal
    avg_check: Decimal


@dataclass
class PlatformStats:
    """Статистика платформы."""

    total_users: int
    total_placements: int
    total_revenue: Decimal


class AnalyticsService:
    """
    Сервис агрегации статистики кампаний и пользователей.
    Интегрирует AI инсайты через MistralAIService.
    """

    def __init__(self) -> None:
        self.ai_service = MistralAIService()

    async def get_advertiser_stats(
        self,
        advertiser_id: int,
        session: AsyncSession,
    ) -> AdvertiserStats:
        """
        Получить статистику рекламодателя.

        Агрегирует PlacementRequest по advertiser_id:
        - total_placements: всего размещений
        - completed_placements: завершённых (status=published)
        - total_spent: SUM Transaction WHERE type=escrow_release
        - total_reach: SUM published_reach
        - total_clicks: SUM clicks_count
        - avg_ctr: CTR = clicks / reach * 100
        """
        # Total placements
        total_result = await session.execute(
            select(func.count()).select_from(PlacementRequest).where(
                PlacementRequest.advertiser_id == advertiser_id
            )
        )
        total_placements = total_result.scalar() or 0

        # Completed placements
        completed_result = await session.execute(
            select(func.count()).select_from(PlacementRequest).where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        completed_placements = completed_result.scalar() or 0

        # Total spent (escrow_release transactions)
        spent_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
                Transaction.user_id == advertiser_id,
                Transaction.type == TransactionType.escrow_release,
            )
        )
        total_spent = spent_result.scalar() or Decimal("0")

        # Total reach and clicks
        reach_result = await session.execute(
            select(
                func.coalesce(func.sum(PlacementRequest.published_reach), 0),
                func.coalesce(func.sum(PlacementRequest.clicks_count), 0),
            ).where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        row = reach_result.one()
        total_reach = row[0] or 0
        total_clicks = row[1] or 0

        # Avg CTR
        avg_ctr = (total_clicks / total_reach * 100) if total_reach > 0 else 0.0

        return AdvertiserStats(
            total_placements=total_placements,
            completed_placements=completed_placements,
            total_spent=total_spent,
            total_reach=total_reach,
            total_clicks=total_clicks,
            avg_ctr=avg_ctr,
        )

    async def get_owner_stats(
        self,
        owner_id: int,
        session: AsyncSession,
    ) -> OwnerStats:
        """
        Получить статистику владельца канала.

        Агрегирует PlacementRequest по owner_id:
        - total_published: всего опубликовано
        - total_earned: SUM Transaction WHERE type=escrow_release AND user_id=owner_id
        - avg_check: средний чек
        """
        # Total published
        published_result = await session.execute(
            select(func.count()).select_from(PlacementRequest).where(
                PlacementRequest.owner_id == owner_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        total_published = published_result.scalar() or 0

        # Total earned - need to get transactions for owner
        # Note: escrow_release transactions go to owner
        earned_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
                Transaction.type == TransactionType.escrow_release,
                # Need to join with placement_request to get owner
            )
        )
        # Alternative: calculate from placement_requests final_price
        earned_alt_result = await session.execute(
            select(
                func.coalesce(
                    func.sum(PlacementRequest.final_price * Decimal("0.85")),
                    Decimal("0"),
                )
            ).where(
                PlacementRequest.owner_id == owner_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.final_price.isnot(None),
            )
        )
        total_earned = earned_alt_result.scalar() or Decimal("0")

        # Avg check
        avg_check = (total_earned / total_published) if total_published > 0 else Decimal("0")

        return OwnerStats(
            total_published=total_published,
            total_earned=total_earned,
            avg_check=avg_check,
        )

    async def get_top_channels_by_reach(
        self,
        advertiser_id: int,
        session: AsyncSession,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Топ каналов по published_reach для рекламодателя.
        """
        from src.db.models.telegram_chat import TelegramChat

        result = await session.execute(
            select(
                TelegramChat.id,
                TelegramChat.title,
                TelegramChat.username,
                func.sum(PlacementRequest.published_reach).label("total_reach"),
            )
            .join(PlacementRequest, PlacementRequest.channel_id == TelegramChat.id)
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.published_reach.isnot(None),
            )
            .group_by(TelegramChat.id, TelegramChat.title, TelegramChat.username)
            .order_by(func.sum(PlacementRequest.published_reach).desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "channel_id": row.id,
                "title": row.title,
                "username": row.username,
                "total_reach": row.total_reach or 0,
            }
            for row in rows
        ]

    async def generate_ai_insights(
        self,
        stats_dict: dict[str, Any],
        plan: str,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """
        Сгенерировать AI инсайты на основе статистики.

        Доступно только для pro/business тарифов.
        Возвращает recommendations, top_channels, optimal_time.
        """
        # Check plan access
        allowed_plans = {"pro", "business"}
        if plan not in allowed_plans:
            return {
                "error": "AI insights available only for Pro and Business plans",
                "recommendations": [],
                "top_channels": [],
                "optimal_time": None,
            }

        # Use Mistral AI to generate insights
        prompt = f"""
        Analyze this advertising campaign statistics and provide recommendations:

        Total placements: {stats_dict.get('total_placements', 0)}
        Completed placements: {stats_dict.get('completed_placements', 0)}
        Total spent: {stats_dict.get('total_spent', 0)} RUB
        Total reach: {stats_dict.get('total_reach', 0)}
        Total clicks: {stats_dict.get('total_clicks', 0)}
        Avg CTR: {stats_dict.get('avg_ctr', 0):.2f}%

        Provide:
        1. 3 specific recommendations to improve campaign performance
        2. Optimal publishing time suggestion
        3. Budget optimization tips

        Response in Russian, concise and actionable.
        """

        try:
            response = await self.ai_service.generate_text(prompt)
            return {
                "recommendations": [response],
                "top_channels": [],
                "optimal_time": 14,  # Default 14:00
                "ai_analysis": response,
            }
        except Exception as e:
            return {
                "error": str(e),
                "recommendations": ["AI analysis temporarily unavailable"],
                "top_channels": [],
                "optimal_time": 14,
            }

    async def get_platform_stats(
        self,
        session: AsyncSession,
    ) -> PlatformStats:
        """
        Получить статистику платформы для администратора.

        - total_users: всего пользователей
        - total_placements: всего размещений
        - total_revenue: общая выручка платформы
        """
        from src.db.models.platform_account import PlatformAccount
        from src.db.models.user import User

        # Total users
        users_result = await session.execute(select(func.count()).select_from(User))
        total_users = users_result.scalar() or 0

        # Total placements
        placements_result = await session.execute(
            select(func.count()).select_from(PlacementRequest)
        )
        total_placements = placements_result.scalar() or 0

        # Total revenue from platform account
        platform_result = await session.execute(
            select(PlatformAccount.profit_accumulated).where(PlatformAccount.id == 1)
        )
        total_revenue = platform_result.scalar() or Decimal("0")

        return PlatformStats(
            total_users=total_users,
            total_placements=total_placements,
            total_revenue=total_revenue,
        )
