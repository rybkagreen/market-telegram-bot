"""Gate result reason codes — i18n keys surfaced via GateResult.reason_code.

Per plan §3.B.2 these are i18n keys the frontend keys off for translation
and conditional rendering. Snake_case values; no further prefix needed
(GateResult.gate field already names the gate).

Mirrors PlacementGate(StrEnum) shape — sibling enum in same package.
"""

from enum import StrEnum


class GateReason(StrEnum):
    OK = "ok"

    # Phase 3a stub markers (existing G07/G15/G16 use string literals;
    # this enum entry exists so future stub-markup migration is uniform)
    PHASE4_PENDING = "phase4_pending"
    PHASE5_PENDING = "phase5_pending"

    # G01 / G03 — legal profile state
    USER_NOT_FOUND = "user_not_found"
    LEGAL_PROFILE_MISSING = "legal_profile_missing"
    LEGAL_PROFILE_INCOMPLETE = "legal_profile_incomplete"

    # G02 — framework contract state
    FRAMEWORK_CONTRACT_UNSIGNED = "framework_contract_unsigned"

    # G03 — checksum failures
    INN_MISSING = "inn_missing"
    INN_CHECKSUM_INVALID = "inn_checksum_invalid"
    OGRN_MISSING = "ogrn_missing"
    OGRN_CHECKSUM_INVALID = "ogrn_checksum_invalid"
    OGRNIP_MISSING = "ogrnip_missing"
    OGRNIP_CHECKSUM_INVALID = "ogrnip_checksum_invalid"
    UNKNOWN_LEGAL_STATUS = "unknown_legal_status"

    # 5b.5 additions — publication + post-publication gates
    ERID_NOT_REGISTERED = "erid_not_registered"
    ORD_CONTRACT_NOT_REPORTED = "ord_contract_not_reported"
    PLACEMENT_TEXT_NOT_MARKED = "placement_text_not_marked"
    PUBLICATION_NOT_VERIFIED = "publication_not_verified"
    PUBLICATION_NOT_REPORTED_TO_ORD = "publication_not_reported_to_ord"

    # 5b.6 additions — payout-side gates (G13/G14)
    PUBLICATION_PERIOD_NOT_ELAPSED = "publication_period_not_elapsed"
    ACT_NOT_GENERATED = "act_not_generated"

    # 5b.7a additions — G06 real-now (channel-add precondition)
    PAYOUT_METHOD_INVALID = "payout_method_invalid"
