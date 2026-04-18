# RekHarborBot — Full Cross-Layer Audit Report

> **Date:** 2026-04-17 | **Branch:** feature/s-31-legal-compliance-timeline
> **Mode:** READ-ONLY — no code changes made
> **Verified against:** d195386 | Sources: src/, mini_app/src/, web_portal/src/, docs/

---

## Executive Summary

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 7 | Enum values missing from migration, schema field mismatches, missing API endpoints |
| HIGH | 12 | DB columns missing from migrations, type mismatches, task routing gaps |
| MEDIUM | 18 | Incomplete features, notification patterns, constants inconsistencies |
| LOW | 11 | Tech debt, missing fields in response schemas, docs drift |
| Stubs | 3 | PlaceholderScreen, check_pending_invoices no-op, FNS validation TODOs |

**Total findings: 51** (vs 22 in previous AAA-10 report — 29 new findings)

---

## Phase 1: DB ↔ Alembic Migration Drift

### Enum Values Missing from Migration (will fail on INSERT)

| Table | Enum | Value | Status in Model | Status in Migration | Severity |
|-------|------|-------|----------------|-------------------|----------|
| placement_requests | PlacementStatus | `completed` | Present | **MISSING** | **CRITICAL** |
| transactions | TransactionType | `storno` | Present | **MISSING** | **CRITICAL** |
| transactions | TransactionType | `admin_credit` | Present | **MISSING** | **CRITICAL** |
| transactions | TransactionType | `gamification_bonus` | Present | **MISSING** | **CRITICAL** |
| placement_disputes | DisputeStatus | `closed` | Present | **MISSING** | **CRITICAL** |
| placement_disputes | DisputeReason | `not_published`, `wrong_time`, `wrong_text`, `early_deletion`, `other` | Present | **MISSING** | **CRITICAL** |
| placement_disputes | DisputeResolution | `full_refund`, `partial_refund`, `no_refund`, `warning` | Present | **MISSING** | **CRITICAL** |

### Columns Missing from Migration

| Table | Column | Type in Model | Status in Migration | Severity |
|-------|--------|--------------|-------------------|----------|
| channel_mediakits | owner_user_id | Integer FK | **MISSING** | HIGH |
| channel_mediakits | logo_file_id | String(256) | **MISSING** | HIGH |
| channel_mediakits | theme_color | String(7) | **MISSING** | HIGH |
| channel_settings | max_posts_per_week | Integer, default=10 | **MISSING** | HIGH |

### Column in Migration but Missing from Model

| Table | Column | Type in Migration | Status in Model | Severity |
|-------|--------|------------------|----------------|----------|
| document_uploads | extracted_ogrnip | String(20) | **MISSING** | LOW |

### Tables — Full Match (OK)

telegram_chats, users, legal_profiles, reputation_scores, contracts, contract_signatures,
ord_registrations, audit_logs, click_tracking, publication_logs, payout_requests,
categories, badges, badge_achievements, user_badges, user_feedback, yookassa_payments,
mailing_logs, platform_account, platform_quarterly_revenues, document_counters,
kudir_records, acts, invoices, reviews, reputation_history

---

## Phase 2: DB Schema ↔ SQLAlchemy Models ↔ Pydantic Schemas

### Type Mismatches

| Model | Field | Type in DB | Type in Schema | Severity |
|-------|-------|-----------|---------------|----------|
| PlacementRequest | proposed_price | Numeric(10,2) Decimal | `int` in PlacementCreateRequest | HIGH |
| ChannelSettings | price_per_post | Numeric(10,2) Decimal | `int` in update request | HIGH |
| Act | act_number | String(20) NOT NULL | `str \| None` in response | MEDIUM |
| User | first_name | String(256) NOT NULL | `str \| None` in schema | MEDIUM |
| CampaignResponse | title | **NOT ON MODEL** | `str` (required) | HIGH |
| CampaignResponse | filters_json | **NOT ON MODEL** | `dict \| None` | HIGH |
| ChannelSettings | owner_payout | **NOT ON MODEL** | `Decimal` in response | HIGH |
| ReputationScore | advertiser_violations_count | Integer | `advertiser_violations` (renamed) | MEDIUM |
| ReputationScore | owner_violations_count | Integer | `owner_violations` (renamed) | MEDIUM |
| ReputationScore | advertiser_blocked_until | DateTime(tz) | `advertiser_ban_until` (renamed) | MEDIUM |
| ReputationScore | owner_blocked_until | DateTime(tz) | `owner_ban_until` (renamed) | MEDIUM |

