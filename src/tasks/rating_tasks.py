"""
Rating Celery tasks для пересчёта рейтингов каналов.
"""

import asyncio
import logging
from datetime import date
from typing import Any

from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="rating:recalculate_ratings_daily")
def recalculate_ratings_daily(self) -> dict[str, Any]:
    """
    Ежедневный пересчёт рейтингов всех каналов.
    Запускается в 04:00 UTC через Celery Beat.

    Returns:
        Статистика пересчёта.
    """
    logger.info("Starting daily ratings recalculation")

    async def _recalculate_async() -> dict[str, Any]:
        from sqlalchemy import select

        from src.core.services.rating_service import rating_service
        from src.db.models.analytics import TelegramChat
        from src.db.models.channel_rating import ChannelRating

        stats = {
            "total_channels": 0,
            "processed": 0,
            "errors": 0,
            "fraud_detected": 0,
        }

        async with async_session_factory() as session:
            # Получаем все активные каналы
            stmt = select(TelegramChat).where(
                TelegramChat.is_active == True,  # noqa: E712
            )
            result = await session.execute(stmt)
            channels = list(result.scalars().all())

            stats["total_channels"] = len(channels)
            calculation_date = date.today()

            for channel in channels:
                try:
                    # Рассчитываем рейтинг
                    score_data = await rating_service.calculate_channel_score(
                        channel.id, calculation_date
                    )

                    if "error" in score_data:
                        stats["errors"] += 1
                        continue

                    # Проверяем на накрутку
                    fraud_data = await rating_service.detect_fraud(channel.id)

                    # Создаём или обновляем запись рейтинга
                    existing_stmt = select(ChannelRating).where(
                        ChannelRating.channel_id == channel.id,
                        ChannelRating.date == calculation_date,
                    )
                    result = await session.execute(existing_stmt)
                    existing_rating = result.scalar_one_or_none()

                    if existing_rating:
                        # Обновляем
                        existing_rating.subscribers = score_data["subscribers"]  # type: ignore
                        existing_rating.avg_views = score_data["avg_views"]  # type: ignore
                        existing_rating.er = score_data["er"]  # type: ignore
                        existing_rating.reach_score = score_data["reach_score"]  # type: ignore
                        existing_rating.er_score = score_data["er_score"]  # type: ignore
                        existing_rating.growth_score = score_data["growth_score"]  # type: ignore
                        existing_rating.frequency_score = score_data["frequency_score"]  # type: ignore
                        existing_rating.reliability_score = score_data["reliability_score"]  # type: ignore
                        existing_rating.age_score = score_data["age_score"]  # type: ignore
                        existing_rating.total_score = score_data["total_score"]  # type: ignore
                        existing_rating.fraud_flag = fraud_data.get("fraud_flag", False)  # type: ignore
                    else:
                        # Создаём новую
                        rating = ChannelRating(
                            channel_id=channel.id,
                            date=calculation_date,
                            subscribers=score_data["subscribers"],
                            avg_views=score_data["avg_views"],
                            er=score_data["er"],
                            reach_score=score_data["reach_score"],
                            er_score=score_data["er_score"],
                            growth_score=score_data["growth_score"],
                            frequency_score=score_data["frequency_score"],
                            reliability_score=score_data["reliability_score"],  # type: ignore
                            age_score=score_data["age_score"],  # type: ignore
                            total_score=score_data["total_score"],  # type: ignore
                            fraud_flag=fraud_data.get("fraud_flag", False),
                        )
                        session.add(rating)

                    if fraud_data.get("fraud_flag", False):
                        stats["fraud_detected"] += 1
                        logger.warning(
                            f"Fraud detected for channel {channel.id}: "
                            f"{fraud_data.get('fraud_reasons', [])}"
                        )

                    stats["processed"] += 1

                except Exception as e:
                    logger.error(f"Error processing channel {channel.id}: {e}")
                    stats["errors"] += 1

            await session.commit()

        return stats

    try:
        return asyncio.run(_recalculate_async())
    except Exception as e:
        logger.error(f"recalculate_ratings_daily failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True, base=BaseTask, name="rating:update_weekly_toplists")
def update_weekly_toplists(self) -> dict[str, Any]:
    """
    Обновление еженедельных топов каналов.
    Запускается каждый понедельник в 05:00 UTC.

    Returns:
        Статистика обновления.
    """
    logger.info("Starting weekly toplists update")

    async def _update_async() -> dict[str, Any]:
        from sqlalchemy import select

        from src.core.services.rating_service import rating_service

        stats = {
            "topics_processed": 0,
            "channels_ranked": 0,
        }

        # Получаем список тематик
        topics = [
            "it",
            "business",
            "realestate",
            "crypto",
            "marketing",
            "finance",
            "news",
            "education",
        ]

        async with async_session_factory() as session:
            for topic in topics:
                try:
                    # Получаем топ каналов по тематике
                    top_channels = await rating_service.get_top_channels(
                        topic=topic,
                        limit=100,
                    )

                    # Обновляем rank_in_topic
                    for rank, channel_data in enumerate(top_channels, start=1):
                        channel_id = channel_data["channel_id"]

                        # Находим последний рейтинг
                        stmt = (
                            select(ChannelRating)
                            .where(ChannelRating.channel_id == channel_id)
                            .order_by(ChannelRating.date.desc())
                        )
                        result = await session.execute(stmt)
                        rating = result.scalar_one_or_none()

                        if rating:
                            rating.rank_in_topic = rank
                            stats["channels_ranked"] += 1

                    stats["topics_processed"] += 1

                except Exception as e:
                    logger.error(f"Error processing topic {topic}: {e}")

            await session.commit()

        return stats

    try:
        return asyncio.run(_update_async())
    except Exception as e:
        logger.error(f"update_weekly_toplists failed: {e}")
        return {"status": "error", "error": str(e)}


# Импортируем ChannelRating для корректной работы
from src.db.models.channel_rating import ChannelRating  # noqa: E402
