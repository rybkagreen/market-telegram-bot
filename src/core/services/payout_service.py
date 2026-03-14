"""
Payout Service — сервис для управления выплатами владельцам каналов.
Спринт 1 — базовая система учёта выплат (80% от цены поста).
Реальная интеграция с CryptoBot добавляется в Спринте 1 (Task 1).
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
from src.core.services.cryptobot_service import (
    InsufficientFundsError,
    PayoutAPIError,
    UserNotFoundError,
    cryptobot_service,
)
from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus
from src.db.models.transaction import TransactionType
from src.db.models.user import User
from src.db.repositories.payout_repo import PayoutRepository
from src.db.repositories.platform_account_repo import PlatformAccountRepo
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

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
        process_payout: Обработать выплату через CryptoBot API
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
            stmt = select(func.sum(Payout.amount)).where(
                Payout.owner_id == owner_user_id,
                Payout.status == PayoutStatus.PENDING,
            )
            result = await session.execute(stmt)
            balance = result.scalar_one() or Decimal("0")
            return balance

    async def get_owner_payouts(
        self,
        owner_user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Payout]:
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
                select(Payout)
                .where(Payout.owner_id == owner_user_id)
                .order_by(Payout.created_at.desc())
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
    ) -> Payout:
        """
        Создать запись о выплате в статусе pending.

        Вызывается после факта публикации поста.

        Args:
            owner_user_id: ID владельца в БД.
            channel_id: ID канала.
            placement_id: ID размещения (mailing_log.id).
            price_per_post: Цена поста в рублях.

        Returns:
            Созданная запись Payout.
        """
        payout_amount, platform_fee = self.calculate_payout(price_per_post)

        async with async_session_factory() as session:
            # Проверяем что payout ещё не создан для этого placement
            existing = await session.get(Payout, placement_id)
            if existing:
                logger.warning(f"Payout already exists for placement {placement_id}")
                return existing

            payout = Payout(
                owner_id=owner_user_id,
                channel_id=channel_id,
                placement_id=placement_id,
                amount=payout_amount,
                platform_fee=platform_fee,
                currency=PayoutCurrency.RUB,
                status=PayoutStatus.PENDING,
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
        Обработать выплату через CryptoBot API.

        Шаги:
        1. Получить Payout из БД по payout_id
        2. Проверить статус: только PENDING → обрабатывать
        3. Проверить минимальную сумму
        4. Получить telegram_id владельца из User
        5. Вызвать cryptobot_service.send_transfer()
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
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return {"success": False, "transfer_id": None, "error": "Payout not found"}

            # Шаг 2: Проверить статус
            if payout.status != PayoutStatus.PENDING:
                logger.warning(
                    f"Payout {payout_id} already processed (status={payout.status.value})"
                )
                return {
                    "success": False,
                    "transfer_id": None,
                    "error": f"Already processed: {payout.status.value}",
                }

            # Шаг 3: Проверить минимальную сумму (конвертируем в USDT для проверки)
            # Используем MIN_PAYOUT из constants (1000 ₽)
            min_payout_rub = float(MIN_PAYOUT)
            if payout.currency == PayoutCurrency.USDT:
                payout_amount = float(payout.amount)
            elif payout.currency == PayoutCurrency.RUB:
                # Конвертируем рубли в USDT по курсу ~90
                usdt_rate = 90
                payout_amount = float(payout.amount) / usdt_rate
            else:
                # Для других валют — прямая конвертация
                payout_amount = float(payout.amount)

            if payout_amount < min_payout_rub:
                logger.warning(
                    f"Payout {payout_id} amount {payout_amount} < minimum {min_payout_rub}"
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

            # Шаг 5: Вызвать CryptoBot API
            try:
                # Определяем валюту для перевода
                transfer_currency = payout.currency.value
                if payout.currency == PayoutCurrency.RUB:
                    # Рубли конвертируем в USDT по курсу ~90
                    transfer_currency = "USDT"
                    usdt_rate = 90
                    transfer_amount = float(payout.amount) / usdt_rate
                else:
                    transfer_amount = float(payout.amount)

                # Формируем комментарий
                channel_username = ""
                if payout.channel:
                    channel_username = (
                        f"@{payout.channel.username}" if payout.channel.username else ""
                    )

                comment = (
                    f"Выплата за размещения{' ' + channel_username if channel_username else ''}"
                )

                # Выполняем перевод
                transfer_result = await cryptobot_service.send_transfer(
                    telegram_id=user.telegram_id,
                    amount=transfer_amount,
                    currency=transfer_currency,
                    comment=comment,
                    disable_notification=False,
                )

                # Шаг 6: Успех — обновляем статус
                payout.status = PayoutStatus.PAID
                payout.tx_hash = transfer_result.get("transfer_id")
                payout.paid_at = payout.created_at  # Используем created_at как paid_at

                await session.flush()

                logger.info(
                    f"Payout {payout_id} completed: {transfer_amount} {transfer_currency} "
                    f"to user {user.telegram_id} | transfer_id={transfer_result.get('transfer_id')}"
                )

                return {
                    "success": True,
                    "transfer_id": transfer_result.get("transfer_id"),
                    "error": None,
                }

            # Шаг 7: Обработка ошибок
            except InsufficientFundsError as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"Insufficient funds: {str(e)}"
                logger.error(f"Payout {payout_id} failed: {error_msg}")

            except UserNotFoundError as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"User not found in CryptoBot: {str(e)}"
                logger.error(f"Payout {payout_id} failed: {error_msg}")

            except PayoutAPIError as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"API error: {str(e)}"
                logger.error(f"Payout {payout_id} failed: {error_msg}")

            except Exception as e:
                payout.status = PayoutStatus.FAILED
                error_msg = f"Unexpected error: {str(e)}"
                logger.exception(f"Payout {payout_id} failed with unexpected error")

            # Записываем ошибку и сохраняем
            payout.wallet_address = error_msg  # Используем wallet_address для хранения ошибки
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
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False

            if payout.status not in (PayoutStatus.PENDING, PayoutStatus.PROCESSING):
                logger.warning(
                    f"Payout {payout_id} cannot be marked as paid (status={payout.status.value})"
                )
                return False

            payout.status = PayoutStatus.PAID
            payout.paid_at = datetime.now(UTC)
            if tx_hash:
                payout.tx_hash = tx_hash

            await session.flush()

            logger.info(f"Payout {payout_id} marked as paid")
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
            payout = await session.get(Payout, payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False

            if payout.status == PayoutStatus.PAID:
                logger.warning(f"Payout {payout_id} already paid, cannot cancel")
                return False

            payout.status = PayoutStatus.CANCELLED
            await session.flush()

            logger.info(f"Payout {payout_id} cancelled")
            return True

    # ─────────────────────────────────────────────
    # Метод для PlacementRequest (Этап 2)
    # ─────────────────────────────────────────────

    async def request_payout_for_placement(
        self,
        owner_id: int,
        amount: Decimal,
        placement_request_id: int,
    ) -> Payout:
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
            Payout объект.

        Raises:
            ValueError: Если amount < MIN_PAYOUT или owner заблокирован.
        """
        from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus

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
        payout = Payout(
            owner_id=owner_id,
            channel_id=0,  # Будет установлено из placement_request
            placement_id=None,  # placement_request_id не FK на mailing_logs
            amount=amount,
            platform_fee=amount * Decimal("0.25"),  # 20% комиссия
            currency=PayoutCurrency.USDT,
            status=PayoutStatus.PENDING,
            wallet_address=None,
            tx_hash=None,
            paid_at=None,
        )

        async with async_session_factory() as session:
            session.add(payout)
            await session.flush()

            logger.info(
                f"Payout request created: {amount} USDT for owner {owner_id}, placement {placement_request_id}"
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
        topups_30d = await txn_repo.sum_topups_window(session, user_id, VELOCITY_WINDOW_DAYS)

        # payouts_30d = await payout_repo.sum_completed_payouts_window(session, user_id, days=VELOCITY_WINDOW_DAYS)
        payout_repo = PayoutRepository(session)
        payouts_30d = await payout_repo.sum_completed_payouts_window(
            session, user_id, VELOCITY_WINDOW_DAYS
        )

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
    ) -> Payout:
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
            active = await payout_repo.get_active_payout(session, user_id)
            if active:
                raise ValueError("У вас уже есть активная заявка на вывод")

            # Velocity check
            await self.check_velocity(session, user_id, gross_amount)

            # Расчёт комиссии: fee = gross * PAYOUT_FEE_RATE (1.5%)
            fee_amount = (gross_amount * PAYOUT_FEE_RATE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            net_amount = gross_amount - fee_amount

            # Списать с earned_rub
            user.earned_rub -= gross_amount

            # platform_account: payout_reserved += gross_amount, profit_accumulated += fee_amount
            platform_repo = PlatformAccountRepo(session)
            await platform_repo.add_to_payout_reserved(session, gross_amount)
            await platform_repo.add_to_profit(session, fee_amount)

            # Transaction(type=REFUND, amount=gross_amount, user_id=user_id)
            txn_repo = TransactionRepository(session)
            await txn_repo.create_transaction(
                user_id=user_id,
                amount=gross_amount,
                transaction_type=TransactionType.REFUND,
                meta_json={"type": "payout_request", "gross_amount": str(gross_amount)},
            )

            # Transaction(type=PAYOUT_FEE, amount=fee_amount, user_id=user_id)
            await txn_repo.create_payout_fee(session, user_id, fee_amount, payout_id=0)

            # Создать PayoutRequest(gross=gross_amount, fee=fee_amount, net=net_amount, status='pending')
            payout = Payout(
                owner_id=user_id,
                channel_id=0,
                placement_id=None,
                gross_amount=gross_amount,
                fee_amount=fee_amount,
                net_amount=net_amount,
                currency=PayoutCurrency.RUB,
                status=PayoutStatus.PENDING,
                wallet_address=None,
                tx_hash=None,
                paid_at=None,
            )
            session.add(payout)
            await session.flush()

            logger.info(
                f"Payout created: gross={gross_amount} ₽, fee={fee_amount} ₽, "
                f"net={net_amount} ₽ for user {user_id}"
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
            payout = await session.get(Payout, payout_id)
            if not payout:
                raise ValueError(f"Payout {payout_id} not found")

            payout.status = PayoutStatus.PAID
            payout.paid_at = datetime.now(UTC)

            # complete_payout: gross_amount and net_amount are required
            if payout.gross_amount is None or payout.net_amount is None:
                raise ValueError(f"Payout {payout_id} missing gross_amount or net_amount")

            # platform_account_repo.complete_payout(session, gross_amount=payout.gross_amount, net_amount=payout.net_amount)
            platform_repo = PlatformAccountRepo(session)
            await platform_repo.complete_payout(session, payout.gross_amount, payout.net_amount)

            await session.flush()

            logger.info(
                f"Payout {payout_id} completed: gross={payout.gross_amount} ₽, net={payout.net_amount} ₽"
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
            payout = await session.get(Payout, payout_id)
            if not payout:
                raise ValueError(f"Payout {payout_id} not found")

            gross_amount = payout.gross_amount or payout.amount
            fee_amount = payout.fee_amount or Decimal("0")

            payout.status = PayoutStatus.CANCELLED
            payout.wallet_address = reason  # Используем для хранения причины

            # UPDATE users SET earned_rub = earned_rub + gross_amount WHERE id = user_id
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(payout.owner_id)
            if user:
                user.earned_rub += gross_amount

            # platform_account: payout_reserved -= gross_amount, profit_accumulated -= fee_amount
            platform_repo = PlatformAccountRepo(session)
            # Для упрощения: вызываем add_to_payout_reserved с отрицательным значением
            # и add_to_profit с отрицательным
            await platform_repo.add_to_payout_reserved(session, -gross_amount)
            if fee_amount > 0:
                await platform_repo.add_to_profit(session, -fee_amount)

            # Transaction(type=REFUND_FULL, amount=gross_amount)
            txn_repo = TransactionRepository(session)
            await txn_repo.create_transaction(
                user_id=payout.owner_id,
                amount=gross_amount,
                transaction_type=TransactionType.REFUND,
                meta_json={"type": "payout_rejected", "reason": reason},
            )

            await session.flush()

            logger.info(f"Payout {payout_id} rejected: reason={reason}, refunded {gross_amount} ₽")


# Глобальный экземпляр
payout_service = PayoutService()
