# CHANGES — 2026-04-27 — Phase 2 § 2.B.2 (a + b) — Caller integration + dead code

## Summary

Closes Phase 2 § 2.B.2 — wires every direct mutation site through
`PlacementTransitionService`, removes 3 dead code units, fixes 4 design
gaps surfaced during work, and locks the regime in with a forbidden-
patterns lint. This bundle covers BOTH § 2.B.2a (caller integration,
prior 3 commits on this branch) and § 2.B.2b (disputes, dead code,
failed_permissions, lint, surprises — this commit set).

## Commits in § 2.B.2 (a + b)

### § 2.B.2a (3 commits, prior)

- `f255be3` — `core: wire PlacementRequestService methods through service`
- `8e108ce` — `core+tasks+bot: wire remaining callers through service`
- `daf5146` — `db+core+api+tasks: delete 6 placement_repo mutation helpers`

### § 2.B.2b (8 commits, this set)

- `592ac09` — `api: wire disputes.resolve through admin_override`
- `cf9ec4a` — `bot/admin: rewrite dispute resolve handler to call API`
- `d69e5b0` — `tasks: delete dispute:resolve_financial Celery task`
- `2aeb9c4` — `tasks: delete retry_failed_publication task (DEAD per T2-1/T2-2)`
- `21c973d` — `core: wire failed_permissions enum`
- `42259da` — `core: add pending_owner expires_at refresh to _sync_status_timestamps`
- `043d3dd` — `core: delete deprecated process_publication_success`
- `a0e97d0` — `scripts: forbidden patterns lint + wire into make ci-local`

## Public contract delta

### Added

- New `AdminOverrideReason` Literal value `"dispute_resolution"` actively
  used by API (`POST /admin/disputes/{id}/resolve`) and bot handler
  (`admin:dispute:resolve:{verdict}:{id}`).
- `failed_permissions` placement status now actively transitioned to
  on `BotNotAdminError` / `InsufficientPermissionsError`. Allow-list
  was already wired in skeleton (Промт-3); this commit set wires the
  publication failure caller (O-10).
- `make ci-local` runs forbidden-pattern lint as first step.
- `scripts/check_forbidden_patterns.sh` extended with three new Python
  guards: direct `<obj>.status = PlacementStatus.*`, setattr-style
  status mutation, manual `<obj>.published_at = ...`. All scoped to
  exempt `placement_transition_service.py`.

### Removed (database / behaviour)

- Behaviour: SLA timeouts (`check_owner_response_sla`,
  `check_counter_offer_sla` from § 2.B.2a) now transition to
  `cancelled` (was `failed`). **Breaking change** for any downstream
  code filtering on `status='failed'` for SLA-recovery flows; recovery
  flows should now also include `'cancelled'` when distinguishing
  organic cancel from technical failure is not relevant.
- Behaviour: permission-related publication failures now use
  `failed_permissions` (was `failed`). Reserves `failed` for technical
  publication errors (`TelegramBadRequest`, network errors, etc.).

### Removed (Python)

- `src/db/repositories/placement_request_repo.py`: methods `accept`,
  `reject`, `counter_offer`, `set_escrow`, `set_published`,
  `update_status` (§ 2.B.2a commit 3). Repo is now read-only per
  § 2.B.0 Decision 2.
- `src/tasks/dispute_tasks.py`: entire file (120 LOC). Dead code —
  zero dispatchers anywhere in src/. Plus `"src.tasks.dispute_tasks"`
  removed from `celery_app.py:include` and the orphan routing test
  removed from `test_celery_routing.py`.
- `src/tasks/placement_tasks.py:retry_failed_publication`: function +
  `_retry_failed_publication_async` helper deleted (~69 LOC). Dead
  per T2-1/T2-2 verify; also INV-1 violator per O-4.
- `src/core/services/placement_request_service.py:process_publication_success`:
  method deleted (~21 LOC). DEPRECATED v4.2 with zero callers.

### Changed (Python — service-mediated)

- All 22+ direct `placement.status = ...` writes replaced with
  `PlacementTransitionService.transition()` or
  `transition_admin_override()`.
- Bot handlers gained `InvalidTransitionError` catches with
  user-friendly Telegram alerts (per O-6).
