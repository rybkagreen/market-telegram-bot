"""
Gamification Celery tasks для удержания пользователей.
Спринт 4 — стрики активности, еженедельные дайджесты, сезонные события.
"""

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


def _is_streak_active(last_login_date: date, today: date, yesterday: date) -> bool:
    """Возвращает True если стрик продолжается (вход сегодня)."""
    return last_login_date in (today, yesterday) and (today - last_login_date).days == 0


async def _process_streak_continue(user: Any, today: date, stats: dict[str, Any]) -> None:
    """Обновить стрик если пользователь активен сегодня."""
    if user.updated_at and user.updated_at.date() == today:
        return  # Уже обновили сегодня

    user.login_streak_days = (user.login_streak_days or 0) + 1

    if user.login_streak_days > user.max_streak_days:
        user.max_streak_days = user.login_streak_days

    stats["streaks_updated"] += 1

    user.xp_points += 10
    stats["xp_awarded"] += 10

    # TASK 8.8: Проверяем бонусы за стрик (7, 14, 30, 100 дней)
    if user.login_streak_days % 7 == 0:
        from src.core.services.xp_service import xp_service

        await xp_service.award_streak_bonus(user.id, user.login_streak_days)


def _process_streak_reset(user: Any, stats: dict[str, Any]) -> None:
    """Сбросить стрик если пользователь пропустил день."""
    if user.login_streak_days > 0:
        user.login_streak_days = 0
        stats["streaks_reset"] += 1


async def _update_user_streak(
    user: Any, today: date, yesterday: date, stats: dict[str, Any]
) -> None:
    """Обработать стрик одного пользователя."""
    if user.last_login_at is None:
        return

    last_login_date = user.last_login_at.date()

    if _is_streak_active(last_login_date, today, yesterday):
        await _process_streak_continue(user, today, stats)
    else:
        _process_streak_reset(user, stats)


