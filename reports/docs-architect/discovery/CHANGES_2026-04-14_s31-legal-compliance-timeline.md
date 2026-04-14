# S-31 Legal Compliance Timeline — Discovery Report

> **Date:** 2026-04-14
> **Branch:** `feature/s-31-legal-compliance-timeline`
> **Commits:** 6
> **Status:** Sprint complete

---

## Summary

S-31 implements the Legal Compliance Timeline — a cross-cutting feature that exposes ORD registration, Act signing, and Contract signing events as a unified chronological timeline in both Web Portal and Mini App placement detail screens. It also adds a critical ERID-before-publication guard per ФЗ-38.

---

## Changes by Commit

### 1. `01fcd91` — `feat(backend): add require_verified_legal_profile dependency and ContractRepo.list_by_placement`

**Files:**
- `src/api/dependencies.py` — Added `require_verified_legal_profile()` async dependency
- `src/db/repositories/contract_repo.py` — Added `list_by_placement(placement_request_id)` method

**Business Impact:**
- 3-level verification guard: profile exists → `is_completed` → `is_verified`
- Returns 403 with structured `{code, message, redirect}` detail object
- Enables legal profile verification before any compliance-sensitive API endpoint

**API Contract Change:**
- New dependency: `require_verified_legal_profile` → `LegalProfile`
- New repo method: `ContractRepo.list_by_placement(placement_request_id: int) → list[Contract]`

---

### 2. `9f0e42f` — `feat(backend): add by-placement endpoints for acts and contracts with legal profile guard`

**Files:**
- `src/api/schemas/act.py` — **Created**: `ActResponse` (uses `sign_status` field, NOT `status`), `ActListResponse`
- `src/api/routers/acts.py` — Added `GET /api/acts/by-placement/{placement_request_id}`
- `src/api/routers/contracts.py` — Added `GET /api/contracts/by-placement/{placement_request_id}`

**Business Impact:**
- Both endpoints require verified legal profile (dependency fires BEFORE participant check)
- Participant check: `current_user.id in {placement.advertiser_id, placement.owner_id}`
- Uses existing repo methods: `list_by_placement_request()` for acts, `list_by_placement()` for contracts

**API Contract:**
- `GET /api/acts/by-placement/{id}` → `ActListResponse` (items: ActResponse[], total: int)
- `GET /api/contracts/by-placement/{id}` → `list[ContractResponse]`
- Auth: `get_current_user` + `require_verified_legal_profile`

---

### 3. `3dd7df9` — `feat(web-portal): add TimelineEvent types and acts/contracts API clients`

**Files:**
- `web_portal/src/lib/timeline.types.ts` — **Created**: `TimelineEvent`, `TimelineEventStatus` (5 values), `TimelineEventType` (4 values)
- `mini_app/src/lib/timeline.types.ts` — **Created**: Identical timeline types
- `web_portal/src/api/acts.ts` — **Created**: `Act` interface, `ActListResponse`, 5 API functions
- `web_portal/src/api/contracts.ts` — **Created**: `ContractListResponse`, `getContractsByPlacement`
- `.gitignore` — Fixed: added negation rules for `mini_app/src/lib/` and `web_portal/src/lib/`

---

### 4. `1d2727d` — `fix(web-portal): replace OrdStatus hardcode with useOrdStatus hook, handle all 5 ord states`

**File:** `web_portal/src/screens/advertiser/OrdStatus.tsx`

**Changes:**
- Replaced hardcoded "⏳ Ожидает регистрации" with `useOrdStatus` hook
- All 5 `ord_status` values: `pending`, `registered` (was missing!), `token_received`, `reported`, `failed`
- ERID displayed in UI — zero `console.log` calls
- Loading/error states added

---

### 5. `3bac7b9` — `feat(tasks): add ERID check before publication — block + notify admins per ФЗ-38`

**Files:**
- `src/db/models/placement_request.py` — Added `ord_blocked = "ord_blocked"` to `PlacementStatus` enum
- `src/tasks/placement_tasks.py` — ERID check in `_publish_placement_async()`

