# CHANGES — Fix A: Migration drift `cd59fc72b378` cleanup

**Date:** 2026-05-12
**Branch:** feature/fix-a-migration-drift-cleanup
**Base:** develop @ e10c1de
**Context:** L71 interim gate (PROMPT_40 runtime debug) revealed pre-existing infrastructure blocker. Fix A resolves migration drift; Fix B (mistralai PyPI quarantine) separate followup.

## Closes

- **BL-080 L71 gate Issue 2** (migration chain `cd59fc72b378` `DuplicateColumn egrul_egrip_snapshot` on fresh `alembic upgrade head`)

## Decisions applied

- **Pre-prod consolidation exception extension** (Marina L71 gate approval) — drift_fix delete permitted под policy "Edit `0001_initial_schema.py` directly until first production user" per CLAUDE.md.

## Summary

Migration `cd59fc72b378_drift_fix_post_t1_2_5f_egrul_.py` was created 2026-05-08
for backfill против existing DBs не имевших egrul/idempotency_key/enum changes.
After creation, `0001_initial_schema.py` был последовательно отредактирован
(commits `6c75bda`, `c62cc48`, `5c8aa66`, `8a283b5`) для прямого включения тех
же changes. Drift_fix accumulated as fully redundant migration.

Šaг 1 probe (см. `tmp/fix_a_probe_2026-05-12.md`) verified all 4 drift_fix ops
уже present в `0001_initial_schema.py`:

| Op | drift_fix | 0001 line | Status |
|---|---|---|---|
| `audit_logs.action` String(64) | ALTER varchar(20)→64 | L405: `sa.String(64)` | already ✓ |
| `legal_profiles.egrul_egrip_snapshot` JSONB | ADD COLUMN | L687: JSONB nullable | already ✓ (DuplicateColumn cause) |
| `payout_requests.idempotency_key` UNIQUE | ADD COLUMN + INDEX | L807 + L815-820 unique=True | already ✓ |
| `payout_requests.payout_method_type` enum | CREATE TYPE + ALTER | L795-805 inline sa.Enum | already ✓ |

Resolution: delete `cd59fc72b378` — нет porting required (Šaг 2 no-op), нет
chain update required (Šaг 3 no-op — drift_fix was chain TIP, no downstream).

## Files touched

- `src/db/migrations/versions/cd59fc72b378_drift_fix_post_t1_2_5f_egrul_.py` — **DELETED** (commit `a9ee327`)
- `reports/docs-architect/discovery/CHANGES_2026-05-12_fix-a-migration-drift-cleanup.md` — this file (closure)

## Verification

**Fresh `alembic upgrade head` from empty DB:**

```
exit code 0
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial_schema -> e6a88faa9fa0
```

No `DuplicateColumn` error. No reference к removed `cd59fc72b378`. Chain HEAD = `e6a88faa9fa0`.

**Schema verified post-upgrade:**

- `audit_logs.action` = varchar(64) ✓
- `legal_profiles.egrul_egrip_snapshot` = jsonb ✓
- `payout_requests.idempotency_key` = varchar(128) + UNIQUE INDEX `ix_payout_requests_idempotency_key` ✓
- `payout_requests.payout_method_type` = enum `payoutmethodtype` {bank_card, yoomoney, sbp, bank_transfer} ✓

**Baselines (final, double-run stable):**

| Gate | Result |
|---|---|
| format-check | 0 errors / 400 files |
| lint | 7 errors (BL-024 baseline) |
| typecheck | 0 errors / 291 files (1 fewer than develop's 292 — drift_fix deletion) |
| pytest run 1 | 1018 passed / 2 skipped / 0 failed / 0 errored |
| pytest run 2 | 1018 passed / 2 skipped / 0 failed / 0 errored (identical) |
| ci-local exit | 1 (lint-only per BL-024 baseline) |

## Surprises log (BL-026)

1. **Probe finding vs expected:** prompt anticipated 1-2 ops would need porting (e.g. T1.2.3 audit_logs.action could be missing from 0001). Reality: **all 4 ops уже в 0001** — drift_fix полностью redundant. Šaг 2 and Šaг 3 collapsed к no-op, sequence finished в 1 commit instead of 3.
2. **Downstream chain size:** zero — drift_fix was chain TIP. Šaг 3 instruction предвидел this possibility (NO downstream → skip к Šaг 4); matched.
3. **No test fixtures referenced `cd59fc72b378`:** pre-flight grep across src/, tests/, alembic/ returned only self-references inside the file itself.
4. **mypy file count:** typecheck baseline dropped 292 → 291 source files (1 fewer due to drift_fix deletion). Expected and benign.

## Not included (Fix B — separate followup)

- `mistralai` PyPI quarantine resolution (Issue 1 от L71 gate)

## Not included (deferred к BACKLOG batch Phase 3 closure)

- GlitchTip `market_bot_db_errors` DB provisioning (Issue 3 от L71 gate, cosmetic)

🔍 Verified against: feature/fix-a-migration-drift-cleanup HEAD (post-delete commit `a9ee327`)
📅 Updated: 2026-05-12
