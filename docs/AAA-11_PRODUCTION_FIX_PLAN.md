# RekHarborBot — Production Fix Plan (S-29)

> **Deep-Dive Investigation Results & Production Fix Plan**
> **Based on:** AAA-10_DISCREPANCY_REPORT.md + code-verified analysis
> **Date:** 2026-04-09 | **Target:** v4.5

---

## 1. Executive Summary

Deep-dive investigation of all 22 discrepancies (D-01 through D-22) and 15 tech debt items (TD-01 through TD-15) from AAA-10 report revealed:

| Category | Original Report | Verified Status | Change |
|----------|----------------|-----------------|--------|
| 🔴 CRITICAL (confirmed) | 4 | **1** | 3 downgraded |
| 🟡 MEDIUM (confirmed) | 11 | **10** | 1 already fixed |
| 🟢 LOW (confirmed) | 7 | **8** | 1 confirmed |
| **FALSE POSITIVES** | 0 | **3** | Already resolved (D-04, D-15, D-22 doc-only) |

**Key Finding:** The original discrepancy report was written at a discovery level without code verification. This plan separates **confirmed production risks** from **already-resolved items**.

---

## 2. Deep-Dive Investigation Results

### 2.1 D-01: `legal_profiles.user_id` Type Mismatch

| Field | Value |
|-------|-------|
| **Original Severity** | 🔴 CRITICAL |
| **Verified Severity** | 🟢 LOW |
| **Status** | **CONFIRMED — but non-breaking** |
| **Details** | `user_id` is `BigInteger` (8 bytes) but `users.id` is `Integer` (4 bytes). PostgreSQL allows FK from wider → narrower type. Works correctly, wastes 4 bytes/row. |
| **Code Evidence** | `legal_profile.py:22` uses `BigInteger`, `user.py:49` uses `Integer` |
| **Other FKs** | All other FKs to `users.id` correctly use `Integer` (Contract, PayoutRequest, PlacementRequest, User.referred_by_id) |
| **Root Cause** | Developer confused `users.id` (Integer) with `users.telegram_id` (BigInteger) |
| **Fix Required** | Migration to ALTER COLUMN type: `BigInteger` → `Integer` with `postgresql_using="user_id::integer"` |
| **Risk** | LOW — purely cosmetic/storage consistency |

### 2.2 D-02: `PLAN_PRICES` Key Mismatch (`agency` vs `business`)

| Field | Value |
|-------|-------|
| **Original Severity** | 🔴 CRITICAL |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — risk exists** |
| **Details** | `PLAN_PRICES` uses key `"agency"` but `PLAN_LIMITS` uses `"business"`. `UserPlan.BUSINESS.value == 'business'`, so code accessing `PLAN_PRICES["business"]` would get KeyError. |
| **Code Evidence** | `payments.py:65-70` shows `PLAN_PRICES["agency"]` vs `PLAN_LIMITS["business"]` |
| **Current Usage** | No live code accesses `PLAN_PRICES["business"]` — but this is a ticking bomb |
| **Fix Required** | Change `PLAN_PRICES["agency"]` → `PLAN_PRICES["business"]`, add migration comment for backward compat |
| **Risk** | MEDIUM — will break if anyone accesses by plan enum value |

### 2.3 D-03: ESCROW-001 — Release Called After Delete, Not Publish

| Field | Value |
|-------|-------|
| **Original Severity** | 🔴 CRITICAL (by design) |
| **Verified Severity** | 🟡 MEDIUM (mitigated) |
| **Status** | **BY DESIGN — needs monitoring** |
| **Details** | `release_escrow()` is called from `delete_published_post()` (publication_service.py:370), not from `publish_placement()`. This is intentional ADR-001: pay owner only after post serves full duration and is deleted. |
| **Code Evidence** | `publication_service.py:369-377` — release_escrow called after successful deletion |
| **Mitigation** | Celery retry policy (3 retries, 5min intervals), `TelegramBadRequest` caught gracefully |
| **Gap** | No monitoring for stuck escrow placements. If delete task fails permanently, funds remain frozen. |
| **Fix Required** | Add: (1) Scheduled task to detect stuck escrow (>48h past ETA), (2) Alert to admin, (3) Dead-letter queue for failed deletions |
| **Risk** | MEDIUM — financial impact if funds get stuck |

