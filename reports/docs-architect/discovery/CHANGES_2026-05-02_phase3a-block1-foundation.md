# CHANGES — Phase 3a Block 1 (Schema foundation)

**Scope:** Block 1 (commits `5ab1651`, `9556b49`) on
`feature/legal-compliance-gates`. This is a partial closure note for
Phase 3a Foundation; the full Phase 3a closure (Blocks 2 + 3 + 4) is
pending and will land its own comprehensive CHANGES at Block 4.1. This
mid-flight CHANGES exists because the Stop hook insists on per-batch
documentation regardless of the planned Block 4 bundle.

## Affected files

### Modified

- `src/db/migrations/versions/0001_initial_schema.py` — 9 new columns
  (pre-prod immutable-only-`0001` exception per CLAUDE.md migration
  policy). No new revisions; head remains `e6a88faa9fa0`.
- `src/db/models/legal_profile.py` — 4 new mapped columns mirroring
  the migration.
- `src/db/models/payout.py` — 1 new mapped column.
- `src/db/models/placement_request.py` — 2 new mapped columns.
- `src/db/models/ord_registration.py` — 2 new mapped columns.
- `src/api/schemas/legal_profile.py` — `LegalProfileResponse` picks up
  4 new fields (verification flags, not PII; safe on the existing
  legal-profile API).
- `tests/unit/snapshots/legal_profile_response.json` — regenerated
  (S-47 contract-drift snapshot).
- `tests/unit/test_contract_schemas.py` — registered
  `GateResultResponse` in `CONTRACT_SCHEMAS`.

### Created

- `src/core/enums/__init__.py` — new package for cross-cutting
  service-domain enums (the first one).
- `src/core/enums/placement_gate.py` — `PlacementGate` StrEnum, 18
  values grouped by transition phase.
- `src/core/schemas/gate_result.py` — `GateResult` dataclass
  (service-layer return type) + `GateResultResponse` Pydantic schema
  (API surface).
- `tests/unit/snapshots/gate_result_response.json` — new snapshot.

## Business logic impact

**None yet.** Block 1 is structural: schema columns, enum vocabulary,
schema shape. No logic reads or writes any of the new fields, no
gate-checker dispatches off `PlacementGate`, no service raises on
`GateResult`.

The intent is to land vocabulary and storage atomically so Blocks 2–3
(service plumbing, audit log, S-48 cleanup) can reference both without
rebasing migrations.

## New / changed contracts

### DB schema (additive only)

- `legal_profiles.fns_verification_status` — `varchar(20)`,
  nullable, server default `'unchecked'`. Used by G03/G06/G16/G17.
- `legal_profiles.fns_verified_at` — `timestamptz`, nullable.
- `legal_profiles.egrul_snapshot_at` — `timestamptz`, nullable.
  Drives EGRUL freshness check in G06.
- `legal_profiles.inn_checksum_valid` — `boolean`, nullable
  three-state (NULL = unchecked, T/F = result).
- `payout_requests.payout_method_type` — `varchar(16)`, nullable.
  Marina D2: typed enum tag over free-form `requisites` string;
  per-method validators land in Phase 3b.
- `placement_requests.publication_verified` — `boolean`, NOT NULL,
  default `false`. G11 post-publication verification gate.
- `placement_requests.publication_verified_at` — `timestamptz`,
  nullable.
- `ord_registrations.published_at` — `timestamptz`, nullable.
  Anchors the ФЗ-38 72h reporting window.
- `ord_registrations.deadline_at` — `timestamptz`, nullable.
  Computed from `published_at + 72h` at the registration site (Phase
  3b territory).

### API contracts

- `LegalProfileResponse` — 4 optional fields appended:
  `fns_verification_status: str | None`,
  `fns_verified_at: datetime | None`,
  `egrul_snapshot_at: datetime | None`,
  `inn_checksum_valid: bool | None`. Backwards compatible (all
  optional, all default `None`); existing clients ignore them.

- `GateResultResponse` (new) — Pydantic mirror of the `GateResult`
  dataclass. Served by `GET /api/placements/{id}/gates` once Phase 3d
  ships the endpoint, and by `TransitionBlockedError` payloads in
  Phase 3c. Snapshotted via `tests/unit/snapshots/gate_result_response.json`.

### Service-domain types

- `PlacementGate` — 18-value StrEnum (`G01`–`G18`). G03 named
  `LEGAL_STATUS_COMPLIANT` (matches DB column; the older
  `LEGAL_TYPE_COMPLIANT` in frozen research artefacts is historical).
  G07/G15/G16 are placeholders for Phase 4 (КЭП + real Мой налог).

- `GateResult` (dataclass) — gate-checker return type. Fields:
  `gate`, `passed`, `blocker`, `reason_code`,
  `remediation_url`, `remediation_data`. Population conventions
  documented in the module docstring (`passed=True` ⇒ `blocker`
  irrelevant; `blocker=False, passed=False` is informational).

### FSM contracts

No FSM changes in Block 1.

## Verification

- `alembic upgrade head` clean, single head `e6a88faa9fa0`.
- `alembic check` reports "No new upgrade operations detected".
- `make lint` — 20 ruff errors (project baseline preserved).
- `tests/unit/test_contract_schemas.py` — 23/23 pass (was 22; +1 for
  `gate_result_response`).
- Unit-test baseline (`tests/unit/`, ignoring `test_main_menu.py` per
  Makefile): 62 fail / 496 pass — matches the pre-Block-1 baseline on
  `develop`. Spot-checked one schema-touching failure
  (`test_escrow_payouts.py::TestPayoutRequest::test_payout_creation`)
  on `develop` directly; it fails identically with the same SQLite
  "no such table" error → pre-existing, not introduced.

## Out of scope (covered by later Phase 3a blocks)

- Block 2: `LegalComplianceService`, gate-checker module skeletons,
  repository methods for gate inputs, custom exceptions
  (`TransitionBlockedError`, `ChannelAddDeclinedError`).
- Block 3: compliance audit-log helper + integration; S-48
  transaction-contract cleanup at three router sites.
- Block 4: comprehensive Phase 3a CHANGES + CHANGELOG bundle.

## References

- `reports/docs-architect/discovery/PHASE3_RESEARCH_2026-05-02.md`
  § 2.3 G-1, § 4.1 (cross-cutting enumeration), § 7 Phase 3a scope.
- `IMPLEMENTATION_PLAN_ACTIVE.md` § 3.B.1 (PlacementGate vocabulary),
  § 3.B.2 (GateResult shape), § 3.D (repo-only DB access for
  gate-checkers).
- Marina decisions: D1 (Medium scope), D2 (typed `payout_method_type`
  enum), D4 (Phase 4 boundary for КЭП + Мой налог).

🔍 Verified against: `9556b49` | 📅 Updated: 2026-05-02T00:00:00Z
