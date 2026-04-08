# RekHarborBot — Complete API Reference

> **RekHarborBot AAA Documentation v4.3 | April 2026**
> **Document:** AAA-02_API_REFERENCE
> **Verified against:** HEAD @ 2026-04-08 | Source: `src/api/routers/` (26 routers), `src/api/schemas/`

---

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [Endpoint Inventory by Domain](#2-endpoint-inventory-by-domain)
3. [Request/Response Schemas](#3-requestresponse-schemas)
4. [Error Codes](#4-error-codes)
5. [Rate Limiting](#5-rate-limiting)
6. [Webhook Specifications](#6-webhook-specifications)
7. [OpenAPI Specification Notes](#7-openapi-specification-notes)
8. [Breaking Change History](#8-breaking-change-history)

---

## 1. Authentication Flow

### 1.1 Telegram Mini App Authentication

**Endpoint:** `POST /api/auth/telegram`

**Request:**
```json
{
  "init_data": "query_id=AAH...&user=%7B%22id%22%3A12345%7D&hash=abc..."
}
```

**Process:**
1. Client extracts `Telegram.WebApp.initData` (signed query string from Telegram)
2. Server validates HMAC-SHA256: `HMAC-SHA256(data_check_string, BOT_TOKEN) == hash`
3. Server extracts `user.id` → finds or creates User by `telegram_id`
4. Server creates JWT: `{user_id, telegram_id, plan, exp=now+24h}`
5. Server returns `{access_token, user}`

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "telegram_id": 12345,
    "username": "testuser",
    "first_name": "Test",
    "plan": "free",
    "is_admin": false,
    "balance_rub": "0.00",
    "earned_rub": "0.00"
  }
}
```

**Source:** `src/api/routers/auth.py:105`

### 1.2 One-Time Code Login (Web Portal)

**Endpoint:** `POST /api/auth/login-code`

**Rate limit:** 10 requests per hour per phone/user

**Response (200):**
```json
{
  "success": true,
  "message": "Code sent"
}
```

**Source:** `src/api/routers/auth_login_code.py`

### 1.3 Telegram Login Widget

**Endpoint:** `POST /api/auth/telegram-login-widget`

**Rate limit:** 5 requests per minute

**Source:** `src/api/routers/auth_login_widget.py`

### 1.4 JWT Authentication (Protected Endpoints)

**Header:** `Authorization: Bearer <jwt_token>`

**JWT Payload:**
```json
{
  "user_id": 1,
  "telegram_id": 12345,
  "plan": "starter",
  "exp": 1712620800
}
```

**Verification:** `get_current_user()` dependency decodes JWT, validates signature (HS256), checks expiry, fetches User from DB.

**Source:** `src/api/dependencies.py`

### 1.5 Admin Authentication

Admin endpoints require:
1. Valid JWT token
2. `User.is_admin == True`

**Dependency:** `get_admin_user()` — extends `get_current_user()` with admin check.

**Source:** `src/api/dependencies.py`

### 1.6 Get Current User

**Endpoint:** `GET /api/auth/me`

**Auth:** JWT required

**Response (200):**
```json
{
  "id": 1,
  "telegram_id": 12345,
  "username": "testuser",
  "first_name": "Test",
  "plan": "starter",
  "is_admin": false,
  "balance_rub": "15000.00",
  "earned_rub": "3200.00",
  "credits": 0,
  "is_active": true,
  "current_role": "advertiser",
  "advertiser_xp": 150,
  "owner_xp": 0,
  "advertiser_level": 3,
  "owner_level": 1,
  "ai_uses_count": 2,
  "ai_uses_reset_at": "2026-05-01T00:00:00",
  "login_streak_days": 5,
  "max_streak_days": 12,
  "referral_code": "abc123",
  "notifications_enabled": true,
  "legal_status_completed": false
}
```

**Source:** `src/api/routers/auth.py:122`

---

## 2. Endpoint Inventory by Domain

### 2.1 Health (`/health`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/health` | None | Health check | `health.py:23` |
| GET | `/health/balances` | X-Admin-Key | Balance invariants check | `health.py:35` |

### 2.2 Users (`/api/users`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/users/me` | JWT | Current user profile | `users.py` |
| GET | `/api/users/{user_id}` | JWT | User by ID | `users.py` |
| PATCH | `/api/users/me` | JWT | Update current user | `users.py` |
| GET | `/api/users/{user_id}/badges` | JWT | User badges | `users.py` |
| GET | `/api/users/{user_id}/stats` | JWT | User statistics | `users.py` |

### 2.3 Campaigns (`/api/campaigns`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| POST | `/api/campaigns` | JWT | Create campaign (201) | `campaigns.py:95` |
| GET | `/api/campaigns` | JWT | List campaigns (paginated) | `campaigns.py:119` |
| GET | `/api/campaigns/{id}` | JWT | Get campaign by ID | `campaigns.py:154` |
| PATCH | `/api/campaigns/{id}` | JWT | Update campaign | `campaigns.py:187` |
| DELETE | `/api/campaigns/{id}` | JWT | Delete campaign (204) | `campaigns.py:225` |
| POST | `/api/campaigns/{id}/start` | JWT | Start campaign | `campaigns.py:254` |
| POST | `/api/campaigns/{id}/cancel` | JWT | Cancel campaign | `campaigns.py:287` |
| GET | `/api/campaigns/list` | JWT | List campaigns (alternative) | `campaigns.py:348` |
| GET | `/api/campaigns/{id}/stats` | JWT | Campaign statistics | `campaigns.py:396` |
| POST | `/api/campaigns/{id}/duplicate` | JWT | Duplicate campaign | `campaigns.py:433` |

**Business Rules:**
- Campaigns are built on `PlacementRequest` model (legacy naming: aliased as `Campaign` in some frontend code)
- User must own the campaign to modify it (403 if not)
- Cannot delete completed campaigns

### 2.4 Channels (`/api/channels`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/channels/` | JWT | List user's channels | `channels.py:130` |
| POST | `/api/channels/` | JWT | Add channel | `channels.py:262` |
| POST | `/api/channels/check` | JWT | Check channel before adding | `channels.py:148` |
| DELETE | `/api/channels/{id}` | JWT | Remove channel (204) | `channels.py:374` |
| PATCH | `/api/channels/{id}/category` | JWT | Update channel category | `channels.py:416` |
| GET | `/api/channels/available` | JWT | Search available channels | `channels.py:502` |
| GET | `/api/channels/stats` | None | Public channel statistics | `channels.py:630` |
| GET | `/api/channels/preview` | JWT | Mediakit preview | `channels.py:700` |
| POST | `/api/channels/{id}/mediakit` | JWT | Create/update mediakit | `channels.py` |
| GET | `/api/channels/compare/preview` | JWT | Comparison preview | `channels.py` |

**Business Rules:**
- Bot must be admin in channel with: `post_messages`, `delete_messages`, `pin_messages`
- Channel must not already be added by this owner
- Channel rules validation (no gambling, 18+, etc.)

### 2.5 Channel Settings (`/api/channel-settings`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/channel-settings/{channel_id}` | JWT | Get settings | `channel_settings.py` |
| PATCH | `/api/channel-settings/{channel_id}` | JWT | Update settings | `channel_settings.py` |

**Updatable fields:** `price_per_post`, format flags (`allow_format_*`), schedule (`publish_start_time`, `publish_end_time`), `max_posts_per_day`, `max_posts_per_week`

### 2.6 Billing (`/api/billing`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| POST | `/api/billing/topup` | JWT | Create top-up (YooKassa) | `billing.py:120` |
| GET | `/api/billing/topup/{payment_id}/status` | JWT | Check payment status | `billing.py:163` |
| GET | `/api/billing/plans` | None | List available plans | `billing.py:196` |
| GET | `/api/billing/balance` | JWT | Get balance | `billing.py:259` |
| GET | `/api/billing/history` | JWT | Transaction history | `billing.py:290` |
| POST | `/api/billing/credits` | JWT | Buy credits (for plans) | `billing.py:340` |
| POST | `/api/billing/plan` | JWT | Change plan | `billing.py:371` |
| GET | `/api/billing/invoice/{invoice_id}` | JWT | Get invoice (⚠️ returns 404 — legacy) | `billing.py:421` |
| POST | `/api/billing/webhooks/yookassa` | IP whitelist | YooKassa webhook | `billing.py:437` |

**Business Rules:**
- MIN_TOPUP=500, MAX_TOPUP=300000
- YooKassa fee: 3.5% on top of desired balance
- Webhook credits `metadata["desired_balance"]`, NOT `gross_amount`
- Only `method=yookassa` supported (USDT removed in v4.2)

### 2.7 Placements (`/api/placements`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/placements/` | JWT | List placements | `placements.py:174` |
| POST | `/api/placements/` | JWT | Create placement request | `placements.py:217` |
| GET | `/api/placements/{id}` | JWT | Get placement details | `placements.py:294` |
| POST | `/api/placements/{id}/accept` | JWT | Owner accepts | `placements.py:313` |
| POST | `/api/placements/{id}/reject` | JWT | Owner rejects | `placements.py:349` |
| POST | `/api/placements/{id}/counter` | JWT | Owner counter-offer | `placements.py:394` |
| POST | `/api/placements/{id}/accept-counter` | JWT | Advertiser accepts counter | `placements.py:429` |
| POST | `/api/placements/{id}/pay` | JWT | Advertiser pays (escrow) | `placements.py:464` |
| DELETE | `/api/placements/{id}` | JWT | Delete placement | `placements.py:512` |
| PATCH | `/api/placements/{id}` | JWT | Unified action endpoint | `placements.py:575` |

**PATCH Actions:**
| Action | Description | Status Transition |
|--------|-------------|-------------------|
| `accept` | Owner accepts | `pending_owner` → `pending_payment` |
| `reject` | Owner rejects | `pending_owner` → `cancelled` |
| `counter` | Owner counter-offer | `pending_owner` → `counter_offer` |
| `pay` | Advertiser pays | `pending_payment` → `escrow` |
| `cancel` | Advertiser cancels | `pending_owner/pending_payment` → `cancelled` |
| `accept-counter` | Advertiser accepts counter | `counter_offer` → `pending_payment` |

### 2.8 Payouts (`/api/payouts`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/payouts/` | JWT | List user's payouts | `payouts.py:50` |
| POST | `/api/payouts/` | JWT | Create payout request | `payouts.py:84` |
| GET | `/api/payouts/{id}` | JWT | Get payout details | `payouts.py:66` |

**Request Schema:**
```json
{
  "amount": 10000,
  "payment_details": "Card: 4276 ******** 1234, Bank: Sberbank"
}
```

**Response Schema:**
```json
{
  "id": 1,
  "owner_id": 5,
  "gross_amount": "10000.00",
  "fee_amount": "150.00",
  "net_amount": "9850.00",
  "status": "pending",
  "requisites": "Card: 4276 ******** 1234, Bank: Sberbank",
  "created_at": "2026-04-08T10:00:00",
  "processed_at": null,
  "rejection_reason": null
}
```

**Business Rules:**
- MIN_PAYOUT=1000
- PAYOUT_FEE_RATE=0.015 (1.5%)
- Cannot have active PayoutRequest (pending/processing) → 409
- earned_rub must >= gross_amount
- Velocity check: payouts_30d / topups_30d ≤ 0.80

### 2.9 Disputes (`/api/disputes`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/disputes/` | JWT | List user's disputes | `disputes.py:91` |
| POST | `/api/disputes/` | JWT | Create dispute | `disputes.py:124` |
| GET | `/api/disputes/{id}` | JWT | Get dispute details | `disputes.py:108` |
| PATCH | `/api/disputes/{id}` | JWT | Owner explanation | `disputes.py:183` |
| GET | `/api/disputes/evidence/{placement_id}` | JWT | Get evidence | `disputes.py:244` |
| GET | `/api/disputes/admin/disputes` | Admin JWT | Admin view all disputes | `disputes.py:370` |
| POST | `/api/disputes/admin/disputes/{id}/resolve` | Admin JWT | Admin resolves | `disputes.py:448` |

### 2.10 Feedback (`/api/feedback`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| POST | `/api/feedback/` | JWT | Submit feedback (201) | `feedback.py:35` |
| GET | `/api/feedback/` | JWT | List user's feedback | `feedback.py:61` |
| GET | `/api/feedback/{id}` | JWT | Get feedback details | `feedback.py:74` |
| GET | `/api/feedback/admin/` | Admin JWT | Admin list all | `feedback.py:102` |
| GET | `/api/feedback/admin/{id}` | Admin JWT | Admin view | `feedback.py:163` |
| POST | `/api/feedback/admin/{id}/respond` | Admin JWT | Admin respond | `feedback.py:200` |
| PATCH | `/api/feedback/admin/{id}/status` | Admin JWT | Admin update status | `feedback.py:267` |

### 2.11 Admin (`/api/admin/*` via `/api` prefix)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/admin/stats` | Admin | Platform statistics | `admin.py:149` |
| GET | `/api/admin/users` | Admin | List users (paginated) | `admin.py:187` |
| GET | `/api/admin/users/{user_id}` | Admin | User detail with stats | `admin.py:386` |
| PATCH | `/api/admin/users/{user_id}` | Admin | Update user (role, plan, is_admin) | `admin.py:441` |
| POST | `/api/admin/users/{user_id}/balance` | Admin | Adjust user balance | `admin.py:508` |
| GET | `/api/admin/legal-profiles` | Admin | List legal profiles | `admin.py:310` |
| POST | `/api/admin/legal-profiles/{user_id}/verify` | Admin | Verify legal profile | `admin.py:340` |
| POST | `/api/admin/legal-profiles/{user_id}/unverify` | Admin | Unverify legal profile | `admin.py:370` |
| GET | `/api/admin/audit-logs` | Admin | Audit log viewer | `admin.py:406` |
| GET | `/api/admin/platform-settings` | Admin | Platform settings | `admin.py:476` |
| PUT | `/api/admin/platform-settings` | Admin | Update settings | `admin.py:498` |

### 2.12 Legal Profile (`/api/legal-profile`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/legal-profile/me` | JWT | Get my legal profile | `legal_profile.py:57` |
| POST | `/api/legal-profile` | JWT | Create legal profile (201) | `legal_profile.py:66` |
| PATCH | `/api/legal-profile` | JWT | Update legal profile | `legal_profile.py:77` |
| POST | `/api/legal-profile/scan` | JWT | Upload document scan | `legal_profile.py:88` |
| GET | `/api/legal-profile/required-fields` | JWT | Required fields per status | `legal_profile.py:102` |
| POST | `/api/legal-profile/validate-inn` | JWT | Validate INN | `legal_profile.py:113` |
| POST | `/api/legal-profile/validate-entity` | JWT | Validate entity data | `legal_profile.py:122` |

### 2.13 Contracts (`/api/contracts`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| POST | `/api/contracts/generate` | JWT | Generate contract (201) | `contracts.py:52` |
| POST | `/api/contracts/accept-rules` | JWT | Accept platform rules | `contracts.py:67` |
| GET | `/api/contracts` | JWT | List user's contracts | `contracts.py:84` |
| GET | `/api/contracts/{id}` | JWT | Get contract details | `contracts.py:96` |
| POST | `/api/contracts/{id}/sign` | JWT | Sign contract | `contracts.py:113` |
| POST | `/api/contracts/request-kep` | JWT | Request KEP (qualified signature) | `contracts.py:138` |
| GET | `/api/contracts/{id}/pdf` | JWT | Download contract PDF | `contracts.py:173` |
| GET | `/api/contracts/platform-rules/text` | None | Get platform rules HTML | `contracts.py:197` |

### 2.14 Analytics (`/api/analytics`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| GET | `/api/analytics/summary` | JWT | User analytics summary | `analytics.py:115` |
| GET | `/api/analytics/activity` | JWT | Activity data (days param) | `analytics.py:153` |
| GET | `/api/analytics/top-channels` | JWT (PRO+) | Top channels by reach | `analytics.py:197` |
| GET | `/api/analytics/topics` | JWT (PRO+) | Topic analytics | `analytics.py:233` |
| GET | `/api/analytics/campaigns/{id}/ai-insights` | JWT (PRO+) | AI-powered insights | `analytics.py:285` |
| GET | `/api/analytics/advertiser` | JWT | Advertiser analytics | `analytics.py:368` |
| GET | `/api/analytics/owner` | JWT | Owner analytics | `analytics.py:449` |
| GET | `/api/analytics/stats/public` | None | Public platform stats | `analytics.py:543` |
| GET | `/api/analytics/r/{short_code}` | None | Tracking redirect (302) | `analytics.py:564` |

### 2.15 AI (`/api/ai`)

| Method | Path | Auth | Description | Source |
|--------|------|------|-------------|--------|
| POST | `/api/ai/generate-ad-text` | JWT | Generate ad text via Mistral | `ai.py:33` |

**Request:**
```json
{
  "description": "Promo code SALE20 for 20% off sneakers",
  "topic": "fashion",
  "count": 3
}
```

### 2.16 Reputation (`/api/reputation`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/reputation/me` | JWT | Current user reputation |
| GET | `/api/reputation/me/history` | JWT | Reputation history |
| GET | `/api/reputation/{user_id}` | JWT | User reputation |
| GET | `/api/reputation/{user_id}/history` | JWT | User reputation history |

### 2.17 Reviews (`/api/reviews`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/reviews/` | JWT | Create review (rating 1-5) |
| GET | `/api/reviews/placement/{placement_id}` | JWT | Both reviews for placement |

### 2.18 Categories (`/api/categories`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/categories/` | None | List all categories |
| GET | `/api/categories/{slug}` | None | Get category details |

### 2.19 ORD (`/api/ord`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/ord/{placement_id}` | JWT | Get ORD registration status |
| POST | `/api/ord/register` | JWT | Register creative with ORD |

### 2.20 Acts (`/api/acts`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/acts/mine` | JWT | List my acts |
| GET | `/api/acts/{act_id}` | JWT | Get act details |
| POST | `/api/acts/{act_id}/sign` | JWT | Sign act |
| GET | `/api/acts/{act_id}/pdf` | JWT | Download act PDF |

### 2.21 Document Validation (`/api/document-validation`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/document-validation/upload` | JWT | Upload document for OCR |
| GET | `/api/document-validation/{upload_id}/status` | JWT | Check processing status |
| GET | `/api/document-validation` | JWT | List uploads |
| DELETE | `/api/document-validation/{upload_id}` | JWT | Delete upload |

### 2.22 Uploads (`/api/uploads`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/uploads/video/{session_id}` | JWT | Get video upload result |

### 2.23 Webhooks (`/webhooks`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhooks/glitchtip-alert` | X-Webhook-Token | GlitchTip webhook handler |
| POST | `/webhooks/yookassa` | IP whitelist | YooKassa payment webhook |

---

## 3. Request/Response Schemas

### 3.1 Key Pydantic Schemas

**TopupRequest** (`src/api/schemas/billing.py`):
```python
class TopupRequest(BaseModel):
    desired_amount: Decimal = Field(ge=500, le=300000)
    method: str = "yookassa"  # only supported method
```

**PlacementCreateRequest** (`src/api/schemas/placement.py`):
```python
class PlacementCreateRequest(BaseModel):
    channel_id: int
    proposed_price: Decimal
    publication_format: str  # post_24h, post_48h, post_7d, pin_24h, pin_48h
    final_text: str
    scheduled_date: datetime | None = None
    media_url: str | None = None
```

**CounterOfferRequest**:
```python
class CounterOfferRequest(BaseModel):
    counter_price: Decimal = Field(ge=100)
    counter_schedule: str | None = None
    counter_comment: str | None = None
```

**DisputeCreate**:
```python
class DisputeCreate(BaseModel):
    placement_id: int
    reason: str  # post_removed_early, bot_kicked, advertiser_complaint
    comment: str
```

**DisputeResolveRequest**:
```python
class DisputeResolveRequest(BaseModel):
    resolution: str  # owner_fault, advertiser_fault, technical, partial
    split_amount: Decimal | None = None  # for partial resolution
```

**LegalProfileCreateRequest**:
```python
class LegalProfileCreateRequest(BaseModel):
    legal_status: str  # legal_entity, individual_entrepreneur, self_employed, individual
    tax_regime: str | None  # usn, osno, npd, ndfl, patent
    inn: str  # encrypted on server side
    kpp: str | None
    company_name: str | None
    full_name: str | None
    # ... bank details, passport, etc.
```

**ContractSignRequest**:
```python
class ContractSignRequest(BaseModel):
    method: str  # button_accept, sms_code
    sms_code: str | None
    ip_address: str | None
```

---

## 4. Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Validation error, invalid amount, missing fields |
| 401 | Unauthorized | Missing/invalid JWT token |
| 403 | Forbidden | Not owner, not admin, insufficient plan |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Active payout exists, duplicate resource |
| 410 | Gone | Placement expired |
| 422 | Unprocessable Entity | Pydantic validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 502 | Bad Gateway | Mistral AI API error |
| 503 | Service Unavailable | AI provider unavailable |

---

## 5. Rate Limiting

| Endpoint | Limit | Implementation |
|----------|-------|----------------|
| `POST /api/auth/login-code` | 10/hour per user | In-memory dict with TTL |
| `POST /api/auth/telegram-login-widget` | 5/min per IP | In-memory dict with TTL |
| Bot handlers | Configurable | Throttling middleware (per-user, per-chat) |
| API general | None (MVP) | Planned post-MVP |

---

## 6. Webhook Specifications

### 6.1 YooKassa Webhook

**Endpoint:** `POST /api/billing/webhooks/yookassa`

**Authentication:** IP whitelist (YooKassa server IPs)

**Request body:**
```json
{
  "type": "payment.succeeded",
  "event": "payment.succeeded",
  "object": {
    "id": "2d3b5e7f-000f-5000-8000-1a8b4e7c2d3e",
    "status": "succeeded",
    "amount": { "value": "10350.00", "currency": "RUB" },
    "metadata": {
      "user_id": "123",
      "desired_balance": "10000"
    }
  }
}
```

**Processing:**
1. Verify source IP
2. Find `YookassaPayment` by `object.id`
3. Credit `metadata["desired_balance"]` to `user.balance_rub`
4. Update `YookassaPayment.status`
5. Create `Transaction` record
6. Send notification

**Idempotency:** Duplicate webhooks are silently ignored if payment already processed.

**Source:** `src/api/routers/billing.py:437`, `src/core/services/billing_service.py:process_topup_webhook()`

---

## 7. OpenAPI Specification Notes

- **Title:** RekHarborBot API
- **Version:** v4.3
- **Base URL:** `/api/`
- **Auth scheme:** Bearer JWT (HS256)
- **Tags:** Auth, Users, Campaigns, Channels, Channel Settings, Billing, Placements, Payouts, Disputes, Feedback, Admin, Legal Profile, Contracts, Acts, ORD, Analytics, AI, Reputation, Reviews, Categories, Uploads, Webhooks, Health
- **Schemas:** All Pydantic v2 models auto-documented
- **Deprecated endpoints:** `/api/billing/invoice/{id}` (always returns 404)

---

## 8. Breaking Change History

| Version | Date | Change | Impact |
|---------|------|--------|--------|
| v4.3 | 2026-03-18 | CryptoBot removed, manual payouts only | Payout flow changed |
| v4.3 | 2026-03-18 | B2B packages removed | No more B2B button/callback |
| v4.3 | 2026-03-18 | `is_banned` → `is_active` | User model field renamed |
| v4.2 | 2026-02-XX | `PLATFORM_COMMISSION` 0.20 → 0.15 | Financial calculation change |
| v4.2 | 2026-02-XX | `MIN_TOPUP` 100 → 500 | Minimum top-up increased |
| v4.2 | 2026-02-XX | `MIN_PAYOUT` 500 → 1000 | Minimum payout increased |
| v4.2 | 2026-02-XX | Stars/USDT removed | Only YooKassa supported |
| v4.2 | 2026-02-XX | `NPD_TAX_RATE` removed | Tax model simplified |

---

🔍 Verified against: HEAD @ 2026-04-08 | Source files: `src/api/routers/` (26 files), `src/api/schemas/` (8 files), `src/api/dependencies.py`
✅ Validation: passed | All endpoints verified against actual router code | Schemas match Pydantic models
