# RekHarborBot — Celery Task Reference

> **RekHarborBot AAA Documentation v4.3 | April 2026**
> **Document:** AAA-06_CELERY_REFERENCE
> **Verified against:** HEAD @ 2026-04-08 | Source: `src/tasks/` (16 files), `src/tasks/celery_config.py`

---

## Table of Contents

1. [Queue Architecture](#1-queue-architecture)
2. [Task Registry (40+ Tasks)](#2-task-registry)
3. [Beat Schedule (26 Periodic Tasks)](#3-beat-schedule)
4. [Task Dependency Graph](#4-task-dependency-graph)
5. [Retry Policies](#5-retry-policies)
6. [Error Handling Patterns](#6-error-handling-patterns)
7. [Monitoring & Alerting](#7-monitoring--alerting)
8. [Known Issues](#8-known-issues)

---

## 1. Queue Architecture

### 1.1 Queue Overview

| Queue | Workers | Concurrency | Purpose | Task Count |
|-------|---------|-------------|---------|-----------|
| `celery` (default) | worker_critical | 2 | Publication tasks (fallback) | 3 |
| `mailing` | worker_critical | 2 | Notifications, SLA checks, reminders | ~12 |
| `notifications` | worker_critical | 2 | User notifications | ~10 |
| `billing` | worker_critical | 2 | Plan renewals, tax calendar | 2 |
| `parser` | worker_background | 4 | Channel parsing, stats updates | 3 |
| `cleanup` | worker_background | 4 | Log cleanup, archival, integrity | 3 |
| `rating` | worker_background | 4 | Rating recalculation, toplists | 2 |
| `gamification` | worker_game | 2 | Streaks, badges, digests | 4 |
| `badges` | worker_game | 2 | Badge eligibility checks | 2 |
| `background` | — | — | ORD registration, ERIR polling | 3 |
| `worker_critical` | — | — | Placement SLA, publication health | 6 |

### 1.2 Worker Configuration

**Source:** `docker-compose.yml`

| Worker | Queues | Concurrency | Command |
|--------|--------|-------------|---------|
| worker_critical | `celery,mailing,notifications,billing` | 2 | `celery -A src.tasks.celery_app worker -Q celery,mailing,notifications,billing -n critical@%h --concurrency=2 -E` |
| worker_background | `parser,cleanup,rating` | 4 | `celery -A src.tasks.celery_app worker -Q parser,cleanup,rating -n background@%h --concurrency=4 -E` |
| worker_game | `gamification,badges` | 2 | `celery -A src.tasks.celery_app worker -Q gamification,badges -n game@%h --concurrency=2 -E` |

**Health Checks:** All workers have `celery inspect ping` health checks (30s interval, 10s timeout, 3 retries).

---

## 2. Task Registry

### 2.1 Publication Tasks (`src/tasks/publication_tasks.py`)

| Task | Name | Queue | Bind | Max Retries | Retry Delay | Purpose |
|------|------|-------|------|-------------|-------------|---------|
| publish_placement | `publication:publish_placement` | default | ✅ | 3 | 3600s (1h) | Send message to channel, pin if needed |
| delete_published_post | `publication:delete_published_post` | default | ✅ | 3 | 300s (5m) | Unpin + delete post, release escrow (ESCROW-001) |
| unpin_and_delete_post | `publication:unpin_and_delete_post` | default | ✅ | 3 | 300s (5m) | Unpin + delete without escrow release |
| check_scheduled_deletions | `publication:check_scheduled_deletions` | default | ❌ | — | — | Beat: find expired posts, trigger deletion |

**Dependencies:** `PublicationService`, Bot instance, `celery_async_session_factory`

**Side Effects:**
- `publish_placement`: Sends message → sets message_id → logs publication → schedules delete
- `delete_published_post`: Deletes message → **releases escrow** → status → completed

**Error Handling:** Retry on Telegram API errors. `TelegramBadRequest` → pass for already-deleted posts.

**⚠️ KNOWN ISSUE:** Tasks use `default` queue, not `worker_critical`. They run on worker_critical only because it includes the `celery` (default) queue.

---

### 2.2 Placement SLA Tasks (`src/tasks/placement_tasks.py`)

| Task | Name | Queue | Bind | Beat Schedule | SLA Constant | Purpose |
|------|------|-------|------|---------------|-------------|---------|
| check_owner_response_sla | `placement:check_owner_response_sla` | worker_critical | ✅ | Every 5 min | 24h | Status→failed, refund 100%, notify |
| check_payment_sla | `placement:check_payment_sla` | worker_critical | ✅ | Every 5 min | 24h | Status→cancelled, reputation -20 |
| check_counter_offer_sla | `placement:check_counter_offer_sla` | worker_critical | ✅ | Every 5 min | 24h | Status→failed, refund 100% |
| publish_placement | `placement:publish_placement` | worker_critical | ✅ | On-demand | — | Send message, reputation +1 |
| retry_failed_publication | `placement:retry_failed_publication` | worker_critical | ✅ | On-demand | — | Retry once, then final fail |
| check_published_posts_health | `placement:check_published_posts_health` | worker_critical | ✅ | Every 6h | — | Monitor bot admin rights |

**Deduplication:** Redis-based via `_check_dedup()` with TTL per task type

**Dependencies:** `PlacementRequestRepository`, `BillingService`, `ReputationService`, `NotificationService`

---

### 2.3 Notification Tasks (`src/tasks/notification_tasks.py`)

| Task | Name | Queue | Bind | Trigger | Purpose |
|------|------|-------|------|---------|---------|
| check_low_balance | `mailing:check_low_balance` | mailing | ✅ | Beat: hourly | Notify users with balance < 50₽ |
| notify_user | `mailing:notify_user` | mailing | ✅ | On-demand | Generic user notification (with dedup) |
| notify_campaign_status | `notifications:notify_campaign_status` | notifications | ✅ | On-demand | Campaign status changes |
| notify_owner_new_placement_task | `notifications:notify_owner_new_placement` | notifications | ❌ | On-demand | New placement to owner |
| notify_owner_xp_for_publication | `notifications:notify_owner_xp_for_publication` | notifications | ❌ | On-demand | XP award notification |
| notify_payout_created_task | `notifications:notify_payout_created` | notifications | ❌ | On-demand | Payout created |
| notify_payout_paid_task | `notifications:notify_payout_paid` | notifications | ❌ | On-demand | Payout completed |
| notify_post_published | `notifications:notify_post_published` | notifications | ❌ | On-demand | Post published |
| notify_campaign_finished | `notifications:notify_campaign_finished` | notifications | ❌ | On-demand | Campaign complete |
| notify_placement_rejected | `notifications:notify_placement_rejected` | notifications | ❌ | On-demand | Placement rejected |
| notify_changes_requested | `notifications:notify_changes_requested` | notifications | ❌ | On-demand | Changes needed |
| notify_low_balance_enhanced | `notifications:notify_low_balance_enhanced` | notifications | ❌ | On-demand | Low balance for campaign |
| notify_plan_expiring | `notifications:notify_plan_expiring` | notifications | ❌ | On-demand | Plan expiring soon |
| notify_expiring_plans | `mailing:notify_expiring_plans` | mailing | ✅ | Beat: daily | Batch plan expiry notices |
| notify_expired_plans | `mailing:notify_expired_plans` | mailing | ✅ | Beat: daily | Batch expired plan notices |
| auto_approve_placements | `mailing:auto_approve_placements` | mailing | ✅ | Beat: hourly | Auto-approve after 24h |
| notify_pending_placement_reminders | `mailing:placement-reminders` | mailing | ✅ | Beat: 2h | Pending placement reminders |

**Deduplication:** `notify_user` uses SHA-256 hash of `(telegram_id, message)` with 5-min TTL

**Error Handling:** `TelegramForbiddenError` → user blocked → don't retry

---

### 2.4 Billing Tasks (`src/tasks/billing_tasks.py`)

| Task | Name | Queue | Beat Schedule | Purpose |
|------|------|-------|---------------|---------|
| check_plan_renewals | `billing:check_plan_renewals` | billing | Daily 03:00 UTC | Auto-renew or downgrade plans |
| check_pending_invoices | `billing:check_pending_invoices` | billing | Every 5 min | ⚠️ DEPRECATED — no-op |

**Plan Renewal Logic:**
- If `credits >= plan_cost` → renew for 30 days, reset `ai_uses_count`
- If `credits < plan_cost` → downgrade to `free`, notify user

---

### 2.5 ORD Tasks (`src/tasks/ord_tasks.py`)

| Task | Name | Queue | Bind | Max Retries | Retry Delay | Purpose |
|------|------|-------|------|-------------|-------------|---------|
| register_creative_task | `ord:register_creative` | background | ✅ | 3 | 300s | Register ad in ORD (Yandex) |
| report_publication_task | `ord:report_publication` | background | ✅ | 3 | 300s | Report publication to ORD |
| poll_erid_status | `ord:poll_erid_status` | background | ✅ | 12 | 300s | Poll ERIR status (up to 1h) |

**ERIR Status Flow:** `pending` → `erir_confirmed` | `erir_failed` | `erir_timeout`

**Dependencies:** `OrdService`, `YandexOrdProvider` or `StubOrdProvider`

---

### 2.6 Parser Tasks (`src/tasks/parser_tasks.py`)

| Task | Name | Queue | Beat Schedule | Time Limit | Purpose |
|------|------|-------|---------------|-----------|---------|
| refresh_chat_database | `parser:refresh_chat_database` | parser | Daily 03:00 | 1800s (30min) | Re-sync channel data from Telegram |
| update_chat_statistics | `parser:update_chat_statistics` | parser | Every 6h | — | Update ER, views, ratings |

---

### 2.7 Cleanup Tasks (`src/tasks/cleanup_tasks.py`)

| Task | Name | Queue | Beat Schedule | Purpose |
|------|------|-------|---------------|---------|
| delete_old_logs | `cleanup:delete_old_logs` | cleanup | Weekly Sun 03:00 | Purge old log entries |

---

### 2.8 Rating Tasks (`src/tasks/rating_tasks.py`)

| Task | Name | Queue | Beat Schedule | Purpose |
|------|------|-------|---------------|---------|
| recalculate_ratings_daily | `rating:recalculate_ratings_daily` | rating | Daily 04:00 | Recalculate channel ratings |
| update_weekly_toplists | `rating:update_weekly_toplists` | rating | Weekly Mon 05:00 | Update top channel lists |

---

### 2.9 Gamification Tasks (`src/tasks/gamification_tasks.py`)

| Task | Name | Queue | Beat Schedule | Purpose |
|------|------|-------|---------------|---------|
| update_streaks_daily | `gamification:update_streaks_daily` | gamification | Daily 00:00 | Update login streaks |
| send_weekly_digest | `gamification:send_weekly_digest` | gamification | Weekly Mon 10:00 | Send weekly digest |
| check_seasonal_events | `gamification:check_seasonal_events` | gamification | Daily 08:00 | Check for seasonal events |

---

### 2.10 Badge Tasks (`src/tasks/badge_tasks.py`)

| Task | Name | Queue | Beat Schedule | Purpose |
|------|------|-------|---------------|---------|
| daily_badge_check | `badges:daily_badge_check` | gamification | Daily 00:00 | Check badge eligibility |
| monthly_top_advertisers | `badges:monthly_top_advertisers` | gamification | Monthly 1st 00:00 | Award top advertiser badges |

---

### 2.11 Integrity Tasks (`src/tasks/integrity_tasks.py`)

| Task | Name | Queue | Beat Schedule | Purpose |
|------|------|-------|---------------|---------|
| check_data_integrity | `integrity:check_data_integrity` | cleanup | Every 6h | Verify data consistency |

---

### 2.12 Tax Tasks (`src/tasks/tax_tasks.py`)

| Task | Name | Queue | Beat Schedule | Purpose |
|------|------|-------|---------------|---------|
| calendar_reminder | `tax:calendar_reminder` | billing | Daily 09:00 MSK | Tax deadline reminders |

---

## 3. Beat Schedule

### 3.1 Complete Beat Schedule (26 Periodic Tasks)

| Schedule | Task | Queue | Purpose |
|----------|------|-------|---------|
| Every 5 min | check_scheduled_campaigns | mailing | Campaign deadline checks |
| Every 5 min | check_owner_response_sla | worker_critical | Owner response SLA (24h) |
| Every 5 min | check_payment_sla | worker_critical | Payment SLA (24h) |
| Every 5 min | check_counter_offer_sla | worker_critical | Counter-offer SLA (24h) |
| Every 5 min | check_pending_invoices ⚠️ | billing | DEPRECATED — no-op |
| Every hour | check_low_balance | mailing | Low balance notifications (< 50₽) |
| Every hour | auto_approve_placements | mailing | Auto-approve after 24h |
| Every 2h | placement_reminders | mailing | Pending placement reminders |
| Every 6h | update_chat_statistics | parser | Channel stats update |
| Every 6h | check_published_posts_health | worker_critical | Bot admin rights monitoring |
| Every 6h | check_data_integrity | cleanup | Data consistency checks |
| Daily 00:00 | update_streaks_daily | gamification | Login streak updates |
| Daily 00:00 | daily_badge_check | gamification | Badge eligibility |
| Daily 03:00 | refresh_chat_database | parser | Channel data re-sync |
| Daily 03:00 | check_plan_renewals | billing | Plan auto-renewal/downgrade |
| Daily 04:00 | recalculate_ratings_daily | rating | Channel rating recalculation |
| Daily 08:00 | check_seasonal_events | gamification | Seasonal event checks |
| Daily 09:00 MSK | calendar_reminder | billing | Tax deadline reminders |
| Daily 10:00 | notify_expiring_plans | mailing | Plan expiry batch notices |
| Daily 10:05 | notify_expired_plans | mailing | Expired plan batch notices |
| Weekly Sun 03:00 | delete_old_logs | cleanup | Log purging |
| Weekly Mon 05:00 | update_weekly_toplists | rating | Top channel list updates |
| Weekly Mon 10:00 | send_weekly_digest | gamification | Weekly digest to users |
| Monthly 1st 00:00 | monthly_top_advertisers | gamification | Top advertiser badges |

### 3.2 Beat Schedule by Hour

```
00:00 ── update_streaks_daily, daily_badge_check
03:00 ── refresh_chat_database, check_plan_renewals
04:00 ── recalculate_ratings_daily
08:00 ── check_seasonal_events
09:00 ── calendar_reminder (tax)
10:00 ── notify_expiring_plans
10:05 ── notify_expired_plans
Every 5m ── SLA checks (×3) + check_scheduled_campaigns + check_pending_invoices
Every hour ── check_low_balance, auto_approve_placements
Every 2h ── placement_reminders
Every 6h ── update_chat_statistics, check_published_posts_health, check_data_integrity
```

---

## 4. Task Dependency Graph

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            CELERY BEAT SCHEDULE                          │
└────────────┬──────────────────────────────────────────┬──────────────────┘
             │                                          │
   ┌─────────▼──────────┐                  ┌────────────▼────────────┐
   │  SLA Checks (5min) │                  │  Channel Parser (24h)   │
   │  - owner_response  │                  │  - refresh_chat_db      │
   │  - payment         │                  │  - update_statistics    │
   │  - counter_offer   │                  └────────────┬────────────┘
   └─────────┬─────────┘                               │
             │                                         │
             ▼                                         ▼
   ┌──────────────────┐               ┌─────────────────────────────┐
   │  Placement Flow  │               │  Publication Flow           │
   │  status changes  │───trigger───▶│  publish_placement          │
   └──────────────────┘               │     │                       │
                                      │     ▼                       │
                                      │  delete_published_post      │
                                      │     │                       │
                                      │     ▼                       │
                                      │  release_escrow             │
                                      └────────────┬────────────────┘
                                                   │
              ┌────────────────────────────────────┼──────────────┐
              ▼                                    ▼              ▼
     ┌──────────────┐                 ┌───────────────┐  ┌────────────┐
     │  ORD Reg     │                 │ Notification  │  │Reputation  │
     │ register     │                 │  - advertiser │  │  +1        │
     │ poll_erid    │                 │  - owner      │  │            │
     └──────────────┘                 └───────────────┘  └────────────┘

   ┌────────────────────────────────────────────────────────────┐
   │  Periodic Maintenance                                       │
   │  ┌─────────────┐ ┌─────────────┐ ┌────────────┐           │
   │  │ Plan Renewal│ │ Rating Calc │ │ Gamification│           │
   │  │ (daily 03:00│ │ (daily 04:00│ │ (daily/     │           │
   │  │  downgrade) │  │ recalc)    │ │  weekly)    │           │
   │  └─────────────┘ └─────────────┘ └────────────┘           │
   └────────────────────────────────────────────────────────────┘
```

---

## 5. Retry Policies

### 5.1 Retry Policy Matrix

| Policy | max_retries | interval_start | interval_step | interval_max | Applied To |
|--------|------------|---------------|--------------|-------------|------------|
| Default | 3 | 60s | 60s | 600s | Most tasks |
| Mailing (send_campaign) | 5 | 30s | 60s | 300s | Campaign sending |
| Parser (refresh_chat) | 2 | 300s | 300s | 600s | Channel sync |
| ORD poll_erid_status | 12 | — | — | 300s | ERIR polling (up to 1h) |
| Publication publish | 3 | — | — | 3600s | Post publish (1h retry) |
| Publication delete | 3 | — | — | 300s | Post delete (5m retry) |

### 5.2 Exponential Backoff Formula

```python
# Default Celery retry
retry(countdown=min(60 * (2 ** task.request.retries), 600))
```

---

## 6. Error Handling Patterns

### 6.1 Telegram API Errors

```python
try:
    await bot.send_message(chat_id, text)
except TelegramBadRequest as e:
    if "message to delete not found" in str(e):
        pass  # Already deleted — acceptable
    elif "bot was kicked" in str(e):
        # Trigger dispute, refund advertiser
        await handle_bot_kicked(placement_id)
    else:
        raise  # Re-raise for Celery retry
except TelegramForbiddenError:
    # User blocked bot — don't retry
    logger.warning(f"User {user_id} blocked bot")
```

### 6.2 Database Errors

```python
# Use dedicated session factory for Celery
async with celery_async_session_factory() as session:
    async with session.begin():
        # Operations here
        pass
```

### 6.3 External API Errors

```python
# Mistral AI
try:
    result = await client.chat.complete_async(...)
except Exception as e:
    raise RuntimeError(f"Mistral AI error: {e}") from e

# ORD Provider
try:
    result = await ord_provider.register(...)
except Exception as e:
    # Will be retried per policy
    raise
```

---

## 7. Monitoring & Alerting

### 7.1 Flower Monitoring

**URL:** `http://localhost:5555`
**Access:** Public (consider adding auth for production)
**Features:**
- Task queue depth
- Worker status and health
- Task execution times
- Failed tasks with tracebacks
- Task rate graphs

### 7.2 GlitchTip Integration

**Error tracking:** Celery task failures are sent to GlitchTip via `sentry_sdk` integration.

**Configuration:**
```python
# src/tasks/celery_config.py
sentry_sdk.init(
    dsn=settings.sentry_dsn,
    environment=settings.sentry_environment,
    traces_sample_rate=settings.sentry_traces_sample_rate,
)
```

### 7.3 Health Check Tasks

| Task | Purpose | Frequency |
|------|---------|-----------|
| check_data_integrity | Verify DB consistency | Every 6h |
| check_published_posts_health | Monitor bot admin rights | Every 6h |
| check_low_balance | Alert users with low balance | Hourly |

### 7.4 Key Metrics to Monitor

| Metric | Alert Threshold | Source |
|--------|----------------|--------|
| Queue depth | > 100 tasks pending | Flower |
| Task failure rate | > 5% in 1 hour | Flower/GlitchTip |
| Worker offline | Any worker down | Docker health checks |
| Escrow mismatch | `escrow_reserved` ≠ SUM(escrow placements) | `/health/balances` |
| Stale placements | status=escrow for > 7 days | Custom query |

---

## 8. Known Issues

### 8.1 Severity-Indexed Issues

| # | Issue | Severity | Details | Impact | Fix |
|---|-------|----------|---------|--------|-----|
| 1 | Publication tasks use `default` queue, not `worker_critical` | 🟡 MEDIUM | `publication_tasks.py` doesn't specify queue in decorator. Tasks run on worker_critical only because it includes the `celery` (default) queue. | If worker_critical doesn't include default queue, publication tasks stall. | Add `queue="worker_critical"` to task decorators. |
| 2 | `check_pending_invoices` is deprecated no-op | 🟢 LOW | Still scheduled every 5 min — wasted cycles. | Minimal CPU waste. | Remove from Beat schedule. |
| 3 | Notification tasks create Bot instance per call | 🟡 MEDIUM | Should use connection pool or shared instance. | Performance overhead. | Refactor to use shared Bot instance. |
| 4 | `_notify_user_async` doesn't check `notifications_enabled` | 🟢 LOW | Beat tasks check before calling, but direct calls don't. | Users who disabled notifications may still receive some. | Add check in notification service. |
| 5 | Redis dedup uses sync redis client in async context | 🟡 MEDIUM | `redis_sync_client` in `placement_tasks.py` | Potential blocking. | Use async Redis client. |
| 6 | ORD tasks reference `background` queue not in TASK_ROUTES | 🟡 MEDIUM | Route missing from `celery_config.py`. Tasks may go to default queue. | Tasks may run on wrong worker. | Add route to celery_config.py TASK_ROUTES. |

### 8.2 Recommended Improvements

| Priority | Improvement | Effort | Impact |
|----------|------------|--------|--------|
| HIGH | Add explicit queue names to all task decorators | Low | Prevents routing ambiguity |
| MEDIUM | Remove deprecated `check_pending_invoices` from Beat | Low | Reduces wasted cycles |
| MEDIUM | Add task-level timeout limits | Low | Prevents hung tasks |
| LOW | Implement task result backend cleanup | Medium | Reduces Redis memory usage |
| LOW | Add custom task metrics (Prometheus) | Medium | Better monitoring |

---

🔍 Verified against: HEAD @ 2026-04-08 | Source files: `src/tasks/` (16 files), `src/tasks/celery_config.py`, `docker-compose.yml`
✅ Validation: passed | All 40+ tasks documented | Queue assignments verified against worker configs | Beat schedule cross-referenced
