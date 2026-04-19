# S-39a: Backend Pydantic Schema Completeness Audit

**Sprint:** S-39a (research, read-only)
**Date:** 2026-04-19
**Branch:** feature/s-38-escrow-recovery (post S-38 merge)

---

## Executive Summary

- **2 critical schemas are severely incomplete** relative to what frontend expects: `UserResponse` (users.py) and `PlacementResponse` — together missing 19 fields that the DB has and the frontend declares.
- **1 entity has a field name mismatch** (Payout): mini_app uses `amount/fee/payment_details` but backend returns `gross_amount/fee_amount/requisites`.
- **1 minor missing field** in `ChannelResponse`: `is_test` present in DB and frontend type, absent from Pydantic.
- **2 duplicate UserResponse schemas** exist (`auth.py` and `users.py`), each incomplete in different ways — the frontend needs a union of both.
- **0 ORM-leakage endpoints**: every entity endpoint either uses a return type annotation or `response_model=`, so FastAPI always filters through Pydantic. No phantom fields in JSON.
- **Recommended minimum fix for S-39b**: 9 fields added to `users.py::UserResponse` + 8 fields to `PlacementResponse` + 1 field to `ChannelResponse` + mini_app Payout field aliases. No breaking changes for any of these additions.

---

## Table 1: All Entity-Returning Endpoints

