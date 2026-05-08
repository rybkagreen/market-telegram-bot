# T1.2 series — master closure document

**Date:** 2026-05-08
**Tag:** v0.5.0
**Branch:** `feature/t1-2-test-failures-cleanup`
**Parent in BACKLOG:** BL-072 T1.2 (closed)
**Companion:** BL-076 (deferred items consolidation)

## Pre-state

| Ref | HEAD | Notes |
|---|---|---|
| `feature/t1-2-test-failures-cleanup` (pre-closure batch) | `e27ca22` | Last sub-block commit (T1.2.8 closure) |
| `develop` | `d68b302` | Phase 3c.1 closure merge — untouched |
| `main` | `59c4094` | Phase 3 closure merge — untouched |
| Tag `v0.4.0-phase3c` | `59c4094` (main) | Phase 3 closure tag — preserved |

**Pre-series baseline (audit, pre-T1.2.0):** 99 audit entries (81 fails / 17
errors / 1 collection error) accumulated pre-Phase-3b — model schema drift
(`bmediakit_comparison`, `escrow_payouts`), sqlite shadow-table issues, FSM
state rename, `auth_utils.create_access_token` refactor, Telegram token
env-dependency, etc. Per audit O.2: PREDATES Phase 3b (NOT a Phase 3b
artifact).

**Pre-closure-batch ci-local baseline (HEAD `e27ca22`):**
- pytest: 0F / 993P / 3S / 0E
- ruff lint: 7 errors (`tests/unit/conftest.py` — intentional asyncio policy
  ordering; BL-024 prohibits modification)
- ruff format: 0 errors (402 files clean)
- mypy: 4 errors (`src/core/services/mediakit_service.py:111-116` —
  `TelegramChat` schema drift; deferred per Marina Q2=c)
- ci-local exit: 2 (lint+mypy non-zero, expected per Q1=a + Q2=c)

## Post-state

| Ref | HEAD | Notes |
|---|---|---|
| `feature/t1-2-test-failures-cleanup` (post-closure batch) | `<closure-final-hash>` | Closure batch commits A+B+C |
| `develop` | `<merge commit от feature>` | Local `--no-ff` merge from feature |
| `main` | `<merge commit от develop>` | Local `--no-ff` merge from develop (atomic FE+BE) |
| Tag `v0.5.0` | main HEAD | New tag |
| Tag `v0.4.0-phase3c` | `59c4094` | Preserved |

**Post-state baseline (на main HEAD post-merge):** unchanged from pre-closure
— **0F / 993P / 3S / 0E + 7 lint / 0 format / 4 mypy / exit 2**.

## Sub-block index (closure CHANGES files)

| Sub-block | CHANGES file | Closure HEAD |
|---|---|---|
| T1.2.1 — auth refactor cleanup | `CHANGES_2026-05-04_t1-2-1-auth-refactor-cleanup.md` | (T1.2.1.2) |
| T1.2.2 — mechanical bulk + C16 | `CHANGES_2026-05-05_t1-2-2-mechanical-bulk-and-c16.md` | (T1.2.2.8) |
| T1.2.3 — audit_logs production fix | `CHANGES_2026-05-07_t1-2-3-audit-logs-production-fix.md` | (T1.2.3.4) |
| T1.2.4 — fixture decision (Phase C closure) | `CHANGES_2026-05-07_t1-2-4-fixture-decision.md` | `ae872a1` |
| T1.2.4b — Pydantic Decimal + auth-DI refactor | `CHANGES_2026-05-07_t1-2-4b-decimal-and-auth-di.md` | `5de1ded` |
| T1.2.5 Phase C-1 — surgical/wholesale deletes | `CHANGES_2026-05-07_t1-2-5-phase-c1.md` | `69f1be0` |
| T1.2.5 Phase C-2 — surgical pruning | `CHANGES_2026-05-07_t1-2-5-phase-c2.md` | `f8cd8d9` |
| D4 — admin_payouts test relocation к integration | `CHANGES_2026-05-07_d4-admin-client-relocation.md` | `b89f2c4` |
| T1.2.5e — payout dead-code cleanup | `CHANGES_2026-05-07_t1-2-5e-payout-cleanup.md` | (covered by T1.2.5e closure commits) |
| T1.2.5g — content_filter Mistral mock | `CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md` | `2379531` |
| T1.2.6 — placement-flow cluster | `CHANGES_2026-05-07_t1-2-6-placement-flow-cluster.md` | `215e219` |
| T1.2.7 — counter_offer cleanup | `CHANGES_2026-05-07_t1-2-7-counter-offer-cleanup.md` | `4e24e8c` |
| T1.2.8 — bot_factory cleanup | `CHANGES_2026-05-07_t1-2-8-bot-factory-cleanup.md` | `7d560bd` |
| Master closure | this file | `<closure-final-hash>` |

