"""ContractRepo for Contract model operations."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy import update as sa_update

from src.db.models.contract import Contract
from src.db.models.contract_signature import ContractSignature
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ContractRepo(BaseRepository[Contract]):
    """Репозиторий для работы с договорами."""

    model = Contract

    async def get_by_user_and_type(self, user_id: int, contract_type: str) -> Contract | None:
        """Получить договор по user_id и типу."""
        result = await self.session.execute(
            select(Contract).where(
                Contract.user_id == user_id,
                Contract.contract_type == contract_type,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_placement(
        self, user_id: int, placement_request_id: int
    ) -> Contract | None:
        """Получить договор по user_id и placement_request_id."""
        result = await self.session.execute(
            select(Contract).where(
                Contract.user_id == user_id,
                Contract.placement_request_id == placement_request_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int, contract_type: str | None = None) -> list[Contract]:
        """Получить список договоров пользователя."""
        conditions = [Contract.user_id == user_id]
        if contract_type is not None:
            conditions.append(Contract.contract_type == contract_type)
        result = await self.session.execute(
            select(Contract).where(*conditions).order_by(Contract.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_signed(self, contract_id: int, method: str, ip: str | None) -> Contract:
        """Пометить договор как подписанный."""
        contract = await self.get_by_id(contract_id)
        if contract is None:
            raise ValueError(f"Contract id={contract_id} not found")
        contract.contract_status = "signed"
        contract.signature_method = method
        contract.signature_ip = ip
        contract.signed_at = datetime.now(tz=UTC)
        await self.session.flush()
        await self.session.refresh(contract)
        return contract

    async def create_signature(
        self,
        contract_id: int,
        user_id: int,
        telegram_id: int,
        role: str,
        legal_status: str,
        signature_method: str,
        document_hash: str,
        template_version: str = "1.0",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Записать событие подписания в audit trail. Никогда не блокирует основную операцию."""
        try:
            sig = ContractSignature(
                contract_id=contract_id,
                user_id=user_id,
                telegram_id=telegram_id,
                role=role,
                legal_status=legal_status,
                signature_method=signature_method,
                document_hash=document_hash,
                template_version=template_version,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.session.add(sig)
            await self.session.flush()
        except Exception:
            logger.exception(
                "Failed to record contract signature audit entry, contract_id=%s", contract_id
            )

    async def get_framework_contract(self, user_id: int, role: str) -> Contract | None:
        """Получить подписанный рамочный договор рекламодателя для данного пользователя и роли."""
        result = await self.session.execute(
            select(Contract).where(
                Contract.user_id == user_id,
                Contract.contract_type == "advertiser_framework",
                Contract.role == role,
                Contract.contract_status == "signed",
            )
        )
        return result.scalar_one_or_none()

    async def request_kep(self, contract_id: int, email: str) -> None:
        """Пометить договор как запрошенный для КЭП."""
        await self.session.execute(
            sa_update(Contract)
            .where(Contract.id == contract_id)
            .values(kep_requested=True, kep_request_email=email)
        )
        await self.session.flush()

    async def list_by_placement(self, placement_request_id: int) -> list[Contract]:
        """Получить список договоров по placement_request_id."""
        result = await self.session.execute(
            select(Contract)
            .where(Contract.placement_request_id == placement_request_id)
            .order_by(Contract.created_at.asc())
        )
        return list(result.scalars().all())