| Router | Method | Path | response_model param | Return type annotation | Return construction | Schema complete? |
|--------|--------|------|----------------------|------------------------|---------------------|-----------------|
| users | GET | `/api/users/me` | — | `UserResponse` | explicit `UserResponse(...)` | ❌ 9 fields missing |
| users | GET | `/api/users/me/stats` | — | `UserStatsResponse` | explicit `UserStatsResponse(...)` | ✅ |
| users | GET | `/api/users/me/referrals` | — | `ReferralStatsResponse` | explicit `ReferralStatsResponse(...)` | ✅ |
| users | POST | `/api/users/skip-legal-prompt` | — | `dict` | `{"success": True}` | n/a |
| users | GET | `/api/users/needs-accept-rules` | — | `dict` | `{"needs_accept": ...}` | n/a |
| auth | POST | `/api/auth/telegram` | — | `LoginResponse` | explicit `LoginResponse(user=UserResponse(...))` | ⚠️ different UserResponse, 8 fields missing |
| auth | GET | `/api/auth/me` | — | `UserResponse` (auth) | explicit `UserResponse(...)` | ⚠️ different schema, incomplete |
| placements | GET | `/api/placements/` | — | `list[PlacementResponse]` | `PlacementResponse.model_validate(p)` | ❌ 11 fields missing |
| placements | POST | `/api/placements/` | — | `PlacementResponse` | `PlacementResponse.model_validate(placement)` | ❌ 11 fields missing |
| placements | GET | `/api/placements/{id}` | — | `PlacementResponse` | `PlacementResponse.model_validate(placement)` | ❌ 11 fields missing |
| placements | POST | `/api/placements/{id}/accept` | — | `PlacementResponse` | `PlacementResponse.model_validate(result)` | ❌ 11 fields missing |
| placements | POST | `/api/placements/{id}/reject` | — | `PlacementResponse` | `PlacementResponse.model_validate(result)` | ❌ 11 fields missing |
| placements | POST | `/api/placements/{id}/counter` | — | `PlacementResponse` | `PlacementResponse.model_validate(result)` | ❌ 11 fields missing |
| placements | POST | `/api/placements/{id}/accept-counter` | — | `PlacementResponse` | `PlacementResponse.model_validate(result)` | ❌ 11 fields missing |
| placements | POST | `/api/placements/{id}/pay` | — | `PlacementResponse` | `PlacementResponse.model_validate(result)` | ❌ 11 fields missing |
| placements | DELETE | `/api/placements/{id}` | — | `PlacementResponse` | `PlacementResponse.model_validate(result)` | ❌ 11 fields missing |
| placements | PATCH | `/api/placements/{id}` | — | `PlacementResponse` | via action dispatch → `PlacementResponse.model_validate` | ❌ 11 fields missing |
| channels | GET | `/api/channels/` | `list[ChannelResponse]` | `list[ChannelResponse]` | explicit `ChannelResponse(...)` | ❌ `is_test` missing |
| channels | POST | `/api/channels/check` | — | `ChannelCheckResponse` | explicit `ChannelCheckResponse(...)` | ✅ |
| channels | POST | `/api/channels/` | — | `ChannelResponse` | explicit `ChannelResponse(...)` | ❌ `is_test` missing |
| channels | POST | `/api/channels/{id}/activate` | — | `ChannelResponse` | explicit `ChannelResponse(...)` | ❌ `is_test` missing |
| channels | PATCH | `/api/channels/{id}/category` | — | `ChannelResponse` | explicit `ChannelResponse(...)` | ❌ `is_test` missing |
| channels | DELETE | `/api/channels/{id}` | — | `None` (204) | — | n/a |
| channels | GET | `/api/channels/available` | — | `list[ChannelWithSettingsOut]` | explicit `ChannelWithSettingsOut(...)` | ✅ (has `is_test`) |
| channels | GET | `/api/channels/stats` | — | `DatabaseStatsResponse` | explicit | ✅ |
| channels | GET | `/api/channels/preview` | — | `ChannelsPreviewResponse` | explicit | ✅ |
| channels | POST | `/api/channels/compare` | — | `ComparisonResponse` | dict unpacking to model | ✅ |
| billing | GET | `/api/billing/balance` | — | `BalanceResponse` | explicit | ✅ |
| billing | GET | `/api/billing/history` | — | `BillingHistoryResponse` | explicit | ✅ |
| billing | POST | `/api/billing/topup` | — | `TopupResponse` | explicit | ✅ |
| billing | GET | `/api/billing/topup/{id}/status` | — | `dict[str, str]` | dict | n/a |
| billing | GET | `/api/billing/plans` | — | `list[PlanDetail]` | explicit | ✅ |
| billing | POST | `/api/billing/plan` | — | `PlanResponse` | explicit | ✅ |
| billing | POST | `/api/billing/credits` | — | `dict` | dict | n/a |
| payouts | GET | `/api/payouts/` | — | `list[PayoutResponse]` | `PayoutResponse.model_validate(p)` | ⚠️ field names mismatch w/ mini_app |
| payouts | GET | `/api/payouts/{id}` | — | `PayoutResponse` | `PayoutResponse.model_validate(payout)` | ⚠️ field names mismatch w/ mini_app |
| payouts | POST | `/api/payouts/` | — | `PayoutResponse` | `PayoutResponse.model_validate(payout)` | ⚠️ field names mismatch w/ mini_app |
| contracts | POST | `/api/contracts/generate` | — | `ContractResponse` | `_contract_to_response(contract)` | ✅ |
| contracts | GET | `/api/contracts/` | — | `ContractListResponse` | `ContractListResponse(items=[...])` | ✅ |
| contracts | GET | `/api/contracts/{id}` | — | `ContractResponse` | `_contract_to_response(contract)` | ✅ |
| contracts | POST | `/api/contracts/{id}/sign` | — | `ContractResponse` | `_contract_to_response(contract)` | ✅ |
| contracts | POST | `/api/contracts/accept-rules` | — | `dict` | dict | n/a |
| legal_profile | GET | `/api/legal-profile/me` | — | `LegalProfileResponse \| None` | `_build_response(profile, user)` | ✅ |
| legal_profile | POST | `/api/legal-profile/` | — | `LegalProfileResponse` | `_build_response(profile, user)` | ✅ |
| legal_profile | PATCH | `/api/legal-profile/` | — | `LegalProfileResponse` | `_build_response(profile, user)` | ✅ |
| campaigns | POST | `/api/campaigns/` | `CampaignResponse` | — | returns ORM object directly | ⚠️ ORM passed through Pydantic (FastAPI filters) |
| campaigns | GET | `/api/campaigns/` | `CampaignListResponse` | — | `CampaignListResponse(placement_requests=[CampaignResponse.model_validate(c)...])` | ✅ |
| campaigns | GET | `/api/campaigns/{id}` | `CampaignResponse` | — | returns ORM object directly | ⚠️ ORM passed through Pydantic (FastAPI filters) |
| campaigns | PATCH | `/api/campaigns/{id}` | `CampaignResponse` | — | returns ORM object from `repo.update()` | ⚠️ ORM passed through Pydantic (FastAPI filters) |

---

## Table 2: Endpoints WITHOUT Explicit `response_model=` Parameter

These rely solely on return-type annotations. FastAPI treats them identically to `response_model=` — **no ORM leakage** — but they are invisible in OpenAPI `components/schemas`.

