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

### Celery Infrastructure Map (S-36)

| Worker | Listens to queues | Concurrency |
|--------|-------------------|-------------|
| `worker_critical` | `worker_critical`, `mailing`, `notifications`, `billing`, `placement` | 2 |
| `worker_background` | `parser`, `cleanup`, `background`, `rating` (dead — historical) | 4 |
| `worker_game` | `gamification`, `badges` | 2 |

### Task Prefix → Queue Convention

| Task prefix | Queue | Worker |
|-------------|-------|--------|
| `mailing:*` | `mailing` | worker_critical |
| `parser:*` | `parser` | worker_background |
| `cleanup:*` | `cleanup` | worker_background |
| `notifications:*` | `notifications` | worker_critical |
| `placement:*` | `worker_critical` | worker_critical |
| `billing:*` | `billing` | worker_critical |
| `ord:*` | `background` | worker_background |
| `badges:*` | `badges` | worker_game |
| `gamification:*` | `gamification` | worker_game |
| `integrity:*` | `cleanup` | worker_background |
| `dispute:*` | `worker_critical` | worker_critical |
| `document_ocr:*` | `worker_critical` | worker_critical |
| `payouts:*` | `background` | worker_background |

**Rules for new tasks:**
- Every new Celery task MUST have explicit `queue=` in its `@celery_app.task(...)` decorator AND a matching pattern in `task_routes` in `celery_app.py`.
- Queue constants live in `src/tasks/celery_app.py` (e.g. `QUEUE_WORKER_CRITICAL`). `celery_config.py` was deleted in S-36.

**Notes:**
- Dead queue `rating` in `worker_background` — historical artifact (`rating_tasks.py` deleted in v4.3). Listener kept for in-flight safety; remove at next docker-compose cleanup.
- 4 periodic notification tasks (`auto_approve_placements`, `notify_pending_placement_reminders`, `notify_expiring_plans`, `notify_expired_plans`) intentionally use `queue=mailing` in their decorator despite the `notifications:*` prefix. Decorator overrides `task_routes`. This is correct: `mailing` is for scheduled batch sends, `notifications` is for event-driven.
- **task_routes uses colon-patterns** (`mailing:*`, `parser:*`, etc.) — Celery does fnmatch against task names. Dot-patterns (`mailing.*`) do NOT match colon-prefixed names. Never revert to dot-patterns.

### Bot Instance Lifecycle (S-37)

- `Bot()` is created **once per worker process** via `worker_process_init` hook in `celery_app.py`.
- All tasks obtain the instance via `get_bot()` from `src/tasks/_bot_factory.py`.
- Session stays alive for the worker's lifetime; closed only in `worker_process_shutdown`.
- **Rule: `Bot()` must NEVER be instantiated outside `_bot_factory.py`.**
- `bot.session.close()` must NEVER be called in task code — session lifecycle is managed by factory.

### Notification Helpers (S-37)

- `_notify_user_async(telegram_id, message, parse_mode, reply_markup)` — low-level send, no `notifications_enabled` check. Use for admin alerts and system messages.
- `_notify_user_checked(user_id, message, ...) -> bool` — checks `user.notifications_enabled` via DB lookup (by internal user.id). Returns `False` if skipped, not found, or blocked. **All new user-facing notification tasks must use this helper.**
- `mailing:notify_user(telegram_id, ...)` — public entry point; checks `notifications_enabled` via `get_by_telegram_id`. If user not found, sends anyway (system/auth flows).
- **Architectural rule**: `Bot()` is never created in `core/services/`. If a service needs to send a message, dispatch a Celery task (e.g., `notify_payment_success.delay(...)`).

### Celery Queue Assignment (legacy summary)

- **critical**: billing, notifications, mailing (concurrency 2)
- **background**: parser, cleanup, rating (concurrency 4)
- **game**: badges, XP (concurrency 2)

## Migration Strategy (Pre-Production)

**CURRENT RULE (until first production user):**
- Do NOT create incremental Alembic migrations for model changes
- Instead: edit `src/db/migrations/versions/0001_initial_schema.py` directly
- After editing: drop and recreate the DB, then `alembic upgrade head`

**Reset command:**
```bash
docker compose exec db psql -U postgres \
  -c "DROP DATABASE market_bot_db; CREATE DATABASE market_bot_db;" \
  && docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head
```

**Verify sync after every model change:**
```bash
docker compose exec api poetry run alembic -c alembic.docker.ini check
# Must output: "No new upgrade operations detected."
```

**Switch to incremental migrations ONLY when:** first real user appears in production.
At that point — `0001_initial_schema.py` becomes immutable (standard Alembic rules apply).

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

---

## Git Flow (MANDATORY)

This section is enforced by hooks. Every sprint is INCOMPLETE without these steps.
**Branches**: `feature/*` → `develop` → `main`

### After EVERY batch of code changes (within a feature branch)

Split staged files into **semantic groups** and commit each group separately:

| Type | Scope examples | When to use |
|------|---------------|-------------|
| `feat` | `(backend)`, `(mini-app)`, `(landing)` | New functionality |
| `fix` | `(tasks)`, `(billing)` | Bug fix |
| `chore` | `(migrations)`, `(config)` | Infrastructure, no logic change |
| `refactor` | `(services)` | Refactoring without behaviour change |
| `test` | — | Test files only |
| `docs` | — | CHANGELOG, discovery reports |

**Rules:**
- NEVER `git add .` in a single commit — always add files by group
- Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`
- `git commit -m "feat(backend): ..."` — English, imperative, under 72 chars

### After EVERY sprint / feature completion

Execute **in this exact order**, stopping immediately on any conflict:

```bash
# 1. Verify clean state
git status   # must be "nothing to commit, working tree clean"

# 2. Push feature branch
git push origin $CURRENT_BRANCH

# 3. Merge into develop
git checkout develop && git pull origin develop
git merge $CURRENT_BRANCH --no-ff -m "chore(develop): merge $CURRENT_BRANCH — <sprint summary>"
git push origin develop

# 4. Merge develop into main
git checkout main && git pull origin main
git merge develop --no-ff -m "chore(main): merge develop — <sprint summary>"
git push origin main

# 5. Return to feature branch
git checkout $CURRENT_BRANCH
```

**Hard limits:**
- `--no-ff` is REQUIRED on every merge — never fast-forward
- On ANY merge conflict: **STOP and report** — never auto-resolve
- Never force-push `develop` or `main`
- Never skip `git pull` before merging

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
