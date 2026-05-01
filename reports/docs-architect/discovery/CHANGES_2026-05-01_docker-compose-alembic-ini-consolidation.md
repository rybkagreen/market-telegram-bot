# CHANGES — chore: consolidate docker-compose mounts на `alembic.ini`

## Дата
2026-05-01

## Тип
Internal infrastructure change (deprecation step). Не public contract.
**No CHANGELOG entry** — internal infra.

## Rationale

В repo два функционально идентичных alembic config файла:

- `alembic.ini` — local dev canonical config.
- `alembic.docker.ini` — bind-mount source для api/bot/seed-test
  containers, монтировался как `/app/alembic.ini` (rename-via-mount).

Файлы отличаются ровно одной комментарной строкой; функционально
идентичны (`script_location = src/db/migrations`, `prepend_sys_path = .`,
sqlalchemy.url считается из `DATABASE_URL` через `env.py`).

Поддержка двух копий — maintenance burden + источник confusion
(prior docs-fix `cdc2f7f` потребовался именно из-за этого rename
asymmetry). Этот PR1 переключает все три docker-compose mount source
entries на canonical `alembic.ini`. После production deploy + smoke
verification, отдельный PR2 удалит orphaned `alembic.docker.ini`.

## Aborted deletion record (per BL-013 (c) bundle)

В предыдущей сессии (2026-05-01T11:46Z) был запущен прямой attempt
удалить `alembic.docker.ini` + обновить `01_file_inventory.md:407`.
Type 4 HARD STOP'нут в research phase когда обнаружено что файл —
load-bearing bind-mount source в `docker-compose.yml:60` (bot),
`docker-compose.yml:220` (api), `docker-compose.test.yml:56`
(seed-test). Прямое удаление сломало бы Docker deploy.

**Lesson:** classification "broken/unused" требует empirical
verification перед mutation. Premise предыдущего prompt'а ("не mounted
properly") эмпирически не верна — файл mounted, просто переименован
на mount boundary.

PR1 (этот) делает файл legitimately not-load-bearing. PR2 безопасно
удалит после deploy verification.

## Scope (5 files touched)

| File | Change |
|---|---|
| `docker-compose.yml` (L60, bot service) | mount source `./alembic.docker.ini` → `./alembic.ini` |
| `docker-compose.yml` (L220, api service) | mount source `./alembic.docker.ini` → `./alembic.ini` |
| `docker-compose.test.yml` (L56, seed-test) | mount source `./alembic.docker.ini` → `./alembic.ini` |
| `alembic.ini` (L4) | comment uplifted к combined precise text (covers both env + fallback semantics) |
| `.qwen/PROJECT_SKILLS.md` (L127) | active instruction `-c alembic.docker.ini` → `-c alembic.ini` (missed hit от docs-fix `cdc2f7f`; .qwen/ был outside .md glob scope того prompt'а) |

Mount destination `/app/alembic.ini:ro` без изменений — внутри
container путь тот же, только source side switched. In-container
alembic команды (`alembic -c alembic.ini upgrade head`) не affected.

## Empirical verification

- `docker compose -f docker-compose.yml config --quiet` → exit 0
  (post-edit).
- `docker compose -f docker-compose.test.yml config --quiet` → exit 0
  (post-edit).
- `rg 'alembic\.docker\.ini' docker-compose.yml docker-compose.test.yml`
  → 0 hits (post-edit).
- `rg 'alembic\.docker\.ini' .qwen/` → 0 hits (post-edit).
- `poetry run ruff check src/ tests/` → 20 errors (baseline match).
- `poetry run ruff format --check src/ tests/` → 0 pending.

## Deployment

После merge в develop → main → production:

```
docker compose build --no-cache nginx api
docker compose up -d nginx api
docker compose restart bot
```

Pick up new mount source. Container internal `/app/alembic.ini`
identical, smoke verify через:

```
docker compose exec api poetry run alembic -c alembic.ini current
docker compose exec api poetry run alembic -c alembic.ini check
```

## Rollback

`git revert <SHA>` восстанавливает прежний mount config. Файл
`alembic.docker.ini` всё ещё на disk (этот PR его не трогает) —
no data loss, мгновенный rollback safe.

## PR2 (next, separate prompt)

После production deploy + smoke verification PR1 — отдельный branch
от свежего develop:

- `git rm alembic.docker.ini`
- update `reports/docs-architect/discovery/01_file_inventory.md:407`
  (entry removal или replacement note per Type 2 ADAPT-AND-LOG decision
  в том прогоне).

## Verified against
🔍 Verified against: develop @ 742b9b4 | 📅 Updated: 2026-05-01