## Cumulative metrics

- **Commits on feature branch (since fork from develop @ `d68b302`):** 69
- **Files touched (cumulative):** 94
- **LOC delta:** +3991 / −3635 (net +356)
- **Tests fixed:** 81 → 0 (test failures), 17 → 0 (collection errors)
- **Test entries closed (per audit):** 99 / 99 (100%)
- **Lint baseline:** entry 21 → exit 7 (residual conftest deferred per BL-024)
- **Format baseline:** 14 → 0
- **Mypy baseline:** 10 → 4 (residual mediakit deferred per Q2=c)

## Production-code side effects (within T1.2 sub-blocks)

The series was framed as test-cleanup, but several sub-blocks surfaced
production bugs requiring fixes:

| Sub-block | Production change | Reason |
|---|---|---|
| T1.2.3 | `audit_logs.action` varchar(20) → varchar(64) + SAVEPOINT pattern в `AuditLogRepo.log` | Schema truncation на 28-char `transition_blocked` action; broken Python-except-only fire-and-forget |
| T1.2.4 C4 | `xp_service` Pattern 1 refactor (6 of 7 methods) + 3 src/ caller updates | S-48 violations (`async with session.begin()`) + 2 latent silent-rollback bugs (`add_advertiser_xp` / `add_owner_xp`) |
| T1.2.4b | `_resolve_user_for_audience` accepts `session` via FastAPI DI | Auth dep bypassed DI via `async_session_factory()` direct call |
| T1.2.4b | `src/api/main.py` exception handler — Pydantic Decimal 422 serialization | 500 → 422 на endpoints с Decimal `ge`/`le` validation |
| T1.2.5e | 11 dead `PayoutService` methods deleted (incl. `create_payout` с 3 S-48 violations) | Zero src/ callers verified empirically |
| T1.2.5e | `PayoutComplianceService` skeleton deleted (`payout_compliance_service.py`) | Empty registries, zero callers; recreate в Phase 5 / 5b.7 |
| T1.2.5e | mini_app payout screens / hooks / types / routes removed | BL-055 redirect-only к web portal |
| T1.2.5e | Free function `calculate_payout` deleted (`src/constants/payments.py`) | Zero src/ callers |
| T1.2.5e | Empty bot admin payout approve/reject callback stubs deleted | Dead code |
| T1.2.6 | `ReputationAction.PUBLICATION` → `publication` (lowercase canonical) | Latent enum case bug surfaced after FK fixture fix in Wave 0 |

## Marina decisions log (cross-sub-block)

Each sub-block CHANGES file documents its own Q-table. High-level recurring
themes:

- **Architectural cleanliness over schedule** (P1) — exemplified в D4 (Path
  2 relocation chosen over SQLite-mimicking-PostgreSQL workaround); T1.2.4
  Q1=(i) `xp_service` src/ refactor над test-only Pattern 2 patch.
- **No workarounds** (P3) — exemplified в T1.2.3 (option (b) over (c)/skip
  markers — root cause fixed at both layers per Marina principle direction
  2026-05-07); T1.2.5e dead-code purge (full PayoutComplianceService
  skeleton deletion над silent-leave).
- **Once-correctly over twice-iteratively** (P4) — exemplified в T1.2.3
  varchar(64) headroom (not just-enough varchar(32)) + 4 contract tests
  locked at fix; T1.2.4 Q6=(i') full xp_service refactor (6 of 7 methods +
  3 callers, не just-the-failing-one).
