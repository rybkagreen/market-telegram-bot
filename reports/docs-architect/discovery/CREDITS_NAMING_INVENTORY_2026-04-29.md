# Legacy `credits` naming inventory — 2026-04-29

**Type:** Read-only audit (no code changes).
**Origin:** Surfaced after series 15.x closure (15.13.1) — `BillingService.buy_credits_for_plan`
имя противоречит реальному поведению (списывает rubles, не credits) после migration
`credits → balance_rub` (январь-апрель 2026).
**Status:** Inventory complete. Cleanup deferred to series 17.x (after series 16.x PII Hardening).

## 1. Branch state at audit

- main = 57eae84
- develop = d652399

## 2. Sweep summary

| Category | Count | Notes |
|----------|-------|-------|
| (A) Active legacy | 9 distinct items (4 methods/endpoints + 4 model/enum fields + 1 settings pair) | runtime код, имена врут |
| (B) Dead code | 2 (`refund_escrow_credits`, `_credit_user`) | guarded `test_no_dead_methods.py` |
| (C) User-facing remnant | 6 (templates + bot/notification messages + legal docstrings) | client visible |
| (D) Filtered (accidental) | 5 | "автокредит", banking-verb "credited" |
| (E) Comments / docstrings | ~10 | yookassa_service docstrings, billing_service header |
| (F) Test code | ~15 | gamification/billing fixtures, dead-method guards |
| (G) Documentation | 0 actionable | README/CLAUDE clean |

## 3. Category (A) — Active legacy

### Methods / endpoints

| Method | Defined at | Callers | Behavior |
|--------|------------|---------|----------|
| `BillingService.buy_credits_for_plan` | `src/core/services/billing_service.py:72` | 1 (`src/api/routers/billing.py:579`) | Списывает `amount_rub` Decimal с `user.balance_rub`, создаёт `Transaction(type=spend)`. Имя врёт. |
| `BillingService.admin_credit_from_platform` | `src/core/services/billing_service.py:954` | 1 (`src/api/routers/admin.py:855`) | Move funds `PlatformAccount.profit_accumulated → User.balance_rub`. Семантика "credit" — banking-verb (зачисление), **не "credits as currency"**. False positive в (A) — semantically defensible, oставить. |
| `POST /api/billing/credits` | `src/api/routers/billing.py:560,563` | 1 FE (`mini_app/src/api/billing.ts:92`) | Тонкая обёртка над `buy_credits_for_plan`. URL содержит `/credits` — public contract. |
| `POST /api/admin/credits/platform-credit` | `src/api/routers/admin.py:834,840` | 1 FE (`web_portal/src/api/admin.ts:94`) | Admin balance top-up из platform profit. |
| `POST /api/admin/credits/gamification-bonus` | `src/api/routers/admin.py:890` | 1 FE (`web_portal/src/api/admin.ts:108`) | Admin gamification reward. |

### Model / enum fields

| Field | Defined at | Read sites | Notes |
|-------|------------|------------|-------|
| `User.credits: int` | `src/db/models/user.py:69` | 7: `auth.py:195,424`, `users.py:133`, `user.py schema:25`, `notification_tasks.py:1229` (UI), `billing_tasks.py:138` (UI), `0001_initial_schema.py:54` | DB column. Public contract в `auth/me`, `users/me`. **Surprise:** двойная валюта в schema — `User.credits` AND `User.balance_rub` оба exist. |
| `Badge.credits_reward: int` | `src/db/models/badge.py:47` | 5+: `seed_badges.py` (12 occ), `badge_service.py:193,194,385`, `badge_tasks.py:46,194,219,229,244,245`, `0001_initial_schema.py:109` | DB column. Bot UI string `+{credits_reward} кр\n` в `badge_tasks.py:245`. |
| `TransactionType.credits_buy` | `src/db/models/transaction.py:34` | 4: enum def, `0001_initial_schema.py:891`, `billing.py:487`, `bot/handlers/billing/billing.py:275` | Persisted enum value в DB. Audit log filter list. |
| `TransactionType.admin_credit` | `src/db/models/transaction.py:45` | 3: enum def, `0001_initial_schema.py:899`, `billing_service.py:999`, `analytics.py:251` | Persisted enum value в DB. Banking-verb (как `admin_credit_from_platform`). |

### Settings (likely dead)

| Setting | Defined | Callers |
|---------|---------|---------|
| `bonus_credits_standard` (env `BONUS_CREDITS_STANDARD`, default 100) | `src/config/settings.py:248` | 0 in src/, 0 in tests/ |
| `bonus_credits_business` (env `BONUS_CREDITS_BUSINESS`, default 500) | `src/config/settings.py:249` | 0 in src/, 0 in tests/ |

