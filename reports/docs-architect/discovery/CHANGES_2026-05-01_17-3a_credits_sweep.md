# CHANGES — 17.3a credits sweep gap + production bugs (2026-05-01)

Завершает sweep gap из 17.2 для visible `credits` residue. Закрывает 2
production user-facing bugs где `user.credits` (всегда 0) показывался
вместо `user.balance_rub`.

## Removed

- `User.credits: Mapped[int]` field (`src/db/models/user.py:69`).
- `users.credits` DB column в `0001_initial_schema.py` (pre-prod policy:
  founder admin = 1 user, можно править initial schema directly).
- `UserResponse.credits: int = 0` Pydantic field (`src/api/schemas/user.py`).
- 3 router callsites populating `credits=user.credits` (`auth.py` × 2,
  `users.py` × 1).
- `Badge.credits_reward: Mapped[int]` field (`src/db/models/badge.py:47`)
  + `badges.credits_reward` DB column в `0001_initial_schema.py`.
- 12 `"credits_reward": N` entries в `src/db/seed_badges.py`.
- `if badge.credits_reward > 0: user.balance_rub +=` block в
  `src/core/services/badge_service.py` (был источником бонуса в баланс
  при выдаче значка — внутренний reward, no external API/FE consumers).
- `"credits_reward"` field из dict, возвращаемого
  `BadgeService.check_achievements()` (`badge_service.py:385`).
- `credits_reward` parameter из `notify_badge_earned` Celery task
  (`src/tasks/badge_tasks.py`) + соответствующий `+{N} кр` line из
  notification message body.
- `Decimal` import из `badge_service.py` (became unused).

## Fixed

- `src/tasks/notification_tasks.py:1231` — «Текущий баланс: …» message
  теперь читает `user.balance_rub` вместо `user.credits` (поле всегда
  было 0, пользователи видели заведомо-неверный баланс).
- `src/tasks/billing_tasks.py:138` — plan-extension insufficient-funds
  message теперь читает `user.balance_rub` вместо `user.credits`;
  заголовок изменён с «Недостаточно кредитов» на «Недостаточно средств»
  (currency-honest copy).
- `tests/unit/test_gamification.py` (4 assertion lines, lines 51/57/63/69)
  — assertion key изменён с `result["credits_awarded"]` на
  `result["balance_rub_awarded"]` чтобы соответствовать ключу,
  возвращаемому `xp_service.award_streak_bonus`
  (`src/core/services/xp_service.py:556`). Тест по-прежнему остаётся в
  pre-existing 76-failed списке из-за независимой transaction-isolation
  проблемы (BL-024-style conftest interaction), но key-name drift
  устранён.

## Migration

- `0001_initial_schema.py`: убраны `credits` (users) и `credits_reward`
  (badges) columns. DB пересоздана локально (`DROP / CREATE DATABASE
  market_bot_db` + `alembic upgrade head`); `alembic check` clean.
- `tests/unit/snapshots/user_response.json` — regenerated; диф
  затрагивает только удалённое property `credits`.

## Verify gates (final)

- ruff (`src/ tests/`): **20 errors** — baseline preserved.
- alembic check: **clean** («No new upgrade operations detected»).
- pytest (full `make ci-local`): **76 failed / 780 passed / 6 skipped /
  17 errored** — baseline preserved exactly.

## Deferred to 17.3b/c

- URL path renames (`/billing/credits`, `/admin/credits/*`) — отдельная
  сессия 17.3b.
- FE TS interface renames (`BuyCreditsResponse`, `PlatformCreditResponse`,
  `GamificationBonusResponse`) — 17.3c.
- FE TS `User.credits: number` field cleanup в 5 местах (3 в
  `web_portal/src/lib/`, 2 в `mini_app/src/lib/types.ts`) — 17.3c
  (требует FE rebuild + повторного прогона types).
- Comment / docstring residue («legacy "credits" terminology removed»,
  YooKassa metadata docstring, log messages с «credited» / «Admin credit»)
  — низкий приоритет, в отдельный pass когда rename phases закончатся.

🔍 Verified against: HEAD будет указан после commit | 📅 Updated: 2026-05-01T00:00:00Z
