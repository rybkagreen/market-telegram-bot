# CHANGES — 16.5b Canonical PII keys extraction

**Date:** 2026-04-30
**Branch:** `feature/16-5b-pii-keys-canonical`
**BL:** BL-051 sub-task 4 (closed) + BL-056 (closed inline)

## What

Extracted canonical 18-key PII/credential scrub list к `src/utils/pii_keys.py`.
Refactored обоих Sentry init modules для import from canonical. Tuple literal
сохранён только в одном месте.

## Why

Two Sentry initializations drift'ились independently:

- `src/api/main.py:_SENTRY_PII_KEYS` (FastAPI process, was 13 keys)
- `src/tasks/sentry_init.py:_CELERY_SENTRY_PII_KEYS` (Celery process, was 16)

Symmetric difference 7 ключей: 5 missing в FastAPI (`address, email,
full_name, inn, phone`) + 2 extra в FastAPI (`password, x-api-key`).

Initial audit framing ("FastAPI strict subset, copy Celery → FastAPI") was
empirically wrong — FastAPI's `password` / `x-api-key` would have been
stripped by pure copy-merge. Шаг 0 inventory caught это до edit.

## How

Option chosen: **canonical extraction** (NOT union-in-both-files).

Rationale:
- Union в two files = duplicate literal. Drift возможен again через любой
  новый Sentry init module.
- Canonical module = drift impossible by import.
- Categorization documented в module docstring (auth / identity / documents
  / payment).
- BL-056 (deferred long-term improvement) closed inline — выгоднее чем
  ship union now and revisit later.

Case applied: **Case A** (no external usages). Шаг 0 grep showed both
private names (`_SENTRY_PII_KEYS`, `_CELERY_SENTRY_PII_KEYS`) used only
inside their own modules. Local literals removed entirely; both `_scrub_pii`
functions reference `SENTRY_PII_KEYS` directly. No alias needed.

`src/api/middleware/log_sanitizer.py` **NOT TOUCHED** — CLAUDE.md NEVER TOUCH
respected. Its 12-key list документирован в canonical module docstring как
known-allowed asymmetry historical decision. Если NEVER TOUCH lifted в
будущем — sanitizer also imports from canonical.

## Files

New:
- `src/utils/pii_keys.py` — canonical 18-key list + categorization docstring.
- `tests/unit/test_pii_keys_canonical.py` — structure invariants (8 tests).
- `tests/unit/test_sentry_inits_use_canonical.py` — behavioral smoke
  (3 tests: FastAPI request scrub, Celery extra scrub, Celery breadcrumbs
  scrub all 18 keys).

Modified:
- `src/api/main.py` — local set literal replaced с `from src.utils.pii_keys
  import SENTRY_PII_KEYS`. `_scrub_pii` body uses `SENTRY_PII_KEYS` directly.
- `src/tasks/sentry_init.py` — same replacement pattern.

## Tests

Local invocation: `poetry run pytest tests/unit/test_pii_keys_canonical.py
tests/unit/test_sentry_inits_use_canonical.py -v` → 11 passed.

Structure invariants:
- `len == 18`, no duplicates, tuple type, all-lowercase / no-whitespace.
- All 4 categories covered (auth, identity, documents, payment) — critical
  keys explicitly enumerated in tests.

Behavioral smoke:
- FastAPI `_scrub_pii` masks all 18 keys в `event["request"]`.
- Celery `_scrub_pii` masks all 18 keys в `event["extra"]` И
  `event["breadcrumbs"]`.

## CI baseline

`make ci-local` invocation:

- Ruff: 128 errors before → 128 errors after (baseline holds).
  Touched files contribute 0 ruff errors.
- Mypy on touched files (`src/api/main.py`, `src/tasks/sentry_init.py`,
  `src/utils/pii_keys.py`): 0 errors in those files (pre-existing 10 errors
  in 5 unrelated files unchanged).
- Pytest: `failed=76, errored=17, passed=736+11(new), skipped=7` — matches
  documented BL-054/BL-028 baseline. New 11 tests added to passing set.

`make ci-local` exits at lint stage (128 pre-existing ruff errors,
predominantly `UP017 datetime.UTC` in tests). Not introduced by this change.

## BL impact

- **BL-051 → 5/6** sub-tasks closed (next: 16.5c YooKassa over-collection).
- **BL-056 CLOSED** inline — canonical PII keys extraction shipped в той же
  серии где surfaced. No separate prompt needed.
- Sanitizer divergence documented как known-allowed; не surfaced as new BL —
  это existing condition, не new debt.

## Plan↔reality drift notes

Fourth time за серию 16.x audit framing был partially inaccurate:

1. 16.2 BL-047/BL-048 inversion.
2. 16.4 "UserResponse leak" реально = "ReferralItem leak".
3. 16.5a "11 vs 16 keys" — три списка с разным intent.
4. 16.5b "FastAPI strict subset Celery + 5 missing" — реально symmetric
   diff 7, не subset.

Pattern уже в memory: trust empirical Шаг 0 inventory over plan/audit
framing. Ни один из четырёх случаев не был поломан агентом — STOP gate
caught каждый.

🔍 Verified against: `53b142b` | 📅 Updated: 2026-04-30T00:00:00Z
