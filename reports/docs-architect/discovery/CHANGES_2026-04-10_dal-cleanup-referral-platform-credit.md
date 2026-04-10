# Discovery: DAL Cleanup + Referral + Platform Credit + Security Hardening

> **Date:** 2026-04-10  
> **Feature:** S-29-dal-cleanup  
> **Parent:** feature/S-27-web-portal branch  

---

## Summary

Comprehensive cleanup of Data Access Layer boundaries, wiring 43 `session.execute()` calls in handlers/routers to existing repositories, fixing 31 mypy errors, 7 bandit warnings, and implementing 2 new features (admin platform credit + referral topup bonus).

---

## Changes by Category

### 1. Dead Code Removal (P0)
- **Deleted 6 dead repository files:** `badge_repo.py`, `campaign_repo.py`, `click_tracking_repo.py`, `mailing_log_repo.py`, `platform_revenue_repo.py`, `yookassa_payment_repo.py`
- **Cleaned `src/db/repositories/__init__.py`:** removed 6 imports + 6 `__all__` entries
- **Impact:** 23 mypy errors eliminated (repo methods referenced non-existent model fields)
- **Rationale:** Zero callers in `src/`, `mini_app/`, `web_portal/`, `tests/`

### 2. New Repositories Created (P1–P2)
| Repository | Methods | Consumers |
|-----------|---------|-----------|
| `ReputationHistoryRepository` | `get_by_user_id()`, `add_batch()` | `reputation.py` admin endpoint |
| `ChannelMediakitRepo` | `get_by_channel_id()`, `update_metrics()` | `mediakit_service.py` |
| `YookassaPaymentRepository` (re-created) | `get_by_payment_id()` | `billing.py` webhook |

### 3. Repository Method Additions
| Repo | New Method | Consumer |
|------|-----------|----------|
| `UserRepository` | `count_referrals()`, `get_referrals()`, `count_active_referrals()`, `sum_referral_earnings()`, `has_successful_payment()` | `users.py` referrals, `cabinet.py` |
| `TransactionRepository` | `sum_by_user_and_type()`, `list_by_user_id()` | `channel_owner.py`, `billing.py` |
| `PlacementRequestRepository` | `has_active_placements()`, `count_published_by_channel()` | `channel_owner.py` |
| `TelegramChatRepository` | `count_active_by_owner()` | `channel_owner.py` |
| `DisputeRepository` | `get_all_paginated()` | `disputes.py` admin |
| `FeedbackRepository` | `get_by_id_with_user()`, `list_all_paginated()`, `respond()`, `update_status_only()` | `feedback.py` admin |

### 4. Handler/Router → Repository Wiring (28 calls replaced)
| File | Before | After |
|------|--------|-------|
| `dispute.py` (handler) | 2× `session.execute(select(User))` | `UserRepository.get_all_admins()` |
| `contract_signing.py` | 1× `session.execute(select(Contract))` | `ContractRepo.get_by_id()` |
| `channel_owner.py` | 3× `session.execute()` | Repo methods |
| `cabinet.py` | 1× `session.execute()` | `UserRepository.count_referrals()` |
| `users.py` | 5× `session.execute()` | `UserRepository` methods |
| `billing.py` | 3× `session.execute()` | `TransactionRepository`, `YookassaPaymentRepository` |
| `acts.py` | 2× `session.execute()` | `ActRepository.get_by_id()` |
| `ord.py` | 1× `session.execute()` | `PlacementRequestRepository.get_by_id()` |
| `feedback.py` | 4× `session.execute()` | `FeedbackRepository` methods |
| `disputes.py` (router) | 2× `session.execute()` | `DisputeRepository.get_all_paginated()` |
| `document_validation.py` | 3× `session.execute()` | `DocumentUploadRepository` methods |

### 5. New Feature: Admin Platform Credit (п.3)
- **`TransactionType` enum:** added `admin_credit`, `gamification_bonus`
- **`BillingService`:** `admin_credit_from_platform()`, `admin_gamification_bonus()`
- **Admin API:** `POST /api/admin/credits/platform-credit`, `POST /api/admin/credits/gamification-bonus`
- **Logic:** deducts from `PlatformAccount.profit_accumulated` → credits to `user.balance_rub`

### 6. New Feature: Referral Topup Bonus (п.4)
- **Constants:** `REFERRAL_MIN_QUALIFYING_TOPUP = 500`, `REFERRAL_BONUS_PERCENT = 10%`
- **`/start` handler:** parses `REF_<code>` deep link, sets `user.referred_by_id` for new users
- **`billing_service.py`:** `process_referral_topup_bonus()` — one-time 10% bonus to referrer on first qualifying topup
- **Idempotency:** checked via `Transaction.meta_json->>'referral_user_id'`

### 7. Security Hardening
| File | Issue | Fix |
|------|-------|-----|
| `login_code.py` | B311 `random.randint` for auth codes | `secrets.randbelow()` |
| `billing.py` | B104 `0.0.0.0` bind | Empty string + explicit IP validation |
| `billing_service.py` | B101 `assert` for type guards | Proper `User \| None` annotations |
| `monitoring.py` | `InaccessibleMessage.edit_reply_markup` crash | `isinstance(Message)` guards |

### 8. Bot Singleton Fix
- **`src/bot/main.py`:** added module-level `bot: Bot \| None = None` + `_create_bot()` helper
- **`src/api/dependencies.py`:** `get_bot()` singleton pattern + `close_bot()` shutdown
- **8 mypy errors fixed** across `notifications.py` and `placement_request_service.py`

---

## Static Analysis Results

| Tool | Before | After |
|------|--------|-------|
| `ruff check src/` | 3 errors | **0 errors** |
| `mypy src/` | **31 errors** | **0 errors** |
| `bandit -r src/` | 7 findings | **0 issues identified** |

---

## Files Modified: 49 (46 modified + 3 new)
## Lines Changed: +1066 / -401

🔍 Verified against: `6f7cfba` | 📅 Updated: 2026-04-10T11:30:00Z
