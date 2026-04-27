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

## LSP — Code Navigation

**Claude Code has a native `LSP` tool available in every session** (requires `ENABLE_LSP_TOOL=1`, already set globally).

Active language servers:
- **Python** — `pyright-langserver` via `pyrightconfig.json` at repo root (venv: `.venv` → poetry virtualenv, Python 3.14, 322 deps resolved)
- **TypeScript / TSX** — `typescript-language-server` picks up each `tsconfig.json` in `mini_app/`, `web_portal/`, `landing/` automatically

### Tool operations
`goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`.
Parameters: `operation`, `filePath`, `line` (1-based), `character` (1-based).

### Usage policy

**Use LSP first** for *semantic* questions about a specific symbol:
- "where is `PlacementRequestService` defined?" → `goToDefinition`
- "who calls `freeze_escrow_for_payment`?" → `findReferences` / `incomingCalls`
- "what methods does `ReputationRepo` expose?" → `documentSymbol`
- "find the class whose name contains `Payout`" → `workspaceSymbol`
- type of a variable, signature of a function → `hover`

**Use Grep / Read** (not LSP) for:
- text search in strings, comments, TODO markers, logs
- regex across non-code files (`*.md`, `*.yaml`, `*.sql`, `alembic/versions/*`)
- counting occurrences
- when LSP returns empty (fall back to Grep as a last resort, and say so explicitly)

**Rule of thumb:** "navigating by symbol" = LSP; "searching for text" = Grep. Never silently use Grep for goto-definition when LSP would answer.

### Fallback signals

If `LSP goToDefinition` returns `[]` or errors:
1. Verify the file is under `include` in `pyrightconfig.json` (Python) or covered by a `tsconfig.json` (TS)
2. For Python — check `.venv` symlink still points at a valid poetry venv (`ls -la .venv`)
3. Only then fall back to Grep, and report the LSP failure to the user

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

### Placement state machine (10 statuses, ORM-canonical)

`pending_owner`, `counter_offer`, `pending_payment`, `escrow`, `published`,
`completed`, `failed`, `failed_permissions`, `refunded`, `cancelled`.

Mutations exclusively through `PlacementTransitionService.transition()`
or `transition_admin_override()`. Direct attribute writes blocked by
forbidden-patterns lint (see § 2.B.0 Decision 7).

Source: `IMPLEMENTATION_PLAN_ACTIVE.md` § 2.B.0 Decision 1.

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

### Bot Instance Lifecycle (S-37 + S-48 refinement)

Two valid patterns, deliberately separated:

1. **`get_bot()` — process-level singleton.** Created once per worker process via
   `worker_process_init` hook, closed in `worker_process_shutdown`. Session is
   bound to the creating event loop. **Safe only when the worker runs in a
   persistent loop.** Use in `bot/main.py` polling.

2. **`ephemeral_bot()` — per-task async context manager.** Creates and closes a
   Bot inside the caller's event loop. **Required in any Celery task that
   wraps async work with `asyncio.run(...)`** — each call spins up a new loop,
   and singleton's aiohttp session bound to a prior loop raises
   `RuntimeError('Event loop is closed')` on the next invocation.

```python
from src.tasks._bot_factory import ephemeral_bot

async def _delete_published_post_async(placement_id: int) -> None:
    async with ephemeral_bot() as bot, async_session_factory() as session:
        ...
```

- **Rule: `Bot()` must NEVER be instantiated outside `_bot_factory.py`.**
- `bot.session.close()` must NEVER be called in task code — both factories
  manage their own lifecycle.

### Service Transaction Contract (S-48)

Transaction ownership rests with the **outermost caller** (Celery task or
FastAPI endpoint). Service methods accepting `session: AsyncSession`:

- **MUST NOT** call `async with session.begin()` — it poisons any session
  that already has an active autobegin transaction (first SELECT starts one).
- **MUST NOT** call `await session.commit()` / `await session.rollback()`.
- **MAY** call `await session.flush()` to materialise constraints early.
- **MAY** use `async with session.begin_nested()` (SAVEPOINT) when a specific
  sub-block must roll back independently without aborting the outer
  transaction.

Methods that open their own session (e.g. `async with async_session_factory()
as session, session.begin():`) are fine — they own that transaction
end-to-end.

**Business-level idempotency.** Financial events carry stable keys on
`Transaction.idempotency_key` (UNIQUE index). EXISTS-check early-exit covers
the happy path; `try/except IntegrityError` around `flush()` covers the
race-past-EXISTS case.

