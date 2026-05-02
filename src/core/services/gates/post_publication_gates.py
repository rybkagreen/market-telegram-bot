"""Post-publication gate checkers (G11-G12).

G11: Publication verified (post is live in the channel and matches sent text)
G12: Publication reported to ОРД (per ФЗ-38 ст. 18.1 + ПП-1427)

All Phase 3b stubs.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest


async def check_g11(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G11_PUBLICATION_VERIFIED — Phase 3b stub."""
    raise NotImplementedError(f"Phase 3b: {PlacementGate.G11_PUBLICATION_VERIFIED.name}")


async def check_g12(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G12_PUBLICATION_REPORTED_TO_ORD — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD.name}"
    )
