"""
Analytics Service для сбора и анализа статистики кампаний.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import redis.asyncio as redis

from src.config.settings import settings
from src.db.repositories.log_repo import MailingLogRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL = 300  # 5 минут


@dataclass
class CampaignStats:
    """Статистика кампании."""

    total_sent: int
    total_failed: int
    total_skipped: int
    total_pending: int
    success_rate: float
    total_cost: Decimal
    reach_estimate: int


@dataclass
class UserAnalytics:
    """Сводная аналитика пользователя."""

    total_campaigns: int
    active_campaigns: int
    completed_campaigns: int
    total_spent: Decimal
    avg_success_rate: float
    total_chats_reached: int


@dataclass
class ChatPerformance:
    """Статистика эффективности чата."""

    chat_telegram_id: int
    chat_title: str
    total_sent: int
    success_rate: float
    avg_rating: float


@dataclass
class PlatformStats:
    """Публичная статистика платформы (Спринт 0)."""

    active_channels: int  # Количество активных каналов (bot_is_admin=True, is_accepting_ads=True)
    total_reach: int  # Суммарный охват (сумма member_count)
    campaigns_launched: int  # Всего запущено кампаний
    campaigns_completed: int  # Всего завершено успешно
    avg_channel_rating: float  # Средний рейтинг каналов
    total_payouts: Decimal  # Суммарно выплачено владельцам (пока 0)


class AnalyticsService:
    """
    Сервис аналитики и статистики.

    Методы:
        get_campaign_stats: Получить статистику кампании
        get_user_summary: Получить сводку пользователя
        get_top_performing_chats: Лучшие чаты
        compare_campaigns: Сравнить кампании
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self._redis: redis.Redis | None = None

    @property
    async def redis_client(self) -> redis.Redis:
        """Ленивая инициализация Redis клиента."""
        if self._redis is None:
            self._redis = redis.from_url(
                str(settings.redis_url),
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _get_cache_key(self, key: str) -> str:
        """
        Получить ключ кэша.

        Args:
            key: Имя ключа.

        Returns:
            Ключ в формате analytics:{key}.
        """
        return f"analytics:{key}"

    async def _check_cache(self, key: str) -> dict[str, Any] | None:
        """
        Проверить кэш.

        Args:
            key: Ключ кэша.

        Returns:
            Данные из кэша или None.
        """
        try:
            redis_client = await self.redis_client
            data = await redis_client.get(key)
            if data:
                import json

                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def _set_cache(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int = DEFAULT_CACHE_TTL,
    ) -> None:
        """
        Сохранить в кэш.

        Args:
            key: Ключ кэша.
            value: Значение.
            ttl: Время жизни в секундах.
        """
        try:
            redis_client = await self.redis_client
            import json

            await redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def get_campaign_stats(self, campaign_id: int) -> CampaignStats | None:
        """
        Получить статистику кампании.

        Args:
            campaign_id: ID кампании.

        Returns:
            CampaignStats или None.
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(f"campaign:{campaign_id}")
        cached = await self._check_cache(cache_key)
        if cached:
            logger.info(f"Cache hit for campaign {campaign_id}")
            return CampaignStats(**cached)

        async with async_session_factory() as session:
            log_repo = MailingLogRepository(session)

            # Получаем статистику кампании
            stats = await log_repo.get_stats_by_campaign(campaign_id)

            if not stats:
                return None

            total = stats.get("total", 0)
            sent = stats.get("sent", 0)
            failed = stats.get("failed", 0)
            skipped = stats.get("skipped", 0)
            pending = stats.get("pending", 0)
            total_cost = Decimal(str(stats.get("total_cost", 0)))

            success_rate = (sent / total * 100) if total > 0 else 0.0

            # Оценка охвата (сумма member_count чатов)
            reach_estimate = stats.get("reach_estimate", 0)

            result = CampaignStats(
                total_sent=sent,
                total_failed=failed,
                total_skipped=skipped,
                total_pending=pending,
                success_rate=success_rate,
                total_cost=total_cost,
                reach_estimate=reach_estimate,
            )

            # Кэширование
            await self._set_cache(
                cache_key,
                {
                    "total_sent": sent,
                    "total_failed": failed,
                    "total_skipped": skipped,
                    "total_pending": pending,
                    "success_rate": success_rate,
                    "total_cost": str(total_cost),
                    "reach_estimate": reach_estimate,
                },
            )

            return result

    async def get_user_summary(
        self,
        user_id: int,
        days: int = 30,
    ) -> UserAnalytics | None:
        """
        Получить сводную аналитику пользователя.

        Args:
            user_id: ID пользователя.
            days: Период в днях.

        Returns:
            UserAnalytics или None.
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(f"user:{user_id}:days:{days}")
        cached = await self._check_cache(cache_key)
        if cached:
            logger.info(f"Cache hit for user {user_id}")
            return UserAnalytics(**cached)

        async with async_session_factory() as session:
            from src.db.repositories.log_repo import MailingLogRepository
            from src.db.repositories.user_repo import UserRepository

            user_repo = UserRepository(session)
            log_repo = MailingLogRepository(session)

            # Получаем пользователя
            user = await user_repo.get_by_id(user_id)
            if not user:
                return None

            # Получаем статистику из БД
            user_stats = await user_repo.get_with_stats(user_id)

            total_campaigns = user_stats.get("total_campaigns", 0)
            active_campaigns = user_stats.get("active_campaigns", 0)
            completed_campaigns = user_stats.get("completed_campaigns", 0)
            total_spent = user_stats.get("total_spent", Decimal("0"))
            match total_spent:
                case int() | float():
                    total_spent = Decimal(str(total_spent))
                case str():
                    total_spent = Decimal(total_spent)

            # Рассчитываем средний success rate через репозиторий
            avg_success_rate = await log_repo.get_user_success_rate(user_id, days=days)

            # Общее количество достигнутых чатов
            total_chats_reached = await log_repo.get_total_chats_reached(user_id, days=days)

            result = UserAnalytics(
                total_campaigns=total_campaigns,
                active_campaigns=active_campaigns,
                completed_campaigns=completed_campaigns,
                total_spent=total_spent,
                avg_success_rate=avg_success_rate,
                total_chats_reached=total_chats_reached,
            )

            # Кэширование
            await self._set_cache(
                cache_key,
                {
                    "total_campaigns": total_campaigns,
                    "active_campaigns": active_campaigns,
                    "completed_campaigns": completed_campaigns,
                    "total_spent": str(total_spent),
                    "avg_success_rate": avg_success_rate,
                    "total_chats_reached": total_chats_reached,
                },
            )

            return result

    async def get_top_performing_chats(
        self,
        user_id: int,
        limit: int = 10,
    ) -> list[ChatPerformance]:
        """
        Получить лучшие чаты по эффективности.

        Args:
            user_id: ID пользователя.
            limit: Количество чатов.

        Returns:
            Список ChatPerformance.
        """
        async with async_session_factory() as session:
            log_repo = MailingLogRepository(session)

            # Получаем топ чатов по success rate
            top_chats = await log_repo.get_top_chats(user_id=user_id, limit=limit)

            result = []
            for chat_data in top_chats:
                result.append(
                    ChatPerformance(
                        chat_telegram_id=chat_data.get("chat_telegram_id", 0),
                        chat_title=chat_data.get("chat_title", ""),
                        total_sent=chat_data.get("total_sent", 0),
                        success_rate=chat_data.get("success_rate", 0.0),
                        avg_rating=chat_data.get("avg_rating", 0.0),
                    )
                )

            return result

    async def compare_campaigns(
        self,
        campaign_ids: list[int],
    ) -> dict[str, Any]:
        """
        Сравнить несколько кампаний.

        Args:
            campaign_ids: Список ID кампаний.

        Returns:
            Сравнительный отчёт.
        """
        results = []
        for campaign_id in campaign_ids:
            stats = await self.get_campaign_stats(campaign_id)
            if stats:
                results.append(
                    {
                        "campaign_id": campaign_id,
                        "total_sent": stats.total_sent,
                        "total_failed": stats.total_failed,
                        "success_rate": stats.success_rate,
                        "total_cost": float(stats.total_cost),
                        "reach_estimate": stats.reach_estimate,
                    }
                )

        # Вычисляем средние значения
        if results:
            avg_sent = sum(r["total_sent"] for r in results) / len(results)
            avg_success = sum(r["success_rate"] for r in results) / len(results)
            avg_cost = sum(r["total_cost"] for r in results) / len(results)
        else:
            avg_sent = avg_success = avg_cost = 0.0

        return {
            "campaigns": results,
            "summary": {
                "count": len(results),
                "avg_sent": avg_sent,
                "avg_success_rate": avg_success,
                "avg_cost": avg_cost,
            },
        }

    async def get_daily_stats(
        self,
        user_id: int,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Получить ежедневную статистику.

        Args:
            user_id: ID пользователя.
            days: Количество дней.

        Returns:
            Список статистик по дням.
        """
        async with async_session_factory() as session:
            log_repo = MailingLogRepository(session)

            end_date = datetime.now(tz=UTC)
            start_date = end_date - timedelta(days=days)

            daily_stats = await log_repo.get_daily_stats(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )

            return daily_stats

    async def get_platform_stats(self) -> PlatformStats:
        """
        Получить публичную статистику платформы (Спринт 0).

        Returns:
            PlatformStats с метриками платформы.
        """
        from sqlalchemy import func, select

        from src.db.models.analytics import TelegramChat
        from src.db.models.campaign import Campaign, CampaignStatus

        async with async_session_factory() as session:
            # Количество активных каналов (opt-in)
            active_channels_stmt = select(func.count(TelegramChat.id)).where(
                TelegramChat.is_active == True,  # noqa: E712
                TelegramChat.bot_is_admin == True,  # noqa: E712
                TelegramChat.is_accepting_ads == True,  # noqa: E712
            )
            active_channels_result = await session.execute(active_channels_stmt)
            active_channels = active_channels_result.scalar_one() or 0

            # Суммарный охват (сумма member_count)
            total_reach_stmt = select(func.sum(TelegramChat.member_count)).where(
                TelegramChat.is_active == True,  # noqa: E712
                TelegramChat.bot_is_admin == True,  # noqa: E712
                TelegramChat.is_accepting_ads == True,  # noqa: E712
            )
            total_reach_result = await session.execute(total_reach_stmt)
            total_reach = total_reach_result.scalar_one() or 0

            # Всего запущено кампаний
            campaigns_launched_stmt = select(func.count(Campaign.id))
            campaigns_launched_result = await session.execute(campaigns_launched_stmt)
            campaigns_launched = campaigns_launched_result.scalar_one() or 0

            # Всего завершено успешно
            campaigns_completed_stmt = select(func.count(Campaign.id)).where(
                Campaign.status == CampaignStatus.DONE
            )
            campaigns_completed_result = await session.execute(campaigns_completed_stmt)
            campaigns_completed = campaigns_completed_result.scalar_one() or 0

            # Средний рейтинг каналов
            avg_rating_stmt = select(func.avg(TelegramChat.rating)).where(
                TelegramChat.is_active == True,  # noqa: E712
                TelegramChat.bot_is_admin == True,  # noqa: E712
                TelegramChat.is_accepting_ads == True,  # noqa: E712
            )
            avg_rating_result = await session.execute(avg_rating_stmt)
            avg_channel_rating = avg_rating_result.scalar_one() or 0.0

            # Суммарно выплачено (пока 0, т.к. модель Payout будет в Спринте 1)
            total_payouts = Decimal("0.00")

            return PlatformStats(
                active_channels=active_channels,
                total_reach=total_reach,
                campaigns_launched=campaigns_launched,
                campaigns_completed=campaigns_completed,
                avg_channel_rating=round(avg_channel_rating, 2),
                total_payouts=total_payouts,
            )


# Глобальный экземпляр
analytics_service = AnalyticsService()
