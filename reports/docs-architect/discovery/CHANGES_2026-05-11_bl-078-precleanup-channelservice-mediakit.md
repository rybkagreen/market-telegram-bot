# CHANGES — BL-078 pre-cleanup: drop ChannelService mediakit duplicates

**Date:** 2026-05-11
**Branch:** `feature/bl-078-precleanup-channelservice-mediakit`
**Base:** `develop` @ `213aef2`
**Author:** Claude Code (executor) / Marina (decision owner)

## Scope

Q8 default из BL-078 14 defaults batch (approved 2026-05-11): **(c) pre-cleanup PR first**.

Удалены 2 duplicate dead methods из `src/core/services/channel_service.py`:
- `ChannelService.get_or_create_mediakit` (lines 89-102 pre-cleanup)
- `ChannelService.update_mediakit` (lines 104-122 pre-cleanup)

Также удалён unused импорт `from src.db.models.channel_mediakit import ChannelMediakit` (line 9 pre-cleanup) — после delete двух методов модель в файле больше не используется.

Net: `-36 lines` (1 import + 34 method body + 1 inter-method blank). Файл: 146 → 110 lines.

## Why

Per `tmp/bl078_mediakit_probe.md` §4 + §5.1:
- ZERO production callers (router/handler/keyboard/Celery/FSM grep)
- ZERO test callers
- Functionality дублирует `MediakitService` (rewrite в Phase B); `ChannelService` variants — orphan stubs
- Pre-cleanup перед Phase B rewrite reduces risk: pure deletion commit independently verifiable, then rewrite proceeds against clean baseline

## Affected files

- `src/core/services/channel_service.py` — `-36 / +0`

## Verification

Baseline gates **unchanged** относительно develop @ `213aef2`:

| Gate | Pre-cleanup | Post-cleanup |
|------|-------------|--------------|
| `make format-check` | 0 | 0 |
| `make lint` | 7 (BL-024 conftest) | 7 (BL-024 conftest) |
| `make typecheck` | 4 (`mediakit_service.py:111-116`) | 4 (`mediakit_service.py:111-116`) |
| `make ci-local` pytest | 0F / 997P / 3S / 0E | 0F / 997P / 3S / 0E |
| `make ci-local` exit | 1 (aggregator on lint+mypy baseline) | 1 (aggregator on lint+mypy baseline) |

Empirical grep confirmation после delete:
- `grep -rn "ChannelService.*get_or_create_mediakit\|ChannelService.*update_mediakit" src/ tests/ web_portal/src/ mini_app/src/` → 0 hits
- `grep -rn "\.get_or_create_mediakit\|\.update_mediakit" src/ tests/ web_portal/src/ mini_app/src/ | grep -v "mediakit_service\|MediakitService"` → 0 hits
- `grep -n "ChannelMediakit\|get_or_create_mediakit\|update_mediakit" src/core/services/channel_service.py` → 0 hits

## Out of scope (Phase B work)

- `MediakitService` rewrite (3 methods)
- `_session_ctx` drop / relocate (`comparison_service` coupling)
- `mediakit_pdf.py` changes
- New PDF endpoint, schemas, frontend, tests, docs
- `is_published`, `views_count`, `downloads_count` column handling (Q5/Q6 — wire в Phase B)
- 4 mypy errors в `mediakit_service.py:111-116` — fixed Phase B (rewrite метода `get_mediakit_data`)

## References

- Probe input: `tmp/bl078_mediakit_probe.md` §4, §5.1
- BACKLOG: BL-078 (full rewrite path-decision 2026-05-08)
- 14 defaults batch: Marina approved 2026-05-11 (Q8 = (c) pre-cleanup PR first)

## Commits

### Commit 1 — `chore(channels): drop dead ChannelService mediakit duplicates (BL-078 pre-cleanup)`
- Hash: filled-in после `git commit`
- Files (2): `src/core/services/channel_service.py`, `reports/docs-architect/discovery/CHANGES_2026-05-11_bl-078-precleanup-channelservice-mediakit.md`
