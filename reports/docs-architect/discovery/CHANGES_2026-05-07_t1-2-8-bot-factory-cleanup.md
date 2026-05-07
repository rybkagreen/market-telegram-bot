# T1.2.8 — bot_factory mock target drift cleanup

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07 (nightrun)
**Pre-state HEAD:** 9b321e3 (T1.2.7 commit 3)
**Pre-state baseline:** 4F / 989P / 3S / 0E + 7 lint / 0 fmt / 4 mypy
**Status:** in-progress

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

### Commit N — TBD

## Deferred to production launch

(filled by closure)

## Verification footer

(filled by closure)
