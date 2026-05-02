"""Advertiser-side gate checkers (G01-G03).

G01: Advertiser legal profile complete
G02: Advertiser framework contract signed
G03: Advertiser legal_status compliant (per legal_status type)

All Phase 3b stubs.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest


async def check_g01(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G01_ADVERTISER_LEGAL_PROFILE_COMPLETE — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE.name}"
    )


async def check_g02(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED.name}"
    )


async def check_g03(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G03_ADVERTISER_LEGAL_STATUS_COMPLIANT — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT.name}"
    )