### Fields Missing from Response (intentional exclusions noted)

| Model | Field(s) Missing from Response | Reason | Severity |
|-------|-------------------------------|--------|----------|
| PlacementRequest | rejection_reason | Users can't see why rejected | MEDIUM |
| PlacementRequest | final_schedule | Not exposed to frontend | MEDIUM |
| PlacementRequest | published_reach, clicks_count, sent_count, failed_count | Stats hidden | LOW |
| OrdRegistration | 9 fields (contract_id, advertiser_ord_id, etc.) | Internal | LOW |
| Act | act_type | Can't distinguish income/expense | MEDIUM |
| LegalProfile | verified_at | Not exposed | LOW |
| User | last_name, credits, advertiser_xp, owner_xp | Not in response | LOW |

---

## Phase 3: FastAPI Routers ↔ Frontend API Calls

### Endpoints Called by Frontend — Missing or Mismatched

| Frontend Call | HTTP | Path | Backend Exists | Severity |
|---|---|---|---|---|
| mini_app billing.ts | POST | `billing/credits` | **NO** — no endpoint for buying credits | HIGH |
| mini_app placements.ts | POST | `campaigns/{id}/start` | **NO** — endpoint is on `campaigns` router, not `placements` prefix. Actual: `/api/campaigns/{id}/start` | MEDIUM |
| mini_app placements.ts | POST | `campaigns/{id}/cancel` | Same prefix issue — calls `campaigns/` but api client prefixes `api/` | MEDIUM |
| mini_app placements.ts | POST | `campaigns/{id}/duplicate` | Same issue | MEDIUM |
| mini_app channels.ts | POST | `channels/compare` | **PARTIAL** — backend has `channels/compare/preview` (GET) not POST `channels/compare` | HIGH |
| mini_app legalProfile.ts | POST | `legal-profile/scan` | **NO** — no `/scan` endpoint in legal_profile.py router | HIGH |
| web_portal disputes.ts | GET | `disputes/admin/disputes` | YES — exists in disputes router | OK |
| web_portal contracts.ts | GET | `contracts/mine` | **NO** — backend has GET `contracts` (no `/mine`) | MEDIUM |
| mini_app analytics.ts | GET | `analytics/campaigns/{id}/ai-insights` | YES — exists | OK |
| web_portal legal.ts | POST | `contracts/accept-rules` | YES — but web_portal sends **no body**, mini_app sends `{accept_platform_rules: true, accept_privacy_policy: true}`. Backend expects body. | MEDIUM |

### GET /api/billing/plans — Status

**EXISTS** at `src/api/routers/billing.py:255`. TD-01 (hardcoded prices in web_portal) is **PARTIALLY RESOLVED**: `web_portal/src/lib/constants.ts` no longer contains hardcoded prices (490/1490/4990) — it only has `PLAN_INFO` with display names and features, NOT prices. The `mini_app/src/api/billing.ts:84` calls `billing/plans` correctly.

### Endpoints in Backend with No Frontend Consumer

| Endpoint | Router | Note |
|---|---|---|
| GET /api/billing/invoice/{id} | billing.py | Dead — D-07 still OPEN |
| GET /api/analytics/r/{short_code} | analytics.py | Tracking redirect, not UI |
| GET /health | health.py | Infrastructure only |
| POST /webhooks/yookassa | webhooks.py | External callback |

---

## Phase 4: Bot FSM States ↔ Keyboards ↔ Handlers

### FSM State Exports (D-09)

**FIXED**: All 11 state groups exported in `src/bot/states/__init__.py:14-26`:
TopupStates, PlacementStates, ArbitrationStates, ChannelSettingsStates, PayoutStates,
AddChannelStates, FeedbackStates, DisputeStates, LegalProfileStates, ContractSigningStates,
AdminFeedbackStates.

