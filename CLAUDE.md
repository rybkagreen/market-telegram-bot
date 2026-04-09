# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RekHarborBot** — a Telegram advertising exchange platform where advertisers buy placements in Telegram channels. Key flows: placement request → owner approval → escrow payment → publication → completion.

## Commands

```bash
# Development
make install          # Install Poetry dependencies
make run              # Run bot in polling mode

# Linting & Type Checking
make lint             # Ruff check
make lint-fix         # Ruff auto-fix (also: poetry run ruff check src/ --fix)
make format           # Ruff format
make typecheck        # MyPy strict check
make ci               # lint + format + typecheck (no tests)

# Tests
make test             # Unit tests
make test-cov         # With coverage report
poetry run pytest tests/unit/test_billing.py -v  # Single test file

# Database Migrations
make migrate          # Apply migrations
make migrate-revision  # Create new migration (set MIGRATION_MESSAGE env var)
make migrate-downgrade # Rollback one step

# Docker
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-logs      # Follow logs
docker compose restart api   # Restart specific service
docker compose logs api --tail=20
```

## Architecture

```
Telegram User
    │
    ▼
Aiogram Bot (polling)     FastAPI (port 8001)
    │                           │
    ├── Middlewares              └── JWT Auth → Routers
    │   ├── DBSessionMiddleware
    │   ├── ThrottlingMiddleware
    │   ├── RoleCheckMiddleware
    │   └── FSMTimeoutMiddleware
    │
    ├── Handlers (FSM-based flows)
    │
    └── Core Services
            │
            ├── PostgreSQL (asyncpg + SQLAlchemy 2 async)
            ├── Redis (FSM storage + Celery broker)
            └── Celery Workers (3 queues: critical, background, game)
```

### Layer Responsibilities

- **`src/bot/`** — Aiogram handlers, keyboards, FSM states, middlewares
- **`src/api/`** — FastAPI routers for Mini App (JWT-authenticated)
- **`src/core/services/`** — All business logic; handlers/routers call services, never touch DB directly
- **`src/db/models/`** — SQLAlchemy ORM models
- **`src/db/repositories/`** — Data access layer (all DB queries go here)
- **`src/tasks/`** — Celery async tasks (3 queues: critical, background, game)
- **`src/config/settings.py`** — Single Pydantic Settings instance (`from src.config.settings import settings`)

### Key Models & Aliases

- **`PlacementRequest`** is the central entity (ad placement). In analytics/cleanup code it's aliased as `Campaign = PlacementRequest`.
- **`PlacementStatus`** is aliased as `CampaignStatus` in `campaigns.py` router.
- **`ReputationRepo`** is exported as `ReputationRepository` at the end of `reputation_repo.py`.

### PlacementStatus State Machine

`pending_owner` → `counter_offer` ↔ `pending_payment` → `escrow` → `published` → (done)
Any state → `cancelled` / `refunded` / `failed` / `failed_permissions`

### Celery Queue Assignment

- **critical**: billing, notifications, mailing (concurrency 2)
- **background**: parser, cleanup, rating (concurrency 4)
- **game**: badges, XP (concurrency 2)

## Deleted in v4.3 Rebuild

Do **not** import these — they no longer exist:
- `src.db.models.crypto_payment` (CryptoPayment, PaymentMethod, PaymentStatus)
- `src.tasks.mailing_tasks` (send_placement_request, publish_single_placement)

Still present (corrected — NOT deleted):
- `MailingLog`, `MailingStatus` — exist in `src/db/models/mailing_log.py`
- `Campaign`, `CampaignStatus` — exist in `src/db/models/campaign.py` as aliases for `PlacementRequest` / `PlacementStatus`

MailingService (no `mailing_service.py`): publishing logic lives in `PublicationService` (`publication_service.py`) and Celery tasks (`publication_tasks.py`, `placement_tasks.py`).

## Ruff Configuration

Target: Python 3.13, line length 100. Rules: E, F, I, N, W, UP, B, C4, SIM.
Current state: 0 errors. Always run `make lint` before committing.

## Payments

Active payment provider: **YooKassa** (cards, SBP, YooMoney). Commission model: 15% platform fee, 85% to channel owner. Credits system: `credits_per_rub_for_plan = 1.0`.

## AI Integration

