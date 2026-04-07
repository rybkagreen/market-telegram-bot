"""AnalyticsService for campaign and user statistics aggregation."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.payments import OWNER_SHARE
from src.core.services.mistral_ai_service import MistralAIService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.session import async_session_factory


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
    """Сервис агрегации статистики кампаний и пользователей. Интегрирует AI инсайты."""

    def __init__(self) -> None:
        self.ai_service = MistralAIService()

    async def get_advertiser_stats(
        self, advertiser_id: int, session: AsyncSession
    ) -> AdvertiserStats:
        """Получить статистику рекламодателя."""
        total_result = await session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(PlacementRequest.advertiser_id == advertiser_id)
        )
        total_placements = total_result.scalar() or 0

        completed_result = await session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        completed_placements = completed_result.scalar() or 0

        spent_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
                Transaction.user_id == advertiser_id,
                Transaction.type == TransactionType.escrow_release,
            )
        )
        total_spent = spent_result.scalar() or Decimal("0")

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
        avg_ctr = (total_clicks / total_reach * 100) if total_reach > 0 else 0.0

        return AdvertiserStats(
            total_placements=total_placements,
            completed_placements=completed_placements,
            total_spent=total_spent,
            total_reach=total_reach,
            total_clicks=total_clicks,
            avg_ctr=avg_ctr,
        )

    async def get_owner_stats(self, owner_id: int, session: AsyncSession) -> OwnerStats:
        """Получить статистику владельца канала."""
        published_result = await session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.owner_id == owner_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        total_published = published_result.scalar() or 0

        earned_result = await session.execute(
            select(
                func.coalesce(func.sum(PlacementRequest.final_price * OWNER_SHARE), Decimal("0"))
            ).where(
                PlacementRequest.owner_id == owner_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.final_price.isnot(None),
            )
        )
        total_earned = earned_result.scalar() or Decimal("0")
        avg_check = (total_earned / total_published) if total_published > 0 else Decimal("0")

        return OwnerStats(
            total_published=total_published,
            total_earned=total_earned,
            avg_check=avg_check,
        )

    async def get_top_channels_by_reach(
        self, advertiser_id: int, session: AsyncSession, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Топ каналов по published_reach для рекламодателя."""
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
        self, stats_dict: dict[str, Any], plan: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Сгенерировать AI инсайты на основе статистики. Доступно только для pro/business."""
        allowed_plans = {"pro", "business"}
        if plan not in allowed_plans:
            return {
                "error": "AI insights available only for Pro and Business plans",
                "recommendations": [],
                "top_channels": [],
                "optimal_time": None,
            }

        prompt = f"Analyze advertising stats: placements={stats_dict.get('total_placements', 0)}, completed={stats_dict.get('completed_placements', 0)}, spent={stats_dict.get('total_spent', 0)}, reach={stats_dict.get('total_reach', 0)}, ctr={stats_dict.get('avg_ctr', 0):.2f}%. Provide 3 recommendations in Russian."

        try:
            response = await self.ai_service.generate(prompt)
            return {
                "recommendations": [response],
                "top_channels": [],
                "optimal_time": 14,
                "ai_analysis": response,
            }
        except Exception as e:
            return {
                "error": str(e),
                "recommendations": ["AI analysis temporarily unavailable"],
                "top_channels": [],
                "optimal_time": 14,
            }

    async def get_platform_stats(self, session: AsyncSession) -> PlatformStats:
        """Получить статистику платформы для администратора."""
        from src.db.models.platform_account import PlatformAccount
        from src.db.models.user import User

        users_result = await session.execute(select(func.count()).select_from(User))
        total_users = users_result.scalar() or 0

        placements_result = await session.execute(
            select(func.count()).select_from(PlacementRequest)
        )
        total_placements = placements_result.scalar() or 0

        platform_result = await session.execute(
            select(PlatformAccount.profit_accumulated).where(PlatformAccount.id == 1)
        )
        total_revenue = platform_result.scalar() or Decimal("0")

        return PlatformStats(
            total_users=total_users, total_placements=total_placements, total_revenue=total_revenue
        )

    async def get_public_stats(self) -> PlatformStats:
        """Получить публичную статистику платформы (без сессии)."""
        from decimal import Decimal

        from sqlalchemy import func, select

        from src.db.models.placement_request import PlacementRequest
        from src.db.models.platform_account import PlatformAccount
        from src.db.models.telegram_chat import TelegramChat

        async with async_session_factory() as session:
            try:
                # Total users
                users_result = await session.execute(
                    select(func.count())
                    .select_from(TelegramChat)
                    .where(TelegramChat.is_active.is_(True))
                )
                total_users = users_result.scalar() or 0

                # Total reach (sum of member_count)
                await session.execute(
                    select(func.sum(TelegramChat.member_count)).where(
                        TelegramChat.is_active.is_(True)
                    )
                )

                # Total placements
                placements_result = await session.execute(
                    select(func.count()).select_from(PlacementRequest)
                )
                total_placements = placements_result.scalar() or 0

                # Total revenue
                platform_result = await session.execute(
                    select(PlatformAccount.profit_accumulated).where(PlatformAccount.id == 1)
                )
                total_revenue = platform_result.scalar() or Decimal("0")

                return PlatformStats(
                    total_users=total_users,
                    total_placements=total_placements,
                    total_revenue=total_revenue,
                )
            except Exception:
                # Return default zeros if any error
                return PlatformStats(
                    total_users=0,
                    total_placements=0,
                    total_revenue=Decimal("0"),
                )