## 4. Category (B) — Dead code

| Item | Where referenced | Verified zero callers | Notes |
|------|------------------|----------------------|-------|
| `refund_escrow_credits` | `tests/unit/test_no_dead_methods.py:27` | grep src/ → empty | Method removed; test enforces absence. |
| `_credit_user` | `tests/unit/test_no_dead_methods.py:34,74`; comment в `src/tasks/billing_tasks.py:159` ("Dispatched by yookassa_service._credit_user") | grep `def _credit_user` src/ → empty | Method removed; **stale doc reference в `billing_tasks.py:159`**. |

## 5. Category (C) — User-facing remnants

| Location | Truncated string | Visibility | Notes |
|----------|------------------|------------|-------|
| `src/templates/contracts/platform_rules.html:90` | "Валюта расчётов — кредиты (1 кредит = 1 ₽). Пополнение — через YooKassa..." | Legal contract (rendered to PDF / shown during onboarding) | **Customer-visible legal text lies.** Touch требует version bump 1.1 → 1.2 + re-acceptance loop (15.9 infra). |
| `src/constants/legal.py:3` | docstring "Обновлено для двухвалютной системы: рубли + кредиты." | comment | Stale. |
| `src/constants/legal.py:24` | "Покупаются за рубли с баланса по курсу 1 кредит = 1 ₽" | Legal text (likely embedded в contract templates) | Customer-facing. |
| `src/constants/legal.py:91` | `<b>Кредиты</b> — для покупки тарифных подписок (1 кредит = 1 ₽)` | Legal text HTML snippet | Customer-facing. |
| `src/tasks/notification_tasks.py:1229` | `f"Текущий баланс: {user.credits} ₽\n\n"` | Telegram bot message | User видит. Поле `credits` рендерится как ₽ post-migration, но имя поля врёт. |
| `src/tasks/billing_tasks.py:138` | `f"Недостаточно кредитов для продления (нужно {plan_cost}, было {user.credits}).\n\n"` | Telegram bot message (plan auto-renewal failure) | User видит. |
| `src/tasks/gamification_tasks.py:205` | `f"+50 кредитов на баланс!\n\n"` | Telegram bot message (gamification reward) | User видит. |
| `src/tasks/badge_tasks.py:245` | `f"+{credits_reward} кр\n"` | Telegram bot message (badge unlock) | User видит. Сокращение "кр" = "кредитов". |

## 6. Category (D) — Filtered out (5 matches skipped)

- `src/tasks/parser_tasks.py:172` — "автокредит" (parser keyword for car-loan posts).
- `src/utils/telegram/topic_classifier.py:205` — "кредит" (topic classifier keyword for finance/loans).
- `src/api/routers/billing.py:683` — comment "идемпотентность + credit balance делает..." (English verb usage).
- `src/api/routers/admin.py:871` — log `f"Admin #{admin_user.id} credited {body.amount} ₽..."` (verb usage).
- `src/core/services/billing_service.py:179,191,1017` — log messages with verb "credited".

**Borderline:** `meta["credited"]` and `meta["rub_credited"]` keys в `process_topup_webhook` — persisted в `Transaction.meta_json` (DB-stored). Surface'нуто как category (E), но arguably (A).

## 7. Category (E/F/G) — Compact lists

### (E) Comments / docstrings

- `src/core/services/yookassa_service.py:117` — docstring `"credits (= int(desired_balance)), status="pending"."`
- `src/core/services/yookassa_service.py:135` — comment `# 2. Compute amounts (1:1 credits — legacy field)`.
- `src/core/services/yookassa_service.py:136` — local var `credits_amount = int(desired_balance)`.
- `src/core/services/yookassa_service.py:236,252` — payload dict `"credits": credits_amount` (returned to caller — borderline contract).
- `src/core/services/billing_service.py:3` — module docstring "Двухвалютная система: рубли (размещения) + кредиты (подписки)" (stale).
- `src/core/services/billing_service.py:63` — class docstring entry "buy_credits_for_plan: Купить кредиты для тарифа (с balance_rub → credits)" (self-contradictory).
- `src/core/services/billing_service.py:166-191` — `meta["credited"]`, `meta["rub_credited"]` keys (persisted в `Transaction.meta_json` — DB-stored, borderline (A) field).
- `src/db/models/transaction.py:44` — comment `# Admin credits and gamification`.
- `src/api/routers/billing.py:683,737` — comments referencing legacy credit semantics.
- `src/config/settings.py:212` — comment `# Стоимость тарифов в кредитах (v4.2)`.

### (F) Test code

