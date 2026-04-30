# CHANGES — BL-061 close (F821 cleanup)

**Date:** 2026-04-30
**Branch:** feature/bl-061-f821-cleanup
**Closes:** BL-061
**Cleanup commit:** 3c42844

## Summary

Deleted stale `TestBadgeAchievementModel` class в `tests/unit/test_gamification.py` (lines 17–60 + decorator). Class was `@pytest.mark.skip`'d 6+ months с factually wrong reason; deletion closes all 6 F821 errors в codebase. Also removed now-unused `from sqlalchemy import select` import (only used inside the deleted class).

## Affected files

- `tests/unit/test_gamification.py` — deleted `TestBadgeAchievementModel` class (44 LOC including decorator) + removed unused `select` import (1 LOC). Other 4 test classes (`TestBadgeService`, `TestStreakBonus`, `TestCategorySubcategory`, `TestSubcategoriesFromDB`) untouched.
- `reports/docs-architect/discovery/F821_TRIAGE_2026-04-30.md` — committed as evidence trail.

## Evidence

- Triage: `reports/docs-architect/discovery/F821_TRIAGE_2026-04-30.md`.
- Skip reason claimed *"Badge model refactored in v4.3, only UserBadge exists"* — verified false: `Badge`, `BadgeCategory`, `BadgeConditionType`, `BadgeAchievement` all still live in `src/db/models/badge.py` (lines 36, 28, 16, 58).
- Last meaningful touch was `d61d748 test: add comprehensive tests for sprints 8-10` — the class was already skipped at that point.

## Baseline impact

| metric | before (post-BL-058) | after (BL-061) | delta |
|---|---|---|---|
| ruff total errors | 34 | 28 | −6 (all F821) |
| ruff F821 | 6 | 0 | −6 |
| ruff format check | 1 file would reformat | 1 file would reformat | unchanged (pre-existing drift in `src/db/migrations/versions/0001_initial_schema.py`, NEVER TOUCH per migrations policy 2026-04-30) |
| pytest failed | 96 | 96 | 0 |
| pytest passed | 753 | 753 | 0 |
| pytest skipped | 7 | 6 | −1 (the deleted class) |
| pytest errors | 133 | 133 | 0 |

Invocation: `poetry run pytest --continue-on-collection-errors -q --tb=no`. Walltime: 949.66s (15m49s).

## Business logic impact

- None. Deleted code was a `@pytest.mark.skip`'d test class — never executed since at least `d61d748`.
- No public contract changed. No API/FSM/DB/migration touched.

## Side note (deferred — not in scope)

- Skip reason wrong → possibly the `Badge` / `BadgeAchievement` model family lacks live unit-test coverage. Not in scope BL-061; deferred for ad-hoc fix or Phase 3 test-health pass.
- Pre-existing format drift on `src/db/migrations/versions/0001_initial_schema.py` exists on `develop` HEAD `4ea8231` (not caused by BL-061). Migrations versions are NEVER TOUCH per migrations policy 2026-04-30 — drift cannot be auto-fixed without a deliberate process exception.

## CHANGELOG.md

Not updated — test deletion only, no public contract change.

🔍 Verified against: 3c42844 | 📅 Updated: 2026-04-30