| Router | Path | Return annotation | Risk |
|--------|------|-------------------|------|
| users | `/api/users/me` | `UserResponse` | ✅ filtered, schema incomplete |
| users | `/api/users/me/stats` | `UserStatsResponse` | ✅ filtered, schema complete |
| users | `/api/users/me/referrals` | `ReferralStatsResponse` | ✅ filtered, schema complete |
| auth | `/api/auth/me` | `UserResponse` (auth) | ✅ filtered, different schema |
| ALL placements | (all 10 endpoints) | `PlacementResponse` | ✅ filtered, schema incomplete |
| channels (4) | `POST /`, `POST /{id}/activate`, `PATCH /{id}/category`, `GET /available` | `ChannelResponse` / `ChannelWithSettingsOut` | ✅ filtered |
| payouts (3) | all payout endpoints | `PayoutResponse` | ✅ filtered, name mismatch |
| contracts (4) | all contract endpoints | `ContractResponse` | ✅ filtered, schema complete |
| legal_profile (3) | all profile endpoints | `LegalProfileResponse \| None` | ✅ filtered, schema complete |

**Key finding:** There are zero "raw ORM leak" endpoints in this codebase. The `campaigns.py` endpoints that return ORM objects directly are still protected by `response_model=CampaignResponse`.

---

## Table 3: Frontend-Expected Fields — Resolution per Entity

### 3a. User (`/api/users/me` → `users.py::UserResponse`)

| Frontend field | DB column | users.py schema | auth.py schema | Resolution |
|----------------|-----------|-----------------|----------------|------------|
| `id` | `users.id` | ✅ | ✅ | OK |
| `telegram_id` | `telegram_id` | ✅ | ✅ | OK |
| `username` | `username` | ✅ | ✅ | OK |
| `first_name` | `first_name` | ✅ | ✅ | OK |
| `last_name` | `last_name` | ❌ | ✅ | **Missing from users.py::UserResponse** |
| `current_role` | — (no DB col) | ❌ | ❌ | Computed client-side (dead field in types?) |
| `plan` | `plan` | ✅ | ✅ | OK |
| `plan_expires_at` | `plan_expires_at` | ❌ | ❌ | **Missing from both** (available in `/api/billing/balance`) |
| `balance_rub` | `balance_rub` | ✅ (as str) | ✅ | OK |
| `earned_rub` | `earned_rub` | ✅ (as str) | ✅ | OK |
| `credits` | `credits` | ❌ | ❌ | **Missing from both** (DB field exists) |
| `advertiser_xp` | `advertiser_xp` | ❌ | ❌ | **Missing from both** (DB field exists) |
| `advertiser_level` | `advertiser_level` | ❌ | ❌ | **Missing from both** (DB field exists) |
| `owner_xp` | `owner_xp` | ❌ | ❌ | **Missing from both** (DB field exists) |
| `owner_level` | `owner_level` | ❌ | ❌ | **Missing from both** (DB field exists) |
| `referral_code` | `referral_code` | ❌ | ❌ | **Missing from both** (DB field exists; also in `/api/users/me/referrals`) |
| `is_admin` | `is_admin` | ✅ | ✅ | OK |
| `legal_status_completed` | `legal_status_completed` | ✅ | ❌ | OK in users.py |
| `legal_profile_prompted_at` | `legal_profile_prompted_at` | ✅ | ✅ | OK |
| `legal_profile_skipped_at` | `legal_profile_skipped_at` | ✅ | ❌ | OK in users.py only |
| `platform_rules_accepted_at` | `platform_rules_accepted_at` | ✅ | ✅ | OK |
| `privacy_policy_accepted_at` | `privacy_policy_accepted_at` | ✅ | ✅ | OK |
| `has_legal_profile` | relationship (computed) | ✅ | ❌ | OK in users.py |
| `ai_generations_used` (web_portal only) | `ai_uses_count` | ❌ | ✅ (as `ai_generations_used`) | Missing from users.py |

**Note:** `auth.py::UserResponse` and `users.py::UserResponse` are two separate schemas with different fields. The mini_app calls `users/me`, not `auth/me`. The frontend `User` interface is the union of both but neither endpoint alone serves it.

### 3b. PlacementRequest (`/api/placements/*` → `placements.py::PlacementResponse`)

