# CHANGES 2026-04-19 — LSP setup (pyright + typescript-language-server)

## Scope
Dev-environment configuration for Claude Code native LSP tool. No runtime code
touched, no public contracts changed.

## Affected files
- `pyrightconfig.json` — **new**, project root
- `.venv` — **new symlink** → `/root/.cache/pypoetry/virtualenvs/market-telegram-bot-7mWyOeBl-py3.14` (already in `.gitignore`, not committed)
- `CLAUDE.md` — **new section** `## LSP — Code Navigation` right after `## Commands`: documents the native `LSP` tool, lists operations, defines usage policy (LSP-first for symbol navigation, Grep for text search), fallback signals

## Out-of-repo changes (developer machine only)
- `~/.bashrc` — appended `export ENABLE_LSP_TOOL=1`
- `/usr/local/bin/{pyright,pyright-langserver,typescript-language-server,tsserver,tsc}` — symlinks into `/opt/node-v22.19.0/bin/`
- `pipx` installed via `apt install pipx` (v1.4.3)
- `poetry` reinstalled via `pipx install poetry` (v2.3.4 at `~/.local/bin/poetry`)
- Host-side poetry venv rebuilt with `/usr/bin/python3.14` after the old `/app/.venv` (docker-created) was found broken on host (symlink to `/usr/local/bin/python3.14` that does not exist here)

## pyrightconfig.json highlights
- `pythonVersion: "3.14"`, matches `pyproject.toml` constraint
- `include`: `src`, `tests`, `scripts`, `conftest.py`
- `exclude`: `mini_app`, `web_portal`, `landing` (those have their own `tsconfig.json` + typescript-language-server), plus the usual `__pycache__`, `node_modules`, `htmlcov`, `logs`, `data`, `tmp`, `.venv`, `venv`
- `venvPath: "."`, `venv: ".venv"` — relative, portable; each dev creates their own `.venv` or symlink

## LSP smoke-test
Direct JSON-RPC roundtrip against `pyright-langserver --stdio`:
- `PlacementRequestService` → `src/core/services/placement_request_service.py:169`
- `ReputationRepo` → `src/db/repositories/reputation_repo.py:12`
Both match `grep "^class X"` ground truth — real goto-definition, no grep fallback.

Full-project `pyright --stats`: 2927 files parsed, 326 checked in 22.7s. 0 import-resolution errors on smoke-test target files (pre-existing type errors unchanged).

## Still to do (user action in TUI)
```
/plugin install pyright-lsp@claude-plugins-official
/plugin install typescript-lsp@claude-plugins-official
```
Then restart Claude Code so it re-reads `ENABLE_LSP_TOOL` and loads the plugins.

## Known leftover
`/usr/local/bin/poetry` — stale shim from an earlier `pip install poetry` (broken: `ModuleNotFoundError: No module named 'poetry'`). Currently masked by PATH order (`/root/.local/bin` comes first). Not removed — awaiting user decision.

## Business logic / API / FSM / DB impact
None. Zero changes to routers, services, models, migrations, handlers, FSM states.

---
🔍 Verified against: c05ec4d384092fe37d3cd52d6edbea1ef2479f93 | 📅 Updated: 2026-04-19T21:50:00Z
