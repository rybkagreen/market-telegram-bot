# S-39: Type Drift Audit — mini_app vs web_portal

> **Sprint:** S-39 | **Phase:** Research | **Date:** 2026-04-17  
> **Scope:** 6 shared entity types (User, PlacementRequest, Channel, Payout, Contract, LegalProfile)  
> **Reference:** CHANGES_2026-04-16_cross-layer-audit.md Phase 7, N-12

---

## Stop-and-Report Checks

- **All files exist:** ✅ All 14 source files found.  
- **Semantic divergence (not drift):** ⚠️ One semi-semantic issue:  
  `Contract` in `web_portal` has **both** `status` and `contract_status?` fields — backend uses only `contract_status`. This is a partial rename that was never cleaned up; both frontends accept the same JSON but web_portal's type allows ambiguity. Flagged in the diff below.

---

## 1. Side-by-Side Diffs

### 1.1 User

**Sources:**  
- mini_app: `mini_app/src/lib/types.ts` (lines 57–81)  
- web_portal: `web_portal/src/lib/types/user.ts` (lines 3–27)  
- backend: `src/api/routers/users.py:UserResponse` (lines 32–50)

| Field | mini_app | web_portal | backend (UserResponse) | Notes |
|---|---|---|---|---|
| `id` | `number` | `number` | `int` | ✅ aligned |
| `telegram_id` | `number` | `number` | `int` | ✅ aligned |
| `username` | `string \| null` | `string \| null` | `str \| None` | ✅ aligned |
| `first_name` | `string` | `string` | `str \| None` | ⚠️ backend allows null |
| `last_name` | `string \| null` | `string \| null` | ❌ absent | drift — not in backend response |
| `current_role` | `UserRole` | ❌ absent | ❌ absent | mini_app-only field |
| `plan` | `Plan` (union) | `Plan` (union) | `str` | ⚠️ backend returns raw string, not enum |
| `plan_expires_at` | `string \| null` | `string \| null` | ❌ absent | drift — not in backend response |
| `balance_rub` | `string` | `string` | `str` | ✅ aligned |
| `earned_rub` | `string` | `string` | `str` | ✅ aligned |
| `credits` | `number` | `number` | ❌ absent | drift — not in backend response |
| `advertiser_xp` | `number` | `number` | ❌ absent | drift — not in backend response |
| `advertiser_level` | `number` | `number` | ❌ absent | drift — not in backend response |
| `owner_xp` | `number` | `number` | ❌ absent | drift — not in backend response |
| `owner_level` | `number` | `number` | ❌ absent | drift — not in backend response |
| `referral_code` | `string` | `string` | ❌ absent | drift — not in backend response |
| `is_admin` | `boolean` | `boolean` | `bool` | ✅ aligned |
| `ai_generations_used` | ❌ absent | `number` | ❌ absent | web_portal-only field |
| `legal_status_completed` | `boolean` | `boolean` | `bool` | ✅ aligned |
| `has_legal_profile` | `boolean` | `boolean` | `bool` | ✅ aligned |
| `legal_profile_prompted_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ aligned |
| `legal_profile_skipped_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ aligned |
| `platform_rules_accepted_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ aligned |
| `privacy_policy_accepted_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ aligned |

**Verdict:** mini_app vs web_portal drift is **minor** (1 field each: `current_role` vs `ai_generations_used`). Both have many fields absent from the backend `UserResponse` schema — this implies the backend is serving fields from the ORM model directly (not via Pydantic) for some endpoints, or the frontend types were written ahead of the API.

---

### 1.2 PlacementRequest

**Sources:**  
- mini_app: `mini_app/src/lib/types.ts` (lines 156–195)  
- web_portal: `web_portal/src/lib/types/placement.ts` (lines 18–54)  
- backend: `src/api/routers/placements.py:PlacementResponse` (lines 213–245)

