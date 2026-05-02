# Phase 3b 5b.1 — Schema additives

**Date**: 2026-05-02
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.1.2 → 5b.1.5 (3 code + 1 docs)
**Origin**: Phase 3b sub-block sequencing post-investigation; Marina M-decisions M1.2 / M3 / M5

## Scope

Three pre-prod schema additives on `0001_initial_schema.py` (no alembic head movement; `e6a88faa9fa0` preserved):

| # | Change | Rationale |
|---|---|---|
| 5b.1.2 | `legal_profile.egrul_egrip_snapshot` JSONB nullable | M1.2 — column awaits Phase 5 EGRUL provider; freshness check uses adjacent `egrul_snapshot_at` timestamp |
| 5b.1.3 | `payout_requests.idempotency_key` String(128) UNIQUE-indexed nullable | M5 — mechanical port from `Transaction.idempotency_key` pattern; service-level keying convention in 5b.7 |
| 5b.1.4 | `payout_requests.payout_method_type` String(16) → `sa.Enum("bank_card", "yoomoney", "sbp", "bank_transfer", name="payoutmethodtype")` | M3 — minimal enum (Phase 3b 4-value subset; Phase 5 may extend); lossless conversion (column never written) |

## Files modified

- `src/db/migrations/versions/0001_initial_schema.py` — 3 column changes + 1 unique index op + 1 DROP TYPE in downgrade
- `src/db/models/legal_profile.py` — `egrul_egrip_snapshot` field + JSONB import + Any import
- `src/db/models/payout.py` — `idempotency_key` field + `payout_method_type` type change + `PayoutMethodType` enum class

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.1.2 | `6c75bda` | feat(db): add legal_profile.egrul_egrip_snapshot JSONB column |
| 5b.1.3 | `c62cc48` | feat(db): add payout_request.idempotency_key UNIQUE column |
| 5b.1.4 | `5c8aa66` | feat(db): convert payout_method_type varchar(16) → enum (4 values) |
| 5b.1.5 | (this commit) | docs(phase3b): 5b.1 closure — schema additives CHANGES + CHANGELOG |

## Verification

| Gate | Pre-5b.1 baseline | 5b.1 result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) | 62 fail / 496 pass / 558 collected | 62 fail / 496 pass / 558 collected |
| Snapshot tests (`test_contract_schemas.py`) | 23 pass | 23 pass |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |
| Schema source compiles | yes | yes |
| Models import (3 new fields present) | n/a | yes |

## Pattern notes

- **JSONB convention** (`egrul_egrip_snapshot`): migration uses `postgresql.JSONB()` (matches existing convention — `yookassa_metadata`, `legal_status_snapshot` etc.); model uses `Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)` (matches `yookassa_payment.py`, `contract.py`, etc.).
- **UNIQUE idempotency convention** (`idempotency_key`): full UNIQUE (not partial-where), matching Transaction's pattern exactly (single-column unique index named `ix_<table>_idempotency_key`). PostgreSQL allows multiple NULLs in unique index by default per SQL standard, so partial-where would have been redundant.
- **Enum convention** (`payout_method_type`): model uses `Mapped[PayoutMethodType | None] = mapped_column(nullable=True)` shortcut — matches `PayoutStatus` precedent in same file. Originally tried explicit `ENUM(..., create_type=False)` (mirroring `placement_status_history.py` precedent) but that broke 10 review_service tests because no other table creates the `payoutmethodtype` postgres type, and `Base.metadata.create_all()` in test fixtures doesn't run alembic. Lesson: explicit `create_type=False` only works when another model on the same metadata creates the type first.

## Out of scope (deferred)

- EGRUL/EGRIP real provider (Phase 5)
- Payout method matrix expansion (Phase 5)
- `idempotency_key` service-level keying convention (5b.7 — payout-side gates)
- New tests — schema additions don't ship logic; test coverage paired with logic in 5b.3+
- All architectural debt surfaces (placementstatus enum 4-counts, fns_verification_status varchar vs Enum, mini_app stale comment per L14, migrations count drift) — Phase 3 closure batch territory

## Notes

This is the first sub-block of Phase 3b. Phase 3a Foundation landed on develop via merge `5926797`. New feature branch `feature/phase3b-compliance-gates` cut from that point. Phase 3a feature branch (`feature/legal-compliance-gates @ 9d072f1`) preserved per project history rule.

Phase 5 introduction (Payout Provider Implementation, NEW phase per Marina decision D) absorbs M4 + M6 + G06/G16/G17/G18 bodies. Foundation Phase 4 markers on G15/G16 stay; G06 + G18 marker change from "Phase 4" to "Phase 5 pending" in 5b.10 closure.

🔍 Verified against: `5c8aa66` (HEAD post-5b.1.4) | 📅 Updated: 2026-05-02T22:33:00Z