- **Per-cluster commits** (granular history) — Marina Q4=(b) consistently:
  T1.2.4 split per-cluster commits (cfa8d35 / 8d4d0c6 / 6417037 / 6903009 /
  a06c6dd / ae872a1); T1.2.5 surgical-vs-wholesale per-file (L60 ≥1-passing
  rule).
- **Probe enumeration miss / classification methodology** (L43, L52, L53,
  L58) — Phase A+B audit classifications treated as working hypotheses,
  Phase C Šаг 0 mandatory before mutation. 4 strikes documented в T1.2.4
  L53 alone (path / surface / root-cause / count strikes).

## Lessons accumulated

Cross-sub-block lessons (L43-L61). High-impact subset:

- **L43** — Mandatory pre-mutation Šаг 0 isolated verification per cluster
- **L44** — Audit shape correctness (path, surface, depth)
- **L45** — `session.execute()` `side_effect` over `return_value` для
  multi-call functions; `await_count` lock-in
- **L46** — Stop-hook noise mitigation: interleaved CHANGES file
  initialization (1st or 2nd commit, не closure)
- **L47** — Pre-fix per-cluster empirical verification mandatory
- **L48** — SQL transaction error chain reading + DBAPI tx-state isolation
  (Python catch не rescues DBAPI-level transaction state — SAVEPOINT
  required for genuine fire-and-forget)
- **L49** — Auto-continue mode discipline (drift → STOP)
- **L50** — S-48 violation surface area inventory
- **L51** — Auth dep bypasses FastAPI DI via `async_session_factory()`
- **L52** — Phase A+B classification methodology: separate data-collection
  from interpretation
- **L53** — Phase A+B credibility decay pattern (4 strikes)
- **L57-L58** — Probe enumeration misses for surface-level reclassification
- **L59** — Plan validation gate (f) cross-conftest infra divergence
  miss
- **L60** — Surgical-vs-wholesale tradeoff diagnostic (≥1 passing →
  surgical; 0 passing → wholesale)
- **L61** — Pytest «sub-package without parent» collision (latent project-wide;
  surfaced via D4 admin_payouts relocation)

## Forward-looking — deferred future workstreams

### Standalone sub-blocks (separate from T1.2 series)

- **T1.2.5f — topup normalize.** Apply payout deeplink pattern (BL-055) к
  topup flow. Requires Marina UX decisions; deferred as separate workstream.
- **T1.2.4d — B3 full elimination of `async_session_factory()` outside
  `db/session.py`.** Would reduce factory call sites from N → 0 outside
  `db/session.py`, completing Pattern 1 contract for the DI session-handling
  chain.

### BACKLOG entries (BL-076 — 19 deferred items)

See `reports/docs-architect/BACKLOG.md` BL-076 для consolidated list.
High-priority subset:

- **T1.2-D1** — `mediakit_service.py` stale fields production bug (4 mypy
  errors residual; runtime AttributeError under any caller).
- **T1.2-D3** — `PayoutComplianceService` recreation для Phase 5 / 5b.7
  (T1.3 / BL-072 T1.3 dependency).
- **T1.2-D7** — `MistralAIService.moderate_content` blanket-except
  fail-open security implication.

## Tag info

| Tag | Commit | Date | Notes |
|---|---|---|---|
| `v0.4.0-phase3c` | `59c4094` (main pre-closure) | 2026-05-04 | Phase 3 closure merge — preserved |
| `v0.5.0` | main HEAD post-closure | 2026-05-08 | T1.2 series atomic FE+BE deploy |

## Preserved branches (not deleted post-merge)

Per project rule (Git Flow MANDATORY § feature branches preserved
post-merge unless Marina explicitly says delete):

- `feature/legal-compliance-gates` @ 9d072f1
- `feature/phase3b-compliance-gates` @ 2d78cf2
- `feature/phase3c-transition-wiring` @ 6f44ccb
- `feature/t1-2-test-failures-cleanup` @ closure-final-hash (this branch)

Hard limit: no remote push (BL-017 — GitHub Actions permanently inactive).

🔍 Verified against: closure batch HEAD post Commit C | 📅 Updated: 2026-05-08
