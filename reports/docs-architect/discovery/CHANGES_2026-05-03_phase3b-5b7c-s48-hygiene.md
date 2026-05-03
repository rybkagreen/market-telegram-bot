# Phase 3b 5b.7c — S-48 hygiene sweep across 43 sites

**Date**: 2026-05-03
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.7c.1 → 5b.7c.5 (4 code + 1 docs per Option Beta)
**Origin**: Phase 3b sub-block 5b.7c — applies P4 once-correctly across all S-48 hygiene surfaces in `src/`. After 5b.7c the codebase has uniform handler-level autocommit pattern (`get_db_session` for routers, `DBSessionMiddleware` for bot) — no asymmetric explicit commits scattered across 43 sites.

## Summary

- 5b.7c sweeps 43 audit-canonical sites (D1 of `tmp/PHASE3B_PRE_CLOSURE_AUDIT_2026-05-03.md`) of S-48 hygiene drift across three classes:
  - **Class i (31 sites)**: redundant explicit `await session.commit()` calls in handlers using injected sessions (`Depends(get_db_session)` for 9 router sites; `DBSessionMiddleware` for 22 bot handler sites). Pure mechanical removal — middleware/dependency autocommits handle durability on success, autoflush + downstream SELECTs handle materialization within a handler.
  - **Class ii (9 sites)**: routers using `async with async_session_factory()` directly (legitimate Pattern 2) lacked the `# S-48: self-contained pattern` marker. Pure additive comment for documentation/lint hygiene.
  - **Class iii (3 sites in `disputes.py`)**: 2 sites with inline `try/except IntegrityError → 409` mapping switch from `commit()` to `flush()` (preserves error surfacing exactly; `get_db_session` autocommits on success). 1 site reclassified Class i per O.4 (no IntegrityError handling at site) and treated mechanically.
- 4 production commits + 1 docs commit per Option Beta (Marina Q1=(а)). Verifications ruff `src/` 4, mypy `src/` 10, pytest unit 62F/633P preserved exactly across all 4 production commits (zero behavior change expected and verified).
- Three lessons surfaced for Phase 3 closure batch (L34/L35/L36 — see Lessons section below).
- Three Class iii (O.3, O.5, O.H) and one mid-priority (`payout_service.create_payout` dead code) deferrals consolidated into "Deferred to production launch" — out of 5b.7c hygiene scope, requires contract-level review or schema considerations.

## Files modified

**Class ii markers (6 router files / 9 sites — pure additive comment):**
- `src/api/routers/billing.py` — L610, L720
- `src/api/routers/analytics.py` — L571
- `src/api/routers/auth_login_widget.py` — L98
- `src/api/routers/campaigns.py` — L343, L409, L600
- `src/api/routers/auth_login_code.py` — L120
- `src/api/routers/auth.py` — L227

**Class i routers (4 files / 9 sites — pure mechanical removal):**
- `src/api/routers/legal_acceptance.py` — L73 (`accept_rules`)
- `src/api/routers/admin.py` — L347, L392, L422, L561 (4 admin handlers)
- `src/api/routers/legal_profile.py` — L79, L92, L111
- `src/api/routers/ord.py` — L55 (`register_creative` — pure removal per Q2=(а))

**Class i bot handlers (9 files / 22 sites — pure mechanical removal + 1 comment update):**
- `src/bot/handlers/shared/contract_signing.py` — L73, L107, L118 (`cb_contract_sign` + `cb_accept_rules` ×2) + L111 comment update
- `src/bot/handlers/shared/legal_profile.py` — L56
- `src/bot/handlers/owner/arbitration.py` — L226, L328, L558
- `src/bot/handlers/owner/channel_owner.py` — L451, L472 (`delete_channel`, `restore_channel`)
- `src/bot/handlers/owner/channel_settings.py` — L33, L132, L199, L221, L313
- `src/bot/handlers/placement/placement.py` — L305, L479, L645
- `src/bot/handlers/advertiser/campaigns.py` — L211, L322
- `src/bot/handlers/dispute/dispute.py` — L110, L278
- `src/bot/handlers/billing/billing.py` — L280

**Class iii (1 file / 3 sites — flush() switch + comment cleanup):**
- `src/api/routers/disputes.py` — L299 (`commit()` → `flush()` in `create_dispute`), L356 (`commit()` → `flush()` in `update_dispute_owner_explanation`), L729 (pure removal — reclassified Class i per Q6=(а)) + L728 paranoia comment removal

