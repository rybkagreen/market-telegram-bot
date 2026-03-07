"""
Badge Service — сервис для управления выдачей значков.
Спринт 4 — геймификация и удержание пользователей.

PRD §9.2: значки за действия — Первый запуск, 100 размещений, Идеальный CTR и т.д.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class BadgeService:
    """
    Сервис для управления выдачей значков.

    Методы:
        check_and_award_badges: Проверить и выдать значки
        award_badge: Выдать конкретный значок
        get_user_badges: Получить значки пользователя
        get_available_badges: Получить доступные значки
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def check_and_award_badges(self, user_id: int) -> list[dict[str, Any]]:
        """
        Проверить условия и выдать все доступные значки.

        Args:
            user_id: ID пользователя.

        Returns:
            Список выданных значков.
        """
        from sqlalchemy import select

        from src.db.models.badge import Badge, UserBadge
        from src.db.models.user import User

        awarded_badges = []

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return []

            # Получаем все значки
            stmt = select(Badge)
            result = await session.execute(stmt)
            badges = list(result.scalars().all())

            # Получаем уже выданные значки
            user_badge_stmt = select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
            user_badge_result = await session.execute(user_badge_stmt)
            earned_badge_ids = {row[0] for row in user_badge_result.all()}

            # Проверяем каждый значок
            for badge in badges:
                if badge.id in earned_badge_ids:
                    continue  # Уже получен

                if await self._check_badge_condition(session, user, badge):
                    # Выдаём значок
                    await self._award_badge_internal(session, user_id, badge.id)
                    awarded_badges.append(
                        {
                            "badge_id": badge.id,
                            "code": badge.code,
                            "name": badge.name,
                            "icon_emoji": badge.icon_emoji,
                            "xp_reward": badge.xp_reward,
                        }
                    )

            await session.commit()

        return awarded_badges

    async def _check_badge_condition(
        self,
        session,
        user,
        badge,
    ) -> bool:
        """
        Проверить условие получения значка.

        Args:
            session: DB session.
            user: Объект пользователя.
            badge: Объект значка.

        Returns:
            True если условие выполнено.
        """
        from src.db.models.badge import BadgeConditionType

        condition = badge.condition_type
        value = badge.condition_value

        if condition == BadgeConditionType.MANUAL:
            return False  # Только вручную

        if condition == BadgeConditionType.STREAK_DAYS:
            return (user.streak_days or 0) >= value

        if condition == BadgeConditionType.SPEND_AMOUNT:
            return float(user.total_spent or 0) >= value

        if condition == BadgeConditionType.EARNED_AMOUNT:
            return float(user.total_earned or 0) >= value

        # Для остальных условий нужны дополнительные запросы
        # (campaigns_count, placements_count, review_count)
        # В упрощённой версии возвращаем False
        return False

    async def _award_badge_internal(
        self,
        session,
        user_id: int,
        badge_id: int,
    ) -> None:
        """
        Внутренний метод выдачи значка.

        Args:
            session: DB session.
            user_id: ID пользователя.
            badge_id: ID значка.
        """
        from src.db.models.badge import UserBadge

        user_badge = UserBadge(
            user_id=user_id,
            badge_id=badge_id,
            earned_at=datetime.now(UTC),
        )
        session.add(user_badge)

        # Добавляем XP за значок
        from src.db.models.badge import Badge
        from src.db.models.user import User

        badge = await session.get(Badge, badge_id)
        if badge and badge.xp_reward > 0:
            user = await session.get(User, user_id)
            if user:
                user.xp_points += badge.xp_reward

        logger.info(f"Awarded badge {badge_id} to user {user_id}")

    async def award_badge(
        self,
        user_id: int,
        badge_code: str,
    ) -> dict[str, Any]:
        """
        Выдать конкретный значок по коду.

        Args:
            user_id: ID пользователя.
            badge_code: Код значка.

        Returns:
            dict с результатом выдачи.
        """
        from sqlalchemy import select

        from src.db.models.badge import Badge, UserBadge

        async with async_session_factory() as session:
            # Находим значок по коду
            stmt = select(Badge).where(Badge.code == badge_code)
            result = await session.execute(stmt)
            badge = result.scalar_one_or_none()

            if not badge:
                return {"error": f"Badge '{badge_code}' not found"}

            # Проверяем не получен ли уже
            existing = await session.get(UserBadge, (user_id, badge.id))
            if existing:
                return {"already_earned": True, "badge_code": badge_code}

            # Выдаём значок
            await self._award_badge_internal(session, user_id, badge.id)
            await session.commit()

            return {
                "success": True,
                "badge_id": badge.id,
                "badge_code": badge.code,
                "badge_name": badge.name,
                "xp_reward": badge.xp_reward,
            }

    async def get_user_badges(self, user_id: int) -> list[dict[str, Any]]:
        """
        Получить все значки пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Список значков.
        """
        from sqlalchemy import select

        from src.db.models.badge import Badge, UserBadge

        async with async_session_factory() as session:
            stmt = (
                select(UserBadge, Badge)
                .join(Badge, UserBadge.badge_id == Badge.id)
                .where(UserBadge.user_id == user_id)
                .order_by(UserBadge.earned_at.desc())
            )
            result = await session.execute(stmt)
            rows = result.all()

            return [
                {
                    "badge_id": row.Badge.id,
                    "code": row.Badge.code,
                    "name": row.Badge.name,
                    "description": row.Badge.description,
                    "icon_emoji": row.Badge.icon_emoji,
                    "xp_reward": row.Badge.xp_reward,
                    "category": row.Badge.category,
                    "earned_at": row.UserBadge.earned_at.isoformat(),
                }
                for row in rows
            ]

    async def get_available_badges(self, user_id: int) -> list[dict[str, Any]]:
        """
        Получить доступные значки (которые ещё не получены).

        Args:
            user_id: ID пользователя.

        Returns:
            Список доступных значков.
        """
        from sqlalchemy import select

        from src.db.models.badge import Badge, UserBadge

        async with async_session_factory() as session:
            # Получаем все значки
            all_badges_stmt = select(Badge)
            result = await session.execute(all_badges_stmt)
            all_badges = list(result.scalars().all())

            # Получаем полученные значки
            earned_stmt = select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
            earned_result = await session.execute(earned_stmt)
            earned_ids = {row[0] for row in earned_result.all()}

            # Возвращаем не полученные
            return [
                {
                    "badge_id": badge.id,
                    "code": badge.code,
                    "name": badge.name,
                    "description": badge.description,
                    "icon_emoji": badge.icon_emoji,
                    "xp_reward": badge.xp_reward,
                    "category": badge.category,
                    "condition_type": badge.condition_type,
                    "condition_value": badge.condition_value,
                }
                for badge in all_badges
                if badge.id not in earned_ids
            ]


# Глобальный экземпляр
badge_service = BadgeService()
