# T1.2.5 Phase C-1 — clean delete actions + Q4 cascade

**Branch:** feature/t1-2-test-failures-cleanup
**Sub-block:** T1.2.5 (Phase C-1 of 2)
**Date:** 2026-05-07
**Pre-state:** HEAD `106bad8`, baseline 53F / 993P / 11S / 0E
**Post-state:** HEAD `69f1be0`, baseline 38F / 997P / 5S / 0E

**Phase C-2 scope (separate session):** Item 1.b — surgical work on C2/C3/C4
post re-baseline (data captured during Šаг 0).

## Goal

T1.2.5 closes the deprecated-tests batch + C20 main_menu redesign + C15 stub
fallout + Q4 architectural leftover from T1.2.4b. Phase C-1 covers Items 2,
3, 4, partial Item 1 (clean deletes + 1 surgical edit). Item 1.b (C2/C3/C4
surgical) deferred to Phase C-2.

## Decisions applied

- **D1** (C15): `tests/test_channel_settings_repo.py` → delete. Production
  is "Stub for legacy" post-v4.3; tests target removed API surface
  (`get_or_create_default`, `owner_id` kwarg, `upsert`, `Decimal('500')`
  default). No production caller broken.
- **D2** (C20): two-step — relocate `TestTosKb` → new
  `tests/unit/test_tos_kb.py`, then delete `tests/unit/test_main_menu.py`
  + drop `--ignore` flag from Makefile.
- **D3 adjusted** (placement_notifications): per Šаг 0 reclassify (file is
  NOT a 3-skip shell — 17 active passing tests + 3 empty skip-shells at
  L307-321), surgical edit removes only the 3 empty skip-shells. 17 passing
  tests against real `notify_*` production API preserved.
- **D4** (admin fixture): **deferred** — see BACKLOG entry below. Test infra
  constraint surfaced during Šаг 1 attempt; Marina chose option (B) to
  defer rather than expand into shared SQLite conftest scope.

## Implementation

### Šаг 1 — Q4 cascade (jwt_rate_limit dead-stub removal)

- Commit: `7a5f187`
- File: `tests/unit/api/test_jwt_rate_limit.py`
- Change: 29-line dead-stub block (`_Result` + `_Session` classes +
  `stub_session_factory` monkey-patch + `asynccontextmanager` import +
  `_make_user` import) → 5 lines. Endpoint `/api/auth/consume-ticket`
  doesn't touch DB; stubs were dead path post-`5de1ded`.
- Verify: 2/2 tests pass; ci-local 53F / 993P (initial run flaked at 54F;
  re-run clean confirmed baseline hold).
- D4 deferral noted in commit body.

### Šаг 2a — TestTosKb relocation

- Commit: `c49c277`
- File created: `tests/unit/test_tos_kb.py` (33 lines, 4 test methods).
- Source: extracted verbatim from `tests/unit/test_main_menu.py:79-104`.
- Verify: 4/4 pass; ci-local 53F / 997P (ΔP=+4 as expected — newly
  collected file added to runs).

### Šаг 2b — main_menu deletion + Makefile cleanup

- Commit: `6949835`
- Files: deleted `tests/unit/test_main_menu.py` (105L removed); Makefile
  `--ignore=tests/unit/test_main_menu.py` flag dropped, comment block
  pruned.
- Verify: ci-local 53F / 997P (ΔF=0 — file was already excluded via
  `--ignore`, removing both file and flag is a no-op for collection).
- `TestMainMenuKb` references removed-`change_role` surface (a4405d0
  redesign); `TestRoleSelectKb` references removed `role_select_kb`
  keyboard. Surface fully sunset.

### Šаг 3 — channel_settings_repo deletion

- Commit: `c7b5c8c`
- File deleted: `tests/test_channel_settings_repo.py` (74L).
- Verify: ci-local 50F / 997P (ΔF=−3 as expected — 3
  AttributeError fails removed).

### Šаг 4 — placement_notifications skip-shells (D3 adjusted)

- Commit: `4535725`
- File: `tests/unit/test_placement_notifications.py` — surgical edit, 22L
  removed (3 empty skip-shell classes + comment header at L302-321).
- Verify: 17/17 active tests still pass; ci-local 50F / 997P (ΔF=0,
  ΔP=0 — empty skip-shells contributed nothing to test count).

### Šаг 5 — ai_service deletion

- Commit: `d4b7462`
- File deleted: `tests/unit/test_ai_service.py` (265L).
- Verify: ci-local 38F / 997P (ΔF=−12 as expected — 12 fails removed).

### Šаг 6 — test_campaign fixture + dependents

- Commit: `69f1be0`
- Files deleted:
  - `tests/test_api_placements.py` (101L, 4 test methods, 100% fixture-dependent)
  - `tests/test_placement_request_repo.py` (86L, 2 test methods, 100% fixture-dependent)
- Edit: `tests/conftest.py` — removed `test_campaign` fixture (8L, was at
  L417-424).
- Verify: ci-local 38F / 997P / 5S (ΔS=−6 — 6 skipped tests dropped from
  collection).

## Verification

| Stage     | F  | P   | S  | E | Δ vs prior      |
| --------- | -- | --- | -- | - | --------------- |
| Pre Šаг 1 | 53 | 993 | 11 | 0 | (baseline)      |
| Šаг 1     | 53 | 993 | 11 | 0 | 0F (Q4 cascade) |
| Šаг 2a    | 53 | 997 | 11 | 0 | +4P (relocate)  |
| Šаг 2b    | 53 | 997 | 11 | 0 | 0 (file --ignored) |
| Šаг 3     | 50 | 997 | 11 | 0 | -3F (C15)       |
| Šаг 4     | 50 | 997 | 11 | 0 | 0 (skip-shells) |
| Šаг 5     | 38 | 997 | 11 | 0 | -12F (C1)       |
| Šаг 6     | 38 | 997 | 5  | 0 | -6S (campaign)  |

