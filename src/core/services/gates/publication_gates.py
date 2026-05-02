"""Pre-publication gate checkers (G08-G10).

G08: ERID registered with ОРД
G09: ORD contract reported
G10: Placement text marked as advertising (`Реклама. erid: ...`)

All Phase 3b stubs.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest


async def check_g08(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G08_ERID_REGISTERED — Phase 3b stub."""
    raise NotImplementedError(f"Phase 3b: {PlacementGate.G08_ERID_REGISTERED.name}")


async def check_g09(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G09_ORD_CONTRACT_REPORTED — Phase 3b stub."""
    raise NotImplementedError(f"Phase 3b: {PlacementGate.G09_ORD_CONTRACT_REPORTED.name}")


async def check_g10(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G10_PLACEMENT_TEXT_MARKED — Phase 3b stub."""
    raise NotImplementedError(f"Phase 3b: {PlacementGate.G10_PLACEMENT_TEXT_MARKED.name}")
