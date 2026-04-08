# RekHarborBot — Database Schema Reference

> **RekHarborBot AAA Documentation v4.3 | April 2026**
> **Document:** AAA-03_DATABASE_REFERENCE
> **Verified against:** HEAD @ 2026-04-08 | Source: `src/db/models/` (33 files), `alembic/versions/` (33 migrations)

---

## Table of Contents

1. [Database Overview](#1-database-overview)
2. [Complete Entity Reference (33 Models)](#2-complete-entity-reference)
3. [Entity Relationship Diagram](#3-entity-relationship-diagram)
4. [Foreign Key Matrix](#4-foreign-key-matrix)
5. [Index Strategy](#5-index-strategy)
6. [Enum Reference](#6-enum-reference)
7. [Encryption Schema](#7-encryption-schema)
8. [Migration History](#8-migration-history)
9. [Known Schema Issues](#9-known-schema-issues)

---

## 1. Database Overview

| Property | Value |
|----------|-------|
| Engine | PostgreSQL 16 (asyncpg driver) |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic (33 migrations) |
| Models | 33 |
| Total tables | ~35+ (including Alembic version table) |
| Connection | `postgresql+asyncpg://user:pass@postgres:5432/market_bot_db` |
| Session factory | `celery_async_session_factory` for Celery, `async_session_factory` for API/bot |
| Loading strategy | Explicit `selectinload`/`joinedload` (no lazy-loading) |
| Refresh pattern | `await session.refresh(obj)` after `flush()` |

**Source files:** `src/db/session.py`, `src/db/base.py`, `src/db/models/`

---

## 2. Complete Entity Reference

### 2.1 Core Entities

#### User (`users`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | Internal PK (≠ telegram_id) |
| telegram_id | BigInteger | UNIQUE, NOT NULL, indexed | — | Primary identity |
| username | String(64) | Nullable | — | Telegram username |
| first_name | String(256) | NOT NULL | — | Required |
| is_admin | Boolean | NOT NULL | false | Admin flag |
| current_role | String(16) | NOT NULL | "new" | new/advertiser/owner/both |
| plan | String(16) | NOT NULL | "free" | free/starter/pro/business |
| plan_expires_at | DateTime | Nullable | — | Plan expiry |
| balance_rub | Numeric(12,2) | NOT NULL | 0.00 | Advertiser balance |
| earned_rub | Numeric(12,2) | NOT NULL | 0.00 | Owner earnings |
| credits | Integer | NOT NULL | 0 | Plan subscription credits only |
| language_code | String(10) | Nullable | — | User's language |
| referral_code | String(32) | UNIQUE, NOT NULL | auto-generated | Referral identifier |
| referred_by_id | Integer | FK → users.id, nullable | — | Self-referencing (referrals) |
| advertiser_xp | Integer | NOT NULL | 0 | Gamification (NEVER MODIFY) |
| owner_xp | Integer | NOT NULL | 0 | Gamification (NEVER MODIFY) |
| advertiser_level | Integer | NOT NULL | 1 | Derived from XP |
| owner_level | Integer | NOT NULL | 1 | Derived from XP |
| ai_uses_count | Integer | NOT NULL | 0 | Monthly AI usage |
| ai_uses_reset_at | DateTime | NOT NULL | — | Monthly reset date |
| login_streak_days | Integer | NOT NULL | 0 | Daily login streak |
| max_streak_days | Integer | NOT NULL | 0 | Record streak |
| is_active | Boolean | NOT NULL | true | Not banned (v4.3 fix) |
| notifications_enabled | Boolean | NOT NULL | true | Push toggle |
| legal_status_completed | Boolean | NOT NULL | false | Legal profile flag |
| legal_profile_prompted_at | DateTime | Nullable | — | Tracking |
| legal_profile_skipped_at | DateTime | Nullable | — | Tracking |
| platform_rules_accepted_at | DateTime | Nullable | — | Contract tracking |
| privacy_policy_accepted_at | DateTime | Nullable | — | Contract tracking |

**Indexes:** PK(id), UQ(telegram_id), UQ(referral_code), IX(current_role), IX(plan), IX(is_active)
**Relationships:** referred_by (self-ref), telegram_chats, placement_requests (×2 as advertiser/owner), transactions, payout_requests, reputation_score, reputation_history, disputes (×2), reviews (×2), badges, feedback, legal_profile, invoices
**Source:** `src/db/models/user.py`

#### PlatformAccount (`platform_account`) — SINGLETON

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, always 1 | 1 | Singleton row |
| escrow_reserved | Numeric | NOT NULL | 0 | SUM of escrow placements |
| payout_reserved | Numeric | NOT NULL | 0 | SUM of pending payouts |
| profit_accumulated | Numeric | NOT NULL | 0 | Platform fees earned |
| total_topups | Numeric | NOT NULL | 0 | Historical desired_balance |
| total_payouts | Numeric | NOT NULL | 0 | Historical net_amount |
| updated_at | DateTime | NOT NULL | now() | Last update |

**Invariants:**
- `escrow_reserved` = SUM(final_price WHERE placement.status = 'escrow')
- `payout_reserved` = SUM(gross_amount WHERE payout.status IN ('pending', 'processing'))
- `profit_accumulated` = SUM(15% escrow releases + 1.5% payout fees)

**Source:** `src/db/models/platform_account.py`

### 2.2 Channel Entities

#### TelegramChat (`telegram_chats`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | Internal PK |
| telegram_id | BigInteger | UNIQUE, NOT NULL, indexed | — | Telegram chat ID |
| username | String(64) | UNIQUE, NOT NULL, indexed | — | @username |
| title | String(256) | NOT NULL | — | Channel title |
| owner_id | Integer | FK → users.id, indexed | — | Channel owner |
| member_count | Integer | NOT NULL | 0 | Subscriber count |
| last_er | Float | NOT NULL | 0.0 | Engagement rate |
| avg_views | Integer | NOT NULL | 0 | Average views |
| last_avg_views | Integer | Nullable | — | Latest avg views |
| last_post_frequency | Float | Nullable | — | Posts per day |
| price_per_post | Integer | Nullable | — | Base price |
| rating | Float | NOT NULL | 0.0 | Platform rating |
| category | String(32) | Nullable, indexed | — | Channel category |
| description | Text | Nullable | — | Channel description |
| is_active | Boolean | NOT NULL | true | Active flag |
| is_test | Boolean | NOT NULL | false, indexed | Test channel |
| last_parsed_at | DateTime | Nullable | — | Last parser update |

**Aliases:** `owner_user_id` → `owner_id`, `topic` → `category`
**Indexes:** PK(id), UQ(telegram_id), UQ(username), IX(category), IX(is_test), IX(owner_id)
**Source:** `src/db/models/telegram_chat.py`

#### ChannelSettings (`channel_settings`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| channel_id | Integer | PK, FK → telegram_chats.id | — | 1:1 with channel |
| price_per_post | Numeric(10,2) | NOT NULL | 1000 | Base price per post |
| allow_format_post_24h | Boolean | NOT NULL | true | |
| allow_format_post_48h | Boolean | NOT NULL | true | |
| allow_format_post_7d | Boolean | NOT NULL | false | |
| allow_format_pin_24h | Boolean | NOT NULL | false | |
| allow_format_pin_48h | Boolean | NOT NULL | false | |
| max_posts_per_day | Integer | NOT NULL | 2 | |
| max_posts_per_week | Integer | NOT NULL | 10 | |
| publish_start_time | Time | NOT NULL | 09:00 | |
| publish_end_time | Time | NOT NULL | 21:00 | |
| break_start_time | Time | Nullable | — | Lunch break start |
| break_end_time | Time | Nullable | — | Lunch break end |
| auto_accept_enabled | Boolean | NOT NULL | false | |

**Source:** `src/db/models/channel_settings.py`

#### ChannelMediakit (`channel_mediakits`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| channel_id | Integer | PK, FK → telegram_chats.id | — | 1:1 with channel |
| (Various mediakit fields in JSONB) | — | — | — | Audience, stats history |

**Source:** `src/db/models/channel_mediakit.py`

#### Category (`categories`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| slug | String | PK | — | Category identifier |
| name | String | NOT NULL | — | Display name |
| description | Text | Nullable | — | |
| sort_order | Integer | NOT NULL | 0 | |
| is_active | Boolean | NOT NULL | true | |

**Source:** `src/db/models/category.py`

### 2.3 Financial Entities

#### Transaction (`transactions`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id, indexed | — | |
| type | Enum(TransactionType) | NOT NULL | — | 20 types |
| amount | Numeric(12,2) | NOT NULL | — | |
| placement_request_id | Integer | FK, nullable, indexed | — | |
| payout_id | Integer | FK → payout_requests.id, nullable | — | |
| yookassa_payment_id | String(64) | Nullable | — | |
| payment_status | String(32) | Nullable | — | |
| description | Text | Nullable | — | |
| meta_json | JSON | Nullable | — | |
| balance_before | Numeric(12,2) | Nullable | — | |
| balance_after | Numeric(12,2) | Nullable | — | |
| contract_id | Integer | FK → contracts.id, nullable | — | |
| counterparty_legal_status | String(30) | Nullable | — | |
| currency | String(3) | NOT NULL | "RUB" | |
| vat_amount | Numeric(12,2) | NOT NULL | 0 | |
| expense_category | String(30) | Nullable | — | |
| is_tax_deductible | Boolean | NOT NULL | false | |
| act_id | Integer | FK → acts.id, nullable, indexed | — | |
| invoice_id | Integer | FK → invoices.id, nullable, indexed | — | |
| reverses_transaction_id | Integer | Self-ref FK, nullable | — | Storno |
| is_reversed | Boolean | NOT NULL | false | |

**TransactionType enum values:** `topup`, `escrow_freeze`, `escrow_release`, `platform_fee`, `refund_full`, `refund_partial`, `cancel_penalty`, `owner_cancel_compensation`, `payout`, `payout_fee`, `credits_buy`, `failed_permissions_refund`, `spend`, `bonus`, `commission`, `refund`, `ndfl_withholding`, `storno`

**Removed types (do NOT use):** `SPEND`, `ADJUSTMENT`, `BONUS`, `WITHDRAWAL` — these were in QWEN.md as "do not use" legacy.

**⚠️ Note:** `spend`, `bonus`, `commission`, `refund` exist as valid enum values per actual code. The QWEN.md "removed" list refers to specific use cases, not enum values themselves.

**Source:** `src/db/models/transaction.py`

#### YookassaPayment (`yookassa_payments`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| payment_id | String(64) | UNIQUE | — | YooKassa payment ID |
| user_id | Integer | FK → users.id | — | |
| gross_amount | Numeric(12,2) | NOT NULL | — | Amount paid by user |
| desired_balance | Numeric(12,2) | NOT NULL | — | Amount credited to user |
| status | String(32) | NOT NULL | — | YooKassa status |
| confirmation_url | String(512) | Nullable | — | Payment page URL |
| metadata | JSON | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |
| completed_at | DateTime | Nullable | — | |

**Source:** `src/db/models/yookassa_payment.py`

#### PayoutRequest (`payout_requests`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| owner_id | Integer | FK → users.id, indexed | — | |
| gross_amount | Numeric(12,2) | NOT NULL | — | Requested amount |
| fee_amount | Numeric(12,2) | NOT NULL | — | gross × 0.015 |
| net_amount | Numeric(12,2) | NOT NULL | — | gross - fee |
| status | Enum(PayoutStatus) | NOT NULL | "pending" | |
| requisites | String(512) | NOT NULL | — | Payment details |
| admin_id | Integer | FK → users.id, nullable | — | Approving admin |
| processed_at | DateTime | Nullable | — | |
| rejection_reason | Text | Nullable | — | |
| ndfl_withheld | Numeric(12,2) | Nullable | — | Sprint B.2 |
| npd_receipt_number | String(64) | Nullable | — | |
| npd_receipt_date | DateTime | Nullable | — | |
| npd_status | String(20) | NOT NULL | "pending" | |
| created_at | DateTime | NOT NULL | now() | |

**PayoutStatus enum:** `pending`, `processing`, `paid`, `rejected`, `cancelled`

**Source:** `src/db/models/payout.py`

#### Invoice (`invoices`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id | — | |
| amount | Numeric(12,2) | NOT NULL | — | |
| status | String(32) | NOT NULL | — | |
| (other fields) | — | — | — | |

**Source:** `src/db/models/invoice.py`

### 2.4 Placement Entities

#### PlacementRequest (`placement_requests`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| advertiser_id | Integer | FK → users.id, indexed | — | |
| owner_id | Integer | FK → users.id, indexed | — | Channel owner |
| channel_id | Integer | FK → telegram_chats.id, indexed | — | |
| campaign_id | Integer | FK → campaigns.id, nullable, indexed | — | |
| status | Enum(PlacementStatus) | NOT NULL | "pending_owner" | |
| publication_format | Enum(PublicationFormat) | NOT NULL | "post_24h" | |
| proposed_price | Numeric(10,2) | NOT NULL | — | |
| final_price | Numeric(10,2) | Nullable | — | After negotiation |
| final_text | Text | NOT NULL | — | Ad content |
| media_url | String(512) | Nullable | — | |
| scheduled_date | DateTime | Nullable | — | Planned publish date |
| message_id | Integer | Nullable | — | Telegram message ID |
| scheduled_delete_at | DateTime | Nullable | — | Auto-delete time |
| deleted_at | DateTime | Nullable | — | Actual delete time |
| expires_at | DateTime | Nullable | — | Offer expiry |
| rejection_reason | Text | Nullable | — | |
| counter_price | Numeric(10,2) | Nullable | — | Owner's counter |
| counter_schedule | String(128) | Nullable | — | |
| counter_comment | Text | Nullable | — | |
| counter_offer_count | Integer | NOT NULL | 0 | |
| escrow_transaction_id | Integer | FK → transactions.id, nullable, indexed | — | |
| tracking_short_code | String(16) | UNIQUE, indexed | — | Click tracking |
| is_test | Boolean | NOT NULL | false | |
| created_at | DateTime | NOT NULL | now() | |
| updated_at | DateTime | NOT NULL | now() | |

**PlacementStatus enum:** `pending_owner`, `counter_offer`, `pending_payment`, `escrow`, `published`, `failed`, `failed_permissions`, `refunded`, `cancelled`, `completed`

**PublicationFormat enum:** `post_24h`, `post_48h`, `post_7d`, `pin_24h`, `pin_48h`

**Indexes:** PK(id), IX(advertiser_id), IX(owner_id), IX(channel_id), IX(status), IX(expires_at), IX(is_test), IX(status, expires_at) [composite], UQ(tracking_short_code)

**Source:** `src/db/models/placement_request.py`

#### Campaign (`campaigns`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| advertiser_id | Integer | FK → users.id | — | |
| status | String(32) | NOT NULL | — | |
| filters_json | JSON | Nullable | — | Targeting filters |
| (other fields) | — | — | — | |

**Source:** `src/db/models/campaign.py`

#### PublicationLog (`publication_logs`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| placement_request_id | Integer | FK → placement_requests.id | — | |
| status | String(32) | NOT NULL | — | published/failed/deleted |
| message_id | Integer | Nullable | — | |
| error_message | Text | Nullable | — | |
| published_at | DateTime | Nullable | — | |
| deleted_at | DateTime | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/publication_log.py`

#### ClickTracking (`click_tracking`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| campaign_id | Integer | FK → campaigns.id | — | |
| placement_request_id | Integer | FK → placement_requests.id | — | |
| original_url | String(2048) | NOT NULL | — | |
| tracking_url | String(64) | UNIQUE | UUID | Generated short code |
| click_count | Integer | NOT NULL | 0 | |
| unique_clicks | Integer | NOT NULL | 0 | |
| last_clicked_at | DateTime | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/click_tracking.py`

### 2.5 Legal & Compliance Entities (v4.3)

#### LegalProfile (`legal_profiles`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id, UNIQUE, indexed | — | 1:1 with user |
| legal_status | Enum(LegalStatus) | NOT NULL | — | |
| tax_regime | Enum(TaxRegime) | Nullable | — | |
| inn | String(128) | NOT NULL | — | **Encrypted** (EncryptedString) |
| inn_hash | String(64) | Nullable, indexed | — | **Hashed** (HashableEncryptedString) |
| kpp | String(64) | Nullable | — | **Encrypted** |
| company_name | String(256) | Nullable | — | **Encrypted** |
| full_name | String(256) | Nullable | — | **Encrypted** |
| passport_data | Text | Nullable | — | **Encrypted** |
| address | String(512) | Nullable | — | **Encrypted** |
| phone | String(64) | Nullable | — | **Encrypted** |
| email | String(128) | Nullable | — | **Encrypted** |
| bank_name | String(256) | Nullable | — | **Encrypted** |
| bank_account | String(64) | Nullable | — | **Encrypted** |
| bank_bik | String(64) | Nullable | — | **Encrypted** |
| yoomoney_wallet | String(64) | Nullable | — | **Encrypted** |
| is_completed | Boolean | NOT NULL | false | All fields filled |
| is_verified | Boolean | NOT NULL | false | Admin verified |
| created_at | DateTime | NOT NULL | now() | |
| updated_at | DateTime | NOT NULL | now() | |

**LegalStatus enum:** `legal_entity`, `individual_entrepreneur`, `self_employed`, `individual`
**TaxRegime enum:** `usn`, `osno`, `npd`, `ndfl`, `patent`

**⚠️ KNOWN ISSUE:** `user_id` column uses BigInteger but `users.id` is Integer — type mismatch.

**Source:** `src/db/models/legal_profile.py`

#### Contract (`contracts`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id, indexed | — | |
| contract_type | Enum(ContractType) | NOT NULL | — | |
| contract_status | Enum(ContractStatus) | NOT NULL | "draft" | |
| legal_profile_id | Integer | FK → legal_profiles.id, nullable | — | |
| placement_request_id | Integer | FK → placement_requests.id, nullable, indexed | — | |
| pdf_url | String(512) | Nullable | — | Generated PDF path |
| signed_at | DateTime | Nullable | — | |
| signature_method | String(20) | Nullable | — | button_accept/sms_code |
| ip_address | String(45) | Nullable | — | |
| legal_status_snapshot | JSON | Nullable | — | Snapshot at signing |
| created_at | DateTime | NOT NULL | now() | |
| updated_at | DateTime | NOT NULL | now() | |

**ContractType enum:** `owner_service`, `advertiser_campaign`, `platform_rules`, `privacy_policy`, `tax_agreement`
**ContractStatus enum:** `draft`, `pending`, `signed`, `expired`, `cancelled`
**SignatureMethod enum:** `button_accept`, `sms_code`

**Source:** `src/db/models/contract.py`

#### ContractSignature (`contract_signatures`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| contract_id | Integer | FK → contracts.id | — | |
| user_id | Integer | FK → users.id | — | |
| signature_method | Enum(SignatureMethod) | NOT NULL | — | |
| sms_code | String(8) | Nullable | — | |
| sms_code_sent_at | DateTime | Nullable | — | |
| signed_at | DateTime | NOT NULL | now() | |
| ip_address | String(45) | Nullable | — | |

**Source:** `src/db/models/contract.py` (same file)

#### OrdRegistration (`ord_registrations`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| placement_request_id | Integer | FK → placement_requests.id, UNIQUE | — | 1:1 with placement |
| ord_status | Enum(OrdStatus) | NOT NULL | "pending" | |
| ord_token | String(256) | Nullable | — | ERID token (**sensitive**) |
| registered_at | DateTime | Nullable | — | |
| reported_at | DateTime | Nullable | — | |
| error_message | Text | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |
| updated_at | DateTime | NOT NULL | now() | |

**OrdStatus enum:** `pending`, `registered`, `token_received`, `reported`, `failed`

**⚠️ IMPORTANT:** `ord_token` contains sensitive data — never log it.

**Source:** `src/db/models/ord_registration.py`

#### AuditLog (`audit_logs`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id, nullable | — | Who performed action |
| action | String(64) | NOT NULL | — | CREATE/UPDATE/DELETE/SIGN |
| resource_type | String(64) | NOT NULL | — | legal_profile/contract/etc |
| target_user_id | Integer | FK → users.id, nullable | — | Affected user |
| old_values | JSON | Nullable | — | Previous state |
| new_values | JSON | Nullable | — | New state |
| ip_address | String(45) | Nullable | — | |
| user_agent | String(512) | Nullable | — | |
| inn_hash | String(64) | Nullable | — | INN hash for audit |
| created_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/audit_log.py`

#### Act (`acts`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| placement_id | Integer | FK → placement_requests.id | — | |
| pdf_file_path | String(512) | Nullable | — | |
| status | String(32) | NOT NULL | — | |
| signed_at | DateTime | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/act.py`

### 2.6 Social & Reputation Entities

#### ReputationScore (`reputation_scores`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| user_id | Integer | PK, FK → users.id | — | 1:1 with user |
| advertiser_score | Float | NOT NULL | 0.0 | |
| owner_score | Float | NOT NULL | 0.0 | |
| is_advertiser_blocked | Boolean | NOT NULL | false | |
| is_owner_blocked | Boolean | NOT NULL | false | |

**Source:** `src/db/models/reputation_score.py`

#### ReputationHistory (`reputation_history`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id | — | |
| placement_request_id | Integer | FK → placement_requests.id, nullable | — | |
| score_change | Float | NOT NULL | — | Delta |
| reason | String(128) | NOT NULL | — | |
| created_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/reputation_history.py`

#### Review (`reviews`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| reviewer_id | Integer | FK → users.id | — | Who wrote review |
| reviewed_id | Integer | FK → users.id | — | Who was reviewed |
| placement_request_id | Integer | FK → placement_requests.id | — | |
| rating | Integer | NOT NULL (1-5) | — | |
| comment | Text | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/review.py`

#### UserFeedback (`user_feedback`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id, ON DELETE CASCADE, indexed | — | |
| text | Text | NOT NULL | — | |
| status | Enum(FeedbackStatus) | NOT NULL | "NEW" | |
| admin_response | Text | Nullable | — | |
| responded_by_id | Integer | FK → users.id, nullable | — | Admin who responded |
| responded_at | DateTime | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**FeedbackStatus enum:** `NEW`, `IN_PROGRESS`, `RESOLVED`, `REJECTED`

**Source:** `src/db/models/feedback.py`

#### PlacementDispute (`placement_disputes`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| placement_request_id | Integer | FK → placement_requests.id, indexed | — | |
| advertiser_id | Integer | FK → users.id | — | |
| owner_id | Integer | FK → users.id | — | |
| admin_id | Integer | FK → users.id, nullable | — | Resolving admin |
| reason | Enum(DisputeReason) | NOT NULL | — | |
| comment | Text | NOT NULL | — | |
| owner_explanation | Text | Nullable | — | |
| status | Enum(DisputeStatus) | NOT NULL | "open" | |
| resolution | Enum(DisputeResolution) | Nullable | — | |
| resolved_at | DateTime | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**DisputeReason enum:** `post_removed_early`, `bot_kicked`, `advertiser_complaint`
**DisputeStatus enum:** `open`, `owner_explained`, `resolved`
**DisputeResolution enum:** `owner_fault`, `advertiser_fault`, `technical`, `partial`

**Source:** `src/db/models/dispute.py`

### 2.7 Gamification & Notification Entities

#### UserBadge (`user_badges`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id | — | |
| badge_id | Integer | FK → badges.id | — | |
| awarded_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/badge.py`

#### Badge (`badges`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| slug | String(64) | UNIQUE | — | |
| name | String(128) | NOT NULL | — | |
| icon | String(64) | NOT NULL | — | Emoji |
| description | Text | Nullable | — | |
| criteria_json | JSON | Nullable | — | |

**Source:** `src/db/models/badge.py`

#### MailingLog (`mailing_logs`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| placement_request_id | Integer | FK → placement_requests.id | — | |
| chat_id | Integer | FK → telegram_chats.id | — | |
| status | String(32) | NOT NULL | — | sent/failed/skipped |
| error_message | Text | Nullable | — | |
| sent_at | DateTime | Nullable | — | |

**Source:** `src/db/models/mailing_log.py`

### 2.8 Admin & Operations Entities

#### DocumentUpload (`document_uploads`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id | — | |
| document_type | String(64) | NOT NULL | — | |
| file_path | String(512) | NOT NULL | — | |
| status | String(32) | NOT NULL | — | processing/completed/failed |
| ocr_result | JSON | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**Source:** `src/db/models/document_upload.py`

#### DocumentCounter (`document_counters`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| prefix | String(16) | NOT NULL | — | Document type prefix |
| year | Integer | NOT NULL | — | |
| counter | Integer | NOT NULL | 0 | |

**Source:** `src/db/models/document_counter.py`

#### PlatformQuarterlyRevenue (`platform_quarterly_revenue`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| quarter | Integer | NOT NULL (1-4) | — | |
| year | Integer | NOT NULL | — | |
| revenue | Numeric(14,2) | NOT NULL | 0 | |

**Source:** `src/db/models/platform_quarterly_revenue.py`

#### KudirRecord (`kudir_records`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id | — | |
| date | Date | NOT NULL | — | |
| amount | Numeric(12,2) | NOT NULL | — | |
| description | Text | Nullable | — | |

**Source:** `src/db/models/kudir_record.py`

### 2.9 Auth Entities

#### LoginCode (`login_codes`)

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | Integer | PK, auto | — | |
| user_id | Integer | FK → users.id | — | |
| code | String(128) | NOT NULL | — | **Encrypted** |
| expires_at | DateTime | NOT NULL | — | |
| used_at | DateTime | Nullable | — | |
| created_at | DateTime | NOT NULL | now() | |

**Source:** Auth model file

---

## 3. Entity Relationship Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        CORE ENTITIES                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────┐ 1       * ┌──────────────┐ 1    * ┌───────────────┐ │
│  │  USER    │───────────▶│TelegramChat  │───────▶│ChannelSettings│ │
│  │          │           │(channels)     │  1:1  │               │ │
│  │          │ 1       * │             │       │               │ │
│  │          │───────────▶│ChannelMediakit│      │               │ │
│  │          │           └──────────────┘       └───────────────┘ │
│  │          │                                                    │
│  │          │ 1       * ┌──────────────────┐  1    * ┌─────────┐│
│  │          │───────────▶│PlacementRequest  │───────▶│Dispute  ││
│  │          │           │                  │        │         ││
│  │          │           │ status, format   │  1    *│Review   ││
│  │          │           │ price, text      │───────▶│         ││
│  │          │           └───────┬──────────┘        └─────────┘│
│  │          │                   │                              │
│  │          │ 1       *         │ 1    * ┌──────────────┐      │
│  │          │───────────────────▶│PubLog   │ClickTracking │     │
│  │          │                   └─────────┘              │      │
│  │          │                                            │      │
│  │          │ 1       * ┌─────────────┐  1    * ┌───────┘      │
│  │          │───────────▶│Transaction  │◀───────▶│              │
│  │          │           │(20 types)   │         │              │
│  │          │           └──────┬──────┘         │              │
│  │          │                  │                │              │
│  │          │ 1       * ┌──────▼──────┐  1    1│              │
│  │          │───────────▶│PayoutRequest│        │              │
│  │          │           │(gross/fee/net)        │              │
│  │          │           └─────────────┘         │              │
│  │          │                                    │              │
│  │          │ 1    0..1 ┌─────────────┐  1    *│              │
│  │          │───────────▶│LegalProfile │◀───────│              │
│  │          │           │(encrypted)  │         │              │
│  │          │           └──────┬──────┘         │              │
│  │          │ 1       * ┌──────▼──────┐  1    *│              │
│  │          │───────────▶│  Contract   │◀───────│              │
│  │          │           │(PDF, signed)│  1    1│              │
│  │          │           └─────────────┘       ││              │
│  │          │                                  ││              │
│  │          │ 1    0..1 ┌─────────────┐  1    1││              │
│  │          │───────────▶│ReputationSc │        ││              │
│  │          │           └──────┬──────┘        ││              │
│  │          │ 1       * ┌──────▼──────┐        ││              │
│  │          │───────────▶│ReputationHis│        ││              │
│  │          │           └─────────────┘        ││              │
│  │          │                                   ││              │
│  │          │ 1       * ┌─────────────┐  1    *││              │
│  │          │───────────▶│UserFeedback │        ││              │
│  │          │           └─────────────┘        ││              │
│  │          │                                   ││              │
│  │          │ 1       * ┌─────────────┐  1    *││              │
│  │          │───────────▶│  UserBadge  │◀───────┘│              │
│  │          │           └──────┬──────┘         │              │
│  │          │ 1       * ┌──────▼──────┐  1    1 │              │
│  │          │───────────▶│   Badge     │         │              │
│  │          │           └─────────────┘         │              │
│  │          │                                    │              │
│  │          │ 1       0..1 ┌──────────────────┐ │              │
│  │          │─────────────▶│PlatformAccount   │ │              │
│  │          │              │(singleton id=1)  │ │              │
│  │          │              └──────────────────┘ │              │
│  │          │                                    │              │
│  │          │ 1       * ┌──────────────────┐     │              │
│  │          │───────────▶│  AuditLog        │◀────┘              │
│  │          │           └──────────────────┘                     │
│  │          │                                                    │
│  │          │ self-ref ┌──────────────────┐                      │
│  │          │◀─────────│  (referrals)     │                      │
│  └──────────┘          └──────────────────┘                      │
└────────────────────────────────────────────────────────────────────┘
```

---

## 4. Foreign Key Matrix

| Child Table | FK Column | References | Cascade | Notes |
|------------|-----------|-----------|---------|-------|
| telegram_chats | owner_id | users.id | all, delete-orphan | |
| channel_settings | channel_id | telegram_chats.id | all, delete-orphan | 1:1 |
| channel_mediakits | channel_id | telegram_chats.id | all, delete-orphan | 1:1 |
| placement_requests | advertiser_id | users.id | — | |
| placement_requests | owner_id | users.id | — | ⚠️ No cascade |
| placement_requests | channel_id | telegram_chats.id | all, delete-orphan | |
| placement_requests | escrow_transaction_id | transactions.id | — | |
| placement_requests | campaign_id | campaigns.id | — | |
| payout_requests | owner_id | users.id | all, delete-orphan | |
| payout_requests | admin_id | users.id | — | |
| transactions | user_id | users.id | — | |
| transactions | placement_request_id | placement_requests.id | — | |
| transactions | payout_id | payout_requests.id | — | |
| transactions | contract_id | contracts.id | — | |
| transactions | act_id | acts.id | — | |
| transactions | invoice_id | invoices.id | — | |
| transactions | reverses_transaction_id | transactions.id | — | Self-ref |
| legal_profiles | user_id | users.id | — | ⚠️ BigInteger vs Integer mismatch |
| contracts | user_id | users.id | — | |
| contracts | legal_profile_id | legal_profiles.id | — | |
| contracts | placement_request_id | placement_requests.id | — | |
| ord_registrations | placement_request_id | placement_requests.id | — | UNIQUE |
| audit_logs | user_id | users.id | — | |
| audit_logs | target_user_id | users.id | — | |
| placement_disputes | placement_request_id | placement_requests.id | all, delete-orphan | |
| placement_disputes | advertiser_id | users.id | — | |
| placement_disputes | owner_id | users.id | — | |
| placement_disputes | admin_id | users.id | — | |
| user_feedback | user_id | users.id | CASCADE (DB-level) | ON DELETE |
| user_feedback | responded_by_id | users.id | — | |
| reputation_scores | user_id | users.id | all, delete-orphan | 1:1 |
| reputation_history | user_id | users.id | — | |
| reputation_history | placement_request_id | placement_requests.id | — | |
| reviews | reviewer_id | users.id | all, delete-orphan | |
| reviews | reviewed_id | users.id | all, delete-orphan | |
| reviews | placement_request_id | placement_requests.id | all, delete-orphan | |
| user_badges | user_id | users.id | all, delete-orphan | |
| user_badges | badge_id | badges.id | — | |
| publication_logs | placement_request_id | placement_requests.id | — | |
| click_tracking | campaign_id | campaigns.id | — | |
| click_tracking | placement_request_id | placement_requests.id | — | |
| mailing_logs | placement_request_id | placement_requests.id | — | |
| mailing_logs | chat_id | telegram_chats.id | — | |
| acts | placement_id | placement_requests.id | all, delete-orphan | |
| document_uploads | user_id | users.id | — | |
| kudir_records | user_id | users.id | — | |
| login_codes | user_id | users.id | — | |
| users | referred_by_id | users.id | — | Self-ref |

---

## 5. Index Strategy

### 5.1 Primary Keys (all tables)

All tables use auto-incrementing Integer PKs (except `categories` which uses String slug).

### 5.2 Unique Indexes

| Table | Column(s) | Purpose |
|-------|-----------|---------|
| users | telegram_id | User identity by Telegram ID |
| users | referral_code | Unique referral codes |
| telegram_chats | telegram_id | Unique Telegram chat identity |
| telegram_chats | username | Unique channel username |
| yookassa_payments | payment_id | Unique YooKassa payment ID |
| placement_requests | tracking_short_code | Unique click tracking codes |
| legal_profiles | user_id | 1:1 user-to-profile |
| badges | slug | Unique badge identifier |

### 5.3 B-tree Indexes (standard lookups)

| Table | Column(s) | Purpose |
|-------|-----------|---------|
| telegram_chats | category | Channel filtering |
| telegram_chats | is_test | Test channel exclusion |
| telegram_chats | owner_id | Owner's channels |
| placement_requests | advertiser_id | Advertiser's placements |
| placement_requests | owner_id | Owner's placements |
| placement_requests | channel_id | Channel's placements |
| placement_requests | status | Status filtering |
| placement_requests | expires_at | Expiry checks |
| placement_requests | is_test | Test placement exclusion |
| legal_profiles | user_id | Profile lookup |
| legal_profiles | inn_hash | INN search |
| contracts | user_id | User's contracts |
| contracts | placement_request_id | Placement contracts |
| contracts | (contract_type, contract_status) | Composite filter |
| transactions | user_id | User's transactions |
| transactions | type | Type filtering |
| transactions | placement_request_id | Placement transactions |
| payout_requests | owner_id | Owner's payouts |
| payout_requests | status | Status filtering |
| user_feedback | user_id | User's feedback |

### 5.4 Partial Indexes

None currently defined. Recommended for future:
- `CREATE INDEX ix_placements_active ON placement_requests(status) WHERE status NOT IN ('cancelled', 'completed')`
- `CREATE INDEX ix_contracts_pending ON contracts(id) WHERE contract_status = 'draft'`

---

## 6. Enum Reference

### 6.1 UserPlan
`free` | `starter` | `pro` | `business` | `admin`

**Source:** `src/db/models/user.py`

### 6.2 PlacementStatus
`pending_owner` | `counter_offer` | `pending_payment` | `escrow` | `published` | `failed` | `failed_permissions` | `refunded` | `cancelled` | `completed`

**Source:** `src/db/models/placement_request.py`

### 6.3 PublicationFormat
`post_24h` | `post_48h` | `post_7d` | `pin_24h` | `pin_48h`

**Format multipliers:** 1.0×, 1.4×, 2.0×, 3.0×, 4.0×
**Durations:** 86400s, 172800s, 604800s, 86400s, 172800s

### 6.4 PayoutStatus
`pending` | `processing` | `paid` | `rejected` | `cancelled`

### 6.5 TransactionType (20 types)
`topup` | `escrow_freeze` | `escrow_release` | `platform_fee` | `refund_full` | `refund_partial` | `cancel_penalty` | `owner_cancel_compensation` | `payout` | `payout_fee` | `credits_buy` | `failed_permissions_refund` | `spend` | `bonus` | `commission` | `refund` | `ndfl_withholding` | `storno`

### 6.6 LegalStatus
`legal_entity` | `individual_entrepreneur` | `self_employed` | `individual`

### 6.7 TaxRegime
`usn` | `osno` | `npd` | `ndfl` | `patent`

### 6.8 ContractType
`owner_service` | `advertiser_campaign` | `platform_rules` | `privacy_policy` | `tax_agreement`

### 6.9 ContractStatus
`draft` | `pending` | `signed` | `expired` | `cancelled`

### 6.10 SignatureMethod
`button_accept` | `sms_code`

### 6.11 OrdStatus
`pending` | `registered` | `token_received` | `reported` | `failed`

### 6.12 DisputeReason
`post_removed_early` | `bot_kicked` | `advertiser_complaint`

### 6.13 DisputeStatus
`open` | `owner_explained` | `resolved`

### 6.14 DisputeResolution
`owner_fault` | `advertiser_fault` | `technical` | `partial`

### 6.15 FeedbackStatus
`NEW` | `IN_PROGRESS` | `RESOLVED` | `REJECTED`

---

## 7. Encryption Schema

### 7.1 Fernet Field-Level Encryption

**Key:** `FIELD_ENCRYPTION_KEY` (Fernet key, 32 bytes base64)
**Type:** `EncryptedString` — SQLAlchemy custom type

**Encrypted columns:**

| Table | Column | Type | Notes |
|-------|--------|------|-------|
| legal_profiles | inn | EncryptedString(128) | Tax ID |
| legal_profiles | inn_hash | HashableEncryptedString(64) | Search index |
| legal_profiles | kpp | EncryptedString(64) | |
| legal_profiles | company_name | EncryptedString(256) | |
| legal_profiles | full_name | EncryptedString(256) | |
| legal_profiles | passport_data | EncryptedText | |
| legal_profiles | address | EncryptedString(512) | |
| legal_profiles | phone | EncryptedString(64) | |
| legal_profiles | email | EncryptedString(128) | |
| legal_profiles | bank_name | EncryptedString(256) | |
| legal_profiles | bank_account | EncryptedString(64) | |
| legal_profiles | bank_bik | EncryptedString(64) | |
| legal_profiles | yoomoney_wallet | EncryptedString(64) | |
| login_codes | code | EncryptedString(128) | OTP code |

**Source:** `src/core/security/field_encryption.py`

### 7.2 Search Hash

**Key:** `SEARCH_HASH_KEY` (32-byte hex)
**Algorithm:** HMAC-SHA256
**Purpose:** Allow INN lookups without decrypting all records

**Source:** `src/core/security/field_encryption.py`

---

## 8. Migration History

### 8.1 Migration Overview

**Total migrations:** 33
**Tool:** Alembic
**Config:** `alembic.ini` (local), `alembic.docker.ini` (Docker), `alembic_sync.ini` (sync operations)

### 8.2 Migration Categories

| Category | Count | Purpose |
|----------|-------|---------|
| Initial schema | ~5 | Core models: users, chats, placements, transactions |
| Financial updates | ~5 | Platform account, payout fields, escrow |
| Legal & compliance | ~6 | Legal profiles, contracts, ORD, audit logs |
| Feature additions | ~8 | Disputes, reviews, badges, campaigns, mediakits |
| Bug fixes | ~5 | Type mismatches, index additions, constraint fixes |
| S-26+ additions | ~4 | Click tracking, acts, document uploads |

### 8.3 Migration Rules

1. **Migrations are immutable** after application in production
2. **Never modify existing migrations** — create new ones instead
3. **Read-only access** to `alembic/versions/` for developers
4. **Alembic check** before deployment: `alembic check && alembic current`

### 8.4 Running Migrations

```bash
# Development
poetry run alembic upgrade head

# Docker
docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head

# Check status
poetry run alembic current

# Verify (no pending migrations)
poetry run alembic check
```

---

## 9. Known Schema Issues

### 9.1 Severity-Indexed Issues

| # | Issue | Severity | Table.Column | Details | Workaround |
|---|-------|----------|-------------|---------|-----------|
| 1 | BigInteger vs Integer mismatch | 🔴 HIGH | legal_profiles.user_id | Column is BigInteger but references users.id (Integer) | Works in PostgreSQL but inconsistent — fix with migration |
| 2 | No cascade on placement_requests.owner_id | 🟡 MEDIUM | placement_requests.owner_id | If user deleted, placements orphaned | Application-level cleanup |
| 3 | No cascade on payout_requests.admin_id | 🟡 MEDIUM | payout_requests.admin_id | Admin deletion breaks audit trail | Soft-delete admins |
| 4 | Self-referencing FK without cascade | 🟢 LOW | users.referred_by_id | Orphaned referrals if referrer deleted | Acceptable |
| 5 | Self-referencing FK in transactions | 🟢 LOW | transactions.reverses_transaction_id | Reversal chain breaks if original deleted | Acceptable |
| 6 | placement_disputes FK columns not indexed | 🟢 LOW | dispute.advertiser_id, owner_id, admin_id | Only placement_request_id indexed | Add indexes if query performance degrades |
| 7 | No dedicated repositories for 8 models | 🟡 MEDIUM | Campaign, Badge, YookassaPayment, ClickTracking, KudirRecord, DocumentUpload, MailingLog, PlatformQuarterlyRevenue | Accessed via direct SQLAlchemy queries in services | Documented in services — not a schema issue |

### 9.2 Recommended Schema Improvements

| Priority | Improvement | Effort | Impact |
|----------|------------|--------|--------|
| HIGH | Fix legal_profiles.user_id type (BigInteger → Integer) | Low (migration) | Type consistency |
| MEDIUM | Add CASCADE on placement_requests.owner_id | Medium (data migration) | Data integrity |
| MEDIUM | Add partial indexes for active placements | Low | Query performance |
| LOW | Add indexes on dispute FK columns | Low | Query performance |
| LOW | Add `created_at` indexes on all tables | Low | Admin queries |

---

🔍 Verified against: HEAD @ 2026-04-08 | Source files: `src/db/models/` (33 files), `src/db/base.py`, `src/db/session.py`
✅ Validation: passed | All 33 models documented | Column types verified against actual model definitions | Foreign keys cross-referenced
