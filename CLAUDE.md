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
make ci-local         # Real verification gate (BL-017 — GHA inactive)

# Tests
make test             # Unit tests
make test-cov         # With coverage report
poetry run pytest tests/unit/test_billing.py -v  # Single test file

# Database Migrations
make migrate          # Apply migrations
make migrate-revision # Create new migration (set MIGRATION_MESSAGE env var)
make migrate-downgrade # Rollback one step

# Docker
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-logs      # Follow logs
docker compose up -d api     # Recreate (NOT 'restart' — restart keeps stale env_file)
docker compose logs api --tail=20
```

## LSP — Code Navigation

**Claude Code has a native `LSP` tool available in every session** (requires `ENABLE_LSP_TOOL=1`, already set globally).

Active language servers:
- **Python** — `pyright-langserver` via `pyrightconfig.json` at repo root (venv: `.venv` → poetry virtualenv, Python 3.14)
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
- type of variable, function signature → `hover`

**Use Grep / Read** (not LSP) for: text in strings/comments/TODOs/logs, regex across non-code files, counting occurrences, when LSP returns empty (fall back explicitly).

**Rule:** "navigating by symbol" = LSP; "searching for text" = Grep.

### Fallback signals

If `LSP goToDefinition` returns `[]` or errors:
1. Verify file is under `include` in `pyrightconfig.json` (Python) or covered by a `tsconfig.json` (TS)
2. For Python — check `.venv` symlink (`ls -la .venv`)
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

- **`PlacementRequest`** is the central entity (ad placement). Aliased as `Campaign = PlacementRequest` in analytics/cleanup code.
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

**Rules:**
- Every new task MUST have explicit `queue=` in `@celery_app.task(...)` AND a matching pattern in `task_routes` in `celery_app.py`.
- Queue constants live in `src/tasks/celery_app.py` (e.g. `QUEUE_WORKER_CRITICAL`).
- 4 periodic notification tasks (`auto_approve_placements`, `notify_pending_placement_reminders`, `notify_expiring_plans`, `notify_expired_plans`) intentionally use `queue=mailing` despite `notifications:*` prefix — decorator overrides `task_routes`. Correct: `mailing` = scheduled batches, `notifications` = event-driven.
- `task_routes` uses **colon-patterns** (`mailing:*`) — Celery fnmatch matches against task names. Dot-patterns (`mailing.*`) do NOT match. Never revert.

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
- `bot.session.close()` must NEVER be called in task code — both factories manage their own lifecycle.

### Service Transaction Contract (S-48)

Transactions belong to the highest layer that knows the unit of work. Three patterns coexist; new code MUST identify which pattern it follows. Patterns 2 and 3 require an inline marker on the `commit()` call.

#### Pattern 1 — Caller-owns (default)

Service receives `session: AsyncSession` (via `__init__` or method param) and **NEVER** calls `session.commit()`, `session.flush()`, or `session.rollback()`. Caller (typically a FastAPI router via `Depends(get_db_session)`) owns lifecycle. `get_db_session` auto-commits on success, rolls back on exception.

- **MUST NOT** `async with session.begin()` — poisons sessions with active autobegin.
- **MUST NOT** `commit()` / `rollback()`.
- **MAY** `flush()` to materialise constraints early.
- **MAY** `async with session.begin_nested()` (SAVEPOINT) for independent sub-block rollback.

No marker. Use this unless you have a specific reason not to. Examples: `ContractService`, `LegalProfileService`, `PlacementTransitionService`, `ChannelService`, `BillingService`, `PayoutService`.

#### Pattern 2 — Self-contained

Method opens its own session via `async with async_session_factory() as session: ...`. Session never crosses method boundary. MUST commit within scope before exit (otherwise implicit rollback reverts writes).

Use only for **leaf operations called from sessionless contexts** — typically Celery tasks receiving primitive args.

Marker:
```python
await session.commit()  # S-48: self-contained pattern
```

Examples: `badge_service.check_and_award_badges`, `award_badge`, `check_achievements` (called from `tasks/badge_tasks.py`).

#### Pattern 3 — External-boundary

Service receives `session: AsyncSession` from caller AND commits at a well-defined point pairing with an external-system interaction. Use only when:

- Service just performed an irreversible external side-effect (Telegram send, payment-provider call)
- DB state confirming it MUST be visible to retry workers before further work fails and rolls back
- `flush()` insufficient (writes inside open tx invisible to other processes)

Replacing `commit()` with `flush()` here reintroduces double-execution risk (e.g., double-publish to Telegram).

Marker:
```python
await session.commit()  # S-48: external-boundary (<short description>)
```

Example: `publication_service.publish_placement` after Telegram send. **Pattern 3 is rare.** Default to Pattern 1.

#### Auditing

A `commit()` in `src/core/services/` is not automatically a violation. Classify by session ownership:
1. Method receives `session` arg → Pattern 1 (commit wrong; remove) OR Pattern 3 (correct; mark).
2. Method opens `async with async_session_factory()` → Pattern 2 (commit required; mark).

`grep` alone cannot distinguish Pattern 1 violation from Pattern 3 carve-out. Verify session ownership before classifying.

#### Idempotency keys

Financial events carry stable keys on `Transaction.idempotency_key` (UNIQUE index). EXISTS-check early-exit covers happy path; `try/except IntegrityError` around `flush()` covers race-past-EXISTS.

Format in use:
- `escrow_freeze:placement={id}`
- `escrow_release:placement={id}:{owner|platform}`
- `refund:placement={id}:scenario={scenario}:{advertiser|owner}`

### Notification Helpers (S-37)

- `_notify_user_async(telegram_id, message, ...)` — low-level send, no `notifications_enabled` check. Admin alerts and system messages.
- `_notify_user_checked(user_id, message, ...) -> bool` — checks `user.notifications_enabled` via DB lookup (by internal `user.id`). Returns `False` if skipped/not-found/blocked. **All new user-facing notification tasks must use this helper.**
- `mailing:notify_user(telegram_id, ...)` — public entry point; checks `notifications_enabled` via `get_by_telegram_id`. If user not found, sends anyway (system/auth flows).
- **Rule:** `Bot()` never created in `core/services/`. Service needing to send → dispatch Celery task.

## Migration Strategy (Pre-Production)

**CURRENT RULE (until first production user):**
- Do NOT create incremental Alembic migrations for model changes
- Edit `src/db/migrations/versions/0001_initial_schema.py` directly
- After editing: drop and recreate the DB, then `alembic upgrade head`

**Reset:**
```bash
docker compose exec db psql -U postgres \
  -c "DROP DATABASE market_bot_db; CREATE DATABASE market_bot_db;" \
  && docker compose exec api poetry run alembic -c alembic.ini upgrade head