Key format (in use today):
- `escrow_freeze:placement={id}`
- `escrow_release:placement={id}:{owner|platform}`
- `refund:placement={id}:scenario={scenario}:{advertiser|owner}`

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

## API Conventions (FIX_PLAN_06 §6.7)

**screen → hook → api-module — единственный путь вызова бэкенда из
`web_portal/src/` и `mini_app/src/`.**

- Экран никогда не импортирует `api` напрямую — только hook.
- Hook инкапсулирует React Query / мутацию и вызывает функцию из
  `web_portal/src/api/<domain>.ts` (или `mini_app/src/lib/`).
- API-модуль — единственное место, где собирается URL и параметры.
- Правило проверяется трёхступенчато:
    1. ESLint `no-restricted-imports` (S-46) — блокирует прямые
       `import { api }` в `screens/**`, `components/**`, `hooks/**`.
    2. `scripts/check_forbidden_patterns.sh` (S-48) — grep-guard на
       7 регрессионных паттернов (import api, legacy-поля,
       phantom-пути).
    3. CI `.github/workflows/contract-check.yml` — прогоняет 1 + 2
       + pytest `tests/unit/test_contract_schemas.py` + pytest
       `tests/unit/api/`.

**Добавление нового endpoint'а:**
1. Pydantic-схема ответа в `src/api/schemas/<domain>.py` (или прямо в
   роутере). Любое изменение formы попадает в
   `tests/unit/test_contract_schemas.py` — после изменения запустить
   `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py`
   и закоммитить обновлённый snapshot в ту же PR.
2. Добавить функцию в `web_portal/src/api/<domain>.ts` — это
   единственное место с fetch/ky.
3. Добавить hook в `web_portal/src/hooks/` (useQuery/useMutation
   поверх api-функции).
4. Подключить hook в экране. Прямой вызов `api.*` в экране — fail
   CI (ESLint + grep-guard).

## Contract drift guard (FIX_PLAN_06 §6.1 Variant B + plan-04)

`tests/unit/test_contract_schemas.py` снимает JSON-schema-снимки
18 моделей и валидирует их против файлов в
`tests/unit/snapshots/*.json`. Любое изменение формы (переименование
/ добавление / удаление поля, смена типа) ломает тест с unified diff
— автор обязан пересгенерировать snapshot и закоммитить рядом со
схемой, что делает drift видимым в ревью.

**Item-схемы (8):** `UserResponse`, `UserAdminResponse`,
`PlacementResponse`, `PayoutResponse`, `ContractResponse`,
`DisputeResponse`, `LegalProfileResponse`, `ChannelResponse`.

**List / pagination wrappers (10, plan-04):**
`AdminPayoutListResponse`, `AdminContractListResponse`,
`UserListAdminResponse`, `DisputeListAdminResponse`,
`FeedbackListAdminResponse`, `DisputeListResponse`,
`FeedbackListResponse`, `ContractListResponse`,
`CampaignListResponse`, `CampaignsListResponse`. Покрывают форму
`{items, total, limit, offset}` (и две легаси-формы в
`campaigns.py`) — переименование `total → count` или
`items → rows` ломает тест.

**Сознательно НЕ покрыто** (item-схема уже фиксирует контракт, либо
ответ собирается inline-dict без Pydantic-обёртки):
`GET /api/payouts/` (`list[PayoutResponse]`),
`GET /api/admin/audit-logs` (inline `dict`).

Регенерация: `UPDATE_SNAPSHOTS=1 poetry run pytest
tests/unit/test_contract_schemas.py`.

Контракт прогоняется в CI — `.github/workflows/contract-check.yml`.

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

## Pre-Launch Blockers

These tasks MUST be completed before deploying with real payments and publications.

### ORD Integration (legal requirement — ФЗ-38)

- `src/core/services/stub_ord_provider.py` issues synthetic ERID
- `ORD_BLOCK_WITHOUT_ERID=false` in current `.env` — publications pass with stub ERID
- Legal exposure: under ФЗ-38 every ad must have a real ERID from an official ОРД operator

**Required before launch:**
1. Contract with one of the ОРД providers (Яндекс ОРД API v7, VK Реклама, Ozon)
2. Obtain API credentials, add to `.env`:
   - `ORD_PROVIDER=yandex`
   - `ORD_API_KEY=...`
   - `ORD_API_URL=...`
3. Set `ORD_BLOCK_WITHOUT_ERID=true` in production `.env`
4. Real provider is auto-selected by `ORD_PROVIDER` in settings (no code change needed)
5. E2E test: placement with real ERID passes, without it — blocked

### FNS Validation (optional hardening, not a legal blocker)

