# RekHarborBot Architecture

## Overview

RekHarborBot is a Telegram advertising marketplace bot connecting advertisers with channel owners (1K-50K subscribers).

## Tech Stack

| Component | Technology |
|-----------|------------|
| Python | 3.13 |
| Framework | aiogram 3.x |
| Database | PostgreSQL + SQLAlchemy 2.0 async |
| Queue | Celery + Redis |
| API | FastAPI |
| Migrations | Alembic |
| AI | Mistral AI (official SDK) |
| Payments | YooKassa only |
| Tax Model | ИП УСН 6% |

## Financial Model v4.2

```
Topup: gross = desired + (desired × 0.035)
Placement: owner gets 85%, platform keeps 15%
Payout: net = gross - (gross × 0.015)
```

### Key Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PLATFORM_COMMISSION` | 0.15 | Platform fee from placements |
| `OWNER_SHARE` | 0.85 | Owner's share (85%) |
| `YOOKASSA_FEE_RATE` | 0.035 | Payment processor fee |
| `PAYOUT_FEE_RATE` | 0.015 | Payout processing fee |
| `PLATFORM_TAX_RATE` | 0.06 | USN tax rate |
| `MIN_TOPUP` | 500 | Minimum top-up amount |
| `MIN_PAYOUT` | 1000 | Minimum payout amount |
| `MIN_CAMPAIGN_BUDGET` | 2000 | Minimum campaign budget |

## Core Services

### BillingService
- `calculate_topup_payment(desired)` → {desired_balance, fee_amount, gross_amount}
- `freeze_escrow(session, user_id, placement_id, amount)` - Lock funds for placement
- `release_escrow(session, placement_id)` - **ONLY called from `delete_published_post`** (ESCROW-001)
- `refund_escrow_full/partial` - Cancellation refunds

### PayoutService
- `create_payout_request(session, owner_id, gross_amount, requisites)`
- `complete_payout(session, payout_id, admin_id)`
- `check_velocity(session, user_id, requested_amount)` - Anti-fraud (max 80% ratio)

### PlacementRequestService
- `create_request(...)` - Create placement request with self-dealing check
- `owner_accept/reject/counter(...)` - Owner arbitration flow
- `cancel(...)` - Cancellation with stage-based refunds

### PublicationService
- `publish_placement(session, bot, placement_id)` - Send message, optional pin
- `delete_published_post(bot, session, placement_id)` - Delete + **release_escrow** (ESCROW-001)

## Database Models

### Key Models

- **User**: `balance_rub` (for placements), `earned_rub` (owner earnings), `credits` (subscriptions)
- **PlatformAccount** (singleton id=1): `escrow_reserved`, `payout_reserved`, `profit_accumulated`
- **PlacementRequest**: `final_price`, `publication_format`, `status`, `message_id`, `scheduled_delete_at`
- **PayoutRequest**: `gross_amount`, `fee_amount`, `net_amount`
- **ChannelSettings**: Format toggles (`allow_format_post_24h`, etc.)

## Escrow Flow (ESCROW-001)

```
1. advertiser pays → freeze_escrow() → platform.escrow_reserved += amount
2. bot publishes post → status = PUBLISHED (NO release yet!)
3. bot deletes post (ETA) → delete_published_post() → release_escrow()
   - owner.earned_rub += final_price × 0.85
   - platform.profit_accumulated += final_price × 0.15
   - platform.escrow_reserved -= final_price
```

**Critical**: `release_escrow()` MUST ONLY be called after successful post deletion.

## Callback Registry

| Callback | Handler | Role |
|----------|---------|------|
| `main:analytics` | `show_advertiser_analytics` | Advertiser |
| `main:owner_analytics` | `show_owner_analytics` | Owner |
| `main:cabinet` | `show_cabinet` | Both |
| `billing:topup_*` | Billing handlers | Advertiser |
| `payout:*` | Payout handlers | Owner |
| `camp:*` | Campaign handlers | Advertiser |
| `own:*` | Owner channel handlers | Owner |

## Plan Limits (PLAN_LIMITS)

| Plan | Price | Active Campaigns | AI/Month | Formats |
|------|-------|------------------|----------|---------|
| free | 0 ₽ | 1 | 0 | post_24h |
| starter | 490 ₽ | 5 | 3 | post_24h, post_48h |
| pro | 1490 ₽ | 20 | 20 | post_24h, post_48h, post_7d |
| business | 4990 ₽ | -1 (unlimited) | -1 | All 5 formats |

**Note**: `PLAN_LIMITS` key is `'business'` (NOT `'agency'`) - PLAN-001 fix.

## Format Multipliers

| Format | Multiplier | Duration |
|--------|------------|----------|
| post_24h | 1.0× | 24 hours |
| post_48h | 1.4× | 48 hours |
| post_7d | 2.0× | 7 days |
| pin_24h | 3.0× | 24 hours + pin |
| pin_48h | 4.0× | 48 hours + pin |

## Velocity Check (Anti-Fraud)

```python
ratio = (payouts_30d + requested) / topups_30d
if ratio > 0.80: raise VelocityCheckError
```

## Self-Dealing Prevention

```python
if channel.owner_id == advertiser_id:
    raise SelfDealingError("Cannot place ads on own channel")
```
