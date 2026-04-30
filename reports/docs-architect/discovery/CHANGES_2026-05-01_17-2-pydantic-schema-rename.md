# CHANGES — 17.2 Commit 3: Pydantic schema + handler rename (admin grant)

**Date:** 2026-05-01
**Branch:** feat/17-2-clean-sweep-persisted-credits
**Series:** 17.x (BL-053 umbrella)
**Closes:** Category C internal of 17.2 (per `PHASE_17_2_RESEARCH_2026-05-01.md`).

## Summary

Rename the admin platform-credit endpoint's Pydantic request schema and handler function to align with the renamed enum value (`admin_credit` → `admin_grant`, Commit 2). URL path **deliberately preserved** — atomic URL rename is series 17.3 scope (bundles with FE deploy).

## Changes

| Old | New | Site |
|---|---|---|
| `class PlatformCreditRequest(BaseModel)` | `class AdminGrantRequest(BaseModel)` | `src/api/routers/admin.py:827` |
| `async def create_platform_credit(...)` | `async def create_admin_grant(...)` | `src/api/routers/admin.py:840` |
| `body: PlatformCreditRequest` (handler param) | `body: AdminGrantRequest` | `src/api/routers/admin.py:841` |
| URL `@router.post("/credits/platform-credit", ...)` | unchanged (defer 17.3) | `src/api/routers/admin.py:833-834` |
| `BillingService.admin_credit_from_platform()` (method name) | unchanged (banking-verb defensible per inventory §13.2) | `src/api/routers/admin.py:855` (call site) |

## Files touched

- `src/api/routers/admin.py` — 1 class def + 1 function def + 1 type annotation = 3 sites in one Edit operation.

## Public contract impact

- OpenAPI `components.schemas` key changes: `PlatformCreditRequest` → `AdminGrantRequest`.
- OpenAPI default `operation_id` changes: `create_platform_credit` → `create_admin_grant`.
- Wire format (request/response body field names) **unchanged**.
- URL path **unchanged** (`POST /api/admin/credits/platform-credit`).
- FE: `web_portal/src/api/admin.ts` uses hand-coded TS interfaces (`PlatformCreditResponse`, etc.) — independent of backend Pydantic class names. No FE breakage. TS interface renames are an optional 17.3 follow-up.

## Verification

- `grep 'PlatformCreditRequest\|create_platform_credit'` against `src/` → 0 matches.
- `grep 'AdminGrantRequest\|create_admin_grant'` against `src/api/routers/admin.py` → 3 matches (def + def + ref).
- FE files unchanged — `web_portal/src/api/admin.ts` `PlatformCreditResponse` interface preserved.

## Out of scope (deferred)

- URL path renames `/credits/platform-credit`, `/credits/gamification-bonus`, `/credits` → 17.3.
- FE TS interface renames (`BuyCreditsResponse`, `PlatformCreditResponse`, `GamificationBonusResponse`) → 17.3.
- `BillingService.admin_credit_from_platform()` method name → leave (banking-verb defensible per inventory).
- `User.credits` / `Badge.credits_reward` columns → future scope decision (inventory §13.2 wider envelope).

## Baseline impact

Public OpenAPI contract change: schema name + operation_id. CHANGELOG.md `[Unreleased]` updated with `### Changed` entry.

🔍 Verified against: HEAD prior to commit (post-Commit-2 = `10b4b62`) | 📅 Updated: 2026-05-01T00:00:00Z
