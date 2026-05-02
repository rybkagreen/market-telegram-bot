"""Pre-payout gate checkers (G13-G18).

G13: Publication period elapsed (configured display window has passed)
G14: Act of completed services generated
G15: Act signed by both sides (Phase 4 — КЭП)
G16: Tax receipt issued (Phase 4 — Мой налог real integration)
G17: VAT obligation handled
G18: Payout reported to ОРД

G13/G14/G17/G18 are Phase 3b stubs; G15/G16 are Phase 4 stubs.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest


async def check_g13(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G13_PUBLICATION_PERIOD_ELAPSED — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G13_PUBLICATION_PERIOD_ELAPSED.name}"
    )


async def check_g14(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G14_ACT_GENERATED — Phase 3b stub."""
    raise NotImplementedError(f"Phase 3b: {PlacementGate.G14_ACT_GENERATED.name}")


async def check_g15(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G15_ACT_SIGNED_BOTH_SIDES — Phase 4 stub."""
    raise NotImplementedError(f"Phase 4: {PlacementGate.G15_ACT_SIGNED_BOTH_SIDES.name}")


async def check_g16(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G16_TAX_RECEIPT_ISSUED — Phase 4 stub."""
    raise NotImplementedError(f"Phase 4: {PlacementGate.G16_TAX_RECEIPT_ISSUED.name}")


async def check_g17(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G17_VAT_OBLIGATION_HANDLED — Phase 3b stub."""
    raise NotImplementedError(f"Phase 3b: {PlacementGate.G17_VAT_OBLIGATION_HANDLED.name}")


async def check_g18(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G18_PAYOUT_REPORTED_TO_ORD — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G18_PAYOUT_REPORTED_TO_ORD.name}"
    )