- `src/core/services/fns_validation_service.py` validates checksum only
- For post-launch adversarial protection — integrate `npchk.nalog.ru`
- Does not block launch (checksum is sufficient against typos)

## Deferred E2E items (plan-08)

Three flows in `web_portal/tests/specs/deep-flows.spec.ts` are
permanently `test.fixme`'d. Each has explicit re-activation criteria
in `reports/docs-architect/BACKLOG.md` — re-activate by satisfying
the criterion, then turn the `test.fixme` into a real `test`.

| ID | Flow | Blocked by |
|---|---|---|
| BL-001 | Dispute round-trip | seed-fixture: escrow placement + open disputable window |
| BL-002 | Channel add via bot verification | Telegram Bot API mock in docker-compose.test.yml |
| BL-003 | KEP signature on framework contract | КриптоПро stub or `signature_method=sms_code` fallback |

Do **not** add new `test.fixme(true, ...)` blocks without recording a
matching BL entry — silent skips defeat the point of the suite.

## Known Issues (2026-03-22)

- **mypy**: 529 errors in 41 files — long-standing, pre-existing, not blocking deployment. Key example: `placements.py:534` returns `PlacementRequest` where `PlacementResponse` expected.
- **ruff**: 0 errors (clean).
- **Menu Button**: ✅ Implemented in src/bot/main.py — MenuButtonWebApp pointing to https://app.rekharbor.ru/
- **Admin Panel**: Deferred to next sprint.

### Resolved

- **ESCROW-002 (2026-04-21)** — auto-deletion of expired placements and
  release of escrow. Fixed by Track A: caller-controlled transaction contract
  for BillingService; `Transaction.idempotency_key` + UNIQUE as the single
  source of idempotency truth; per-task `ephemeral_bot()` lifecycle;
  `check_escrow_stuck` group C for recovery. See
  `CHANGES_2026-04-21_fix-escrow-auto-release.md` and
  `/root/.claude/plans/lexical-swinging-pony.md` Track B for architectural
  follow-up.

---

## Research reports — Objections section (MANDATORY)

When producing a research / consolidation report before any implementation
(deep-dive Explore agents, architecture audits, plan reviews):

If you spot any of the following in the original plan or in the findings,
raise them **explicitly in a separate section "Возражения и риски"
("Objections and risks"), placed BEFORE the "Вопросы для подтверждения"
("Questions for confirmation") section:**

- Security holes (auth bypass, missing rate-limit, replay, weak validation)
- Internal contradictions (plan says X but the codebase pattern is Y)
- Missed edge cases (race conditions, concurrent writes, Redis flush, partial failure)
- Bad naming (semantic mismatch between term and what it actually denotes)
- API ergonomics traps (default values that silently disable safety, optional
  params that should be required, footguns for future contributors)

Do **NOT** disguise objections as clarifying questions. A question like
"подтверждаем X, как сказано в плане?" is rubber-stamping when you
actually disagree — instead write "план требует X, я считаю Y потому что
Z, какой выбираем?".

It is far better to surface five uncomfortable observations than to skip
one security hole. The user expects you to push back on the plan when you
have grounds — that is the value of having you review it, not just execute
it.

### Phase mode discipline

You operate in one of two modes. Be explicit about which one you're in.

**Research / planning mode** (deep-dive Explore, audits, plan reviews,
consolidation reports BEFORE any code is written):
> "Be critical. Look for problems. Dispute decisions with reasoning."

In this mode, raise concerns aggressively. Argue with the plan when you
have grounds. The expected output is a sharper plan, not agreement.

**Implementation mode** (writing/editing code per an already-agreed plan):
> "Implement the plan as written. If a blocking problem surfaces — stop
> and report. Do NOT introduce improvements that are not in the plan."

In this mode, scope discipline matters. The user has decided what they
want; your job is to land it precisely. Cosmetic refactors, "while-I'm-here"
cleanups, extra abstraction layers — out of scope unless the plan asks
for them.

### What counts as "raise explicitly" vs "defer"

**Raise explicitly (block / interrupt the work):**
- (a) Security problem (auth bypass, missing validation, secret exposure,
  rate-limit gap, replay risk, signature trust assumption)
- (b) Bug or likely bug (race condition, off-by-one, wrong type, missing
  error path that will fire under realistic load)
- (c) Plain contradiction in the plan or requirements (the plan says X but
  the codebase already does Y; two parts of the plan conflict)
- (d) Decision that will materially complicate future maintenance (heavy
  coupling, premature abstraction, hidden invariant nobody will remember,
  deletion of a load-bearing affordance)