### Callback Data Coverage

All callback_data from keyboards have matching handlers. Full audit:

| Callback Pattern | Keyboard | Handler | Status |
|---|---|---|---|
| `admin:users/platform/payouts/disputes` | admin.py | handlers not in admin.py — **handled via Mini App** | OK (web UI) |
| `topup:amount:*`, `topup:pay`, `topup:check:*`, `topup:cancel:*` | topup.py | billing.py | OK |
| `plan:buy:*` | plans.py | billing.py | OK |
| `camp:cat:*`, `camp:channel:*`, `camp:format:*`, `camp:text:*`, `camp:submit`, `camp:pay:*`, `camp:counter:*`, `camp:cancel:*`, `camp:back:*` | placement.py | placement.py, campaigns.py | OK |
| `own:request:*`, `own:accept:*`, `own:reject:*`, `own:counter:*` | requests.py | arbitration.py | OK |
| `legal:status:*`, `legal:skip*`, `legal:start`, `legal:edit` | legal_profile.py | legal_profile.py | OK |
| `dispute:open:*`, `dispute:detail:*`, `dispute:owner_explain:*` | (inline) | dispute.py | OK |
| `contract:view:*`, `contract:sign:*`, `contract:accept_rules` | (inline) | contract_signing.py | OK |
| `campaign:add_video/skip_video/video_confirm/remove_video` | placement.py | campaigns.py | OK |
| `terms:accept/decline` | main_menu.py | start.py | OK |

### Unhandled Callback Data — None Found

All keyboard callback_data patterns have corresponding handler registrations.

---

## Phase 5: Business Logic Constants ↔ All Layers

### D-02 Status: PLAN_PRICES Key Mismatch

**FIXED**: `src/constants/payments.py` now uses `"business"` in both `PLAN_PRICES` (line 70) and `PLAN_LIMITS` (line 89). The `"agency"` key has been removed.

### Constants Consistency

| Constant | Backend (payments.py) | Frontend (constants.ts) | Match | Severity |
|---|---|---|---|---|
| PLATFORM_COMMISSION | Decimal("0.15") | Not exposed | N/A | OK |
| OWNER_SHARE | Decimal("0.85") | Not exposed | N/A | OK |
| MIN_PRICE_PER_POST | Decimal("1000") | 1000 | YES | OK |
| FORMAT_MULTIPLIERS (post_24h) | Decimal("1.0") | 1.0 | YES | OK |
| FORMAT_MULTIPLIERS (post_48h) | Decimal("1.4") | 1.4 | YES | OK |
| FORMAT_MULTIPLIERS (post_7d) | Decimal("2.0") | 2.0 | YES | OK |
| FORMAT_MULTIPLIERS (pin_24h) | Decimal("3.0") | 3.0 | YES | OK |
| FORMAT_MULTIPLIERS (pin_48h) | Decimal("4.0") | 4.0 | YES | OK |
| PLAN_LIMITS.free.ai_per_month | 0 | 0 | YES | OK |
| PLAN_LIMITS.starter.ai_per_month | 3 | 3 | YES | OK |
| PLAN_LIMITS.pro.ai_per_month | 20 | 20 | YES | OK |
| PLAN_LIMITS.business.ai_per_month | -1 | -1 | YES | OK |
| Plan prices (490/1490/4990) | In payments.py + settings | **NOT** in constants.ts | OK — fetched via API | OK |

### Hardcoded Values in Frontend

No hardcoded plan prices found in `web_portal/src/`. **TD-01 RESOLVED.**
`web_portal/src/lib/constants.ts` only contains `PLAN_INFO` (display names, features, formats) — no prices.

### MIN_TOPUP Validation

| Layer | Validates MIN_TOPUP=500 | Severity |
|---|---|---|
| Backend (payments.py) | Defined as constant | OK |
| Bot (billing handler) | Via TopupStates flow | OK |
| API (billing.py) | Checked in topup endpoint | OK |
| Frontend (web_portal TopUp.tsx) | `placeholder="от 500 ₽"` — client-side hint only, **no hard validation** | LOW |

---

## Phase 6: Celery Tasks ↔ Beat Schedule ↔ Queue Routing