**Documentation:**
- `CHANGELOG.md` — Unreleased section appended.
- `reports/docs-architect/discovery/CHANGES_2026-05-03_phase3b-5b7c-s48-hygiene.md` (NEW — this file).

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.7c.1 | `0a5d540` | feat(api): S-48 Pattern 2 marker hygiene — 9 routers |
| 5b.7c.2 | `88659e9` | refactor(api): remove redundant Pattern 1 commits in routers (S-48 hygiene) |
| 5b.7c.3 | `3bcda7c` | refactor(bot): remove redundant Pattern 1 commits in handlers (S-48 hygiene) |
| 5b.7c.4 | `6439e08` | refactor(api): disputes.py Pattern 1 cleanup — flush() switch + comment |
| 5b.7c.5 | (this commit) | docs(phase3b): 5b.7c closure — S-48 hygiene sweep across 43 sites |

## Phase A+B+C trace

Phase A+B artifact: `tmp/PHASE3B_5B7C_INVESTIGATION_2026-05-03.md`. Canonical input: `tmp/PHASE3B_PRE_CLOSURE_AUDIT_2026-05-03.md` D1 section. Findings driving Phase C decisions:

- **A.1 — Autocommit primitives re-verified.** `src/api/dependencies.py:170-183` `get_db_session` autocommits on success / rolls back on exception. `src/bot/middlewares/db_session.py:12-25` `DBSessionMiddleware.__call__` autocommits on success (no explicit rollback, but `async with` exit closes session and SQLAlchemy implicitly rolls back uncommitted state). Both primitives sufficient for Pattern 1 contract.
- **A.5 — Enumeration completeness check.** `grep` count matches audit D1 exactly: 21 router commits + 22 bot handler commits + 4 service commits = 47. No new sites since `02bf454`. Headline "(40 sites)" in prompt was off by 3 (43 actual); investigation surfaced as O.7 and resolved here.
- **A.2 — Class i routers site-by-site verification.** All 9 sites (`legal_acceptance.py`, `admin.py` ×4, `legal_profile.py` ×3, `ord.py`) confirmed pure-Pattern-1-violation, mechanical-safe pure removal. Service-internal autoflush handles materialization; in-memory operations follow.
- **A.4 — Class iii careful flush() analysis.** L299/L356 (`create_dispute`, `update_dispute_owner_explanation`) have inline `try/except IntegrityError → 409` mapping; flush() switch preserves IntegrityError surfacing equivalently (PostgreSQL immediate constraint mode). L729 (admin resolve) audit-listed as Class iii but actual code has no IntegrityError handling — reclassified Class i per O.4.
- **A.6 — Multi-commit single-handler edge case.** `cb_accept_rules` in `contract_signing.py` has TWO commits in same function. Both removable; SQLAlchemy autoflushes on the post-mutation re-read SELECT; comment "Reload after commit" updated to reflect actual mechanism.
- **A.9 — Commit grouping (Option Beta — recommended).** 5 commits: Class ii markers / Class i routers / Class i bot handlers / Class iii disputes / docs. STOP-gate clarity per dispatch surface; lowest-to-highest risk ordering; mirrors 5b.6/5b.7a/5b.7b cadence.
- **B-pattern: pure removal default; flush() only where strictly needed.** Per Q4=(а): Class iii L299/L356 get `flush()` because `refresh()` follows IntegrityError catch and IntegrityError surfacing must happen synchronously; everywhere else autoflush + autocommit suffice.

## Marina decisions (Q1-Q6)

| # | Question | Decision |
|---|---|---|
| Q1 | Commit grouping strategy: Alpha (4) / Beta (5) / Gamma (3) | **(Beta)** 5 commits — cleanest STOP gates per dispatch surface; lowest-to-highest risk ordering; mirrors prior sub-block cadence |
| Q2 | `ord.py:55` Pattern 1 vs Pattern 3 marker: pure removal vs Pattern 3 marker for ORD provider HTTP coupling | **(а)** Pure removal — `OrdService.register_creative` has EXISTS-check + UNIQUE constraint protection; functional idempotency comes from those, not commit ordering. Pattern 3 marker would be misleading documentation suggesting retry-safety guarantee that's actually provided by EXISTS-check + UNIQUE |
| Q3 | Class iii disputes flush() switch: adopt? | **(а)** L299/L356 `commit()` → `flush()` switch. Preserves IntegrityError → 409 mapping; mirrors 5b.7b CL-1 precedent |
| Q4 | Class i flush() vs pure removal default | **(а)** Pure removal everywhere; relies on service-internal autoflush + handler-level autocommit. Adding `flush()` to all 31 sites would clutter codebase with redundant explicit-flush markers |
| Q5 | `cb_accept_rules` comment update style: update / delete / preserve | **(а)** Update to "Reload to get fresh attribute values from DB after service mutations" — removes stale "after commit" terminology |
| Q6 | `disputes.py:729` reclassification: treat as Class i / Class iii / preserve | **(а)** Class i (mechanical removal + drop L728 paranoia comment) — audit D1.1 mis-classified; no IntegrityError handling at this site |

## Relationship to 5b.7a O.4 / 5b.7b CL-1 closure attribution

