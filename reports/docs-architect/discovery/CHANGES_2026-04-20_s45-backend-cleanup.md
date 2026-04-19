# S-45 Backend cleanup — CHANGES

**Branch:** `chore/s-45-backend-cleanup`
**Scope:** remove dead code identified in `FIX_PLAN_04_backend_cleanup.md`.
**Risk:** low. Three independent deletions; no behaviour change on any live
code path.

## Audit — no live callers for any removal

Before deletion, grep across `mini_app/`, `web_portal/`, `src/bot/handlers/`,
and `tests/` confirmed:

| Candidate | Live callers | Verdict |
|---|---|---|
| `POST /api/placements/{id}/accept` | 0 | **Remove** |
| `POST /api/placements/{id}/reject` | 0 | **Remove** |
| `POST /api/placements/{id}/counter` | 0 | **Remove** |
| `POST /api/placements/{id}/accept-counter` | 0 | **Remove** |
| `POST /api/placements/{id}/pay` | 0 | **Remove** |
| `DELETE /api/placements/{id}` | 0 | **Remove** |
| `DisputeRepository.get_by_user` | 0 | **Remove** |
| `celery_config.py` imports | 0 | Already clean — no action |
| `rating` queue consumer | 0 tasks routed to it | **Remove listener** |

`mini_app/src/api/placements.ts` and `web_portal/src/api/campaigns.ts` both
use `api.patch('placements/{id}', { action: ... })` for every action
(`accept|reject|counter|accept-counter|counter-reply|pay|cancel`). No
POST/DELETE calls survive.

`celery_config.py` was already deleted in S-36. Remaining references live
only in `docs/` / `reports/` / `CHANGELOG.md` (historical) and `.qwen/`
(external skills). `tests/tasks/test_celery_routing.py::test_celery_config_deleted`
actively guards against its return.

## Affected files

| File | Change | Lines |
|---|---|---|
| `src/api/routers/placements.py` | Removed 6 legacy endpoints + their helpers (`RejectRequest`, `CounterOfferRequest`, `NOT_CHANNEL_OWNER`, `NOT_PLACEMENT_ADVERTISER`, `field_validator` import) | −259 / +2 |
| `src/db/repositories/dispute_repo.py` | Removed `get_by_user` | −11 |
| `docker-compose.yml` | `worker_background` no longer listens on `rating` queue | −1 / +1 |

Total: **−271 / +3** (one-liner docker-compose swap counted both ways).

## Public contracts — effect

- **HTTP surface:** narrows. `PATCH /api/placements/{id}` with
  `action: accept|reject|counter|accept-counter|counter-reply|pay|cancel`
  remains the only action path. This has been the sole client invocation
  route since S-35 (advertiser wizard, owner inbox, counter-offer flow
  — all already using PATCH).
- **DB schema:** unchanged.
- **Celery task routing:** unchanged. The removed `rating` consumer was
  already unreachable — `task_routes` in `src/tasks/celery_app.py` does
  not include any rule pointing to `rating`.
- **FSM:** unchanged.

## Commits

- `f846ed0` — `refactor(api): remove legacy placement POST/DELETE endpoints`
- `080965a` — `refactor(db): remove unused DisputeRepository.get_by_user`
- `b32aeeb` — `chore(docker): drop dead rating queue from worker_background`

## Verification

- `ruff check src/api/routers/placements.py src/db/repositories/dispute_repo.py`
  → *All checks passed!*
- `ruff check src/` → 11 pre-existing errors in unrelated files
  (`document_validation.py`, `channel_owner.py`), 0 regressions in any
  touched file. Stash+recheck confirms the counts are identical before
  and after this branch.
- `grep` for `RejectRequest | CounterOfferRequest | NOT_CHANNEL_OWNER |
  NOT_PLACEMENT_ADVERTISER` across `src/` and `tests/` — no stale imports.
- `grep` for legacy endpoint paths across `mini_app/`, `web_portal/`,
  `src/bot/handlers/` — no live callers (matches only in `docs/` and
  `reports/` as historical documentation).
- `tests/test_api_placements.py` exercises `POST /` and `GET /` only;
  not affected by the removal.

## Deploy

```bash
docker compose up -d --build worker_background api
```

`worker_background` needs a restart because the listener list changed.
`api` picks up the removed routes. Nothing else moves.

🔍 Verified against: b32aeeb | 📅 Updated: 2026-04-20T00:10:00+03:00
