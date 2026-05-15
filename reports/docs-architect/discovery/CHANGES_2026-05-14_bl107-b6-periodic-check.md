# CHANGES 2026-05-14 — BL-107 Phase B.6 (Periodic re-verification Celery task)

## Context

Background half of the BL-107 manual+automatic verification stack. Phases
B.4 и B.5a/b shipped the two static verification paths (Trustchannelbot
admin check at channel-add and manual evidence submission через
mini_app + admin review). Phase B.6 closes the temporal loop: existing
verified channels are re-checked daily, and verification state mutates
when underlying Telegram-side facts change.

**What this enables:**

- @Trustchannelbot removed от channel admins → verification automatically
  lost within 24h, owner notified, audit trail recorded.
- Channel grew past ФЗ-303 threshold since verification was granted →
  threshold-crossing counter increments (admin can manually re-review).
- `member_count` refreshed nightly, `last_blogger_registry_check_at`
  timestamps updated.

Built atop Phase B.5b (`e114948`). No frontend, no endpoint, no DB
schema change.

## Changes

### New file — `src/tasks/channel_registry_tasks.py`

Single module (175 lines) with sync Celery task wrapper +
`asyncio.run(_check_channel_registry_status_async())` async body.

| Symbol | Purpose |
|---|---|
| `check_channel_registry_status` | sync Celery task — `name="parser:check_channel_registry_status"`, `queue="parser"` |
| `_check_channel_registry_status_async` | async implementation; consumes `settings.rkn_periodic_check_enabled`, `settings.rkn_threshold_subscribers` |

Returns counters dict — `processed`, `threshold_crossed`,
`verification_lost`, `still_verified`, `member_count_refreshed`,
`api_failures` — for observability and tests. Returns `{"skipped":
"disabled"}` if feature flag off.

Uses:

- `ephemeral_bot()` per S-37 — `asyncio.run` task needs loop-bound Bot
- `celery_async_session_factory as async_session_factory` per project alias
- `verify_trustchannelbot_admin` + `TrustchannelbotResolutionError` from Phase B.3
- `BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN` — only this method re-checked
- `AuditLogRepo` — single fire-and-forget log when verification lost
- `notify_owner_verification_lost` — new Phase B.6 helper

S-48 compliance: task is top-level caller for its own unit of work →
`await session.commit()` inside task body is allowed (Pattern 2-ish:
task opens its own session, commits at end).

### Modified — `src/tasks/celery_app.py`

Two edits:

1. **`include` list** — added `"src.tasks.channel_registry_tasks"`
   alphabetically between `billing_tasks` и `cleanup_tasks`. Required
   for Celery to register the task.
2. **`get_beat_schedule()` dict** — new entry
   `bl107-check-channel-registry-status-daily`:

   ```python
   "bl107-check-channel-registry-status-daily": {
       "task": "parser:check_channel_registry_status",
       "schedule": crontab(hour=3, minute=45),
       "options": {"queue": QUEUE_PARSER},
   }
   ```

   Slot 03:45 UTC — между collect-stats (03:30 UTC) и Sunday cleanup
   (03:00 UTC). No collision с other scheduled work.

### Modified — `src/core/services/notification_service.py`

Added module-level helper at file end:

```python
async def notify_owner_verification_lost(
    session: AsyncSession,
    owner_user_id: int,
    channel_id: int,
) -> bool:
```

Looks up owner через `UserRepository(session).get_by_id(...)`,
dispatches `notify_user.delay(...)` Celery task with HTML message:

> ⚠️ Верификация канала сброшена
>
> Канал ID: <code>{id}</code>
>
> @Trustchannelbot больше не является администратором канала, поэтому
> автоматическая верификация в Реестре блогеров (ФЗ-303) была
> отозвана.
>
> Чтобы восстановить статус, добавьте @Trustchannelbot обратно в
> администраторы канала или подайте заявку вручную через раздел
> «Реестр блогеров» в mini app.

Pattern matches Phase B.5a `notify_owner_verification_decided` —
session-arg signature, returns `bool` (success), session read-only
(no commit).

### New file — `tests/unit/test_bl107_periodic_re_verification.py`

11 pure unit scenarios, AsyncMock-only:

| # | Scenario | Verifies |
|---|---|---|
| 1 | Feature flag disabled | Returns `{"skipped": "disabled"}`, no factories touched |
| 2 | No channels match | Counters all 0, `session.commit()` still called once |
| 3 | Trustchannelbot still admin | `still_verified` ++, no field mutation |
| 4 | Trustchannelbot removed | 5 fields reset, audit logged, owner notified |
| 5 | MANUAL_EVIDENCE channel | `verify_trustchannelbot_admin` NOT called for this channel |
| 6 | Threshold crossing | `threshold_crossed` ++ when verification snapshot < 10k и current ≥ 10k |
| 7 | `bot.get_chat` raises | `api_failures` ++, no other side effects |
| 8 | `TrustchannelbotResolutionError` | `api_failures` ++, no verification reset (transient) |
| 9 | Member-count refresh | `member_count_refreshed` ++, field updated |
| 10 | Multi-channel aggregation | 3 channels с mixed outcomes — counters aggregate |
| 11 | Single commit | `session.commit()` called exactly once at task end |

