"""
XP Service — сервис для управления опытом и уровнями.
Спринт 4 — геймификация и удержание пользователей.

Таблица уровней (PRD §9.1):
- Уровень 1: 0 XP (Новичок)
- Уровень 2: 100 XP (Начинающий)
- Уровень 3: 300 XP (Опытный)
- Уровень 4: 600 XP (Продвинутый)
- Уровень 5: 1000 XP (Эксперт)
- Уровень 6: 1500 XP (Профессионал)
- Уровень 7: 2100 XP (Мастер)
- Уровень 8: 2800 XP (Ветеран)
- Уровень 9: 3600 XP (Легенда)
- Уровень 10: 4500 XP (Икона)
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


# Импортируем словари из cabinet.py для консистентности
ADVERTISER_LEVEL_NAMES = {
    1: "Новичок 🌱",
    2: "Активный ⭐",
    3: "Профи 🔥",
    4: "Эксперт 💎",
    5: "Мастер 🚀",
    6: "Легенда 🎯",
    7: "Бог рекламы 👑",
}

OWNER_LEVEL_NAMES = {
    1: "Новичок 🌱",
    2: "Популярный ⭐",
    3: "Избранный 🔥",
    4: "Топовый 💎",
    5: "Легенда 🚀",
    6: "Влиятельный 🎯",
    7: "Медиамагнат 👑",
}


# Таблица уровней (PRD §9.1)
LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 300,
    4: 600,
    5: 1000,
    6: 1500,
    7: 2100,
    8: 2800,
    9: 3600,
    10: 4500,
}

# Названия уровней
LEVEL_NAMES = {
    1: "Новичок",
    2: "Начинающий",
    3: "Опытный",
    4: "Продвинутый",
    5: "Эксперт",
    6: "Профессионал",
    7: "Мастер",
    8: "Ветеран",
    9: "Легенда",
    10: "Икона",
}

# Скидки по уровням (PRD §9.1)
LEVEL_DISCOUNTS = {
    1: 0,
    2: 0,
    3: 3,
    4: 5,
    5: 8,
    6: 10,
    7: 12,
    8: 15,
    9: 18,
    10: 20,
}

# XP-награды за действия
XP_REWARDS = {
    "first_campaign": 200,  # Первая кампания
    "campaign_launched": 50,  # Запуск кампании
    "campaign_completed": 100,  # Завершение кампании
    "review_left": 20,  # Оставлен отзыв
    "channel_added": 30,  # Добавлен канал
    "daily_login": 10,  # Ежедневный вход
    "referral_joined": 50,  # Реферал зарегистрировался
    "referral_first_campaign": 100,  # Реферал запустил первую кампанию
}


@dataclass
class LevelUpEvent:
    """Событие повышения уровня."""

    user_id: int
    old_level: int
    new_level: int
    xp_reward: int


class XPService:
    """
    Сервис для управления опытом и уровнями.

    Методы:
        add_xp: Добавить XP пользователю
        get_level_for_xp: Получить уровень по XP
        get_level_privileges: Получить привилегии уровня
        get_progress_to_next_level: Получить прогресс до следующего уровня
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    def get_level_for_xp(self, xp: int) -> int:
        """
        Получить уровень по количеству XP.

        Args:
            xp: Количество очков опыта.

        Returns:
            Уровень (1-10).
        """
        for level in range(10, 0, -1):
            if xp >= LEVEL_THRESHOLDS[level]:
                return level
        return 1

    def get_level_name(self, level: int) -> str:
        """
        Получить название уровня.

        Args:
            level: Номер уровня.

        Returns:
            Название уровня.
        """
        return LEVEL_NAMES.get(level, "Неизвестно")

    def get_level_discount(self, level: int) -> int:
        """
        Получить скидку уровня в процентах.

        Args:
            level: Номер уровня.

        Returns:
            Скидка в процентах.
        """
        return LEVEL_DISCOUNTS.get(level, 0)

    def get_level_privileges(self, level: int) -> dict[str, Any]:
        """
        Получить привилегии уровня.

        Args:
            level: Номер уровня.

        Returns:
            dict с discount_pct, badge, features.
        """
        return {
            "discount_pct": self.get_level_discount(level),
            "level_name": self.get_level_name(level),
            "features": self._get_level_features(level),
        }

    def _get_level_features(self, level: int) -> list[str]:
        """
        Получить список особенностей уровня.

        Args:
            level: Номер уровня.

        Returns:
            Список особенностей.
        """
        features = []

        if level >= 3:
            features.append("Скидка 3% на все размещения")
        if level >= 5:
            features.append("Приоритетная поддержка")
        if level >= 7:
            features.append("Персональный менеджер")
        if level >= 10:
            features.append("Эксклюзивный значок")

        return features

    def get_progress_to_next_level(
        self,
        current_level: int,
        current_xp: int,
    ) -> dict[str, Any]:
        """
        Получить прогресс до следующего уровня.

        Args:
            current_level: Текущий уровень.
            current_xp: Текущее количество XP.

        Returns:
            dict с current_xp, next_level_xp, progress_percent, xp_to_next.
        """
        if current_level >= 10:
            # Максимальный уровень
            return {
                "current_xp": current_xp,
                "next_level_xp": LEVEL_THRESHOLDS[10],
                "progress_percent": 100.0,
                "xp_to_next": 0,
                "max_level": True,
            }

        next_level = current_level + 1
        current_threshold = LEVEL_THRESHOLDS[current_level]
        next_threshold = LEVEL_THRESHOLDS[next_level]

        xp_in_current_level = current_xp - current_threshold
        xp_needed = next_threshold - current_threshold
        progress_percent = (xp_in_current_level / xp_needed) * 100 if xp_needed > 0 else 0

        return {
            "current_xp": current_xp,
            "next_level_xp": next_threshold,
            "progress_percent": min(100.0, progress_percent),
            "xp_to_next": next_threshold - current_xp,
            "max_level": False,
        }

    async def add_xp(
        self,
        user_id: int,
        amount: int,
        reason: str,
    ) -> LevelUpEvent | None:
        """
        Добавить XP пользователю (ОБЩЕЕ — для обратной совместимости).

        Args:
            user_id: ID пользователя.
            amount: Количество XP.
            reason: Причина начисления (для логирования).

        Returns:
            LevelUpEvent если уровень повышен, иначе None.
        """

        from src.db.models.user import User

        async with async_session_factory() as session, session.begin():
            # ✅ БЛОКИРОВКА СТРОКИ для предотвращения race condition
            from sqlalchemy import select

            stmt = select(User).where(User.id == user_id).with_for_update()
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found")
                return None

            old_level = user.level
            old_xp = user.xp_points

            # Добавляем XP
            user.xp_points += amount
            new_xp = user.xp_points

            # Проверяем повышение уровня
            new_level = self.get_level_for_xp(new_xp)

            level_up_event = None
            if new_level > old_level:
                user.level = new_level
                level_up_event = LevelUpEvent(
                    user_id=user_id,
                    old_level=old_level,
                    new_level=new_level,
                    xp_reward=XP_REWARDS.get("campaign_completed", 0),
                )
                logger.info(
                    f"User {user_id} leveled up: {old_level} → {new_level} ({old_xp} → {new_xp} XP)"
                )
            else:
                logger.info(f"User {user_id} gained {amount} XP ({old_xp} → {new_xp} XP)")

            # session.begin() автоматически commit
            return level_up_event

    # === Спринт 5: Раздельный XP для рекламодателей и владельцев ===

    async def add_advertiser_xp(
        self,
        user_id: int,
        amount: int,
        reason: str = "campaign",
    ) -> tuple[int, bool]:
        """
        Добавить XP рекламодателя.

        Args:
            user_id: ID пользователя.
            amount: Количество XP.
            reason: Причина начисления.

        Returns:
            (new_level, leveled_up)
        """
        from src.db.models.user import User

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return (1, False)

            old_level = user.advertiser_level
            user.advertiser_xp += amount
            new_xp = user.advertiser_xp

            # Вычисляем новый уровень
            new_level = self.get_level_for_xp(new_xp)
            leveled_up = False

            if new_level > old_level:
                user.advertiser_level = new_level
                leveled_up = True
                logger.info(
                    f"User {user_id} advertiser level up: {old_level} → {new_level} "
                    f"({amount} XP for {reason})"
                )

            # Обновляем общий XP для обратной совместимости
            user.xp_points = user.advertiser_xp + user.owner_xp
            user.level = max(user.advertiser_level, user.owner_level)

            await session.flush()
            return (new_level, leveled_up)

    async def add_owner_xp(
        self,
        user_id: int,
        amount: int,
        reason: str = "publication",
    ) -> tuple[int, bool]:
        """
        Добавить XP владельца.

        Args:
            user_id: ID пользователя.
            amount: Количество XP.
            reason: Причина начисления.

        Returns:
            (new_level, leveled_up)
        """
        from src.db.models.user import User

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return (1, False)

            old_level = user.owner_level
            user.owner_xp += amount
            new_xp = user.owner_xp

            # Вычисляем новый уровень
            new_level = self.get_level_for_xp(new_xp)
            leveled_up = False

            if new_level > old_level:
                user.owner_level = new_level
                leveled_up = True
                logger.info(
                    f"User {user_id} owner level up: {old_level} → {new_level} "
                    f"({amount} XP for {reason})"
                )

            # Обновляем общий XP для обратной совместимости
            user.xp_points = user.advertiser_xp + user.owner_xp
            user.level = max(user.advertiser_level, user.owner_level)

            await session.flush()
            return (new_level, leveled_up)

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """
        Получить общую статистику пользователя (для обратной совместимости).

        Args:
            user_id: ID пользователя.

        Returns:
            dict с level, xp, progress, privileges.
        """

        from src.db.models.user import User

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return {"error": "User not found"}

            progress = self.get_progress_to_next_level(user.level, user.xp_points)
            privileges = self.get_level_privileges(user.level)

            return {
                "user_id": user_id,
                "level": user.level,
                "level_name": self.get_level_name(user.level),
                "xp_points": user.xp_points,
                "progress": progress,
                "privileges": privileges,
                "total_spent": float(user.total_spent) if user.total_spent else 0,
                "total_earned": float(user.total_earned) if user.total_earned else 0,
                "streak_days": user.streak_days or 0,
            }

    # === Спринт 5: Раздельная статистика ===

    async def get_advertiser_stats(self, user_id: int) -> dict[str, Any]:
        """
        Получить статистику рекламодателя.

        Args:
            user_id: ID пользователя.

        Returns:
            dict с advertiser_level, advertiser_xp, progress.
        """
        from src.db.models.user import User

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return {"error": "User not found"}

            progress = self.get_progress_to_next_level(
                user.advertiser_level,
                user.advertiser_xp,
            )

            return {
                "user_id": user_id,
                "level": user.advertiser_level,
                "level_name": ADVERTISER_LEVEL_NAMES.get(user.advertiser_level, "Неизвестно"),
                "xp_points": user.advertiser_xp,
                "progress": progress,
                "privileges": self.get_level_privileges(user.advertiser_level),
            }

    async def get_owner_stats(self, user_id: int) -> dict[str, Any]:
        """
        Получить статистику владельца.

        Args:
            user_id: ID пользователя.

        Returns:
            dict с owner_level, owner_xp, progress.
        """
        from src.db.models.user import User

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return {"error": "User not found"}

            progress = self.get_progress_to_next_level(
                user.owner_level,
                user.owner_xp,
            )

            return {
                "user_id": user_id,
                "level": user.owner_level,
                "level_name": OWNER_LEVEL_NAMES.get(user.owner_level, "Неизвестно"),
                "xp_points": user.owner_xp,
                "progress": progress,
                "privileges": self.get_level_privileges(user.owner_level),
            }

    async def award_streak_bonus(self, user_id: int, streak_days: int) -> dict[str, Any]:
        """
        Начислить бонус за стрик активности.

        Бонусы:
        - 7 дней: +50 XP + 10 кредитов
        - 14 дней: +100 XP + 25 кредитов
        - 30 дней: +300 XP + 100 кредитов
        - 100 дней: +1000 XP + 500 кредитов + значок

        Args:
            user_id: ID пользователя.
            streak_days: Количество дней стрика.

        Returns:
            dict с начисленными бонусами.
        """
        from src.core.services.badge_service import badge_service
        from src.db.models.user import User

        # Таблица бонусов
        bonuses = {
            7: {"xp": 50, "credits": 10, "badge_code": None},
            14: {"xp": 100, "credits": 25, "badge_code": None},
            30: {"xp": 300, "credits": 100, "badge_code": "streak_30_days"},
            100: {"xp": 1000, "credits": 500, "badge_code": "streak_100_days"},
        }

        # Находим максимальный порог который достигнут
        earned_bonus = None
        for threshold, bonus in sorted(bonuses.items(), reverse=True):
            if streak_days >= threshold:
                earned_bonus = bonus
                break

        if not earned_bonus:
            return {"skipped": True, "reason": "threshold not reached"}

        async with async_session_factory() as session, session.begin():
            # ✅ БЛОКИРОВКА СТРОКИ для предотвращения race condition
            from sqlalchemy import select

            stmt = select(User).where(User.id == user_id).with_for_update()
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return {"error": "User not found"}

            # Начисляем XP
            user.xp_points += earned_bonus["xp"]  # type: ignore

            # Начисляем кредиты
            user.credits += earned_bonus["credits"]  # type: ignore

            # Выдаём значок если есть
            badge_awarded: dict[str, Any] | None = None
            badge_code: str | None = earned_bonus.get("badge_code")  # type: ignore
            if badge_code:
                result = await badge_service.award_badge(user_id, badge_code)
                if result.get("success"):  # type: ignore
                    badge_awarded = result  # type: ignore

            # session.begin() автоматически commit
            return {
                "success": True,
                "streak_days": streak_days,
                "xp_awarded": earned_bonus["xp"],  # type: ignore
                "credits_awarded": earned_bonus["credits"],  # type: ignore
                "badge_awarded": badge_awarded,
            }


# Глобальный экземпляр
xp_service = XPService()