```

**Verify after every model change:**
```bash
docker compose exec api poetry run alembic -c alembic.ini check
# Must output: "No new upgrade operations detected."
```

**Switch to incremental migrations ONLY when:** first real user appears in production. Then `0001_initial_schema.py` becomes immutable (standard Alembic rules).

## Ruff Configuration

Target: Python 3.13, line length 100. Rules: E, F, I, N, W, UP, B, C4, SIM. Always run `make lint` before committing.

## Payments (Промт 15.7)

Active payment provider: **YooKassa** (cards, SBP, YooMoney).

Single source of truth: `src/constants/fees.py`. Hardcoding any of these values is blocked by `tests/unit/test_no_hardcoded_fees.py`.

- **Topup:** YooKassa pass-through 3.5% (`YOOKASSA_FEE_RATE = 0.035`). User pays `desired_balance × (1 + 0.035)`. Platform earns 0.
- **Placement successful release:** 20% / 80% gross split (`PLATFORM_COMMISSION_RATE = 0.20`, `OWNER_SHARE_RATE = 0.80`) plus 1.5% service fee withheld from owner gross (`SERVICE_FEE_RATE = 0.015`). Effective: owner net **78.8%**, platform total **21.2%** of `final_price`.
- **Cancel after_confirmation (post-escrow, pre-publish):** 50/40/10 — `CANCEL_REFUND_ADVERTISER_RATE = 0.50`, `CANCEL_REFUND_OWNER_RATE = 0.40`, `CANCEL_REFUND_PLATFORM_RATE = 0.10`. Pre-escrow cancel = 100% advertiser refund. Post-publish cancel = 0% refund (treated as completed).
- **Payout fee** (withdrawal): 1.5% (`PAYOUT_FEE_RATE` in `src/constants/payments.py`).

Credits system: `credits_per_rub_for_plan = 1.0`.

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

**screen → hook → api-module — единственный путь вызова бэкенда из `web_portal/src/` и `mini_app/src/`.**

- Экран никогда не импортирует `api` напрямую — только hook.
- Hook инкапсулирует React Query / мутацию и вызывает функцию из `web_portal/src/api/<domain>.ts` (или `mini_app/src/lib/`).
- API-модуль — единственное место, где собирается URL и параметры.
- Правило проверяется трёхступенчато:
    1. ESLint `no-restricted-imports` (S-46) — блокирует прямые `import { api }` в `screens/**`, `components/**`, `hooks/**`.
    2. `scripts/check_forbidden_patterns.sh` (S-48) — grep-guard на 7 регрессионных паттернов.
    3. CI `.github/workflows/contract-check.yml` — прогоняет 1 + 2 + pytest `tests/unit/test_contract_schemas.py` + `tests/unit/api/`.

**Добавление нового endpoint'а:**
1. Pydantic-схема ответа в `src/api/schemas/<domain>.py` (или прямо в роутере). Любое изменение формы → `tests/unit/test_contract_schemas.py` ломается → `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py` и закоммитить snapshot в ту же PR.
2. Добавить функцию в `web_portal/src/api/<domain>.ts` — единственное место с fetch/ky.
3. Добавить hook в `web_portal/src/hooks/`.
4. Подключить hook в экране. Прямой вызов `api.*` в экране — fail CI.

## Contract drift guard (FIX_PLAN_06 §6.1 Variant B + plan-04)

`tests/unit/test_contract_schemas.py` снимает JSON-schema-снимки 18 моделей и валидирует их против файлов в `tests/unit/snapshots/*.json`. Любое изменение формы (переименование/добавление/удаление поля, смена типа) ломает тест с unified diff — автор пересгенерирует snapshot и закоммитит рядом со схемой.

**Item-схемы (8):** `UserResponse`, `UserAdminResponse`, `PlacementResponse`, `PayoutResponse`, `ContractResponse`, `DisputeResponse`, `LegalProfileResponse`, `ChannelResponse`.

**List wrappers (10):** `AdminPayoutListResponse`, `AdminContractListResponse`, `UserListAdminResponse`, `DisputeListAdminResponse`, `FeedbackListAdminResponse`, `DisputeListResponse`, `FeedbackListResponse`, `ContractListResponse`, `CampaignListResponse`, `CampaignsListResponse`. Покрывают форму `{items, total, limit, offset}`.

**Сознательно НЕ покрыто:** `GET /api/payouts/` (`list[PayoutResponse]`), `GET /api/admin/audit-logs` (inline `dict`).

Регенерация: `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py`.

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

### ORD Integration (legal — ФЗ-38)

- `stub_ord_provider.py` issues synthetic ERID
- `ORD_BLOCK_WITHOUT_ERID=false` in current `.env` — publications pass with stub ERID
- Legal exposure: ФЗ-38 requires real ERID from official ОРД operator

**Required before launch:**
1. Contract with ОРД provider (Яндекс ОРД API v7, VK Реклама, Ozon)
2. API credentials in `.env`: `ORD_PROVIDER=yandex`, `ORD_API_KEY=...`, `ORD_API_URL=...`
3. Set `ORD_BLOCK_WITHOUT_ERID=true` in production
4. Real provider auto-selected by `ORD_PROVIDER` (no code change)
5. E2E test: placement with real ERID passes, without it — blocked

### FNS Validation (optional hardening, not a launch blocker)

- `fns_validation_service.py` validates checksum only
- Post-launch hardening — integrate `npchk.nalog.ru`
- Does not block launch (checksum sufficient against typos)

## Deferred E2E items (plan-08)

Three flows in `web_portal/tests/specs/deep-flows.spec.ts` are permanently `test.fixme`'d. Re-activation criteria in `reports/docs-architect/BACKLOG.md`.

| ID | Flow | Blocked by |
|---|---|---|
| BL-001 | Dispute round-trip | seed-fixture: escrow placement + open disputable window |
| BL-002 | Channel add via bot verification | Telegram Bot API mock in docker-compose.test.yml |
| BL-003 | KEP signature on framework contract | КриптоПро stub or `signature_method=sms_code` fallback |

Do **not** add new `test.fixme(true, ...)` blocks without a matching BL entry.

---

## Engineering Principles

These govern non-trivial work. They override time-saving heuristics within the current sub-block scope. They do NOT override safety rules, S-48, or explicit Marina decisions.

### Principle 1 — Architectural cleanliness over schedule (within sub-block scope)

Within the current sub-block, choose clean over quick. Workarounds compound; clean code does not.

If achieving cleanliness requires changes that **expand beyond the current sub-block** (touch upcoming-block plan, modify shipped CHANGES, require schema/migration revision), STOP and surface to planner. Do not expand scope autonomously across sub-block boundaries.

### Principle 2 — Three-phase workflow for non-trivial tasks

Non-trivial = ANY of: touches >2 files, crosses module boundary, has multiple plausible architectural approaches, plan contains unresolved ambiguity. Trivial work (single-file edit, signature copy, mechanical refactor with established pattern) skips phases A/B.

- **Phase A — Investigate.** Build full picture before any mutation: existing patterns, all callers, related code, constraints, types. No mutations during Phase A. Output to `tmp/<task>_investigation.md` if substantial.
- **Phase B — Re-evaluate.** Given findings: is original plan still right? Better approach within sub-block? Crosses sub-block boundary? STOP and surface.
- **Phase C — Execute.** Only after A and B complete. Per-commit gates per prompt.

Investigate before deciding, re-evaluate before executing.

### Principle 3 — No workarounds

A workaround is any of:
- Inline fix whose rationale lives only in commit message
- New code with `TODO`, `FIXME`, `HACK`, `temporary`, "for now" comments
- Symptom handling instead of root cause (`try: x() except: pass`)
- Special-case branch instead of correct generalization
- Magic number / hardcoded path duplicating named constant
- Copy-paste of similar logic instead of extracted shared helper (when actually same)

If a workaround forms during execution: investigate root cause (return to Phase A), propose proper fix. If proper fix fits in sub-block — do it. If it expands scope — STOP, surface. **Do not commit "for now" intending to fix later.** The "for now" version is what ships.

### Principle 4 — Once-correctly over twice-iteratively

If two solutions exist and one is "good enough but I'd want to revisit later", choose the other. If the right approach takes 3x longer but eliminates a follow-up cleanup commit, take the longer path. If a refactor is justified by current work, do it now in the same commit (within sub-block scope per P1).

This applies within the agent's autonomous decision space. Cross-sub-block decisions remain Marina's territory.

### Principle 5 — Conflict handling

When principles conflict with elsewhere-stated rules:
- **Safety rules** (ПД discipline, no-secrets-in-commits): always win, no exception
- **S-48 contract**: wins
- **Explicit Marina decisions** in current prompt: win
- **BL-013 stop-hook defer (b)/(c)**: applies to documentation bundling only; do NOT defer code-quality decisions or proper-fix-vs-workaround judgments
- **Time / token budget heuristics**: lose to these principles within sub-block scope

When uncertain about a conflict, surface to planner.

### Self-audit before each commit

1. Did I investigate before executing? (P2)
2. Did I re-evaluate plan against findings? (P2)
3. Is anything I'm shipping a workaround per P3?
4. Is there a once-correctly version I'm declining for time? (P4)
5. If I diverged from prompt, is the divergence within sub-block scope? (P1)

If any answer fails — return to investigation or surface to planner. Do not commit through a failed self-check.

---

## Research reports — Objections section (MANDATORY)

When producing a research / consolidation report before any implementation: if you spot any of the following, raise them **explicitly in a "Возражения и риски" section, BEFORE "Вопросы для подтверждения":**

- Security holes (auth bypass, missing rate-limit, replay, weak validation)
- Internal contradictions (plan says X but codebase pattern is Y)
- Missed edge cases (race conditions, concurrent writes, Redis flush, partial failure)
- Bad naming (semantic mismatch between term and what it denotes)
- API ergonomics traps (defaults that disable safety, optional params that should be required)

Do **NOT** disguise objections as clarifying questions. Better to surface five uncomfortable observations than skip one security hole. The user expects you to push back when you have grounds.

### Phase mode discipline

Be explicit about which mode you're in.

**Research / planning mode** (deep-dive Explore, audits, plan reviews, consolidation reports BEFORE code is written):
> "Be critical. Look for problems. Dispute decisions with reasoning."

Raise concerns aggressively. The expected output is a sharper plan, not agreement.

**Implementation mode** (writing/editing code per agreed plan):
> "Implement as written. If a blocking problem surfaces — stop and report. Do NOT introduce improvements not in the plan."

Cosmetic refactors, "while-I'm-here" cleanups, extra abstraction layers — out of scope unless plan asks.

### What counts as "raise explicitly" vs "defer"

**Raise explicitly (block the work):**
- (a) Security problem (auth bypass, missing validation, secret exposure, rate-limit gap, replay, signature trust assumption)
- (b) Bug or likely bug (race, off-by-one, wrong type, missing error path firing under realistic load)
- (c) Plain contradiction (plan says X but codebase does Y; two parts conflict)
- (d) Decision that materially complicates future maintenance (heavy coupling, premature abstraction, hidden invariant, deletion of load-bearing affordance)

**Defer to one-line footnote** ("возможные дальнейшие улучшения, не требуют действий сейчас"):
- Cosmetic refactors, style nits, test coverage gaps in untouched code, perf opts without measured impact, naming preferences without semantic mismatch

Rule: future maintainer would shrug → defer. Future maintainer hits a real incident → raise.

### Plan validation gate (MANDATORY before approving any Phase N plan)

Before "research → STOP → implementation" handoff, run these checks. Failure = plan reworked, not patched during implementation.

- **(a) `tsc --noEmit` dry-run** with the plan's strip-list applied to `mini_app/` and `web_portal/`. If the plan removes files / hooks / api modules, simulate locally and confirm both frontends still build.
- **(b) Per-endpoint PII classification** for every endpoint switched to web_portal-only auth. Read request schema + response schema + service-side DB writes. No-PII endpoint requires explicit UX-cost justification or carve-out. File-name heuristics not a substitute.
- **(c) Audit of merged decisions from previous phases.** Diff plan text against codebase reality on `develop`. Anything plan says is already-true must be already-true, or plan needs explicit "drift fix" commit as first step.
- **(d) Ruff baseline diff.** `make lint` before any edit; compare after alignment commit. Plans must not regress baseline.
- **(e) Cross-artifact reference check (BL-015).** Every BL-ID, ticket ID, file path, line, commit SHA must resolve. Run `grep -E '\b(BL-[0-9]+|plan-[0-9]+|FIXME|TODO\([^)]+\))\b' <plan>.md` and verify.
- **(f) Test infrastructure surface (BL-024).** Before any plan touching tests is approved, `grep -rn 'autouse=True' tests/` and review `conftest.py` hierarchy. Document autouse fixtures and shadowing. **`tests/integration/conftest.py` is load-bearing infra** — its NullPool + connection-rollback override is intentional, not a cleanup target.
- **(g) Mutation-audit completeness (BL-026).** When auditing field writes, enumerate (1) calls to helpers matching `update_<field>|set_<field>|change_<field>` and (2) bulk SQLAlchemy `.values(<field>=...)` writes — both accept runtime values and bypass static literal scans. Where possible, **delete** parameter-driven helpers rather than lint-allow.
- **(h) Verify gate naming.** Each command actually covers what's intended? Use `make -n <target>` dry-run before declaring command as gate. (Origin: BL-057 — series 16.x verify gates were de-facto lint-only because `make ci-local` halted on baseline.)

The output is a short alignment commit (`docs(phase-N): align plan with PF.X / O.Y decisions`) on the feature branch *before* any implementation commit. Skipping the gate or rolling its findings into the first implementation commit defeats the purpose.

Research-agent enumerations (Agent A/B/C, deep-dive Explore catalogs) are **incomplete-by-default**. § B.1 of any phase plan begins with a "final mutation audit" step that re-greps for the relevant pattern.

---

## Process discipline

### Stop-hook relay protocol (BL-006, BL-013, BL-016)

Stop-hook output is **informational** — surfaces documentation gaps to the user, does not authorise the agent to close them. The agent's correct response:

1. Relay the warning to the user with three-way choice:
   - **(a) immediate fix-commit** (warning is load-bearing — public contract changed and CHANGES is genuinely missing)
   - **(b) bundle into next natural commit** (default — warning will be addressed at next commit boundary anyway)
   - **(c) defer to phase closure** (only if no risk of CHANGES becoming stale relative to documented commits — i.e. the WIP itself is the phase closure work)

Defer (b)/(c) applies to documentation bundling only. Do not use BL-013 defer to postpone code-quality decisions or ship a workaround "for now" (see Principle 3).

**Loop-firing tolerance:** if the **same** hook warning fires more than twice in succession on identical HEAD/transcript state, ack twice non-trivially, then silent-ignore subsequent identical fires. Identical fires within a single decision point count as ONE ack, not multiple. This avoids the BL-016 anti-pattern where each post-commit turn re-issues the same warning, burning context and pressuring the agent into autonomous fix to "stop the alarm".

The STOP gate (research → STOP → user "давай" → implementation) applies to **every commit**, including `docs(...)` / `chore(...)` — not only `feat(...)` / `fix(...)`.

### Cross-artifact reference fabrication (BL-015)

Before committing any plan / CHANGES / BACKLOG entry that cross-refs another doc by name, ID, or section: `grep` for the target and confirm it exists. Once a fabricated reference enters one artifact, copy-paste through prompt templates multiplies it.

### Stale plan vs reality (BL-007, BL-018)

The implementation plan is allowed to drift between sessions. Line numbers in the plan are HINTS, not absolutes. Sub-agent searches must work by signature/content, not by `L<N>`. If the plan describes a file/function/line no longer matching reality, surface explicitly — do not silently adapt.

### Verification gate language (BL-018, BL-028)

GitHub Actions are permanently inert (BL-017 ACCEPTED). The actual verification gate is `make ci-local`. Phase plans must phrase verification gates as:

> "Local `make ci-local` passes against baseline X (failed=N1, errored=N2, collection=N3, mypy=N4, ruff=N5)."

— not "CI green" and not bare numbers like "76 failed". Baseline numbers must always be quoted with the **exact invocation** (`pytest --continue-on-collection-errors tests/` and `make ci-local` produce different counts on the same source tree — BL-028).

Baseline updates land per-phase as part of `CHANGES_*.md`, not as standalone documents.

---

## Text Artifact Control

In this project all identifiers, file names, keywords, and project
names are written in a single writing system without hidden characters.
Before any file write, before grep/search, and before code generation,
check the text (your own and the user's) for the following artifacts
and normalize them.

### 1. Homoglyph substitutions (visually similar letters from other alphabets)

Inside a Russian word, only Cyrillic letters should appear.
Suspicious twins from Latin and Greek:
- Latin in a Cyrillic word: a e o p c x y i A B C E H K M O P T X Y
- Cyrillic in a Latin word: а е о р с х у і
- Greek letters near either: ο (omicron), α, ρ, ν, μ, τ

### 2. Latin diacritics in a Russian context

Š š Č č Ž ž Ć ć Đ đ Ř ř Ł ł Ń ń ě ş ţ — for a Russian-language project,
this is almost always an autogeneration artifact, not deliberate text.

### 3. Mixed scripts within a single word

A word must be entirely in one alphabet. Artifacts:
- "шagh", "Pуссkий", "файл.tхt", "Šаг" instead of "Шаг"
- Do not confuse with legitimate cases: "GitHub-репозиторий", "API-ключ" —
  these are separate words joined by a hyphen, not script mixing within one word.

### 4. Invisible and control characters

These should not appear in plain text:
- Zero-width: U+200B, U+200C, U+200D, U+FEFF (BOM)
- Soft hyphen: U+00AD
- Bidirectional overrides: U+202A–U+202E, U+2066–U+2069
- Word joiner: U+2060

### 5. Non-standard spaces

- Non-breaking space (U+00A0) where a regular space is expected
- Narrow no-break space (U+202F), em/en space, hair space
- In code and identifiers — always normalize to U+0020.

### 6. Typography vs ASCII

In code, configs, and commands — ASCII only:
- Quotes: " ' instead of " " ' '
- Dashes: - instead of — – −
- Ellipsis: ... instead of …

### Actions on detection

- **Code, identifiers, file names, paths** — normalize
  immediately and without asking; this is a functional risk.
- **Configs, YAML frontmatter, JSON keys** — normalize immediately.
- **Documentation and comments** — normalize if the artifact
  breaks project consistency.
- **User-facing strings and UI text** — ask before
  replacing; they may be intentional.
- After normalization, briefly list what was found, where, and what it was replaced with.

### Before grep / Glob / project-wide search

If you are searching for the project name or another term that may
have ended up in the code under several spellings — first check
whether homoglyph or diacritic variants exist, and use an extended
pattern or several search passes.

---

## Documentation & Changelog Sync (MANDATORY)

This section is enforced by hooks. Every task is INCOMPLETE without these steps.

### After EVERY code change
1. Create `reports/docs-architect/discovery/CHANGES_<YYYY-MM-DD>_<short-desc>.md`
   - List: affected files, business logic impact, new/changed API/FSM/DB contracts
   - Footer: `🔍 Verified against: <commit_hash> | 📅 Updated: <ISO8601>`
2. Append-only: never rewrite existing CHANGES_*.md files.

### After EVERY sprint / milestone
1. Update `CHANGELOG.md` → move `[Unreleased]` to `[vX.Y.Z] - <YYYY-MM-DD>`
   Sections: Added | Changed | Fixed | Removed | Breaking | Migration Notes

---

## Git Flow (MANDATORY — local-merge-only model per BL-017)

**Workflow:** `feature/*` → `develop` → `main`. **All operations are LOCAL.** No `git push` to remote — GitHub CI is permanently inactive (BL-017 ACCEPTED). Real verification gate is `make ci-local`.

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
- [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`
- English, imperative, under 72 chars
- NEVER force-push, rebase, or squash on feature branches — preserve history

### After EVERY sprint / feature completion (local merges only)

```bash
# 1. Verify clean state
git status   # must be "nothing to commit, working tree clean"

# 2. Merge feature into develop (local, --no-ff required)
git checkout develop
git merge $CURRENT_BRANCH --no-ff -m "chore(develop): merge $CURRENT_BRANCH — <sprint summary>"

# 3. Merge develop into main (local, --no-ff required)
git checkout main
git merge develop --no-ff -m "chore(main): merge develop — <sprint summary>"

# 4. Return to feature branch (or delete it)
git checkout $CURRENT_BRANCH
```

**Hard limits:**
- `--no-ff` REQUIRED on every merge — never fast-forward
- On ANY conflict: **STOP and report** — never auto-resolve
- Never force-push `develop` or `main` (and never push at all)
- Feature branch is preserved post-merge unless Marina explicitly says delete

### HIGH-CONSEQUENCE FILES (require explicit Marina approval)

The files listed below carry high blast radius (PII encryption, audit
integrity, legal/compliance state, schema invariants). Modifications
require explicit Marina approval before commit. The agent must STOP
and surface a change proposal — not proceed autonomously.

Migration policy (forward-only post-apply per BL-061; pre-prod exception
for `0001_initial_schema.py` editable until first production user)
overlaps with the listed entry — intentional defense-in-depth.

```
src/core/security/field_encryption.py
src/api/middleware/log_sanitizer.py
src/db/models/audit_log.py
src/db/models/legal_profile.py
src/db/models/contract.py
src/db/models/ord_registration.py
src/db/migrations/versions/          ← read-only after production apply (pre-prod exception: 0001_initial_schema.py editable until first user)
```

Note: `src/api/middleware/audit_middleware.py` was previously listed but removed for Phase 1 §1.B.0b refactor (PF.4 decision — JWT re-decode replaced with `request.state.user_id` read). After Phase 1 merge, it's owned by Phase 1; do not re-add unless the security model around audit logging changes.

### Landing-specific rules

- Landing lives in: `/opt/market-telegram-bot/landing/`
- It is FULLY STATIC — never add runtime FastAPI calls
- Tailwind `@theme` tokens come from `DESIGN.md` only
- TS version: 6.0.2 (align with mini_app and web_portal)
- Motion imports: `import { ... } from 'motion/react'` (package name: `motion`)
- CSP: no unsafe-inline, no unsafe-eval
- Fonts: DM Sans, Outfit, Poppins, Roboto — all via Google Fonts
