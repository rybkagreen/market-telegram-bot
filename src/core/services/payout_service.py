"""
PayoutRequest Service — сервис для управления выплатами владельцам каналов.
Спринт 1 — базовая система учёта выплат (80% от цены поста).
Выплаты обрабатываются вручную администратором.
"""

import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.payments import (
    MIN_PAYOUT,
    OWNER_SHARE,
    PAYOUT_FEE_RATE,
    PLATFORM_COMMISSION,
    VELOCITY_MAX_RATIO,
    VELOCITY_WINDOW_DAYS,
)
from src.core.exceptions import VelocityCheckError
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.transaction import TransactionType
from src.db.models.user import User
from src.db.repositories.payout_repo import PayoutRepository
from src.db.repositories.platform_account_repo import PlatformAccountRepository
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory


class InsufficientFundsError(Exception):
    pass


class PayoutAPIError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


logger = logging.getLogger(__name__)


# Compatibility for Python 3.10 and 3.11+
try:
    from datetime import UTC  # Python 3.11+
except ImportError:
    UTC = timezone.utc  # type: ignore[misc, assignment]  # noqa: UP017


class PayoutService:
    """
    Сервис для управления выплатами.

    Методы:
        calculate_payout: Рассчитать сумму выплаты (80% от цены поста)
        get_owner_balance: Получить баланс владельца к выплате
        create_pending_payout: Создать запись о выплате в статусе pending
        process_payout: Обработать выплату через ручную обработку администратором
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        # v4.2: используем константы из payments.py
        self.payout_percentage = OWNER_SHARE  # 85% владельцу
        self.platform_percentage = PLATFORM_COMMISSION  # 15% платформе

    def calculate_payout(self, price_per_post: Decimal) -> tuple[Decimal, Decimal]:
        """
        Рассчитать сумму выплаты и комиссию платформы.

        Args:
            price_per_post: Цена поста в рублях.

        Returns:
            Кортеж (payout_amount, platform_fee).
        """
        payout_amount = price_per_post * self.payout_percentage
        platform_fee = price_per_post * self.platform_percentage
        return payout_amount.quantize(Decimal("0.01")), platform_fee.quantize(Decimal("0.01"))

    async def get_owner_balance(self, owner_user_id: int) -> Decimal:
        """
        Получить баланс владельца к выплате (сумма pending выплат).

        Args:
            owner_user_id: ID владельца в БД.

        Returns:
            Сумма к выплате.
        """
        from sqlalchemy import func, select

        async with async_session_factory() as session:
            stmt = select(func.sum(PayoutRequest.gross_amount)).where(
                PayoutRequest.owner_id == owner_user_id,
                PayoutRequest.status == PayoutStatus.pending,
            )
            result = await session.execute(stmt)
            balance = result.scalar_one() or Decimal("0")
            return balance

    async def get_owner_payouts(
        self,
        owner_user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PayoutRequest]:
        """
        Получить список выплат владельца.

        Args:
            owner_user_id: ID владельца в БД.
            limit: Максимальное количество записей.
            offset: Смещение.

        Returns:
            Список выплат.
        """
        from sqlalchemy import select

        async with async_session_factory() as session:
            stmt = (
                select(PayoutRequest)
                .where(PayoutRequest.owner_id == owner_user_id)
                .order_by(PayoutRequest.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create_pending_payout(
        self,
        owner_user_id: int,
        channel_id: int,
        placement_id: int,
        price_per_post: Decimal,
    ) -> PayoutRequest:
        """
        Создать запись о выплате в статусе pending.

        Вызывается после факта публикации поста.

        Args:
            owner_user_id: ID владельца в БД.
            channel_id: ID канала.
            placement_id: ID размещения (mailing_log.id).
            price_per_post: Цена поста в рублях.

        Returns:
            Созданная запись PayoutRequest.
        """
        payout_amount, platform_fee = self.calculate_payout(price_per_post)

        async with async_session_factory() as session:
            # Проверяем что payout ещё не создан для этого placement
            existing = await session.get(PayoutRequest, placement_id)
            if existing:
                logger.warning(f"PayoutRequest already exists for placement {placement_id}")
                return existing

            # Legacy method - uses old model structure
            # New code should use create_payout instead
            payout = PayoutRequest(
                owner_id=owner_user_id,
                gross_amount=payout_amount,
                fee_amount=platform_fee,
                net_amount=payout_amount - platform_fee,
                status=PayoutStatus.pending,
                requisites="pending_placement",
            )

            session.add(payout)
            await session.flush()
            await session.refresh(payout)

            logger.info(
                f"Created pending payout {payout.id}: {payout_amount} ₽ for owner {owner_user_id}"
            )

            return payout

    async def process_payout(self, payout_id: int) -> dict:
        """
        Обработать выплату через ручную обработку администратором.

        Шаги:
        1. Получить PayoutRequest из БД по payout_id
        2. Проверить статус: только PENDING → обрабатывать
        3. Проверить минимальную сумму
        4. Получить telegram_id владельца из User
        5. Выполнить выплату через admin panel
        6. При успехе: статус → COMPLETED, записать transfer_id
        7. При ошибке: статус → FAILED, записать error_message
        8. Вернуть {"success": bool, "transfer_id": str | None, "error": str | None}

        Args:
            payout_id: ID выплаты.

        Returns:
            dict с результатом выплаты.
        """
        async with async_session_factory() as session:
            # Шаг 1: Получить выплату
            payout = await session.get(PayoutRequest, payout_id)
            if not payout:
                logger.error(f"PayoutRequest {payout_id} not found")
                return {"success": False, "transfer_id": None, "error": "PayoutRequest not found"}

            # Шаг 2: Проверить статус
            if payout.status != PayoutStatus.pending:
                logger.warning(
                    f"PayoutRequest {payout_id} already processed (status={payout.status.value})"
                )
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": f"Already processed: {payout.status.value}",
                }

            # Шаг 3: Проверить минимальную сумму
            # Используем MIN_PAYOUT из constants (1000 ₽)
            min_payout_rub = float(MIN_PAYOUT)
            payout_amount = float(payout.gross_amount)

            if payout_amount < min_payout_rub:
                logger.warning(
                    f"PayoutRequest {payout_id} amount {payout_amount} < minimum {min_payout_rub}"
                )
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": f"Amount below minimum ({min_payout_rub})",
                }

            # Шаг 4: Получить telegram_id владельца
            user = await session.get(User, payout.owner_id)
            if not user:
                logger.error(f"User {payout.owner_id} not found for payout {payout_id}")
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": "User not found",
                }

            if not user.telegram_id:
                logger.error(f"User {payout.owner_id} has no telegram_id")
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": "User has no telegram_id",
                }

            # Шаг 5: v4.3 — выплаты ручные через admin панель
            try:
                # v4.3: Выплаты ручные — admin одобряет вручную через /admin панель
                # Статус уже processing, admin переведёт деньги и нажмёт "Одобрить"
                payout.processed_at = datetime.now(UTC)
                await session.flush()

                logger.info(
                    f"PayoutRequest {payout_id} marked processing for manual admin transfer "
                    f"to user {user.telegram_id}, amount={payout.net_amount}"
                )

                return {
                    "success": True,
                    "transfer_id": None,
                    "error": None,
                }

            # Шаг 7: Обработка ошибок
            except InsufficientFundsError as e:
                payout.status = PayoutStatus.rejected
                error_msg = f"Insufficient funds: {str(e)}"
                logger.error(f"PayoutRequest {payout_id} failed: {error_msg}")

            except UserNotFoundError as e:
                payout.status = PayoutStatus.rejected
                error_msg = f"Payout processing error: {str(e)}"
                logger.error(f"PayoutRequest {payout_id} failed: {error_msg}")

            except PayoutAPIError as e:
                payout.status = PayoutStatus.rejected
                error_msg = f"API error: {str(e)}"
                logger.error(f"PayoutRequest {payout_id} failed: {error_msg}")

            except Exception as e:
                payout.status = PayoutStatus.rejected
                error_msg = f"Unexpected error: {str(e)}"
                logger.exception(f"PayoutRequest {payout_id} failed with unexpected error")

            # Записываем ошибку и сохраняем
            payout.rejection_reason = error_msg  # Используем wallet_address для хранения ошибки
            await session.flush()

            return {
                "success": False,
                "transfer_id": None,
                "error": error_msg,
            }

    async def mark_payout_paid(
        self,
        payout_id: int,
        tx_hash: str | None = None,
    ) -> bool:
        """
        Отметить выплату как выплаченную.

        Args:
            payout_id: ID выплаты.
            tx_hash: Хэш транзакции.

        Returns:
            True если успешно.
        """
        async with async_session_factory() as session:
            payout = await session.get(PayoutRequest, payout_id)
            if not payout:
                logger.error(f"PayoutRequest {payout_id} not found")
                return False

            if payout.status not in (PayoutStatus.pending, PayoutStatus.processing):
                logger.warning(
                    f"PayoutRequest {payout_id} cannot be marked as paid (status={payout.status.value})"
                )
                return False

            payout.status = PayoutStatus.paid
            payout.processed_at = datetime.now(UTC)
            # tx_hash field removed in v4.2 - payout uses YooKassa only

            await session.flush()

            logger.info(f"PayoutRequest {payout_id} marked as paid")
            return True

    async def cancel_payout(self, payout_id: int) -> bool:
        """
        Отменить выплату.

        Args:
            payout_id: ID выплаты.

        Returns:
            True если успешно.
        """
        async with async_session_factory() as session:
            payout = await session.get(PayoutRequest, payout_id)
            if not payout:
                logger.error(f"PayoutRequest {payout_id} not found")
                return False

            if payout.status == PayoutStatus.paid:
                logger.warning(f"PayoutRequest {payout_id} already paid, cannot cancel")
                return False

            payout.status = PayoutStatus.cancelled
            await session.flush()

            logger.info(f"PayoutRequest {payout_id} cancelled")
            return True

    # ─────────────────────────────────────────────
    # Метод для PlacementRequest (Этап 2)
    # ─────────────────────────────────────────────

    async def request_payout_for_placement(
        self,
        owner_id: int,
        amount: Decimal,
        placement_request_id: int,
    ) -> PayoutRequest:
        """
        Создать запрос на выплату для владельца после публикации.

        Проверки:
        1. amount >= 100 кр (MIN_PAYOUT)
        2. owner не заблокирован

        Args:
            owner_id: ID владельца.
            amount: Сумма к выплате.
            placement_request_id: ID заявки.

        Returns:
            PayoutRequest объект.

        Raises:
            ValueError: Если amount < MIN_PAYOUT или owner заблокирован.
        """
        from src.db.models.payout import PayoutRequest, PayoutStatus

        # Проверка 1: amount >= MIN_PAYOUT
        if amount < MIN_PAYOUT:
            raise ValueError(f"Amount {amount} < MIN_PAYOUT {MIN_PAYOUT}")

        # Проверка 2: owner не заблокирован
        from src.db.repositories.reputation_repo import ReputationRepo

        async with async_session_factory() as session:
            rep_repo = ReputationRepo(session)
            rep_score = await rep_repo.get_by_user(owner_id)

            if (
                rep_score
                and rep_score.is_owner_blocked
                and rep_score.owner_blocked_until
                and rep_score.owner_blocked_until > datetime.now(UTC)
            ):
                raise ValueError("Owner is blocked")

        # Создаём payout
        fee_amount = amount * Decimal("0.25")  # 20% комиссия
        payout = PayoutRequest(
            owner_id=owner_id,
            gross_amount=amount,
            fee_amount=fee_amount,
            net_amount=amount - fee_amount,
            status=PayoutStatus.pending,
            requisites=f"placement_{placement_request_id}",
        )

        async with async_session_factory() as session:
            session.add(payout)
            await session.flush()
            await session.refresh(payout)

            logger.info(
                f"PayoutRequest request created: {amount} USDT for owner {owner_id}, placement {placement_request_id}"
            )

            return payout

    # ══════════════════════════════════════════════════════════════
    # S-06: PayoutService v4.2 — новые методы
    # ══════════════════════════════════════════════════════════════

    async def check_velocity(
        self,
        session: AsyncSession,
        user_id: int,
        requested_amount: Decimal,
    ) -> None:
        """
        Проверить velocity limit — соотношение вывод/пополнения за 30 дней.

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.
            requested_amount: Запрошенная сумма вывода.

        Raises:
            VelocityCheckError: Если ratio > VELOCITY_MAX_RATIO (80%).
        """
        # topups_30d = await transaction_repo.sum_topups_window(session, user_id, days=VELOCITY_WINDOW_DAYS)
        txn_repo = TransactionRepository(session)
        topups_30d = await txn_repo.sum_topups_30d(user_id)

        # payouts_30d = await payout_repo.sum_completed_payouts_window(session, user_id, days=VELOCITY_WINDOW_DAYS)
        payout_repo = PayoutRepository(session)
        payouts_30d = await payout_repo.sum_completed_payouts_window(user_id, VELOCITY_WINDOW_DAYS)

        if topups_30d == Decimal("0"):
            # Нет пополнений за 30 дней — нечего проверять
            return

        ratio = (payouts_30d + requested_amount) / topups_30d

        if ratio > VELOCITY_MAX_RATIO:
            raise VelocityCheckError(
                f"Вывод заморожен на ревью администратора. "
                f"Соотношение вывод/пополнение: {ratio:.2%} (макс. {VELOCITY_MAX_RATIO:.0%}). "
                f"Свяжитесь с поддержкой."
            )

    async def create_payout(
        self,
        session: AsyncSession,
        user_id: int,
        gross_amount: Decimal,
    ) -> PayoutRequest:
        """
        Создать заявку на выплату.

        Args:
            session: Асинхронная сессия.
            user_id: ID пользователя.
            gross_amount: Запрошенная сумма (gross).

        Returns:
            Созданная заявка на выплату.

        Raises:
            ValueError: Если gross_amount < MIN_PAYOUT или уже есть активная заявка.
            InsufficientFundsError: Если недостаточно earned_rub.
            VelocityCheckError: Если превышен velocity limit.
        """
        if gross_amount < MIN_PAYOUT:
            raise ValueError(f"Минимальная сумма вывода {MIN_PAYOUT} ₽")

        async with session.begin():
            # SELECT FOR UPDATE user
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            if user.earned_rub < gross_amount:
                raise InsufficientFundsError(
                    f"Insufficient earned_rub: {user.earned_rub} < {gross_amount}"
                )

            # Проверить нет ли активной заявки
            payout_repo = PayoutRepository(session)
            active = await payout_repo.get_active_for_owner(user_id)
            if active:
                raise ValueError("У вас уже есть активная заявка на вывод")

            # Velocity check
            await self.check_velocity(session, user_id, gross_amount)

            # Расчёт комиссии: fee = gross * PAYOUT_FEE_RATE (1.5%)
            fee_amount = (gross_amount * PAYOUT_FEE_RATE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Sprint B.2: рассчитать НДФЛ / NPD статус
            legal_status = user.legal_profile.legal_status if user.legal_profile else "individual"
            ndfl_withheld = Decimal("0")
            npd_status = "pending"

            if legal_status == "individual":
                # Физлицо — удержать НДФЛ 13%
                ndfl_withheld = (gross_amount * Decimal("0.13")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            elif legal_status == "self_employed":
                # Самозанятый — ждать чек НПД (48h таймаут)
                npd_status = "pending"
            # legal_entity, individual_entrepreneur — без удержания

            net_amount = gross_amount - fee_amount - ndfl_withheld

            # Списать с earned_rub
            user.earned_rub -= gross_amount

            # platform_account: payout_reserved += gross_amount, profit_accumulated += fee_amount
            platform_repo = PlatformAccountRepository(session)
            await platform_repo.add_to_payout_reserved(session, gross_amount)
            await platform_repo.add_to_profit(session, fee_amount)

            # Создать PayoutRequest с рассчитанными полями
            payout = PayoutRequest(
                owner_id=user_id,
                gross_amount=gross_amount,
                fee_amount=fee_amount,
                net_amount=net_amount,
                status=PayoutStatus.pending,
                requisites="payout_request",
                ndfl_withheld=ndfl_withheld,
                npd_status=npd_status,
            )
            session.add(payout)
            await session.flush()
            await session.refresh(payout)

            # Создаём транзакции ПОСЛЕ flush() — payout.id уже известен
            txn_repo = TransactionRepository(session)
            await txn_repo.create(
                {
                    "user_id": user_id,
                    "type": TransactionType.refund_full,
                    "amount": gross_amount,
                    "payout_id": payout.id,
                    "meta_json": {"type": "payout_request", "gross_amount": str(gross_amount)},
                },
            )

            await txn_repo.create(
                {
                    "user_id": user_id,
                    "type": TransactionType.payout_fee,
                    "amount": fee_amount,
                    "payout_id": payout.id,
                },
            )

            # Sprint B.2: транзакция удержания НДФЛ (если > 0)
            if ndfl_withheld > 0:
                await txn_repo.create(
                    {
                        "user_id": user_id,
                        "type": TransactionType.ndfl_withholding,
                        "amount": ndfl_withheld,
                        "payout_id": payout.id,
                        "meta_json": {
                            "type": "ndfl_withholding",
                            "rate": "0.13",
                            "legal_status": legal_status,
                        },
                    },
                )

            logger.info(
                f"PayoutRequest created: gross={gross_amount} ₽, fee={fee_amount} ₽, "
                f"ndfl={ndfl_withheld} ₽, net={net_amount} ₽ for user {user_id} "
                f"(legal_status={legal_status})"
            )

            return payout

    async def complete_payout(
        self,
        session: AsyncSession,
        payout_id: int,
    ) -> None:
        """
        Администратор подтвердил перевод — завершить выплату.

        Args:
            session: Асинхронная сессия.
            payout_id: ID заявки на выплату.
        """
        async with session.begin():
            payout = await session.get(PayoutRequest, payout_id)
            if not payout:
                raise ValueError(f"PayoutRequest {payout_id} not found")

            payout.status = PayoutStatus.paid
            payout.processed_at = datetime.now(UTC)

            # complete_payout: gross_amount and net_amount are required
            if payout.gross_amount is None or payout.net_amount is None:
                raise ValueError(f"PayoutRequest {payout_id} missing gross_amount or net_amount")

            # platform_account_repo.complete_payout(session, gross_amount=payout.gross_amount, net_amount=payout.net_amount)
            platform_repo = PlatformAccountRepository(session)
            await platform_repo.complete_payout(session, payout.gross_amount, payout.net_amount)

            await session.flush()

            # Sprint D.2: записать расход — выплата владельцу канала (PAYOUT_TO_CONTRACTORS)
            try:
                from src.constants.expense_categories import ExpenseCategory
                from src.core.services.tax_aggregation_service import TaxAggregationService

                if payout.net_amount > 0:
                    await TaxAggregationService.record_expense_for_usn(
                        session,
                        payout.net_amount,
                        ExpenseCategory.PAYOUT_TO_CONTRACTORS.value,
                        f"Payout to channel owner for request {payout_id}",
                    )
            except Exception as e:
                logger.error(f"Failed to record payout expense for payout {payout_id}: {e}")

            logger.info(
                f"PayoutRequest {payout_id} completed: gross={payout.gross_amount} ₽, net={payout.net_amount} ₽"
            )

    async def reject_payout(
        self,
        session: AsyncSession,
        payout_id: int,
        reason: str,
    ) -> None:
        """
        Администратор отклонил выплату — вернуть деньги на earned_rub.

        Args:
            session: Асинхронная сессия.
            payout_id: ID заявки на выплату.
            reason: Причина отклонения.
        """
        async with session.begin():
            payout = await session.get(PayoutRequest, payout_id)
            if not payout:
                raise ValueError(f"PayoutRequest {payout_id} not found")

            gross_amount = payout.gross_amount or Decimal("0")
            fee_amount = payout.fee_amount or Decimal("0")

            payout.status = PayoutStatus.cancelled
            payout.rejection_reason = reason  # Используем для хранения причины

            # UPDATE users SET earned_rub = earned_rub + gross_amount WHERE id = user_id
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(payout.owner_id)
            if user:
                user.earned_rub += gross_amount

            # platform_account: payout_reserved -= gross_amount, profit_accumulated -= fee_amount
            platform_repo = PlatformAccountRepository(session)
            # Для упрощения: вызываем add_to_payout_reserved с отрицательным значением
            # и add_to_profit с отрицательным
            await platform_repo.add_to_payout_reserved(session, -gross_amount)
            if fee_amount > 0:
                await platform_repo.add_to_profit(session, -fee_amount)

            # Transaction(type=REFUND_FULL, amount=gross_amount)
            txn_repo = TransactionRepository(session)
            await txn_repo.create(
                {
                    "user_id": payout.owner_id,
                    "type": TransactionType.refund_full,
                    "amount": gross_amount,
                    "meta_json": {"type": "payout_rejected", "reason": reason},
                },
            )

            await session.flush()

            logger.info(
                f"PayoutRequest {payout_id} rejected: reason={reason}, refunded {gross_amount} ₽"
            )

    async def calculate_payout_with_tax(self, user_id: int, gross_amount: Decimal) -> dict:
        """
        Рассчитать выплату с учётом налоговой нагрузки на основе юридического профиля.

        Args:
            user_id: ID пользователя.
            gross_amount: Брутто-сумма выплаты.

        Returns:
            dict с ключами: gross, tax, net, tax_note.
        """
        from src.constants.legal import NDFL_RATE
        from src.db.repositories.legal_profile_repo import LegalProfileRepo

        async with async_session_factory() as session:
            profile = await LegalProfileRepo(session).get_by_user_id(user_id)

        if profile is None:
            return {
                "gross": gross_amount,
                "tax": Decimal("0"),
                "net": gross_amount,
                "tax_note": "Заполните юридический профиль для расчёта налогов.",
            }

        status = profile.legal_status

        if status in ("legal_entity", "individual_entrepreneur"):
            return {
                "gross": gross_amount,
                "tax": Decimal("0"),
                "net": gross_amount,
                "tax_note": "Налог уплачивается вами самостоятельно по выбранному режиму.",
            }

        if status == "self_employed":
            return {
                "gross": gross_amount,
                "tax": Decimal("0"),
                "net": gross_amount,
                "tax_note": "НПД (6%) вы уплачиваете самостоятельно через «Мой налог».",
            }

        if status == "individual":
            ndfl = (gross_amount * NDFL_RATE).quantize(Decimal("0.01"))
            return {
                "gross": gross_amount,
                "tax": ndfl,
                "net": gross_amount - ndfl,
                "tax_note": f"НДФЛ 13% ({ndfl} ₽) будет удержан платформой.",
            }

        return {"gross": gross_amount, "tax": Decimal("0"), "net": gross_amount, "tax_note": ""}


# Глобальный экземпляр
payout_service = PayoutService()
