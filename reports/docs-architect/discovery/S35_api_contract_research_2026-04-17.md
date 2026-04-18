# S-35 API Contract Research: Frontend ↔ Backend Mismatches

**Sprint:** S-35 | **Phase:** Research (read-only)  
**Scope:** N-04..N-08 from CHANGES_2026-04-16_cross-layer-audit.md (Phase 3)  
**Date:** 2026-04-17

---

## Summary Table

| Finding | Method | Path | Frontend file:line | Backend file:line | Body (frontend) | Body (backend schema) | Mismatch type | Fix owner |
|---------|--------|------|--------------------|------------------|-----------------|-----------------------|---------------|-----------|
| N-04 | POST | billing/credits | mini_app/src/api/billing.ts:92 | src/api/routers/billing.py:429 | `{ desired_amount: number }` | `TopupRequest { desired_amount: int, method: str="yookassa" }` | **FALSE ALARM** — endpoint exists, contract matches | — |
| N-05 | POST | channels/compare | mini_app/src/api/channels.ts:56 | src/api/routers/channels.py:1059 | `{ channel_ids: number[] }` | `ChannelIdsRequest { channel_ids: list[int] }` | **Response schema mismatch** (field renames + missing fields) | backend or frontend |
| N-06 | POST | legal-profile/scan | mini_app/src/api/legalProfile.ts:14 | src/api/routers/legal_profile.py:96 | `{ scan_type, file_id }` | `ScanUpload { scan_type: str, file_id: str }` | **FALSE ALARM** — endpoint exists, contract matches | — |
| N-07 | GET | contracts/mine | web_portal/src/api/contracts.ts:15 | MISSING (`/contracts` exists) | — | — | Dead file with wrong path; live hooks use `GET /contracts` via legal.ts ✓ | frontend (cleanup) |
| N-08 | POST | contracts/accept-rules | web_portal/src/api/legal.ts:65 | src/api/routers/contracts.py:74 | **empty body** | `AcceptRulesRequest { accept_platform_rules: bool, accept_privacy_policy: bool }` | **422 Unprocessable Entity** — required fields not sent | frontend (web_portal) |

---

## N-04 — POST billing/credits

**Verdict: FALSE ALARM. Endpoint exists and contract is compatible.**

### Frontend call (mini_app/src/api/billing.ts:91-93)
```typescript
export function buyCredits(amountRub: number): Promise<BuyCreditsResponse> {
  return api.post('billing/credits', { json: { desired_amount: amountRub } }).json<BuyCreditsResponse>()
}
// BuyCreditsResponse = { amount_rub: number }
```

### Backend endpoint (src/api/routers/billing.py:429-457)
```python
@router.post("/credits", ...)
async def buy_credits(body: TopupRequest, current_user: CurrentUser) -> dict:
    # TopupRequest = { desired_amount: int, method: str = "yookassa" }
    ...
    return {"amount_rub": body.desired_amount}
```

**Analysis:** Router is mounted at `/api/billing` → endpoint is `/api/billing/credits`. Frontend sends `desired_amount` only; backend `method` field has a default value `"yookassa"` so it's not required. Response `{"amount_rub": int}` matches `BuyCreditsResponse`. No action needed.

---

## N-05 — channels/compare: method match, response schema mismatch

**Verdict: Endpoint method is correct (POST), but response field names diverge.**

### Frontend call (mini_app/src/api/channels.ts:55-57)
```typescript
export function compareChannels(channelIds: number[]): Promise<ChannelCompareResponse> {
  return api.post('channels/compare', { json: { channel_ids: channelIds } }).json<ChannelCompareResponse>()
}
```

Frontend expects `ChannelCompareResponse`:
```typescript
interface ChannelCompareResponse {
  channels: Array<{
    id: number; title: string; username: string
    subscribers: number    // ← field name
    topic: string          // ← missing in backend
    rating: number         // ← missing in backend
    avg_views: number
    last_er: number        // ← field name
    price_per_post: number
  }>
}
// Note: no best_values or recommendation at root level
```

### Backend endpoint (src/api/routers/channels.py:1059-1085)
```python
@router.post("/compare", ...)
async def compare_channels(request: ChannelIdsRequest, current_user: CurrentUser) -> ComparisonResponse:
    ...
```

Backend `ComparisonResponse`:
```python
class ComparisonChannelItem(BaseModel):
    id: int; username: str | None; title: str | None
    member_count: int       # ← frontend expects "subscribers"
    avg_views: int
    er: float               # ← frontend expects "last_er"
    post_frequency: float   # ← extra (frontend ignores)
    price_per_post: float
    price_per_1k_subscribers: float  # ← extra
    is_best: dict[str, bool]         # ← extra

class ComparisonResponse(BaseModel):
    channels: list[ComparisonChannelItem]
    best_values: dict[str, float]    # ← extra, not in frontend type
    recommendation: ComparisonRecommendation  # ← extra
```

**Field-level diff:**

