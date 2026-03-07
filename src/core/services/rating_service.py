"""
Rating Service — сервис для расчёта рейтинга каналов.
Формула из PRD §7.1: 6 компонентов с весами.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class RatingService:
    """
    Сервис для расчёта и управления рейтингами каналов.

    Формула рейтинга (PRD §7.1):
    - reach_score (вес 30%) — охват канала
    - er_score (вес 25%) — engagement rate
    - growth_score (вес 15%) — прирост подписчиков
    - frequency_score (вес 10%) — частота публикаций
    - reliability_score (вес 15%) — надёжность (отзывы)
    - age_score (вес 5%) — возраст канала

    Методы:
        calculate_channel_score: Рассчитать все компоненты рейтинга
        recalculate_all_ratings: Пересчитать рейтинги всех каналов
        get_top_channels: Получить топ каналов по тематике
        get_reliability_stars: Получить звёзды надёжности
    """

    # Веса компонентов (PRD §7.1)
    WEIGHTS = {
        "reach": 0.30,
        "er": 0.25,
        "growth": 0.15,
        "frequency": 0.10,
        "reliability": 0.15,
        "age": 0.05,
    }

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def calculate_channel_score(
        self,
        channel_id: int,
        calculation_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Рассчитать все компоненты рейтинга для канала.

        Args:
            channel_id: ID канала в БД.
            calculation_date: Дата расчёта (по умолчанию сегодня).

        Returns:
            dict со всеми компонентами и total_score.
        """

        from src.db.models.analytics import TelegramChat

        if calculation_date is None:
            calculation_date = date.today()

        async with async_session_factory() as session:
            channel = await session.get(TelegramChat, channel_id)
            if not channel:
                return {"error": "Channel not found"}

            # Считаем все компоненты
            reach_score = self._calculate_reach_score(channel)
            er_score = self._calculate_er_score(channel)
            growth_score = await self._calculate_growth_score(session, channel)
            frequency_score = await self._calculate_frequency_score(session, channel)
            reliability_score = await self._calculate_reliability_score(session, channel)
            age_score = self._calculate_age_score(channel)

            # Итоговый score
            total_score = (
                reach_score * self.WEIGHTS["reach"]
                + er_score * self.WEIGHTS["er"]
                + growth_score * self.WEIGHTS["growth"]
                + frequency_score * self.WEIGHTS["frequency"]
                + reliability_score * self.WEIGHTS["reliability"]
                + age_score * self.WEIGHTS["age"]
            )

            return {
                "channel_id": channel_id,
                "date": calculation_date,
                "subscribers": channel.member_count,
                "avg_views": channel.last_avg_views,
                "er": channel.last_er,
                "reach_score": round(reach_score, 2),
                "er_score": round(er_score, 2),
                "growth_score": round(growth_score, 2),
                "frequency_score": round(frequency_score, 2),
                "reliability_score": round(reliability_score, 2),
                "age_score": round(age_score, 2),
                "total_score": round(total_score, 2),
            }

    def _calculate_reach_score(self, channel) -> float:
        """
        Reach score (0-100, вес 30%).
        Основан на member_count.

        Логика:
        - 0-1000 подписчиков: 0-20 баллов
        - 1000-5000: 20-40
        - 5000-10000: 40-60
        - 10000-50000: 60-80
        - 50000+: 80-100
        """
        subscribers = channel.member_count or 0

        if subscribers <= 1000:
            return min(20, (subscribers / 1000) * 20)
        elif subscribers <= 5000:
            return 20 + min(20, ((subscribers - 1000) / 4000) * 20)
        elif subscribers <= 10000:
            return 40 + min(20, ((subscribers - 5000) / 5000) * 20)
        elif subscribers <= 50000:
            return 60 + min(20, ((subscribers - 10000) / 40000) * 20)
        else:
            return min(100, 80 + ((subscribers - 50000) / 50000) * 20)

    def _calculate_er_score(self, channel) -> float:
        """
        ER score (0-100, вес 25%).
        Основан на last_er (engagement rate).

        Логика:
        - ER < 1%: 0-20 баллов
        - 1-3%: 20-40
        - 3-5%: 40-60
        - 5-10%: 60-80
        - 10%+: 80-100
        """
        er = channel.last_er or 0

        if er < 1:
            return min(20, er * 20)
        elif er < 3:
            return 20 + min(20, ((er - 1) / 2) * 20)
        elif er < 5:
            return 40 + min(20, ((er - 3) / 2) * 20)
        elif er < 10:
            return 60 + min(20, ((er - 5) / 5) * 20)
        else:
            return min(100, 80 + ((er - 10) / 10) * 20)

    async def _calculate_growth_score(
        self,
        session,
        channel,
    ) -> float:
        """
        Growth score (0-100, вес 15%).
        Основан на приросте подписчиков за 7 дней.

        Логика:
        - Прирост > 50%: флаг накрутки (0 баллов)
        - 10-50%: 60-100 баллов
        - 0-10%: 40-60
        - -10-0%: 20-40
        - < -10%: 0-20
        """
        from sqlalchemy import select

        from src.db.models.analytics import ChatSnapshot

        # Получаем снимки за последние 7 дней
        seven_days_ago = date.today() - timedelta(days=7)

        stmt = (
            select(ChatSnapshot)
            .where(
                ChatSnapshot.chat_id == channel.id,
                ChatSnapshot.snapshot_date >= seven_days_ago,
            )
            .order_by(ChatSnapshot.snapshot_date.desc())
        )
        result = await session.execute(stmt)
        snapshots = list(result.scalars().all())

        if len(snapshots) < 2:
            return 50.0  # Нет данных для сравнения

        old_subscribers = snapshots[-1].subscribers
        new_subscribers = snapshots[0].subscribers if snapshots else channel.member_count

        if old_subscribers == 0:
            return 50.0

        growth_rate = ((new_subscribers - old_subscribers) / old_subscribers) * 100

        # Детектор накрутки
        if growth_rate > 50:
            return 0.0

        if growth_rate > 10:
            return min(100, 60 + ((growth_rate - 10) / 40) * 40)
        elif growth_rate > 0:
            return 40 + (growth_rate / 10) * 20
        elif growth_rate > -10:
            return 20 + ((growth_rate + 10) / 10) * 20
        else:
            return max(0, 20 + (growth_rate + 10))

    async def _calculate_frequency_score(
        self,
        session,
        channel,
    ) -> float:
        """
        Frequency score (0-100, вес 10%).
        Основан на частоте публикаций (постов в день).

        Логика:
        - 0 постов: 0 баллов
        - 0-1 пост/день: 0-40
        - 1-3 поста/день: 40-80
        - 3-5 постов/день: 80-100
        - > 5 постов/день: спам, 0 баллов
        """
        frequency = channel.last_post_frequency or 0

        if frequency <= 0:
            return 0.0
        elif frequency <= 1:
            return frequency * 40
        elif frequency <= 3:
            return 40 + ((frequency - 1) / 2) * 40
        elif frequency <= 5:
            return 80 + ((frequency - 3) / 2) * 20
        else:
            return 0.0  # Спам

    async def _calculate_reliability_score(
        self,
        session,
        channel,
    ) -> float:
        """
        Reliability score (0-100, вес 15%).
        Основан на отзывах (Review.score_compliance).

        Логика:
        - Средняя оценка compliance * 20 (макс 100)
        - Если нет отзывов: 50 баллов
        """
        from sqlalchemy import func, select

        from src.db.models.review import Review

        stmt = (
            select(func.avg(Review.score_compliance))
            .where(
                Review.channel_id == channel.id,
                Review.is_hidden == False,  # noqa: E712
            )
        )
        result = await session.execute(stmt)
        avg_compliance = result.scalar_one() or 0

        if avg_compliance == 0:
            return 50.0  # Нет отзывов

        return min(100, avg_compliance * 20)

    def _calculate_age_score(self, channel) -> float:
        """
        Age score (0-100, вес 5%).
        Основан на возрасте канала.

        Логика:
        - < 1 месяца: 0-20
        - 1-3 месяца: 20-40
        - 3-6 месяцев: 40-60
        - 6-12 месяцев: 60-80
        - > 12 месяцев: 80-100
        """
        created_at = channel.created_at

        if not created_at:
            return 50.0  # Нет данных

        age_days = (datetime.now() - created_at).days

        if age_days < 30:
            return min(20, (age_days / 30) * 20)
        elif age_days < 90:
            return 20 + ((age_days - 30) / 60) * 20
        elif age_days < 180:
            return 40 + ((age_days - 90) / 90) * 20
        elif age_days < 365:
            return 60 + ((age_days - 180) / 180) * 20
        else:
            return min(100, 80 + ((age_days - 365) / 365) * 20)

    async def get_top_channels(
        self,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Получить топ каналов по рейтингу.

        Args:
            topic: Тематика для фильтрации.
            limit: Максимальное количество результатов.

        Returns:
            Список каналов с рейтингами.
        """
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat
        from src.db.models.channel_rating import ChannelRating

        async with async_session_factory() as session:
            # Получаем последние рейтинги
            stmt = (
                select(TelegramChat, ChannelRating)
                .join(ChannelRating, ChannelRating.channel_id == TelegramChat.id)
                .where(
                    TelegramChat.is_active == True,  # noqa: E712
                    TelegramChat.is_accepting_ads == True,  # noqa: E712
                    ChannelRating.fraud_flag == False,  # noqa: E712
                )
                .order_by(ChannelRating.total_score.desc())
                .limit(limit)
            )

            if topic:
                stmt = stmt.where(TelegramChat.topic == topic)

            result = await session.execute(stmt)
            rows = result.all()

            return [
                {
                    "channel_id": row.TelegramChat.id,
                    "username": row.TelegramChat.username,
                    "title": row.TelegramChat.title,
                    "total_score": row.ChannelRating.total_score,
                    "reliability_stars": row.ChannelRating.reliability_stars,
                }
                for row in rows
            ]


# Глобальный экземпляр
rating_service = RatingService()
