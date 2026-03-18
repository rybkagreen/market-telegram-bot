"""
Celery задачи для системы достижений и значков.
Спринт 8 — автоматическая проверка и выдача значков.
"""

import asyncio
import logging
from datetime import UTC

from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="badges:check_user_achievements")
def check_user_achievements(self, user_id: int) -> dict:
    """
    Проверить достижения конкретного пользователя.

    Вызывается после ключевых событий:
    - Запуск кампании
    - Завершение рассылки
    - Обновление стрика

    Args:
        user_id: ID пользователя в БД.

    Returns:
        dict со списком выданных значков.
    """

    async def _check_async() -> dict:
        from src.core.services.badge_service import badge_service

        awarded_badges = await badge_service.check_achievements(user_id)

        if awarded_badges:
            # Отправляем уведомления о каждом значке
            for badge in awarded_badges:
                notify_badge_earned.delay(
                    user_id=user_id,
                    badge_name=badge["name"],
                    badge_emoji=badge["icon_emoji"],
                    xp_reward=badge["xp_reward"],
                    credits_reward=badge["credits_reward"],
                )

        return {
            "user_id": user_id,
            "awarded_badges": awarded_badges,
            "count": len(awarded_badges),
        }

    try:
        return asyncio.run(_check_async())
    except Exception as e:
        logger.error(f"check_user_achievements failed for user {user_id}: {e}")
        return {"error": str(e), "awarded_badges": []}


@celery_app.task(bind=True, base=BaseTask, name="badges:daily_badge_check")
def daily_badge_check(self) -> dict:
    """
    Ежедневная проверка достижений всех активных пользователей.

    Запуск: каждый день в 00:00 UTC.
    Проверяет стрики и другие ежедневные достижения.

    Returns:
        dict со статистикой проверки.
    """

    async def _check_daily_async() -> dict:
        from sqlalchemy import select

        from src.db.models.user import User

        checked_count = 0
        awarded_count = 0

        async with async_session_factory() as session:
            # Получаем активных пользователей (которые заходили за последние 7 дней)
            from datetime import datetime, timedelta

            week_ago = datetime.now(UTC) - timedelta(days=7)

            # ИЗМЕНЕНО (2026-03-17): is_banned → is_active, last_login_at → updated_at
            # (поля is_banned и last_login_at не существуют в модели User)
            stmt = select(User).where(
                User.is_active.is_(True),
                User.updated_at >= week_ago,
            )
            result = await session.execute(stmt)
            users = list(result.scalars().all())

            # Проверяем достижения для каждого
            from src.core.services.badge_service import badge_service

            for user in users:
                try:
                    awarded = await badge_service.check_achievements(user.id)
                    checked_count += 1
                    awarded_count += len(awarded)
                except Exception as e:
                    logger.error(f"Daily badge check failed for user {user.id}: {e}")

        return {
            "checked_users": checked_count,
            "awarded_badges": awarded_count,
        }

    try:
        result = asyncio.run(_check_daily_async())
        logger.info(f"Daily badge check completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Daily badge check failed: {e}")
        return {"error": str(e), "checked_users": 0, "awarded_badges": 0}