- **5b.7a O.4** fixed bot handler `add_channel_confirm` (1 site) — established pattern: bot handlers using `DBSessionMiddleware` should not call explicit `session.commit()`.
- **5b.7b CL-1** fixed router `create_payout` (1 site) — established pattern: routers using `Depends(get_db_session)` should not call explicit `session.commit()`; `flush()` for IntegrityError surfacing.
- **5b.7c** applies P4 once-correctly across remaining 41 sites uniformly. Pattern crystalized: handler-level dependency (`get_db_session`/`DBSessionMiddleware`) owns commit lifecycle; explicit commits are redundant double-commits. Marker hygiene on Pattern 2 (9 routers using `async_session_factory()` directly) per CLAUDE.md S-48 contract documentation requirement.

After 5b.7c the codebase has uniform handler-level autocommit pattern. Remaining S-48 violations are known-deferred (see "Deferred to production launch" below).

## Why pure removal over flush() everywhere (Q4 rationale)

Per Marina Q4=(а): explicit `flush()` would clutter codebase with 31 lines of "I want flush, not commit" markers where service-internal autoflush + handler-level autocommit already cover all paths. `flush()` only at sites where downstream code reads from session needing post-flush state (Class iii disputes L299/L356 — `refresh()` follows IntegrityError catch and IntegrityError surfacing must be synchronous).

**Minimal disturbance principle.** 31 mechanical Pattern 1 removals stay pure deletions; 2 disputes.py sites get `flush()` switch because (a) IntegrityError catch must surface synchronously (without `flush()`, IntegrityError fires on `get_db_session.commit` at yield exit — too late for the 409 mapping), AND (b) `refresh()` follows in same handler. Adding `flush()` everywhere would obscure the `flush()`-actually-needed sites in noise.

## ord.py:55 NOT Pattern 3 (O.1 rationale)

Per investigation A.2.4 + Marina Q2=(а): `OrdService.register_creative` does EXISTS-check (`repo.get_by_placement` short-circuit) + UNIQUE constraint protection on `OrdRegistration.placement_request_id`. These provide functional retry-safety without commit-ordering guarantee.

Pattern 3 marker (`# S-48: external-boundary (...)`) is required only when DB row recording an external action MUST be visible to retry workers BEFORE further work fails. ORD register's retry-safety comes from application-level idempotency (EXISTS-check) and DB-level uniqueness (UNIQUE constraint), not from commit ordering. Pattern 3 marker would falsely suggest external-side-effect coupling to durability ordering — misleading documentation. Pure removal correct.

## disputes.py:729 reclassification (Q6 / O.4 rationale)

Audit D1.1 listed L729 under "Pattern 1 with inline IntegrityError handling — legitimate but could be flush()". Investigation A.4.3 verified: try/except at L713-726 wraps `transition_admin_override` for `(InvalidTransitionError, TransitionInvariantError)` only — NOT IntegrityError. Commit at L729 is OUTSIDE that try; pure Pattern 1 violation with no defensive 409 mapping.

L728 paranoia comment (`# Router owns the outermost transaction (S-48: service.flush() only).`) describes prior contract intent but is now stale post-`get_db_session` autocommit alignment. Reclassified Class i; treatment matches mechanical removal + paranoia comment cleanup.

## Verification

| Gate | Pre-5b.7c (`02bf454`) | Post-5b.7c |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| ruff format-check | 5 pre-existing files | 5 pre-existing files (unchanged — not introduced by 5b.7c) |
| pytest unit (excl `test_main_menu`) | 62F / 633P | 62F / 633P (verified after each of 5b.7c.2/.3/.4) |
| `make ci-local` aggregate (audit baseline) | 81F / 913P / 6S / 17E | unchanged (relative gate — no new failures introduced) |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |
| S-48 violations remaining (post-3b-5b.7c) | known-deferred only | unchanged (see Deferred to production launch) |

**Note on "62F / 616P" in 5b.7c prompt header.** Prompt-stated baseline was stale-by-17-passes; actual baseline at `02bf454` is 62F / 633P (verified by stash-revert + re-run). Failure count exact match (62) — relative gate "no new failures" preserved across all 4 production commits.

## Surfaces and resolutions (informational; investigation O.1-O.8)

