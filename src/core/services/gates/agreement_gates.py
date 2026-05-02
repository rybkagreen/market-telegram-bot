"""Supplementary-agreement gate checker (G07).

G07: Supplementary agreement signed (per-placement addendum to framework contract).

Phase 4 stub — requires КЭП integration shipped in Phase 4.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest


async def check_g07(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G07_SUPPLEMENTARY_AGREEMENT_SIGNED — Phase 4 stub."""
    raise NotImplementedError(
        f"Phase 4: {PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED.name}"
    )