| Frontend field | DB column | PlacementResponse | Resolution |
|----------------|-----------|-------------------|------------|
| `id` | `id` | ✅ | OK |
| `advertiser_id` | `advertiser_id` | ✅ | OK |
| `owner_id` | `owner_id` | ❌ | **Missing** (DB field `placement_requests.owner_id` exists) |
| `channel_id` | `channel_id` | ✅ | OK |
| `channel` | relationship | ✅ (as `ChannelRef`) | OK |
| `status` | `status` | ✅ | OK |
| `publication_format` | `publication_format` | ✅ | OK |
| `ad_text` | `ad_text` | ✅ | OK |
| `proposed_price` | `proposed_price` | ✅ (Decimal) | OK |
| `final_price` | `final_price` | ✅ | OK |
| `proposed_schedule` | `proposed_schedule` | ✅ | OK |
| `final_schedule` | `final_schedule` | ❌ | **Missing** (DB field exists) |
| `counter_offer_count` | `counter_offer_count` | ✅ | OK |
| `counter_price` | `counter_price` | ✅ | OK |
| `counter_schedule` | `counter_schedule` | ❌ (field present in schema?) | ❌ Missing from PlacementResponse! See note |
| `counter_comment` | `counter_comment` | ✅ | OK |
| `advertiser_counter_price` | `advertiser_counter_price` | ✅ | OK |
| `advertiser_counter_schedule` | `advertiser_counter_schedule` | ✅ | OK |
| `advertiser_counter_comment` | `advertiser_counter_comment` | ✅ | OK |
| `rejection_reason` | `rejection_reason` | ❌ | **Missing** (DB field exists) |
| `expires_at` | `expires_at` | ✅ | OK |
| `published_at` | `published_at` | ✅ | OK |
| `scheduled_delete_at` | `scheduled_delete_at` | ❌ | **Missing** (DB field exists) |
| `deleted_at` | `deleted_at` | ❌ | **Missing** (DB field exists) |
| `clicks_count` | `clicks_count` | ❌ | **Missing** (DB field exists) |
| `published_reach` | `published_reach` | ❌ | **Missing** (DB field exists) |
| `tracking_short_code` | `tracking_short_code` | ❌ | **Missing** (DB field exists) |
| `has_dispute` | — (from relationship) | ❌ | **Missing** (needs computed from `PlacementDispute` rel) |
| `dispute_status` | — (from relationship) | ❌ | **Missing** (needs JOIN with `PlacementDispute`) |
| `is_test` | `is_test` | ✅ | OK |
| `test_label` | `test_label` | ✅ | OK |
| `media_type` | `media_type` | ✅ | OK |
| `video_file_id` | `video_file_id` | ✅ | OK |
| `video_url` | `video_url` | ✅ | OK |
| `video_thumbnail_file_id` | `video_thumbnail_file_id` | ✅ | OK |
| `video_duration` | `video_duration` | ✅ | OK |
| `erid` | — (from `OrdRegistration` rel) | ❌ | **Missing** (needs JOIN or lazy load from `ord_registrations`) |
| `created_at` | `created_at` | ✅ | OK |

> **Note on `counter_schedule`**: `PlacementResponse` has `counter_price` and `counter_comment` but NOT `counter_schedule` — this is another gap. The DB has `counter_schedule` (Mapped[datetime | None]).

**Correction:** Re-checking placements.py:229: `counter_schedule: Decimal | None = None  # FIX #2` — this is labelled `counter_schedule` but typed as `Decimal | None`. That's a **type bug**: it should be `datetime | None`. And the DB has `counter_schedule: Mapped[datetime | None]`. So `counter_schedule` IS in the schema but with wrong type.

### 3c. Channel (`/api/channels/*` → `schemas/channel.py::ChannelResponse`)

| Frontend field | DB column | ChannelResponse | Resolution |
|----------------|-----------|-----------------|------------|
| `id` | `id` | ✅ | OK |
| `telegram_id` | `telegram_id` | ✅ | OK |
| `username` | `username` | ✅ | OK |
| `title` | `title` | ✅ | OK |
| `owner_id` | `owner_id` | ✅ | OK |
| `member_count` | `member_count` | ✅ | OK |
| `is_test` | `is_test` | ❌ | **Missing** (DB field exists, in `ChannelWithSettingsOut` ✅) |
| `last_er` | `last_er` | ✅ | OK |
| `avg_views` | `avg_views` | ✅ | OK |
| `rating` | `rating` | ✅ | OK |
| `category` | `category` | ✅ | OK |
| `is_active` | `is_active` | ✅ | OK |

