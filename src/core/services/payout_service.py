"""
PayoutRequest Service — сервис для управления выплатами владельцам каналов.
Спринт 1 — базовая система учёта выплат (80% от цены поста).
Выплаты обрабатываются вручную администратором.
"""

import logging
from datetime import UTC, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.fees import (
    OWNER_SHARE_RATE,
    PLATFORM_COMMISSION_RATE,
)
from src.core.exceptions import (
    PayoutAlreadyFinalizedError,
    PayoutNotFoundError,
)
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.transaction import TransactionType
from src.db.repositories.audit_log_repo import AuditLogRepo
from src.db.repositories.platform_account_repo import PlatformAccountRepository
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
        complete_payout: Завершить выплату (caller-owned session)
        reject_payout: Отклонить выплату c возвратом на earned_rub (caller-owned)
        approve_request: Админ одобрил → complete_payout под FOR UPDATE
        reject_request: Админ отклонил → reject_payout под FOR UPDATE с финальным
            статусом rejected
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self.payout_percentage = OWNER_SHARE_RATE  # 80% владельцу
        self.platform_percentage = PLATFORM_COMMISSION_RATE  # 20% платформе

    async def complete_payout(
        self,
        session: AsyncSession,
        payout_id: int,
    ) -> None:
        """
        Администратор подтвердил перевод — завершить выплату.

        Service Transaction Contract (CLAUDE.md § S-48): caller владеет
        транзакцией. Метод ожидает уже открытую (или autobegin'утую)
        сессию и выполняет только flush; commit/rollback — за caller'ом.

        Args:
            session: Асинхронная сессия с активной транзакцией caller'а.
            payout_id: ID заявки на выплату.
        """
        payout = await session.get(PayoutRequest, payout_id)
        if not payout:
            raise ValueError(f"PayoutRequest {payout_id} not found")

        payout.status = PayoutStatus.paid
        payout.processed_at = datetime.now(UTC)

        # complete_payout: gross_amount and net_amount are required
        if payout.gross_amount is None or payout.net_amount is None:
            raise ValueError(f"PayoutRequest {payout_id} missing gross_amount or net_amount")

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

        Service Transaction Contract (CLAUDE.md § S-48): caller владеет
        транзакцией. Метод ожидает уже открытую (или autobegin'утую)
        сессию и выполняет только flush; commit/rollback — за caller'ом.

        Args:
            session: Асинхронная сессия с активной транзакцией caller'а.
            payout_id: ID заявки на выплату.
            reason: Причина отклонения.
        """
        payout = await session.get(PayoutRequest, payout_id)
        if not payout:
            raise ValueError(f"PayoutRequest {payout_id} not found")

        gross_amount = payout.gross_amount or Decimal("0")
        fee_amount = payout.fee_amount or Decimal("0")

        payout.status = PayoutStatus.cancelled
        payout.rejection_reason = reason  # хранение причины

        # UPDATE users SET earned_rub = earned_rub + gross_amount WHERE id = user_id
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(payout.owner_id)
        if user:
            user.earned_rub += gross_amount

        # platform_account: payout_reserved -= gross_amount, profit_accumulated -= fee_amount
        platform_repo = PlatformAccountRepository(session)
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

    # ══════════════════════════════════════════════════════════════
    # Admin panel — approve / reject payout requests (S-42)
    # ══════════════════════════════════════════════════════════════

    async def approve_request(
        self,
        payout_id: int,
        admin_id: int,
    ) -> PayoutRequest:
        """
        Админ одобрил выплату: pending/processing → paid.

        Выполняется в одной сессии под `SELECT … FOR UPDATE` блокировкой
        строки `PayoutRequest`: два параллельных approve на одном
        `payout_id` сериализуются — второй увидит уже финализированную
        запись и поднимет `ValueError("already finalized")`.

        Порядок блокировок: `PayoutRequest` → `PlatformAccount` (через
        `complete_payout`/`platform_repo.complete_payout`). Тот же порядок
        соблюдается в `reject_request` — deadlock невозможен.

        Args:
            payout_id: ID заявки.
            admin_id: ID админа (User.id), выполнившего действие.

        Returns:
            Обновлённая `PayoutRequest`.

        Raises:
            ValueError: Если заявка не найдена или уже в финальном статусе.
        """
        async with async_session_factory() as session:
            async with session.begin():
                stmt = select(PayoutRequest).where(PayoutRequest.id == payout_id).with_for_update()
                payout = (await session.execute(stmt)).scalar_one_or_none()
                if payout is None:
                    raise PayoutNotFoundError(
                        f"PayoutRequest {payout_id} not found",
                        extra={"payout_id": payout_id},
                    )
                if payout.status in (
                    PayoutStatus.paid,
                    PayoutStatus.rejected,
                    PayoutStatus.cancelled,
                ):
                    raise PayoutAlreadyFinalizedError(
                        f"PayoutRequest {payout_id} already finalized "
                        f"(status={payout.status.value})",
                        extra={"payout_id": payout_id, "status": payout.status.value},
                    )

                await self.complete_payout(session, payout_id)
                payout.admin_id = admin_id
                await AuditLogRepo(session).log(
                    action="payout_approve",
                    resource_type="payout_request",
                    user_id=admin_id,
                    resource_id=payout.id,
                    target_user_id=payout.owner_id,
                    extra={
                        "amount": str(payout.gross_amount),
                        "method": payout.payout_method_type,
                    },
                )
                # commit — неявный, на выходе из session.begin()

            await session.refresh(payout)
            logger.info(f"PayoutRequest {payout_id} approved by admin {admin_id}")
            return payout

    async def reject_request(
        self,
        payout_id: int,
        admin_id: int,
        reason: str,
    ) -> PayoutRequest:
        """
        Админ отклонил выплату: возвращает деньги на `earned_rub`
        и ставит статус `rejected` (не `cancelled` — cancelled — это отмена
        пользователем).

        Та же стратегия, что в `approve_request`: одна сессия, `SELECT …
        FOR UPDATE` на `PayoutRequest`, тот же порядок блокировок
        (`PayoutRequest` → `PlatformAccount`).

        Args:
            payout_id: ID заявки.
            admin_id: ID админа.
            reason: Причина отклонения.

        Returns:
            Обновлённая `PayoutRequest`.

        Raises:
            ValueError: Если заявка не найдена или уже в финальном статусе.
        """
        async with async_session_factory() as session:
            async with session.begin():
                stmt = select(PayoutRequest).where(PayoutRequest.id == payout_id).with_for_update()
                payout = (await session.execute(stmt)).scalar_one_or_none()
                if payout is None:
                    raise PayoutNotFoundError(
                        f"PayoutRequest {payout_id} not found",
                        extra={"payout_id": payout_id},
                    )
                if payout.status in (
                    PayoutStatus.paid,
                    PayoutStatus.rejected,
                    PayoutStatus.cancelled,
                ):
                    raise PayoutAlreadyFinalizedError(
                        f"PayoutRequest {payout_id} already finalized "
                        f"(status={payout.status.value})",
                        extra={"payout_id": payout_id, "status": payout.status.value},
                    )

                await self.reject_payout(session, payout_id, reason)
                # reject_payout выставляет status=cancelled — поверх него
                # ставим финальный rejected (cancelled = отмена пользователем).
                payout.status = PayoutStatus.rejected
                payout.admin_id = admin_id
                await AuditLogRepo(session).log(
                    action="payout_reject",
                    resource_type="payout_request",
                    user_id=admin_id,
                    resource_id=payout.id,
                    target_user_id=payout.owner_id,
                    extra={"reason": reason},
                )

            await session.refresh(payout)
            logger.info(f"PayoutRequest {payout_id} rejected by admin {admin_id}: {reason}")
            return payout


# Глобальный экземпляр
payout_service = PayoutService()
