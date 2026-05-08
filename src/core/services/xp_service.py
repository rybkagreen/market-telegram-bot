"""
XP Service — сервис для управления опытом и уровнями.

Pattern 1 (S-48): caller-controlled transaction. Methods accept session arg;
caller manages commit/rollback boundary. Service does not own session lifecycle.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

USER_NOT_FOUND = "User not found"
UNKNOWN_STR = "Неизвестно"


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
    """Caller-controlled transaction (S-48 contract).

    Service does not own session lifecycle — every async method accepts
    session arg; caller manages commit/rollback boundary.
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""

    def get_level_for_xp(self, xp: int) -> int:
        """Получить уровень по количеству XP."""
        for level in range(10, 0, -1):
            if xp >= LEVEL_THRESHOLDS[level]:
                return level
        return 1

    def get_level_name(self, level: int) -> str:
        """Получить название уровня."""
        return LEVEL_NAMES.get(level, UNKNOWN_STR)

    def get_level_discount(self, level: int) -> int:
        """Получить скидку уровня в процентах."""
        return LEVEL_DISCOUNTS.get(level, 0)

    def get_level_privileges(self, level: int) -> dict[str, Any]:
        """Получить привилегии уровня."""
        return {
            "discount_pct": self.get_level_discount(level),
            "level_name": self.get_level_name(level),
            "features": self._get_level_features(level),
        }

    def _get_level_features(self, level: int) -> list[str]:
        """Получить список особенностей уровня."""
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
        """Получить прогресс до следующего уровня."""
        if current_level >= 10:
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
        session: AsyncSession,
        user_id: int,
        amount: int,
        reason: str,
    ) -> LevelUpEvent | None:
        """Добавить XP пользователю (общий путь, обратная совместимость)."""
        from sqlalchemy import select

        from src.db.models.user import User

        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User {user_id} not found")
            return None

        old_level = user.advertiser_level
        old_xp = user.advertiser_xp

        user.advertiser_xp += amount
        new_xp = user.advertiser_xp

        new_level = self.get_level_for_xp(new_xp)

        level_up_event = None
        if new_level > old_level:
            user.advertiser_level = new_level
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

        return level_up_event

    async def add_advertiser_xp(
        self,
        session: AsyncSession,
        user_id: int,
        amount: int,
        reason: str = "campaign",
    ) -> tuple[int, bool]:
        """Добавить XP рекламодателя."""
        from src.db.models.user import User

        user = await session.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return (1, False)

        old_level = user.advertiser_level
        user.advertiser_xp += amount
        new_xp = user.advertiser_xp

        new_level = self.get_level_for_xp(new_xp)
        leveled_up = False

        if new_level > old_level:
            user.advertiser_level = new_level
            leveled_up = True
            logger.info(
                f"User {user_id} advertiser level up: {old_level} → {new_level} "
                f"({amount} XP for {reason})"
            )

        return (new_level, leveled_up)

    async def add_owner_xp(
        self,
        session: AsyncSession,
        user_id: int,
        amount: int,
        reason: str = "publication",
    ) -> tuple[int, bool]:
        """Добавить XP владельца."""
        from src.db.models.user import User

        user = await session.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return (1, False)

        old_level = user.owner_level
        user.owner_xp += amount
        new_xp = user.owner_xp

        new_level = self.get_level_for_xp(new_xp)
        leveled_up = False

        if new_level > old_level:
            user.owner_level = new_level
            leveled_up = True
            logger.info(
                f"User {user_id} owner level up: {old_level} → {new_level} "
                f"({amount} XP for {reason})"
            )

        return (new_level, leveled_up)

    async def get_user_stats(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Получить общую статистику пользователя."""
        from src.db.models.user import User

        user = await session.get(User, user_id)
        if not user:
            return {"error": USER_NOT_FOUND}

        combined_level = max(user.advertiser_level, user.owner_level)
        combined_xp = user.advertiser_xp + user.owner_xp
        progress = self.get_progress_to_next_level(combined_level, combined_xp)
        privileges = self.get_level_privileges(combined_level)

        return {
            "user_id": user_id,
            "level": combined_level,
            "level_name": self.get_level_name(combined_level),
            "xp_points": combined_xp,
            "progress": progress,
            "privileges": privileges,
            "total_spent": float(getattr(user, "total_spent", None) or 0),
            "total_earned": float(getattr(user, "total_earned", None) or 0),
            "streak_days": getattr(user, "streak_days", None) or 0,
        }

    async def get_advertiser_stats(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Получить статистику рекламодателя."""
        from src.db.models.user import User

        user = await session.get(User, user_id)
        if not user:
            return {"error": USER_NOT_FOUND}

        progress = self.get_progress_to_next_level(
            user.advertiser_level,
            user.advertiser_xp,
        )

        return {
            "user_id": user_id,
            "level": user.advertiser_level,
            "level_name": ADVERTISER_LEVEL_NAMES.get(user.advertiser_level, UNKNOWN_STR),
            "xp_points": user.advertiser_xp,
            "progress": progress,
            "privileges": self.get_level_privileges(user.advertiser_level),
        }

    async def get_owner_stats(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Получить статистику владельца."""
        from src.db.models.user import User

        user = await session.get(User, user_id)
        if not user:
            return {"error": USER_NOT_FOUND}

        progress = self.get_progress_to_next_level(
            user.owner_level,
            user.owner_xp,
        )

        return {
            "user_id": user_id,
            "level": user.owner_level,
            "level_name": OWNER_LEVEL_NAMES.get(user.owner_level, UNKNOWN_STR),
            "xp_points": user.owner_xp,
            "progress": progress,
            "privileges": self.get_level_privileges(user.owner_level),
        }

    async def award_streak_bonus(
        self,
        session: AsyncSession,
        user_id: int,
        streak_days: int,
    ) -> dict[str, Any]:
        """Начислить бонус за стрик активности.

        Бонусы:
        - 7 дней: +50 XP + 10 ₽
        - 14 дней: +100 XP + 25 ₽
        - 30 дней: +300 XP + 100 ₽
        - 100 дней: +1000 XP + 500 ₽ + значок
        """
        from sqlalchemy import select

        from src.core.services.badge_service import badge_service
        from src.db.models.user import User

        bonuses = {
            7: {"xp": 50, "balance_rub": 10, "badge_code": None},
            14: {"xp": 100, "balance_rub": 25, "badge_code": None},
            30: {"xp": 300, "balance_rub": 100, "badge_code": "streak_30_days"},
            100: {"xp": 1000, "balance_rub": 500, "badge_code": "streak_100_days"},
        }

        earned_bonus = None
        for threshold, bonus in sorted(bonuses.items(), reverse=True):
            if streak_days >= threshold:
                earned_bonus = bonus
                break

        if not earned_bonus:
            return {"skipped": True, "reason": "threshold not reached"}

        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {"error": USER_NOT_FOUND}

        user.advertiser_xp += earned_bonus["xp"]  # type: ignore
        user.balance_rub += Decimal(str(earned_bonus["balance_rub"]))  # type: ignore

        badge_awarded: dict[str, Any] | None = None
        badge_code: str | None = earned_bonus.get("badge_code")  # type: ignore
        if badge_code:
            badge_result = await badge_service.award_badge(user_id, badge_code)
            if badge_result.get("success"):  # type: ignore
                badge_awarded = badge_result  # type: ignore

        return {
            "success": True,
            "streak_days": streak_days,
            "xp_awarded": earned_bonus["xp"],  # type: ignore
            "balance_rub_awarded": earned_bonus["balance_rub"],  # type: ignore
            "badge_awarded": badge_awarded,
        }


# Глобальный экземпляр
xp_service = XPService()
