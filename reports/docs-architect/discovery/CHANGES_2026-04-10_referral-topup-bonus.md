# CHANGES_2026-04-10_referral-topup-bonus

**Date:** 2026-04-10T09:33:00Z
**Author:** Qwen Code (backend-core)
**Commit:** f423788
**Type:** feat (referral program — first topup bonus)

---

## Summary

Implemented one-time referral bonus payout when a referred user makes their first topup.
The referrer receives 10% of the topup amount, credited to their `balance_rub`.

---

## Files Changed

| File | Change |
|------|--------|
| `src/constants/payments.py` | Added `REFERRAL_MIN_QUALIFYING_TOPUP = Decimal("500")`, `REFERRAL_BONUS_PERCENT = Decimal("0.10")` |
| `src/db/repositories/user_repo.py` | Added `get_by_referral_code(referral_code: str) -> User \| None` method |
| `src/bot/handlers/shared/start.py` | Parse `REF_` prefix from deep link args; set `user.referred_by_id` for new users |
| `src/core/services/billing_service.py` | Added `process_referral_topup_bonus()` method; called from `process_topup_webhook()` |

---

## Business Logic

### Flow
```
/start REF_123456 → new user → referred_by_id = referrer.id
              ↓
User tops up via YooKassa → process_topup_webhook()
              ↓
  process_referral_topup_bonus():
    1. user.referred_by_id IS NOT NULL?
    2. No existing bonus with meta_json.referral_user_id == user.id?
    3. topup_amount >= 500?
    4. bonus = topup_amount * 0.10
    5. referrer.balance_rub += bonus
    6. Transaction(type=bonus, meta_json={type: referral_topup_bonus, ...})
```

### Idempotency
Checked via `Transaction` table: `meta_json->>'referral_user_id' = '{user_id}'` AND `type = 'bonus'`.
Second and subsequent topups do NOT trigger bonus.

### Constants
- `REFERRAL_MIN_QUALIFYING_TOPUP = 500` (reuses `MIN_TOPUP`)
- `REFERRAL_BONUS_PERCENT = 0.10` (10%)

---

## DB Contract Changes

**No migration needed.** Uses existing columns:
- `users.referred_by_id` (already exists, was never populated — now it is)
- `users.referral_code` (already exists)
- `transactions.meta_json` (JSONB, already exists)

---

## API / Handler Changes

- `/start` handler now parses `REF_<referrer_code>` deep link format
- Example: `https://t.me/RekHarborBot?start=REF_ref_123456789`

---

## Impact Analysis

| Area | Impact |
|------|--------|
| Existing referrals | None — `referred_by_id` was always NULL, now populated for new users |
| Existing topups | None — bonus only applies to new webhooks after deploy |
| Balance calculations | Referrer `balance_rub` increases by 10% of referred user's first topup |
| Transaction history | New `bonus` type transactions with `meta_json.type = "referral_topup_bonus"` |

---

## Testing Notes

Manual test scenarios:
1. New user clicks `/start REF_ref_123` → `referred_by_id` should be set
2. Referred user tops up 1000 ₽ → referrer gets 100 ₽ bonus
3. Same user tops up again → NO bonus (idempotent)
4. Topup < 500 → NO bonus
5. User without referrer → NO bonus

---

🔍 Verified against: f423788 | 📅 Updated: 2026-04-10T09:33:00Z