Mocks: `ephemeral_bot` / `async_session_factory` replaced with
`@asynccontextmanager`-decorated stubs yielding pre-built AsyncMock
instances. `AuditLogRepo` class replaced с MagicMock so `.log(...)`
doesn't touch the mocked session's `begin_nested`.
`notify_owner_verification_lost` patched separately.

Coverage on `channel_registry_tasks.py`: 98%.

### Modified — `CHANGELOG.md`

Added `### Phase B.6 — BL-107 Periodic re-verification Celery task`
subsection under `[Unreleased]`. Documents added items, behavior
change, feature flag, и operational notes.

## Untouched (deferred к subsequent phases)

- **Endpoints** — Phase B.5a stable
- **Frontend** — Phase B.5b stable
- **Schema / migrations** — Phase B.1 done; no model changes
- **Gate framework** — Phase B.2 stable
- **Telegram helpers** — Phase B.3 stable (only consumed)
- **Channel-add hookup** — Phase B.4 stable
- **BL-002 mock infrastructure** — Phase B.8 (not yet built; Phase B.6
  tests mock everything без needing aiohttp stub)
- **O.7 carve-out** (bot handler `is_test` parity) — Phase B.7
- **E2E / Playwright** — Phase B.9
- **BACKLOG.md** — deferred к BL-107 closure
- **Admin escalation flow for threshold crossings** — counter exists
  in task return value; surfacing this к админ UI is out of scope
  (would need notification template + admin dashboard widget)

## Verification

- `make typecheck`: 0/305 ✓ (was 0/304, +1 module)
- `make lint`: 7 baseline preserved (all 7 in `tests/unit/conftest.py` — BL-024) ✓
- `make format`: clean (applied на этой PR) ✓
- `alembic check`: drift-free ✓ (Phase B.6 не touches schema)
- `pytest tests/unit/test_bl107_periodic_re_verification.py`: 11/11 ✓
- `pytest tests/unit/test_bl107_*.py`: 89/89 ✓ (78 prior + 11 new)

## Decisions echoed

- **Q17 (task module location):** New file `channel_registry_tasks.py`
  rather than appending к `parser_tasks.py`. Empirical: `parser_tasks.py`
  is 1400+ lines and topic-bound (refresh/parsing/classification); a
  ФЗ-303 re-verification task semantically distinct. Clean separation
  also простой for grep / on-call investigation.
- **Q18 (re-check scope):** Only `TRUSTCHANNELBOT_ADMIN` channels
  re-checked. `MANUAL_EVIDENCE` channels excluded by design — admin
  judgement is stable; periodic auto-revocation would undermine the
  manual review workflow. Documented в task docstring.
- **Q19 (audit action string):** `blogger_registry_auto_unverified` —
  free-form string per Phase B.5a convention
  (`blogger_registry_evidence_submitted`, `blogger_registry_verified`,
  `blogger_registry_rejected`). No enum — AuditLog.action is
  `String(64)` free-form.
- **Q20 (verification-lost notification):** New module-level helper
  `notify_owner_verification_lost(session, owner_user_id, channel_id)`
  mirroring Phase B.5a `notify_owner_verification_decided` signature.
  Alternative (a) — extending `notify_owner_verification_decided` with
  `decision="verification_lost"` — rejected: message text and trigger
  context are sufficiently different that a separate helper reads
  cleaner и tests cleaner.
- **Q21 (transient error handling):** `TrustchannelbotResolutionError`
  during periodic check increments `api_failures` but does NOT reset
  verification. Empirical reasoning: a single API failure shouldn't
  punish the channel; the next 24h run will re-check.
- **Q22 (session.commit at task body):** Allowed по S-48 — task is
  top-level caller, not a service. Tests verify `commit` is called
  exactly once at task end (not per-channel) so partial-run mutations
  are reverted on exception.

## What BL-107 Phase B.6 delivers (operational)

After deploy + Beat restart:

- 03:45 UTC daily: task fires
- For each channel ≥ rkn_threshold_subscribers, не is_test, is_active:
  - `member_count` refreshed
  - `last_blogger_registry_check_at` set к now
  - If `TRUSTCHANNELBOT_ADMIN` method и bot выпал → verification reset,
    audit log written, owner gets Telegram notification within seconds
    of task completion
  - If `MANUAL_EVIDENCE` method → no Trustchannelbot probing
- Task returns observability counters (visible в Celery result backend)

Combined с Phase B.4 (channel-add gate) и Phase B.5 (manual evidence
path), BL-107 now has full coverage:

- **Add-time enforcement** (B.4) — channel-add G19 + Trustchannelbot
  check
- **Manual escape hatch** (B.5a/b) — owner submission + admin review
- **Drift detection** (B.6) — daily background re-verification

🔍 Verified against: branch HEAD pre-commit | 📅 Created: 2026-05-14
