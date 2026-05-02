"""Owner-side gate checkers (G04-G06).

G04: Owner legal profile complete
G05: Owner framework contract signed
G06: Owner payout method valid

All Phase 3b stubs.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest


async def check_g04(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G04_OWNER_LEGAL_PROFILE_COMPLETE — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE.name}"
    )


async def check_g05(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G05_OWNER_FRAMEWORK_CONTRACT_SIGNED — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED.name}"
    )


async def check_g06(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G06_OWNER_PAYOUT_METHOD_VALID — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID.name}"
    )
