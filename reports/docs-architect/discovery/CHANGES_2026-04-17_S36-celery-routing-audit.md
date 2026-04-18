# CHANGES — S-36 Celery Task Routing Audit

**Date:** 2026-04-17 | **Sprint:** S-36 | **Mode:** read-only (no code modified)

## Affected files

| File | Action | Notes |
|------|--------|-------|
| `reports/docs-architect/discovery/S36_celery_routing_research_2026-04-17.md` | Created | Full routing audit report |

## Business logic impact

None — research only. No production code was modified.

## New/changed API / FSM / DB contracts

None.

## Key findings documented

- `celery_config.py` `BEAT_SCHEDULE` and `TASK_ROUTES` are dead code (not imported by `celery_app.py`)
- 6 critical placement SLA tasks (`check_owner_response_sla`, `check_payment_sla`, `check_counter_offer_sla`, `check_escrow_sla`, `check_escrow_stuck`, `check_published_posts_health`) are absent from the active Beat schedule — never run automatically
- 13 tasks (`dispute:*`, `gamification:*`, `badges:*`, `integrity:*`) route to default `celery` queue due to missing `queue=` and no matching route
- Active `task_routes` has only 4 entries; `publication.*` is a dead route
- `tax_tasks.py` contains no `@celery_app.task` decorators; referenced task `tax:calendar_reminder` is unimplemented
- 69 tasks inventoried across 10 modules with effective queue assignment for each

---

🔍 Verified against: d195386 | 📅 Updated: 2026-04-17T00:00:00Z
