# CHANGES — chore: remove orphaned `alembic.docker.ini` + update file inventory

## Дата
2026-05-01

## Тип
Internal infrastructure change (PR2 of 2 — completes consolidation begun in PR1).
Не public contract. **No CHANGELOG entry**.

## Rationale

PR1 (`6ca5141`, merged earlier today) switched all three docker-compose
mount sources (`docker-compose.yml:60` bot, `docker-compose.yml:220` api,
`docker-compose.test.yml:56` seed-test) from `./alembic.docker.ini` →
`./alembic.ini`. Production deploy (`docker compose build --no-cache
nginx api && up -d nginx api`) recreated containers with the new mount
source, and in-container alembic was empirically smoke-verified:

```
$ docker compose exec api poetry run alembic -c alembic.ini current
e6a88faa9fa0 (head)
$ docker compose exec api poetry run alembic -c alembic.ini check
No new upgrade operations detected.
```

`/app/alembic.ini` inside containers now serves the canonical
`alembic.ini` from host (verified via `docker compose exec api cat
/app/alembic.ini` showing the new combined comment line).

`alembic.docker.ini` is therefore orphaned — no remaining tracked
non-.md references in the repo. Safe to delete.

## Scope

Two files touched:

| File | Change |
|---|---|
| `alembic.docker.ini` | **deleted** (`git rm`); 647 bytes, root:root, mtime Mar 20 21:03; was tracked since `97bb7b4` (S-01 initial public stage) |
| `reports/docs-architect/discovery/01_file_inventory.md` (L406-407) | row for `alembic.docker.ini` removed (approach D2-(i): standalone table row, removal preserves table structure); `alembic.ini` description uplifted to mention "mounted into Docker containers as `/app/alembic.ini`" so the table still surfaces the Docker context that the deleted row used to indicate |

## Empirical verification

Pre-deletion grep (PR1 already cleared non-.md refs):
```
$ git ls-files | xargs grep -l 'alembic\.docker\.ini' 2>/dev/null
reports/docs-architect/discovery/01_file_inventory.md          # this PR updates
reports/docs-architect/discovery/CHANGES_2026-05-01_docker-compose-alembic-ini-consolidation.md  # historical record (PR1 CHANGES)
reports/docs-architect/discovery/CHANGES_2026-05-01_docs-alembic-ini-fix.md                       # historical record (docs-fix CHANGES)
```

Post-deletion expected state: only the two historical CHANGES files
reference the name (legitimate immutable historical records — not active
instructions or load-bearing config).

## D2 approach used

**Approach (i): Remove entry entirely.** The entry was a standalone row
in a flat repo-root-files table. Adjacent rows (`alembic.ini`,
`alembic_sync.ini`) are independent. Removal preserves table structure
without leaving a "removed in <date>" stub.

The neighbouring `alembic.ini` description was uplifted minimally to
mention Docker mount usage so the doc still tells the reader where Docker
gets its alembic config from.

## Aborted-attempt lesson record

The earlier session (2026-05-01T11:46Z) attempted a direct deletion
prompt before PR1 existed. That attempt was Type 4 HARD STOP'ped during
research phase when the agent discovered `alembic.docker.ini` was
load-bearing (3 docker-compose bind-mount sources). The HARD STOP design
worked as intended — caught the destructive misclassification before any
mutation. PR1 + PR2 (this) is the correct decoupled path: PR1 makes the
file legitimately not-load-bearing (mount-source switch), PR2 deletes it
after empirical post-deploy verification.

## Rollback

`git revert <SHA>` restores the file (still in git history at
`97bb7b4` and prior commits). Docker-compose mounts no longer reference
the file, so revert alone is harmless — file would simply re-appear on
disk as orphaned. To fully revert the consolidation, additionally revert
PR1 (`6ca5141`).

## Verified against
🔍 Verified against: develop @ 6ca5141 | 📅 Updated: 2026-05-01
