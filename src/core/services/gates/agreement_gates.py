"""Supplementary-agreement gate checker (G07).

G07: Supplementary agreement signed (per-placement addendum to framework contract).

Phase 4 real body: queries ContractRepo for the placement's
``supplementary_agreement`` Contract rows; requires BOTH advertiser-side and
owner-side rows with ``contract_status='signed'``. Until the pair is signed,
the gate blocks transitions ``pending_owner|counter_offer → pending_payment``.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.contract_repo import ContractRepo


async def check_g07(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G07_SUPPLEMENTARY_AGREEMENT_SIGNED — both parties signed paired ДС.

    Per plan §3.B (pre-escrow gates), applies before the
    ``pending_owner → pending_payment`` and ``counter_offer → pending_payment``
    transitions.

    Body: ``ContractRepo.exists_signed_supplementary_both_sides(placement.id)``
    returns True iff there exist ``contract_type='supplementary_agreement'``
    rows with ``contract_status='signed'`` for BOTH roles (advertiser + owner).

    Failure reason code: ``SUPPLEMENTARY_NOT_SIGNED`` (distinct from
    PHASE4_PENDING marker — periodic task classifies as user-actionable
    real-fail, not "not yet wired" placeholder).

    Pattern 1 (S-48): receives session, read-only query via ContractRepo.
    """
    repo = ContractRepo(session)
    both_signed = await repo.exists_signed_supplementary_both_sides(placement.id)

    return GateResult(
        gate=PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED,
        passed=both_signed,
        blocker=not both_signed,
        reason_code=(
            GateReason.OK.value if both_signed else GateReason.SUPPLEMENTARY_NOT_SIGNED.value
        ),
        remediation_url=None if both_signed else "/contracts/supplementary",
    )
