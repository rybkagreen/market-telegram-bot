# T1.2.3 — audit_logs production fix

**Date started:** 2026-05-07
**Branch:** feature/t1-2-test-failures-cleanup
**Predecessor:** T1.2.2 closure @ 1996fbb
**Baseline (pre-fix, ci-local):** 73F / 957P / 14S / 0E

## Scope

Original T1.2.3 was scoped as "pg integration tx-bleed cleanup" (clusters C5/C13/C19).
Phase A+B probe surfaced two corrections:
- C5 misgrouped — actually unit SQLite fixture gap, reassigned to T1.2.4
- C13/C19 audit-claimed root cause "fixture tx-bleed" was wrong — real cause is two-layer
  production bug in audit_logs

This sub-block delivers the production fix: schema widen + SAVEPOINT refactor + failure-path test coverage.

## Marina decisions (2026-05-07)

- Q1: C5 → T1.2.4
- Q2: option (b) — both layers in T1.2.3
- Q3: audit_logs.action varchar(64)
- Q4: add L48

## Predecessor probes

- Phase A+B probe artifact: `tmp/T1_2_3_REBASELINE_2026-05-07.md` — cluster classification, root cause uncovered
- Phase A.5 probe artifact: `tmp/T1_2_3_CALLER_SURFACE_2026-05-07.md` — caller surface, GREEN readiness

## Work plan (filled progressively)

[Sections to be appended as commits land]

- Шаг 1: CHANGES init + scope (this commit)
- Шаг 2: schema widen
- Шаг 3: SAVEPOINT refactor
- Шаг 4: failure-path tests
- Шаг 5: re-baseline
- Шаг 6: closure (L48, deferred items, Q7 progress)

## Шаг 2 — Schema widen (commit T1.2.3.1)

- `0001_initial_schema.py`: `audit_logs.action varchar(20) → varchar(64)`
- `src/db/models/audit_log.py`: `String(20) → String(64)`; comment refreshed
  (`# allowed: READ, WRITE, DELETE, ADMIN_READ` → `# action verb identifying
  the audited operation; vocabulary grows over time`)
- Rationale: max current action string is 28 chars (`legal_profile_scan_upload`).
  varchar(64) gives 36-char headroom (>2× peak). 3 actions sat exactly at varchar(20)
  boundary; widen also resolves their latent fragility.
- Pre-prod immutability exception applies (no users yet, BL-061 explicit carve-out).

## Шаг 3 — SAVEPOINT refactor (commit T1.2.3.2)

- `src/db/repositories/audit_log_repo.py::log()`: wrap insert+flush in `session.begin_nested()`
- Removed redundant explicit `flush()` (SAVEPOINT close handles it)
- Logger output identical (observability contract preserved)
- Public method signature unchanged — 13 production call sites unaffected
- Architectural rationale: previous fire-and-forget contract was broken — Python
  try/except cannot rescue DBAPI-level transaction state. Now genuine: any audit
  write failure rolls back at SAVEPOINT level, leaving parent session healthy.

## Шаг 4 — Failure-path tests (commit T1.2.3.3)

- New file `tests/integration/test_audit_log_repo.py` (~150 lines, 4 tests)
- Real DB trigger via over-long `resource_type` (varchar(50) → 60-char input).
  Independent of widened `action` column — test stays meaningful even if `action`
  is widened further later.
- Mock-based variant covers non-DBAPI exception path
  (`AsyncMock(side_effect=RuntimeError("boom"))` patched onto `session.execute`).
- 4 contract assertions per failure test: log() doesn't raise; parent tx survives;
  parent commitable; failed audit row absent.
- caplog test locks observability contract (warning + exc_info).
- Closes the coverage gap: pre-Phase-C, no test verified the SAVEPOINT contract.

## Шаг 5 — Re-baseline (folded into closure commit T1.2.3.4)

| Metric | Pre-fix | Post-fix | Δ |
|---|---|---|---|
| F | 73 | 68 | -5 |
| P | 957 | 966 | +9 |
| S | 14 | 14 | 0 |
| E | 0 | 0 | 0 |

Delta matches expected exactly: -5F = C13 (4F) + C19 (1F) confirmed resolved;
+9P = 5 relocated from F + 4 new contract tests (Шаг 4).