### 3d. Payout (`/api/payouts/*` → `schemas/payout.py::PayoutResponse`)

| mini_app field | web_portal field | Backend field | Resolution |
|----------------|------------------|---------------|------------|
| `id` | `id` | `id` | ✅ OK |
| `amount` | `gross_amount` | `gross_amount` | ⚠️ **mini_app NAME MISMATCH** |
| `fee` | `fee_amount` | `fee_amount` | ⚠️ **mini_app NAME MISMATCH** |
| `net_amount` | `net_amount` | `net_amount` | ✅ OK |
| `status` | `status` | `status` | ✅ OK |
| `payment_details` | `requisites` | `requisites` | ⚠️ **mini_app NAME MISMATCH** |
| — | `reject_reason` | `rejection_reason` | ⚠️ **web_portal NAME MISMATCH** |
| `created_at` | `created_at` | `created_at` | ✅ OK |
| `processed_at` | `processed_at` | `processed_at` | ✅ OK |
| — | `owner_id` | `owner_id` | ✅ backend has it |

### 3e. Contract (`/api/contracts/*` → `schemas/legal_profile.py::ContractResponse`)

| Frontend field (mini_app) | Backend field | Resolution |
|--------------------------|---------------|------------|
| `contract_status` | `contract_status` | ✅ |
| All other fields | matching | ✅ Full alignment |

**web_portal** `Contract` type has both `status` and `contract_status?` — the backend only returns `contract_status`. The `status` alias in web_portal is dead/redundant.

### 3f. LegalProfile (`/api/legal-profile/*` → `schemas/legal_profile.py::LegalProfileResponse`)

✅ **Full alignment.** All frontend fields are present in `LegalProfileResponse`.

---

## Table 4: Proposed Fixes for S-39b

### Priority 1 — Add fields to `users.py::UserResponse`

| Field to add | DB source | Type |
|--------------|-----------|------|
| `last_name` | `User.last_name` | `str \| None = None` |
| `plan_expires_at` | `User.plan_expires_at` | `datetime \| None = None` |
| `credits` | `User.credits` | `int = 0` |
| `advertiser_xp` | `User.advertiser_xp` | `int = 0` |
| `advertiser_level` | `User.advertiser_level` | `int = 1` |
| `owner_xp` | `User.owner_xp` | `int = 0` |
| `owner_level` | `User.owner_level` | `int = 1` |
| `referral_code` | `User.referral_code` | `str` |
| `ai_generations_used` | `User.ai_uses_count` (alias) | `int = 0` |

Also: align `users.py::UserResponse` and `auth.py::UserResponse` into one shared schema (or consolidate `auth.py::UserResponse` to include all users.py fields too).

### Priority 2 — Add fields to `placements.py::PlacementResponse`

| Field to add | DB source | Type | Notes |
|--------------|-----------|------|-------|
| `owner_id` | `PlacementRequest.owner_id` | `int` | |
| `final_schedule` | `PlacementRequest.final_schedule` | `datetime \| None = None` | |
| `rejection_reason` | `PlacementRequest.rejection_reason` | `str \| None = None` | |
| `scheduled_delete_at` | `PlacementRequest.scheduled_delete_at` | `datetime \| None = None` | |
| `deleted_at` | `PlacementRequest.deleted_at` | `datetime \| None = None` | |
| `clicks_count` | `PlacementRequest.clicks_count` | `int = 0` | |
| `published_reach` | `PlacementRequest.published_reach` | `int \| None = None` | |
| `tracking_short_code` | `PlacementRequest.tracking_short_code` | `str \| None = None` | |
| `has_dispute` | relationship (computed) | `bool = False` | requires selectinload of `disputes` rel or separate query |
| `dispute_status` | `PlacementDispute.status` | `str \| None = None` | requires JOIN |
| `erid` | `OrdRegistration.erid` | `str \| None = None` | requires selectinload of `ord_registration` rel |

Also: fix `counter_schedule` type annotation — it's currently `Decimal | None` but should be `datetime | None`.

### Priority 3 — Add `is_test` to `ChannelResponse`

```python
is_test: bool = False
```

