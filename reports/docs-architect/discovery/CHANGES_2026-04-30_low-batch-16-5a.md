# CHANGES — 2026-04-30 — LOW batch 16.5a (BL-051 partial)

## Summary

Series 16.x — 16.5a closure. 4 of 6 sub-tasks из BL-051 done. Все
unambiguous fixes из combined 16.5 Шаг 0 inventory (см.
`tmp/16-5_step0_inventory.md`).

Remaining:
- Sub-task 4 (sanitizer/Sentry parity) → 16.5b (option (c): Sentry-only
  merge, log_sanitizer untouched per CLAUDE.md NEVER TOUCH).
- Sub-task 6 (YooKassa webhook over-collection) → 16.5c (after readers
  audit; persist site router-level, not service-level — `Transaction.meta_json`
  already minimal, real over-collection в `YookassaPayment.yookassa_metadata`).

## What changed

### Sub-task 1 — login_code redact

- `src/bot/handlers/shared/login_code.py:50`: `Generated login code
  {code} for telegram_id={telegram_id}` → `Generated login code for
  telegram_id={telegram_id}`. Plaintext one-time code больше не
  логируется. Closes auth-bypass surface через log access.
- Поведение reply пользователю не изменено — код по-прежнему
  отправляется в bot reply (`_CODE_TEMPLATE.format(code=code)`).

### Sub-task 2 — mini_app dead exports

- Deleted `createPayout` в `mini_app/src/api/payouts.ts`.
- Deleted `useCreatePayout` в `mini_app/src/hooks/queries/usePayoutQueries.ts`
  + cleaned now-unused imports (`useMutation`, `useQueryClient`, `useUiStore`).
- `getPayouts` / `usePayouts` retained (used by `OwnPayouts.tsx:29`).
- Loaded-gun pattern matches Phase 1 strip semantics (payout flow lives
  в web_portal, mini_app только redirect).

### Sub-task 3 — dead LegalProfileStates

- Deleted `src/bot/states/legal_profile.py` (15 states, 0 handlers
  verified via grep).
- Removed re-export + `__all__` entry from `src/bot/states/__init__.py`.

### Sub-task 5 — notify_admins_new_feedback delete

- Deleted dead function в `src/bot/handlers/shared/notifications.py`
  (loaded-gun: defined но 0 callers, dangling comment в `feedback.py:53-54`
  references non-existent `tasks/feedback_tasks.py`).
- Removed dangling 2-line comment в `src/api/routers/feedback.py:53-54`
  (logger.info preserved, surrounding session/lookup retained — out of
  scope для этого clean-up).
- Added new test `test_no_dead_notification_functions_revived` в
  `tests/unit/test_no_dead_methods.py` с AST-based module-function
  guard. Prevents re-introduction.

## Inventory note

Шаг 0 inventory из combined 16.5 surface'нула audit framing inaccuracies
(сохранено в `tmp/16-5_step0_inventory.md`):
- Sub-task 4 had 3 lists, not 2. NEVER TOUCH conflict on log_sanitizer.
- Sub-task 5 was dead code, not over-echoing.
- Sub-task 6 persist site был router (`api/routers/billing.py:731`),
  не service (`billing_service.py`); `Transaction.meta_json` уже минимален,
  real over-collection в `YookassaPayment.yookassa_metadata`.
Все 3 split на отдельные follow-up promts (16.5b, 16.5c).

## CI baseline

| Check | Before | After | Delta |
|-------|--------|-------|-------|
| ruff src/ | 21 | 21 | 0 |
| mypy src/ (errors / files checked) | 10 / 275 | 10 / 274 | -1 file (legal_profile.py deleted) |
| tsc --noEmit mini_app | exit 0 | exit 0 | clean |
| pytest test_no_dead_methods.py | 3 passed | 4 passed | +1 (new guard) |

## Not changed

- `src/api/middleware/log_sanitizer.py` (NEVER TOUCH respected).
- `src/api/main.py` Sentry list (16.5b).
- `src/tasks/sentry_init.py` Celery Sentry list (16.5b).
- YooKassa webhook persistence (16.5c).
- Auth flow logic (только log statement).
- `src/api/routers/feedback.py` orchestration block beyond comment removal.

## Files changed

- M `src/bot/handlers/shared/login_code.py` (sub-task 1)
- M `mini_app/src/api/payouts.ts` (sub-task 2)
- M `mini_app/src/hooks/queries/usePayoutQueries.ts` (sub-task 2)
- D `src/bot/states/legal_profile.py` (sub-task 3)
- M `src/bot/states/__init__.py` (sub-task 3)
- M `src/bot/handlers/shared/notifications.py` (sub-task 5)
- M `src/api/routers/feedback.py` (sub-task 5)
- M `tests/unit/test_no_dead_methods.py` (sub-task 5 guard)

## Origins

- BL-051 sub-tasks 1, 2, 3, 5.
- PII audit § O.6, O.7, O.9, O.10.
- Marina decision 2026-04-30: split combined 16.5 → 16.5a/b/c.

🔍 Verified against: `<commit_sha>` (will be filled at commit time)
📅 Updated: 2026-04-30