@celery_app.task(bind=True, base=BaseTask, name="badges:monthly_top_advertisers")
def monthly_top_advertisers(self) -> dict:
    """
    Проверка топ рекламодателей месяца.

    Запуск: 1-го числа каждого месяца в 00:00 UTC.
    Выдаёт значок "Топ рекламодатель" топ-10 пользователям.

    Returns:
        dict со списком победителей.
    """

    async def _check_monthly_async() -> dict:
        from sqlalchemy import func, select

        from src.db.models.badge import Badge
        from src.db.models.placement_request import PlacementRequest as Campaign

        async with async_session_factory() as session:
            # Считаем сумму потраченных средств за последний месяц
            from datetime import datetime, timedelta

            month_ago = datetime.now(UTC) - timedelta(days=30)

            stmt = (
                select(
                    Campaign.user_id,
                    func.sum(Campaign.cost).label("total_spent"),
                )
                .where(
                    Campaign.created_at >= month_ago,
                    Campaign.status.in_(["done", "running", "queued"]),
                )
                .group_by(Campaign.user_id)
                .order_by(func.sum(Campaign.cost).desc())
                .limit(10)
            )

            result = await session.execute(stmt)
            top_advertisers = list(result.all())

            # Находим значок "Топ рекламодатель"
            badge_stmt = select(Badge).where(Badge.code == "top_advertiser_monthly")
            badge_result = await session.execute(badge_stmt)
            badge = badge_result.scalar_one_or_none()

            if not badge:
                logger.warning("Badge 'top_advertiser_monthly' not found")
                return {"error": "Badge not found", "top_advertisers": []}

            # Выдаём значки топ-10
            from src.core.services.badge_service import badge_service

            awarded = []
            for row in top_advertisers:
                user_id = row.user_id
                total_spent = row.total_spent

                try:
                    award_result: dict = await badge_service.award_badge(user_id, badge.code)
                    if award_result.get("success"):
                        awarded.append(
                            {
                                "user_id": user_id,
                                "total_spent": float(total_spent),
                            }
                        )

                        # Отправляем уведомление
                        notify_badge_earned.delay(
                            user_id=user_id,
                            badge_name=badge.name,
                            badge_emoji=badge.icon_emoji,
                            xp_reward=badge.xp_reward,
                            credits_reward=badge.credits_reward,
                        )
                except Exception as e:
                    logger.error(f"Failed to award top advertiser badge to user {user_id}: {e}")

            return {
                "top_advertisers": awarded,
                "count": len(awarded),
            }

    try:
        result = asyncio.run(_check_monthly_async())
        logger.info(f"Monthly top advertisers check completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Monthly top advertisers check failed: {e}")
        return {"error": str(e), "top_advertisers": []}


@celery_app.task(name="badges:notify_badge_earned")
def notify_badge_earned(
    user_id: int,
    badge_name: str,
    badge_emoji: str,
    xp_reward: int,
    credits_reward: int,
) -> bool:
    """
    Отправить уведомление о получении значка.

    Args:
        user_id: ID пользователя.
        badge_name: Название значка.
        badge_emoji: Emoji значка.
        xp_reward: Награда XP.
        credits_reward: Награда кредитами.

    Returns:
        True если уведомление отправлено.
    """
    from src.tasks.notification_tasks import notify_user

    # Формируем сообщение
    message_parts = [
        "🏅 <b>Новый значок!</b>\n\n",
        f"{badge_emoji} <b>{badge_name}</b>\n\n",
    ]

    if xp_reward > 0:
        message_parts.append(f"+{xp_reward} XP\n")
    if credits_reward > 0:
        message_parts.append(f"+{credits_reward} кр\n")

    message_parts.append("\nПоздравляем с достижением!")

    message = "".join(message_parts)

    # Отправляем уведомление
    success = notify_user.delay(
        telegram_id=user_id,
        message=message,
        parse_mode="HTML",
    )

    return success


# ─────────────────────────────────────────────
# Триггеры для проверки достижений
# ─────────────────────────────────────────────


@celery_app.task(name="badges:trigger_after_campaign_launch")
def trigger_after_campaign_launch(user_id: int) -> dict:
    """
    Триггер проверки достижений после запуска кампании.

    Args:
        user_id: ID пользователя.
    """
    return check_user_achievements.delay(user_id)


@celery_app.task(name="badges:trigger_after_campaign_complete")
def trigger_after_campaign_complete(user_id: int) -> dict:
    """
    Триггер проверки достижений после завершения кампании.

    Args:
        user_id: ID пользователя.
    """
    return check_user_achievements.delay(user_id)


@celery_app.task(name="badges:trigger_after_streak_update")
def trigger_after_streak_update(user_id: int, new_streak: int) -> dict:
    """
    Триггер проверки достижений после обновления стрика.

    Args:
        user_id: ID пользователя.
        new_streak: Новое значение стрика.
    """
    # Проверяем только если стрик кратен 7 (бонусные вехи)
    if new_streak % 7 == 0:
        return check_user_achievements.delay(user_id)
    return {"skipped": True, "reason": "not milestone"}
