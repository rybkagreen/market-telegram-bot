# T1.2.6 — Placement-flow cluster + ESCROW false-positive

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07
**Pre-state HEAD:** 773eb38
**Pre-state baseline:** 12F / 981P / 3S / 0E + 7 lint (conftest) / 0 format / 4 mypy (mediakit)
**Status:** in-progress (commit 5 finalizes)

## Marina decisions

- **Cluster 1 (ESCROW invariant):** β — multi-callsite allowlist (publication_service.py + disputes.py advertiser_fault branch); AST or strict-regex comment-strip implementation, agent выбирает по ergonomics.
- **Cluster 2 (reputation FK ×4):** α — root `tests/conftest.py` shared fixture; 4 reputation tests refactored.
- **Cluster 3 (review INV-1 ×1):** α — status switch in test_review_service fixture (1 LOC); KISS, NOT reuse Cluster 2 fixture.

Rejected:
- ε delete (Cluster 1) — invariant still has defensive value via allowlist.
- β AST-only / γ inline (Cluster 2) — fixture sharing wins на reuse + DRY.
- β C5 wholesale / γ Cluster 2 reuse (Cluster 3) — over-engineering.

## Commits

### Commit 1 — `docs(t1.2.6): create placeholder CHANGES для interleaved updates`
- Hash: <set during commit>
- Files: reports/docs-architect/discovery/CHANGES_2026-05-07_t1-2-6-placement-flow-cluster.md (NEW)

### Commit 2 — `test(billing): modernize ESCROW invariant к multi-callsite allowlist`
- Hash: <set during commit>
- Files: tests/unit/test_billing.py (modify)
- LOC: +54/-21 (net +33), 75 changed lines.
- Implementation: AST-based scan via `ast.walk` over `Path("/opt/.../src").rglob("*.py")`. Filters `ast.Call` nodes whose callee is `release_escrow` (matches both `Name` and `Attribute` forms — covers `release_escrow(...)` и `obj.release_escrow(...)`). Skips `SyntaxError` files defensively.
- Approved callsites:
  - `src/core/services/publication_service.py` — success path (delete_published_post)
  - `src/api/routers/disputes.py` — admin dispute resolution (advertiser_fault, added в commit 8cfa49a)
- Test renamed: `test_release_escrow_only_in_delete_published_post` → `test_release_escrow_only_in_approved_callsites` (reflects new multi-callsite invariant).
- Removed unused `import subprocess` (was only used by replaced grep-based test).
- Why AST: robust против comments/docstrings/f-string false-positives — was Issue 1A в Phase A+B probe (line 595 docstring). Issue 1B (line 672 real call) addressed via allowlist expansion.
- Side fix: SIM114 ruff issue surfaced and resolved via fname helper variable refactor.
- Verify: `pytest TestEscrowReleaseLocation` PASSED. `ruff check`, `ruff format --check` pass.

### Commit 3 — `test(reputation): root fixture + refactor 4 FK-violating tests (Cluster 2)`
- Hash: <set during commit>
- Files:
  - `tests/conftest.py` (modify) — add `Decimal` import, add `PlacementRequest`/`PlacementStatus` import, add `placement_request` fixture (between `test_channel` и `placement_request_service`).
  - `tests/test_reputation_service.py` (modify) — 4 tests refactored к use `placement_request` fixture instead of hardcoded `placement_request_id=1`.
- Fixture `placement_request`: status `pending_owner` (early lifecycle, не trip INV-1 placement_escrow_integrity), depends on existing root fixtures `advertiser_user` / `owner_user` / `test_channel`. Real DB row, FK-resolvable.
- Side fix: `ReputationAction.PUBLICATION` → `ReputationAction.publication` в `test_history_recorded` (line 81). Pre-existing latent test bug — uppercase form is invalid (enum members lowercase per `src/db/models/reputation_history.py:16-34` и all production usage). Test prior failed at FK violation BEFORE reaching assertion; after FK fix, assertion bug surfaces. Fixing together per Principle 3 (no workarounds).
- Closes 4F. Pre-state: 11F. Expected post-state: 7F.
- Verify: `pytest tests/test_reputation_service.py::TestReputationService -v` → 4 PASSED.

### Commit 4 — TBD

### Commit 5 — TBD

## Deferred to production launch

(filled by commit 5 finalizer)

## Verification footer

(filled by commit 5 finalizer)
