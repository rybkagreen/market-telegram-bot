"""ContractRepo for Contract model operations."""

import logging
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from src.db.models.contract import Contract
from src.db.models.contract_event import ContractEvent
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

    async def get_latest_acceptance(self, user_id: int, contract_type: str) -> Contract | None:
        """Latest signed Contract row of given type for user, ordered by signed_at DESC.

        Used by needs_accept_rules() to compare stored template_version against the
        current CONTRACT_TEMPLATE_VERSION constant. Filters by contract_status='signed'
        so unsigned drafts don't count as acceptance.
        """
        result = await self.session.execute(
            select(Contract)
            .where(
                Contract.user_id == user_id,
                Contract.contract_type == contract_type,
                Contract.contract_status == "signed",
            )
            .order_by(Contract.signed_at.desc().nulls_last())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_placement(self, user_id: int, placement_id: int) -> Contract | None:
        """Получить договор по user_id и placement_id."""
        result = await self.session.execute(
            select(Contract).where(
                Contract.user_id == user_id,
                Contract.placement_id == placement_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_supplementary_for_placement(self, placement_id: int) -> list[Contract]:
        """Все ДС-строки для placement (обе стороны: advertiser + owner, если существуют)."""
        result = await self.session.execute(
            select(Contract).where(
                Contract.placement_id == placement_id,
                Contract.contract_type == "supplementary_agreement",
            )
        )
        return list(result.scalars().all())

    async def get_by_placement_and_role(
        self, placement_id: int, role: Literal["owner", "advertiser"]
    ) -> Contract | None:
        """Одна ДС для пары (placement, role). Используется для idempotency check."""
        result = await self.session.execute(
            select(Contract).where(
                Contract.placement_id == placement_id,
                Contract.contract_type == "supplementary_agreement",
                Contract.role == role,
            )
        )
        return result.scalar_one_or_none()

    async def count_unsigned_supplementary_for_user(self, user_id: int) -> int:
        """Count ДС-строк пользователя, не дошедших до signed (для P6 badge)."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Contract)
            .where(
                Contract.user_id == user_id,
                Contract.contract_type == "supplementary_agreement",
                Contract.contract_status != "signed",
                Contract.contract_status != "cancelled",
                Contract.contract_status != "expired",
            )
        )
        return int(result.scalar_one())

    async def exists_signed_supplementary_both_sides(self, placement_id: int) -> bool:
        """True iff BOTH owner+advertiser ДС exist with contract_status='signed'.

        Backs G07_SUPPLEMENTARY_AGREEMENT_SIGNED gate body (PROMPT 27 Step 7).
        """
        result = await self.session.execute(
            select(Contract.role).where(
                Contract.placement_id == placement_id,
                Contract.contract_type == "supplementary_agreement",
                Contract.contract_status == "signed",
            )
        )
        signed_roles = {row[0] for row in result.all()}
        return signed_roles == {"owner", "advertiser"}

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

    async def record_event(
        self,
        contract_id: int,
        event_type: str,
        actor_user_id: int | None = None,
        event_metadata: dict[str, Any] | None = None,
    ) -> ContractEvent:
        """Append ContractEvent row для аудита sub-stage progression (BL-037).

        event_type validation defers to Pydantic discriminator schema added in
        PROMPT 27 Step 4 (src/core/schemas/contract_event.py).
        S-48 Pattern 1: flush only, caller owns transaction.
        """
        event = ContractEvent(
            contract_id=contract_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            event_metadata=event_metadata,
        )
        self.session.add(event)
        await self.session.flush()
        return event

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

    async def has_signed_framework(self, user_id: int, role: str) -> bool:
        """Check whether user has a fully-signed framework contract for given role.

        Thin predicate over `get_framework_contract` — returns True only if
        a contract exists AND its signed_at timestamp is set.
        """
        contract = await self.get_framework_contract(user_id, role)
        return contract is not None and contract.signed_at is not None
