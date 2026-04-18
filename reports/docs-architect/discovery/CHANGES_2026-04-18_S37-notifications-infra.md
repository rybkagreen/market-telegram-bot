# S-37 Notification Infrastructure Fixes — Discovery Report

## Summary

Sprint S-37 fixed 4 classes of notification infrastructure problems:

1. **`task_routes` dot/colon mismatch** — `fnmatch("mailing:check_low_balance", "mailing.*")` returns `False`. All 13 route patterns changed from dot-notation (`prefix.*`) to colon-notation (`prefix:*`).
2. **18 per-call `Bot()` instantiations** — Each task created a new `Bot(token=...)` + `aiohttp.ClientSession`, discarded after each send. Replaced with a per-process singleton via `_bot_factory.py`.
3. **12 tasks skipped `notifications_enabled` check** — User-facing tasks dispatched messages without respecting `user.notifications_enabled`. Added `_notify_user_checked()` helper and migrated all user-facing tasks to it.
4. **`yookassa_service` layering violation** — Service layer created `Bot()` directly. Replaced with `notify_payment_success.delay(...)` Celery task dispatch.

---

## Affected Files

### New
- `src/tasks/_bot_factory.py` — Singleton Bot factory; `init_bot()`, `get_bot()`, `close_bot()`
- `tests/tasks/test_bot_factory.py` — 4 unit tests
- `tests/tasks/test_notifications_enabled.py` — 7 unit tests

### Modified
| File | Change |
|------|--------|
| `src/tasks/celery_app.py` | dot→colon in all 13 `task_routes` entries; `worker_process_init/shutdown` lifecycle hooks |
| `src/tasks/notification_tasks.py` | 9 `Bot(token=...)` → `get_bot()`; new `_notify_user_checked()`; `mailing:notify_user` checks `notifications_enabled` |
| `src/tasks/placement_tasks.py` | 4 `Bot()` → `get_bot()`; `_notify_user` helper checks `notifications_enabled` |
| `src/tasks/integrity_tasks.py` | `Bot()` → `get_bot()` in `_notify_admin_failures` |
| `src/tasks/gamification_tasks.py` | `Bot()` → `get_bot()` in `_send_digest_to_user` |
| `src/tasks/billing_tasks.py` | New `notifications:notify_payment_success` Celery task |
| `src/core/services/yookassa_service.py` | `_credit_user`: removed inline `Bot()` + `send_message`; replaced with `notify_payment_success.delay()` |
| `tests/tasks/test_celery_routing.py` | Updated to colon-pattern assertion; removed `S37_KNOWN_ISSUES` exclusion |
| `CLAUDE.md` | Removed S-37 tracked-issue note; added Bot lifecycle and notification helpers sections |
| `QWEN.md` | Same additions as CLAUDE.md |

---

## Business Logic Impact

### Routing (Phase 1)
- `mailing:check_low_balance` and `mailing:notify_user` now route correctly to `mailing` queue on `worker_critical`.
- Previously these landed on the Celery default queue (unassigned), risking unprocessed notifications.

### Bot Lifecycle (Phase 2)
- Each Celery worker process creates exactly one `Bot` instance at startup via `worker_process_init` signal.
- No more per-send TLS handshakes or `ClientSession` leak risk.
- `close_bot()` is called at `worker_process_shutdown` to cleanly close the `aiohttp` session.

### Notification Preference Enforcement (Phase 3)
- All 12 user-facing notification tasks now check `user.notifications_enabled` before sending.
- `_notify_user_checked(user_id, ...)`: DB lookup by `user.id`, returns `False` if disabled, user not found, or `TelegramForbiddenError` (bot blocked).
- Admin/system alerts (`_notify_user_async`) remain unguarded — intentional.

### Yookassa Service Decoupling (Phase 4)
- `core/services/` no longer contains any `Bot()` instantiation.
- Payment success notification is dispatched as `notifications:notify_payment_success` Celery task, keeping the YooKassa webhook handler non-blocking.

---

## New/Changed API Contracts

### `_notify_user_async(telegram_id, message, parse_mode, reply_markup=None) → None`
Low-level send via singleton Bot. No `notifications_enabled` check.

### `_notify_user_checked(user_id, message, parse_mode="HTML", reply_markup=None) → bool`
- Looks up user by internal DB `user.id`
- Returns `False` if: user not found, `notifications_enabled=False`, or `TelegramForbiddenError`
- Returns `True` on successful send

### `notifications:notify_payment_success(user_id, amount_rub, payment_id) → bool`
New Celery task on `notifications` queue. Fetches user, formats payment success message, delegates to `_notify_user_checked`.

---

## Test Coverage

| Test file | Tests | Coverage |
|-----------|-------|---------|
| `tests/tasks/test_bot_factory.py` | 4 | Singleton, idempotent init, close clears, fallback init |
| `tests/tasks/test_notifications_enabled.py` | 7 | Disabled/not-found/enabled/forbidden in `_notify_user_checked`; disabled/not-found in `mailing:notify_user`; disabled in `notify_payment_success` |
| `tests/tasks/test_celery_routing.py` | Updated | Colon-pattern routing, dot-patterns don't match colon names |

All 39 tests pass (`pytest tests/tasks/ -x`).

---

🔍 Verified against: bd9269d81219dea118507386571c951f99ae5efd | 📅 Updated: 2026-04-18T00:00:00Z
