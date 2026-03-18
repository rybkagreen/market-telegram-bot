"""
Billing Service для управления платежами и балансом.
Двухвалютная система: рубли (размещения) + кредиты (подписки).
"""

import logging
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.payments import (
    MAX_TOPUP,
    MIN_CAMPAIGN_BUDGET,
    MIN_TOPUP,
    OWNER_SHARE,
    YOOKASSA_FEE_RATE,
)
from src.core.services.notification_service import notification_service
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.platform_account_repo import PlatformAccountRepo
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class InsufficientFundsError(Exception):
    """Недостаточно средств на балансе."""


class BillingService:
    """
    Сервис для управления платежами и балансом.

    Методы:
        create_payment: Создать платёж (пополняет balance_rub)
        check_payment: Проверить статус платежа
        add_balance_rub: Зачислить рубли на баланс
        buy_credits_for_plan: Купить кредиты для тарифа (с balance_rub → credits)
        freeze_escrow: Заморозить рубли для размещения
        release_escrow: Освободить эскроу после удаления поста (ESCROW-001)
        refund_escrow: Возврат средств при отмене
        apply_referral_bonus: Начислить реферальный бонус (в рублях)
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""

    async def add_balance_rub(
        self,
        user_id: int,
        amount_rub: Decimal,
        payment_method: str = "yookassa",
        payment_id: str | None = None,
    ) -> Transaction:
        """
        Зачислить рубли на balance_rub пользователя.

        Args:
            user_id: ID пользователя.
            amount_rub: Сумма в рублях.
            payment_method: Метод оплаты.
            payment_id: ID платежа.

        Returns:
            Транзакция пополнения.
        """
        from src.db.models.transaction import Transaction

        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if not user:
                raise ValueError(f"User {user_id} not found")

            balance_before = user.balance_rub
            user.balance_rub += amount_rub

            transaction = Transaction(
                user_id=user_id,
                amount=amount_rub,
                type=TransactionType.TOPUP,
                payment_id=payment_id,
                description=f"Пополнение через {payment_method}",
                meta_json={
                    "method": payment_method,
                    "currency": "rub",
                },
                balance_before=balance_before,
                balance_after=user.balance_rub,
                created_at=datetime.now(UTC),
            )
            session.add(transaction)
            await session.flush()

            logger.info(
                f"Balance topped up: +{amount_rub} ₽ for user {user_id}, new balance: {user.balance_rub} ₽"
            )

            return transaction

    async def buy_credits_for_plan(
        self,
        user_id: int,
        amount_rub: Decimal,
    ) -> tuple[int, Transaction, Transaction]:
        """
        Купить кредиты для тарифа с рублёвого баланса.

        Args:
            user_id: ID пользователя.
            amount_rub: Сумма в рублях (списывается с balance_rub).

        Returns:
            Кортеж (credits_purchased, spend_transaction, topup_transaction).

        Raises:
            InsufficientFundsError: Если недостаточно balance_rub.
        """
        from src.config.settings import settings
        from src.db.models.transaction import Transaction

        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if not user:
                raise ValueError(f"User {user_id} not found")

            # Проверка баланса
            if user.balance_rub < amount_rub:
                raise InsufficientFundsError(
                    f"Insufficient balance_rub: {user.balance_rub} < {amount_rub}"
                )

            # Конвертация: 1 кредит = 1 рубль (v4.2)
            credits_to_add = int(amount_rub * Decimal(str(settings.credits_per_rub_for_plan)))

            # Списываем рубли
            balance_rub_before = user.balance_rub
            user.balance_rub -= amount_rub

            spend_transaction = Transaction(
                user_id=user_id,
                amount=amount_rub,
                type=TransactionType.SPEND,
                payment_id=None,
                description=f"Покупка {credits_to_add} кр для тарифа",
                meta_json={
                    "type": "buy_credits",
                    "currency": "rub",
                },
                balance_before=balance_rub_before,
                balance_after=user.balance_rub,
                created_at=datetime.now(UTC),
            )
            session.add(spend_transaction)

            # Зачисляем кредиты
            credits_before = user.credits
            user.credits += credits_to_add

            topup_transaction = Transaction(
                user_id=user_id,
                amount=Decimal(str(credits_to_add)),
                type=TransactionType.BONUS,
                payment_id=None,
                description=f"Начислено {credits_to_add} кр за {amount_rub} ₽",
                meta_json={
                    "type": "credits_purchase",
                    "currency": "credits",
                },
                balance_before=Decimal(str(credits_before)),
                balance_after=Decimal(str(user.credits)),
                created_at=datetime.now(UTC),
            )
            session.add(topup_transaction)

            await session.flush()

            logger.info(
                f"Credits purchased: {credits_to_add} кр for {amount_rub} ₽ by user {user_id}"
            )

            return credits_to_add, spend_transaction, topup_transaction

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
        Начислить реферальный бонус в рублях на balance_rub.

        Args:
            referrer_id: ID пригласившего.
            referred_user_id: ID приглашённого.
            bonus_amount: Сумма бонуса в рублях.

        Returns:
            True если бонус начислен.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Проверяем реферера
            referrer = await user_repo.get_by_id(referrer_id)
            if not referrer:
                return False

            # Начисляем бонус в рублях на balance_rub
            balance_before = referrer.balance_rub
            referrer.balance_rub += bonus_amount

            # Создаём транзакцию напрямую (не через repository.create_transaction)
            transaction = Transaction(
                user_id=referrer_id,
                amount=bonus_amount,
                type=TransactionType.BONUS,
                payment_id=None,
                description=f"Реферальный бонус за пользователя {referred_user_id}",
                meta_json={
                    "type": "referral_bonus",
                    "referred_user_id": referred_user_id,
                    "bonus_rub": float(bonus_amount),
                    "currency": "rub",
                },
                balance_before=balance_before,
                balance_after=referrer.balance_rub,
                created_at=datetime.now(UTC),
            )
            session.add(transaction)

            logger.info(
                f"Referral bonus {bonus_amount} ₽ to user {referrer_id}, new balance: {referrer.balance_rub} ₽"
            )

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
            stmt = select(func.count(User.id)).where(User.referred_by_id == user_id)
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
            if user is None:
                logger.error(f"User {campaign.user_id} not found for campaign {campaign_id}")
                return False

            # Type guard: user is guaranteed to be User here
            assert isinstance(user, User), "user must be User instance"

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

        async with async_session_factory() as session, session.begin():
            # 1. Получить placement с блокировкой
            stmt = select(MailingLog).where(MailingLog.id == placement_id).with_for_update()
            result = await session.execute(stmt)
            placement = result.scalar_one_or_none()
            if not placement:
                logger.error(f"Placement {placement_id} not found")
                return False

            # Проверить статус
            if placement.status != MailingStatus.FAILED:
                logger.warning(
                    f"Placement {placement_id} status is not FAILED ({placement.status})"
                )
                return False

            # ⚠️ ИДЕМПОТЕНТНОСТЬ: проверить флаг возврата
            meta = placement.meta_json or {}
            if meta.get("refund_sent"):
                logger.warning(
                    f"refund_failed_placement: already refunded for placement {placement_id}"
                )
                return True  # уже возвращено

            # 2. Получить кампанию и рекламодателя
            stmt = select(Campaign).where(Campaign.id == placement.campaign_id).with_for_update()
            result = await session.execute(stmt)
            campaign: Campaign | None = result.scalar_one_or_none()
            if campaign is None:
                logger.error(f"Campaign {placement.campaign_id} not found")
                return False

            stmt = select(User).where(User.id == campaign.user_id).with_for_update()
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                logger.error(f"User {campaign.user_id} not found for refund")
                return False

            # Type guard: user is guaranteed to be User here
            assert isinstance(user, User), "user must be User instance"

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
            logger.error(
                f"refund_failed_placement: notification failed for placement {placement_id}: {e}"
            )
            # Не падаем — деньги уже вернули

        return True

    # ─────────────────────────────────────────────
    # Методы для PlacementRequest (Этап 2)
    # ─────────────────────────────────────────────

    async def refund_escrow_credits(
        self,
        placement_id: int,
        advertiser_id: int,
        amount: Decimal,
    ) -> bool:
        """
        Вернуть средства из эскроу рекламодателю (в credits).

        Args:
            placement_id: ID заявки.
            advertiser_id: ID рекламодателя.
            amount: Сумма для возврата.

        Returns:
            True если возврат успешен.
        """
        from src.db.models.transaction import Transaction

        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(advertiser_id)

            if not user:
                logger.error(f"User {advertiser_id} not found for escrow refund")
                return False

            # Начисление средств
            user.credits += int(amount)

            # Создание транзакции
            transaction = Transaction(
                user_id=advertiser_id,
                amount=amount,
                type=TransactionType.ESCROW_RELEASE,
                payment_id=None,
                meta_json={
                    "type": "escrow_refund",
                    "placement_id": placement_id,
                },
                balance_before=Decimal(str(user.credits - int(amount))),
                balance_after=Decimal(str(user.credits)),
                created_at=datetime.now(UTC),
            )
            session.add(transaction)
            await session.flush()

            logger.info(
                f"Escrow refunded: {amount} credits to advertiser {advertiser_id} for placement {placement_id}"
            )

            return True

    async def freeze_escrow_for_placement(
        self,
        placement_id: int,
        advertiser_id: int,
        amount: Decimal,
    ) -> "Transaction":
        """
        Заблокировать средства для PlacementRequest.
        1. Проверить balance_rub рекламодателя
        2. Списать amount с balance_rub
        3. Создать Transaction(type=escrow_freeze, amount=amount)

        Args:
            placement_id: ID заявки.
            advertiser_id: ID рекламодателя.
            amount: Сумма для блокировки (в рублях).

        Returns:
            Транзакция эскроу.

        Raises:
            InsufficientFundsError: Если недостаточно balance_rub.
        """
        from src.db.models.transaction import Transaction

        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(advertiser_id)

            if not user:
                raise ValueError(f"User {advertiser_id} not found")

            # Проверка баланса (balance_rub для размещений)
            if user.balance_rub < amount:
                raise InsufficientFundsError(
                    f"Insufficient balance_rub: {user.balance_rub} < {amount}"
                )

            # Списание средств с balance_rub
            balance_before = user.balance_rub
            user.balance_rub -= amount

            # Создание транзакции
            transaction = Transaction(
                user_id=advertiser_id,
                amount=amount,
                type=TransactionType.ESCROW_FREEZE,
                payment_id=None,
                meta_json={
                    "type": "escrow_freeze",
                    "placement_id": placement_id,
                    "currency": "rub",
                },
                balance_before=balance_before,
                balance_after=user.balance_rub,
                created_at=datetime.now(UTC),
            )
            session.add(transaction)
            await session.flush()

            logger.info(
                f"Escrow frozen: {amount} ₽ from advertiser {advertiser_id} for placement {placement_id}"
            )

            return transaction

    # ══════════════════════════════════════════════════════════════
    # S-05: BillingService v4.2 — новые методы
    # ══════════════════════════════════════════════════════════════

    def calculate_topup_payment(self, desired_balance: Decimal) -> dict[str, Decimal]:
        """
        Рассчитать комиссию и итоговую сумму пополнения.

        Args:
            desired_balance: Желаемая сумма зачисления (desired_balance).

        Returns:
            dict с desired_balance, fee_amount, gross_amount.

        Raises:
            ValueError: Если desired_balance < MIN_TOPUP или > MAX_TOPUP.
        """
        if desired_balance < MIN_TOPUP:
            raise ValueError(f"Минимальное пополнение {MIN_TOPUP} ₽")
        if desired_balance > MAX_TOPUP:
            raise ValueError(f"Максимальное пополнение {MAX_TOPUP} ₽")

        fee_amount = (desired_balance * YOOKASSA_FEE_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross_amount = desired_balance + fee_amount

        return {
            "desired_balance": desired_balance,
            "fee_amount": fee_amount,
            "gross_amount": gross_amount,
        }

    async def process_topup_webhook(
        self,
        session: AsyncSession,
        payment_id: str,
        gross_amount: Decimal,
        metadata: dict,
    ) -> None:
        """
        Обработать вебхук успешного пополнения от ЮKassa.

        Args:
            session: Асинхронная сессия.
            payment_id: ID платежа в ЮKassa.
            gross_amount: Фактически оплаченная сумма (gross).
            metadata: Метаданные платежа (desired_balance, user_id).

        Note:
            Зачислять metadata['desired_balance'] (НЕ gross_amount).
            Разница = комиссия ЮKassa которую уже забрала ЮKassa.
        """
        desired_balance = Decimal(metadata["desired_balance"])
        user_id = int(metadata["user_id"])

        # Идемпотентность: проверить что payment_id не обработан ранее
        txn_repo = TransactionRepository(session)
        existing = await txn_repo.find_one(Transaction.payment_id == payment_id)
        if existing and existing.meta_json and existing.meta_json.get("processed"):
            logger.warning(f"Payment {payment_id} already processed")
            return

        async with session.begin():
            # SELECT FOR UPDATE
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Зачислить desired_balance (НЕ gross_amount!)
            balance_before = user.balance_rub
            user.balance_rub += desired_balance

            # PlatformAccount: total_topups += desired_balance
            platform_repo = PlatformAccountRepo(session)
            await platform_repo.add_to_topups(session, desired_balance)

            # Transaction(type=TOPUP, amount=desired_balance)
            transaction = Transaction(
                user_id=user_id,
                amount=desired_balance,
                type=TransactionType.TOPUP,
                payment_id=payment_id,
                payment_status="succeeded",
                description=f"Пополнение через ЮKassa (payment_id={payment_id})",
                meta_json={
                    "method": "yookassa",
                    "currency": "rub",
                    "gross_amount": str(gross_amount),
                    "processed": True,
                },
                balance_before=balance_before,
                balance_after=user.balance_rub,
            )
            session.add(transaction)
            await session.flush()

            logger.info(
                f"Topup webhook processed: +{desired_balance} ₽ for user {user_id}, "
                f"payment_id={payment_id}, gross={gross_amount} ₽"
            )

    async def freeze_escrow(
        self,
        session: AsyncSession,
        user_id: int,
        placement_id: int,
        amount: Decimal,
    ) -> None:
        """
        Заморозить средства на эскроу для размещения.

        Args:
            session: Асинхронная сессия.
            user_id: ID рекламодателя.
            placement_id: ID заявки.
            amount: Сумма для заморозки.

        Raises:
            ValueError: Если amount < MIN_CAMPAIGN_BUDGET.
            InsufficientFundsError: Если недостаточно balance_rub.
        """
        if amount < MIN_CAMPAIGN_BUDGET:
            raise ValueError(f"Минимальный бюджет размещения {MIN_CAMPAIGN_BUDGET} ₽")

        async with session.begin():
            # SELECT FOR UPDATE user
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            if user.balance_rub < amount:
                raise InsufficientFundsError(
                    f"Insufficient balance_rub: {user.balance_rub} < {amount}"
                )

            # UPDATE users SET balance_rub = balance_rub - amount
            balance_before = user.balance_rub
            user.balance_rub -= amount

            # platform_account_repo.add_to_escrow(session, amount)
            platform_repo = PlatformAccountRepo(session)
            await platform_repo.add_to_escrow(session, amount)

            # Transaction(type=ESCROW_FREEZE, amount=amount, user_id=user_id)
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                type=TransactionType.ESCROW_FREEZE,
                payment_id=None,
                meta_json={
                    "type": "escrow_freeze",
                    "placement_id": placement_id,
                    "currency": "rub",
                },
                balance_before=balance_before,
                balance_after=user.balance_rub,
            )
            session.add(transaction)
            await session.flush()

            logger.info(
                f"Escrow frozen: {amount} ₽ from advertiser {user_id} for placement {placement_id}"
            )

    async def release_escrow(
        self,
        session: AsyncSession,
        placement_id: int,
        final_price: Decimal,
        advertiser_id: int,
        owner_id: int,
    ) -> None:
        """
        Освободить эскроу при успешной публикации.

        Args:
            session: Асинхронная сессия.
            placement_id: ID заявки.
            final_price: Финальная стоимость размещения.
            advertiser_id: ID рекламодателя.
            owner_id: ID владельца канала.

        Note:
            owner_amount = final_price * OWNER_SHARE (округление ROUND_HALF_UP)
            platform_fee = final_price - owner_amount (остаток, НЕ final_price * 0.15)
        """
        async with session.begin():
            # owner_amount = final_price * OWNER_SHARE (округление)
            owner_amount = (final_price * OWNER_SHARE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            # platform_fee = final_price - owner_amount (остаток)
            platform_fee = final_price - owner_amount

            # UPDATE users SET earned_rub = earned_rub + owner_amount WHERE id = owner_id
            user_repo = UserRepository(session)
            owner = await user_repo.get_by_id(owner_id)
            if not owner:
                raise ValueError(f"Owner {owner_id} not found")

            earned_before = owner.earned_rub
            owner.earned_rub += owner_amount

            # Transaction(type=ESCROW_RELEASE, amount=owner_amount, user_id=owner_id)
            owner_transaction = Transaction(
                user_id=owner_id,
                amount=owner_amount,
                type=TransactionType.ESCROW_RELEASE,
                payment_id=None,
                meta_json={
                    "type": "escrow_release",
                    "placement_id": placement_id,
                    "share": "owner",
                    "currency": "rub",
                },
                balance_before=earned_before,
                balance_after=owner.earned_rub,
            )
            session.add(owner_transaction)

            # platform_account_repo.release_from_escrow(session, amount=final_price, platform_fee=platform_fee)
            platform_repo = PlatformAccountRepo(session)
            await platform_repo.release_from_escrow(session, final_price, platform_fee)

            # Transaction(type=COMMISSION, amount=platform_fee)
            commission_transaction = Transaction(
                user_id=advertiser_id,  # Платформа (условно)
                amount=platform_fee,
                type=TransactionType.COMMISSION,
                payment_id=None,
                meta_json={
                    "type": "commission",
                    "placement_id": placement_id,
                    "share": "platform",
                    "currency": "rub",
                },
                balance_before=Decimal("0"),
                balance_after=platform_fee,
            )
            session.add(commission_transaction)
            await session.flush()

            logger.info(
                f"Escrow released: {owner_amount} ₽ to owner {owner_id} (earned_rub), "
                f"{platform_fee} ₽ commission for placement {placement_id}"
            )

    async def refund_escrow(
        self,
        session: AsyncSession,
        placement_id: int,
        final_price: Decimal,
        advertiser_id: int,
        owner_id: int,
        scenario: str,
    ) -> None:
        """
        Вернуть средства с эскроу при отмене размещения.

        Args:
            session: Асинхронная сессия.
            placement_id: ID заявки.
            final_price: Финальная стоимость размещения.
            advertiser_id: ID рекламодателя.
            owner_id: ID владельца канала.
            scenario: Сценарий отмены ('before_escrow', 'after_escrow_before_confirmation', 'after_confirmation').

        Scenarios:
            before_escrow: advertiser +100%, owner 0%, platform 0%
            after_escrow_before_confirmation: advertiser +100%, owner 0%, platform 0%, reputation -5
            after_confirmation: advertiser +50%, owner +42.5%, platform +7.5%, reputation -20
        """
        async with session.begin():
            if scenario == "before_escrow" or scenario == "after_escrow_before_confirmation":
                # advertiser +100%, owner 0%, platform 0%
                advertiser_refund = final_price
                owner_compensation = Decimal("0")
                platform_share = Decimal("0")

            elif scenario == "after_confirmation":
                # advertiser +50%, owner +42.5%, platform +7.5%
                advertiser_refund = (final_price * Decimal("0.50")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                owner_compensation = (final_price * Decimal("0.425")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                # platform_share = final_price - advertiser_refund - owner_compensation (остаток)
                platform_share = final_price - advertiser_refund - owner_compensation

            else:
                raise ValueError(f"Unknown scenario: {scenario}")

            # UPDATE users SET balance_rub = balance_rub + advertiser_refund WHERE id = advertiser_id
            user_repo = UserRepository(session)
            advertiser = await user_repo.get_by_id(advertiser_id)
            if advertiser:
                advertiser.balance_rub += advertiser_refund

            # UPDATE users SET earned_rub = earned_rub + owner_compensation WHERE id = owner_id
            owner = await user_repo.get_by_id(owner_id)
            if owner and owner_compensation > 0:
                owner.earned_rub += owner_compensation

            # platform_account: escrow_reserved -= final_price, profit_accumulated += platform_share
            platform_repo = PlatformAccountRepo(session)
            # escrow_reserved -= final_price (через release_from_escrow с amount=final_price, fee=0)
            # Но здесь нужно просто уменьшить escrow_reserved
            # Используем прямую логику: escrow_reserved -= final_price
            # profit_accumulated += platform_share
            # Для простоты: вызываем release_from_escrow с platform_fee=platform_share
            await platform_repo.release_from_escrow(session, final_price, platform_share)

            # Transactions
            if advertiser_refund > 0:
                advertiser_txn = Transaction(
                    user_id=advertiser_id,
                    amount=advertiser_refund,
                    type=TransactionType.REFUND,
                    payment_id=None,
                    meta_json={
                        "type": "refund",
                        "scenario": scenario,
                        "placement_id": placement_id,
                        "share": "advertiser",
                    },
                    balance_before=advertiser.balance_rub - advertiser_refund
                    if advertiser
                    else Decimal("0"),
                    balance_after=advertiser.balance_rub if advertiser else Decimal("0"),
                )
                session.add(advertiser_txn)

            if owner_compensation > 0 and owner:
                owner_txn = Transaction(
                    user_id=owner_id,
                    amount=owner_compensation,
                    type=TransactionType.ESCROW_RELEASE,
                    payment_id=None,
                    meta_json={
                        "type": "owner_compensation",
                        "scenario": scenario,
                        "placement_id": placement_id,
                        "share": "owner",
                    },
                    balance_before=owner.earned_rub - owner_compensation,
                    balance_after=owner.earned_rub,
                )
                session.add(owner_txn)

            await session.flush()

            logger.info(
                f"Escrow refunded: scenario={scenario}, advertiser={advertiser_refund} ₽, "
                f"owner={owner_compensation} ₽, platform={platform_share} ₽"
            )


# Глобальный экземпляр
billing_service = BillingService()
