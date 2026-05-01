# CHANGES — BL-067: Remove `src/api/routers/__init__.py` re-exports

**Date:** 2026-05-01
**Branch:** `chore/bl-067-remove-routers-init-reexports`
**Type:** chore (internal package shape, not public contract)

## Rationale

`src/api/routers/__init__.py` previously did:

```python
from src.api.routers.auth import router as auth
# … six more identical lines for billing/analytics/campaigns/channel_settings/placements/reputation
```

This pattern shadows attribute access on the `src.api.routers` package: the
name `src.api.routers.auth` resolves to an `APIRouter` instance, not к
module. That breaks two test patterns:

1. `from src.api.routers import auth` returns an `APIRouter`, not a module —
   `inspect`/attribute lookup against the auth submodule fails.
2. `monkeypatch.setattr(<module-object>, "X", …)` requires acquiring the
   module first, which the shadow makes harder than necessary.

Surface'd by BL-055 (`/api/auth/exchange-bot-token-to-portal`) integration
test, which had to use `importlib.import_module("src.api.routers.auth")` as
a workaround to bypass the shadow.

## Scope

- `src/api/routers/__init__.py` — emptied of re-exports; replaced with a
  module docstring documenting the explicit-import convention.
- `tests/unit/api/test_exchange_bot_token_to_portal.py` — `importlib`
  workaround removed; replaced with idiomatic
  `from src.api.routers import auth as auth_module` (which now resolves к
  module after the shadow is gone). Workaround comments removed.
- All production callers (notably `src/api/main.py`) already used explicit
  `from src.api.routers.<submodule> import router as <submodule>_router` —
  no production code change required.

## Backwards compatibility

- `from src.api.routers import auth` (and the six other shadowed names) no
  longer returns an `APIRouter` instance. Now resolves к module via Python's
  standard submodule import system. **No callers used the shadow form** in
  the previous codebase (verified by grep across `src/` and `tests/`); the
  re-exports were vestigial.
- Internal package shape only — not part of public contract. No
  CHANGELOG entry per scope guideline.

## Verification

- `python -c "import src.api.routers.auth; print(type(src.api.routers.auth).__name__)"`
  → `module` (was `APIRouter` before the fix).
- `python -c "from src.api.main import app; print(len(app.routes))"`
  → `144` routes registered. No regression.
- `pytest tests/unit/api/test_exchange_bot_token_to_portal.py -x` → 7
  passed (BL-055 coverage intact after workaround removal).
- `pytest tests/unit/api/test_placements_patch.py
  tests/test_bot_cancel_scenario_consistency.py -x` → 26 passed (adjacent
  router-importing tests intact).
- `ruff check` / `ruff format --check` on touched files: clean.

## Rollback

`git revert <SHA>` is safe. The change has no DB / migration / public-API
side effect — единственный effect is internal import resolution shape.

## Type 1/2 notes

- Type 1 (improve-and-note): import block in `test_exchange_bot_token_to_portal.py`
  re-sorted by `ruff --fix` after the workaround removal (single fix-up,
  expected for any edit к imports).
- Type 2 adaptations: none. Empirical research matched the BL-055 prompt
  context exactly (7 re-exports, single workaround consumer).

🔍 Verified against: this commit (HEAD of `chore/bl-067-remove-routers-init-reexports`) | 📅 Updated: 2026-05-01T13:30:00+03:00
