# Mypy Baseline — Phase 0 Diff

**Date:** 2026-04-25
**Scope:** PF.1 follow-up research — verify Phase 0 introduced no new
mypy errors in the files it touched.

## Commit references

| Role | Hash | Description |
|------|------|-------------|
| PRE (parent of Phase 0, develop) | `59908b7` | `chore(develop): merge fix/plan-05-typed-exceptions — brand refresh, analytics unification, escrow pipeline, mobile sweep` |
| POST (post-Phase 0, develop) | `1fd0960` | `chore(develop): merge feature/env-constants-jwt-aud — Phase 0` |
| POST (post-Phase 0, main) | `7fe748c` | mirrors `1fd0960` (same tree) |
| Working branch | `chore/phase0-followup` | off `1fd0960` |

## Venv-compatibility precondition

`git diff 59908b7..1fd0960 -- pyproject.toml poetry.lock` returns empty.
The `.venv` symlink (→ `/root/.cache/pypoetry/virtualenvs/market-telegram-bot-7mWyOeBl-py3.14`)
is therefore identical for both checkouts. The same mypy build was used
both times.

## Total error counts (orientation only — not the gate)

| State | Errors | Files | Source files checked |
|-------|--------|-------|----------------------|
| PRE   | 10     | 5     | 271                  |
| POST  | 10     | 5     | 272                  |

Source-file count delta `+1` is consistent with Phase 0's net file
change: **+2** new modules (`src/constants/erid.py`,
`src/constants/legal.py`) **−1** deleted (`src/config/__init__.py`).

## The gate — new errors in Phase 0-touched files

Methodology: extracted `error:` lines from both raw mypy outputs,
sorted, and compared with `diff`. Output was identical byte-for-byte.

### Phase 0 file surface (23 files)

```
src/api/auth_utils.py
src/api/dependencies.py
src/api/main.py
src/api/middleware/audit_middleware.py
src/api/routers/auth.py
src/api/routers/auth_e2e.py
src/api/routers/auth_login_code.py
src/api/routers/auth_login_widget.py
src/api/schemas/auth.py
src/bot/handlers/shared/legal_profile.py
src/bot/handlers/shared/login_code.py
src/bot/handlers/shared/start.py
src/bot/main.py
src/config/settings.py
src/constants/erid.py
src/constants/legal.py
src/core/services/link_tracking_service.py
src/core/services/publication_service.py
src/core/services/stub_ord_provider.py
tests/unit/api/test_jwt_aud_claim.py
tests/unit/api/test_jwt_rate_limit.py
tests/unit/test_contract_schemas.py
```

(Note: `make typecheck` runs `mypy src/`, so the three `tests/…` files
are not in scope of this run by configuration. They have separate type
hygiene; that is not the question PF.1 is asking.)

### New errors in Phase 0-touched files

**Empty list.** None of the 10 surviving errors lives in any Phase 0
file. For reference, the 10 surviving errors (identical PRE and POST)
are concentrated in 5 untouched files:

```
src/bot/handlers/advertiser/campaigns.py:172  [call-arg]
src/bot/handlers/owner/channel_owner.py:439   [union-attr]  (×2)
src/core/services/analytics_service.py:397    [arg-type]
src/core/services/mediakit_service.py:111-116 [attr-defined] (×4)
src/tasks/ord_tasks.py:59                     [call-arg]    (×2)
```

## Verdict

**Clean. Phase 1 not blocked. Baseline frozen at 10 errors / 5 files.**

Phase 0's surface added zero new mypy errors. The pre-existing 10-error
baseline is unchanged in identity and count. Any future regression
should be measured against this same set; the per-file/per-code list
above is the canonical reference.

## Artifacts

- Raw PRE output: `reports/docs-architect/discovery/mypy_baseline_pre_phase0.txt`
- Raw POST output: `reports/docs-architect/discovery/mypy_baseline_post_phase0.txt`
- This summary: `reports/docs-architect/typecheck_baseline.md`

🔍 Verified against: `1fd0960` (post-Phase 0 develop) | 📅 Updated: 2026-04-25T00:00:00Z

---

## Note (added 2026-04-26)

Original PF.1 baseline `10/5/272` was labelled "errors/notes/files" —
incorrect. Correct semantics is **errors / files-with-errors /
source-files-checked** matching standard mypy output `Found N errors
in M files (checked K source files)`. Number values were correct;
labels were wrong. Subsequent reads should use corrected labels.

Current baseline (verified 2026-04-26 on main d5075ab):
`Found 10 errors in 5 files (checked 273 source files)` →
**10 / 5 / 273** under corrected semantics. The +1 in
source-files-checked is one new file added to tree since 7fe748c.