| Field | mini_app | web_portal | backend (PlacementResponse) | Notes |
|---|---|---|---|---|
| `id` | `number` | `number` | `int` | ✅ |
| `advertiser_id` | `number` | `number` | `int` | ✅ |
| `owner_id` | `number` | `number` | ❌ absent | drift — not in backend response |
| `channel_id` | `number` | `number` | `int` | ✅ |
| `channel` | `ChannelRef?` (no `member_count`) | `{id,username,title,member_count}?` | `ChannelRef?` (no `member_count`) | ⚠️ web_portal adds member_count |
| `status` | `PlacementStatus` | `PlacementStatus` | `str` | ⚠️ backend returns raw string |
| `publication_format` | `PublicationFormat` | `PublicationFormat` | `str` | ⚠️ backend returns raw string |
| `ad_text` | `string` | `string` | `str` | ✅ |
| `proposed_price` | `string` | `string` | `Decimal` → serialized as string | ✅ effective |
| `final_price` | `string \| null` | `string \| null` | `Decimal \| None` | ✅ effective |
| `proposed_schedule` | `string` | `string` | `datetime \| None` | ⚠️ frontend expects string, backend may return null |
| `final_schedule` | `string \| null` | `string \| null` | ❌ absent | drift |
| `counter_offer_count` | `number` | `number` | `int` | ✅ |
| `counter_price` | `string \| null` | `string \| null` | `Decimal \| None` | ✅ effective |
| `counter_schedule` | `string \| null` | `string \| null` | `datetime \| None` | ✅ effective |
| `counter_comment` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `advertiser_counter_price` | `string \| null` | ❌ absent | `Decimal \| None` | web_portal missing |
| `advertiser_counter_schedule` | `string \| null` | ❌ absent | `datetime \| None` | web_portal missing |
| `advertiser_counter_comment` | `string \| null` | ❌ absent | `str \| None` | web_portal missing |
| `rejection_reason` | `string \| null` | `string \| null` | ❌ absent | backend missing |
| `expires_at` | `string` | `string` | `datetime \| None` | ✅ effective |
| `published_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ effective |
| `scheduled_delete_at` | `string \| null` | `string \| null` | ❌ absent | backend missing |
| `deleted_at` | `string \| null` | `string \| null` | ❌ absent | backend missing |
| `clicks_count` | `number` | `number` | ❌ absent | backend missing |
| `published_reach` | `number \| null` | `number \| null` | ❌ absent | backend missing |
| `tracking_short_code` | `string \| null` | `string \| null` | ❌ absent | backend missing |
| `has_dispute` | `boolean` | `boolean` | ❌ absent | backend missing |
| `dispute_status` | `DisputeStatus \| null` | `DisputeStatus \| null` | ❌ absent | backend missing |
| `is_test` | `boolean` | `boolean` | `bool` | ✅ |
| `test_label` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `media_type` | `MediaType` | `MediaType` | `str` | ⚠️ backend returns raw string |
| `video_file_id` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `video_url` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `video_thumbnail_file_id` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `video_duration` | `number \| null` | `number \| null` | `int \| None` | ✅ |
| `erid` | `string \| null` | `string \| null` | ❌ absent | backend missing |
| `created_at` | `string` | `string` | `datetime` | ✅ effective |
| `updated_at` | ❌ absent | ❌ absent | `datetime` | backend-only |

**Additional enum drift:**  
`PlacementStatus` in mini_app includes `'completed'` — web_portal does NOT have this value.

**Verdict:** Significant drift. web_portal is missing 3 advertiser counter-offer fields that are in backend + mini_app. Backend `PlacementResponse` is missing ~10 fields present in both frontends — suggesting the real serialization happens via ORM model, not this schema.

---

### 1.3 Channel

**Sources:**  
- mini_app: `mini_app/src/lib/types.ts` (lines 99–113)  
- web_portal: `web_portal/src/lib/types/channel.ts` (lines 14–24)  
- backend: `src/api/schemas/channel.py:ChannelResponse` (lines 139–172)

| Field | mini_app | web_portal `Channel` | web_portal `ChannelResponse` | backend `ChannelResponse` | Notes |
|---|---|---|---|---|---|
| `id` | `number` | `number` | `number` | `int` | ✅ |
| `telegram_id` | `number` | `number` | `number` | `int` | ✅ |
| `username` | `string` | `string` | `string` | `str` | ✅ |
| `title` | `string` | `string` | `string` | `str` | ✅ |
| `owner_id` | `number` | `number` | `number` | `int` | ✅ |
| `member_count` | `number` | `number` | `number` | `int` | ✅ |
| `is_test` | `boolean` | ❌ absent | ❌ absent | ❌ absent | mini_app-only flag |
| `last_er` | `number` | ❌ absent | ❌ absent | `float` | web_portal missing; backend has it |
| `avg_views` | `number` | ❌ absent | ❌ absent | `int` | web_portal missing; backend has it |
| `rating` | `number` | `number` | `number` | `float` | ✅ |
| `category` | `string` | `string` | `string \| null` | `str \| null` | ⚠️ mini_app non-null, others nullable |
| `is_active` | `boolean` | `boolean` | `boolean` | `bool` | ✅ |
| `created_at` | ❌ absent | ❌ absent | `string` | `str` | web_portal ChannelResponse + backend have it |

**Verdict:** web_portal `Channel` interface is stripped-down (no `last_er`, `avg_views`). mini_app has `is_test` that nothing else does. `ChannelResponse` in web_portal is a superset of `Channel` but still misses analytics fields present in backend.

---

### 1.4 Payout

**Sources:**  
- mini_app: `mini_app/src/lib/types.ts` (lines 197–212)  
- web_portal: `web_portal/src/lib/types/billing.ts` (lines 7–22)  
- backend: `src/api/schemas/payout.py:PayoutResponse` (lines 32–52)

| Field | mini_app | web_portal | backend | Notes |
|---|---|---|---|---|
| `id` | `number` | `number` | `int` | ✅ |
| `owner_id` | `number` | `number` | `int` | ✅ |
| `gross_amount` | `string` | `string` | `Decimal` | ✅ effective |
| `fee_amount` | `string` | `string` | `Decimal` | ✅ effective |
| `net_amount` | `string` | `string` | `Decimal` | ✅ effective |
| `status` | `PayoutStatus` | `PayoutStatus` | `PayoutStatus` | ✅ |
| `requisites` | `string` | `string` | `str` | ✅ |
| `admin_id` | `number \| null` | `number \| null` | `int \| None` | ✅ |
| `processed_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ effective |
| `rejection_reason` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `ndfl_withheld` | `string \| null` | `string \| null` | `Decimal \| None` | ✅ effective |
| `npd_status` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `npd_receipt_number` | ❌ absent | ❌ absent | `str \| None` | backend-only field |
| `created_at` | `string` | `string` | `datetime` | ✅ effective |
| `updated_at` | `string` | `string` | `datetime` | ✅ effective |

