"""
Billing Service для управления платежами и балансом.
Работает с кредитами (1 кредит = 1 рублю).
"""

import logging
import uuid
from datetime import UTC
from decimal import Decimal
from typing import Any

from src.core.services.notification_service import notification_service
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class BillingService:
    """
    Сервис для управления платежами и балансом.

    Методы:
        create_payment: Создать платёж
        check_payment: Проверить статус платежа
        deduct_credits: Списать кредиты
        apply_referral_bonus: Начислить реферальный бонус
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def create_payment(
        self,
        user_id: int,
        amount: Decimal,
        payment_method: str = "yookassa",
    ) -> dict[str, Any]:
        """
        Создать платёж.

        Args:
            user_id: ID пользователя.
            amount: Сумма платежа в рублях (конвертируется в кредиты 1:1).
            payment_method: Метод оплаты.

        Returns:
            Данные платежа (payment_id, payment_url).
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if not user:
                raise ValueError(f"User {user_id} not found")

            # Генерируем payment_id
            payment_id = str(uuid.uuid4())

            # Конвертируем рубли в кредиты (1:1)
            credits_amount = int(amount)

            # Создаём транзакцию со статусом pending
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.TOPUP,
                payment_id=payment_id,
                meta_json={
                    "status": "pending",
                    "method": payment_method,
                    "credits": credits_amount,
                },
            )

            # В production здесь создаём платёж в YooKassa
            # Для now возвращаем заглушку
            payment_url = f"https://yookassa.ru/payment/{payment_id}"

            logger.info(
                f"Payment {payment_id} created for user {user_id}, amount: {amount} RUB = {credits_amount} credits"
            )

            return {
                "payment_id": payment_id,
                "payment_url": payment_url,
                "amount": str(amount),
                "credits": credits_amount,
                "status": "pending",
            }

    async def check_payment(
        self,
        payment_id: str,
        user_id: int,
    ) -> dict[str, Any]:
        """
        Проверить статус платежа.

        Args:
            payment_id: ID платежа.
            user_id: ID пользователя.

        Returns:
            Статус платежа.
        """
        async with async_session_factory() as session:
            transaction_repo = TransactionRepository(session)

            # Ищем транзакцию по payment_id
            transaction = await transaction_repo.find_one(
                Transaction.payment_id == payment_id,
                Transaction.user_id == user_id,
            )

            if not transaction:
                raise ValueError(f"Payment {payment_id} not found")

            # Получаем статус из meta_json
            meta = transaction.meta_json or {}
            status = meta.get("status", "pending")

            # В production здесь проверяем статус в YooKassa
            # Если paid, то зачисляем кредиты на баланс
            credited = meta.get("credited") if meta else None
            if status == "succeeded" and credited is not True:
                # Зачисляем кредиты на баланс (1 рубль = 1 кредит)
                user_repo = UserRepository(session)
                credits_amount = int(transaction.amount)
                await user_repo.update_credits(user_id, credits_amount)

                # Обновляем транзакцию
                meta["credited"] = True
                meta["credits_credited"] = credits_amount
                await transaction_repo.update(transaction.id, {"meta_json": meta})

                logger.info(
                    f"Payment {payment_id} credited: {credits_amount} credits to user {user_id}"
                )

                # Уведомляем пользователя
                await notification_service.notify_low_balance(
                    user_id=user_id,
                    balance=Decimal(credits_amount),
                )

            return {
                "payment_id": payment_id,
                "status": status,
                "amount": str(transaction.amount),
                "credited": meta.get("credited", False),
            }

    async def deduct_credits(
        self,
        user_id: int,
        credits: int,
        description: str = "",
    ) -> bool:
        """
        Списать кредиты с баланса.

        Args:
            user_id: ID пользователя.
            credits: Количество кредитов для списания.
            description: Описание списания.

        Returns:
            True если списание успешно.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Проверяем баланс
            user = await user_repo.get_by_id(user_id)
            if not user:
                return False

            if user.credits < credits:
                logger.warning(
                    f"User {user_id} has insufficient credits: {user.credits} < {credits}"
                )
                return False

            # Списываем кредиты
            await user_repo.update_credits(user_id, -credits)

            # Создаём транзакцию (для истории, в рублях)
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=user_id,
                amount=Decimal(credits),  # 1 кредит = 1 рублю
                transaction_type=TransactionType.SPEND,
                meta_json={"description": description, "credits_spent": credits},
            )

            logger.info(f"Spend {credits} credits from user {user_id}: {description}")

            return True

    async def apply_referral_bonus(
        self,
        referrer_id: int,
        referred_user_id: int,
        bonus_amount: Decimal,
    ) -> bool:
        """
        Начислить реферальный бонус.

        Args:
            referrer_id: ID пригласившего.
            referred_user_id: ID приглашённого.
            bonus_amount: Сумма бонуса в рублях (конвертируется в кредиты 1:1).

        Returns:
            True если бонус начислен.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Проверяем реферера
            referrer = await user_repo.get_by_id(referrer_id)
            if not referrer:
                return False

            # Начисляем бонус в кредитах (1 рубль = 1 кредит)
            bonus_credits = int(bonus_amount)
            await user_repo.update_credits(referrer_id, bonus_credits)

            # Создаём транзакцию
            transaction_repo = TransactionRepository(session)
            await transaction_repo.create_transaction(
                user_id=referrer_id,
                amount=bonus_amount,
                transaction_type=TransactionType.BONUS,
                payment_id=None,
                meta_json={
                    "type": "referral_bonus",
                    "referred_user_id": referred_user_id,
                    "bonus_credits": bonus_credits,
                },
            )

            logger.info(f"Referral bonus {bonus_credits} credits to user {referrer_id}")

            # Уведомляем
            await notification_service.notify_referral_bonus(
                user_id=referrer_id,
                bonus_amount=bonus_amount,
                referred_user_id=referred_user_id,
            )

            return True

    async def activate_plan(self, user_id: int, plan: str) -> bool:
        """
        Активировать тариф пользователя.

        Логика:
        1. Получить цену тарифа из settings (tariff_cost_*)
        2. Проверить user.credits >= plan_price
        3. Атомарно (session.begin()):
           - Списать credits
           - Установить user.plan = plan
           - Установить user.plan_expires_at = now() + 30 дней
           - Создать Transaction(type="plan_purchase")
        4. Вернуть True при успехе, False при недостатке средств

        Args:
            user_id: ID пользователя в БД.
            plan: Название тарифа (starter, pro, business).

        Returns:
            True если тариф активирован, False при недостатке средств.
        """
        from datetime import datetime, timedelta

        from sqlalchemy import select

        from src.config.settings import settings
        from src.db.models.transaction import Transaction
        from src.db.models.user import User, UserPlan

        # 1. Получить цену тарифа
        plan_prices = {
            "free": settings.tariff_cost_free,
            "starter": settings.tariff_cost_starter,
            "pro": settings.tariff_cost_pro,
            "business": settings.tariff_cost_business,
            "admin": settings.tariff_cost_admin,
        }
        plan_price = plan_prices.get(plan.lower(), 0)

        async with async_session_factory() as session, session.begin():
            # 2. Получить пользователя с блокировкой
            stmt = select(User).where(User.id == user_id).with_for_update()
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found for plan activation")
                return False

            # Для FREE тарифа — просто активируем без списания
            if plan.lower() == "free":
                user.plan = UserPlan.FREE
                user.plan_expires_at = None
                user.ai_generations_used = 0
                logger.info(f"User {user_id} activated FREE plan")
                return True

            # 3. Проверить баланс
            if user.credits < plan_price:
                logger.warning(
                    f"User {user_id} has insufficient credits: {user.credits} < {plan_price}"
                )
                return False

            try:
                # 4. Атомарно: списать кредиты, установить тариф, создать транзакцию
                user.credits -= plan_price
                user.plan = UserPlan(plan.lower())
                user.plan_expires_at = datetime.now(UTC) + timedelta(days=30)
                user.ai_generations_used = 0

                # Создать транзакцию
                transaction = Transaction(
                    user_id=user.id,
                    amount=Decimal(str(plan_price)),
                    type="spend",
                    payment_id=None,
                    meta_json={
                        "type": "plan_purchase",
                        "plan": plan.lower(),
                        "credits_spent": plan_price,
                    },
                    balance_before=Decimal(str(user.credits + plan_price)),
                    balance_after=Decimal(str(user.credits)),
                    created_at=datetime.now(UTC),
                )
                session.add(transaction)

                # session.begin() автоматически commit
                logger.info(
                    f"User {user_id} activated {plan.upper()} plan for {plan_price} credits"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to activate plan {plan} for user {user_id}: {e}")
                return False


# ─────────────────────────────────────────────
# Реферальная программа (Спринт 4)
# ─────────────────────────────────────────────

    async def apply_referral_signup_bonus(
        self,
        referrer_id: int,
        referred_user_id: int,
    ) -> dict[str, Any]:
        """
        Начислить бонус за регистрацию реферала.

        PRD §9.3: +50 XP пригласившему за регистрацию.

        Args:
            referrer_id: ID пригласившего.
            referred_user_id: ID приглашённого.

        Returns:
            dict с результатом начисления.
        """
        from src.core.services.xp_service import XPService

        xp_service = XPService()

        async with async_session_factory() as session:
            from src.db.models.user import User

            referrer = await session.get(User, referrer_id)
            if not referrer:
                return {"error": "Referrer not found"}

            # Начисляем XP
            level_up = await xp_service.add_xp(
                user_id=referrer_id,
                amount=50,  # +50 XP за регистрацию реферала
                reason="referral_signup",
            )

            return {
                "success": True,
                "xp_awarded": 50,
                "level_up": level_up is not None,
                "new_level": referrer.level + (1 if level_up else 0),
            }

    async def apply_referral_first_campaign_bonus(
        self,
        referrer_id: int,
        referred_user_id: int,
        campaign_id: int,
    ) -> dict[str, Any]:
        """
        Начислить бонус за первую кампанию реферала.

        PRD §9.3: +100 XP пригласившему за первую кампанию реферала.

        Args:
            referrer_id: ID пригласившего.
            referred_user_id: ID приглашённого.
            campaign_id: ID первой кампании.

        Returns:
            dict с результатом начисления.
        """
        from src.core.services.xp_service import XPService

        xp_service = XPService()

        async with async_session_factory() as session:
            from src.db.models.user import User

            referrer = await session.get(User, referrer_id)
            if not referrer:
                return {"error": "Referrer not found"}

            # Начисляем XP
            level_up = await xp_service.add_xp(
                user_id=referrer_id,
                amount=100,  # +100 XP за первую кампанию реферала
                reason="referral_first_campaign",
            )

            # Также начисляем кредиты (100 кр)
            user_repo = UserRepository(session)
            await user_repo.update_credits(referrer_id, 100)

            return {
                "success": True,
                "xp_awarded": 100,
                "credits_awarded": 100,
                "level_up": level_up is not None,
                "new_level": referrer.level + (1 if level_up else 0),
            }

    async def get_referral_stats(self, user_id: int) -> dict[str, Any]:
        """
        Получить статистику рефералов пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            dict с total_referrals, total_earned, referrals_list.
        """
        from typing import cast

        from sqlalchemy import func, select

        from src.db.models.user import User

        async with async_session_factory() as session:
            # Считаем количество рефералов
            stmt = (
                select(func.count(User.id))
                .where(User.referred_by_id == user_id)
            )
            result = await session.execute(stmt)
            total_referrals = result.scalar_one() or 0

            # Получаем список рефералов
            stmt = (
                select(User)
                .where(User.referred_by_id == user_id)
                .order_by(User.created_at.desc())
                .limit(10)
            )
            result = await session.execute(stmt)
            referrals = cast(list[User], list(result.scalars().all()))

            referrals_list: list[dict] = [
                {
                    "telegram_id": r.telegram_id,
                    "username": r.username,
                    "first_name": r.first_name,
                    "registered_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in referrals
            ]

            return {
                "user_id": user_id,
                "total_referrals": total_referrals,
                "referrals": referrals_list,
                "total_earned": 0,  # Placeholder для будущей статистики
            }

    async def freeze_campaign_funds(self, campaign_id: int) -> bool:
        """
        Заморозить средства кампании на эскроу.

        Логика:
        1. Получить кампанию из БД
        2. Проверить что у пользователя хватает credits >= campaign.cost
        3. Списать credits с user.credits
        4. Установить campaign.status = "queued"
        5. Создать запись Transaction(type="escrow_freeze", amount=campaign.cost)
        6. Вернуть True при успехе, False при недостатке средств

        Args:
            campaign_id: ID кампании.

        Returns:
            True если средства заморожены, False при недостатке средств.
        """
        from datetime import datetime

        from sqlalchemy import select

        from src.db.models.campaign import Campaign, CampaignStatus
        from src.db.models.transaction import Transaction
        from src.db.models.user import User

        async with async_session_factory() as session, session.begin():
            # 1. Получить кампанию с блокировкой (FOR UPDATE)
            stmt = select(Campaign).where(Campaign.id == campaign_id).with_for_update()
            result = await session.execute(stmt)
            campaign = result.scalar_one_or_none()
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return False

            # 2. Получить пользователя с блокировкой
            stmt = select(User).where(User.id == campaign.user_id).with_for_update()
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                logger.error(f"User {campaign.user_id} not found for campaign {campaign_id}")
                return False

            # 3. Проверить баланс
            if user.credits < campaign.cost:
                logger.warning(
                    f"User {user.id} has insufficient credits: {user.credits} < {campaign.cost}"
                )
                return False

            try:
                # 4. Все три операции атомарно (внутри session.begin())
                user.credits -= int(campaign.cost)
                campaign.status = CampaignStatus.QUEUED

                # Создать транзакцию напрямую через session.add
                transaction = Transaction(
                    user_id=user.id,
                    amount=Decimal(str(campaign.cost)),
                    type="spend",
                    payment_id=None,
                    meta_json={
                        "type": "escrow_freeze",
                        "campaign_id": campaign_id,
                        "credits_frozen": int(campaign.cost),
                    },
                    balance_before=Decimal(str(user.credits + int(campaign.cost))),
                    balance_after=Decimal(str(user.credits)),
                    created_at=datetime.now(UTC),
                )
                session.add(transaction)

                # session.begin() автоматически commit при выходе без исключений
                logger.info(
                    f"Frozen {campaign.cost} credits for campaign {campaign_id} (user {user.id})"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to freeze funds for campaign {campaign_id}: {e}")
                # session.begin() автоматически rollback при исключении
                return False

    async def release_escrow_funds(self, placement_id: int) -> bool:
        """
        Освободить средства после подтверждённой публикации.

        Логика:
        1. Получить placement из БД (с campaign и channel owner)
        2. Рассчитать: owner_amount = placement.cost * 0.80
        3. Начислить owner_amount на credits владельца канала
        4. Создать Transaction(type="escrow_release") для владельца
        5. Вернуть True

        Args:
            placement_id: ID размещения (mailing_log.id).

        Returns:
            True если средства освобождены.
        """
        from datetime import datetime
        from decimal import Decimal

        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat
        from src.db.models.mailing_log import MailingLog, MailingStatus
        from src.db.models.transaction import Transaction
        from src.db.models.user import User

        async with async_session_factory() as session:
            async with session.begin():
                # 1. Получить placement с блокировкой
                stmt = select(MailingLog).where(MailingLog.id == placement_id).with_for_update()
                result = await session.execute(stmt)
                placement = result.scalar_one_or_none()
                if not placement:
                    logger.error(f"Placement {placement_id} not found")
                    return False

                # ⚠️ ИДЕМПОТЕНТНОСТЬ: не начислять повторно
                if placement.status == MailingStatus.PAID:
                    logger.warning(f"release_escrow_funds: placement {placement_id} already paid, skipping")
                    return True  # не ошибка, просто уже сделано

                if placement.status != MailingStatus.SENT:
                    logger.error(f"release_escrow_funds: unexpected status {placement.status} for placement {placement_id}")
                    return False

                # 2. Получить канал и владельца с блокировкой
                stmt = select(TelegramChat).where(TelegramChat.id == placement.chat_id).with_for_update()
                result = await session.execute(stmt)
                chat = result.scalar_one_or_none()
                if not chat or not chat.owner_user_id:
                    logger.error(f"Channel or owner not found for placement {placement_id}")
                    return False

                stmt = select(User).where(User.id == chat.owner_user_id).with_for_update()
                result = await session.execute(stmt)
                owner = result.scalar_one_or_none()
                if not owner:
                    logger.error(f"Owner not found for placement {placement_id}")
                    return False

                # 3. Расчёт с Decimal и quantize для округления
                owner_amount = (
                    Decimal(str(placement.cost)) * Decimal("0.80")
                ).quantize(Decimal("0.01"))
                platform_fee = (
                    Decimal(str(placement.cost)) * Decimal("0.20")
                ).quantize(Decimal("0.01"))

                # Проверка на ноль
                if owner_amount <= 0:
                    logger.warning(f"release_escrow_funds: zero cost for placement {placement_id}")
                    return False

                try:
                    # 4. Начислить и сменить статус атомарно
                    owner.credits += int(owner_amount)
                    placement.status = MailingStatus.PAID

                    # Создать транзакцию напрямую
                    transaction = Transaction(
                        user_id=owner.id,
                        amount=owner_amount,
                        type="bonus",
                        payment_id=None,
                        meta_json={
                            "type": "escrow_release",
                            "placement_id": placement_id,
                            "campaign_id": placement.campaign_id,
                            "channel_id": chat.id,
                            "owner_amount": float(owner_amount),
                            "platform_fee": float(platform_fee),
                        },
                        balance_before=Decimal(str(owner.credits - int(owner_amount))),
                        balance_after=Decimal(str(owner.credits)),
                        created_at=datetime.now(UTC),
                    )
                    session.add(transaction)

                    # TASK 2: Создать запись Payout для истории выплат
                    from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus

                    payout = Payout(
                        owner_id=owner.id,
                        channel_id=chat.id,
                        placement_id=placement_id,
                        amount=Decimal(str(owner_amount)),
                        platform_fee=Decimal(str(platform_fee)),
                        currency=PayoutCurrency.RUB,  # Внутренняя валюта платформы
                        status=PayoutStatus.PAID,  # Автоматическая выплата
                        paid_at=datetime.now(UTC),
                    )
                    session.add(payout)

                    # session.begin() автоматически commit
                    logger.info(
                        f"Released {owner_amount} credits to owner {owner.id} for placement {placement_id} (payout {payout.id})"
                    )
                    return True

                except Exception as e:
                    logger.error(f"Failed to release escrow funds for placement {placement_id}: {e}")
                    return False

    async def refund_failed_placement(self, placement_id: int) -> bool:
        """
        Возврат средств за несостоявшееся размещение.

        Логика:
        1. Получить placement, убедиться что status == "failed"
        2. Получить campaign.user (рекламодатель)
        3. Начислить placement.cost на user.credits
        4. Создать Transaction(type="refund", amount=placement.cost)
        5. Отправить уведомление пользователю

        Args:
            placement_id: ID размещения (mailing_log.id).

        Returns:
            True если возврат успешен.
        """
        from datetime import datetime

        from sqlalchemy import select

        from src.db.models.campaign import Campaign
        from src.db.models.mailing_log import MailingLog, MailingStatus
        from src.db.models.transaction import Transaction
        from src.db.models.user import User

        async with async_session_factory() as session:
            async with session.begin():
                # 1. Получить placement с блокировкой
                stmt = select(MailingLog).where(MailingLog.id == placement_id).with_for_update()
                result = await session.execute(stmt)
                placement = result.scalar_one_or_none()
                if not placement:
                    logger.error(f"Placement {placement_id} not found")
                    return False

                # Проверить статус
                if placement.status != MailingStatus.FAILED:
                    logger.warning(f"Placement {placement_id} status is not FAILED ({placement.status})")
                    return False

                # ⚠️ ИДЕМПОТЕНТНОСТЬ: проверить флаг возврата
                meta = placement.meta_json or {}
                if meta.get("refund_sent"):
                    logger.warning(f"refund_failed_placement: already refunded for placement {placement_id}")
                    return True  # уже возвращено

                # 2. Получить кампанию и рекламодателя
                stmt = select(Campaign).where(Campaign.id == placement.campaign_id).with_for_update()
                result = await session.execute(stmt)
                campaign = result.scalar_one_or_none()
                if not campaign:
                    logger.error(f"Campaign {placement.campaign_id} not found")
                    return False

                stmt = select(User).where(User.id == campaign.user_id).with_for_update()
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if not user:
                    logger.error(f"User {campaign.user_id} not found for refund")
                    return False

                try:
                    # 3. Вернуть средства + установить флаг атомарно
                    refund_amount = Decimal(str(placement.cost))
                    user.credits += int(refund_amount)

                    # Установить флаг что возврат отправлен
                    meta["refund_sent"] = True
                    meta["refund_at"] = datetime.now(UTC).isoformat()
                    placement.meta_json = meta

                    # 4. Создать транзакцию возврата
                    transaction = Transaction(
                        user_id=user.id,
                        amount=refund_amount,
                        type="refund",
                        payment_id=None,
                        meta_json={
                            "type": "refund",
                            "placement_id": placement_id,
                            "campaign_id": placement.campaign_id,
                            "reason": "failed_placement",
                        },
                        balance_before=Decimal(str(user.credits - int(refund_amount))),
                        balance_after=Decimal(str(user.credits)),
                        created_at=datetime.now(UTC),
                    )
                    session.add(transaction)

                    # session.begin() автоматически commit
                    logger.info(
                        f"Refunded {refund_amount} credits to advertiser {user.id} for placement {placement_id}"
                    )

                    # Сохраняем данные для уведомления (после коммита)
                    user_telegram_id = user.telegram_id
                    campaign_title = campaign.title or f"Кампания #{campaign.id}"

                except Exception as e:
                    logger.error(f"Failed to refund placement {placement_id}: {e}")
                    return False

        # 5. Уведомление ПОСЛЕ коммита транзакции (не внутри begin())
        try:
            from src.tasks.notification_tasks import notify_user

            notify_user.delay(
                telegram_id=user_telegram_id,
                message=(
                    f"💰 Возврат средств\n\n"
                    f"Кампания: {campaign_title}\n"
                    f"Сумма: {int(refund_amount)} кр\n"
                    f"Средства зачислены на баланс."
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"refund_failed_placement: notification failed for placement {placement_id}: {e}")
            # Не падаем — деньги уже вернули

        return True


# Глобальный экземпляр
billing_service = BillingService()
