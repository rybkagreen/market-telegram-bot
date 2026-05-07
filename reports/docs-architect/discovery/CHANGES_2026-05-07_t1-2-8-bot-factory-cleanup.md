# T1.2.8 — bot_factory mock target drift cleanup

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07 (nightrun)
**Pre-state HEAD:** 9b321e3 (T1.2.7 commit 3)
**Pre-state baseline:** 4F / 989P / 3S / 0E + 7 lint / 0 fmt / 4 mypy
**Post-state HEAD:** 7d560bd (Wave 2 commit 2) → finalized at commit 3
**Post-state baseline:** 0F / 993P / 3S / 0E + 7 lint / 0 fmt / 4 mypy
**Δ:** -4F closed (bot_factory ×4), +4P
**Status:** closed

## Marina decision

Default — agent autonomy для simple mock target path drift / aiogram constructor sig changes. STOP triggers для factory pattern refactor / deletion.

## Scope

4 failing tests:

```
tests/tasks/test_bot_factory.py::TestGetBotSingleton::test_get_bot_returns_singleton
tests/tasks/test_bot_factory.py::TestGetBotSingleton::test_init_bot_idempotent
tests/tasks/test_bot_factory.py::TestGetBotSingleton::test_close_bot_clears_instance
tests/tasks/test_bot_factory.py::TestGetBotSingleton::test_get_bot_initializes_if_none
```

All: `Bot()` mock not invoked / real Bot returned where mock expected. Pattern = aiogram infra drift.

## Commits

### Commit 1 — `docs(t1.2.8): create placeholder CHANGES для interleaved updates`
- Hash: <set during commit>

### Commit 2 — `test(bot-factory): mock new_bot instead of Bot symbol`
- Hash: <set during commit>
- Files: `tests/tasks/test_bot_factory.py` (×4 patch path updates + variable rename).
- Probe: `tmp/t1_2_8_probe.md` — classified scenario (i) per nightrun decision matrix (mock target path drift).

#### Root cause

`src/tasks/_bot_factory.py` was unified в commit `911a4c8 fix(billing): consolidate escrow pipeline and unify Bot factory` к delegate Bot construction к `src.bot.session_factory.new_bot()`. The `from aiogram import Bot` import в `_bot_factory.py` is retained но used only as type annotation (`_bot: Bot | None = None`).

Tests pre-dated этого refactor и mocked `src.tasks._bot_factory.Bot`. Patch was no-op (Bot symbol not invoked); `new_bot()` ran unobstructed; real Bot returned where mock expected.

#### Fix

Replace 4 occurrences of:
```python
with patch("src.tasks._bot_factory.Bot") as mock_bot:
    ...
    mock_bot.return_value = mock_instance
```

With:
```python
with patch("src.tasks._bot_factory.new_bot") as mock_new_bot:
    ...
    mock_new_bot.return_value = mock_instance
```

Variable renamed `mock_bot → mock_new_bot` for accuracy (now matches what's mocked).

#### Closes 4F. Pre-state: 4F/989P. Expected post-state: 0F/993P.

- Verify: `pytest TestGetBotSingleton -v` → 4 PASSED. Lint clean. Format clean.

### Commit 3 — `docs(t1.2.8): closure CHANGES finalize + tmp cleanup`
- Hash: <set during commit>
- Files: this file (finalize); rm `tmp/t1_2_8_probe.md`.

## Deferred to production launch

### Bot factory invariant — INV-3

Per `src/bot/session_factory.py` docstring: `Bot()` is created only в `session_factory.py` и `_bot_factory.py` (which delegates). If new direct callsites появляются, INV-3 invariant broken. Could be enforced via lint (similar к ESCROW-001 в Cluster 1 commit 2). Recorded для test-health epic Phase 4 backlog.

### Test infra — `_reset_factory()` helper

Tests call `_reset_factory()` в `setup_method`/`teardown_method` для clear singleton state. Could be elevated к pytest fixture с autouse. Out of T1.2.8 scope.

## Verification footer

🔍 Verified against: `7d560bd` | 📅 Updated: 2026-05-07T20:25:00Z