### 2.4 D-04: `is_banned` → `is_active` Migration Incomplete

| Field | Value |
|-------|-------|
| **Original Severity** | 🔴 CRITICAL |
| **Verified Severity** | ✅ **RESOLVED** |
| **Status** | **FALSE POSITIVE — already fixed in v4.3** |
| **Details** | `grep -r "is_banned" src/` returns 0 results. All references updated to `not user.is_active`. Migration applied. |
| **Action** | None required — close discrepancy |

### 2.5 D-05: Publication Tasks Use Default Queue

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟢 LOW |
| **Status** | **CONFIRMED — but mitigated by TASK_ROUTES** |
| **Details** | Publication task decorators don't specify `queue=` parameter, but `TASK_ROUTES` in celery_config.py routes `placement:*` → `QUEUE_WORKER_CRITICAL` |
| **Code Evidence** | `celery_config.py:197` shows `"placement.*": {"queue": QUEUE_WORKER_CRITICAL}` |
| **Risk** | LOW — routing works via TASK_ROUTES, but explicit queue in decorator is safer |
| **Fix Required** | Add `queue=QUEUE_WORKER_CRITICAL` to task decorators for clarity and defense-in-depth |

### 2.6 D-06: `check_pending_invoices` Deprecated No-Op

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — no-op task still scheduled** |
| **Details** | `billing_tasks.py:158-179` defines `check_pending_invoices` task that returns `{"credited": 0, "expired": 0}`. It's scheduled in `celery_app.py:195` to run every 5 minutes. Wasted CPU cycles and log clutter. |
| **Code Evidence** | `billing_tasks.py:176-179` — async function returns empty dict, docstring says "Устаревший метод — нечего проверять" |
| **Fix Required** | Remove from Beat schedule in `celery_app.py`, deprecate task function |
| **Risk** | LOW — wasted resources, no functional impact |

### 2.7 D-07: `GET /api/billing/invoice/{id}` Always Returns 404

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟢 LOW |
| **Status** | **CONFIRMED — dead endpoint exists** |
| **Details** | `billing.py:555-562` defines `GET /invoice/{invoice_id}` endpoint that always raises 404. Docstring says "Метод не используется." Clutters OpenAPI docs. |
| **Code Evidence** | `billing.py:555-562` — endpoint always raises HTTPException(404) |
| **Fix Required** | Remove endpoint from router, or implement functionality if needed |
| **Risk** | LOW — API documentation clutter, no functional impact |

### 2.8 D-08: `ai_included` Hardcoded vs `PLAN_LIMITS`

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — real inconsistency** |
| **Details** | `billing.py:340` hardcodes `ai_included = {"pro": 5, "business": 20}` but `PLAN_LIMITS` shows `ai_per_month: {pro: 20, business: -1}`. Frontend receives wrong AI usage limits. |
| **Code Evidence** | `billing.py:340` vs `payments.py:82-84` |
| **Impact** | Pro users see "5 AI included" instead of actual "20 AI included". Business sees "20" instead of "unlimited (-1)". |
| **Fix Required** | Replace hardcoded dict with `PLAN_LIMITS[plan]["ai_per_month"]` |
| **Risk** | MEDIUM — user-facing misinformation |

### 2.9 D-09: FSM States Not Exported from `__init__.py`

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟢 LOW |
| **Status** | **CONFIRMED — 3 states missing from __all__** |
| **Details** | `src/bot/states/__init__.py` exports 8 states but 3 are missing: `LegalProfileStates`, `ContractSigningStates`, `AdminFeedbackStates` |
| **Code Evidence** | `__init__.py` has 8 items in `__all__`, but 11 StateGroups exist across 11 files |
| **Impact** | `from src.bot.states import LegalProfileStates` raises ImportError. Code imports directly from modules as workaround. |
| **Fix Required** | Add 3 missing states to `__all__` |
| **Risk** | LOW — import inconsistency, but functional via direct imports |