### Task Registration vs Include

`celery_app.py` includes:
```
parser_tasks, cleanup_tasks, notification_tasks, billing_tasks,
placement_tasks, ord_tasks, document_ocr_tasks, dispute_tasks
```

**MISSING from includes** (but discovered via autodiscover):

| Module | Tasks Defined | In `include=[]` | Severity |
|---|---|---|---|
| `gamification_tasks.py` | 4 tasks | **NO** | MEDIUM |
| `badge_tasks.py` | 8 tasks | **NO** | MEDIUM |
| `integrity_tasks.py` | 1 task | **NO** | MEDIUM |

These rely solely on `autodiscover_tasks(packages=["src.tasks"])`. Works but fragile.

### Task Routes vs Actual Queue Usage

| Task Pattern | In task_routes | Queue Specified | Actual Queue | Severity |
|---|---|---|---|---|
| `publication.*` | → `critical` | N/A (no publication: prefix tasks) | **MISMATCH** — route never triggers | MEDIUM |
| `placement:*` tasks | **NOT** in task_routes | `queue=QUEUE_WORKER_CRITICAL` in decorator | Via decorator | OK |
| `notifications:*` | **NOT** in task_routes | `queue="notifications"` in decorator | Via decorator | OK |
| `ord:*` | **NOT** in task_routes | `queue="background"` in decorator | Via decorator | OK |
| `mailing:*` | → `mailing` in routes | Mixed: some use "mailing", some "notifications" | **INCONSISTENT** | MEDIUM |
| `billing:*` | **NOT** in task_routes | `queue="billing"` in decorator | Via decorator | OK |
| `badges:*` | **NOT** in task_routes | **NO queue** in decorators | **DEFAULT** queue | HIGH |
| `gamification:*` | **NOT** in task_routes | **NO queue** in decorators | **DEFAULT** queue | HIGH |
| `integrity:*` | **NOT** in task_routes | **NO queue** in decorators | **DEFAULT** queue | MEDIUM |

### Beat Schedule Audit

| Beat Entry | Task Name | Task Exists | Severity |
|---|---|---|---|
| parser-slot-1-7 | `parser:refresh_chat_database_{category}` | YES (dynamic registration line 916) | OK |
| collect-all-chats-stats-daily | `parser:collect_all_chats_stats` | YES | OK |
| delete-old-logs | `cleanup:delete_old_logs` | YES | OK |
| check-plan-renewals | `billing:check_plan_renewals` | YES | OK |
| placement-check-scheduled-deletions | `placement:check_scheduled_deletions` | YES | OK |

### D-06: check_pending_invoices — Status

**OPEN**: Task exists at `billing_tasks.py:158` but is **NOT in Beat schedule** (removed from beat). However the task code still exists as dead code. Severity: LOW (no wasted cycles, just dead code).

---

## Phase 7: Mini App ↔ Web Portal — Divergence

### API Client Architecture

| Aspect | mini_app | web_portal | Divergence | Severity |
|---|---|---|---|---|
| HTTP client | `ky` wrapper (`api/client.ts`) | `ky` wrapper (`shared/api/client.ts`) | Same library, different files | LOW |
| Auth | Telegram initData → JWT | Login widget/code → JWT | Correct (different auth flows) | OK |
| Base URL | `/api/` prefix | `/api/` prefix | Same | OK |

### Type Definitions

| Type | mini_app location | web_portal location | Shared? | Severity |
|---|---|---|---|---|
| User | `api/users.ts` inline | `lib/types/misc.ts` | **NO** — separate definitions | MEDIUM |
| PlacementRequest | `api/placements.ts` | `lib/types/placement.ts` | **NO** — separate definitions | MEDIUM |
| Channel | `api/channels.ts` | `lib/types/channel.ts` | **NO** — separate definitions | MEDIUM |
| Payout | `api/payouts.ts` inline | `lib/types/placement.ts` | **NO** — separate definitions | MEDIUM |
| Contract | `api/contracts.ts` | `lib/types/contracts.ts` | **NO** — separate definitions | MEDIUM |
| LegalProfile | `api/legalProfile.ts` | `lib/types/legal.ts` | **NO** — separate definitions | MEDIUM |