| Frontend field | Backend field | Status |
|---------------|---------------|--------|
| `subscribers` | `member_count` | Rename mismatch — frontend gets `undefined` |
| `topic` | *(absent)* | Missing in backend response |
| `rating` | *(absent)* | Missing in backend response |
| `last_er` | `er` | Rename mismatch — frontend gets `undefined` |
| `price_per_post` | `price_per_post` | ✓ |
| `avg_views` | `avg_views` | ✓ |
| `id`, `title`, `username` | same | ✓ |

**Fix owner: backend** — `ComparisonChannelItem` needs: rename `member_count→subscribers`, `er→last_er`; add `topic: str | None` and `rating: float | None` from `TelegramChat`.

---

## N-06 — POST legal-profile/scan

**Verdict: FALSE ALARM. Endpoint exists and contract is compatible.**

### Frontend call (mini_app/src/api/legalProfile.ts:14-15)
```typescript
uploadScan: (scanType: string, fileId: string) =>
  api.post('legal-profile/scan', { json: { scan_type: scanType, file_id: fileId } }).json<{ success: boolean }>(),
```

### Backend endpoint (src/api/routers/legal_profile.py:96-112)
```python
@router.post("/scan", ...)
async def upload_scan(data: ScanUpload, ...) -> dict:
    # ScanUpload = { scan_type: str, file_id: str }
    ...
    return {"success": True}
```

Router is mounted without prefix override (`app.include_router(legal_profile_router)`) but has `prefix="/api/legal-profile"` on the router itself — making the endpoint `/api/legal-profile/scan`. Frontend calls `legal-profile/scan` with `/api` prefixUrl → resolves to `/api/legal-profile/scan`. Body and response match perfectly. No action needed.

---

## N-07 — GET contracts/mine vs GET contracts

**Verdict: Dead file with wrong path; live hooks use the correct `GET /contracts`.**

### The broken file (web_portal/src/api/contracts.ts:14-15) — NOT used by hooks
```typescript
export const getMyContracts = (): Promise<ContractListResponse> =>
  api.get('contracts/mine').json<ContractListResponse>()
  // ← "contracts/mine" does NOT exist on backend → 404
```

### The live file (web_portal/src/api/legal.ts:52-54) — used by all hooks
```typescript
export async function getMyContracts() {
  return api.get('contracts').json<{ items: Contract[] }>()
  // ← "contracts" EXISTS on backend ✓
}
```

### Backend (src/api/routers/contracts.py:95-108)
```python
@router.get("")   # prefix="/api/contracts" → GET /api/contracts
async def list_contracts(current_user, session, type=None, status=None) -> ContractListResponse:
    # returns ContractListResponse { items: list[ContractResponse], total: int }
```

**Hook import chain:**
- `web_portal/src/hooks/useContractQueries.ts:2` → imports `getMyContracts` from `@/api/legal` ✓
- `web_portal/src/hooks/queries.ts:4` → imports `getMyContracts` from `@/api/legal` ✓
- `web_portal/src/api/contracts.ts` → defines `getMyContracts` with wrong path, but **no file imports it**

**Fix owner: frontend (web_portal)** — remove or fix `web_portal/src/api/contracts.ts` to avoid confusion (dead code with a 404 path).

---

## N-08 — contracts/accept-rules body divergence

**Verdict: web_portal `acceptRules()` function sends empty body → 422 on backend.**

### Backend schema (src/api/schemas/legal_profile.py:118-120)
```python
class AcceptRulesRequest(BaseModel):
    accept_platform_rules: bool   # required, no default
    accept_privacy_policy: bool   # required, no default
```

### Backend handler (src/api/routers/contracts.py:74-92)
```python
@router.post("/accept-rules", ...)
async def accept_rules(data: AcceptRulesRequest, ...) -> dict:
    if not (data.accept_platform_rules and data.accept_privacy_policy):
        raise HTTPException(400, "Both must be accepted")
    ...
```

### mini_app — CORRECT (mini_app/src/api/contracts.ts:19-21)
```typescript
acceptRules: () =>
  api.post('contracts/accept-rules', { json: { accept_platform_rules: true, accept_privacy_policy: true } })
    .json<{ success: boolean }>(),
```

### web_portal — TWO callers, one broken

**Broken:** `web_portal/src/api/legal.ts:64-66`
```typescript
export async function acceptRules() {
  return api.post('contracts/accept-rules').json()  // ← NO body → FastAPI returns 422
}
```
Called from: `web_portal/src/hooks/useContractQueries.ts:37-39`

**Correct (direct call):** `web_portal/src/screens/common/AcceptRules.tsx:40-42`
```typescript
await api.post('contracts/accept-rules', {
  json: { accept_platform_rules: true, accept_privacy_policy: true },
})
```

**Fix owner: frontend (web_portal)** — `web_portal/src/api/legal.ts:acceptRules()` must add `{ json: { accept_platform_rules: true, accept_privacy_policy: true } }` to the POST body.

---

## Additional Mismatches Found (outside N-04..N-08)

> Per sprint rules: described here, not fixed in this sprint.

### Extra-1: web_portal `signContract` — wrong body field name

**File:** `web_portal/src/api/legal.ts:60-62`
```typescript
export async function signContract(id: number, method: string) {
  return api.post(`contracts/${id}/sign`, { json: { method } }).json<Contract>()
  //                                              ^^^^^^ sends "method"
}
```

