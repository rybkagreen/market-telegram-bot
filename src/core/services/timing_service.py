"""
Timing Service — сервис для выбора оптимального времени публикации.
Спринт 2 — анализ постов канала для рекомендации времени.
"""

import logging
from datetime import datetime
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class TimingService:
    """
    Сервис для анализа и рекомендации времени публикации.

    Методы:
        suggest_optimal_time: Предложить лучшее время для публикации
        analyze_channel_activity: Анализировать активность канала
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def suggest_optimal_time(
        self,
        channel_id: int,
    ) -> dict[str, Any]:
        """
        Предложить оптимальное время для публикации в канале.

        Анализирует последние посты канала и определяет время
        с наибольшим количеством просмотров.

        Args:
            channel_id: ID канала в БД.

        Returns:
            dict с recommended_time, confidence, analysis.
        """

        from src.db.models.analytics import TelegramChat

        async with async_session_factory() as session:
            channel = await session.get(TelegramChat, channel_id)
            if not channel:
                return {
                    "recommended_time": None,
                    "confidence": 0.0,
                    "analysis": "Channel not found",
                }

            # Если нет recent_posts — возвращаем дефолтную рекомендацию
            if not channel.recent_posts:
                return {
                    "recommended_time": "12:00",  # Дефолт — полдень
                    "confidence": 0.5,
                    "analysis": "No recent posts data, using default",
                }

            # Анализируем время постов (заглушка — в реальности нужен Telethon)
            # В Спринте 2 это базовая реализация
            best_hour = self._analyze_posts_time(channel.recent_posts)  # type: ignore[arg-type]  # TypedDict vs dict compatibility

            recommended_time = f"{best_hour:02d}:00"

            return {
                "recommended_time": recommended_time,
                "confidence": 0.7,  # Средняя уверенность
                "analysis": f"Best hour based on {len(channel.recent_posts)} recent posts",
                "best_hour": best_hour,
            }

    def _analyze_posts_time(self, recent_posts: list[dict]) -> int:
        """
        Проанализировать время постов и найти лучший час.

        Args:
            recent_posts: Список постов с датой и просмотрами.

        Returns:
            Лучший час (0-23).
        """
        if not recent_posts:
            return 12  # Дефолт

        # Считаем просмотры по часам
        hour_views: dict[int, int] = {}
        hour_counts: dict[int, int] = {}

        for post in recent_posts:
            post_date = post.get("date")
            post_views = post.get("views", 0)

            if post_date:
                try:
                    # Парсим дату
                    if isinstance(post_date, str):
                        dt = datetime.fromisoformat(post_date)
                    else:
                        dt = post_date

                    hour = dt.hour
                    hour_views[hour] = hour_views.get(hour, 0) + post_views
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except (ValueError, TypeError):
                    continue

        if not hour_views:
            return 12

        # Находим час с максимальными средними просмотрами
        best_hour = 12
        best_avg_views = 0

        for hour, total_views in hour_views.items():
            count = hour_counts.get(hour, 1)
            avg_views = total_views / count

            if avg_views > best_avg_views:
                best_avg_views = avg_views
                best_hour = hour

        return best_hour

    async def analyze_channel_activity(
        self,
        channel_id: int,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        Проанализировать активность канала за период.

        Args:
            channel_id: ID канала в БД.
            days: Количество дней для анализа.

        Returns:
            dict с post_frequency, best_days, best_hours.
        """

        from src.db.models.analytics import TelegramChat

        async with async_session_factory() as session:
            channel = await session.get(TelegramChat, channel_id)
            if not channel:
                return {
                    "post_frequency": 0,
                    "best_days": [],
                    "best_hours": [],
                }

            recent_posts = channel.recent_posts or []

            # Считаем посты по дням недели
            day_counts: dict[int, int] = {}  # 0=Monday, 6=Sunday
            hour_counts: dict[int, int] = {}

            for post in recent_posts:
                post_date = post.get("date")
                if post_date:
                    try:
                        if isinstance(post_date, str):
                            dt = datetime.fromisoformat(post_date)
                        else:
                            dt = post_date

                        day_counts[dt.weekday()] = day_counts.get(dt.weekday(), 0) + 1
                        hour_counts[dt.hour] = hour_counts.get(dt.hour, 0) + 1
                    except (ValueError, TypeError):
                        continue

            # Находим лучшие дни и часы
            best_days = sorted(day_counts.keys(), key=lambda d: day_counts.get(d, 0), reverse=True)[
                :3
            ]
            best_hours = sorted(
                hour_counts.keys(), key=lambda h: hour_counts.get(h, 0), reverse=True
            )[:3]

            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

            return {
                "post_frequency": len(recent_posts) / max(days, 1),
                "best_days": [day_names[d] for d in best_days],
                "best_hours": [f"{h:02d}:00" for h in best_hours],
                "total_posts_analyzed": len(recent_posts),
            }


# Глобальный экземпляр
timing_service = TimingService()
