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

🔍 Verified against: `1996fbb` | 📅 Updated: 2026-05-07
