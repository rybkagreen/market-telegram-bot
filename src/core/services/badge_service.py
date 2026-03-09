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
        from sqlalchemy import func, select

        from src.db.models.badge import BadgeConditionType
        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog, MailingStatus

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

        # Campaigns count
        if condition == BadgeConditionType.CAMPAIGNS_COUNT:
            stmt = select(func.count(Campaign.id)).where(
                Campaign.user_id == user.id
            )
            count = (await session.execute(stmt)).scalar() or 0
            return count >= value

        # Placements count (для владельцев)
        if condition == BadgeConditionType.PLACEMENTS_COUNT:
            stmt = select(func.count(MailingLog.id)).where(
                MailingLog.chat_id.in_(
                    select(MailingLog.chat_id).where(
                        MailingLog.chat_id.in_(
                            select(func.max(MailingLog.chat_id)).where(
                                MailingLog.status == MailingStatus.SENT
                            )
                        )
                    )
                )
            )
            # Упрощённо: считаем размещения по каналам пользователя
            from src.db.models.analytics import TelegramChat
            stmt = select(func.count(MailingLog.id)).join(
                TelegramChat, MailingLog.chat_id == TelegramChat.id
            ).where(
                TelegramChat.owner_user_id == user.id,
                MailingLog.status == MailingStatus.SENT,
            )
            count = (await session.execute(stmt)).scalar() or 0
            return count >= value

        # Review count
        if condition == BadgeConditionType.REVIEW_COUNT:
            from src.db.models.review import Review
            stmt = select(func.count(Review.id)).where(
                Review.reviewer_id == user.id
            )
            count = (await session.execute(stmt)).scalar() or 0
            return count >= value

        return False

    async def _award_badge_internal(
        self,
        session,
        user_id: int,
        badge_id: int,
    ) -> dict[str, int]:
        """
        Внутренний метод выдачи значка.

        Args:
            session: DB session.
            user_id: ID пользователя.
            badge_id: ID значка.

        Returns:
            dict с начисленными XP и кредитами.
        """
        from src.db.models.badge import Badge, UserBadge
        from src.db.models.user import User

        user_badge = UserBadge(
            user_id=user_id,
            badge_id=badge_id,
            earned_at=datetime.now(UTC),
        )
        session.add(user_badge)

        # Добавляем XP и кредиты за значок
        badge = await session.get(Badge, badge_id)
        rewards = {"xp": 0, "credits": 0}

        if badge:
            user = await session.get(User, user_id)
            if user:
                if badge.xp_reward > 0:
                    user.xp_points += badge.xp_reward
                    rewards["xp"] = badge.xp_reward

                if badge.credits_reward > 0:
                    user.credits += badge.credits_reward
                    rewards["credits"] = badge.credits_reward

        logger.info(f"Awarded badge {badge_id} to user {user_id} (XP: {rewards['xp']}, Credits: {rewards['credits']})")
        return rewards

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

    async def check_achievements(self, user_id: int) -> list[dict[str, Any]]:
        """
        Проверить все достижения пользователя и выдать новые значки.

        Использует модель BadgeAchievement для проверки условий.

        Args:
            user_id: ID пользователя.

        Returns:
            Список выданных значков с наградами.
        """
        from sqlalchemy import select

        from src.db.models.badge import Badge, BadgeAchievement, UserBadge
        from src.db.models.user import User

        awarded_badges = []

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return []

            # Получаем уже выданные значки
            user_badge_stmt = select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
            user_badge_result = await session.execute(user_badge_stmt)
            earned_badge_ids = {row[0] for row in user_badge_result.all()}

            # Получаем все активные достижения
            stmt = select(BadgeAchievement).where(
                BadgeAchievement.is_active == True  # noqa: E712
            )
            result = await session.execute(stmt)
            achievements = list(result.scalars().all())

            # Проверяем каждое достижение
            for achievement in achievements:
                if achievement.badge_id in earned_badge_ids:
                    continue  # Уже получен

                # Проверяем условие
                condition_met = await self._check_achievement_condition(
                    session, user, achievement
                )

                if condition_met:
                    # Выдаём значок
                    await self._award_badge_internal(
                        session, user_id, achievement.badge_id
                    )

                    # Получаем информацию о значке
                    badge = await session.get(Badge, achievement.badge_id)
                    if badge:
                        awarded_badges.append({
                            "badge_id": badge.id,
                            "code": badge.code,
                            "name": badge.name,
                            "icon_emoji": badge.icon_emoji,
                            "xp_reward": badge.xp_reward,
                            "credits_reward": badge.credits_reward,
                            "description": badge.description,
                        })

            await session.commit()

        return awarded_badges

    async def _check_achievement_condition(
        self,
        session,
        user,
        achievement,
    ) -> bool:
        """
        Проверить условие достижения из BadgeAchievement.

        Args:
            session: DB session.
            user: Объект пользователя.
            achievement: Объект достижения.

        Returns:
            True если условие выполнено.
        """
        from sqlalchemy import func, select

        from src.db.models.analytics import TelegramChat
        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog, MailingStatus
        from src.db.models.review import Review

        achievement_type = achievement.achievement_type
        threshold = achievement.threshold

        # Campaign count
        if achievement_type == "campaign_count":
            stmt = select(func.count(Campaign.id)).where(
                Campaign.user_id == user.id
            )
            count = (await session.execute(stmt)).scalar() or 0
            return count >= threshold

        # Placement count (для владельцев каналов)
        if achievement_type == "placement_count":
            stmt = select(func.count(MailingLog.id)).join(
                TelegramChat, MailingLog.chat_id == TelegramChat.id
            ).where(
                TelegramChat.owner_user_id == user.id,
                MailingLog.status == MailingStatus.SENT,
            )
            count = (await session.execute(stmt)).scalar() or 0
            return count >= threshold

        # Streak days
        if achievement_type == "streak_days":
            return (user.login_streak_days or 0) >= threshold

        # XP level
        if achievement_type == "xp_level":
            return user.level >= threshold

        # Total spent
        if achievement_type == "total_spent":
            return float(user.total_spent or 0) >= threshold

        # Total earned
        if achievement_type == "total_earned":
            return float(user.total_earned or 0) >= threshold

        # Review count
        if achievement_type == "review_count":
            stmt = select(func.count(Review.id)).where(
                Review.reviewer_id == user.id
            )
            count = (await session.execute(stmt)).scalar() or 0
            return count >= threshold

        return False


# Глобальный экземпляр
badge_service = BadgeService()
