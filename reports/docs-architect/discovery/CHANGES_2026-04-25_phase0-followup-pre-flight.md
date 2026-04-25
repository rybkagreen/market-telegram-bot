# CHANGES 2026-04-25 — Phase 0 follow-up: Pre-flight research

## Scope

Research-only branch (`chore/phase0-followup`) executed before Phase 1 starts. Four pre-flight checks (PF.1–PF.4) addressed Phase 0 acceptance gaps surfaced during merge review. **No source code, schemas, contracts, or behaviour changed.**

Full analysis with verdicts and decision rationale: `PHASE0_FOLLOWUP_2026-04-25.md` (this directory).

## Affected files

### Added — research artifacts
- `tests/integration/test_ticket_bridge_e2e.py` — single integration test closing the gap left by `tests/unit/api/test_jwt_aud_claim.py` case 5 (case 5 stops at "consume returns AuthTokenResponse"; this test feeds the resulting `access_token` back into `get_current_user` to verify it actually authenticates). Passes (`1 passed in 5.29s` against `1fd0960`).
- `reports/docs-architect/discovery/PHASE0_FOLLOWUP_2026-04-25.md` — consolidated PF.1–PF.4 findings + recommendations.
- `reports/docs-architect/discovery/typecheck_baseline.md` — frozen mypy baseline (10 errors / 5 files / 272 source files at `1fd0960`). Any future error against this set = blocker.
- `reports/docs-architect/discovery/mypy_baseline_pre_phase0.txt` — raw `make typecheck` output at parent commit `59908b7`.
- `reports/docs-architect/discovery/mypy_baseline_post_phase0.txt` — raw `make typecheck` output at post-Phase-0 commit `1fd0960`.

### Not modified
No file under `src/`, `mini_app/`, `web_portal/`, `landing/`, `alembic/`, `docker*`, `pyproject.toml`, or `CHANGELOG.md` was touched. No public contracts changed.

## Business logic impact

None. This is verification + documentation work to gate Phase 1 entry.

## API / FSM / DB contracts

Unchanged.

## Decisions captured (input to Phase 1)

User-approved on 2026-04-25 after reading `PHASE0_FOLLOWUP_2026-04-25.md`:

1. **PF.2 — 426 flip + `WWW-Authenticate` header.** Phase 1 first commit (§1.B.0a) flips `src/api/dependencies.py:67` `HTTP_401_UNAUTHORIZED` → `HTTP_426_UPGRADE_REQUIRED` for the aud-less rejection branch and adds the `WWW-Authenticate` header (closing the inconsistency with the missing-credentials branch at line 44-49). Test `tests/unit/api/test_jwt_aud_claim.py::test_case3_*` updated. Marked as breaking-fix in CHANGELOG.

2. **PF.4 — `audit_middleware.py` refactor in §1.B.0b.** ≈ 21 LOC across 2 files (`src/api/middleware/audit_middleware.py` + `src/api/dependencies.py`): `_resolve_user_for_audience` writes `request.state.user_id`, helper `_extract_user_id_from_token` deleted, middleware reads from `request.state`. Closes the Phase 0 FIXME. Within the spirit of the ≤ 50 LOC threshold.

3. **PF.3 — host `poetry run pytest` accepted as canon.** Existing practice for `tests/integration/*`. Phase 1 docs to add a one-liner in CONTRIBUTING / dev-readme stating this. A TODO ticket "mount `tests/` into api image or add test-stage to Dockerfile" filed against Phase 3 (Phase 2 is reserved for `PlacementTransitionService` + `status_history`, not loaded with infrastructure work).

## Acceptance criteria — verified

- [x] `poetry run pytest tests/integration/test_ticket_bridge_e2e.py -v` → `1 passed in 5.29s`
- [x] `make typecheck` post-Phase-0 = `Found 10 errors in 5 files (checked 272 source files)` — identical error set to pre-Phase-0 (`59908b7`); 0 new errors in Phase 0 surface
- [x] `git status --short` clean apart from `.venv` and the five intentional artifacts above

## Why these decisions exist (audit trail)

The Phase 0 review surfaced four gaps during the merge into `develop`/`main`:

- The CHANGES doc claimed "no new mypy errors in Phase 0 surface" but full-repo `make typecheck` was not re-run → PF.1 verified independently.
- Phase 0 shipped 401 for aud-less tokens while `IMPLEMENTATION_PLAN_ACTIVE.md` §1.B.1 specified 426 → PF.2 chose the right resolution with evidence on whether legacy-token holders existed (they don't).
- `tests/unit/api/test_jwt_aud_claim.py` case 5 verifies the bridge response shape but never feeds the resulting token through the auth dependency → PF.3 closed that loop.
- Phase 1 plan proposed creating a parallel `aud_audit_middleware.py` rather than fixing the FIXME in the existing one — risk of permanent technical debt → PF.4 quantified the fix-in-place cost (≈ 21 LOC) to justify refactor.

🔍 Verified against: 1fd0960fb4e99fc03646475d89e52b5f972d287d | 📅 Updated: 2026-04-25T08:34:16Z