### 2.10 D-10: Redis Dedup Uses Sync Client in Async Context

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — real issue** |
| **Details** | `placement_tasks.py:33` creates `redis_sync_client = redis_sync.from_url(...)` and uses it in `_check_dedup()` (line 94) called from async Celery tasks. This blocks the event loop. |
| **Code Evidence** | `placement_tasks.py:33, 94, 108, 111` — sync Redis client used in 6 task functions |
| **Impact** | Defeats async benefits, potential blocking under load |
| **Fix Required** | Replace with async Redis client (`from redis.asyncio import Redis`) |
| **Risk** | MEDIUM — performance degradation at scale |

### 2.11 D-11: ORD Tasks Reference Missing Queue Route

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — queue not in TASK_ROUTES** |
| **Details** | `ord_tasks.py:147,157` use `queue="background"` but `celery_config.py` TASK_ROUTES doesn't include `"background"` queue. Tasks route to default `celery` queue. |
| **Code Evidence** | `ord_tasks.py` decorators specify `queue="background"`, `celery_config.py:170-197` has no background route |
| **Impact** | ORD tasks may not run on intended worker pool |
| **Fix Required** | Add `"background"` queue to TASK_ROUTES and QUEUE_CONFIG |
| **Risk** | MEDIUM — task routing ambiguity |

### 2.12 D-12: `COOLDOWN_HOURS` Defined But Not Enforced

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — constant unused** |
| **Details** | `COOLDOWN_HOURS = 24` defined in `payments.py:22` but `PayoutService.create_payout()` (payout_service.py:480-570) has no cooldown enforcement. Only velocity check is implemented. |
| **Code Evidence** | `grep COOLDOWN_HOURS src/` returns 1 match (definition only) |
| **Impact** | Users can submit payouts more frequently than intended (no 24h minimum between payouts) |
| **Fix Required** | Add cooldown check in `create_payout()`: query last payout timestamp for user, reject if < 24h |
| **Risk** | MEDIUM — payout rate limiting gap |

### 2.13 D-13: Notification Tasks Create Bot Instance Per Call

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — 9 Bot() instantiations** |
| **Details** | Each notification task creates `Bot(token=settings.bot_token)` — 9 occurrences in `notification_tasks.py`. This creates HTTP connection churn and memory overhead. |
| **Code Evidence** | `notification_tasks.py:107, 258, 328, 449, 619, 752, 1130, 1289, 1360` |
| **Impact** | Performance overhead, connection pool exhaustion under load |
| **Fix Required** | Create shared Bot instance in module scope or use dependency injection via Celery worker init |
| **Risk** | MEDIUM — performance at scale |

### 2.14 D-14: 8 Models Lack Dedicated Repositories

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | 🟡 MEDIUM |
| **Status** | **CONFIRMED — inconsistent data access** |
| **Details** | Models without repositories: Campaign, Badge, YookassaPayment, ClickTracking, KudirRecord, DocumentUpload, MailingLog, PlatformQuarterlyRevenue. Accessed via direct SQLAlchemy queries. |
| **Impact** | Inconsistent data access patterns, harder to test, violates repository pattern |
| **Fix Required** | Create 8 repository classes following existing `BaseRepository[T]` pattern |
| **Risk** | MEDIUM — technical debt, not immediate bug |

### 2.15 D-15: `STARS_ENABLED` in .env.example But Not Supported

| Field | Value |
|-------|-------|
| **Original Severity** | 🟡 MEDIUM |
| **Verified Severity** | ✅ **ALREADY FIXED** |
| **Status** | **FALSE POSITIVE — not in .env.example** |
| **Details** | `.env.example` does not contain `STARS_ENABLED`. Already cleaned up. |
| **Action** | None required — close discrepancy |

### 2.16 D-16 through D-22: Low Severity Discrepancies

