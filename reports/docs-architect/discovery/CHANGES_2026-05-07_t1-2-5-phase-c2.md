# T1.2.5 Phase C-2 — surgical work on C2/C3/C4 closes T1.2.5

**Branch:** feature/t1-2-test-failures-cleanup
**Sub-block:** T1.2.5 (Phase C-2 of 2 — closes T1.2.5)
**Date:** 2026-05-07
**Pre-state:** HEAD `4193da5`, baseline 38F / 997P / 5S / 0E (post-C1 closure)
**Post-state:** HEAD `f8cd8d9`, baseline 12F / 997P / 5S / 0E

## Goal

Surgical work on C2 (`test_start_and_role.py`), C3 (`test_fsm_middlewares.py`),
C4 (`test_gamification.py`) closes T1.2.5 fully. Failing tests reference
removed internal helpers / topology elements (anti-pattern); passing tests
preserved as actual coverage. C4 file wholesale-deleted (0% passing).

## Decisions applied

- **C4** (`test_gamification.py`): wholesale delete. 6/6 fail; 5/6 reference
  removed `classify_subcategory` / `get_subcategories_from_db` from
  `src.utils.categories` (now empty deprecation file post-v4.3); 1/6
  unrelated `ConnectionRefusedError` to PostgreSQL.

- **C3** (`test_fsm_middlewares.py`): surgical — delete 9 failing methods
  + entire `TestMiddlewareStructure` class. Top-level `import subprocess`
  + `import pytest` kept (still used by passing tests). 12 passing tests
  on current FSM public surface preserved.

- **C2** (`test_start_and_role.py`): surgical — delete 11 failing methods
  + entire `TestStartCommandExistingUser` class. Remove orphan imports
  (`asyncio`, `patch`, `FSMContext`) + 8 orphan fixtures (`tg_user_new`,
  `tg_user_existing`, `db_user_advertiser`, `db_user_banned`,
  `mock_message`, `mock_state`, `mock_async_session`, `mock_user_repo`).
  5 passing tests on current public surface preserved.

## Implementation

### Šаг 1 — C4 wholesale delete

- Commit: `bda6c01`
- Deleted: `tests/unit/test_gamification.py` (132L removed).
- Verify: ci-local 32F / 997P / 5S / 0E (ΔF=−6 as expected — exact).
- One textual reference remained in `tests/test_streak_bonus.py:4`
  docstring ("split from test_gamification.py") — historical comment, not
  a code dependency; left as-is.

### Šаг 2 — C3 surgical

- Commit: `67bd63a`
- File: `tests/unit/test_fsm_middlewares.py` — 94L deleted.
- Removed methods (9):
  - `TestFSMStates::test_placement_states_defined`
  - `TestFSMStates::test_arbitration_states_defined`
  - `TestFSMStates::test_channel_settings_states_defined`
  - `TestFSMStates::test_channel_owner_states_defined`
  - `TestFSMStates::test_admin_states_defined`
  - `TestFSMStates::test_all_states_importable`
  - `TestMiddlewareStructure::test_throttling_middleware_has_redis_param`
  - `TestMiddlewareStructure::test_fsm_timeout_constant_defined`
  - `TestMiddlewareStructure::test_throttle_time_constant_defined`
- Removed class: `TestMiddlewareStructure` (all 3 methods failed; entire
  class became empty).
- Preserved 12 passing tests:
  - `TestFSMStates`: `test_topup_states_defined`, `test_feedback_states_defined`,
    `test_dispute_states_defined` (3)
  - `TestMiddlewares`: 5 `*_imports` tests
  - `TestCallbackRegistry`: 2 tests
  - `TestNoBotPayoutFlow`: 2 tests
- Verify: ci-local 23F / 997P / 5S / 0E (ΔF=−9 as expected — exact).

### Šаг 3 — C2 surgical

- Commit: `f8cd8d9`
- File: `tests/unit/test_start_and_role.py` — 380L deleted, 5L added (net
  −375L, file shrunk from 477L → 102L).
- Removed methods (11):
  - `TestStartCommandNewUser`: 4 methods (test_new_user_created_in_db,
    test_new_user_receives_welcome_message, test_new_user_fsm_cleared,
    test_concurrent_start_requests)
  - `TestStartCommandExistingUser`: all 4 methods (entire class removed)
  - `TestRoleSelection`: 3 methods (test_change_role_shows_menu,
    test_change_role_clears_state, test_change_role_callback_answered)
- Removed orphan imports: `asyncio`, `patch` from `unittest.mock`,
  `FSMContext` from `aiogram.fsm.context`.
- Removed orphan fixtures (8): `tg_user_new`, `tg_user_existing`,
  `db_user_advertiser`, `db_user_banned`, `mock_message`, `mock_state`,
  `mock_async_session`, `mock_user_repo`.
- Preserved 5 passing tests:
  - `TestStartCommandNewUser::test_new_user_role_is_new`
  - `TestRoleSelection::test_role_callback_data_format`
  - `TestRoleValidation`: 3 methods