| # | Surface | Resolution |
|---|---|---|
| O.1 | `ord.py:55` Pattern classification ambiguity | RESOLVED via Q2=(а) pure removal — EXISTS-check + UNIQUE provide retry-safety, not commit ordering |
| O.2 | `placement.py:305` explicit commit doesn't actually prevent retry duplicates anyway | INFORMATIONAL only (separate retry-safety concern; UX-equivalent before/after — not 5b.7c charter) |
| O.3 | `DBSessionMiddleware` lacks explicit rollback path (asymmetric to `get_db_session`) | DEFERRED to Phase 3 closure batch lessons (middleware-contract refactor; out of 5b.7c hygiene scope) |
| O.4 | `disputes.py:729` audit mis-classification (Class iii listed but no IntegrityError handling) | RESOLVED via Q6=(а) Class i reclassification + paranoia comment cleanup |
| O.5 | Pragmatic `session.rollback()` violations in bot handlers (`arbitration.py:322`, `placement.py:317` etc.) | DEFERRED to Phase 3 closure batch lessons (S-48 contract tension known issue; requires contract-level discussion not localized fix) |
| O.6 | `cb_accept_rules` stale "after commit" comment | RESOLVED via Q5=(а) update |
| O.7 | Site count 43 (not prompt's 40) | RESOLVED in this CHANGES (correct count documented; prompt headline was off-by-3) |
| O.8 | `make ci-local` baseline red gate semantic | DEFERRED via audit O.6 / Marina audit Q4 (relative gate operational) |

## Deferred to production launch (Phase 3 closure batch → BACKLOG, NOT inline)

- **`DBSessionMiddleware` explicit rollback path** (O.3) — middleware refactor to add `try/except` around handler invocation for symmetry with `get_db_session`. Out of 5b.7c hygiene scope; requires middleware-contract review.
- **Pragmatic `session.rollback()` violations in bot handlers** (O.5) — multiple handlers explicitly call `await session.rollback()` inside `except` blocks (necessary so next `session.execute()` doesn't raise `InFailedSQLTransactionError`). Pattern 1 strict reading conflicts with operational necessity. Requires CLAUDE.md S-48 contract clarification (allow `rollback()` in caller-owned pattern, OR migrate handlers to nested-savepoint pattern).
- **`payout_service.create_payout` dead code S-48 violation** (O.H from 5b.7b, re-surfaced) — `async with session.begin()` poisons sessions; deferred per 5b.7a Q7=(b). Phase 5 revival blocker; remove or fix at revival time.
- **Frontend update for handler-level autocommit awareness** — none required (HTTP boundary invariant); informational only.
- **Bot retry-safety on duplicate-creation paths** (O.2) — `placement.py:305` and similar sites: explicit commit doesn't prevent retry duplicates anyway; production-prep should add proper idempotency layer (UPSERT or business-key EXISTS-check). Not S-48 issue; separate workstream.

## Lessons (for Phase 3 closure batch — NOT inline BACKLOG)

- **L34 — Audit re-classification before execution.** Cross-sub-block audits (e.g. `tmp/PHASE3B_PRE_CLOSURE_AUDIT_2026-05-03.md`) provide canonical site enumerations, but classification assumptions need site-by-site verification. Investigation A.4.3 caught audit D1.1 mis-classifying `disputes.py:729` as Class iii (no IntegrityError handling at site). Re-grep + read-context (5-10 lines around each site) cheaper than trusting audit classification blindly. Pattern: audit gives the *list*; investigation verifies the *labels*.
- **L35 — Pattern 3 markers only for legitimately-paired-with-external-side-effect callsites.** `ord.py:55` looked like Pattern 3 (router commits after ORD provider HTTP), but functional idempotency comes from EXISTS-check + UNIQUE constraint, not commit ordering. Pattern 3 marker would have been misleading documentation suggesting retry-safety guarantee. Rule: Pattern 3 marker required only when DB row recording external action MUST be visible to retry workers BEFORE further work fails. If EXISTS-check or UNIQUE provides equivalent protection — Pattern 1 mechanical removal is correct.
- **L36 — Explicit `flush()` only where downstream code reads from session.** Marina Q4=(а) crystallized minimal-disturbance principle: 31 mechanical Pattern 1 removals stay pure deletions; 2 `disputes.py` sites (L299, L356) get `flush()` because IntegrityError catch must surface synchronously and `refresh()` follows. Adding `flush()` everywhere would clutter codebase with redundant explicit-flush markers where autoflush + autocommit already work. Rule: `flush()` only when (a) IntegrityError surfacing required mid-handler, OR (b) downstream `refresh()`/SELECT in same handler reads PK-materialized state.

## Out of scope (mirror 5b.7a/5b.7b closure pattern)

- Phase 4 / Phase 5 work
- Frontend changes
- Schema/migration changes
- Gate body refactoring (closed in 5b.3-5b.7b)
- `PayoutComplianceService` body fills (Phase 5 territory)
- Channel-add hook changes (5b.7a closed)
- `payout_service.create_payout` dead code (Q7 deferred)
- `DBSessionMiddleware` explicit rollback (O.3 deferred)
- Pragmatic `session.rollback()` cleanup (O.5 deferred)

🔍 Verified against: `02bf454` (pre) → `3bcda7c + 5b.7c.4 + 5b.7c.5` (post) | 📅 2026-05-03
