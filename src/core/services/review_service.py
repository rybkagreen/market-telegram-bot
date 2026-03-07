"""
Review Service — сервис для управления отзывами.
Спринт 2 — двусторонняя система оценки рекламодатель ↔ владелец.
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.db.models.mailing_log import MailingLog, MailingStatus
from src.db.models.review import Review, ReviewerRole
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


@dataclass
class ReviewCreateData:
    """Данные для создания отзыва."""

    reviewer_id: int
    placement_id: int
    reviewer_role: ReviewerRole

    # Оценки рекламодателя → каналу
    score_compliance: int | None = None
    score_audience: int | None = None
    score_speed: int | None = None

    # Оценки владельца → рекламодателю
    score_material: int | None = None
    score_requirements: int | None = None
    score_payment: int | None = None

    comment: str | None = None


class ReviewService:
    """
    Сервис для управления отзывами.

    Методы:
        create_review: Создать отзыв
        get_channel_rating: Получить средний рейтинг канала
        get_user_rating: Получить рейтинг пользователя
        check_duplicate_fraud: Проверка на дубликат/фрод
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def create_review(self, data: ReviewCreateData) -> Review:
        """
        Создать отзыв о размещении.

        Args:
            data: Данные отзыва.

        Returns:
            Созданный отзыв.

        Raises:
            ValueError: Если размещение не завершено или отзыв уже есть.
        """

        async with async_session_factory() as session:
            # Проверяем что размещение существует и завершено
            placement = await session.get(MailingLog, data.placement_id)
            if not placement:
                raise ValueError(f"Placement {data.placement_id} not found")

            if placement.status not in (MailingStatus.SENT,):
                raise ValueError(
                    f"Cannot review placement {data.placement_id}: "
                    f"status={placement.status.value}"
                )

            # Проверяем что отзыв ещё не создан
            existing = await session.get(Review, data.placement_id)
            if existing:
                raise ValueError(f"Review already exists for placement {data.placement_id}")

            # Определяем reviewee (кого оцениваем)
            if data.reviewer_role == ReviewerRole.ADVERTISER:
                # Рекламодатель оценивает владельца канала
                from src.db.models.analytics import TelegramChat

                channel = await session.get(TelegramChat, placement.chat_id)
                if not channel or not channel.owner_user_id:
                    raise ValueError("Channel owner not found")
                reviewee_id = channel.owner_user_id
            else:
                # Владелец оценивает рекламодателя
                from src.db.models.campaign import Campaign

                campaign = await session.get(Campaign, placement.campaign_id)
                if not campaign:
                    raise ValueError("Campaign not found")
                reviewee_id = campaign.user_id

            # Создаём отзыв
            review = Review(
                reviewer_id=data.reviewer_id,
                reviewee_id=reviewee_id,
                channel_id=placement.chat_id,
                placement_id=data.placement_id,
                reviewer_role=data.reviewer_role,
                score_compliance=data.score_compliance,
                score_audience=data.score_audience,
                score_speed=data.score_speed,
                score_material=data.score_material,
                score_requirements=data.score_requirements,
                score_payment=data.score_payment,
                comment=data.comment,
                is_hidden=False,
            )

            session.add(review)
            await session.flush()
            await session.refresh(review)

            logger.info(
                f"Created review {review.id}: "
                f"reviewer={data.reviewer_id}, placement={data.placement_id}"
            )

            return review

    async def get_channel_rating(self, channel_id: int) -> dict[str, Any]:
        """
        Получить средний рейтинг канала.

        Args:
            channel_id: ID канала.

        Returns:
            dict с average_score, total_reviews, score_breakdown.
        """
        from sqlalchemy import func, select

        async with async_session_factory() as session:
            # Средний балл по отзывам от рекламодателей
            stmt = (
                select(
                    func.avg(Review.score_compliance).label("avg_compliance"),
                    func.avg(Review.score_audience).label("avg_audience"),
                    func.avg(Review.score_speed).label("avg_speed"),
                    func.count(Review.id).label("total_reviews"),
                )
                .where(
                    Review.channel_id == channel_id,
                    Review.reviewer_role == ReviewerRole.ADVERTISER,
                    Review.is_hidden == False,  # noqa: E712
                )
            )
            result = await session.execute(stmt)
            row = result.one()

            avg_compliance = float(row.avg_compliance or 0)
            avg_audience = float(row.avg_audience or 0)
            avg_speed = float(row.avg_speed or 0)
            total_reviews = row.total_reviews or 0

            # Общий средний балл
            overall_avg = (avg_compliance + avg_audience + avg_speed) / 3 if avg_compliance or avg_audience or avg_speed else 0

            return {
                "channel_id": channel_id,
                "average_score": round(overall_avg, 2),
                "total_reviews": total_reviews,
                "score_breakdown": {
                    "compliance": round(avg_compliance, 2),
                    "audience": round(avg_audience, 2),
                    "speed": round(avg_speed, 2),
                },
            }

    async def get_user_rating(self, user_id: int) -> dict[str, Any]:
        """
        Получить рейтинг пользователя (полученные отзывы).

        Args:
            user_id: ID пользователя.

        Returns:
            dict с average_score, total_reviews, score_breakdown.
        """
        from sqlalchemy import func, select

        async with async_session_factory() as session:
            # Отзывы где пользователь — reviewee
            stmt = (
                select(
                    func.avg(Review.score_material).label("avg_material"),
                    func.avg(Review.score_requirements).label("avg_requirements"),
                    func.avg(Review.score_payment).label("avg_payment"),
                    func.count(Review.id).label("total_reviews"),
                )
                .where(
                    Review.reviewee_id == user_id,
                    Review.reviewer_role == ReviewerRole.OWNER,
                    Review.is_hidden == False,  # noqa: E712
                )
            )
            result = await session.execute(stmt)
            row = result.one()

            avg_material = float(row.avg_material or 0)
            avg_requirements = float(row.avg_requirements or 0)
            avg_payment = float(row.avg_payment or 0)
            total_reviews = row.total_reviews or 0

            overall_avg = (avg_material + avg_requirements + avg_payment) / 3 if avg_material or avg_requirements or avg_payment else 0

            return {
                "user_id": user_id,
                "average_score": round(overall_avg, 2),
                "total_reviews": total_reviews,
                "score_breakdown": {
                    "material": round(avg_material, 2),
                    "requirements": round(avg_requirements, 2),
                    "payment": round(avg_payment, 2),
                },
            }

    async def check_duplicate_fraud(self, reviewer_id: int, placement_id: int) -> bool:
        """
        Проверить на дубликат отзыва (антифрод).

        Args:
            reviewer_id: ID рецензента.
            placement_id: ID размещения.

        Returns:
            True если дубликат найден.
        """
        from sqlalchemy import select

        async with async_session_factory() as session:
            stmt = select(Review.id).where(
                Review.reviewer_id == reviewer_id,
                Review.placement_id == placement_id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            return existing is not None


# Глобальный экземпляр
review_service = ReviewService()