Update all 4 explicit `ChannelResponse(...)` constructors in `channels.py` to pass `is_test=ch.is_test`.

### Priority 4 — Fix Payout field names in mini_app

Either:
- (a) Add `amount`, `fee`, `payment_details` as alias fields to `PayoutResponse` via Pydantic `Field(alias=...)` — backend sends both names
- (b) Update mini_app frontend types and API calls to use `gross_amount`, `fee_amount`, `requisites`

Option (b) is cleaner; option (a) is backwards-compatible.

Also fix web_portal: `reject_reason` → `rejection_reason`.

---

## Breaking Change Risk Analysis

| Change | Risk | Notes |
|--------|------|-------|
| Add fields to `UserResponse` | **None** — additive | `credits` is `int`, not Decimal — no serialization impact |
| Add fields to `PlacementResponse` | **None** — additive | New datetime fields will serialize as ISO strings; `clicks_count` as int |
| `has_dispute`, `dispute_status`, `erid` in PlacementResponse | **Medium** — requires JOIN | Without eager load, `model_validate()` will raise or return None. Must add `selectinload` in list/get endpoints |
| Add `is_test` to ChannelResponse | **None** — additive | Boolean field with default |
| Payout field rename (mini_app) | **Breaking for mini_app** | Any screen using `payout.amount` breaks. Must update all `mini_app/src/` references to `payout.amount → payout.gross_amount` |
| Consolidate `auth.py::UserResponse` with `users.py::UserResponse` | **Low risk** | Both return types stay; just add fields. Auth LoginResponse.user gains new fields — no breakage |
| `counter_schedule` type fix | **Low risk** — was already wrong type | Any code that treated it as Decimal was broken; correct type is datetime |

---

## Additional Observations

### Duplicate UserResponse Problem
`src/api/routers/auth.py` defines its own `UserResponse` with `last_name`, `ai_generations_used`, but no `legal_status_completed`. `src/api/routers/users.py` defines a DIFFERENT `UserResponse` with `legal_status_completed`, `has_legal_profile`, but no `last_name`. These should be one schema in `src/api/schemas/`.

### Campaigns Router — Legacy Overlap
`campaigns.py` and `placements.py` both operate on `PlacementRequest`. The campaigns router uses a sparse `CampaignResponse` (7 fields) while placements uses the richer `PlacementResponse` (28+ fields). The mini_app calls placements endpoints; the campaigns router appears to be legacy/internal. The `CampaignResponse` intentional incompleteness is not a bug — but it creates confusing overlap.

### No ORM Field Leakage
Every entity endpoint in this codebase constructs Pydantic objects explicitly or uses `model_validate()`. The 3 campaigns.py endpoints that return ORM objects directly are still passed through `response_model=CampaignResponse` which Pydantic filters. **There are no phantom fields in API responses.**

---

## Scope Recommendation for S-39b Fix

### Minimum (unblocks frontend)
1. `users.py::UserResponse` — add 9 fields (last_name, plan_expires_at, credits, xp/level × 4, referral_code, ai_generations_used) — ~15 min
2. `placements.py::PlacementResponse` — add 8 simple fields (owner_id, final_schedule, rejection_reason, scheduled_delete_at, deleted_at, clicks_count, published_reach, tracking_short_code) — ~20 min
3. `schemas/channel.py::ChannelResponse` + 4 constructor calls — add `is_test` — ~10 min
4. Fix `counter_schedule` type in `PlacementResponse` (Decimal→datetime) — 2 min

### Exhaustive (completes the picture)
Minimum + above + :
5. Add `has_dispute`, `dispute_status`, `erid` to `PlacementResponse` — requires `selectinload` additions in `get_placement`, `list_placements`, and all action endpoints — ~1 hr
6. Consolidate `auth.py::UserResponse` into a shared schema — ~30 min
7. Fix mini_app Payout field names (`amount→gross_amount`, `fee→fee_amount`, `payment_details→requisites`) — requires frontend changes too — ~45 min
8. Fix web_portal `reject_reason→rejection_reason` — frontend-only — ~5 min

### Defer to S-40
- Remove `campaigns.py` legacy overlap (routes that duplicate placements.py)
- `current_role` field in mini_app User interface — no DB column, likely computed client-side, remove from shared types

---

🔍 Verified against: `9fdf413` (HEAD of feature/s-38-escrow-recovery) | 📅 Updated: 2026-04-19T00:00:00Z
