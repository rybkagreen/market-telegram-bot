"""
Billing Service для управления платежами и балансом.
Двухвалютная система: рубли (размещения) + кредиты (подписки).
"""

import logging
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.payments import (
    MAX_TOPUP,
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


class PaymentProviderError(Exception):
    """Платёжный провайдер (YooKassa) вернул ошибку.

    Несёт code/description/request_id для пользовательского сообщения
    и трассировки в support. Caller (роутер) транслирует в HTTP 503
    с user-friendly формулировкой.
    """

    def __init__(self, code: str, description: str, request_id: str) -> None:
        self.code = code
        self.description = description
        self.request_id = request_id
        super().__init__(
            f"Payment provider error [{code}] {description} (req={request_id})"
        )


class BillingService:
    """
    Сервис для управления платежами и балансом.

    Методы:
        create_payment: Создать платёж (пополняет balance_rub)
        check_payment: Проверить статус платежа
        buy_credits_for_plan: Купить кредиты для тарифа (с balance_rub → credits)
        freeze_escrow: Заморозить рубли для размещения
        release_escrow: Освободить эскроу после удаления поста (ESCROW-001)
        refund_escrow: Возврат средств при отмене
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""

    async def buy_credits_for_plan(
        self,
        user_id: int,
        amount_rub: Decimal,
    ) -> tuple[int, Transaction, Transaction]:
        """
        Оплатить тариф с рублёвого баланса.

        Кредиты удалены — используется единая валюта balance_rub.

        Args:
            user_id: ID пользователя.
            amount_rub: Сумма в рублях.

        Returns:
            Кортеж (amount_int, transaction, transaction) — дубли для обратной совместимости.

        Raises:
            InsufficientFundsError: Если недостаточно balance_rub.
        """
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

            # Списываем рубли
            balance_rub_before = user.balance_rub
            user.balance_rub -= amount_rub

            transaction = Transaction(
                user_id=user_id,
                amount=amount_rub,
                type=TransactionType.spend,
                yookassa_payment_id=None,
                description=f"Оплата тарифа: {amount_rub} ₽",
                meta_json={
                    "type": "plan_payment",
                    "currency": "rub",
                },
                balance_before=balance_rub_before,
                balance_after=user.balance_rub,
                created_at=datetime.now(UTC),
            )
            session.add(transaction)

            await session.commit()
            await session.refresh(transaction)

            logger.info(f"Plan payment: {amount_rub} ₽ by user {user_id}")

            return int(amount_rub), transaction, transaction

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
                Transaction.yookassa_payment_id == payment_id,
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
                # Зачисляем рубли на баланс
                user_repo = UserRepository(session)
                amount_rub = transaction.amount
                await user_repo.update_balance_rub(user_id, amount_rub)

                # Обновляем транзакцию
                meta["credited"] = True
                meta["rub_credited"] = float(amount_rub)
                await transaction_repo.update(transaction.id, {"meta_json": meta})

                logger.info(f"Payment {payment_id} credited: {amount_rub} ₽ to user {user_id}")

                # Уведомляем пользователя
                await notification_service.notify_low_balance(
                    user_id=user_id,
                    balance=amount_rub,
                )

            return {
                "payment_id": payment_id,
                "status": status,
                "amount": str(transaction.amount),
                "credited": meta.get("credited", False),
            }

    async def activate_plan(self, user_id: int, plan: str) -> bool:
        """
        Активировать тариф пользователя.

        Логика:
        1. Получить цену тарифа из settings (tariff_cost_*)
        2. Проверить user.balance_rub >= plan_price
        3. Атомарно (session.begin()):
           - Списать balance_rub
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
                user.ai_uses_count = 0
                logger.info(f"User {user_id} activated FREE plan")
                return True

            # 3. Проверить баланс
            if user.balance_rub < Decimal(str(plan_price)):
                logger.warning(
                    f"User {user_id} has insufficient balance: {user.balance_rub} < {plan_price}"
                )
                return False

            try:
                # 4. Атомарно: списать рубли, установить тариф, создать транзакцию
                user.balance_rub -= Decimal(str(plan_price))
                user.plan = UserPlan(plan.lower())
                user.plan_expires_at = datetime.now(UTC) + timedelta(days=30)
                user.ai_uses_count = 0

                # Создать транзакцию
                transaction = Transaction(
                    user_id=user.id,
                    amount=Decimal(str(plan_price)),
                    type=TransactionType.spend,
                    yookassa_payment_id=None,
                    meta_json={
                        "type": "plan_purchase",
                        "plan": plan.lower(),
                    },
                    balance_before=user.balance_rub + Decimal(str(plan_price)),
                    balance_after=user.balance_rub,
                    created_at=datetime.now(UTC),
                )
                session.add(transaction)

                # session.begin() автоматически commit
                logger.info(f"User {user_id} activated {plan.upper()} plan for {plan_price} ₽")
                return True

            except Exception as e:
                logger.error(f"Failed to activate plan {plan} for user {user_id}: {e}")
                return False

    async def refund_failed_placement(self, session: AsyncSession, placement_id: int) -> bool:
        """
        Возврат средств за несостоявшееся размещение.

        Логика:
        1. Получить placement, убедиться что status == "failed"
        2. Получить placement_request и рекламодателя
        3. Начислить placement.cost на user.balance_rub
        4. Создать Transaction(type="refund_full", amount=placement.cost)
        5. Отправить уведомление пользователю

        Args:
            session: Асинхронная сессия.
            placement_id: ID размещения (mailing_log.id).

        Returns:
            True если возврат успешен.
        """
        from datetime import datetime

        from sqlalchemy import select

        from src.db.models.mailing_log import MailingLog, MailingStatus
        from src.db.models.placement_request import PlacementRequest
        from src.db.models.transaction import Transaction
        from src.db.models.user import User

        # 1. Получить placement с блокировкой
        stmt = select(MailingLog).where(MailingLog.id == placement_id).with_for_update()
        result = await session.execute(stmt)
        placement = result.scalar_one_or_none()
        if not placement:
            logger.error(f"Placement {placement_id} not found")
            return False

        # Проверить статус
        if placement.status != MailingStatus.failed:
            logger.warning(f"Placement {placement_id} status is not failed ({placement.status})")
            return False

        # ⚠️ ИДЕМПОТЕНТНОСТЬ: проверить флаг возврата
        meta = placement.meta_json or {}
        if meta.get("refund_sent"):
            logger.warning(
                f"refund_failed_placement: already refunded for placement {placement_id}"
            )
            return True  # уже возвращено

        # 2. Получить placement_request и рекламодателя
        stmt = (
            select(PlacementRequest)
            .where(PlacementRequest.id == placement.placement_request_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        placement_request: PlacementRequest | None = result.scalar_one_or_none()
        if placement_request is None:
            logger.error(f"PlacementRequest {placement.placement_request_id} not found")
            return False

        stmt = select(User).where(User.id == placement_request.advertiser_id).with_for_update()
        result = await session.execute(stmt)
        advertiser: User | None = result.scalar_one_or_none()
        if advertiser is None:
            logger.error(f"Advertiser {placement_request.advertiser_id} not found for refund")
            return False

        try:
            # 3. Вернуть средства + установить флаг атомарно
            refund_amount = Decimal(str(placement.cost))
            advertiser.balance_rub += refund_amount

            # Установить флаг что возврат отправлен
            meta["refund_sent"] = True
            meta["refund_at"] = datetime.now(UTC).isoformat()
            placement.meta_json = meta

            # 4. Создать транзакцию возврата
            transaction = Transaction(
                user_id=advertiser.id,
                amount=refund_amount,
                type=TransactionType.refund_full,
                yookassa_payment_id=None,
                meta_json={
                    "type": "refund",
                    "placement_id": placement_id,
                    "placement_request_id": placement.placement_request_id,
                    "reason": "failed_placement",
                },
                balance_before=advertiser.balance_rub - refund_amount,
                balance_after=advertiser.balance_rub,
                created_at=datetime.now(UTC),
            )
            session.add(transaction)

            logger.info(
                f"Refunded {refund_amount} to advertiser {advertiser.id} for placement {placement_id}"
            )

            # Сохраняем данные для уведомления (после коммита)
            user_telegram_id = advertiser.telegram_id
            placement_desc = f"Placement #{placement_id}"

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
                    f"Размещение: {placement_desc}\n"
                    f"Сумма: {refund_amount} RUB\n\n"
                    f"Средства возвращены на баланс."
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to send refund notification: {e}")

        return True

    # ─────────────────────────────────────────────
    # Методы для PlacementRequest (Этап 2)
    # ─────────────────────────────────────────────

    async def freeze_escrow_for_placement(
        self,
        session: AsyncSession,
        placement_id: int,
        advertiser_id: int,
        amount: Decimal,
        is_test: bool = False,
    ) -> Transaction:
        """
        Заморозить эскроу для PlacementRequest — единственный путь freeze.

        Операции (атомарно в рамках caller transaction):
        1. EXISTS-проверка по idempotency_key=escrow_freeze:placement={id}.
        2. (Если НЕ is_test) проверка balance_rub >= amount и списание.
        3. platform_account.escrow_reserved += amount.
        4. Transaction(type=escrow_freeze, amount=amount, idempotency_key).

        Args:
            session: Сессия.
            placement_id: ID заявки.
            advertiser_id: ID рекламодателя.
            amount: Сумма блокировки (для is_test может быть 0).
            is_test: Тестовый placement — balance_rub не трогаем,
                всё остальное (Transaction, platform_account) — как обычно.

        Returns:
            Transaction с заполненным id. При idempotency-hit возвращает
            существующую транзакцию.

        Raises:
            ValueError: advertiser не найден.
            InsufficientFundsError: balance_rub < amount (только НЕ is_test).
        """
        from sqlalchemy import select
        from sqlalchemy.exc import IntegrityError

        from src.db.models.transaction import Transaction
        from src.db.repositories.platform_account_repo import PlatformAccountRepo

        freeze_key = f"escrow_freeze:placement={placement_id}"

        existing = await session.scalar(
            select(Transaction).where(Transaction.idempotency_key == freeze_key)
        )
        if existing is not None:
            logger.info(
                f"freeze_escrow_for_placement: placement {placement_id} "
                f"already frozen (idempotency hit)"
            )
            return existing

        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(advertiser_id)
        if not user:
            raise ValueError(f"User {advertiser_id} not found")

        balance_before = user.balance_rub

        if not is_test:
            if user.balance_rub < amount:
                raise InsufficientFundsError(
                    f"Insufficient balance_rub: {user.balance_rub} < {amount}"
                )
            user.balance_rub -= amount

        platform_repo = PlatformAccountRepo(session)
        await platform_repo.add_to_escrow(session, amount)

        transaction = Transaction(
            user_id=advertiser_id,
            amount=amount,
            type=TransactionType.escrow_freeze,
            placement_request_id=placement_id,
            yookassa_payment_id=None,
            idempotency_key=freeze_key,
            meta_json={
                "type": "escrow_freeze",
                "placement_id": placement_id,
                "currency": "rub",
                "is_test": is_test,
            },
            balance_before=balance_before,
            balance_after=user.balance_rub,
            created_at=datetime.now(UTC),
        )
        session.add(transaction)
        try:
            await session.flush()
        except IntegrityError as exc:
            logger.warning(
                f"freeze_escrow_for_placement: idempotency race for "
                f"placement {placement_id}: {exc}"
            )
            raise
        await session.refresh(transaction)

        logger.info(
            f"Escrow frozen: {amount} ₽ for placement {placement_id} "
            f"(advertiser={advertiser_id}, is_test={is_test})"
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

            Caller-controlled transaction: метод работает в рамках транзакции
            вызывающего, не открывает и не коммитит её. Используется session.flush()
            для ранней материализации ограничений.
        """
        desired_balance = Decimal(metadata["desired_balance"])
        user_id = int(metadata["user_id"])

        # Идемпотентность: проверить что payment_id не обработан ранее
        txn_repo = TransactionRepository(session)
        existing = await txn_repo.find_one(Transaction.yookassa_payment_id == payment_id)
        if existing and existing.meta_json and existing.meta_json.get("processed"):
            logger.warning(f"Payment {payment_id} already processed")
            return

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
            type=TransactionType.topup,
            yookassa_payment_id=payment_id,
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

        # Sprint A.3: записать выручку в УСН и КУДиР
        from src.core.services.tax_aggregation_service import TaxAggregationService

        await TaxAggregationService.record_income_for_usn(
            session,
            gross_amount,
            f"Topup via YooKassa (payment_id={payment_id})",
        )

        # Sprint D.2: записать расход — комиссия ЮKassa (BANK_COMMISSIONS)
        try:
            from src.constants.expense_categories import ExpenseCategory

            if gross_amount > desired_balance:
                yk_fee = gross_amount - desired_balance
                await TaxAggregationService.record_expense_for_usn(
                    session,
                    yk_fee,
                    ExpenseCategory.BANK_COMMISSIONS.value,
                    f"ЮKassa commission for payment {payment_id}",
                )
        except Exception as e:
            logger.error(f"Failed to record YooKassa fee expense for payment {payment_id}: {e}")

        # Referral bonus: check if this user has a referrer
        try:
            await self.process_referral_topup_bonus(
                session, user_id=user_id, topup_amount=desired_balance
            )
        except Exception as e:
            logger.error(f"Failed to process referral topup bonus for user {user_id}: {e}")

        logger.info(
            f"Topup webhook processed: +{desired_balance} ₽ for user {user_id}, "
            f"payment_id={payment_id}, gross={gross_amount} ₽"
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

            Caller-controlled transaction: метод работает в рамках транзакции
            вызывающего, не открывает и не коммитит её.

            Idempotent: каждая из двух порождаемых транзакций несёт стабильный
            Transaction.idempotency_key. При повторном вызове метод находит
            существующий ключ и выходит без побочных эффектов. При конкурентной
            вставке UNIQUE-индекс в БД пропускает лишь одного победителя.
        """
        from sqlalchemy import exists, select
        from sqlalchemy.exc import IntegrityError

        owner_key = f"escrow_release:placement={placement_id}:owner"
        platform_key = f"escrow_release:placement={placement_id}:platform"

        # Idempotency: если ключ уже есть — релиз уже выполнен, no-op.
        already = await session.scalar(
            select(
                exists().where(
                    Transaction.idempotency_key.in_([owner_key, platform_key])
                )
            )
        )
        if already:
            logger.info(
                f"release_escrow: placement {placement_id} already released (idempotency hit)"
            )
            return

        # Formula: owner_amount = final_price * OWNER_SHARE (rounded)
        owner_amount = (final_price * OWNER_SHARE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        # Formula: platform_fee = final_price - owner_amount (remainder)
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
            type=TransactionType.escrow_release,
            placement_request_id=placement_id,
            yookassa_payment_id=None,
            idempotency_key=owner_key,
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
            type=TransactionType.commission,
            placement_request_id=placement_id,
            yookassa_payment_id=None,
            idempotency_key=platform_key,
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
        try:
            await session.flush()
        except IntegrityError as exc:
            # Race: кто-то параллельно успел вставить — откат на savepoint не нужен,
            # так как caller получит ту же ошибку и откатит свою транзакцию.
            # Логируем и пробрасываем — retry на уровне Celery подхватит и
            # на следующей итерации EXISTS-проверка вверху сработает.
            logger.warning(
                f"release_escrow: idempotency race for placement {placement_id}: {exc}"
            )
            raise

        # Sprint A.3: записать комиссию размещения в УСН и КУДиР
        # Sprint C.1: рассчитать НДС 22% от комиссии платформы
        from src.core.services.tax_aggregation_service import TaxAggregationService

        vat_amount = (platform_fee * Decimal("0.22")).quantize(Decimal("0.01"))

        await TaxAggregationService.record_income_for_usn(
            session,
            platform_fee,
            f"Placement commission (placement_id={placement_id})",
            vat_amount=vat_amount,
        )

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

        Caller-controlled transaction: метод работает в рамках транзакции вызывающего.

        Idempotent: каждая порождаемая транзакция несёт стабильный
        Transaction.idempotency_key (по сценарию); повторный вызов — no-op.
        """
        from sqlalchemy import exists, select
        from sqlalchemy.exc import IntegrityError

        advertiser_key = f"refund:placement={placement_id}:scenario={scenario}:advertiser"
        owner_key = f"refund:placement={placement_id}:scenario={scenario}:owner"

        # Idempotency: если один из ключей уже есть — refund уже выполнен, no-op.
        already = await session.scalar(
            select(
                exists().where(
                    Transaction.idempotency_key.in_([advertiser_key, owner_key])
                )
            )
        )
        if already:
            logger.info(
                f"refund_escrow: placement {placement_id} scenario {scenario} "
                f"already refunded (idempotency hit)"
            )
            return

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
            # Formula: platform_share = final_price - advertiser_refund - owner_compensation
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
        await platform_repo.release_from_escrow(session, final_price, platform_share)

        # Transactions
        if advertiser_refund > 0:
            advertiser_txn = Transaction(
                user_id=advertiser_id,
                amount=advertiser_refund,
                type=TransactionType.refund_full,
                placement_request_id=placement_id,
                yookassa_payment_id=None,
                idempotency_key=advertiser_key,
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
                type=TransactionType.escrow_release,
                placement_request_id=placement_id,
                yookassa_payment_id=None,
                idempotency_key=owner_key,
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

        try:
            await session.flush()
        except IntegrityError as exc:
            logger.warning(
                f"refund_escrow: idempotency race for placement {placement_id} "
                f"scenario {scenario}: {exc}"
            )
            raise

        logger.info(
            f"Escrow refunded: scenario={scenario}, advertiser={advertiser_refund} ₽, "
            f"owner={owner_compensation} ₽, platform={platform_share} ₽"
        )

    async def admin_credit_from_platform(
        self,
        session: AsyncSession,
        admin_id: int,
        user_id: int,
        amount: Decimal,
        comment: str = "",
    ) -> Transaction:
        """
        Зачисляет средства из profit_accumulated платформы на баланс пользователя.
        Проверяет что profit_accumulated >= amount перед списанием.
        """
        from src.db.models.platform_account import PlatformAccount
        from src.db.models.transaction import Transaction
        from src.db.models.user import User

        # 1. Загрузить PlatformAccount (id=1)
        pa = await session.get(PlatformAccount, 1)
        if not pa:
            # Создать если не существует
            pa = PlatformAccount(id=1)
            session.add(pa)
            await session.flush()
            await session.refresh(pa)

        # 2. Загрузить пользователя
        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # 3. Проверить: platform_account.profit_accumulated >= amount
        if pa.profit_accumulated < amount:
            raise ValueError(
                f"Недостаточно средств на балансе платформы: {pa.profit_accumulated} < {amount}"
            )

        # 4. Списать с платформы, зачислить пользователю
        pa.profit_accumulated -= amount
        balance_before = user.balance_rub
        user.balance_rub += amount

        # 5. Создать Transaction
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=TransactionType.admin_credit,
            yookassa_payment_id=None,
            description=f"Зачисление администратором: {comment}"
            if comment
            else "Зачисление администратором",
            meta_json={
                "type": "admin_credit",
                "admin_id": admin_id,
                "comment": comment,
            },
            balance_before=balance_before,
            balance_after=user.balance_rub,
            created_at=datetime.now(UTC),
        )
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)

        logger.info(f"Admin credit: {amount} ₽ from platform to user {user_id} by admin {admin_id}")

        return transaction

    async def admin_gamification_bonus(
        self,
        session: AsyncSession,
        admin_id: int,
        user_id: int,
        amount: Decimal,
        xp_amount: int = 0,
        comment: str = "",
    ) -> Transaction:
        """
        Начисляет геймификационный бонус из profit_accumulated.
        amount > 0 — денежный бонус, xp_amount > 0 — XP.
        """
        from src.db.models.platform_account import PlatformAccount
        from src.db.models.transaction import Transaction
        from src.db.models.user import User

        # 1. Загрузить PlatformAccount
        pa = await session.get(PlatformAccount, 1)
        if not pa:
            pa = PlatformAccount(id=1)
            session.add(pa)
            await session.flush()
            await session.refresh(pa)

        # 2. Загрузить пользователя
        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # 3. Проверить достаточно средств (если amount > 0)
        if amount > 0 and pa.profit_accumulated < amount:
            raise ValueError(
                f"Недостаточно средств на балансе платформы: {pa.profit_accumulated} < {amount}"
            )

        # 4. Списать с платформы, зачислить
        if amount > 0:
            pa.profit_accumulated -= amount
            balance_before = user.balance_rub
            user.balance_rub += amount
        else:
            balance_before = user.balance_rub

        if xp_amount > 0:
            user.advertiser_xp += xp_amount

        # 5. Создать Transaction
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=TransactionType.gamification_bonus,
            yookassa_payment_id=None,
            description=f"Геймификационный бонус: {comment}"
            if comment
            else "Геймификационный бонус",
            meta_json={
                "type": "gamification_bonus",
                "admin_id": admin_id,
                "xp_amount": xp_amount,
                "comment": comment,
            },
            balance_before=balance_before,
            balance_after=user.balance_rub,
            created_at=datetime.now(UTC),
        )
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)

        logger.info(
            f"Gamification bonus: {amount} ₽ + {xp_amount} XP to user {user_id} by admin {admin_id}"
        )

        return transaction

    async def process_referral_topup_bonus(
        self,
        session: AsyncSession,
        user_id: int,
        topup_amount: Decimal,
    ) -> bool:
        """
        Вызывается при каждом пополнении пользователя.
        Проверяет условия и начисляет разовый реферальный бонус рефереру.
        Возвращает True если бонус был начислен.

        Бизнес-правило:
        - Реферер получает REFERRAL_BONUS_PERCENT % от суммы пополнения
        - Выплата РАЗОВАЯ (идемпотентность через meta_json)
        - Минимальная сумма: REFERRAL_MIN_QUALIFYING_TOPUP
        """
        from sqlalchemy import select, text

        from src.constants.payments import (
            REFERRAL_BONUS_PERCENT,
            REFERRAL_MIN_QUALIFYING_TOPUP,
        )
        from src.db.models.user import User

        # 1. Загрузить user с referred_by_id
        user = await session.get(User, user_id)
        if not user or user.referred_by_id is None:
            return False  # не реферал

        referrer_id = user.referred_by_id

        # 2. Проверить идемпотентность — бонус уже выплачен за этого реферала
        existing_txn = await session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == referrer_id,
                Transaction.type == TransactionType.bonus,
                text("meta_json->>'referral_user_id' = :ruid"),
            )
            .params(ruid=str(user_id))
        )
        if existing_txn.scalar_one_or_none():
            return False  # уже выплачено за этого реферала

        # 3. Проверить topup_amount >= REFERRAL_MIN_QUALIFYING_TOPUP
        if topup_amount < REFERRAL_MIN_QUALIFYING_TOPUP:
            return False

        # 4. Рассчитать бонус
        bonus_amount = (topup_amount * REFERRAL_BONUS_PERCENT).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 5. Начислить бонус рефереру
        referrer = await session.get(User, referrer_id)
        if not referrer:
            return False

        balance_before = referrer.balance_rub
        referrer.balance_rub += bonus_amount

        # 6. Создать Transaction
        transaction = Transaction(
            user_id=referrer_id,
            amount=bonus_amount,
            type=TransactionType.bonus,
            yookassa_payment_id=None,
            description=f"Реферальный бонус за пополнение пользователя {user_id}",
            meta_json={
                "type": "referral_topup_bonus",
                "referral_user_id": str(user_id),
                "topup_amount": str(topup_amount),
                "bonus_percent": str(REFERRAL_BONUS_PERCENT),
            },
            balance_before=balance_before,
            balance_after=referrer.balance_rub,
            created_at=datetime.now(UTC),
        )
        session.add(transaction)
        await session.flush()

        logger.info(
            f"Referral topup bonus: {bonus_amount} ₽ to referrer {referrer_id} "
            f"for user {user_id} topup of {topup_amount} ₽"
        )

        return True