**Defer to a one-line footnote at the end of the report**
(category: "возможные дальнейшие улучшения, не требуют действий сейчас"):
- Cosmetic refactors ("could rename X for clarity")
- Style/consistency nits not breaking anything
- Test coverage gaps in untouched code
- Performance optimisations without measured impact
- Naming preferences without semantic mismatch

The split rule: if a future maintainer would shrug at the issue, defer it.
If a future maintainer would have to redo significant work or hit a real
incident, raise it.

### Plan validation gate (MANDATORY before approving any Phase N plan)

Before a phase's plan is approved for implementation — i.e. before the
"research → STOP → implementation" handoff — run the following three
checks. Any failure means the plan is reworked, not patched during
implementation.

- **(a) `tsc --noEmit` dry-run with the plan's strip-list applied to
  `mini_app/` and `web_portal/`.** If the plan removes files / hooks /
  api modules, simulate the deletion locally (or branch) and confirm
  both frontends still build. A plan that ships a broken TS graph is
  not a plan, it's a regression. (Origin: Phase 1 O.1 — plan said
  "delete contracts.ts" but 6 portal screens still imported it.)
- **(b) Per-endpoint PII classification for every endpoint the plan
  switches to web_portal-only auth.** Read request schema + response
  schema + service-side DB writes. An endpoint with no PII fields
  requires explicit justification for web_portal-only (UX cost, not
  legal cost) or a carve-out (e.g. `legal_acceptance.py`). File-name
  heuristics are not a substitute. (Origin: Phase 1 A.2 — `accept-rules`
  lived in `contracts.py` but is non-PII boolean ack.)
- **(c) Audit of merged decisions from previous phases.** Diff the
  current plan text against the codebase reality on `develop`.
  Anything the plan says is already-true must actually be already-true,
  or the plan needs an explicit "drift fix" commit as its first step.
  (Origin: Phase 0 PF.2 — Phase 1 plan still said "401 for aud-less"
  and "don't touch audit_middleware.py" after Phase 0 follow-up
  reversed both.)

The output of this gate is a short alignment commit (`docs(phase-N):
align plan with PF.X / O.Y decisions`) on the feature branch *before*
any implementation commit. Skipping the gate or rolling its findings
into the first implementation commit defeats the purpose — drift stays
invisible.

---

## Process discipline (added from Phase 2 lessons)

These rules were extracted from BACKLOG entries BL-006, BL-007, BL-013,
BL-015, BL-016, BL-018, BL-024, BL-026, BL-028 (Phase 2 closure,
2026-04-27). They extend — not replace — the "Phase mode discipline"
section above.

### Plan validation gate — extended (BL-015, BL-024, BL-026, BL-018)

The original three checks (a/b/c) above are necessary but not
sufficient. Before approving any phase plan, also run:

- **(d) Ruff baseline diff.** Capture `make lint` output before any
  edit and compare it after the alignment commit. Plans must not
  regress the ruff baseline; if a phase plan adds new files or moves
  code, baseline must hold within the documented tolerance.
- **(e) Cross-artifact reference check (BL-015).** Every backlog
  reference, ticket ID, file path, line number, and commit SHA in the
  phase plan must resolve to an existing entity. Run
  `grep -E '\b(BL-[0-9]+|plan-[0-9]+|FIXME|TODO\([^)]+\))\b' <plan>.md`
  and verify each match exists in BACKLOG.md / repo / git log. Plan
  authors hallucinate IDs (origin: `plan-08` propagated through three
  artifacts before being caught).
- **(f) Test infrastructure surface (BL-024).** Before any plan
  touching test files is approved, run `grep -rn 'autouse=True' tests/`
  and review the conftest.py hierarchy depth + override patterns.
  Document all autouse fixtures and shadowing in the plan. Treat
  `tests/integration/conftest.py` as load-bearing infra: its
  NullPool + connection-rollback override is intentional, not a target
  for "cleanup".
- **(g) Mutation-audit completeness (BL-026).** When auditing field
  writes, enumerate (1) calls to helpers whose name matches
  `update_<field>|set_<field>|change_<field>` and (2) bulk SQLAlchemy
  `.values(<field>=...)` writes — both accept a runtime value and
  bypass static literal scans. Generic mutation helpers with a
  parameter-driven RHS are blind spots in regex/AST literal scans.
  Where possible, **delete** parameter-driven helpers rather than
  lint-allowing them; the lint cannot reason about runtime parameters.