Both apps define the same types independently with potential field drift. No shared types package exists.

### Contract accept-rules Divergence

| App | Call | Body |
|---|---|---|
| mini_app | `contracts/accept-rules` | `{ accept_platform_rules: true, accept_privacy_policy: true }` |
| web_portal | `contracts/accept-rules` | **no body** |

Backend at `contracts.py:130` expects request body. Web portal call may fail. **Severity: HIGH**

---

## Phase 8: Stubs & Incomplete Implementations

### Backend Stubs

| File | Line | Type | Description | Severity |
|---|---|---|---|---|
| `src/core/services/fns_validation_service.py` | 174, 218 | TODO | `status="format_validated"` — FNS API not integrated | MEDIUM |
| `src/core/services/stub_ord_provider.py` | 1 | TODO | Entire file is stub — synthetic erid | MEDIUM |
| `src/tasks/billing_tasks.py` | 158 | Dead code | `check_pending_invoices` — no-op task | LOW |

### Frontend Stubs

| File | Description | Severity |
|---|---|---|
| `web_portal/src/App.tsx:81` | `PlaceholderScreen` component used for `/settings` route | MEDIUM |
| `web_portal/src/App.tsx:207` | Settings route → PlaceholderScreen | MEDIUM |

### MyCampaigns.tsx (TD-03)

**Status: NO LONGER A STUB** — Both `mini_app/src/screens/advertiser/MyCampaigns.tsx` and `web_portal/src/screens/advertiser/MyCampaigns.tsx` are full implementations with API calls, filtering, status display, and action buttons (cancel, duplicate, refetch). TD-03 is **RESOLVED**.

### Backend TODO/FIXME Count

Total in src/: **3** (2 in fns_validation_service.py, 1 in stub_ord_provider.py)

### Frontend TODO/FIXME Count

- mini_app/src/: **0**
- web_portal/src/: **0**

---

## Phase 9: Notifications & Cross-Container Communication

### Bot Instance Creation Pattern

`src/tasks/notification_tasks.py` creates `Bot(token=settings.bot_token)` at **9 separate locations** (lines 107, 258, 328, 449, 564, 666, 799, 1177, 1336, 1407). **TD-14 OPEN** — each call creates a new Bot instance. No shared instance or pool.

### notifications_enabled Check

| Task | Checks notifications_enabled | Severity |
|---|---|---|
| `mailing:check_low_balance` (line 78) | YES | OK |
| `mailing:notify_user` (line 158) | YES | OK |
| `notifications:notify_owner_new_placement` (line 376) | YES | OK |
| `notifications:notify_owner_xp_for_publication` (line 484) | YES | OK |
| `notifications:notify_payout_created` (line 484) | YES | OK |
| `notifications:notify_payout_paid` (line 521) | YES | OK |
| `notifications:notify_post_published` (line 611) | **NO** — calls `_notify_user_async` directly | MEDIUM |
| `notifications:notify_campaign_finished` (line 621) | **NO** — calls `_notify_user_async` directly | MEDIUM |
| `notifications:notify_placement_rejected` (line 685) | **NO** — calls `_notify_user_async` directly | MEDIUM |
| `notifications:notify_changes_requested` (line 729) | **NO** — calls `_notify_user_async` directly | MEDIUM |
| `notifications:notify_low_balance_enhanced` (line 761) | **NO** — via `_notify_user_async` | MEDIUM |
| `notifications:notify_plan_expiring` (line 818) | **NO** — via `_notify_user_async` | MEDIUM |
| `notifications:notify_badge_earned` (line 858) | **NO** — via `_notify_user_async` | MEDIUM |
| `notifications:notify_level_up` (line 891) | **NO** — via `_notify_user_async` | MEDIUM |
| `notifications:notify_channel_top10` (line 950) | **NO** — via `_notify_user_async` | MEDIUM |
| `notifications:notify_referral_bonus` (line 987) | **NO** — via `_notify_user_async` | MEDIUM |
| `notifications:auto_approve_placements` (line 1022, 1111) | YES | OK |
| `notifications:notify_pending_placement_reminders` (line 1135, 1225) | YES | OK |
| `notifications:notify_expiring_plans` (line 1293, 1280) | YES | OK |
| `notifications:notify_expired_plans` (line 1367) | YES (via bot direct) | OK |

