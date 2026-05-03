"""Gate-checker functions for legal compliance.

Each gate-checker is a pure async function with signature:
    async def check_gNN(session: AsyncSession, placement: PlacementRequest) -> GateResult

Block 2 ships only NotImplementedError stubs. Phase 3b fills validation logic.
"""

from . import (
    advertiser_gates,
    agreement_gates,
    owner_gates,
    payout_gates,
    post_publication_gates,
    publication_gates,
)

__all__ = [
    "advertiser_gates",
    "agreement_gates",
    "owner_gates",
    "payout_gates",
    "post_publication_gates",
    "publication_gates",
]