Mistral AI (`mistralai` SDK) used for:
1. Ad text generation (`src/core/services/mistral_ai_service.py`)
2. Content moderation L3 check (`src/utils/content_filter/`)
3. Channel topic classification (`src/utils/telegram/llm_classifier.py`)

## Content Filter

3-level pipeline: **L1** regex → **L2** pymorphy3 morphology → **L3** Mistral LLM (only if L3 enabled and L1/L2 pass).

## Tests

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`. Integration tests use `testcontainers` for real PostgreSQL — do not mock the DB.

## Component Inventory (Verified 2026-03-22)

| Component | Count | Location |
|-----------|-------|----------|
| API Routers | 15 | `src/api/routers/` |
| Core Services | 15 | `src/core/services/` |
| DB Models | 19 | `src/db/models/` |
| FSM State groups | 9 | `src/bot/states/` |
| Bot Handlers | 18 | `src/bot/handlers/` |
| Alembic Migrations | 7 | `src/db/migrations/versions/` |
| Mini App Screens | 39 | `mini_app/src/screens/` |

Mini App breakdown: common (9), advertiser (13), owner (11), admin (6).

## ORD Integration

- **OrdProvider protocol**: `src/core/services/ord_provider.py` — abstract interface, `OrdRegistrationResult` dataclass
- **StubOrdProvider**: `src/core/services/stub_ord_provider.py` — synthetic erid, logs warnings
- **OrdService**: delegates to `_provider` (default: StubOrdProvider); call `set_provider()` to inject a real implementation
- **Real provider**: set `ORD_PROVIDER=yandex|vk|ozon`, `ORD_API_KEY`, `ORD_API_URL` in `.env`
- **Block without erid**: `ORD_BLOCK_WITHOUT_ERID=true` (default `false` — safe until provider configured)
- **Tracking link**: appended to post text if `placement.tracking_short_code` is set
- **tracking_short_code** generated automatically at escrow transition (`_freeze_escrow_for_payment`)
- **Celery tasks**: `ord:register_creative`, `ord:report_publication` (queue=background)

## Known Issues (2026-03-22)

- **mypy**: 529 errors in 41 files — long-standing, pre-existing, not blocking deployment. Key example: `placements.py:534` returns `PlacementRequest` where `PlacementResponse` expected.
- **ruff**: 0 errors (clean).
- **Menu Button**: ✅ Implemented in src/bot/main.py — MenuButtonWebApp pointing to https://app.rekharbor.ru/
- **Admin Panel**: Deferred to next sprint.

---

## Documentation & Changelog Sync (MANDATORY)

This section mirrors INSTRUCTIONS.md and is enforced by hooks. Every task is INCOMPLETE
without these steps.

### After EVERY code change
1. Create `reports/docs-architect/discovery/CHANGES_<YYYY-MM-DD>_<short-desc>.md`
   - List: affected files, business logic impact, new/changed API/FSM/DB contracts
   - Footer: `🔍 Verified against: <commit_hash> | 📅 Updated: <ISO8601>`
2. Append-only: never rewrite existing CHANGES_*.md files.

### After EVERY sprint / milestone
1. Update `CHANGELOG.md` → move `[Unreleased]` to `[vX.Y.Z] - <YYYY-MM-DD>`
   Sections: Added | Changed | Fixed | Removed | Breaking | Migration Notes

### NEVER TOUCH (extended list for Claude Code)
# Original list from CLAUDE.md applies PLUS:
src/core/security/field_encryption.py
src/api/middleware/audit_middleware.py
src/api/middleware/log_sanitizer.py
src/db/models/audit_log.py
src/db/models/legal_profile.py
src/db/models/contract.py
src/db/models/ord_registration.py
src/db/migrations/versions/          ← read-only, never edit after production apply

### Landing-specific rules
- Landing lives in: /opt/market-telegram-bot/landing/
- It is FULLY STATIC — never add runtime FastAPI calls
- Tailwind @theme tokens come from DESIGN.md only
- TS version: 6.0.2 (align with mini_app and web_portal)
- Motion imports: `import { ... } from 'motion/react'` (package name: `motion`)
- CSP: no unsafe-inline, no unsafe-eval
- Fonts: DM Sans, Outfit, Poppins, Roboto — all via Google Fonts