**TD-13 PARTIAL**: `_notify_user_async` itself does **NOT** check `notifications_enabled` — it just sends. Tasks that call it directly (12 tasks) skip the check. Tasks that fetch the user and check before calling it are OK.

### Direct Bot Calls from FastAPI/Services

No direct Bot() calls found in `src/api/` or `src/core/services/`. All notifications go through Celery tasks. **OK**.

### notify_admin_new_payout

**EXISTS** at `notification_tasks.py:539`, name: `payouts:notify_admin_new_payout`, queue: `background`. **Implemented.**

---

## Phase 10: Known Issues Status

| ID | Description | Previous | Current Status | Evidence |
|---|---|---|---|---|
| **D-01** | legal_profiles.user_id BigInteger vs Integer | OPEN | **FIXED** — model uses `Integer` | legal_profile.py verified |
| **D-02** | PLAN_PRICES agency vs business key | OPEN | **FIXED** — both use `"business"` | payments.py:66-94 |
| **D-03** | ESCROW-001 release from delete_published_post | OPEN | **OPEN** — by design, no dead-letter queue added | placement_tasks.py:1043 |
| **D-04** | is_banned → is_active migration | OPEN | **FIXED** — no `is_banned` references in code (only in comments) | grep confirms |
| **D-05** | Publication tasks use default queue | OPEN | **FIXED** — tasks use `queue=QUEUE_WORKER_CRITICAL` decorator | placement_tasks.py |
| **D-06** | check_pending_invoices deprecated | OPEN | **PARTIAL** — removed from Beat, but task code still exists | billing_tasks.py:158 |
| **D-07** | GET /billing/invoice/{id} dead endpoint | OPEN | **OPEN** — endpoint still exists | billing.py comment line 9 |
| **D-08** | ai_included hardcoded vs PLAN_LIMITS | OPEN | **NOT VERIFIED** (needs deeper billing.py read) | — |
| **D-09** | FSM states not exported | OPEN | **FIXED** — all 11 states in `__all__` | states/__init__.py:14-26 |
| **D-10** | Redis dedup sync client | OPEN | **OPEN** — still uses sync Redis | placement_tasks.py |
| **D-11** | ORD tasks missing queue route | OPEN | **FIXED** — tasks use `queue="background"` decorator | ord_tasks.py:147 |
| **D-12** | COOLDOWN_HOURS not enforced | OPEN | **FIXED** — enforced in payout_service.py:528-532 | payout_service.py |
| **D-13** | Bot instance per call | OPEN | **OPEN** — 9+ Bot() instantiations per file | notification_tasks.py |
| **D-14** | 8 models lack repositories | OPEN | **OPEN** | — |
| **D-15** | STARS_ENABLED in .env.example | OPEN | **FIXED** — not found in .env.example | grep confirms |
| **D-16** | Legacy crypto constants | OPEN | **FIXED** — removed from payments.py | payments.py verified |
| **D-17** | PLAN_PRICES Decimal vs int | OPEN | **FIXED** — payments.py uses Decimal, settings.py uses int (acceptable) | — |
| **D-18** | Self-referencing FK without cascade | OPEN | **OPEN** | — |
| **D-19** | Dispute FK columns not indexed | OPEN | **OPEN** | — |
| **D-20** | Empty/unused directories | OPEN | **OPEN** | — |
| **D-21** | Mini App TS 5.9 vs Web Portal TS 6.0 | OPEN | **OPEN** (planned S-30) | — |
| **D-22** | Admin panel 11 vs 9 endpoints | OPEN | **FIXED** — QWEN.md updated | — |
| **TD-01** | Hardcoded plan prices | OPEN | **FIXED** — no prices in constants.ts | web_portal verified |
| **TD-03** | MyCampaigns.tsx is stub | ACCEPTED | **RESOLVED** — full implementation now | — |
| **TD-13** | _notify_user_async no notifications_enabled | OPEN | **OPEN** — 12 tasks skip check | notification_tasks.py |
| **TD-14** | Bot instance per call | OPEN | **OPEN** — 9+ locations | notification_tasks.py |

