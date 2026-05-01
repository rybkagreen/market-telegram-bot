# CHANGES — docs: fix `alembic.docker.ini` references к `alembic.ini`

## Rationale

Empirical evidence from BL-064 / BL-067 sessions showed that
`alembic -c alembic.docker.ini ...` invocations against the api
container fail with a `script_location` error. The default
`alembic.ini` (no `-c` flag, or `-c alembic.ini`) works cleanly.
File `alembic.docker.ini` exists at repo root but is not effectively
mounted / wired into the api container path layout. Documentation
across `CLAUDE.md`, `QWEN.md`, `docs/AAA-03_DATABASE_REFERENCE.md`,
`docs/AAA-09_DEPLOYMENT.md` was instructing users to use the broken
form. This commit fixes the docs to match what works empirically.

Removing the file `alembic.docker.ini` itself is **out of scope**
(non-`.md` change).

## Scope

`.md` files only. No code, configs, migrations, or tests touched.

## Files changed (4)

| File | Hits | Change |
|------|------|--------|
| `CLAUDE.md` | 2 | Reset command + verify-sync command |
| `QWEN.md` | 3 | After-models block, DB-reset block, deployment-rule footer |
| `docs/AAA-03_DATABASE_REFERENCE.md` | 2 | Config description (Type 1 redundancy collapse) + Docker run-migrations command |
| `docs/AAA-09_DEPLOYMENT.md` | 3 | Production migration apply + status-check + rollback step 3 |

Total active replacements: **10** occurrences across 4 files.

## Type 1 IMPROVE-AND-NOTE applied

`docs/AAA-03_DATABASE_REFERENCE.md:952` — original line listed three
config files, with `alembic.ini` (local) and `alembic.docker.ini`
(Docker) as separate entries. Literal replacement would have produced
`alembic.ini (local), alembic.ini (Docker)` (redundant). Collapsed to
`alembic.ini (local + Docker), alembic_sync.ini (sync operations)` —
single line, no LOC delta. This is bounded < 5 LOC, single file.

## HISTORICAL occurrences left untouched (2)

| File | Line | Reason |
|------|------|--------|
| `reports/docs-architect/discovery/01_file_inventory.md` | 407 | Repo file inventory snapshot describing existence of `alembic.docker.ini` (file does exist on disk + tracked in git). Historical reports dir; descriptive of repo state, not an active instruction. |
| `reports/docs-architect/discovery/PHASE_17_2_RESEARCH_2026-05-01.md` | 386 | File is **untracked** in git as of branch creation — likely in-progress Phase 17.2 research artifact. Modifying untracked work risks interfering with concurrent authoring. Out of scope; surface to Marina for separate handling. |

## Type 2 ADAPT-AND-LOG

The PHASE_17_2_RESEARCH skip is itself a Type 2 adaptation — the file
contains an active forward-looking command but its untracked status
makes it ambiguous whether it should be in this commit's scope. Default
lean: leave untouched, surface for Marina decision.

## Rollback

`git revert <SHA>` is safe. Docs-only change, zero code impact, zero
runtime impact. Worst case if reverted: docs return to broken
instructions; no service degradation.

🔍 Verified against: b924e7d2c6d931d1a6cc31cd9a5743edc793bd3f (develop)
📅 Updated: 2026-05-01T14:35:00+03:00