@celery_app.task(bind=True, base=BaseTask, name="gamification:update_streaks_daily", queue="gamification")
def update_streaks_daily(self) -> dict[str, Any]:
    """
    Обновить стрики активности пользователей.
    Запускается ежедневно в 00:00 UTC.

    Логика:
    - Если пользователь заходил вчера или сегодня — стрик продолжается
    - Если пропустил день — стрик сбрасывается
    - За каждый день стрика +10 XP

    Returns:
        Статистика обновления.
    """
    logger.info("Starting daily streaks update")

    async def _update_async() -> dict[str, Any]:
        from sqlalchemy import select

        from src.db.models.user import User

        stats = {
            "total_users": 0,
            "streaks_updated": 0,
            "streaks_reset": 0,
            "xp_awarded": 0,
        }

        async with async_session_factory() as session:
            stmt = select(User).where(User.is_active == True)  # noqa: E712
            result = await session.execute(stmt)
            users = list(result.scalars().all())

            stats["total_users"] = len(users)
            today = date.today()
            yesterday = today - timedelta(days=1)

            for user in users:
                await _update_user_streak(user, today, yesterday, stats)

            await session.commit()

            return stats

    try:
        result = asyncio.run(_update_async())
        logger.info(f"Daily streaks update completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error updating streaks: {e}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=BaseTask, name="gamification:send_weekly_digest", queue="gamification")
def send_weekly_digest(self) -> dict[str, Any]:
    """
    Отправить еженедельный дайджест неактивным пользователям.
    Запускается каждый понедельник в 10:00 UTC.

    Логика:
    - Найти пользователей которые не заходили 7+ дней
    - Отправить уведомление с призывом вернуться
    - Предложить бонус за возвращение

    Returns:
        Статистика отправки.
    """
    logger.info("Starting weekly digest send")

    async def _send_async() -> dict[str, Any]:
        from sqlalchemy import select

        from src.db.models.user import User

        stats = {
            "total_inactive": 0,
            "digests_sent": 0,
            "errors": 0,
        }

        async with async_session_factory() as session:
            # Находим неактивных пользователей (7+ дней)
            seven_days_ago = datetime.now(UTC) - timedelta(days=7)

            # ИЗМЕНЕНО (2026-03-17): is_banned → is_active (поле is_banned не существует в модели User)
            stmt = (
                select(User)
                .where(
                    User.is_active == True,  # noqa: E712
                    User.updated_at < seven_days_ago,
                )
                .limit(1000)
            )
            result = await session.execute(stmt)
            inactive_users = list(result.scalars().all())

            stats["total_inactive"] = len(inactive_users)

            for user in inactive_users:
                try:
                    # Проверяем что уведомления включены
                    if not user.notifications_enabled:
                        continue

                    # Отправляем дайджест
                    await _send_digest_to_user(user)
                    stats["digests_sent"] += 1

                except Exception as e:
                    logger.error(f"Error sending digest to user {user.id}: {e}")
                    stats["errors"] += 1

        return stats

    try:
        return asyncio.run(_send_async())
    except Exception as e:
        logger.error(f"send_weekly_digest failed: {e}")
        return {"status": "error", "error": str(e)}


async def _send_digest_to_user(user) -> bool:
    """
    Отправить дайджест пользователю.

    Args:
        user: Объект пользователя.

    Returns:
        True если успешно.
    """
    from src.tasks._bot_factory import get_bot

    bot = get_bot()

    text = (
        f"👋 <b>Мы скучаем, {user.first_name or user.username or 'друг'}!</b>\n\n"
        f"Вы не заходили в бота уже неделю.\n\n"
        f"🎁 <b>Бонус за возвращение:</b>\n"
        f"+50 кредитов на баланс!\n\n"
        f"📊 <b>Что вы пропустили:</b>\n"
        f"• Новые B2B-пакеты со скидками\n"
        f"• Улучшенная система рейтингов\n"
        f"• Геймификация с уровнями и значками\n\n"
        f"Нажмите /start чтобы вернуться!"
    )

    await bot.send_message(
        chat_id=user.telegram_id,
        text=text,
        parse_mode="HTML",
    )

    # Начисляем бонус за возвращение
    await _award_return_bonus(user.id)

    return True


async def _award_return_bonus(user_id: int) -> None:
    """
    Начислить бонус за возвращение.

    Args:
        user_id: ID пользователя.
    """
    async with async_session_factory() as session:
        from decimal import Decimal

        from src.db.models.transaction import TransactionType
        from src.db.repositories.user_repo import UserRepository

        user_repo = UserRepository(session)
        await user_repo.update_balance_rub(user_id, Decimal("50"))  # +50 ₽ бонус

        # Создаём транзакцию

        from src.db.repositories.transaction_repo import TransactionRepository

        transaction_repo = TransactionRepository(session)
        await transaction_repo.create({
            "user_id": user_id,
            "amount": Decimal(50),
            "type": TransactionType.bonus,
            "reference_type": "return_bonus",
            "description": "Бонус за возвращение после недели неактивности",
        })


@celery_app.task(bind=True, base=BaseTask, name="gamification:check_seasonal_events", queue="gamification")
def check_seasonal_events(self) -> dict[str, Any]:
    """
    Проверить и активировать сезонные события.
    Запускается ежедневно в 08:00 UTC.

    Сезонные события:
    - Новый год (декабрь-январь) — праздничные значки
    - Чёрная пятница (ноябрь) — скидки на тарифы
    - День святого Валентина (февраль) — бонусы за рефералов

    Returns:
        Статистика событий.
    """
    logger.info("Starting seasonal events check")

    async def _check_async() -> dict[str, Any]:
        today = date.today()
        events = []

        # Новый год (20 декабря - 10 января)
        if (today.month == 12 and today.day >= 20) or (today.month == 1 and today.day <= 10):
            events.append({
                "name": "new_year",
                "active": True,
                "bonus": "Праздничный значок + 100 XP",
            })

        # Чёрная пятница (последняя пятница ноября)
        if today.month == 11 and today.weekday() == 4:  # Пятница
            events.append({
                "name": "black_friday",
                "active": True,
                "bonus": "Скидка 50% на все тарифы",
            })

        # День святого Валентина (14 февраля)
        if today.month == 2 and today.day == 14:
            events.append({
                "name": "valentines_day",
                "active": True,
                "bonus": "Двойные XP за рефералов",
            })

        return {
            "date": today.isoformat(),
            "active_events": events,
            "total_events": len(events),
        }

    try:
        return asyncio.run(_check_async())
    except Exception as e:
        logger.error(f"check_seasonal_events failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True, base=BaseTask, name="gamification:award_daily_login_bonus", queue="gamification")
def award_daily_login_bonus(self, user_id: int) -> dict[str, Any]:
    """
    Начислить бонус за ежедневный вход.
    Вызывается при каждом входе пользователя.

    Args:
        user_id: ID пользователя.

    Returns:
        Статистика начисления.
    """
    logger.info(f"Awarding daily login bonus to user {user_id}")

    async def _award_async() -> dict[str, Any]:
        from src.core.services.xp_service import xp_service
        from src.db.models.user import User

        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return {"error": "User not found"}

            # Проверяем последний вход
            today = date.today()
            last_login = user.updated_at.date() if user.updated_at else None

            if last_login == today:
                # Уже получал бонус сегодня
                return {"already_awarded": True}

            # Начисляем XP за вход
            level_up = await xp_service.add_xp(
                user_id=user_id,
                amount=10,  # +10 XP за ежедневный вход
                reason="daily_login",
            )

            # Обновляем last_login
            user.updated_at = datetime.now(UTC)
            await session.flush()

            return {
                "success": True,
                "xp_awarded": 10,
                "level_up": level_up is not None,
                "streak_days": user.login_streak_days or 0,
            }

    try:
        return asyncio.run(_award_async())
    except Exception as e:
        logger.error(f"award_daily_login_bonus failed: {e}")
        return {"status": "error", "error": str(e)}
