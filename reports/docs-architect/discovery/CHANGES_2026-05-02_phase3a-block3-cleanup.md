# Phase 3a Block 3 — Cleanup (full scope, reframed per caller audit)

**Date**: 2026-05-02
**Branch**: feature/legal-compliance-gates
**Commits**: 3.1 → 3.5 (4 code + 1 docs); preceded by chore/clarify-s48-patterns
  merge into develop and develop merge into this branch
**Scope decision**: (c) Full per Marina, reframed per (F) — codify S-48
  taxonomy first, then mark carve-outs in code

## Scope

Three categories, 14 mutation sites, 4 commits:

1. Audit log integration: 5 service-method sites (additive)
2. S-48 carve-out markers: 4 sites referencing CLAUDE.md taxonomy (comment-only)
3. Router redundancy: 5 sites in 2 routers (4 simple removals + 1 commit→flush refactor)

**Note**: Original spec listed 7 router sites (6 simple + 1 refactor at :423).
During implementation, 2 of the 6 "simple" sites turned out to be wrapped
in `try/except IntegrityError → 409` (same pattern as :423) and were
deferred — see "Out of scope" below.

## Files modified

- `src/core/services/legal_profile_service.py` — audit on 3 methods
- `src/core/services/payout_service.py` — audit on 2 methods
- `src/core/services/badge_service.py` — 3 marker comments (no behavior change)
- `src/core/services/publication_service.py` — 1 marker comment (no behavior change)
- `src/api/routers/contracts.py` — 3 redundant commits removed
- `src/api/routers/channels.py` — 1 redundant commit removed (line 1245) +
  1 refactor (commit→flush at :423)

## Audit log integration (commit 1645a64)

Reused existing `AuditLogRepo.log()` from `src/db/repositories/audit_log_repo.py`.
Fire-and-forget pattern — internal try/except → logger.warning, never blocks.

| Service.method | Action | Resource type |
|---|---|---|
| LegalProfileService.create_profile | legal_profile_create | legal_profile |
| LegalProfileService.update_profile | legal_profile_update | legal_profile |
| LegalProfileService.upload_scan | legal_profile_scan_upload | legal_profile |
| PayoutService.approve_request | payout_approve | payout_request |
| PayoutService.reject_request | payout_reject | payout_request |

Implementation notes:
- `update_profile` snapshots `data.keys()` before in-place mutation (the
  service adds `inn_hash` if `inn` was passed). The `extra={"updated_fields"}`
  reflects what the caller actually requested, not internal artifacts.
- `upload_scan` originally had no profile reference; added a
  `LegalProfileRepo.get_by_user_id` lookup post-update to obtain
  `profile.id` for `resource_id`. Skipped audit if profile None
  (defensive — should not happen in normal flow).
- `PayoutService` uses session-as-method-param (older pattern); audit
  call placed inside `session.begin()` block, before the implicit
  commit at exit.

PII discipline: extra dict carries only field names + non-PII metadata
(legal_status string, gross_amount string, payout_method_type string,
scan_type category, list of updated field names, rejection reason). Raw
INN, FIO, passport numbers, addresses, and bank details are NEVER logged.

## S-48 carve-out markers (commit 4eff829)

Original Block 3 plan called these "S-48 violations". Caller audit (Step 1
of original plan) showed they are **legitimate carve-outs** for two
canonical patterns documented in CLAUDE.md by chore/clarify-s48-patterns:

| Site | Pattern | Marker |
|---|---|---|
| badge_service.py:79 | 2 — Self-contained | `# S-48: self-contained pattern` |
| badge_service.py:229 | 2 — Self-contained | `# S-48: self-contained pattern` |
| badge_service.py:379 | 2 — Self-contained | `# S-48: self-contained pattern` |
| publication_service.py:308 | 3 — External-boundary | `# S-48: external-boundary (Telegram message_id idempotency)` |

No commit() lines removed. Comment-only change (4 lines insertions,
4 lines deletions in diff because each line is rewritten with the
suffix).

Caller audit: `tmp/PHASE3A_BLOCK3_CALLER_AUDIT_2026-05-02.md`.

## Router redundancy

### Simple removals (commit 11c3c5f)

4 sites — `get_db_session` auto-commits on success path; explicit commits
redundant.

