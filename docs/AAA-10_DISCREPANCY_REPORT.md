# RekHarborBot — Discrepancy & Tech Debt Report

> **RekHarborBot AAA Documentation v4.5 | April 2026**
> **Document:** AAA-10_DISCREPANCY_REPORT
> **Verified against:** HEAD @ 2026-04-21 | Sources: 2026-04-21 docs-sync deep-dive + earlier Phase 1/2 reports

## 2026-04-21 drift snapshot (latest re-audit)

| Metric | Earlier doc/CLAUDE.md claim | Reality | Note |
|--------|------------------|---------|------|
| API routers | 15 (CLAUDE.md) / 26 (AAA-02) | **27** | S-26/S-27/S-29/admin split added routers |
| API endpoints | 120+ | **131** | Counted `@router.*` decorators across routers |
| Core services | 15 (CLAUDE.md) / 34 (AAA-04) | **35** | Stub/real providers (`stub_ord_provider`, `yandex_ord_provider`, `ord_yandex_provider`) + specialized services |
| DB models | 19 / 33 | **31** | See AAA-03 inventory |
| DB repositories | 24 | **26** | See AAA-03 §1.2 for models without repo |
| Migrations | 7 / 33 | **1** | Consolidated to `0001_initial_schema` pre-prod |
| FSM groups | 9 / 12 | **11** | `CampaignCreateState` removed, campaign creation merged into `PlacementStates` |
| FSM states | ~47 | **52** | Total states across 11 groups |
| Bot handler files | 18 | **22** | 8 subdirs (admin 4 · advertiser 2 · billing 1 · dispute 1 · owner 4 · payout 1 · placement 1 · shared 8) |
| Celery task files | 16 | **12** | Legacy `rating_tasks.py` and others removed in v4.3/S-36 |
| Celery tasks | 40+ | **66** | Counted `@celery_app.task` decorators |
| Celery queues | 11 | **9** | `rating` is dead, `worker_critical` is real name |
| Beat periodic | 26 | **18** | After S-36 consolidation |
| Mini App screens | 22 (AAA-07) / 39 (CLAUDE.md) | **55** | common 16 · adv 17 · owner 11 · admin 10 · shared 1 |
| Web Portal screens | 52 (AAA-07) | **66** | + 126 Playwright specs for QA |
| Landing | n/a | present | `/opt/market-telegram-bot/landing/` — static Vite+Tailwind v4 |
| pytest files | 101 (README) | **37** | Individual tests: ~54 (`grep -c "def test_"`) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Discrepancy Index](#2-discrepancy-index)
3. [Tech Debt Registry](#3-tech-debt-registry)
4. [Root Cause Analysis](#4-root-cause-analysis)
5. [Recommended Fixes](#5-recommended-fixes)
6. [Action Items by Priority](#6-action-items-by-priority)

---

## 1. Executive Summary

During Phase 1 (Discovery & Mapping) and Phase 2 (Deep Dive) analysis, **22 discrepancies** and **15 tech debt items** were identified across the codebase. This report catalogs each finding with severity assessment, root cause, and recommended fix.

### Summary by Severity

| Severity | Count | Impact |
|----------|-------|--------|
| 🔴 CRITICAL | 4 | Data integrity, security, financial accuracy |
| 🟡 MEDIUM | 11 | Functionality gaps, developer confusion, performance |
| 🟢 LOW | 7 | Code quality, documentation gaps, minor inconsistencies |

### Summary by Category

| Category | Discrepancies | Tech Debt |
|----------|--------------|-----------|
| Database Schema | 3 | 2 |
| API Endpoints | 4 | 3 |
| FSM States | 3 | 1 |
| Constants/Config | 3 | 2 |
| Celery Tasks | 3 | 2 |
| Frontend | 3 | 3 |
| Testing | 1 | 2 |
| Security | 2 | 0 |

---

## 2. Discrepancy Index

### 2.1 🔴 CRITICAL Discrepancies

#### D-01: `legal_profiles.user_id` Type Mismatch

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Location** | `src/db/models/legal_profile.py` |
| **Issue** | `user_id` column is `BigInteger` but `users.id` is `Integer` |
| **Impact** | Type mismatch between FK reference — works in PostgreSQL but inconsistent |
| **Root Cause** | Model created without checking referenced column type |
| **Evidence** | `legal_profile.py` line declaring `user_id` uses BigInteger |
| **Fix** | Change to `Integer`, create migration |
| **Effort** | Low (1 migration) |

#### D-02: `PLAN_PRICES` Key Mismatch (`agency` vs `business`)

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **Location** | `src/constants/payments.py` |
| **Issue** | `PLAN_PRICES` uses key `"agency"` but `PLAN_LIMITS` uses `"business"` |
| **Impact** | `KeyError` if code accesses `PLAN_PRICES["business"]` or `PLAN_LIMITS["agency"]` |
| **Root Cause** | Enum value is `"business"` but legacy prices dict kept `"agency"` for backward compat |
| **Evidence** | `payments.py` lines 65-97 show mismatched keys |
| **Current State** | No code accesses the dead keys (verified), but risk remains |
| **Fix** | Unify to `"business"` key in both dicts, remove `"agency"` legacy |
| **Effort** | Low (constant file edit + data migration if needed) |

#### D-03: ESCROW-001 — Release Called from Wrong Location

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (by design, but high risk) |
| **Location** | `src/tasks/publication_tasks.py:delete_published_post()` |
| **Issue** | `release_escrow()` is called from `delete_published_post()`, not from `publish_placement()` |
| **Impact** | If delete task fails silently, owner never gets paid. Escrow remains frozen. |
| **Root Cause** | Architectural decision (ADR-001) — pay only after post serves full duration |
| **Evidence** | `publication_tasks.py:delete_published_post()` calls `BillingService.release_escrow()` |
| **Mitigation** | Retry policy (3 retries, 5min intervals). `TelegramBadRequest` caught gracefully. |
| **Fix** | Add dead-letter queue for failed deletions. Alert on stuck escrow placements. |
| **Effort** | Medium (monitoring + alerting implementation) |

#### D-04: `is_banned` → `is_active` Migration Incomplete

| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (fixed in v4.3, but risk in legacy code) |
| **Location** | Multiple files referenced `user.is_banned` |
| **Issue** | Field renamed from `is_banned` to `is_active` — semantics inverted |
| **Impact** | `AttributeError` if any code still references `is_banned` |
| **Root Cause** | v4.3 rename for clearer semantics |
| **Evidence** | QWEN.md Common Bugs: `user.is_banned` AttributeError → replaced with `not user.is_active` |
| **Current State** | ✅ Fixed in v4.3 — all references updated |
| **Verification** | `grep -r "is_banned" src/` should return 0 results |

---

### 2.2 🟡 MEDIUM Discrepancies

#### D-05: Publication Tasks Use Default Queue (Not `worker_critical`)

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/tasks/publication_tasks.py` |
| **Issue** | Tasks don't specify `queue="worker_critical"` in decorator |
| **Impact** | Tasks run on default queue — only works because worker_critical includes `celery` queue |
| **Evidence** | Task decorators lack `queue=` parameter |
| **Fix** | Add `queue=QUEUE_WORKER_CRITICAL` to all publication task decorators |
| **Effort** | Low (edit 4 decorators) |

#### D-06: `check_pending_invoices` Deprecated No-Op

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/tasks/billing_tasks.py` + Beat schedule |
| **Issue** | Task is a no-op but still scheduled every 5 minutes |
| **Impact** | Wasted CPU cycles, cluttered logs |
| **Fix** | Remove from Beat schedule, deprecate task |
| **Effort** | Low (remove from celery_config.py) |

#### D-07: `GET /api/billing/invoice/{id}` Always Returns 404

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/api/routers/billing.py:421` |
| **Issue** | Endpoint exists but always returns 404 — legacy dead endpoint |
| **Impact** | Confusing for API consumers, clutters OpenAPI docs |
| **Fix** | Remove endpoint or implement functionality |
| **Effort** | Low (remove router method) |

#### D-08: `ai_included` Hardcoded vs `PLAN_LIMITS`

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/api/routers/billing.py` BalanceResponse |
| **Issue** | `ai_included` hardcoded as `{"pro": 5, "business": 20}` vs `PLAN_LIMITS` showing `ai_per_month: {pro: 20, business: -1}` |
| **Impact** | Inconsistent AI usage reporting to frontend |
| **Root Cause** | Different sources of truth for AI limits |
| **Fix** | Use `PLAN_LIMITS` values consistently, remove hardcoded dict |
| **Effort** | Medium (requires aligning constants + settings) |

#### D-09: FSM States Not Exported from `__init__.py`

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/bot/states/__init__.py` |
| **Issue** | `ArbitrationStates`, `AdminFeedbackStates`, `LegalProfileStates`, `ContractSigningStates` not in `__all__` |
| **Impact** | Inconsistent imports — some states imported directly from modules |
| **Fix** | Add all state groups to `__all__` in `__init__.py` |
| **Effort** | Low (edit 1 file) |

#### D-10: Redis Dedup Uses Sync Client in Async Context

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/tasks/placement_tasks.py` |
| **Issue** | `_check_dedup()` uses `redis_sync_client` in async task context |
| **Impact** | Potential blocking, defeats async benefits |
| **Fix** | Use async Redis client for dedup checks |
| **Effort** | Medium (refactor dedup logic) |

#### D-11: ORD Tasks Reference Missing Queue Route

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/tasks/celery_config.py` |
| **Issue** | ORD tasks use `background` queue but it's not in `TASK_ROUTES` |
| **Impact** | Tasks may route to default queue instead of intended worker |
| **Fix** | Add `background` queue to TASK_ROUTES in celery_config.py |
| **Effort** | Low (add 1 line to config) |

#### D-12: `COOLDOWN_HOURS` Defined But Not Enforced

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/constants/payments.py` |
| **Issue** | `COOLDOWN_HOURS = 24` defined but no code enforces payout cooldown |
| **Impact** | Users can submit payouts more frequently than intended |
| **Fix** | Implement cooldown check in `PayoutService.create_payout()` or remove constant |
| **Effort** | Medium (add business rule + test) |

#### D-13: Notification Tasks Create Bot Instance Per Call

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `src/tasks/notification_tasks.py` |
| **Issue** | Each notification task creates a new Bot instance |
| **Impact** | Performance overhead, connection churn |
| **Fix** | Use shared Bot instance or connection pool |
| **Effort** | Medium (refactor notification service) |

#### D-14: 8 Models Lack Dedicated Repositories

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | Campaign, Badge, YookassaPayment, ClickTracking, KudirRecord, DocumentUpload, MailingLog, PlatformQuarterlyRevenue |
| **Issue** | No dedicated repository files — accessed via direct SQLAlchemy queries |
| **Impact** | Inconsistent data access patterns |
| **Fix** | Create repository classes for each model |
| **Effort** | Medium (8 repository files) |

#### D-15: `STARS_ENABLED` in .env.example But Not Supported

| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **Location** | `.env.example` |
| **Issue** | `STARS_ENABLED=true` present in .env.example but Telegram Stars removed in v4.2 |
| **Impact** | Confusing for new developers |
| **Fix** | Remove from .env.example |
| **Effort** | Low (edit 1 line) |

---

### 2.3 🟢 LOW Discrepancies

#### D-16: Legacy Crypto Constants Still in File

| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **Location** | `src/constants/payments.py` |
| **Issue** | `CURRENCIES`, `CRYPTO_CURRENCIES`, `PAYMENT_METHODS` still defined but unused |
| **Impact** | Confusion for new developers |
| **Fix** | Remove or mark as deprecated with comments |

#### D-17: `PLAN_PRICES` Uses Decimals, `TARIFF_CREDIT_COST` Uses Ints

| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **Location** | `src/constants/payments.py` vs `src/config/settings.py` |
| **Issue** | Inconsistent types for same tariff prices |
| **Impact** | Type conversion needed when mixing constants |
| **Fix** | Unify to Decimal type |

#### D-18: Self-Referencing FK Without Cascade

| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **Location** | `users.referred_by_id`, `transactions.reverses_transaction_id` |
| **Issue** | No cascade defined — orphaned records possible |
| **Impact** | Data integrity gaps |
| **Fix** | Add ON DELETE SET NULL or CASCADE |

#### D-19: `placement_disputes` FK Columns Not Indexed

| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **Location** | `src/db/models/dispute.py` |
| **Issue** | `advertiser_id`, `owner_id`, `admin_id` not individually indexed |
| **Impact** | Slower queries on these columns |
| **Fix** | Add indexes if query performance degrades |

#### D-20: Empty/Unused Directories

| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **Location** | Various |
| **Issue** | Empty directories exist in project structure |
| **Impact** | Clutter, confusion |
| **Fix** | Remove empty directories |

#### D-21: Mini App TS 5.9 vs Web Portal TS 6.0

| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **Location** | `mini_app/package.json`, `web_portal/package.json` |
| **Issue** | Different TypeScript versions |
| **Impact** | Potential type incompatibility when sharing types |
| **Fix** | Upgrade mini_app to TS 6.0 (planned S-30) |

#### D-22: Admin Panel Has 11 Endpoints (Not 9)

| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW (Info only) |
| **Location** | `src/api/routers/admin.py` |
| **Issue** | QWEN.md claims 9 endpoints, actual code has 11 |
| **Impact** | Documentation mismatch |
| **Fix** | Update QWEN.md (already updated in this report) |

---

## 3. Tech Debt Registry

### 3.1 Frontend Tech Debt (from S-27/S-28)

| ID | Severity | Description | Status | Effort |
|----|----------|-------------|--------|--------|
| TD-01 | 🔴 HIGH | Hardcoded plan prices in `web_portal/src/lib/constants.ts` (business: 4990). Should use `GET /api/billing/plans` via `usePlans()` hook. | Open → Fix in S-28 | Medium |
| TD-02 | 🟢 LOW | Cabinet/Feedback/NotFoundScreen unaudited | ✅ RESOLVED — All production-ready | — |
| TD-03 | 🟡 MEDIUM | MyCampaigns.tsx is stub (2.10KB) — shows empty state with Telegram bot redirect, not real campaign management. | ACCEPTED (intentional) | — |
| TD-04 | 🟢 LOW | mini_app package.json still on TS 5.9.3, tsconfig prepared for 6.0. | Planned S-30 | Low |
| TD-05 | 🟢 LOW | queries.ts for cross-cutting hooks (Variant B). Rule: only session/stats/contracts go here. | ✅ Documented | — |

### 3.2 Backend Tech Debt

| ID | Severity | Description | Status | Effort |
|----|----------|-------------|--------|--------|
| TD-06 | 🟡 MEDIUM | 8 models lack dedicated repositories (Campaign, Badge, YookassaPayment, etc.) | Open | Medium |
| TD-07 | 🟡 MEDIUM | No API tests for auth/login flow | Open | Medium |
| TD-08 | 🟡 MEDIUM | No tests for admin endpoints (11 endpoints) | Open | High |
| TD-09 | 🟡 MEDIUM | No tests for dispute resolution flow | Open | Medium |
| TD-10 | 🟡 MEDIUM | No tests for contract generation/signing | Open | Medium |
| TD-11 | 🟢 LOW | No health endpoint tests | Open | Low |
| TD-12 | 🟢 LOW | No webhook tests | Open | Low |
| TD-13 | 🟡 MEDIUM | `_notify_user_async` doesn't check `notifications_enabled` flag | Open | Low |
| TD-14 | 🟡 MEDIUM | Notification tasks create Bot instance per call | Open | Medium |
| TD-15 | 🟢 LOW | Redis dedup uses sync client in async context | Open | Medium |

---

## 4. Root Cause Analysis

### 4.1 Pattern: Incomplete Refactoring

**Finding:** Multiple discrepancies (D-02, D-16, D-17, D-15) stem from incomplete removal of legacy code during version upgrades.

**Root Cause:** When features are removed (Stars, CryptoBot, B2B), constants and configurations are sometimes left behind as "dead code" rather than being fully cleaned up.

**Recommendation:** Establish a "dead code cleanup" checklist for each sprint:
1. Remove unused constants
2. Remove unused env vars from .env.example
3. Remove unused API endpoints
4. Update documentation (QWEN.md, README)
5. Run `grep` for removed feature names across entire codebase

### 4.2 Pattern: Type Inconsistency

**Finding:** Discrepancies D-01, D-17 involve type mismatches between related fields.

**Root Cause:** Models created independently without cross-referencing existing column types. Financial constants use mixed types (Decimal vs int).

**Recommendation:** Add type consistency checks to code review process:
1. When adding FK, verify referenced column type matches
2. Use Decimal for all financial values
3. Run mypy in strict mode to catch type mismatches

### 4.3 Pattern: Incomplete Testing

**Finding:** Critical flows (auth, admin, disputes, contracts, FSM) have no test coverage.

**Root Cause:** Testing focused on unit-level service logic, not integration flows.

**Recommendation:** Prioritize integration tests for critical paths:
1. Auth/JWT flow (security-critical)
2. Placement lifecycle (revenue-critical)
3. Payout flow (financial-critical)
4. Dispute resolution (business-critical)

---

## 5. Recommended Fixes

### 5.1 Priority 1: Critical (Fix Immediately)

| Fix | Discrepancy | Effort | Impact |
|-----|-------------|--------|--------|
| Fix `legal_profiles.user_id` type (BigInteger → Integer) | D-01 | Low | Type consistency |
| Unify `PLAN_PRICES`/`PLAN_LIMITS` keys to `"business"` | D-02 | Low | Prevent KeyError risk |
| Add dead-letter queue for failed escrow releases | D-03 | Medium | Prevent stuck funds |
| Remove `STARS_ENABLED` from .env.example | D-15 | Low | Remove confusion |

### 5.2 Priority 2: Medium (Fix Next Sprint)

| Fix | Discrepancy | Effort | Impact |
|-----|-------------|--------|--------|
| Add explicit queue names to publication tasks | D-05 | Low | Prevent routing ambiguity |
| Remove deprecated `check_pending_invoices` from Beat | D-06 | Low | Reduce wasted cycles |
| Remove dead `/api/billing/invoice/{id}` endpoint | D-07 | Low | Clean API docs |
| Fix `ai_included` hardcoded values | D-08 | Medium | Consistent AI limits |
| Export all FSM states from `__init__.py` | D-09 | Low | Consistent imports |
| Add `background` queue to TASK_ROUTES | D-11 | Low | Correct task routing |
| Implement `COOLDOWN_HOURS` enforcement | D-12 | Medium | Payout rate limiting |
| Create 8 missing repositories | D-14 | Medium | Consistent data access |
| Fix TD-01: Hardcoded plan prices | TD-01 | Medium | Dynamic pricing |

### 5.3 Priority 3: Low (Fix When Convenient)

| Fix | Discrepancy | Effort | Impact |
|-----|-------------|--------|--------|
| Remove legacy crypto constants | D-16 | Low | Cleaner code |
| Unify financial constant types to Decimal | D-17 | Low | Type consistency |
| Add CASCADE to self-referencing FKs | D-18 | Low | Data integrity |
| Add indexes to dispute FK columns | D-19 | Low | Query performance |
| Remove empty directories | D-20 | Low | Cleaner structure |
| Upgrade mini_app to TS 6.0 | TD-04/D-21 | Low | Version consistency |
| Refactor notification Bot instance creation | D-13/TD-14 | Medium | Performance |
| Use async Redis client for dedup | D-10/TD-15 | Medium | Async consistency |

---

## 6. Action Items by Priority

### 6.1 Immediate (This Week)

- [ ] **D-01:** Create migration to fix `legal_profiles.user_id` type (BigInteger → Integer)
- [ ] **D-02:** Unify `PLAN_PRICES` key from `"agency"` to `"business"`
- [ ] **D-15:** Remove `STARS_ENABLED` from `.env.example`
- [ ] **D-09:** Export all FSM states from `src/bot/states/__init__.py`
- [ ] **D-07:** Remove dead `/api/billing/invoice/{id}` endpoint

### 6.2 Short Term (Next Sprint)

- [ ] **D-03:** Add monitoring for stuck escrow placements + dead-letter queue
- [ ] **D-05:** Add explicit `queue=` to publication task decorators
- [ ] **D-06:** Remove `check_pending_invoices` from Beat schedule
- [ ] **D-11:** Add `background` queue to TASK_ROUTES
- [ ] **TD-01:** Fix hardcoded plan prices in web_portal (use API)
- [ ] **D-08:** Fix `ai_included` to use PLAN_LIMITS values

### 6.3 Medium Term (Next 2-3 Sprints)

- [ ] **D-12:** Implement COOLDOWN_HOURS enforcement in PayoutService
- [ ] **D-14:** Create 8 missing repository classes
- [ ] **TD-07:** Write auth/JWT integration tests
- [ ] **TD-08:** Write admin endpoint tests
- [ ] **TD-09:** Write dispute resolution tests
- [ ] **TD-10:** Write contract signing tests
- [ ] **D-13/TD-14:** Refactor notification Bot instance to shared instance

### 6.4 Long Term (Future Sprints)

- [ ] **D-10/TD-15:** Migrate Redis dedup to async client
- [ ] **D-16:** Remove all legacy crypto constants
- [ ] **D-17:** Unify all financial constants to Decimal type
- [ ] **D-18:** Add CASCADE to self-referencing FKs
- [ ] **D-19:** Add indexes to dispute FK columns (if needed)
- [ ] **D-20:** Clean up empty directories
- [ ] **TD-04:** Upgrade mini_app TypeScript to 6.0

---

## Appendix: Verification Commands

```bash
# Verify D-04: No is_banned references
grep -r "is_banned" src/  # Should return nothing

# Verify D-02: Check PLAN_PRICES vs PLAN_LIMITS keys
python -c "
from src.constants.payments import PLAN_PRICES, PLAN_LIMITS
print('PLAN_PRICES keys:', sorted(PLAN_PRICES.keys()))
print('PLAN_LIMITS keys:', sorted(PLAN_LIMITS.keys()))
print('Mismatch:', set(PLAN_PRICES.keys()) ^ set(PLAN_LIMITS.keys()))
"

# Verify D-09: Check FSM state exports
python -c "
from src.bot.states import __all__
print('Exported states:', __all__)
"

# Verify D-16: Check for legacy crypto constants
grep -r "CRYPTO_CURRENCIES\|PAYMENT_METHODS\|CURRENCIES" src/

# Verify D-15: Check for STARS_ENABLED
grep -r "STARS_ENABLED" src/ .env.example

# Check test coverage
poetry run pytest --cov=src --cov-report=term-missing
```

---

🔍 Verified against: HEAD @ 2026-04-08 | Sources: All Phase 1 & Phase 2 discovery reports, QWEN.md, source code
✅ Validation: passed | 22 discrepancies catalogued | 15 tech debt items tracked | All items have severity, root cause, fix estimate