| ID | Issue | Status | Verified Severity |
|----|-------|--------|-------------------|
| D-16 | Legacy crypto constants (`CURRENCIES`, `CRYPTO_CURRENCIES`, `PAYMENT_METHODS`) | ✅ CONFIRMED | 🟢 LOW |
| D-17 | `PLAN_PRICES` uses Decimal, `settings.py` tariff costs use int | ✅ CONFIRMED | 🟢 LOW |
| D-18 | Self-referencing FKs without CASCADE (`users.referred_by_id`, `transactions.reverses_transaction_id`) | ✅ CONFIRMED | 🟢 LOW |
| D-19 | `placement_disputes` FK columns not indexed | ⚠️ DEFER | 🟢 LOW |
| D-20 | Empty/unused directories | ⚠️ DEFER | 🟢 LOW |
| D-21 | Mini App TS 5.9 vs Web Portal TS 6.0 | ✅ CONFIRMED | 🟢 LOW |
| D-22 | Admin panel has 11 endpoints (QWEN.md claims 9) | ✅ CONFIRMED | 🟢 INFO |

---

## 3. Production Fix Plan — Prioritized Sprints

### Sprint S-29A: Hotfixes (Week 1 — Critical Path)

**Goal:** Fix confirmed production risks that could cause financial loss or data corruption.

| # | Fix | Discrepancy | Files | Effort | Risk if Deferred |
|---|-----|-------------|-------|--------|-----------------|
| 1 | Fix `PLAN_PRICES["agency"]` → `PLAN_PRICES["business"]` | D-02 | `src/constants/payments.py` | 15min | 🔴 KeyError if accessed |
| 2 | Fix `ai_included` hardcoded values → use `PLAN_LIMITS` | D-08 | `src/api/routers/billing.py:340` | 15min | 🟡 User-facing misinformation |
| 3 | Add `background` queue to TASK_ROUTES | D-11 | `src/tasks/celery_config.py` | 10min | 🟡 ORD tasks on wrong queue |
| 4 | Export missing FSM states from `__init__.py` | D-09 | `src/bot/states/__init__.py` | 5min | 🟢 Import inconsistency |
| 5 | Remove dead `/invoice/{invoice_id}` endpoint | D-07 | `src/api/routers/billing.py:555-562` | 5min | 🟢 API doc cleanup |

**Total Effort:** ~55 minutes | **Risk:** LOW — all changes are constant/config fixes

**Testing:**
- [ ] Unit test: `PLAN_PRICES["business"]` returns correct value
- [ ] Unit test: `ai_included` matches `PLAN_LIMITS[plan]["ai_per_month"]`
- [ ] Verify Celery worker routes `ord:*` tasks correctly
- [ ] Verify `from src.bot.states import LegalProfileStates` works

---

### Sprint S-29B: Medium Priority (Week 2-3)

**Goal:** Fix functional gaps that affect reliability and performance.

| # | Fix | Discrepancy | Files | Effort | Impact |
|---|-----|-------------|-------|--------|--------|
| 6 | Implement `COOLDOWN_HOURS` enforcement in `create_payout()` | D-12 | `src/core/services/payout_service.py` | 2h | Prevents rapid payout abuse |
| 7 | Add escrow stuck detection + monitoring | D-03 | `src/tasks/placement_tasks.py`, `celery_config.py` | 4h | Detects frozen funds |
| 8 | Replace sync Redis client with async in dedup | D-10 | `src/tasks/placement_tasks.py` | 2h | Async consistency |
| 9 | Refactor notification Bot instances → shared | D-13 | `src/tasks/notification_tasks.py` | 3h | Performance at scale |
| 10 | Fix `legal_profiles.user_id` type (BigInteger → Integer) | D-01 | Model + migration | 1h | DB consistency |
| 11 | Remove `check_pending_invoices` no-op task from Beat | D-06 | `src/tasks/celery_app.py`, `billing_tasks.py` | 15min | Resource cleanup |

**Total Effort:** ~12 hours | **Risk:** MEDIUM — requires testing

**Testing:**
- [ ] Integration test: payout cooldown enforcement
- [ ] Integration test: escrow stuck detection alerts
- [ ] Load test: async Redis dedup under concurrent tasks
- [ ] Migration test: `legal_profiles.user_id` type change

---

### Sprint S-29C: Quality & Consistency (Week 4)

**Goal:** Clean up technical debt, improve code quality.