Research-agent enumerations (Agent A/B/C output, deep-dive Explore
catalogs) must be treated as **incomplete-by-default**. § B.1 of any
phase plan begins with a "final mutation audit" step that re-greps the
codebase for the relevant pattern; do not trust the research catalog
alone. (Origin: Phase 2 § 2.B.2a found 6 callers of
`PlacementRequestRepository.update_status` that the initial enumeration
missed.)

### Stop-hook relay protocol (BL-006, BL-013, BL-016)

Stop-hook output is **informational** — its purpose is to surface
documentation gaps to the user, not to authorise the agent to close
them. The agent's correct response to a hook warning is:

1. Relay the warning to the user, with the user's three-way choice:
   - **(a) immediate fix-commit** (warning is load-bearing — public
     contract changed and CHANGES is genuinely missing);
   - **(b) bundle into next natural commit** (default — warning will
     be addressed at the next commit boundary anyway);
   - **(c) defer to phase closure** (only if no risk of CHANGES
     becoming stale relative to documented commits — i.e. the work in
     progress is itself the phase closure work).

Loop-firing tolerance: if the **same** hook warning fires more than
twice in succession on identical HEAD/transcript state, ack it twice
non-trivially, then silent-ignore subsequent identical fires. Identical
fires within a single decision point count as one ack, not multiple.
This avoids the BL-016 anti-pattern where each agent turn after a
commit re-issues the same warning, burning context and pressuring the
agent into autonomous fix to "stop the alarm".

The STOP gate (research → STOP → user "давай" → implementation)
applies to **every commit**, including `docs(...)` /  `chore(...)` /
process-rule commits, not only `feat(...)` / `fix(...)`. Auto-mode on
docs today is auto-mode on code tomorrow — same anti-pattern.

### Cross-artifact reference fabrication (BL-015)

Before committing any plan / CHANGES / BACKLOG entry that cross-refs
another doc by name, ID, or section: `grep` for the target and confirm
it exists. Once a fabricated reference enters one artifact, copy-paste
through prompt templates multiplies it. Same rule applies during
research-artifact consolidation (Agent C-style review).

### Stale plan vs reality (BL-007, BL-018)

The implementation plan is allowed to drift from the codebase between
sessions. Line numbers in the plan are HINTS, not absolutes. Sub-agent
searches must work by signature/content, not by `L<N>`. If the plan
describes a file/function/line that no longer matches reality, surface
this explicitly in the report — do not silently adapt.

The Phase 0 closure note "2 ruff warnings in
`document_validation.py`" turning into "0 warnings on develop" by
Phase 2 start is the canonical example: baseline drifts during
unrelated work, not because anyone fixed it deliberately.

### Verification gate language (BL-018, BL-028)

GitHub Actions are permanently inert for this repository (BL-017
ACCEPTED). The actual verification gate is `make ci-local`. All
future phase plans must phrase verification gates as:

> "Local `make ci-local` passes against baseline X (failed=N1,
>  errored=N2, collection=N3, mypy=N4, ruff=N5)."

— not "CI green" and not bare numbers like "76 failed". Baseline
numbers must always be quoted with the **exact invocation** that
produced them. `pytest --continue-on-collection-errors tests/` and
`make ci-local` produce different counts on the same source tree
(BL-028: 96+132 vs 76+17 on the same HEAD); without the invocation,
the baseline is ambiguous and silent regressions slip past the gate.

Baseline updates land per-phase as part of `CHANGES_*.md` rather than
as standalone documents.

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
src/api/middleware/log_sanitizer.py
src/db/models/audit_log.py
src/db/models/legal_profile.py
src/db/models/contract.py
src/db/models/ord_registration.py
src/db/migrations/versions/          ← read-only, never edit after production apply

# Notes:
# - src/api/middleware/audit_middleware.py was previously listed here but
#   removed for Phase 1 §1.B.0b refactor (PF.4 decision: replace unsafe JWT
#   re-decode with request.state.user_id read; ~21 LOC, 2 files). After Phase 1
#   merge, the file is owned by Phase 1; do not re-add to NEVER TOUCH unless
#   the security model around audit logging changes again.

### Landing-specific rules
- Landing lives in: /opt/market-telegram-bot/landing/
- It is FULLY STATIC — never add runtime FastAPI calls
- Tailwind @theme tokens come from DESIGN.md only
- TS version: 6.0.2 (align with mini_app and web_portal)
- Motion imports: `import { ... } from 'motion/react'` (package name: `motion`)
- CSP: no unsafe-inline, no unsafe-eval
- Fonts: DM Sans, Outfit, Poppins, Roboto — all via Google Fonts