**Business Impact:**
- Before publication, queries `OrdRegistration` by `placement_request_id`
- Allowed statuses: `token_received`, `registered`, `reported`, `erir_confirmed`
- If not allowed → sets `placement.status = "ord_blocked"`, notifies ALL admins via bot, blocks publication
- Admin notification includes: placement ID, advertiser ID, owner ID, ORD status, ERID value

**Flow:**
```
placement.status == 'escrow'
    → message_id check (dedup)
    → ERID CHECK (ФЗ-38)
        → YES: proceed with publication
        → NO:  status = 'ord_blocked' + notify admins
```

---

### 6. `32d8c2f` — `feat(api-client): throw structured error for legal_profile_* 403 responses in Mini App client`

**File:** `mini_app/src/api/client.ts`

**Changes:**
- Added 403 handler in `afterResponse` hook
- Throws structured `Error` with `.detail` property for `legal_profile_*` codes
- Web portal client (`web_portal/src/shared/api/client.ts`) already had this from prior session
- No `useToast`/`showToast` called in ky client (hook limitation — structured error thrown instead)

---

## Pre-existing Work (from Prior Session)

The following files were already implemented before this session:

| File | Status |
|------|--------|
| `web_portal/src/lib/timeline.ts` | Already had all 4 exports: `deriveOrdTimelineEvents`, `deriveActTimelineEvents`, `deriveContractTimelineEvents`, `mergeAndSortTimelineEvents` |
| `web_portal/src/screens/advertiser/campaign/CampaignWaiting.tsx` | Already had imports, queries, complianceEvents, and JSX section |
| `web_portal/src/screens/owner/OwnRequestDetail.tsx` | Already had imports, queries, complianceEvents, and JSX section |
| `web_portal/src/shared/api/client.ts` | Already had 403 interceptor |

**Only missing piece was:** Mini App client 403 interceptor — added in commit `32d8c2f`.

---

## API Endpoints Added

| Method | Path | Auth | Response |
|--------|------|------|----------|
| `GET` | `/api/acts/by-placement/{placement_request_id}` | `get_current_user` + `require_verified_legal_profile` | `ActListResponse` |
| `GET` | `/api/contracts/by-placement/{placement_request_id}` | `get_current_user` + `require_verified_legal_profile` | `list[ContractResponse]` |

---

## New Types / Enums

### Python
- `PlacementStatus.ord_blocked` — New status for ERID-blocked publications

### TypeScript
- `TimelineEventStatus`: `'default' | 'warning' | 'success' | 'danger' | 'info'`
- `TimelineEventType`: `'placement' | 'ord' | 'act' | 'contract'`
- `TimelineEvent`: `{ id, type, label, status, timestamp, metadata? }`
- `Act`: `{ id, placement_request_id, act_number, sign_status, pdf_file_path, signed_at, created_at }`

---

## Security Notes

- `ord_token` (ERID) is displayed in UI but NEVER logged to console
- 403 interceptor throws structured error — components handle toast notification
- Legal profile verification uses lazy import to avoid circular dependencies
- Admin notifications contain ERID value for manual intervention

---

## Verification Results

| Check | Result |
|-------|--------|
| `registered` in timeline.ts | ✅ 1 match |
| `advertiser_framework` in timeline.ts | ✅ 0 matches (does not exist) |
| `console.log(ord_token)` | ✅ 0 matches |
| `sign_status` in timeline.ts | ✅ 1 match (act.sign_status) |
| `legal_profile_` in web_portal client | ✅ 2 matches |
| `legal_profile_` in mini_app client | ✅ 2 matches |
| `showToast/useToast` in ky clients | ✅ 0 matches (hook limitation respected) |
| TSC web_portal | ✅ 0 new errors |
| TSC mini_app | ✅ 0 new errors |

---

## Migration Notes

No database migration required. The `ord_blocked` status is a new enum value in `PlacementStatus` — SQLAlchemy handles it as a new string value without schema change.

---

🔍 Verified against: `32d8c2f` | 📅 Updated: `2026-04-14T18:30:00Z`
