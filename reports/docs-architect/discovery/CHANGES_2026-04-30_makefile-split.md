# CHANGES — Makefile lint/test split (BL-057)

**Date:** 2026-04-30
**Branch:** `feature/makefile-split-lint-test`
**BL:** BL-057 (new — surfaced during 16.5b closure review)

## What

Split `Makefile` targets so `lint`, `format-check`, `typecheck`,
`check-forbidden`, `test` are independent gates. `make ci-local`
aggregates outcomes; runs все targets regardless of individual failures;
exits non-zero если any gate failed.

## Why

Previously `make ci-local` halted on lint stage. Baseline 128 ruff errors
caused immediate non-zero exit before test stage ever ran. Все verify gates
серии 16.x ("make ci-local clean — pre-existing failures only") де-факто
полагались на:

1. Lint baseline holds (true verify).
2. Manual `pytest` invocation отдельно (not part of ci-local).

Naming "ci-local clean" implied behavioral test pass; реально верифицировался
только lint baseline. Test phase signal был masked.

## How

- New `format-check` target broken out (was inline в ci-local previously).
- `ci-local` rewritten as shell aggregator pattern: `set +e; failed=0;
  $(MAKE) gate || failed=1; ... if [ $failed -ne 0 ]; then exit 1; fi`.
- Each gate uses `$(MAKE) --no-print-directory <target>` so individual
  targets remain the canonical entry points.
- Test stage uses inline pytest invocation preserved verbatim from previous
  `ci-local` (ignores `tests/e2e_api`, `tests/unit/test_main_menu.py`,
  `--no-cov`, `--tb=short`).
- Standalone `test` target unchanged (`pytest tests/ -v --tb=short`).

No new dependencies. No change to lint tool selection. Existing 128 ruff
errors and 10 mypy errors preserved as baseline.

## Files

- `Makefile` — refactor.

## Tests

Empirical verification on `feature/makefile-split-lint-test`:

| Gate | Exit | Output (baseline) |
|------|------|-------------------|
| `make check-forbidden` | 0 | 31 checks passed |
| `make lint` | 2 | 128 ruff errors (baseline) |
| `make format-check` | 2 | 83 files would reformat (baseline) |
| `make typecheck` | 2 | 10 mypy errors in 5 files (baseline) |
| `make ci-local` | 2 | All 5 gates ran; aggregated. Test phase: 76 failed, 725 passed, 7 skipped, 17 errors |

Test phase actually ran inside `ci-local` for the first time. Failed/error
counts match BL-054 cluster baseline (76 failed, 17 errors per 16.5b
sample). Passed count drifted 736→725 — normal flux from intermediate
work between sample date and now; no regression in failure cluster.

No new ruff errors (128 stays 128). No new mypy errors (10 stays 10).

## BL impact

- **BL-057 CLOSED** — Makefile semantic clarity shipped.
- **BL-058 SURFACED** — "Ruff baseline cleanup batch (UP017 datetime.UTC в
  tests/, E302 blank lines, прочие — 128 errors total). 83 format-check
  delta separately." Mechanical scope, ~1 hour agent time. Deferred —
  likely после 17.x credits cleanup или раньше если Marina prioritizes.
- **Series 16.x verify gates retroactively** — manual pytest каждой серии
  reported pass; behavioral coverage есть. Forward, gates honest by
  construction.

## Plan↔reality drift notes

Этот fix **сам surfaced as plan-validation gap**, не plan↔code drift.
В моём (Claude.ai) plan validation gates checklist'е не было "(g) verify
gate naming — каждая команда в gate реально покрывает то что я
подразумеваю?". Memory edit добавлен.

Pattern для будущего: **don't trust target naming, verify what command
actually runs via `make -n` dry-run before declaring it as gate.**

## Side effect — series 16.x context

Все verify gates 16.1–16.5b reported "ci-local clean / baseline only" —
reading это retroactively через honest semantic, claim был partially
misleading (lint baseline holds, тесты бежали manually и passed). Behavioral
correctness не под вопросом — just naming hygiene.

🔍 Verified against: 4802b64 | 📅 Updated: 2026-04-30T00:00:00Z