- `tests/integration/test_billing_hotfix_bundle.py:84,154,164,194,202,231` — verb usage "credited" + payload string "manual credit for support".
- `tests/integration/test_payout_concurrent.py:258` — comment "Owner's earned_rub credited exactly...".
- `tests/integration/test_bot_topup_handler.py:78` — fixture dict `"credits": 100`.
- `tests/unit/test_no_dead_methods.py:27,34,74` — guard test (already covered in (B)).
- `tests/unit/test_gamification.py:32,96,102,108,114` — `credits_reward = 50` + assertion keys `credits_awarded`.
- `tests/integration/test_yookassa_create_topup_payment.py:89,188` — `result["credits"] == 100` assertions (validate yookassa_service payload contract).

### (G) Documentation

- `README.md`, `CLAUDE.md`, `docs/` — clean (grep returned 0 hits).

## 8. Frontend findings

### mini_app

- `mini_app/src/api/billing.ts:92` — `api.post('billing/credits', ...)` call to `/api/billing/credits` endpoint (FE function name `BuyCreditsResponse`).
- `mini_app/src/lib/types.ts:65,417` — `credits: number` field в типах User / адресатных responses.

### web_portal

- `web_portal/src/api/admin.ts:94,108` — `admin/credits/platform-credit` and `admin/credits/gamification-bonus` POST URLs.
- `web_portal/src/lib/types.ts:23` — `credits: number` field.
- `web_portal/src/lib/types/user.ts:13,44` — `credits: number` field.
- `web_portal/src/screens/admin/AdminUserDetail.tsx:34-278` — local React state `creditAmount`, `creditComment`, `creditFeedback` + 9 references throughout the screen (admin top-up form UI).

## 9. DB schema findings

`src/db/migrations/versions/0001_initial_schema.py` (pre-prod policy: editable until first user):
- Line 54: `users.credits` Integer column (default 0, NOT NULL).
- Line 109: `badges.credits_reward` Integer column (default 0, NOT NULL).
- Line 891: `TransactionType` enum value `"credits_buy"`.
- Line 899: `TransactionType` enum value `"admin_credit"`.

ORM models confirm:
- `User.credits: Mapped[int]` (`src/db/models/user.py:69`).
- `Badge.credits_reward: Mapped[int]` (`src/db/models/badge.py:47`).
- `TransactionType.credits_buy = "credits_buy"` (`src/db/models/transaction.py:34`).
- `TransactionType.admin_credit = "admin_credit"` (`src/db/models/transaction.py:45`).

Pre-prod policy in CLAUDE.md: schema editable directly in `0001_initial_schema.py` until first production user. Currently still pre-prod.

## 10. API path findings

Public URL paths containing `/credits`:
- `POST /api/billing/credits` — buy plan with balance.
- `POST /api/admin/credits/platform-credit` — admin top-up из platform profit.
- `POST /api/admin/credits/gamification-bonus` — admin gamification reward.

Public response payload fields containing `credits`:
- `auth/me`, `users/me`, `register` response → `credits: int` (User schema).
- `yookassa_service.create_topup_payment` returns dict with `"credits": int` key (callers checked в test fixture `result["credits"] == 100`).

## 11. Precision-loss observation (extra context)

**`BillingService.buy_credits_for_plan`** (lines 72-132):
- Signature: `(user_id: int, amount_rub: Decimal) -> tuple[int, Transaction, Transaction]`.
- Return statement (line 132): `return int(amount_rub), transaction, transaction`.
- Docstring (line 87): explicitly notes `(amount_int, transaction, transaction)` — "дубли для обратной совместимости" — duplication acknowledged legacy.
- Cast points:
  - `int(amount_rub)` at return — precision-lossy для `Decimal("100.50")` → 100.
  - Inside method: `user.balance_rub -= amount_rub` (Decimal — no loss).
  - `Transaction(amount=amount_rub, ...)` (Decimal — no loss).
  - `description = f"Оплата тарифа: {amount_rub} ₽"` (str repr — no loss).
- Other precision-loss spots в method: none beyond return cast.
- **Caller behavior (post-15.13.1):** `await billing_service.buy_credits_for_plan(...)` — return value discarded entirely. Lossy `int` never observed by anyone. Зомби-cast.

**`BillingService.admin_credit_from_platform`** (lines 954-1019):
- Signature: returns `Transaction` (no tuple, no int cast).
- All arithmetic Decimal. No precision loss observed.

**`yookassa_service.py:136`:**
- `credits_amount = int(desired_balance)` — другой int cast в codebase. Decimal → int conversion, потенциальный precision-loss point.
- Used in transaction record creation and в return payload. Audit was surface-level — full impact assessment скоупом этого inventory не покрыт.

## 12. Surprises

