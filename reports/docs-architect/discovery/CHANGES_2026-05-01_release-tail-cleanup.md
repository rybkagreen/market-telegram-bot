# CHANGES — Release tail cleanup (2026-05-01)

## BL-071 — Correct deploy command for env_file changes

`docker compose restart <service>` does not re-read `env_file`. Use
`docker compose up -d <service>` which recreates the container with
refreshed environment.

Updated:

- `CLAUDE.md` — Commands / Docker subsection (single command snippet at
  top of file): `docker compose restart api` → `docker compose up -d api`
  with inline rationale comment. Note: the "Applying Changes" section
  the BL-071 finding referenced lives in operator memory (MEMORY.md),
  not in CLAUDE.md itself; CLAUDE.md only has the one Docker command
  snippet, which is now consistent with the BL-071 rule.

- `docs/AAA-09_DEPLOYMENT.md` — Section 7 (Incident Response Procedures),
  4 instances replaced:
  - 7.1 Service Down (line 535)
  - 7.2 Database Connection Issues (line 555)
  - 7.3 Celery Worker Stuck (line 574)
  - 7.4 Bot Not Responding (line 590)

  Each command's preceding numbered comment also updated from
  "Restart …" to "Recreate …" to match the new semantics. Inline
  rationale added once at section 7.1; the remaining three follow the
  same pattern.

## Obsolete WIP discovery files removed

Two untracked WIP discovery artifacts removed as obsolete after v0.1.0:

- `PHASE_17_2_RESEARCH_2026-05-01.md` — 17.2 closed in v0.1.0
- `PLAN_17-1_2026-04-30.md` — 17.1 closed in v0.1.0

Both contained references to `alembic.docker.ini`, removed in BL-070
during release v0.1.0 preparation.

## Affected files

| File | Change |
|---|---|
| `CLAUDE.md` | 1 line: `restart` → `up -d` + inline note |
| `docs/AAA-09_DEPLOYMENT.md` | 8 lines (4 commands + 4 comments) |
| `reports/docs-architect/discovery/PHASE_17_2_RESEARCH_2026-05-01.md` | deleted (was untracked) |
| `reports/docs-architect/discovery/PLAN_17-1_2026-04-30.md` | deleted (was untracked) |
| `reports/docs-architect/discovery/CHANGES_2026-05-01_release-tail-cleanup.md` | new |

## Business / contract impact

None. Documentation and operator-runbook only. No code, schema, API,
FSM, or task contract changes. Baseline (pytest + ruff + alembic
check) unchanged.

🔍 Verified against: 309dbbc96bfead5aae46a68fe900116e036477d0 | 📅 Updated: 2026-05-01T00:00:00Z