- `contracts.py` line 67 — generate_contract endpoint, no try/except
- `contracts.py` line 134 — sign_contract, inside try/except for
  PermissionError + ValueError (not commit-related)
- `contracts.py` line 155 — request_kep, same try/except shape
- `channels.py` line 1245 — set_category, no try/except, autoflush
  before subsequent `session.refresh(channel)` makes the change visible

### channels.py:423 refactor (commit 2f7c3d0)

Single-line change: `commit()` → `flush()` inside existing
`try/except IntegrityError → 409` handler. Transaction boundary returns
to `get_db_session`; duplicate-channel 409 UX preserved (existing
rollback + raise unchanged).

## Behavioral verification

- **Channel-add 409 path**: no direct test coverage exists. Pre-existing
  failures in `tests/test_channel_settings_repo.py` (3) and
  `tests/test_api_channel_settings.py` (5 errors) verified to predate
  3.4 by stash + re-run on HEAD~1.
- **Full unit suite**: 62 failed / 496 passed / 558 collected — exactly
  matches Block 2 baseline. No new regressions.

## Verification

| Gate | Block 2 baseline | Block 3 result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) | 62 fail / 496 pass / 558 collected | 62 fail / 496 pass / 558 collected (`pytest tests/unit/ --ignore=tests/unit/test_main_menu.py`) |
| Snapshot tests (`tests/unit/test_contract_schemas.py`) | 23 pass | 23 pass |
| alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |

## Out of scope (deferred)

- **channels.py lines 1139 and 1191** — discovered during 3.3
  implementation to be wrapped in `try/except IntegrityError → 409`
  (same pattern as :423). Original spec listed them as simple removals;
  they actually need the same `commit()→flush()` refactor that 3.4
  applied to :423. Per the prompt's strict rule (any site wrapped in
  `try/except IntegrityError → 409` must NOT be touched in 3.3,
  surface and defer), deferred to follow-up — recommended 1 commit,
  ~4 lines.
- CHANGELOG.md `[Unreleased]` entry — Block 4 bundle.
- Tests for audit log emission — Phase 3b/closure.
- (M) Architectural fitness test
  (`tests/architecture/test_s48_compliance.py`, AST walk verifying
  every commit() matches a canonical pattern) — post-Phase-3
  investment, depends on stable taxonomy.
- BACKLOG.md updates — accumulating for Phase 3 closure batch.

## Lessons accumulating for Phase 3 closure batch

- **L12** — grep-only S-48 classification ловит false positives; verify
  session-ownership before classifying. (Surfaced via Block 3 caller
  audit; codified in CLAUDE.md by chore/clarify-s48-patterns.)
- **L13** — discovery cataloging by line number alone misses pattern
  variations: 3 of 7 router sites in this block use the same
  `try/except IntegrityError → 409` pattern, but only :423 was flagged
  for refactor. The other two (1139, 1191) were classified as "simple
  removals" until reading their context. Pattern-based discovery
  (grep for `IntegrityError` proximate to commit/flush) would have
  caught all three at once.
- (M) candidate — architectural fitness test for S-48 patterns.

## Commit hashes

| Commit | Hash | Description |
|---|---|---|
| Step 0 develop merge | f294d4a | Pull S-48 taxonomy from chore branch |
| 3.1 | 1645a64 | feat(audit): 5 compliance service sites |
| 3.2 | 4eff829 | docs(core): S-48 carve-out markers |
| 3.3 | 11c3c5f | refactor(api): 4 simple commit removals |
| 3.4 | 2f7c3d0 | refactor(api): channels.py:423 commit→flush |
| 3.5 | (this commit) | docs(phase3a): Block 3 closure CHANGES |

## Notes

This Block 3 came in reframed form vs original plan. The reframe was the
right call: forcibly removing badge_service commits would have silently
reverted badge/XP grants; replacing publication_service:308 with flush()
would have reintroduced double-publish risk. Both surfaced via empirical
caller audit before any mutation.

The router redundancy scope adjustment (6→4+2 deferred) is a minor
discovery from inside the work. Same pattern (`try/except IntegrityError
→ 409`) at multiple sites in the same router suggests a small refactor
could consolidate the duplicate-resource-conflict handling — flagged for
Phase 3 closure consideration but out of scope for this block.
