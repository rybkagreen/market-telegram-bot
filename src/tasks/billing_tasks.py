"""
Celery задачи для биллинга: продление тарифов, проверка платежей.

Использует asyncio.run() для запуска async кода в синхронных Celery задачах.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from src.constants.tariffs import TARIFF_CREDIT_COST
from src.db.models.user import User, UserPlan
from src.db.repositories.user_repo import UserRepository
from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="billing:check_plan_renewals", queue="billing")
def check_plan_renewals() -> dict:
    """
    Проверить истекающие тарифы и продлить/понизить.

    Запускается ежедневно в 03:00 UTC через Celery Beat.

    Логика:
    - Если plan_expires_at <= now() → пытаемся списать кредиты
    - Кредитов хватает → продляем на 30 дней
    - Кредитов не хватает → план → FREE, уведомление
    """
    return asyncio.run(_check_plan_renewals())


async def _check_plan_renewals() -> dict:
    """Асинхронная реализация проверки продлений."""
    renewed = 0
    downgraded = 0

    async with async_session_factory() as session:
        user_repo = UserRepository(session)

        # Получаем всех пользователей с истёкшим или истекающим тарифом
        # ADMIN тариф не продлеваем автоматически — он бесплатный и постоянный
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(
                User.plan != UserPlan.FREE,
                User.plan != UserPlan.ADMIN,  # ADMIN не продлеваем
                User.plan_expires_at <= datetime.now(UTC) + timedelta(hours=1),
            )
        )
        users = result.scalars().all()

        for user in users:
            # Конвертируем plan.value в строку для TARIFF_CREDIT_COST
            plan_key = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
            plan_cost = TARIFF_CREDIT_COST.get(plan_key, 0)

            if user.credits >= plan_cost:
                # Списываем кредиты и продляем
                try:
                    await user_repo.update_credits(user.id, -plan_cost)
                    from sqlalchemy import update as _update
                    await session.execute(
                        _update(User).where(User.id == user.id).values(ai_uses_count=0)
                    )
                    from sqlalchemy import update

                    await session.execute(
                        update(User)
                        .where(User.id == user.id)
                        .values(plan_expires_at=datetime.now(UTC) + timedelta(days=30))
                    )
                    await session.commit()
                    renewed += 1
                    logger.info(
                        f"Plan renewed: user={user.telegram_id}, "
                        f"plan={user.plan}, cost={plan_cost}"
                    )

                    # Отправляем уведомление об успешном продлении
                    try:
                        from src.db.models.notification import NotificationType
                        from src.tasks.notification_tasks import notify_user

                        plan_name = plan_key.upper()
                        new_expires = datetime.now(UTC) + timedelta(days=30)
                        message = (
                            f"✅ <b>Тариф продлён</b>\n\n"
                            f"Ваш тариф <b>{plan_name}</b> успешно продлён.\n"
                            f"Списано кредитов: <b>{plan_cost}</b>\n"
                            f"Действует до: <b>{new_expires.strftime('%d.%m.%Y')}</b>\n\n"
                            f"Спасибо что остаётесь с нами!"
                        )

                        notify_user.delay(
                            telegram_id=user.telegram_id,
                            message=message,
                            notification_type=NotificationType.PLAN_RENEWED.value,
                            parse_mode="HTML",
                        )
                    except Exception as notify_err:
                        logger.error(f"Failed to send plan renewed notification: {notify_err}")

                except Exception as e:
                    logger.error(f"Failed to renew plan for user {user.telegram_id}: {e}")
            else:
                # Недостаточно кредитов — понижаем до FREE
                from sqlalchemy import update as _update
                await session.execute(
                    _update(User).where(User.id == user.id).values(
                        plan="free", plan_expires_at=None, ai_uses_count=0
                    )
                )
                await session.commit()
                logger.warning(
                    f"Plan expired: user={user.telegram_id}, "
                    f"had {user.credits} credits, needed {plan_cost}"
                )
                downgraded += 1

                # Отправляем уведомление о истечении тарифа
                try:
                    from src.db.models.notification import NotificationType
                    from src.tasks.notification_tasks import notify_user

                    plan_name = plan_key.upper()
                    message = (
                        f"⚠️ <b>Тариф не продлён</b>\n\n"
                        f"Ваш тариф <b>{plan_name}</b> истёк.\n"
                        f"Недостаточно кредитов для продления (нужно {plan_cost}, было {user.credits}).\n\n"
                        f"Тариф сброшен на <b>FREE</b>.\n"
                        f"Пополните баланс и продлите тариф в разделе /tariffs."
                    )

                    notify_user.delay(
                        telegram_id=user.telegram_id,
                        message=message,
                        notification_type=NotificationType.PLAN_EXPIRED.value,
                        parse_mode="HTML",
                    )
                except Exception as notify_err:
                    logger.error(f"Failed to send plan expired notification: {notify_err}")

    return {"renewed": renewed, "downgraded": downgraded}


@celery_app.task(name="billing:check_pending_invoices", queue="billing", bind=True)
def check_pending_invoices(self) -> dict:
    """
    Устаревший метод — не используется.
    Запускается каждые 5 минут.
    """
    import asyncio

    # Создаём новый event loop для async операций
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_check_pending_invoices())
        return result
    finally:
        loop.close()


async def _check_pending_invoices() -> dict:
    """Устаревший метод — нечего проверять."""
    return {"credited": 0, "expired": 0}