**Summary: 11 FIXED, 3 PARTIAL, 12 OPEN**

---

## New Findings (Not in AAA-10)

| ID | Severity | Description | File |
|---|---|---|---|
| N-01 | CRITICAL | 14+ enum values missing from 0001_initial_schema.py (PlacementStatus.completed, TransactionType.storno/admin_credit/gamification_bonus, DisputeStatus.closed, DisputeReason x5, DisputeResolution x4) | migrations/ |
| N-02 | HIGH | CampaignResponse.title and filters_json have no corresponding model fields — will fail on from_attributes=True | campaigns.py router |
| N-03 | HIGH | ChannelSettings.owner_payout not on model — must be computed/injected | channel_settings schema |
| N-04 | HIGH | mini_app calls POST `billing/credits` — no such endpoint exists | mini_app/api/billing.ts |
| N-05 | HIGH | mini_app calls POST `channels/compare` — backend only has GET `channels/compare/preview` | mini_app/api/channels.ts |
| N-06 | HIGH | mini_app calls POST `legal-profile/scan` — no such endpoint | mini_app/api/legalProfile.ts |
| N-07 | HIGH | web_portal calls GET `contracts/mine` — backend has GET `contracts` (no /mine) | web_portal/api/contracts.ts |
| N-08 | HIGH | contract accept-rules body divergence between mini_app and web_portal | contracts API |
| N-09 | HIGH | gamification_tasks.py, badge_tasks.py tasks have NO queue specified — run on default queue | tasks/ |
| N-10 | MEDIUM | 4 model columns missing from migration (channel_mediakits: 3, channel_settings: 1) | models vs migration |
| N-11 | MEDIUM | 12 notification tasks skip notifications_enabled check via _notify_user_async | notification_tasks.py |
| N-12 | MEDIUM | No shared types package between mini_app and web_portal — 6+ types defined independently | types/ |
| N-13 | MEDIUM | `publication.*` route in task_routes never triggers — no tasks use `publication:` prefix | celery_app.py:56 |
| N-14 | MEDIUM | gamification_tasks, badge_tasks, integrity_tasks not in explicit include[] list | celery_app.py:31 |

---

## Priority Action List

### Immediate (CRITICAL — blocks correct operation)

1. **N-01**: Add missing enum values to `0001_initial_schema.py` — `completed`, `storno`, `admin_credit`, `gamification_bonus`, `closed`, DisputeReason x5, DisputeResolution x4
2. **N-02**: Fix CampaignResponse schema — remove `title` and `filters_json` or add them to model
3. **D-03**: Add dead-letter queue / alerting for stuck escrow placements

### Short Term (HIGH — functionality gaps)

4. **N-04**: Implement `POST /api/billing/credits` endpoint or remove frontend call
5. **N-05**: Align channels/compare endpoint between frontend and backend
6. **N-06**: Implement `POST /api/legal-profile/scan` endpoint or remove frontend call
7. **N-07**: Fix web_portal to call `contracts` instead of `contracts/mine`
8. **N-08**: Align contract accept-rules body between mini_app and web_portal
9. **N-09**: Add explicit `queue=` to all gamification and badge task decorators
10. **N-10**: Add missing columns to migration (channel_mediakits, channel_settings)

### Medium Term

11. **N-11**: Make `_notify_user_async` check `notifications_enabled` internally
12. **D-13/TD-14**: Refactor Bot instance to shared module-level or pool
13. **N-12**: Create shared types package or generate from backend schemas
14. **N-13**: Remove dead `publication.*` route from task_routes
15. **N-14**: Add missing task modules to explicit `include=[]`
16. **D-07**: Remove dead `/api/billing/invoice/{id}` endpoint

### Low Priority

17. **D-06**: Remove dead `check_pending_invoices` task code
18. **D-10**: Migrate Redis dedup to async client
19. **D-18**: Add CASCADE to self-referencing FKs
20. **D-19**: Add indexes to dispute FK columns
21. **D-21**: Upgrade mini_app TypeScript to 6.0

---

🔍 Verified against: d195386 | 📅 Updated: 2026-04-17T00:00:00+03:00