- Router `disputes.resolve` calls `transition_admin_override` with
  `admin_override_reason="dispute_resolution"`. Outermost
  `await session.commit()` preserved (router owns the FastAPI request
  transaction; service does not commit per S-48).
- Bot handler `admin/disputes.py:admin_resolve_dispute` now calls
  internal API endpoint (`api_resolve_dispute_admin`) instead of
  inlining ~57 LOC of duplicated billing + status logic. Outcome
  strings preserved for UI parity.

### Service skeleton (`PlacementTransitionService`) extensions

- `_ALLOW_LIST` extension (in § 2.B.2a):
  - `escrow → cancelled` (advertiser cancel-after-escrow with 50%
    refund — `bot/handlers/placement/placement.py`).
- `_sync_status_timestamps` extension (this prompt):
  - `pending_owner → expires_at +24h` (Surprise 5 design gap).
  - The three `pending_*` cases collapsed into a single
    set-membership branch (also satisfies SIM114).

## Surprises closed

| # | Description | Resolution |
|---|---|---|
| § 2.B.2a Surprise 1 | 6 extra `update_status` callers in placement_tasks.py not in research § 1b | Wired inline; SLA-timeout behavior changed `failed → cancelled` |
| § 2.B.2a Surprise 2 | 2 unflagged `update_status` in api/routers/campaigns.py | Wired with `InvalidTransitionError → HTTP 400` |
| § 2.B.2a Surprise 3 | `test_expires_at_consistency.py::test_bot_arbitration_uses_24h_regression_guard` requires source text | Double-write workaround in arbitration.py kept; **BL-027** for proper rewrite |
| § 2.B.2a Surprise 4 | `process_publication_success` body called deleted `set_published` | Stubbed to NotImplementedError → fully deleted in § 2.B.2b commit 7 |
| § 2.B.2a Surprise 5 | `pending_owner` not in `_sync_status_timestamps` | Added in § 2.B.2b commit 6 |
| § 2.B.2a Surprise 6 | INV-1 ordering in `_freeze_escrow_for_payment` | Correctly ordered in § 2.B.2a commit 1 |
| § 2.B.2b note | `disputes.py:704` line drift vs plan (plan said L718) | Audited and resolved — plan line numbers were stale, semantic targets matched |
| § 2.B.2b note | `admin/disputes.py:252` line drift vs plan (plan said L1011) | Audited and resolved — file is shorter than plan assumed |
| § 2.B.2b note | `billing_service.py:166,270` contains internal `await session.commit()` | Out of scope per Промт-5 — flagged for future BL |

## Verification gates

Phase 2 § 2.B.2 closing baseline (this set):

- failed = 76, errored = 17, collection error = 1 — unchanged from
  pre-§2.B.2 baseline.
- passing = 625 (was 626 pre-§2.B.2b — −1 from removing dead
  routing test for the deleted dispute task).
- mypy: 10 errors / 5 files / 278 source files — unchanged.
- ruff: pre-existing 22 errors → 21 errors (one SIM114 closed by
  collapsing the three `pending_*` branches into one).
- 0 regressions across all 8 commits (PASS → FAIL/ERROR diff empty
  after each commit).
- `make ci-local` passes the new forbidden-patterns step (17/17).
- `make check-forbidden` direct invocation: 17/17 OK.

## BACKLOG additions (this prompt set)

- **BL-025** — DB-level CHECK constraint `placement_escrow_integrity`
  pins INV-1 to enum (Phase 4 epic).
- **BL-026** — Mutation-audit process gap: parameter-driven helpers
  escape static enumeration (Phase 3 closure / CLAUDE.md update).
- **BL-027** — `test_expires_at_consistency.py` requires source-text
  refactor — keeps double-write in arbitration.py until rewritten
  (Phase 3).

BACKLOG.md is uncommitted in the working tree per BL-006 protocol —
will be bundled with Phase 3 closure.

## Origins

- IMPLEMENTATION_PLAN_ACTIVE.md § 2.B.0 Decisions 1-12.
- PHASE2_RESEARCH_AGENT_A_2026-04-26.md.
- DISPUTES_PATHS_DUMP_2026-04-27.md.
- MUTATION_AUDIT_2026-04-27.md (working tree).
- § 2.B.2a closure report (Промт-4).
- Промт-5 (this prompt) — § 2.B.2b execution.

🔍 Verified against: a0e97d0 | 📅 Updated: 2026-04-27
