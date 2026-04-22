"""
Integration-тест полного жизненного цикла выплаты (FIX_PLAN_06 §6.5).

Цель — покрыть связку PayoutService.approve_request / reject_request поверх
реальной Postgres-схемы (testcontainers) и зафиксировать финансовые
инварианты, которые юнит-тесты с моками пропустили бы:
    * Смена статуса pending → paid / rejected
    * Фиксация `admin_id` и `processed_at`
    * Обновление `PlatformAccount.payout_reserved` / `total_payouts`
    * Возврат `earned_rub` владельцу при reject

Изоляция (plan-06, 2026-04-21):
    Используется SAVEPOINT-pattern из SQLAlchemy 2 docs (см.
    `tests/integration/README.md`). Все сессии — на одном connection'е
    под одной наружной транзакцией; `join_transaction_mode=
    "create_savepoint"` превращает service-внутренний `session.begin()`
    в SAVEPOINT, наружный rollback откатывает всё → TRUNCATE между
    тестами не нужен.

    Тест `test_payout_concurrent.py` живёт на engine-bound фабрике с
    TRUNCATE — для honest-concurrency через asyncio.gather.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.services import payout_service as payout_service_module
from src.db import session as session_module
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.platform_account import PlatformAccount
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


def _unique_int() -> int:
    """32-bit positive int, уникальный в рамках процесса."""
    return uuid.uuid4().int % 2_000_000_000


@pytest_asyncio.fixture
async def bound_factory(test_engine: Any) -> AsyncGenerator[Any]:
    """SAVEPOINT-isolated session factory (plan-06).

    Открывает один connection, заворачивает его в наружную транзакцию,
    отдаёт `async_sessionmaker(bind=connection,
    join_transaction_mode="create_savepoint")`. Все сессии — и тестовые
    seed'ы, и service-внутренние через async_session_factory — садятся
    на тот же connection. Каждый `async with session.begin():` внутри
    сервиса теперь открывает SAVEPOINT (а не реальную транзакцию), и
    наружный `trans.rollback()` откатывает всё разом.

    Преимущества над прежним engine + TRUNCATE подходом:
        * Нет cross-test leakage — каждый тест видит чистую базу.
        * Sequence не сбрасываются — нет «прошло/упало от порядка».
        * Параллельный прогон (`pytest -n auto`) безопасен.
        * Быстрее: SAVEPOINT rollback ≪ TRUNCATE … RESTART IDENTITY.

    Несовместим с `asyncio.gather` (asyncpg single-threaded на один
    connection). Concurrent-тесты используют отдельную фабрику,
    см. `test_payout_concurrent.py`.
    """
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        try:
            factory = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            with (
                patch.object(session_module, "async_session_factory", factory),
                patch.object(payout_service_module, "async_session_factory", factory),
            ):
                yield factory
        finally:
            await trans.rollback()


async def _seed_pending_payout(factory: Any) -> tuple[int, int, int]:
    """Создать admin + owner + PlatformAccount + PayoutRequest (pending).

    Returns: (admin_id, owner_id, payout_id).
    """
    gross = Decimal("1000.00")
    fee = Decimal("15.00")
    net = Decimal("985.00")

    async with factory() as session:
        admin = User(
            telegram_id=_unique_int(),
            username=f"admin_{_unique_int()}",
            first_name="Admin",
            is_admin=True,
            balance_rub=Decimal("0"),
        )
        owner = User(
            telegram_id=_unique_int(),
            username=f"owner_{_unique_int()}",
            first_name="Owner",
            balance_rub=Decimal("0"),
            earned_rub=Decimal("0"),
        )
        session.add_all([admin, owner])
        await session.flush()

        # PlatformAccount — singleton с id=1. В payout_reserved уже лежит
        # наша заявка (эмулируем: request_payout ранее положил туда gross).
        platform = PlatformAccount(
            id=1,
            escrow_reserved=Decimal("0"),
            payout_reserved=gross,
            profit_accumulated=fee,
            total_topups=Decimal("0"),
            total_payouts=Decimal("0"),
        )
        session.add(platform)

        payout = PayoutRequest(
            owner_id=owner.id,
            gross_amount=gross,
            fee_amount=fee,
            net_amount=net,
            status=PayoutStatus.pending,
            requisites=f"REQ-{uuid.uuid4().hex[:12]}",
        )
        session.add(payout)
        await session.commit()

        return admin.id, owner.id, payout.id


class TestApproveLifecycle:
    """FIX_PLAN_06 §6.5 — happy path approve."""

    async def test_approve_moves_pending_to_paid(self, bound_factory: Any) -> None:
        from src.core.services.payout_service import payout_service

        admin_id, _owner_id, payout_id = await _seed_pending_payout(bound_factory)

        result = await payout_service.approve_request(payout_id, admin_id)
        assert result.status == PayoutStatus.paid

        # Проверяем фактическое состояние в БД (не in-memory объект)
        async with bound_factory() as session:
            refreshed = await session.get(PayoutRequest, payout_id)
            assert refreshed is not None
            assert refreshed.status == PayoutStatus.paid
            assert refreshed.admin_id == admin_id
            assert refreshed.processed_at is not None

            platform = await session.get(PlatformAccount, 1)
            assert platform is not None
            # После complete_payout: payout_reserved уменьшен на gross.
            # (total_payouts не обновляется в текущей реализации
            # platform_account_repo.complete_payout, см. S-42.)
            assert platform.payout_reserved == Decimal("0")

    async def test_approve_on_paid_raises(self, bound_factory: Any) -> None:
        """Повторный approve уже финализированной выплаты → ValueError."""
        from src.core.services.payout_service import payout_service

        admin_id, _owner_id, payout_id = await _seed_pending_payout(bound_factory)

        await payout_service.approve_request(payout_id, admin_id)
        with pytest.raises(ValueError, match="already finalized"):
            await payout_service.approve_request(payout_id, admin_id)


class TestRejectLifecycle:
    """FIX_PLAN_06 §6.5 — happy path reject."""

    async def test_reject_moves_pending_to_rejected_and_refunds(self, bound_factory: Any) -> None:
        from src.core.services.payout_service import payout_service

        admin_id, owner_id, payout_id = await _seed_pending_payout(bound_factory)

        result = await payout_service.reject_request(
            payout_id, admin_id, reason="Невалидные реквизиты"
        )
        assert result.status == PayoutStatus.rejected

        async with bound_factory() as session:
            refreshed = await session.get(PayoutRequest, payout_id)
            assert refreshed is not None
            assert refreshed.status == PayoutStatus.rejected
            assert refreshed.admin_id == admin_id
            assert refreshed.rejection_reason == "Невалидные реквизиты"

            owner = await session.get(User, owner_id)
            assert owner is not None
            # reject_payout возвращает gross на earned_rub
            assert owner.earned_rub == Decimal("1000.00")

    async def test_reject_requires_unfinalized(self, bound_factory: Any) -> None:
        """Нельзя отклонить уже paid-выплату."""
        from src.core.services.payout_service import payout_service

        admin_id, _owner_id, payout_id = await _seed_pending_payout(bound_factory)
        await payout_service.approve_request(payout_id, admin_id)

        with pytest.raises(ValueError, match="already finalized"):
            await payout_service.reject_request(payout_id, admin_id, reason="поздно")