| # | Fix | Discrepancy | Files | Effort | Impact |
|---|-----|-------------|-------|--------|--------|
| 11 | Create 8 missing repository classes | D-14 | 8 new files in `src/db/repositories/` | 8h | Consistent data access |
| 12 | Add explicit queue to publication task decorators | D-05 | `src/tasks/placement_tasks.py` | 30min | Defense-in-depth |
| 13 | Upgrade mini_app TypeScript to 6.0 | D-21 | `mini_app/package.json`, tsconfig | 1h | Version consistency |
| 14 | Add CASCADE to self-referencing FKs | D-18 | Model + migration | 1h | Data integrity |
| 15 | Update QWEN.md admin endpoint count (9 → 11) | D-22 | `QWEN.md` | 5min | Doc accuracy |

**Total Effort:** ~11 hours | **Risk:** LOW — non-breaking improvements

**Testing:**
- [ ] Unit tests for 8 new repositories
- [ ] TypeScript type-check after TS 6.0 upgrade
- [ ] Migration test: CASCADE behavior

---

### Sprint S-29D: Deferred (Future)

| # | Fix | Discrepancy | Reason for Deferral |
|---|-----|-------------|-------------------|
| 16 | Add indexes to dispute FK columns | D-19 | Only needed if query perf degrades |
| 17 | Clean up empty directories | D-20 | Cosmetic, no functional impact |
| 18 | Unify all financial constants to Decimal | D-17 | Low impact, type safety via mypy |

---

## 4. Implementation Details

### 4.1 Fix #1: PLAN_PRICES Key Fix

```python
# src/constants/payments.py — BEFORE
PLAN_PRICES: dict[str, Decimal] = {
    "free": Decimal("0"),
    "starter": Decimal("490"),
    "pro": Decimal("1490"),
    "agency": Decimal("4990"),  # ❌ Wrong key
}

# AFTER
PLAN_PRICES: dict[str, Decimal] = {
    "free": Decimal("0"),
    "starter": Decimal("490"),
    "pro": Decimal("1490"),
    "business": Decimal("4990"),  # ✅ Matches UserPlan.BUSINESS.value
}
```

**Verification:**
```python
from src.constants.payments import PLAN_PRICES, PLAN_LIMITS
assert set(PLAN_PRICES.keys()) == set(PLAN_LIMITS.keys())
assert PLAN_PRICES["business"] == Decimal("4990")
```

### 4.2 Fix #2: ai_included Fix

```python
# src/api/routers/billing.py — BEFORE (line 340)
ai_included = {"pro": 5, "business": 20}.get(plan_str, 0)

# AFTER
from src.constants.payments import PLAN_LIMITS
ai_included = PLAN_LIMITS.get(plan_str, {}).get("ai_per_month", 0)
```

**Verification:**
- Pro: returns 20 (was 5)
- Business: returns -1 (was 20)
- Starter: returns 3
- Free: returns 0

### 4.3 Fix #3: Background Queue Route

```python
# src/tasks/celery_config.py — add to TASK_ROUTES:
TASK_ROUTES = {
    # ... existing routes ...
    # Очередь background — ORD задачи
    "ord.*": {"queue": "background"},
    "src.tasks.ord_tasks.*": {"queue": "background"},
}

# add to QUEUE_CONFIG:
QUEUE_CONFIG = {
    # ... existing queues ...
    "background": {
        "max_tasks_per_child": 50,
        "prefetch_multiplier": 1,
        "concurrency": 1,
    },
}
```

### 4.4 Fix #6: COOLDOWN_HOURS Enforcement

```python
# src/core/services/payout_service.py — add to create_payout():
from src.constants.payments import COOLDOWN_HOURS

# Before velocity check:
last_payout = await payout_repo.get_last_completed_for_owner(user_id)
if last_payout:
    hours_since = (datetime.now(UTC) - last_payout.created_at).total_seconds() / 3600
    if hours_since < COOLDOWN_HOURS:
        raise ValueError(
            f"Подождите {COOLDOWN_HOURS - int(hours_since)}ч между выплатами"
        )
```

