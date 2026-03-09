"""
Comparison Service — сервис для сравнения каналов.
Спринт 10 — сравнение каналов для рекламодателей.
"""

import logging
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class ComparisonService:
    """Сервис для сравнения каналов."""

    async def get_channels_for_comparison(
        self,
        channel_ids: list[int],
    ) -> list[dict[str, Any]]:
        """
        Получить данные каналов для сравнения.

        Args:
            channel_ids: Список ID каналов.

        Returns:
            Список словарей с данными каналов.
        """
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat

        async with async_session_factory() as session:
            stmt = select(TelegramChat).where(TelegramChat.id.in_(channel_ids))
            result = await session.execute(stmt)
            channels = list(result.scalars().all())

            # Сортируем в порядке ID как передано
            channel_map = {ch.id: ch for ch in channels}
            return [
                self._channel_to_dict(channel_map[cid]) for cid in channel_ids if cid in channel_map
            ]

    def _channel_to_dict(self, channel) -> dict[str, Any]:
        """Конвертировать канал в словарь."""
        return {
            "id": channel.id,
            "username": channel.username,
            "title": channel.title,
            "member_count": channel.member_count or 0,
            "avg_views": channel.last_avg_views or 0,
            "er": channel.last_er or 0.0,
            "post_frequency": channel.last_post_frequency or 0.0,
            "rating": channel.rating or 0.0,
            "price_per_post": float(channel.price_per_post) if channel.price_per_post else 0,
            "topic": channel.topic,
        }

    def calculate_comparison_metrics(
        self,
        channels_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Рассчитать дополнительные метрики для сравнения.

        Args:
            channels_data: Данные каналов.

        Returns:
            dict с рассчитанными метриками.
        """
        if not channels_data:
            return {"channels": [], "best_values": {}, "recommendation": {}}

        # Цена за 1000 подписчиков (CPM)
        for ch in channels_data:
            if ch["member_count"] > 0:
                ch["price_per_1k_subscribers"] = round(
                    ch["price_per_post"] / (ch["member_count"] / 1000), 2
                )
            else:
                ch["price_per_1k_subscribers"] = 0

        # Найти лучшие значения по каждой метрике
        metrics_higher_better = ["member_count", "avg_views", "er", "post_frequency", "rating"]
        metrics_lower_better = ["price_per_post", "price_per_1k_subscribers"]

        best_values = {}

        for metric in metrics_higher_better:
            values = [ch.get(metric, 0) for ch in channels_data]
            best_values[metric] = max(values) if values else 0

        for metric in metrics_lower_better:
            values = [ch.get(metric, 0) for ch in channels_data if ch.get(metric, 0) > 0]
            best_values[metric] = min(values) if values else 0

        # Пометить лучшие значения
        for ch in channels_data:
            ch["is_best"] = {}
            for metric in metrics_higher_better:
                ch["is_best"][metric] = ch.get(metric, 0) == best_values.get(metric, 0)
            for metric in metrics_lower_better:
                if ch.get(metric, 0) > 0:
                    ch["is_best"][metric] = ch.get(metric, 0) == best_values.get(metric, 0)
                else:
                    ch["is_best"][metric] = False

        # Рекомендация
        recommendation = self._generate_recommendation(channels_data)

        return {
            "channels": channels_data,
            "best_values": best_values,
            "recommendation": recommendation,
        }

    def _generate_recommendation(
        self,
        channels_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Сгенерировать рекомендацию какой канал лучше.

        Логика:
        - Если важен охват → канал с максимальными avg_views
        - Если важна эффективность → канал с лучшим ER
        - Если важен бюджет → канал с минимальным price_per_1k_subscribers

        Returns:
            dict с рекомендацией.
        """
        if not channels_data:
            return {"channel_id": None, "reason": "", "channel_name": ""}

        # Простая эвристика: лучший по ER (Engagement Rate)
        best_by_er = max(channels_data, key=lambda x: x.get("er", 0))

        # Если ER одинаковый, смотрим на avg_views
        channels_with_best_er = [
            ch for ch in channels_data if ch.get("er", 0) == best_by_er.get("er", 0)
        ]
        if len(channels_with_best_er) > 1:
            best = max(channels_with_best_er, key=lambda x: x.get("avg_views", 0))
        else:
            best = best_by_er

        return {
            "channel_id": best["id"],
            "reason": "Лучший Engagement Rate",
            "channel_name": best.get("title") or best.get("username") or f"Канал {best['id']}",
        }

    def format_metric_with_indicator(
        self,
        value: float,
        best_value: float,
        metric_type: str = "higher_better",
    ) -> str:
        """
        Форматировать метрику с индикатором.

        Args:
            value: Значение метрики.
            best_value: Лучшее значение среди всех.
            metric_type: "higher_better" или "lower_better".

        Returns:
            Строка с индикатором.
        """
        if best_value == 0:
            return f"{value:.1f}"

        if metric_type == "higher_better":
            if value == best_value:
                return f"✅ {value:.1f}"
            elif value >= best_value * 0.8:
                return f"🟢 {value:.1f}"  # 80%+ от лучшего
            elif value >= best_value * 0.5:
                return f"🟡 {value:.1f}"  # 50-80% от лучшего
            else:
                return f"🔴 {value:.1f}"  # < 50% от лучшего
        else:
            # lower_better (например, цена)
            if value == best_value:
                return f"✅ {value:.1f}"
            elif value <= best_value * 1.2:
                return f"🟢 {value:.1f}"
            elif value <= best_value * 1.5:
                return f"🟡 {value:.1f}"
            else:
                return f"🔴 {value:.1f}"


# Глобальный экземпляр
comparison_service = ComparisonService()