`make ci-local` exits non-zero because 68F remain — this is the expected
post-T1.2.3 baseline (T1.2.4-6 still pending). Not a regression.

ci-local log: `tmp/T1_2_3_ci-local_post-fix.log`

## Closure (commit T1.2.3.4)

### Cumulative T1.2 progress
- Pre-T1.2.3: 30/99 entries closed (~30%)
- Post-T1.2.3: 35/99 entries closed (~35%) (C13 4 + C19 1)
- C5 (7) reassigned to T1.2.4 — does not count toward T1.2.3 closure

### Q7 closure criteria progress
- Target: ci-local 0F / 0E
- Pre-T1.2.3: 73F / 0E
- Post-T1.2.3: **68F / 0E**
- Remaining for full T1.2 closure:
  - T1.2.4 — unit fixture decision (C5 + C10 + C4) — 9 entries
  - T1.2.5 — deprecated tests batch (C1 + C2 + C3 + C4-residual + parts of C20) — ~37 entries
  - T1.2.6 — ESCROW-001 architectural decision (C18) — 1 entry
  - Plus: minor clusters C6/C7/C8/C9/C11/C12/C14/C15/C16/C17 — ~21 entries

### Deferred to BACKLOG (consolidate в T1.2 final closure batch)

DO NOT touch BACKLOG.md inline per project convention. Following items recorded
here for the final T1.2 closure consolidation:

- **AUDIT-LOG-1** — Review SAVEPOINT pattern adoption across other side-effect
  repos. Audit logging now isolates failures correctly; assess whether other
  "best-effort" side-effect writes (event publishing, denormalized cache updates,
  retry-shadow writes, etc.) follow the same broken fire-and-forget
  Python-except-only pattern. Candidate scan target: any repo method whose
  docstring claims "fire and forget" or "never blocks" without a SAVEPOINT wrap.
- **AUDIT-LOG-2** — Action vocabulary documentation. The `audit_logs.action`
  column was originally designed as a 4-value enum (READ/WRITE/DELETE/ADMIN_READ);
  vocabulary has grown organically to 12 values. Consider documenting the action
  taxonomy or formalizing as a Postgres ENUM in a future migration once
  vocabulary stabilizes.

### L48 lesson

**L48 — SQL transaction error chain reading + DBAPI tx-state isolation**

Two-part lesson surfaced by C13/C19 root cause analysis during T1.2.3 Phase A+B
probe:

(a) `InFailedSQLTransactionError` is **always** downstream of a prior failed
statement. Audit pipelines must walk the traceback chain to the first error,
OR run the tests, not statically inspect the outermost exception.
Outermost-exception classification mis-diagnosed C13/C19 as "fixture tx-bleed"
in the original failures audit; the real cause was schema truncation on an
audit INSERT (`audit_logs.action varchar(20)` + 28-char production action
string), and the InFailedSQLTransactionError was the secondary symptom.

(b) Python `try/except` does NOT rescue DBAPI-level transaction state. Within
a parent transaction, genuine fire-and-forget side effects need SAVEPOINT
(`session.begin_nested()`) — the Python catch handles the language-level
exception, but the DB session remains poisoned until SAVEPOINT rollback or
top-level rollback. The original `AuditLogRepo.log()` claimed fire-and-forget
in its docstring but only had Python-except — claim was advertised, not
delivered.

Source: T1.2.3 Phase A+B probe (root cause uncovered) + Phase A.5 caller
surface (SAVEPOINT pattern verified compatible with all 13 callers) +
Phase C empirical verification (C13/C19 confirmed resolved post-fix).

### Engineering Principles self-audit
- **P2** — investigated before deciding (Phase A+B + A.5 probes locked all
  unknowns; classification table empty before Phase C launch)
- **P3** — no workarounds (option (b) over (c)/skip-markers per Marina
  principle direction 2026-05-07; root cause fixed at both layers)
- **P4** — once-correctly (varchar(64) headroom not just-enough varchar(32);
  SAVEPOINT pattern locked by 4 contract tests not deferred to "later")

🔍 Verified against: `1996fbb` (predecessor) → post-fix HEAD (T1.2.3.4) | 📅 Updated: 2026-05-07
