# CHANGES — 2026-04-27 — Phase 2 § 2.B.0 alignment + § 2.B.1 skeleton

## Summary

Closes Phase 2 preparation work and skeleton landing. Bundles CHANGES
+ CHANGELOG that were deferred per BL-013 option (b) across multiple
commits since the pre-Phase-2 hotfix merge (commit `d5075ab` on main).

This single CHANGES file covers:
- § 2.B.0 alignment frozen (12 decisions + Tier-2).
- § 2.B.1 skeleton landed (migration + Pydantic + service + tests).
- Test-infrastructure cleanup (Pattern III completion in root conftest).
- Workflow cleanup (deploy.yml deleted, contract-check + frontend
  renamed to .disabled).
- 27 broken tests un-blocked across selective fix commits.
- Plan-08 → BL-014 fabricated reference fixed.

## Commits in this merge (16 total + 1 bundle)

### § 2.B.0 alignment + research
- `4ffa30a` docs(phase-2): research artifacts (Agent A/B/C + consolidation)
- `c8faaf8` docs(phase-2): CHANGES + CHANGELOG for pre-Phase-2 hotfixes
- `eb35903` docs(phase-2): § 2.B.0 alignment — 12 decisions + Tier-2 frozen
- `59b8a35` docs(backlog): Tier-3 items from Phase 2 research
- `7db453d` docs(phase-2): fix fabricated 'plan-08 backlog' reference

### Workflow cleanup + local CI gate
- `75288dc` chore(infra): cleanup dead workflows + add local CI gate (BL-017)

### Test infrastructure cleanup (Pattern III completion)
- `aba5f41` docs(phase-2): BL-008 triage — INVALIDATED + 117 failures categorised
- `99a696b` test(fixtures): remove obsolete current_role= from User-builders
- `19ba703` test(fixtures): satisfy INV-1 placement_escrow_integrity in ORD seeds
- `8b85377` test(publication): use spec= so isinstance checks match in source
- `3a9fbcf` test(conftest): wire root test_engine to postgres_container (Pattern III complete)
- `3c4231d` test(review-service): wire local db_session to root postgres_container

### § 2.B.1 implementation (skeleton, 4 artifacts)
- `009fc1c` db: add placement_status_history table and drop ord_blocked enum value
- `72fb7f7` core: TransitionMetadata Pydantic schema (closed model)
- `110e200` core: PlacementTransitionService skeleton
- `ded5b6c` test: unit tests for PlacementTransitionService

### This bundle commit
- `<NEW>` docs(phase-2): CHANGES + CHANGELOG bundle for § 2.B.0 + § 2.B.1

## Public contract delta

### Added (database)
- New table `placement_status_history` — append-only audit trail of
  placement status transitions. Autoincrement BIGINT PK, FK to
  `placement_requests` (CASCADE) and `users` (SET NULL), index on
  `(placement_id, changed_at DESC)`.

### Removed (database)
- Enum value `ord_blocked` from `placementstatus` — declared in DB
  enum but never used by ORM model (Decision 1 schema cleanup).
  Migration tested in both directions; pre-prod has 0 rows in
  `placement_requests`, so removal is safe.

### Added (Python)
- `src/db/models/placement_status_history.py` — `PlacementStatusHistory`
  ORM model.
- `src/core/schemas/transition_metadata.py` — `TransitionMetadata`
  Pydantic schema (closed, `extra="forbid"`, Literal enums for
  `trigger`, `error_code`, `admin_override_reason`).
- `src/core/services/placement_transition_service.py` —
  `PlacementTransitionService` with `transition()`,
  `transition_admin_override()`, `_sync_status_timestamps()`,
  `_check_invariants()`. NOT YET WIRED to existing 11 callers
  (§ 2.B.2 work).
- Exceptions: `InvalidTransitionError`, `TransitionInvariantError`.

### Changed (test infrastructure)
- Root `tests/conftest.py` `test_engine` fixture now consumes
  `postgres_container` testcontainer instead of reading
  `settings.database_url` (which pointed to `localhost:5432` with no
  host port binding). Pattern III completion.
- `tests/unit/test_review_service.py` local `db_session` override
  rewired to root `postgres_container`. File still under unit/
  pending move to integration/ (BL-022).

### Changed (CI)
- `.github/workflows/deploy.yml` — DELETED (never functional, 0 successful runs).
- `.github/workflows/contract-check.yml` — RENAMED to `.disabled`.
- `.github/workflows/frontend.yml` — RENAMED to `.disabled`.
- New `make ci-local` target for verification gate (replaces inert GH CI).

### Fixed (tests)
- `expires_at` consistency for placement counter_offer / pending_payment
  (24h via service path, was 3h).
- `check_scheduled_deletions` filter now restricted to `published` status.
- 27 placement-related tests un-blocked across 3 selective fix commits.

### Documented (BACKLOG, working tree)
- BL-008 → INVALIDATED (OOM hypothesis didn't reproduce).
- BL-014, BL-017 — added (correlation_id wiring, GH Actions inert).
- BL-018, BL-019 — added (gate phrasing, test-debt mountain).
- BL-021, BL-022 — added (DATABASE_URL hostname, test_review_service move).
- BL-023, BL-024 — added (newly-revealed errors, plan-validation gate (f)).
- All 9 process-findings remain in working tree, accumulating for
  Phase 3 closure packaged CLAUDE.md update per BL-006 protocol.

## Migration deployment notes

`placement_status_history` migration must be applied to production
database after merge to `main`. Pre-prod has 0 rows in
`placement_requests`, so backfill is empty (Decision 9). Migration
sequence:

```bash
# After merge to main + git pull on production server:
docker compose exec api poetry run alembic -c /app/alembic.ini upgrade head
docker compose up -d --build
```

Both directions (upgrade/downgrade) tested locally during § 2.B.1.
The `placement_escrow_integrity` CHECK constraint is dropped + recreated
during type swap (deviation #3 in Промт-3 closure).

## Verification gates

Phase 2 § 2.B.2 baseline (pytest, post-merge):

- failed ≤ 76
- errored ≤ 17
- collection ≤ 1

Mypy: 10 errors / 5 files / 278 source files checked.

Ruff: pre-existing baseline ≈ 12 (BL-007 drift).

## Origins

- IMPLEMENTATION_PLAN_ACTIVE.md § 2.B.0 (alignment) + § 2.B.1 (skeleton).
- BL_008_INVESTIGATION_2026-04-26.md — OOM hypothesis testing.
- CONFTEST_DB_INVESTIGATION_2026-04-26.md — Pattern III root cause.
- PROD_STATE_OBSERVATION_2026-04-26.md — workflow + production state.
- BL_008_TRIAGE_2026-04-26.md — 117 failure categorisation.
- PHASE2_RESEARCH_2026-04-26.md — original Tier-1 blockers.
