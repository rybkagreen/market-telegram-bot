"""
Celery задачи для биллинга: продление тарифов, проверка платежей.
"""

import logging
from datetime import UTC, datetime, timedelta

from src.db.models.crypto_payment import CryptoPayment, PaymentStatus
from src.db.models.user import User, UserPlan
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.celery_app import app

logger = logging.getLogger(__name__)

# Стоимость тарифов в кредитах
PLAN_COSTS = {
    UserPlan.STARTER: 299,
    UserPlan.PRO: 999,
    UserPlan.BUSINESS: 2999,
}


@app.task(name="tasks.billing_tasks:check_plan_renewals")
def check_plan_renewals() -> dict:
    """
    Проверить истекающие тарифы и продлить/понизить.

    Запускается ежедневно в 03:00 UTC через Celery Beat.

    Логика:
    - Если plan_expires_at <= now() → пытаемся списать кредиты
    - Кредитов хватает → продляем на 30 дней
    - Кредитов не хватает → план → FREE, уведомление
    """
    import asyncio

    return asyncio.get_event_loop().run_until_complete(_check_plan_renewals())


async def _check_plan_renewals() -> dict:
    """Асинхронная реализация проверки продлений."""
    renewed = 0
    downgraded = 0

    async with async_session_factory() as session:
        user_repo = UserRepository(session)

        # Получаем всех пользователей с истёкшим или истекающим тарифом
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(
                User.plan != UserPlan.FREE,
                User.plan_expires_at <= datetime.now(UTC) + timedelta(hours=1),
            )
        )
        users = result.scalars().all()

        for user in users:
            plan_cost = PLAN_COSTS.get(user.plan, 0)

            if user.credits >= plan_cost:
                # Списываем кредиты и продляем
                try:
                    await user_repo.update_credits(user.id, -plan_cost)
                    await user_repo.reset_ai_usage(user.id)
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
                        f"plan={user.plan.value}, cost={plan_cost}"
                    )
                except Exception as e:
                    logger.error(f"Failed to renew plan for user {user.telegram_id}: {e}")
            else:
                # Недостаточно кредитов — понижаем до FREE
                await user_repo.expire_plan(user.id)
                logger.warning(
                    f"Plan expired: user={user.telegram_id}, "
                    f"had {user.credits} credits, needed {plan_cost}"
                )
                downgraded += 1
                # TODO: отправить уведомление пользователю через бота

    return {"renewed": renewed, "downgraded": downgraded}


@app.task(name="tasks.billing_tasks:check_pending_invoices")
def check_pending_invoices() -> dict:
    """
    Проверить неоплаченные счета CryptoBot и зачислить кредиты.
    Запускается каждые 5 минут.
    """
    import asyncio

    return asyncio.get_event_loop().run_until_complete(_check_pending_invoices())


async def _check_pending_invoices() -> dict:
    """Асинхронная реализация проверки инвойсов."""
    from sqlalchemy import select, update

    from src.core.services.cryptobot_service import cryptobot_service

    credited = 0
    expired_count = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(CryptoPayment).where(
                CryptoPayment.status == PaymentStatus.PENDING,
                CryptoPayment.method == "cryptobot",
            )
        )
        payments = result.scalars().all()

        for payment in payments:
            try:
                if not payment.invoice_id:
                    continue

                invoice = await cryptobot_service.get_invoice(payment.invoice_id)

                if invoice.status == "paid":
                    # Зачисляем кредиты
                    user_repo = UserRepository(session)
                    total_credits = payment.credits + payment.bonus_credits
                    await user_repo.update_credits(payment.user_id, total_credits)

                    await session.execute(
                        update(CryptoPayment)
                        .where(CryptoPayment.id == payment.id)
                        .values(
                            status=PaymentStatus.PAID,
                            credited_at=datetime.now(UTC),
                        )
                    )
                    await session.commit()
                    credited += 1
                    logger.info(f"Credits awarded: payment={payment.id}, credits={total_credits}")

                elif invoice.status in ("expired", "cancelled"):
                    from sqlalchemy import update

                    await session.execute(
                        update(CryptoPayment)
                        .where(CryptoPayment.id == payment.id)
                        .values(status=PaymentStatus(invoice.status))
                    )
                    await session.commit()
                    expired_count += 1

            except Exception as e:
                logger.error(f"Failed to check invoice {payment.invoice_id}: {e}")

    return {"credited": credited, "expired": expired_count}
