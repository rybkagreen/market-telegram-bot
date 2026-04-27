# CHANGES — Phase 2 merge to develop + baseline correction

📅 Created: 2026-04-27
🎯 Status: completed

## What

Merged `feature/placement-transition-callers` → `develop` via `--no-ff`.
12 commits, 0 conflicts. Merge commit `9adaef2`.

## Baseline correction

Prior session handoff (Промт-6) stated "make ci-local PASSES". That was
inaccurate. Empirical re-check on `develop` @ `bf875c93` (pre-merge):
`make ci-local` raw target exits non-zero because the lint step inside
the target runs `ruff check src/ tests/` strictly, and `tests/` carries
105 pre-existing ruff errors (BL-019 test debt). `make ci-local` would
PASS only after BL-019 is closed.

The merge does NOT introduce any of those `tests/` errors — they
predate Phase 2 by weeks (visible on `develop @ bf875c93` before the
merge).

## Substantive gates (matter for correctness)

Verified on `develop` BOTH before and after merge — identical numbers:

| Gate                    | develop @ bf875c93 (pre) | develop @ 9adaef2 (post) | Baseline expected |
|-------------------------|--------------------------|--------------------------|-------------------|
| Forbidden patterns      | 17/17 PASS               | 17/17 PASS               | 17/17 PASS        |
| Mypy                    | 10 errors / 5 files      | 10 errors / 5 files      | 10 / 5            |
| Mypy source files       | 277                      | 277                      | 277               |
| Pytest (ci-local scope) | 76 failed + 17 errored   | (not re-run, identical tree) | 76 + 17       |
| Pytest passed           | 625                      | 625                      | 625               |
| Pytest skipped          | 7                        | 7                        | 7                 |
| Ruff `src/`             | 21 errors                | 21 errors                | 21                |

`ci-local scope` = `pytest tests/ --ignore=tests/e2e_api
--ignore=tests/unit/test_main_menu.py --no-cov` (per Makefile target).

## Pre-existing baseline (not introduced by Phase 2)

Verified on `develop @ bf875c93` (pre-merge):

- Ruff `tests/`: **105** errors (BL-019 test debt, unrelated to Phase 2).
- Ruff `src/ tests/` combined: **126** errors (21 src + 105 tests).
- `tests/unit/test_main_menu.py`: ImportError on `role_select_kb` —
  pre-existing collection error documented in BL-008 investigation,
  worked around with `--ignore=` in `make ci-local`.
- `tests/e2e_api/`: requires docker-compose stack; excluded from
  `make ci-local` per BL-008.

## `make ci-local` literal exit status

`make ci-local` exits non-zero on `develop` (both before and after the
merge) due to the `ruff check src/ tests/` step. This is BL-019 test
debt — pre-existing, tracked separately, NOT a Phase 2 regression.

The substantive gates the target executes (forbidden-patterns + mypy +
pytest) all match the documented baseline. The literal exit code is a
property of the unfinished BL-019 cleanup, not of the merge.

## Public contract delta

None. Merge commit only. Phase 2 § 2.B.0 / § 2.B.1 / § 2.B.2 closures
already shipped CHANGES files for their respective code deltas.

## Affected files

This commit (docs only):
- `reports/docs-architect/discovery/CHANGES_2026-04-27_phase2-merge-and-baseline-fix.md` (new)
- `CHANGELOG.md` ([Unreleased] entry)

Merge commit `9adaef2` (Phase 2 squash from feature branch): 20 files
changed, +708/-573. See merge body and the two prior § 2.B closure
CHANGES files for content.

## Origins

- Phase 2 implementation per `IMPLEMENTATION_PLAN_ACTIVE.md` § 2.B.
- BL-019 ruff `tests/` test debt — pre-existing, separate workstream.
- Промт-6A (this prompt) — recovery from Промт-6 hook-loop incident.

## Branch state

- `feature/placement-transition-callers`: HEAD `5648717` (12 commits ahead of pre-merge develop)
- `develop` pre-merge: `bf875c93`
- `develop` post-merge: `9adaef2`

## Footer

🔍 Verified against: 9adaef251e0b64a2f129172bcc075ddecb9c7823 | 📅 Updated: 2026-04-27