**Backend schema** (`src/api/schemas/legal_profile.py:113-115`):
```python
class ContractSignRequest(BaseModel):
    signature_method: SignatureMethod   # expects "signature_method"
    sms_code: str | None = None
```

**mini_app correct** (`mini_app/src/api/contracts.ts:14-15`):
```typescript
sign: (id, method, smsCode?) =>
  api.post(`contracts/${id}/sign`, { json: { signature_method: method, sms_code: smsCode } })
```

**Impact:** Every sign attempt from web_portal sends `method` which backend ignores (422 or default-fails).  
**Fix owner:** frontend (web_portal) — rename `method` → `signature_method` in body.

---

### Extra-2: web_portal `requestKep` — wrong path AND missing body field

**File:** `web_portal/src/api/legal.ts:74-76` and `web_portal/src/components/contracts/KepWarning.tsx:22-25`

```typescript
// legal.ts:74-76
export async function requestKep(contractId: number, email: string) {
  return api.post(`contracts/${contractId}/request-kep`, { json: { email } }).json<Contract>()
  //             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ wrong — has contractId in path
  //                                                         missing contract_id in body
}

// KepWarning.tsx:22-25
api.post(`contracts/${contractId}/request-kep`, { json: { email } }).json()
//                                               same two bugs
```

**Backend route** (`src/api/routers/contracts.py:160-177`):
```python
@router.post("/request-kep")  # → POST /api/contracts/request-kep (no {id} in path)
async def request_kep(data: KepRequestBody, ...):
    # KepRequestBody = { contract_id: int, email: str }
```

**mini_app correct** (`mini_app/src/api/contracts.ts:22-23`):
```typescript
requestKep: (contractId, email) =>
  api.post('contracts/request-kep', { json: { contract_id: contractId, email } })
```

**Impact:** web_portal KEP requests hit a non-existent path (`/api/contracts/{id}/request-kep` → 404 or route conflict with `GET /{contract_id}`).  
**Fix owner:** frontend (web_portal) — remove `${contractId}` from path, add `contract_id` to body.

---

### Extra-3: D-07 verification — GET /api/billing/invoice/{id}

The docstring at the top of `src/api/routers/billing.py:9` lists `GET /api/billing/invoice/{id}` as an endpoint, but **no such route is implemented** in that file. The equivalent functionality is `GET /api/billing/topup/{payment_id}/status` (billing.py:203).

Mini_app calls `billing/topup/${paymentId}/status` which matches the real endpoint. No frontend is calling `billing/invoice/{id}`. The docstring is stale documentation — not a runtime issue. Recommend: remove the stale line from the docstring.

---

### Extra-4: Campaign actions — paths are CORRECT

Mini_app calls:
- `POST campaigns/${id}/start` → backend `src/api/routers/campaigns.py:294` with prefix `/api/campaigns` ✓
- `POST campaigns/${id}/cancel` → backend line 336 ✓
- `POST campaigns/${id}/duplicate` → backend line 540 ✓

---

## Recommendations: Fix Order

### Priority 1 — P0 runtime errors (will 422/404 in production)

| Fix | File | Change |
|-----|------|--------|
| N-08 | `web_portal/src/api/legal.ts:65` | Add `{ json: { accept_platform_rules: true, accept_privacy_policy: true } }` |
| Extra-1 | `web_portal/src/api/legal.ts:61` | Rename `{ method }` → `{ signature_method: method, sms_code: undefined }` |
| Extra-2 | `web_portal/src/api/legal.ts:75` + `KepWarning.tsx:24` | Path: `contracts/request-kep`; body: add `contract_id` |

### Priority 2 — Data rendering broken (UI shows undefined)

| Fix | File | Change |
|-----|------|--------|
| N-05 | `src/api/routers/channels.py:1034-1044` | Rename `member_count→subscribers`, `er→last_er`; add `topic`, `rating` to `ComparisonChannelItem` |

Alternative for N-05: fix the frontend type alias (`ChannelCompareResponse`) to match backend field names. Backend is the canonical source for field semantics, so backend fix is preferred.

### Priority 3 — Dead code cleanup (no runtime impact)

| Fix | File | Change |
|-----|------|--------|
| N-07 | `web_portal/src/api/contracts.ts` | Delete or rewrite to use `GET contracts` instead of `contracts/mine` |
| Extra-3 | `src/api/routers/billing.py:9` | Remove stale `GET /api/billing/invoice/{id}` from docstring |

---

## False Alarms from Original Audit

| Finding | Status |
|---------|--------|
| N-04 POST billing/credits | Endpoint exists at `billing.py:429`, body/response match |
| N-06 POST legal-profile/scan | Endpoint exists at `legal_profile.py:96`, body/response match |

The original Phase 3 audit likely missed these endpoints because both use non-obvious schema reuse (`TopupRequest` for credits) or the prefix is defined directly on the router object rather than in `include_router`.

---

🔍 Verified against: `d195386` | 📅 Updated: 2026-04-17T00:00:00Z
