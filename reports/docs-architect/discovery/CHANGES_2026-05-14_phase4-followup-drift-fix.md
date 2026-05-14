# CHANGES 2026-05-14 — Phase 4 followup: migration "drift" false positive

## Context

PROMPT 34 был запущен с premise: Phase 4 ДС closure (v0.8.0, 2026-05-13)
добавил ORM models (`ContractEvent`, `Contract.parent_contract_id`) +
переименовал `placement_request_id → placement_id` + удалил `ord_audit_log`,
но не обновил миграцию `0001_initial_schema.py`. Запланированной стратегией
был edit 0001 per BL-061 pre-prod exception (S-33 precedent).

Probe ходом расследования показал что premise был **неверен**: migration
**был** обновлён в Phase 4 commit `0e6ef5b feat(model): supplementary
agreement extensions to Contract + new ContractEvent table`. Drift, который
показывал `alembic check`, был **false positive** из-за регистрационного
бага в ORM `__init__.py`.

## Real root cause

`src/db/models/__init__.py` re-exports все ORM models — это единственное
место, откуда `env.py` (через `from src.db.models import *`) импортирует
их и регистрирует в `Base.metadata` перед autogenerate.

Phase 4 commit (`0e6ef5b`) добавил `ContractEvent` в `__init__.py`, но
`OrdAuditLog` (введённый ранее в BL-080 8c commit `804fdf6`) был
**никогда добавлен** в `__init__.py`. Сама модель полностью определена
(`src/db/models/ord_audit_log.py`, 74 строки) и активно используется
в production через прямые пути импорта:

- `src/core/services/ord_service.py` — 10 audit writes
- `src/tasks/ord_tasks.py` — ERROR/RETRY events
- `src/db/repositories/ord_audit_log_repo.py` — repo class
- `src/api/routers/admin.py` — ADMIN_OVERRIDE events

Поскольку `env.py` загружает только то что в `__init__.py`, `OrdAuditLog`
не попадал в `Base.metadata` при alembic-runtime. Autogenerate сравнивает
ORM metadata с DB schema, видел "table exists в DB, отсутствует в ORM",
и выдавал ложный "drop table ord_audit_log".

## Changes applied

### `src/db/models/__init__.py`

Добавлено re-exporting `OrdAuditLog` + `OrdAuditEventType`:

```python
from src.db.models.ord_audit_log import OrdAuditEventType, OrdAuditLog
```

И в `__all__`:

```python
"OrdAuditEventType",
"OrdAuditLog",
```

Это восстанавливает regular ORM canonical visibility для `alembic` autogenerate
и для всех остальных consumers, которые могут импортировать через package
namespace вместо прямого пути.

### `0001_initial_schema.py`

**НЕ ТРОНУТ.** Файл уже полностью отражает post-Phase-4 ORM state благодаря
commit `0e6ef5b` (rename `placement_request_id → placement_id`, добавление
`parent_contract_id` + `contract_events` table + индексов + UNIQUE partial
`uq_contracts_supplementary_placement_role`).

### `e6a88faa9fa0_*.py`

**НЕ ТРОНУТ.** Immutable per BL-061.

## Verification

| Gate | Pre-fix | Post-fix |
|------|---------|----------|
| `alembic check` (pre-prod DB) | ❌ drift показан (false positive + real DB lag) | ❌ drift показан (только real DB lag — explainer ниже) |
| `alembic check` (fresh temp DB) | — | ✅ "No new upgrade operations detected." |
| `alembic upgrade head` (fresh temp DB) | — | ✅ clean apply (0001 → e6a88faa9fa0) |
| `ruff check src/` | 0 errors | 0 errors |
| `mypy src/` | 0/298 | 0/298 |
| `pytest --collect-only` | 1224 / 0 errors | 1224 / 0 errors |
| `pytest tests/ --ignore=tests/e2e_api` | (см. отдельный run) | (см. отдельный run) |

**Pre-prod DB still shows drift after fix** — это **не migration debt**, это
**DB schema lag**. Pre-prod DB был создан из earlier 0001 (до commit `0e6ef5b`)
и не был re-applied после Phase 4. Текущий 0001 + e6a88faa9fa0 + ORM —
**canonical и согласованы**, что доказывает fresh DB apply.

Pre-prod DB reset required для cleanup, но это **operational task**, не
migration code change. Per CLAUDE.md:

```bash
docker compose exec db psql -U postgres \
  -c "DROP DATABASE market_bot_db; CREATE DATABASE market_bot_db;" \
  && docker compose exec api poetry run alembic -c alembic.ini upgrade head
```

Validation против temp DB (`market_bot_phase4_test`) выполнена в этой
сессии вместо live pre-prod reset, чтобы не нарушить идущих containers
(api/bot/celery — Up 25h с активным connection к market_bot_db).

## Touched files

- `src/db/models/__init__.py` — добавлены OrdAuditEventType, OrdAuditLog
- `CHANGELOG.md` — entry в [Unreleased]
- `reports/docs-architect/discovery/CHANGES_2026-05-14_phase4-followup-drift-fix.md` (this file)

## Untouched

- `src/db/migrations/versions/0001_initial_schema.py` — already canonical (0e6ef5b)
- `src/db/migrations/versions/e6a88faa9fa0_*.py` — immutable per BL-061
- `src/db/models/ord_audit_log.py` — model уже корректный, проблема была только в re-export
- Phase 4 feature work — already shipped в v0.8.0
- BL-107 work — paused для duration of this fix; will resume через cherry-pick

## Migration Notes

- **No migration revisions added or modified.** 0001 + e6a88faa9fa0 остаются canonical.
- **Pre-prod DB reset operational task (independent of this commit)**:
  `DROP DATABASE market_bot_db / CREATE DATABASE market_bot_db / alembic upgrade head`.
  Required перед first production user (will produce schema matching ORM exactly).
- **Production fresh deploy** (когда настанет) сразу будет canonical — fresh
  `alembic upgrade head` apply'нет 0001 + e6a88faa9fa0 с полным Phase 4 schema.

## Followup

После cherry-pick `<fix_SHA>` в main session
(`feature/bl-107-channel-registration-verification`):

- BL-107 Phase B.1 baseline `alembic check` тоже потребует pre-prod DB reset
  для clean state. Альтернатива — phase B.1 запускать против temp DB как
  было сделано здесь.
- BL-061 honor: 0001 editable pre-prod exception **не использован** в этом
  fix (никаких 0001 edits). Phase B.1 still может использовать exception
  при необходимости.

## Lessons learned (BACKLOG candidates, no action этого commit)

- `__init__.py` re-export — single point of failure для alembic ORM
  visibility. Возможна `env.py` auto-discovery (pkgutil walk) как замена,
  устраняющая ручную регистрацию.
- Probe phase BL-107 не проверял `__init__.py` registration — added
  potentially к probe rubric.
- Tests fixture использует `metadata.create_all()` (per memory note) —
  это **тоже** имеет тот же баг: fixture создаёт только tables что в
  `Base.metadata` после import `src.db.models`, т.е. без `OrdAuditLog`
  до этого fix. Тестировочное покрытие для `OrdAuditLog` flow likely
  отсутствует или использует прямой `from src.db.models.ord_audit_log
  import OrdAuditLog`. BACKLOG audit candidate.