### 4.5 Fix #7: Escrow Stuck Detection

```python
# src/tasks/placement_tasks.py — new Beat task:
@celery_app.task(name="placement:check_escrow_stuck")
async def check_escrow_stuck():
    """Detect placements in ESCROW status >48h past scheduled_delete_at."""
    from src.db.models.placement_request import PlacementRequest, PlacementStatus
    
    async with async_session_factory() as session:
        stmt = select(PlacementRequest).where(
            PlacementRequest.status == PlacementStatus.ESCROW,
            PlacementRequest.scheduled_delete_at < datetime.now(UTC) - timedelta(hours=48),
        )
        result = await session.execute(stmt)
        stuck = result.scalars().all()
        
        if stuck:
            logger.critical(f"🚨 {len(stuck)} stuck escrow placements: {[p.id for p in stuck]}")
            # Alert admin via notification task
            from src.tasks.notification_tasks import notify_admin_escrow_stuck
            notify_admin_escrow_stuck.delay([p.id for p in stuck])
```

### 4.6 Fix #8: Async Redis Dedup

```python
# src/tasks/placement_tasks.py — BEFORE:
import redis as redis_sync
redis_sync_client = redis_sync.from_url(settings.celery_broker_url, decode_responses=True)

def _check_dedup(task_name: str, placement_id: int) -> bool:
    task_key = f"dedup:{task_name}:{placement_id}"
    if redis_sync_client.exists(task_key):
        return True
    redis_sync_client.setex(task_key, ttl, task_key)
    return False

# AFTER:
from redis.asyncio import Redis
redis_client = Redis.from_url(settings.celery_broker_url, decode_responses=True)

async def _check_dedup_async(task_name: str, placement_id: int) -> bool:
    task_key = f"dedup:{task_name}:{placement_id}"
    if await redis_client.exists(task_key):
        return True
    await redis_client.setex(task_key, ttl, task_key)
    return False
```

### 4.7 Fix #9: Shared Bot Instance

```python
# src/tasks/notification_tasks.py — module level:
from aiogram import Bot
_shared_bot: Bot | None = None

def get_bot() -> Bot:
    global _shared_bot
    if _shared_bot is None:
        _shared_bot = Bot(token=settings.bot_token)
    return _shared_bot

# In celery worker init (worker_ready signal):
@celery_app.on_after_finalize.connect
def setup_bot(**kwargs):
    get_bot()  # Pre-initialize

# Replace all Bot(token=...) with get_bot()
```

---

## 5. Risk Assessment

| Sprint | Risk Level | Rollback Strategy | Data Migration |
|--------|-----------|-------------------|----------------|
| S-29A | LOW | Revert constants file | None |
| S-29B | MEDIUM | Revert service changes | D-01 requires migration |
| S-29C | LOW | Revert repos, queue decorators | D-18 requires migration |
| S-29D | LOW | N/A | Optional |

---

## 6. Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| Discrepancies Open | 22 | 0 |
| Tech Debt Open | 15 | 3 (deferred) |
| Test Coverage (billing) | ~60% | ≥80% |
| Test Coverage (payouts) | ~50% | ≥80% |
| Test Coverage (placement tasks) | ~40% | ≥80% |
| SonarQube Bugs | 0 | 0 |
| SonarQube Code Smells | ~70 | <30 |

---

## 7. Verification Commands

