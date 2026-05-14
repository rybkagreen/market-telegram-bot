"""PlacementGate — 18 legal compliance gates (Phase 3 framework).

Grouped by transition phase. Each gate name encodes (sequence, scope,
condition) so call sites read clearly without referring back to a table.
G03 named LEGAL_STATUS_COMPLIANT (not LEGAL_TYPE_*) — matches the
legal_profiles.legal_status DB column; the older LEGAL_TYPE_* naming
in frozen research artifacts is historical.

Implementation per gate в src/core/services/gates/ (Phase 3b).
G07/G15/G16 return ``reason_code="phase4_pending"`` (markers) — real
bodies require МES Acts + КЭП + Мой налог real integration shipped in
Phase 4. G17/G18 mirror this with ``reason_code="phase5_pending"``.
"""

from enum import StrEnum


class PlacementGate(StrEnum):
    # ── Pre-creation (advertiser, before placement creation) ────────────
    G01_ADVERTISER_LEGAL_PROFILE_COMPLETE = "G01_ADVERTISER_LEGAL_PROFILE_COMPLETE"
    G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED = "G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED"
    G03_ADVERTISER_LEGAL_STATUS_COMPLIANT = "G03_ADVERTISER_LEGAL_STATUS_COMPLIANT"

    # ── Owner-side (channel-add hard precondition — DECLINE on fail) ─────
    G04_OWNER_LEGAL_PROFILE_COMPLETE = "G04_OWNER_LEGAL_PROFILE_COMPLETE"
    G05_OWNER_FRAMEWORK_CONTRACT_SIGNED = "G05_OWNER_FRAMEWORK_CONTRACT_SIGNED"
    G06_OWNER_PAYOUT_METHOD_VALID = "G06_OWNER_PAYOUT_METHOD_VALID"

    # ── Pre-escrow (placement → pending_payment) ────────────────────────
    G07_SUPPLEMENTARY_AGREEMENT_SIGNED = "G07_SUPPLEMENTARY_AGREEMENT_SIGNED"  # Phase 4

    # ── Pre-publication (escrow → published) ────────────────────────────
    G08_ERID_REGISTERED = "G08_ERID_REGISTERED"
    G09_ORD_CONTRACT_REPORTED = "G09_ORD_CONTRACT_REPORTED"
    G10_PLACEMENT_TEXT_MARKED = "G10_PLACEMENT_TEXT_MARKED"

    # ── Post-publication (published → completed) ────────────────────────
    G11_PUBLICATION_VERIFIED = "G11_PUBLICATION_VERIFIED"
    G12_PUBLICATION_REPORTED_TO_ORD = (
        # ORD report by end of next month per ФЗ-38 ст. 18.1 + ПП-1427
        "G12_PUBLICATION_REPORTED_TO_ORD"
    )

    # ── Pre-payout (completed → payout_processing) ──────────────────────
    G13_PUBLICATION_PERIOD_ELAPSED = "G13_PUBLICATION_PERIOD_ELAPSED"
    G14_ACT_GENERATED = "G14_ACT_GENERATED"
    G15_ACT_SIGNED_BOTH_SIDES = "G15_ACT_SIGNED_BOTH_SIDES"  # Phase 4 (КЭП)
    G16_TAX_RECEIPT_ISSUED = "G16_TAX_RECEIPT_ISSUED"  # Phase 4 (Мой налог real)
    G17_VAT_OBLIGATION_HANDLED = "G17_VAT_OBLIGATION_HANDLED"
    G18_PAYOUT_REPORTED_TO_ORD = "G18_PAYOUT_REPORTED_TO_ORD"

    # ── Channel-add (owner-side, ФЗ-303 blogger registry — BL-107) ──────
    G19_BLOGGER_REGISTRY_VERIFIED = "G19_BLOGGER_REGISTRY_VERIFIED"