**`PayoutStatus` enum drift:**  
Backend has `cancelled` value; neither frontend includes it.

**Verdict:** Payout is the **best-aligned** type. Only gap: `npd_receipt_number` in backend (not surfaced to frontends) and `cancelled` status variant.

---

### 1.5 Contract

**Sources:**  
- mini_app: `mini_app/src/lib/types.ts` (lines 555–571)  
- web_portal: `web_portal/src/lib/types/contracts.ts` (lines 15–32)  
- backend: `src/api/schemas/legal_profile.py:ContractResponse` (lines 185–202)

| Field | mini_app | web_portal | backend | Notes |
|---|---|---|---|---|
| `id` | `number` | `number` | `int` | ✅ |
| `user_id` | `number` | `number` | `int` | ✅ |
| `contract_type` | `ContractType` | `ContractType` | `ContractType` | ✅ |
| `contract_status` | `ContractStatus` | `ContractStatus?` (optional) | `ContractStatus` | ⚠️ web_portal marks as optional |
| `status` | ❌ absent | `ContractStatus` (required) | ❌ absent | **SEMANTIC ISSUE** — web_portal alias |
| `placement_request_id` | `number \| null` | `number \| null` | `int \| None` | ✅ |
| `template_version` | `string` | `string` | `str` | ✅ |
| `signature_method` | `SignatureMethod \| null` | `SignatureMethod \| null` | `SignatureMethod \| None` | ✅ |
| `signed_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ effective |
| `expires_at` | `string \| null` | `string \| null` | `datetime \| None` | ✅ effective |
| `pdf_url` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `kep_requested` | `boolean` | `boolean` | `bool` | ✅ |
| `kep_request_email` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `role` | `string \| null` | `ContractRole \| null` | `str \| None` | ⚠️ web_portal uses typed union |
| `created_at` | `string` | `string` | `datetime` | ✅ effective |
| `updated_at` | `string` | `string` | `datetime` | ✅ effective |

**Verdict:** The `status` / `contract_status` dual field in web_portal is a real semantic smell. Backend always returns `contract_status`; mini_app uses `contract_status` correctly. web_portal has both and makes `contract_status` optional — consuming code may use either field, leading to silent undefined reads.

---

### 1.6 LegalProfile

**Sources:**  
- mini_app: `mini_app/src/lib/types.ts` (lines 508–533)  
- web_portal: `web_portal/src/lib/types/legal.ts` (lines 9–38)  
- backend: `src/api/schemas/legal_profile.py:LegalProfileResponse` (lines 139–167)

| Field | mini_app | web_portal | backend | Notes |
|---|---|---|---|---|
| `id` | `number` | `number` | `int` | ✅ |
| `user_id` | `number` | `number` | `int` | ✅ |
| `legal_status` | `LegalStatus` | `LegalStatus` | `LegalStatus` | ✅ |
| `inn` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `kpp` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `ogrn` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `ogrnip` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `legal_name` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `address` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `tax_regime` | `TaxRegime \| null` | `TaxRegime \| null` | `TaxRegime \| None` | ✅ |
| `bank_name` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `bank_account` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `bank_bik` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `bank_corr_account` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `yoomoney_wallet` | `string \| null` | `string \| null` | `str \| None` | ✅ |
| `passport_series` | ❌ absent | `string \| null` | ❌ not in response | web_portal exposes PII |
| `passport_number` | ❌ absent | `string \| null` | ❌ not in response | web_portal exposes PII |
| `passport_issued_by` | ❌ absent | `string \| null` | ❌ not in response | web_portal exposes PII |
| `passport_issued_at` | ❌ absent | `string \| null` | ❌ not in response | ⚠️ name mismatch: backend uses `passport_issue_date` |
| `has_passport_data` | `boolean` | `boolean` | `bool` (computed) | ✅ |
| `has_inn_scan` | `boolean` | `boolean` | `bool` (computed) | ✅ |
| `has_passport_scan` | `boolean` | `boolean` | `bool` (computed) | ✅ |
| `has_self_employed_cert` | `boolean` | `boolean` | `bool` (computed) | ✅ |
| `has_company_doc` | `boolean` | `boolean` | `bool` (computed) | ✅ |
| `is_verified` | `boolean` | `boolean` | `bool` | ✅ |
| `is_complete` | `boolean` | `boolean` | `bool` (computed) | ✅ |
| `created_at` | `string` | `string` | `datetime` | ✅ effective |
| `updated_at` | `string` | `string` | `datetime` | ✅ effective |

**Verdict:** LegalProfile is well-aligned except web_portal includes 4 passport fields absent from backend response. Field name mismatch: web_portal uses `passport_issued_at` but backend `LegalProfileCreate` uses `passport_issue_date`.

---

## 2. Consolidated Diff Table

| Type | Field | mini_app type | web_portal type | Pydantic type | Recommended source |
|---|---|---|---|---|---|
| User | `current_role` | `UserRole` | ❌ | — | backend (missing) |
| User | `ai_generations_used` | ❌ | `number` | — | backend (missing) |
| User | `last_name` | `string\|null` | `string\|null` | ❌ | backend `UserResponse` |
| User | `credits` | `number` | `number` | ❌ | backend `UserResponse` |
| PlacementRequest | `advertiser_counter_*` (3 fields) | present | ❌ | `Decimal\|None` | backend `PlacementResponse` |
| PlacementRequest | `completed` status | present | ❌ | — | backend `PlacementStatus` |
| PlacementRequest | `owner_id` | `number` | `number` | ❌ | backend `PlacementResponse` |
| PlacementRequest | `channel.member_count` | ❌ | `number` | ❌ | backend `ChannelRef` |
| Channel | `is_test` | `boolean` | ❌ | ❌ | review (admin-only?) |
| Channel | `last_er`, `avg_views` | present | ❌ | present | backend `ChannelResponse` |
| Payout | `npd_receipt_number` | ❌ | ❌ | `str\|None` | consider exposing |
| Payout | `cancelled` status | ❌ | ❌ | present | add to both frontends |
| Contract | `status` (alias) | ❌ | `ContractStatus` | ❌ | **remove from web_portal** |
| Contract | `contract_status` optional | present | optional | required | fix web_portal: make required |
| LegalProfile | `passport_*` (4 fields) | ❌ | present | not in response | PII — keep out of mini_app ✓ |
| LegalProfile | `passport_issued_at` | — | `string\|null` | `passport_issue_date` | **rename in web_portal** |

---

## 3. Current Infrastructure

### 3.1 Package architecture

```
/opt/market-telegram-bot/
├── mini_app/           # Independent Vite React app
│   └── package.json    # No workspaces field
├── web_portal/         # Independent Vite React app
│   └── package.json    # No workspaces field
├── package.json        # Root: {"devDependencies": {"typescript": "^6.0.2"}} only
└── (no pnpm-workspace.yaml, lerna.json, turbo.json, nx.json)
```

**Assessment:** Independent sub-projects in a monorepo directory. No workspace tooling. Root `package.json` is a stub (only TypeScript devDep). No npm workspaces configured.

### 3.2 Codegen tooling audit

**mini_app/package.json:** No openapi, datamodel-code-generator, pydantic-to-typescript, or any schema-gen tooling.  
**web_portal/package.json:** Same — absent.  
**pyproject.toml:** No datamodel-code-generator or pydantic-to-typescript entries.

### 3.3 FastAPI OpenAPI endpoint

`src/api/main.py` creates `FastAPI(...)` with **no** `openapi_url=None` — meaning the default `/openapi.json` endpoint is active. The schema is therefore available at runtime.

---

## 4. Implementation Options

### Option A — Shared npm package via local workspaces

**Structure:**
```
/shared-types/
  package.json     { "name": "@rekharbor/shared-types" }
  index.ts         # Hand-maintained canonical types