**Cumulative ΔF = −15, ΔP = +4, ΔS = −6, ΔE = 0.**

Verify gate command: `make ci-local` (per BL-018 phrasing).

## Q4 disposition

L57 leftover applied — cascaded into Šаг 1 commit. `_Session` stub +
`stub_session_factory` monkey-patch + `asynccontextmanager` + `_make_user`
import all dropped. Standalone test file passes 2/2.

## Phase C-2 scope (deferred)

Item 1.b — surgical work on C2/C3/C4 after re-baseline. Re-baseline data
captured in `tmp/T1_2_5_C0_*_rebaseline.txt` during Šаг 0:

- **C2** (`tests/unit/test_start_and_role.py`): 11 failed, 5 passed.
  Fail signature — `AttributeError` on `async_session_factory` /
  `safe_callback_edit` (start.py refactor moved these).
- **C3** (`tests/unit/test_fsm_middlewares.py`): 9 failed, 12 passed.
  Fail signature — import + missing-attr errors on FSM/middleware
  structure.
- **C4** (`tests/unit/test_gamification.py`): 6 failed, 0 passed.
  Fail signature — `ImportError` on `classify_subcategory` /
  `get_subcategories_from_db` from `src.utils.categories` + 1
  connection-refused.

Per-test classification + surgical execution → next sub-block session.

## Cumulative T1.2 progress

T1.2.5 Phase C-1 closes 6 entries (C1 + C15 + C20 + L57 leftover via Q4 +
placement_notifications skip-shells + test_campaign fixture cluster).

Cumulative T1.2: ~56/99 (~57%).

Remaining T1.2: T1.2.5 Phase C-2 (C2/C3/C4 surgical) + T1.2.6 (ESCROW-001
architectural).

## Deferred to BACKLOG (T1.2 final closure batch)

### admin_client 4-way → 1-way fixture (D4 deferred from T1.2.5 Phase C-1)

T1.2.4b closed L51 in production (`5de1ded`). Test-side mirror in
`tests/unit/api/test_admin_payouts.py:104-149` still carries 4-way
override. Three architectural paths:

1. Extend `tests/unit/conftest.py` SQLite `needed_tables` (add
   `legal_profiles` + audit other auth-chain dependencies). Additive,
   low ripple, but slippery slope into SQLite-mimicking-PostgreSQL
   territory.

2. Relocate `tests/unit/api/test_admin_payouts.py` →
   `tests/integration/api/`. Cleanest layering (admin endpoint with full
   ORM chain = integration territory). Requires test relocation +
   fixture rewiring + CI gate adjustments.

3. Refactor `_resolve_user_for_audience` to avoid mandatory
   `selectinload` on `User.legal_profile` when callsite doesn't need
   it. Touches `src/api/dependencies.py` — T1.2.4d B3 reserved scope or
   new sub-block.

Choose path при resumption.

### MistralAIService unit test coverage

Coverage for current `src/core/services/mistral_ai_service.py` deleted
along with `tests/unit/test_ai_service.py` (C1). Resurrection = rewrite
from scratch against actual public surface. Out of T1.2 cleanup scope.

### bmediakit_comparison stale fields production bug

Already deferred via T1.2.4 Q3=a (`tests/test_bmediakit_comparison.py`
left as-is). No new deferral introduced here.

## Lessons

- **L58** — Probe enumeration miss for surface-level reclassification.
  T1.2.5 Phase A+B probe artifact characterised
  `tests/unit/test_placement_notifications.py` as a 3-skip-shell file.
  Šаг 0 reclassify (read entire file before mutation) revealed: 17
  active passing tests against real `notify_*` production API + 3 empty
  skip-shells at L307-321. D3 adjusted accordingly per Marina decision.
  Apply forward: probe artifacts are SUMMARIES, not authoritative
  enumerations — Šаг 0 verify must include a quick `pytest <file>` +
  body read for any file slated for full deletion. Discipline parallel
  to L52/L53/L57.

- **L59** — Plan validation gate (f) cross-conftest infra divergence
  miss. T1.2.5 plan invoked the `api_client_with_auth` reference pattern
  (`tests/conftest.py:472-538`) for D4 admin_client refactor without
  noting that `tests/unit/api/test_admin_payouts.py` lives under
  `tests/unit/` — which has its own `db_session` fixture
  (`tests/unit/conftest.py:42-77`) that creates a stripped-down
  in-memory SQLite (only 3 tables: `users`, `telegram_chats`,
  `channel_mediakits`). Post-`5de1ded` auth chain calls
  `selectinload(User.legal_profile)` → `OperationalError('no such
  table: legal_profiles')` blocks the 1-way refactor in this conftest
  scope. Apply forward: when planning a fixture pattern transplant from
  `tests/conftest.py` to deeper subdirectories, BL-024 / Plan
  validation gate (f) must include a check for overriding `db_session`
  fixtures and document table-set divergence. The conftest hierarchy
  surface is part of test-infra contract, not just `autouse=True`
  fixtures.

🔍 Verified against: `69f1be0` (feature HEAD post-C1) | `d68b302`
(develop) | `59c4094` (main) | 📅 2026-05-07
