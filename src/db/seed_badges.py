"""
Seed script для заполнения базовых значков и достижений.
Запуск: poetry run python -m src.db.seed_badges

Спринт 8 — Геймификация
"""

import asyncio
import logging

from src.db.session import async_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_badges() -> None:
    """Создать базовые значки и достижения."""

    from src.db.models.badge import Badge, BadgeAchievement, BadgeCategory, BadgeConditionType

    async with async_session_factory() as session:
        # Базовые значки
        badges_data = [
            # Для рекламодателей
            {
                "code": "first_campaign",
                "name": "Первая кампания",
                "description": "Запуск первой рекламной кампании",
                "icon_emoji": "🚀",
                "xp_reward": 200,
                "credits_reward": 50,
                "category": BadgeCategory.ADVERTISER,
                "condition_type": BadgeConditionType.CAMPAIGNS_COUNT,
                "condition_value": 1,
                "is_rare": False,
                "is_active": True,
            },
            {
                "code": "10_campaigns",
                "name": "Опытный рекламодатель",
                "description": "Запуск 10 кампаний",
                "icon_emoji": "📊",
                "xp_reward": 500,
                "credits_reward": 100,
                "category": BadgeCategory.ADVERTISER,
                "condition_type": BadgeConditionType.CAMPAIGNS_COUNT,
                "condition_value": 10,
                "is_rare": False,
                "is_active": True,
            },
            {
                "code": "100_campaigns",
                "name": "Мастер кампаний",
                "description": "Запуск 100 кампаний",
                "icon_emoji": "🏆",
                "xp_reward": 2000,
                "credits_reward": 500,
                "category": BadgeCategory.ADVERTISER,
                "condition_type": BadgeConditionType.CAMPAIGNS_COUNT,
                "condition_value": 100,
                "is_rare": True,
                "is_active": True,
            },
            {
                "code": "top_spender_monthly",
                "name": "Топ рекламодатель месяца",
                "description": "Вход в топ-10 рекламодателей месяца",
                "icon_emoji": "👑",
                "xp_reward": 1000,
                "credits_reward": 300,
                "category": BadgeCategory.ADVERTISER,
                "condition_type": BadgeConditionType.MANUAL,
                "condition_value": 0,
                "is_rare": True,
                "is_active": True,
            },
            # Для владельцев каналов
            {
                "code": "first_placement",
                "name": "Первая публикация",
                "description": "Первая успешная публикация рекламы",
                "icon_emoji": "📢",
                "xp_reward": 100,
                "credits_reward": 25,
                "category": BadgeCategory.OWNER,
                "condition_type": BadgeConditionType.PLACEMENTS_COUNT,
                "condition_value": 1,
                "is_rare": False,
                "is_active": True,
            },
            {
                "code": "100_placements",
                "name": "100 размещений",
                "description": "100 успешных публикаций",
                "icon_emoji": "💯",
                "xp_reward": 1000,
                "credits_reward": 200,
                "category": BadgeCategory.OWNER,
                "condition_type": BadgeConditionType.PLACEMENTS_COUNT,
                "condition_value": 100,
                "is_rare": False,
                "is_active": True,
            },
            {
                "code": "1000_placements",
                "name": "1000 размещений",
                "description": "1000 успешных публикаций",
                "icon_emoji": "🎯",
                "xp_reward": 5000,
                "credits_reward": 1000,
                "category": BadgeCategory.OWNER,
                "condition_type": BadgeConditionType.PLACEMENTS_COUNT,
                "condition_value": 1000,
                "is_rare": True,
                "is_active": True,
            },
            # Стрики активности
            {
                "code": "streak_7_days",
                "name": "Недельный стрик",
                "description": "7 дней активности подряд",
                "icon_emoji": "🔥",
                "xp_reward": 100,
                "credits_reward": 20,
                "category": BadgeCategory.BOTH,
                "condition_type": BadgeConditionType.STREAK_DAYS,
                "condition_value": 7,
                "is_rare": False,
                "is_active": True,
            },
            {
                "code": "streak_30_days",
                "name": "Месяц активности",
                "description": "30 дней активности подряд",
                "icon_emoji": "🌟",
                "xp_reward": 500,
                "credits_reward": 100,
                "category": BadgeCategory.BOTH,
                "condition_type": BadgeConditionType.STREAK_DAYS,
                "condition_value": 30,
                "is_rare": False,
                "is_active": True,
            },
            {
                "code": "streak_100_days",
                "name": "100 дней активности",
                "description": "100 дней активности подряд",
                "icon_emoji": "💎",
                "xp_reward": 2000,
                "credits_reward": 500,
                "category": BadgeCategory.BOTH,
                "condition_type": BadgeConditionType.STREAK_DAYS,
                "condition_value": 100,
                "is_rare": True,
                "is_active": True,
            },
            # Отзывы
            {
                "code": "first_review",
                "name": "Первый отзыв",
                "description": "Оставить первый отзыв",
                "icon_emoji": "⭐",
                "xp_reward": 50,
                "credits_reward": 10,
                "category": BadgeCategory.BOTH,
                "condition_type": BadgeConditionType.REVIEW_COUNT,
                "condition_value": 1,
                "is_rare": False,
                "is_active": True,
            },
            {
                "code": "10_reviews",
                "name": "Активный рецензент",
                "description": "10 оставленных отзывов",
                "icon_emoji": "📝",
                "xp_reward": 300,
                "credits_reward": 50,
                "category": BadgeCategory.BOTH,
                "condition_type": BadgeConditionType.REVIEW_COUNT,
                "condition_value": 10,
                "is_rare": False,
                "is_active": True,
            },
        ]

        # Создаём значки
        created_badges = []
        for badge_data in badges_data:
            # Проверяем существует ли уже
            existing = await session.execute(
                Badge.__table__.select().where(Badge.code == badge_data["code"])
            )
            if existing.fetchone():
                logger.info(f"Badge '{badge_data['code']}' already exists, skipping")
                continue

            badge = Badge(**badge_data)
            session.add(badge)
            created_badges.append(badge)
            logger.info(f"Created badge: {badge.name} ({badge.code})")

        await session.flush()

        # Создаём достижения для значков
        achievements_data = []
        for badge in created_badges:
            achievement = BadgeAchievement(
                badge_id=badge.id,
                achievement_type=badge.condition_type.value,
                threshold=badge.condition_value,
                description=badge.description,
                is_active=badge.is_active,
            )
            session.add(achievement)
            achievements_data.append(achievement)
            logger.info(f"Created achievement for badge {badge.name}")

        await session.commit()

        logger.info(f"✅ Seed completed: {len(created_badges)} badges, {len(achievements_data)} achievements")


if __name__ == "__main__":
    asyncio.run(seed_badges())