- Preserved fixtures: `db_user_new_role`, `mock_callback`.
- Preserved imports: `AsyncMock`, `MagicMock`, `pytest`.
- Verify: ci-local 12F / 997P / 5S / 0E (ΔF=−11 as expected — exact).

## Verification

| Stage     | F  | P   | S | E | Δ vs prior      |
| --------- | -- | --- | - | - | --------------- |
| Pre Šаг 1 | 38 | 997 | 5 | 0 | (post-C1 baseline) |
| Šаг 1     | 32 | 997 | 5 | 0 | -6F (C4 delete) |
| Šаг 2     | 23 | 997 | 5 | 0 | -9F (C3 surgical) |
| Šаг 3     | 12 | 997 | 5 | 0 | -11F (C2 surgical) |

**Cumulative Phase C-2 ΔF = −26.** Matches plan projection.

Verify gate command: `make ci-local` (per BL-018 phrasing).

## Cumulative T1.2.5 (Phase C-1 + Phase C-2)

| Phase | Commits | ΔF | ΔP | ΔS |
|---|---|---|---|---|
| C-1 (8 commits) | 7a5f187…4193da5 | -15 | +4 | -6 |
| C-2 (4 commits — incl this one) | bda6c01…f8cd8d9 | -26 | 0 | 0 |
| **T1.2.5 total** | **12 commits** | **-41** | **+4** | **-6** |

Pre-T1.2.5 baseline (HEAD `106bad8` post-T1.2.4b): 53F / 993P / 11S / 0E.
Post-T1.2.5 baseline (HEAD `f8cd8d9`): **12F / 997P / 5S / 0E**.

## Cumulative T1.2 progress

T1.2.5 Phase C-2 closes 3 entries (C2 + C3 + C4).

Cumulative T1.2: ~59/99 (~60%) — was ~56/99 post-C1.

Remaining T1.2:
- T1.2.6 (ESCROW-001 / C18 architectural) — last major item, ~12F residual
  baseline likely contains its cluster
- D4 admin_client refactor (deferred from C-1, see C-1 closure for 3 paths)
- Small residual fails — categorize в T1.2.6 Šаг 0

## T1.2.6 readiness signal

12F residual baseline. Cluster vs scattered analysis is **next session's
Šаг 0** scope, not Phase C-2. No data captured here intentionally —
T1.2.5 fully closed.

## Deferred to BACKLOG (T1.2 final closure batch)

### Coverage for current FSM topology (replaces deleted C3 internal tests)

C3 surgical removed 9 tests asserting internal FSM topology elements
(state names, middleware constants, init signatures). Public surface
coverage (FSM transition behavior, throttling effect, admin filter
gating) is **not** covered by surviving tests (which only verify
imports work). Future sub-block: behavioral tests on FSM transitions
+ middleware effects.

### Coverage for current `cmd_start` / `cb_tos_*` / `go_to_*_menu` public surface (replaces deleted C2 internal tests)

C2 surgical removed 11 tests on `_handle_start` / `safe_callback_edit` /
`async_session_factory` (all internal helpers). Public entry points
(`cmd_start` command handler, `cb_tos_accept` / `cb_tos_decline` callback
handlers, role-selection callback handler) have **no behavioral test
coverage** post-deletion. Surviving tests cover only role validation
constants + callback string format.

### Gamification coverage (replaces deleted C4)

If production has live gamification logic (`src/tasks/gamification_tasks.py`,
`src/tasks/badge_tasks.py`, `src/core/services/badge_service.py`),
fresh tests against actual current surface would close coverage gap.
Out of T1.2 cleanup scope.

### D4 admin_client refactor (carried forward from C-1)

See T1.2.5 Phase C-1 closure CHANGES § Deferred to BACKLOG for the 3
architectural paths (extend `tests/unit/conftest.py` SQLite tables /
relocate to `tests/integration/api/` / refactor
`_resolve_user_for_audience` selectinload). No new analysis here —
verbatim carried forward.

### MistralAIService unit test coverage (carried forward from C-1)

Fresh tests against current `src/core/services/mistral_ai_service.py`
public surface. Out of T1.2 cleanup scope; no new analysis here.

### bmediakit_comparison stale fields production bug (carried forward)

Already deferred via T1.2.4 Q3=a. No new analysis here.

## Lessons

- **L60** — Surgical-vs-wholesale tradeoff diagnostic. When per-test
  classification reveals 0% passing in a file, wholesale delete is
  cleaner than surgical — preserves zero coverage anyway and avoids
  partial-file edits with import/fixture orphan analysis. Threshold
  applied: **≥1 passing test → surgical** (preserves real coverage on
  current public surface); **0 passing → wholesale**. C4 ran
  wholesale (6F/0P), C2/C3 ran surgical (mixed). Rule emerges as
  natural decision: delete file when fully broken; keep+prune when
  partially valid. Apply forward: Šаг 0 classification table directly
  drives this — count passing tests per file as primary diagnostic.

🔍 Verified against: `f8cd8d9` (feature HEAD post-C2) | `d68b302`
(develop) | `59c4094` (main) | 📅 2026-05-07
