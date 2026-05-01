# CHANGES — chore: BACKLOG batch update for 2026-05-01 work

## Дата
2026-05-01

## Тип
Documentation / process — BACKLOG.md tracking update. Не public contract.
**No CHANGELOG entry**.

## Rationale

Six closures + one process finding accumulated сегодня без BACKLOG
entries. Этот batch update закрывает gap.

## Scope

`reports/docs-architect/BACKLOG.md`:

1. **Header timestamp** uplifted: `_Last updated: 2026-04-30…_` →
   `_Last updated: 2026-05-01 (BL-064/066/067/068/069/070 closed; BL-071
   process finding added)_`.
2. **7 new entries appended** к "Closed items" section (после BL-052):

   | ID | Title | Type | Commit/merge |
   |---|---|---|---|
   | BL-064 | `charge_balance_for_plan` canonical enum alignment + expense analytics fix | RESOLVED | `c9a44d6` / merge `b924e7d` |
   | BL-066 | Split bot↔API HMAC secret из BOT_TOKEN | RESOLVED | `89d0c12` / merge `2c0d799` |
   | BL-067 | Remove `routers/__init__.py` re-exports | RESOLVED | `379fe8e` / merge `69dbc79` |
   | BL-068 | Docs fix: `alembic.docker.ini` → `alembic.ini` references в .md | RESOLVED | `cdc2f7f` / merge `742b9b4` |
   | BL-069 | docker-compose mount consolidation на canonical `alembic.ini` (PR1 of 2) | RESOLVED | `e577c7d` / merge `6ca5141` |
   | BL-070 | Remove orphaned `alembic.docker.ini` + file inventory update (PR2 of 2) | RESOLVED | `5bb291b` / merge `c93cc3c` |
   | BL-071 | `docker compose restart` does NOT re-read env_file (process-finding) | OPEN low-pri | (surface BL-066 deploy) |

## Empirical sources

Каждая entry sourced empirically:
- Commit messages read via `git log --format='%H %s%n%b'` для BL-064,
  BL-066, BL-067 (pre-existing today).
- BL-068, BL-069, BL-070 — work landed earlier in same session, SHAs
  captured in real time.
- BL-071 — surface'нут когда `docker compose restart bot` failed к
  pick up `BOT_API_HMAC_SECRET` from `.env` после BL-066 был provisioned;
  `docker compose up -d bot` resolved. Alpine probe via
  `docker run --env-file .env` confirmed `.env` content correct.

## Verified against
🔍 Verified against: develop @ c93cc3c | 📅 Updated: 2026-05-01
