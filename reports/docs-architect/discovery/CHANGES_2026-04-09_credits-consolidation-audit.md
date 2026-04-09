# S-29: Credits → Balance Rub Consolidation — Discovery Report

> **Date:** 2026-04-09
> **Author:** Prompt Orchestrator
> **Status:** Research complete, ready for implementation sprint

---

## Executive Summary

The RekHarborBot project operates a **dual-currency system** where `credits` (internal integer currency, 1:1 with rubles) is used for plan purchases, gamification rewards, and referral bonuses, while `balance_rub` (Decimal) is used for campaign placements and top-ups.

This audit found **176 references to `credits`** across **49 files** in the backend, frontend, and tests. The conversion rate is `credits_per_rub_for_plan = 1.0` (1:1), meaning the dual-currency system adds complexity with zero financial benefit.

**Goal:** Remove `credits` entirely. All transactions use `balance_rub` (rubles) as the single currency.

---

## Scope

| Category | Files | References |
|----------|-------|-----------|
| Database Models | 3 | 3 columns |
| Repositories | 1 | 1 method |
| Services | 4 | 38 references |
| Celery Tasks | 4 | 12 references |
| API Routers | 8 | 36 references |
| Bot Handlers | 2 | 7 references |
| Constants/Settings | 3 | 11 references |
| Frontend (Mini App) | 8 | 26 references |
| Frontend (Web Portal) | 7 | 11 references |
| Tests | 7 | 21 references |
| Migrations | 2 | 3 references |
| **Total** | **49** | **176** |

---

## Key Architectural Decisions

1. **`credits_buy` enum value**: KEPT (deprecated) for historical transaction records. New type `plan_purchase` added for future plan payments.
2. **Badge `credits_reward`**: Column dropped, all rewards zeroed. XP rewards remain.
3. **Data migration**: `UPDATE users SET balance_rub = balance_rub + credits` before dropping column.
4. **API compatibility**: `/billing/credits` endpoint removed. Plan purchase endpoint modified to use `balance_rub`.
5. **No feature parity loss**: The `buy_credits_for_plan()` intermediate step is eliminated entirely — users pay for plans directly from ruble balance.

---

## Sprint Structure

| Phase | Task | Agent | Est. Effort |
|-------|------|-------|------------|
| S-29.1 | Models, Repos, Migration | @backend-core | 1-2 days |
| S-29.2 | Services & Celery Tasks | @backend-core | 2 days |
| S-29.3 | API Routers & Bot Handlers | @backend-core | 1 day |
| S-29.4 | Frontend + Tests | @frontend-miniapp + @qa-analysis | 2 days |
| **Total** | | | **6-7 days** |

---

## Risk Matrix

| Level | Count | Description |
|-------|-------|-------------|
| 🔴 Critical | 5 | Data loss, plan purchase flow, plan renewal, YooKassa webhook, activate_plan |
| 🟡 Medium | 4 | API contract changes, transaction type history, notification messages, badge seed data |
| 🟢 Low | 3 | Admin UI, test fixtures, landing page (already clean) |

---

## Files Modified: 49
## Files Untouched: 22+ (confirmed clean)
## Breaking Changes: API schema changes on 6 endpoints
## Rollback: Full DB backup required pre-migration

---

🔍 Verified against: commit $(git rev-parse HEAD) | 📅 Updated: 2026-04-09T12:00:00Z