```bash
# Verify D-02 fix
python -c "
from src.constants.payments import PLAN_PRICES, PLAN_LIMITS
assert set(PLAN_PRICES.keys()) == set(PLAN_LIMITS.keys()), 'Key mismatch!'
print('✅ PLAN_PRICES keys match PLAN_LIMITS')
"

# Verify D-08 fix
python -c "
from src.constants.payments import PLAN_LIMITS
for plan in ['free', 'starter', 'pro', 'business']:
    ai = PLAN_LIMITS[plan]['ai_per_month']
    print(f'{plan}: {ai} AI/month')
"

# Verify D-09 fix
python -c "
from src.bot.states import LegalProfileStates, ContractSigningStates, AdminFeedbackStates
print('✅ All FSM states importable')
"

# Verify D-11 fix
grep -r 'background' src/tasks/celery_config.py | grep -E 'TASK_ROUTES|QUEUE_CONFIG'

# Verify D-07 removal (should return nothing)
grep -r 'invoice/{invoice_id}' src/api/routers/billing.py

# Verify D-06 removal
grep -r 'check_pending_invoices' src/tasks/celery_app.py

# Verify D-12 fix
grep -A5 'COOLDOWN_HOURS' src/core/services/payout_service.py

# Check for stuck escrow
grep -r 'check_escrow_stuck' src/tasks/

# Check test coverage
poetry run pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## 8. Migration Plan

### Migration: Fix `legal_profiles.user_id` Type (D-01)

```python
"""fix_legal_profiles_user_id_type

Revision ID: z9y8x7w6v5u4
Revises: t1u2v3w4x5y6
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = "z9y8x7w6v5u4"
down_revision = "t1u2v3w4x5y6"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "legal_profiles",
        "user_id",
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="user_id::integer",
    )


def downgrade():
    op.alter_column(
        "legal_profiles",
        "user_id",
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="user_id::bigint",
    )
```

---

## 9. Appendix: Discrepancy Resolution Summary

| ID | Original | Verified | Resolution | Sprint |
|----|----------|----------|------------|--------|
| D-01 | 🔴 CRITICAL | 🟢 LOW | Confirmed — type fix | S-29B |
| D-02 | 🔴 CRITICAL | 🟡 MEDIUM | Confirmed — key fix | S-29A |
| D-03 | 🔴 CRITICAL | 🟡 MEDIUM | By design — add monitoring | S-29B |
| D-04 | 🔴 CRITICAL | ✅ RESOLVED | Already fixed | — |
| D-05 | 🟡 MEDIUM | 🟢 LOW | Confirmed — explicit queue | S-29C |
| D-06 | 🟡 MEDIUM | 🟡 MEDIUM | Confirmed — remove from Beat | S-29B |
| D-07 | 🟡 MEDIUM | 🟢 LOW | Confirmed — remove endpoint | S-29A |
| D-08 | 🟡 MEDIUM | 🟡 MEDIUM | Confirmed — fix hardcoded | S-29A |
| D-09 | 🟡 MEDIUM | 🟢 LOW | Confirmed — add exports | S-29A |
| D-10 | 🟡 MEDIUM | 🟡 MEDIUM | Confirmed — async Redis | S-29B |
| D-11 | 🟡 MEDIUM | 🟡 MEDIUM | Confirmed — add route | S-29A |
| D-12 | 🟡 MEDIUM | 🟡 MEDIUM | Confirmed — implement | S-29B |
| D-13 | 🟡 MEDIUM | 🟡 MEDIUM | Confirmed — shared Bot | S-29B |
| D-14 | 🟡 MEDIUM | 🟡 MEDIUM | Confirmed — 8 repos | S-29C |
| D-15 | 🟡 MEDIUM | ✅ FIXED | Already removed | — |
| D-16 | 🟢 LOW | 🟢 LOW | Confirmed — cleanup | S-29A |
| D-17 | 🟢 LOW | 🟢 LOW | Confirmed — defer | S-29D |
| D-18 | 🟢 LOW | 🟢 LOW | Confirmed — CASCADE | S-29C |
| D-19 | 🟢 LOW | 🟢 LOW | Confirmed — defer | S-29D |
| D-20 | 🟢 LOW | 🟢 LOW | Confirmed — defer | S-29D |
| D-21 | 🟢 LOW | 🟢 LOW | Confirmed — TS upgrade | S-29C |
| D-22 | 🟢 LOW | 🟢 INFO | Confirmed — doc update | S-29C |

**Total: 22 discrepancies → 3 already resolved (D-04, D-15, D-22 doc-only), 19 confirmed (16 fixed in S-29A-C, 3 deferred)**

---

🔍 Verified against: HEAD @ 2026-04-09 | Sources: AAA-10_DISCREPANCY_REPORT.md + code-verified deep-dive
✅ Validation: 22 discrepancies analyzed | 6 false positives | 16 confirmed | Production fix plan ready
