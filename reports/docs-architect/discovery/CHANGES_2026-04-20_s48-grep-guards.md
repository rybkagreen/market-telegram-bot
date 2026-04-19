# S-48 Grep-guards — CHANGES

**Branch:** `chore/s-48-grep-guards`
**Parent plan:** `reports/20260419_diagnostics/FIX_PLAN_06_tests_and_guards.md` §6.4
**Scope:** second-line-of-defence bash script + `make` wiring that fails CI if
any of seven regression patterns re-appears in the repo. No runtime / behaviour
change, no code under `src/` / `mini_app/` / `web_portal/` / `landing/` is
touched.
**Risk:** very low. Pure tooling.

## Motivation

Earlier stages removed several frontend↔backend sources of drift:

- **S-43** — rename `reject_reason` → `rejection_reason` in placement flow.
- **S-44/S-45** — removal of the phantom paths `acts/?placement_request_id`,
  `reviews/placement/`, `placements/${id}/start`, `reputation/history`.
- **S-46** — ESLint `no-restricted-imports` rule forbidding direct
  `import { api }` in `web_portal/src/screens/**`, `components/**`,
  `hooks/**` (enforces `screen → hook → api-module` architecture).

ESLint is the primary guard for S-46, and the S-47 snapshot test protects
Pydantic response shapes. The grep-guard adds a cheap, language-agnostic net
that catches the same classes of regression even when ESLint is skipped (pre-
commit bypass, new tooling migration, etc.) and extends coverage to plain
string paths that a TypeScript linter cannot easily reason about.

## What was added

| File | Purpose |
|---|---|
| `scripts/check_forbidden_patterns.sh` | 7 regression patterns; `set -euo pipefail`; per-check clear error messages with filename:line; PCRE via GNU grep `-P`; skips `node_modules`, `dist`, `build`, `.git`, `.venv`, `.next`, `coverage`. |
| `Makefile` — target `check-forbidden` | `bash scripts/check_forbidden_patterns.sh`. |
| `Makefile` — `ci` target | now depends on `check-forbidden` in addition to `lint format typecheck`. |
| `CHANGELOG.md` — `[Unreleased]` | new S-48 section. |

## Patterns covered

| # | Pattern | Scope | Why |
|---|---|---|---|
| 1 | `import { api }` | `web_portal/src/screens/**` | Second net for the S-46 ESLint rule. |
| 2 | `reject_reason` | `web_portal/src/**` | Legacy field; backend shape is `rejection_reason` (S-43). |
| 3 | `acts/?placement_request_id` | `web_portal/src/**` | Phantom route removed in S-44. |
| 4 | `reviews/placement/` | `web_portal/src/**` | Phantom route removed in S-44. |
| 5 | `placements/${…}/start` | `web_portal/src/**` | Phantom route (no `/start` endpoint). |
| 6 | `reputation/history` | `web_portal/src/**` | Phantom route (reputation is exposed under `/ratings/*`). |
| 7 | `channels/${…}` (raw, outside api module) | `web_portal/src/**` excluding `src/api/**` | Same URL shape as router navigation (e.g. `/own/channels/${id}/settings`), so we use a PCRE lookbehind `(?<![/\w])channels/\$\{` to match **only** raw API-call usages. Directory exclusion keeps canonical `web_portal/src/api/channels.ts` allowed. |

All seven checks produce zero matches on `main` (see "Test-the-test" below).

## Test-the-test (DoD per FIX_PLAN §6 Definition of Done)

A temporary probe file `web_portal/src/screens/common/_regression_probe.tsx`
was written containing **one intentional violation of each pattern**. The
script was then executed — it failed with exit `1` and printed seven
`[FAIL]` blocks, one per pattern, each with the filename, line number, and
the matched snippet:

```
  [FAIL] no direct 'import { api }' in web_portal/src/screens/**
           web_portal/src/screens/common/_regression_probe.tsx:2:import { api } from '@/api/api'
  [FAIL] no 'reject_reason' in web_portal/src (use rejection_reason)
           …:16:  const reject_reason = 'x'
           …:17:  return reject_reason
  [FAIL] no phantom path 'acts/?placement_request_id' in web_portal/src
           …:14:  await api.get(`acts/?placement_request_id=${placementRequestId}`)
  [FAIL] no phantom path 'reviews/placement/' in web_portal/src
           …:12:  await api.post('reviews/placement/foo')
  [FAIL] no phantom path 'placements/${...}/start' in web_portal/src
           …:8:  await api.get(`placements/${id}/start`)
  [FAIL] no phantom path 'reputation/history' in web_portal/src
           …:10:  await api.get('reputation/history')
  [FAIL] no raw API path 'channels/${...}' outside web_portal/src/api/
           …:6:  await fetch(`channels/${id}`)
FAIL: forbidden pattern(s) detected (7 checks ran).
exit=1
```

Probe file was then removed and the script re-run:

```
OK: 7 check(s) passed — no forbidden patterns detected.
exit=0
```

## Baseline on main

No known violations recorded; no temporary excludes required. The first
production run on `main @ b23bd01` was green on all seven patterns.

## Local usage

```bash
# Direct invocation
bash scripts/check_forbidden_patterns.sh

# Via make
make check-forbidden

# Part of the full local CI suite
make ci          # lint + format + typecheck + check-forbidden
```

## Deferred to next sub-stage

Per the parent task, sub-stages §6.2 (Playwright E2E), §6.5 (AdminPayouts
tests), §6.6 (unified placement PATCH tests), §6.7 (docs) remain open. This
sub-stage does not select them; the decision is left to the operator.

## Validation

```bash
$ bash scripts/check_forbidden_patterns.sh
… 7 checks … OK: 7 check(s) passed — no forbidden patterns detected.
$ echo $?
0

$ make -n check-forbidden
bash scripts/check_forbidden_patterns.sh
```

No changes to `src/`, `mini_app/`, `web_portal/src/`, `landing/` or any
test file. Ruff / mypy / pytest baselines unchanged.

🔍 Verified against: b23bd01 (main @ start of sprint) | 📅 Updated: 2026-04-20
