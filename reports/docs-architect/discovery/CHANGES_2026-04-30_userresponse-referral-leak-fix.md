# CHANGES — 2026-04-30 — UserResponse referral leak fix (16.4)

## Summary

Series 16.x Group D — schema response cleanup. Endpoints возвращающие
referral lists больше не leak'ают `first_name`/`last_name` других
пользователей. Self / admin endpoints остаются без изменений.

Strategy applied: **(a) drop PII fields from response schema** — applied
к фактическому leak surface `ReferralItem` (а не к `UserResponse`,
который используется только в self-context).

Closes BL-050 (MED-6: UserResponse referral leak). PII_AUDIT_2026-04-28
finding line 115.

## Audit findings (Шаг 0 inventory)

### Mini_app payout strip status (Phase 1 invariant verify)

- `mini_app/src/screens/owner/OwnPayoutRequest.tsx` — clean placeholder,
  redirect-only via `OpenInWebPortal target="/own/payouts/request"`. ✅
- `mini_app/src/screens/owner/OwnPayouts.tsx` — read-only list display,
  no PII input.
- `mini_app/src/api/payouts.ts` — `getPayouts` + `createPayout` exported.
  `createPayout` accepts `payment_details` (PII) но **dead code** (no
  caller in any screen/component). Same for hook
  `useCreatePayout` в `usePayoutQueries.ts`. Уже tracked в BL-051
  ("loaded gun unused"), не блокирует 16.4.
- **Verdict:** Phase 1 UI strip complete. Не STOP — dead exports lives в
  BL-051 LOW batch (16.5 scope).

### UserResponse exposure (pre-state)

`src/api/schemas/user.py:13-47` — `UserResponse` includes
`first_name: str`, `last_name: str | None`. **Used by 3 endpoints, all
self-context** (own user data — не leak):

| Endpoint | File:line | Audience | Context |
|----------|-----------|----------|---------|
| `GET /api/users/me` | `users.py:109` | both | self (own data) |
| `POST /api/auth/...` | `auth.py:185` | both | self (login response) |
| `GET /api/auth/me` | `auth.py:414` | both | self (own data) |

Conclusion: `UserResponse` is **not** the leak surface. The PII audit
collapsed `UserResponse.first_name/last_name` and `ReferralItem.first_name`
into one finding; the actual leak vector is the latter.

### Referral surfaces (the actual leak)

`GET /api/users/me/referrals` (`src/api/routers/users.py:257-315`) returns
`ReferralStatsResponse` containing `list[ReferralItem]`. Pre-state schema:

```python
class ReferralItem(BaseModel):
    id: int
    username: str | None = None
    first_name: str       # <-- BL-050: other user's PII
    joined_at: str
    is_active: bool
```

Each item describes another user (the referrer's referral). `first_name`
of OTHER users → ПД leak per ФЗ-152 art. 3 п.1.

### Frontend usage (pre-existing drift)

`web_portal/src/lib/types/misc.ts:22-28` already defined `ReferralItem`
**without** `first_name` (frontend never used the field):

```typescript
export interface ReferralItem {
  id: number
  username: string | null
  telegram_id: number     // <-- never returned by backend (drift)
  is_active: boolean
  created_at: string      // <-- backend returned `joined_at` (drift)
}
```

`web_portal/src/screens/common/Referral.tsx:367` rendered `User #{r.telegram_id}`
fallback — `r.telegram_id` was undefined at runtime (silent drift bug).

## What changed

### Backend

- `src/api/routers/users.py` — `ReferralItem` schema:
  - **Removed** `first_name: str` field (BL-050 leak vector).
  - **Renamed** `joined_at` → `created_at` (align with frontend; frontend
    was already reading `r.created_at`).
  - Constructor call в `get_my_referrals` updated accordingly.
  - `UserResponse` (own-data schema) and `ReferralStatsResponse` shape
    untouched apart from item field rename.

### Frontend

- `web_portal/src/lib/types/misc.ts` — `ReferralItem`:
  - **Removed** `telegram_id: number` (was never returned by backend).
  - Now: `{ id, username, is_active, created_at }`.
- `web_portal/src/screens/common/Referral.tsx` — display fallback:
  - `avatarChar(r.username, r.telegram_id)` → `avatarChar(r.username, r.id)`.
  - `User #{r.telegram_id}` → `User #{r.id}` (anonymous internal id —
    same anonymity property, plus no telegram_id surface).

### Tests

- New: `tests/unit/test_pii_referral_isolation.py` (9 tests):
  - Asserts `first_name`/`last_name` not in `ReferralItem.model_fields`.
  - Asserts dumped JSON of `ReferralStatsResponse.referrals[*]` carries
    no PII keys.
  - Parametrised blacklist guard for `first_name`, `last_name`,
    `telegram_id` to prevent regression.

### Not changed

- `User.first_name`/`last_name` ORM columns — user's own data, остаются.
- Self endpoints (`/api/users/me`, `/api/auth/me`, `/api/auth/login`).
- Admin endpoints (`admin.py:290-291, 637-638, 706-707, 803-804`) —
  separate audit finding (MED, audience pinning), out of BL-050 scope
  (BL-051 territory).
- Auth pinning (16.1), encryption (16.2), bot flow (16.3) — все
  без изменений.
- Database schema, migrations.

## CI baseline

| Check | Before | After |
|-------|--------|-------|
| `poetry run mypy src/` | 10 errors / 5 files | 10 errors / 5 files |
| `poetry run ruff check src/` | 21 errors | 21 errors |
| `poetry run pytest tests/unit/test_contract_schemas.py` | 22 passed | 22 passed |
| `poetry run pytest tests/unit/test_s34_schema_regression.py` | (incl. above) | (incl. above) |
| `poetry run pytest tests/unit/test_pii_referral_isolation.py` | n/a (new file) | 9 passed |
| `npx tsc --noEmit` (web_portal) | exit 0 | exit 0 |

Mypy / ruff baselines не ухудшены. Pre-existing baseline preserved
through `git stash` ⇄ check.

## BL-055 surfaced (deferred)

`BL-055 — Direct bot-to-portal ticket exchange (avoid mini_app
intermediate)` — improvement из 16.3 closure deviation. Не блокирует
launch; 16.3's mini_app intermediate redirect functionally correct.
Pickup: post-series 16.x. См. BACKLOG.

## Origins

- `PII_AUDIT_2026-04-28.md` § 2.2 line 115 (MED-6).
- `BACKLOG.md` BL-050.
- 16.3 closure: `OwnPayoutRequest` placeholder verified pinpoint clean.

🔍 Verified against: <set after commit> | 📅 Updated: 2026-04-30