mini_app/package.json → "@rekharbor/shared-types": "workspace:*"
web_portal/package.json → "@rekharbor/shared-types": "workspace:*"
root/package.json → "workspaces": ["mini_app", "web_portal", "shared-types"]
```

**Pros:**
- Types are centralized; single source of truth
- Works offline / without running server
- TypeScript can be written idiomatically (e.g., discriminated unions, branded types)

**Cons:**
- Still manually maintained — drift from Pydantic models can re-emerge
- Requires npm workspace setup (pnpm or npm 7+)
- Build tooling in both apps must resolve workspace protocol

---

### Option B — Generate TypeScript from FastAPI OpenAPI schema

**Tool:** `openapi-typescript` (zero runtime, generates read-only TS from OpenAPI 3.x)  
**Workflow:** Add to each app's `package.json`:
```json
"scripts": {
  "generate-types": "openapi-typescript http://localhost:8001/openapi.json -o src/lib/types/api.generated.ts",
  "prebuild": "npm run generate-types"
}
```

**Pros:**
- Pydantic models are the **true** source of truth
- Zero manual maintenance — types regenerate on every build
- Catches schema mismatches at build time
- Works with `openapi-typescript` (stable, well-maintained)

**Cons:**
- Requires running API server to generate (or a saved `openapi.json` snapshot)
- Backend `PlacementResponse` and `UserResponse` are currently **incomplete** (many fields missing vs what the ORM serializes) — generation would produce the incomplete schema, not what the API actually returns
- Requires fixing backend schemas first to be authoritative
- Generated types are often verbose (schema components, not clean interfaces)

---

### Option C — Shared file, copied on build (simplest)

**Structure:**
```
/shared/types.ts    # Manually maintained, single canonical file
```
Build script copies it to `mini_app/src/lib/types/shared.ts` and `web_portal/src/lib/types/shared.ts` before `tsc`.

**Pros:**
- Zero tooling change required
- Works now without workspace reconfiguration
- Can be done incrementally (migrate 1 type at a time)

**Cons:**
- Copy step can be forgotten; still manually maintained
- No real single-source guarantee if files diverge again

---

## 5. Recommendation

**Recommended: Option B (OpenAPI generation), but with a prerequisite fix.**

### Why

1. Pydantic schemas are already the contractual boundary for the API — they should be the source of truth, not hand-written TS.
2. FastAPI's `/openapi.json` is live and already exports them correctly for `LegalProfile`, `Contract`, `Payout` (the schemas with dedicated schema files).
3. `openapi-typescript` is a mature, zero-runtime tool that maps directly to FastAPI's output.

### Prerequisite (must precede codegen adoption)

**The backend `UserResponse` and `PlacementResponse` are incomplete.** Many fields consumed by both frontends are absent from these Pydantic schemas — which means the API is returning ORM model attributes directly (JSON serialization path bypasses Pydantic for some fields). Before codegen is viable:

1. Audit `GET /api/users/me` and `GET /api/placements/` actual responses vs `UserResponse`/`PlacementResponse` — identify which fields come from ORM vs Pydantic.
2. Add the missing fields to the Pydantic schemas (or create proper response schemas for each router).
3. Only then can generated types be authoritative.

### Interim (unblocked today)

For the 4 well-defined schemas (`Payout`, `Contract`, `LegalProfile`, `Channel`):
- Fix the 5 identified drift points (table in §2) manually in both frontends.
- This resolves the `Contract.status` semantic issue and `passport_issued_at` name mismatch.

### Implementation order

1. Fix Contract drift (status/contract_status) in web_portal — 5 min, zero risk.
2. Fix `passport_issued_at` → `passport_issue_date` in web_portal `LegalProfile`.
3. Add `npd_receipt_number` and `cancelled` status to both Payout types.
4. (S-39 followup sprint) Audit User/PlacementRequest backend schemas; add missing fields.
5. (S-40+) Add `openapi-typescript` as `devDependency` in both packages; add `generate-types` script; commit generated `api.generated.ts` and wrap it with human-friendly aliases.

---

🔍 Verified against: d195386 | 📅 Updated: 2026-04-17T00:00:00Z