1. **Двойная валюта в DB schema:** `User.credits` AND `User.balance_rub` оба exist. `User.balance_rub` is the live currency post-migration; `User.credits` ещё в ORM model и schema, читается в API responses (`auth/me`, `users/me`) and в bot UI strings (`"Текущий баланс: {user.credits} ₽"`). **Не verified** writes vs read-only — нужен отдельный sub-audit при rename.
2. **`yookassa_service` payload field `"credits"`:** returned in dict from `create_topup_payment`. Test fixture asserts `result["credits"] == 100`. Это contract между `yookassa_service` and callers — renaming требует касания assertion + caller dict access (router billing.py).
3. **`bonus_credits_standard` / `bonus_credits_business` settings:** 0 callers found in src/ или tests/. Likely dead settings; нужно confirm что env vars unused в deploy configs (не part of grep scope).
4. **`platform_rules.html:90` legal text:** contract template still uses "кредиты" terminology. Если contract rendered with current `CONTRACT_TEMPLATE_VERSION = "1.1"` from 15.8, customers see this. Touching legal text → version bump → re-acceptance loop fire (per 15.9 infrastructure).
5. **Comment в `billing_tasks.py:159`** references `_credit_user` method that doesn't exist. Stale doc reference.
6. **Inconsistent verb vs noun usage:** `admin_credit_from_platform` semantics is verb "credit" (banking — зачислять funds) — **not stale**. The name врёт only if read as "credits as currency". This is ambiguous categorisation in (A); included but flagged as semantically defensible.

## 13. Scope assessment

**Total touchable points:** ~70+ distinct sites across `src/`, `tests/`, `mini_app/`, `web_portal/`, `templates/`, schema.

By proposed bundling for series 17.x:

### 17.1 — Backend cleanup (small, low risk)

- Rename `BillingService.buy_credits_for_plan` → e.g. `charge_balance_for_plan` (1 def + 1 caller).
- Remove `bonus_credits_standard` / `bonus_credits_business` settings (verified dead).
- Remove precision-loss `int(amount_rub)` cast from return (zombie cast — caller discards).
- Remove stale `_credit_user` comment в `billing_tasks.py:159`.
- Update module docstrings + class docstrings (`billing_service.py:3,63`, `yookassa_service.py:117,135`).

### 17.2 — DB schema + ORM + Pydantic + frontend types (medium, cross-stack)

- `User.credits` → audit (read vs write) → likely remove column or alias к `balance_rub`.
- `Badge.credits_reward` → `Badge.reward_rub` или similar.
- `TransactionType.credits_buy` → `plan_purchase` or similar.
- `TransactionType.admin_credit` — оставить (banking-verb).
- ORM models, Pydantic schemas, response schemas, frontend types (`mini_app + web_portal`).
- `yookassa_service` payload key `"credits"` → e.g. `"amount_int"` + test fixture updates.

### 17.3 — API path renames (medium, breaking)

- `/api/billing/credits` → `/api/billing/plans/buy` (or similar).
- `/api/admin/credits/platform-credit` → `/api/admin/balance/platform-credit`.
- `/api/admin/credits/gamification-bonus` → similar.
- Coordinated FE deploy (atomic).

### 17.4 — Legal templates + UI strings (medium, customer-facing)

- `platform_rules.html` rewrite "кредиты" → "рубли" + version bump 1.1 → 1.2.
- `src/constants/legal.py:3,24,91` — legal text + docstring.
- `notification_tasks.py:1229`, `billing_tasks.py:138`, `gamification_tasks.py:205`, `badge_tasks.py:245` — bot UI strings.
- Re-acceptance loop fire (15.9 infrastructure).

**Note on 17.4:** legal template `platform_rules.html` имеет отдельный приоритет — fix мини-промтом до серии 17.x (separate scope, version bump 1.1 → 1.2, fired re-acceptance).

## 14. Open questions для серии 17.x kickoff

1. `User.credits` column dual-currency: read-only vestigial or still being written? Audit needed.
2. `admin_credit_from_platform` — оставить (banking-verb)? Recommend yes per inventory.
3. `/api/billing/credits` URL rename strategy: atomic FE/BE deploy or compat shim period?
4. Admin endpoint URL renames — acceptable to break без compat?
5. `platform_rules.html` legal text rewrite — separate mini-promt before 17.x (recommended) or bundle с 17.4?
6. `bonus_credits_*` settings — verify unused в deploy configs before deletion.
7. `_credit_user` stale comment — bundle с 17.1 (recommended).
8. `yookassa_service` payload `"credits"` key — rename strategy (affects 2 test assertions + caller).
9. `Badge.credits_reward` — bundle с `User.credits` (17.2) или standalone?
10. `TransactionType.credits_buy` / `admin_credit` enum values — pre-prod safe to rename, but affects analytics filter strings.

---

**End of inventory. Cleanup deferred to series 17.x. Tracked as BL-053.**
