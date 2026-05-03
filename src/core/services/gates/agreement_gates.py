"""Supplementary-agreement gate checker (G07).

G07: Supplementary agreement signed (per-placement addendum to framework contract).

Phase 4 pending marker — real body (МES Acts API integration + КЭП
verification) lands in Phase 4. Marker reuses ``PHASE4_PENDING``
(mirror G15/G16; sibling pattern to G17/G18 ``PHASE5_PENDING``).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest


async def check_g07(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G07_SUPPLEMENTARY_AGREEMENT_SIGNED — Phase 4 pending marker.

    Per plan §3.B (pre-escrow gates), applies before the
    ``pending_owner → pending_payment`` and ``counter_offer → pending_payment``
    transitions. Real body — query Acts table for the placement's
    supplementary-agreement Act, verify both signatures present — is
    Phase 4 territory (МES Acts API + КЭП verification).

    Pattern 1 (S-48): receives session (unused), no commit/flush/rollback.
    """
    return GateResult(
        gate=PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED,
        passed=False,
        blocker=True,
        reason_code=GateReason.PHASE4_PENDING.value,
        remediation_url=None,
    )
