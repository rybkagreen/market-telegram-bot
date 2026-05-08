# D4 closure — admin_client tests relocation to integration layer

**Date:** 2026-05-07
**Sub-block:** D4 (deferred from T1.2.5 Phase C-1)
**Pre-state:** HEAD `531cae6` (T1.2.5 C-2 closure docs), baseline 12F / 997P / 5S / 0E
**Post-state:** HEAD `<closure>`, baseline 12F / 997P / 5S / 0E

## Goal

Path 2 (relocate to integration layer) chosen per architectural cleanliness
principle. Admin endpoint with full ORM chain auth dependency = integration
test layer by definition.

## Decision rationale

Three architectural paths documented в T1.2.5 Phase C-1 closure CHANGES:

1. Extend tests/unit/conftest.py SQLite needed_tables — workaround
   (SQLite-mimicking-PostgreSQL slippery slope)
2. Relocate to tests/integration/api/ — clean layering ✓ chosen
3. Refactor `_resolve_user_for_audience` selectinload — out of scope
   (touches dependencies.py, T1.2.4d B3 reserved)

Marina principle: «архитектурная чистота, не временные решения.»
Path 2 = principled.

## Implementation

### Šаг 1 — relocate + adapt + namespace fix
- Commit: `b89f2c4`
- `git mv tests/unit/api/test_admin_payouts.py → tests/integration/api/test_admin_payouts.py`
- Fixture 4-way override → 1-way (get_db_session only); auth resolvers
  run real DI chain on testcontainer-seeded admin/advertiser users
- Service-layer mocks preserved (`payout_service.{approve,reject}_request`)
  at proper boundary
- `admin_user` fixture defined locally (DB-seeded); `advertiser_user`
  reused from tests/conftest.py:378
- `fake_payout_{paid,rejected}` parametrized by `admin_user.id` (was
  hardcoded 9001); same for `assert_awaited_with` calls
- JWT `source="web_portal"` (admin endpoint requires web_portal audience
  per BL-049)
- **Latent fix:** added empty `tests/unit/__init__.py` +
  `tests/integration/__init__.py` to resolve pytest package namespace
  collision (see L61 below)

### Šаг 2 — closure CHANGES + cleanup
- This file
- Commit: `<closure>`
- tmp/ cleanup

## Verification

| Stage | F | P | S | E |
|---|---|---|---|---|
| Pre Šаг 1 | 12 | 997 | 5 | 0 |
| Post Šаг 1 (after namespace fix) | 12 | 997 | 5 | 0 |
| Targeted: `tests/integration/api/test_admin_payouts.py` | — | 9 | — | — |

Baseline preserved exactly (12F / 997P / 5S / 0E) — no regression, no
test-count drift between unit and integration discovery.

## Cumulative T1.2 progress

D4 closure: +1 entry (~60/99 → ~61/99).

## Lessons

### L61 — Pytest «sub-package without parent» collision

**Symptom:** adding `tests/integration/api/__init__.py` triggered 9
ModuleNotFoundError на existing `tests/unit/api/test_*.py` файлах.

**Cause:** Pytest `prepend` import mode (default до pytest 9) определяет
package-path тестового файла, поднимаясь вверх до first dir БЕЗ
`__init__.py`. State до Šаг 1:

```
tests/__init__.py        ✓
tests/unit/              ✗ no __init__.py
tests/unit/api/__init__.py  ✓
```

→ `tests/unit/api/test_X.py` registered as top-level package
`api.test_X` (поднялся до `tests/unit/`, увидел отсутствие __init__,
зафиксировал `tests/unit/` как rootdir-equivalent).

When `tests/integration/api/__init__.py` was added, second directory
заявил тот же top-level package `api`. Python module system выбрал
один (likely lex-first), второй полностью разломан.

**Это латентный баг проекта,** не следствие D4 specifically — любая
expansion of `tests/<layer>/api/` triggered бы тот же collision.

**Fix:** add empty `tests/unit/__init__.py` + `tests/integration/__init__.py`
→ proper sub-package hierarchy (`tests.unit.api`, `tests.integration.api`,
distinct fully-qualified names).

**Apply forward:**

1. **Перед добавлением test files в любой `tests/<layer>/<subdir>/`,
   проверить parent `__init__.py` chain:**
   ```bash
   find tests/ -type d ! -name __pycache__ -exec test -e {}/__init__.py \; -print
   ```
2. **Если parent не пакет, но subdir/__init__.py добавляется** —
   обязательно создать parent __init__.py одновременно.
3. **Project-wide audit candidate:** проверить, есть ли другие
   sub-package-without-parent ловушки в `tests/`. (Напр.
   `tests/unit/services/__init__.py` без `tests/unit/__init__.py` =
   та же проблема, ждёт триггера.) В D4 scope не входит — surfaced
   for follow-up.
4. **Long-term cleanup option:** switch `pyproject.toml` pytest
   addopts to `--import-mode=importlib` — modern pattern избегает
   namespace fights целиком, но требует separate validation pass
   (тоже не D4 scope).

**Diagnostic phrase для будущего:** «ModuleNotFoundError на
existing tests» при добавлении нового test directory = check
__init__.py chain первым делом.

🔍 Verified against: `b89f2c4` (D4 Šаг 1) | `d68b302` (develop) | `59c4094` (main) | 📅 2026-05-07
