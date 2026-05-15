# BL-107 — Consolidated Closure CHANGES

**Workstream:** Channel registration verification (ФЗ-303 compliance)
**Phases:** B.1 — B.9 + 3 CI gate rounds (PROMPT 44 / 45 / 45-ext / 45-ext-of-ext)
**Date:** 2026-05-15
**Tag:** v0.9.0
**Branch merged:** `feature/bl-107-channel-registration-verification` → `develop`

## Executive summary

ФЗ-303 от 08.08.2024 requires Telegram channels ≥10 000 subscribers to register in Roskomnadzor's blogger registry. BL-107 brings the platform into compliance through three complementary mechanisms: add-time enforcement (G19 placement gate + Trustchannelbot auto-verification), a manual evidence escape hatch (owner submission + admin review), and daily drift detection (Celery re-verification). Phase B also folds in BL-002 (channel-add E2E mock infrastructure) and closes the O.7 carve-out (bot path `is_test` parity). The closing CI gate rounds (PROMPT 44 / 45 / extensions) caught three latent production defects: a G19 gate eager-load regression, a SQLAlchemy `Mapped[StrEnum]` case-mismatch, and a `/api/analytics/summary` validation gap. Final state: ci-local 1204 passed (0 failed); test-e2e BL-107 own 12/12 PASS across 3 browser projects; 13 residual fails (R4/R5/R6/R10), all pre-existing baseline or test-infra, all filed to BACKLOG.

## Phase-by-phase summary

### Phase B.1 — Schema foundation (`4ab6d7c`)

Adds 7 verification-state fields to `TelegramChat` (`is_blogger_registry_verified`, `blogger_registry_verified_at`, `blogger_registry_application_number`, `blogger_registry_verified_by_admin_id`, `blogger_registry_verification_method`, `member_count_at_verification`, `last_blogger_registry_check_at`) plus the `BloggerRegistryVerificationMethod(StrEnum)` enum with members `trustchannelbot_admin` and `manual_evidence`. Per BL-061 pre-prod exception, edits `0001_initial_schema.py` in place (no incremental revision). Forced scope expansion: adding a second FK from `telegram_chats` to `users` ambiguated the existing bidirectional `back_populates` and required explicit `foreign_keys=` on both sides (`TelegramChat.owner` ↔ `User.telegram_chats`) — a one-line surgical fix on each model. 15 introspection-level regression tests pin column shape, enum contract, and ORM instantiation.

### Phase B.2 — Gate framework (`97137d9`)

Adds `PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED`, three `GateReason` codes (`BLOGGER_REGISTRY_NOT_VERIFIED`, `BLOGGER_REGISTRY_PENDING_REVIEW`, `SUBSCRIBER_COUNT_UNKNOWN` reserved for B.3), and the new `ChannelAddContext` frozen dataclass. G19 implementation follows the existing dual-variant pattern (placement-side `check_g19` + channel-context `check_g19_channel_add` sharing pure-logic core `_check_g19_core`). A parallel registry `_CHANNEL_CONTEXT_GATE_CHECKERS` plus the `_CHANNEL_ADD_GATES` resolution table and `check_gates_for_channel_add` orchestration method live alongside the existing per-role/per-transition machinery. G19 also extends `_TRANSITION_GATES` for `(pending_owner, pending_payment)` and `(counter_offer, pending_payment)` — placement-side defence-in-depth for channels added before the gate landed. 22 pure-unit tests + contract-snapshot regen.

### Phase B.3 — Telegram API + settings (`8bf5e55`)

Introduces `src/utils/telegram/verify_blogger_registry.py` with the cross-SDK `TelegramAdminLister(Protocol)` (duck-typed against both `aiogram.Bot` and `python-telegram-bot.Bot`), a lazy in-memory cache for the Trustchannelbot ID with `asyncio.Lock` for concurrent-safe resolution, `verify_trustchannelbot_admin(bot, chat_id)`, and `TrustchannelbotResolutionError`. Five new `rkn_*` Settings fields wire the threshold (10 000), Trustchannelbot username/ID override, periodic-check feature flag, and `rkn_block_unverified_placements` production guard; `.env.example` updated. Replaces the Phase B.2 temporary `_DEFAULT_RKN_THRESHOLD = 10_000` module constant with `settings.rkn_threshold_subscribers`. 11 unit tests cover cache lock, env override, API failures, and reset helper.

### Phase B.4 — Channel-add hookup (`03a82fb`)

Wires the Trustchannelbot helper and channel-context G19 gate into both add paths — API router (`src/api/routers/channels.py:create_channel`) and bot handler (`src/bot/handlers/owner/channel_owner.py:add_channel_confirm`) — through the same single `check_gates_for_channel_add` orchestration call. On verification success: 5 audit fields populated (`is_blogger_registry_verified`, `verified_at`, `verification_method=TRUSTCHANNELBOT_ADMIN`, `member_count_at_verification`, `last_blogger_registry_check_at`). On `TrustchannelbotResolutionError`: blocks add with `SUBSCRIBER_COUNT_UNKNOWN`, writes audit log, user-facing message. Admin test bypass (`is_admin AND body.is_test`) skips both `check_gates_for_user_role` and G19 verification. Forced Phase B.3 fix: `TelegramAdminLister.get_chat_administrators` return type relaxed from `list[Any]` to `Sequence[Any]` to accept both SDK return shapes (`tuple` vs `list`). 9 wiring tests (5 API + 4 bot) + 1 existing test fixture update.

### Phase B.5a — Admin review backend (`59cf1ef`)

5 new endpoints: `POST /api/channels/{id}/submit-registry-evidence` (owner), `GET /api/admin/channel-verifications` (paginated list with status filter), `GET /api/admin/channel-verifications/{id}` (detail with audit history), `POST /api/admin/channel-verifications/{id}/verify` (sets `is_verified=True`, `method=manual_evidence`, populates all 6 audit fields), `POST /api/admin/channel-verifications/{id}/reject` (resets `application_number` for re-submission). 9 Pydantic schemas in `src/api/schemas/channel_verification.py` with `extra="forbid"`. Two new notification helpers in `NotificationService` follow S-48 Pattern 1 (caller-owns session, dispatch via `notify_user.delay()`): `notify_admins_evidence_submitted`, `notify_owner_verification_decided(decision: "verified" | "rejected")`. 21 unit tests across submit (7) and admin endpoints (14) — happy-path, conflict guards (409 on already-verified / no-submission), permission (403 non-admin), validation (422 on schema violations).

### Phase B.5b — Frontend (`e114948`)

Admin: 2 web_portal screens (`AdminChannelVerificationsList` paginated queue with `pending_review` / `verified` filter; `AdminChannelVerificationDetail` two-column layout + inline verify/reject forms with required reason / optional notes). Hooks: `useAdminChannelVerifications`, `useAdminChannelVerificationDetail`, `useVerifyChannelManually`, `useRejectChannelVerification` (mutations invalidate detail + list queries). API client in `web_portal/src/api/admin_channel_verifications.ts`. Sidebar entry "Проверка каналов" between Споры/Обращения; 2 new routes; breadcrumbs added. Owner mini_app: `OwnSubmitRegistryEvidence` screen with vanilla validation (3 fields: required `application_number`, optional `registry_url`, optional `notes`), CSS module pattern, haptic feedback, success toast. Entry button in `OwnChannelDetail` for channels ≥10k. UI strings hardcoded Russian per project convention. **Acknowledged gap:** vitest infrastructure absent in both frontends → component tests deferred to Phase B.9.A.

### Phase B.6 — Periodic re-verification Celery task (`5485729`)

New `src/tasks/channel_registry_tasks.py` (~175 lines) with `parser:check_channel_registry_status` task on queue `parser`. Daily at 03:45 UTC (slot between collect-stats 03:30 and Sunday cleanup 03:00). For each channel ≥10k where `is_test=False`, `is_active=True`, and `verification_method=TRUSTCHANNELBOT_ADMIN`: refresh `member_count`, re-call `verify_trustchannelbot_admin`. If Trustchannelbot removed → reset 5 verification fields, write `blogger_registry_auto_unverified` audit, notify owner via new `notify_owner_verification_lost` helper. `MANUAL_EVIDENCE` channels excluded by design (admin judgement is stable). Threshold-crossing counter increments when `member_count_at_verification < threshold ≤ member_count` (admin can manually re-review). Feature-flagged via `settings.rkn_periodic_check_enabled`. Returns observability counters; uses `ephemeral_bot()` + `celery_async_session_factory` per S-37/S-48. 11 unit tests pin all branches; coverage 98%.

### Phase B.7 — Bot is_test parity (`e6fd580`)

Closes the O.7 5b.7a deferred carve-out. Adds FSM state `selecting_is_test` between `selecting_category` and `confirming`. Admin owners get a new inline-keyboard step (Тестовый / Реальный); non-admins skip the step and proceed with `is_test=False` default — UX preserved exactly. Defense-in-depth `user.is_admin` checks at both the FSM gate handler and `add_channel_confirm` cover stale state / direct callback injection. `add_channel_confirm` now reads `is_test_flag` from FSM data (was hardcoded `False`) and passes it explicitly to `TelegramChat(...)`. 8 unit tests cover both branches + defense-in-depth + happy paths.

### Phase B.8 — Mock infrastructure (`d8da720`) — closes BL-002

Custom aiohttp Telegram Bot API stub at `tests/e2e/telegram_api_stub/` (Application with 9 method handlers + safe-noop catch-all, fixtures dataclass with `@verified_channel`/`@not_verified_channel`/`@api_failure` JSON sets, thread-safe `StubState` for side-effect introspection via `/__stub__/state`/`/__stub__/reset`). Minimal `python:3.12-slim + aiohttp` Dockerfile; new `telegram-stub` service in `docker-compose.test.yml` joined to `e2e_network` with `/health` healthcheck. New `telegram_api_base_url` Setting (alias `TELEGRAM_API_BASE_URL`) routes both Telegram SDKs through the stub when set: `src/bot/session_factory.py:new_bot()` uses `AiohttpSession(api=TelegramAPIServer.from_base(...))`, `src/api/dependencies.py:get_bot()` rewrites `Bot.base_url` and `Bot.base_file_url`. **R4 production guard, 3-layer defense-in-depth:** (L1) `_validate_telegram_api_base_url` model_validator in `Settings` refuses to construct when `sentry_environment == "production" AND telegram_api_base_url is not None` (app cannot start); (L2) `logger.warning` + Sentry breadcrumb in both startup paths; (L3) deploy-script assertion deferred operationally (no accessible deploy script). 21 unit tests across stub server (10) + Settings validator (5) + bot factory routing (6).

### Phase B.9.A — Vitest infrastructure (`6356f4c`)

Pinned dev-dep install (vitest@4.1.6, @testing-library/react@16.3.2, @testing-library/jest-dom@6.9.1, @testing-library/user-event@14.6.1, jsdom@29.1.1, @vitest/ui@4.1.6) + per-frontend `vitest.config.ts` (mergeConfig with Vite, jsdom env, explicit alias mirror) in both web_portal and mini_app. Separate `tsconfig.test.json` (extends app config, adds jest-dom types, relaxes unused-vars), `tsconfig.app.json` exclude clause for `*.test.{ts,tsx}` / `*.spec.{ts,tsx}` / `src/test/**`. `globals: false` chosen for ESLint cleanliness — test files explicitly `import { describe, it, expect, vi } from 'vitest'`. Smoke test in each frontend confirms RTL + jsdom + jest-dom matchers integrated.

### Phase B.9.B — Component tests (`e0124f2`)

9 new component tests (3 per BL-107 screen) using the Phase B.9.A infrastructure: web_portal `AdminChannelVerificationsList` (3: render-with-items / empty-state / row-click-navigation), `AdminChannelVerificationDetail` (3: render-pending / reject-validation-blocks-API / verify-submits-navigates), mini_app `OwnSubmitRegistryEvidence` (3: render-fields / submit-trimmed-payload-navigates / empty-application-number-blocks). `renderWithProviders` helper wraps `QueryClientProvider` (fresh per-test client, retries off) + `MemoryRouter`. Three Phase A carve-out fixes surfaced empirically: `afterEach(cleanup)` in setup (auto-cleanup needs the hook under `globals: false`); `src/**/*.d.ts` added to `tsconfig.test.json` include (ambient declarations need explicit propagation under `moduleDetection: "force"`); `tsconfig.app.json` exclude rewritten without brace expansion (TypeScript glob doesn't support `{ts,tsx}`).

### Phase B.9.C — Playwright BL-002 unblock (`ff93a5a`)

Unwraps the `test.fixme` placeholder at `web_portal/tests/specs/deep-flows.spec.ts:288-296` (left as a marker since plan-08). Replaces with a real `POST /api/channels/check` test against the `@verified_channel` stub fixture — exercises both `bot.get_chat()` and `bot.get_chat_member()` through the Phase B.8 routing. Chosen over `POST /api/channels/` because the latter enforces G04/G05/G06 owner-side legal compliance which the seeded test owner doesn't carry — out-of-scope per Marina prohibitions. BL-002 marker preserved as inline comment for historical traceability.

### Phase B.9.D — E2E coverage (`56a0d8b`)

4 new specs in `web_portal/tests/specs/bl-107-channel-registration.spec.ts`:
- **D.1** verified-channel precheck (POST /api/channels/check, `@verified_channel`)
- **D.2** not-verified channel precheck (`@not_verified_channel`)
- **D.3** manual-evidence full flow (owner submit → admin pending list → admin verify → admin verified list, mixes owner+admin storageState via `apiRequest.newContext`)
- **D.4** periodic re-verification stub-state-introspection proxy (full Celery task invocation requires a worker service in `docker-compose.test.yml`, deferred)

Specs run across 3 Playwright projects (mobile-webkit, mobile-chromium, desktop-chromium) → 12 cases total.

## CI gate work (post-feature)

### PROMPT 44 — initial gate run (4 commits)

First `make ci-local` against the integrated BL-107 stack revealed 4 failures spread across queue routing, gate eager-load, mock contracts, and lint baseline.

- **`db3063b`** — Celery beat schedule set-based refactor (queue resolution).
- **`ef26f68`** — **PRODUCTION FIX.** G19 gate `session.get(TelegramChat, ...)` did not eagerload `placement.channel`, causing a `MissingGreenlet` under async context when the gate fired at transition. Regression from Phase B.2 surfaced only when ci-local exercised the full transition path; caught before any real ramp.
- **`db7e2f1`** — G19 unit-test mock contract alignment (mock `session.get_one` now returns a `TelegramChat` shaped like production rather than a bare `MagicMock`).
- **`8c73591`** — `tests/unit/conftest.py` lint baseline (BL-024 preserved baseline of 7 ruff items).

End of PROMPT 44: ci-local PASS (1204 tests, 2 skipped).

### PROMPT 45 — auth infrastructure (Pattern 1 + 2)

`make test-e2e` surfaced 141 failures, almost all rooted in JWT audience-claim mismatch between Playwright fixtures and the web_portal default audience. Two-pattern auth resolution:

- **`ab554b3` (Pattern 1)** — `JWTService.create_access_token` default audience flipped to `web_portal`; mini_app callers now pass `audience="mini_app"` explicitly. Brings ~50 fails to green by aligning the e2e seed JWTs with the dependency expectations.
- **`8d80c04` (Pattern 2)** — `web_portal/tests/fixtures/test.ts` overrides Playwright's `request` fixture to read `rh_token` from `storageState.localStorage` and inject `Authorization: Bearer …`. Production frontend uses localStorage (not cookies) for auth; Playwright's `request` is a separate `APIRequestContext` that only inherits cookies — so specs calling `request.post(...)` after `test.use({ storageState })` previously shipped no Authorization header and got 401. Pattern 2 closes that gap for the test-fixture `request`.

### PROMPT 45 Extension — residuals cleanup (5 commits)

Three distinct Playwright `APIRequestContext` surfaces had to be addressed separately (test-fixture `request`, `browser.newContext({storageState}).request`, `apiRequest.newContext({storageState})`) plus three latent test/production issues:

- **`368f241` (P2b)** — `apiRequestFor(storageStateFile)` factory in `test.ts` migrates 4 `deep-flows.spec.ts` tests off `browser.newContext({storageState}).request` to the factory; auto-disposes per-test contexts.
- **`f890148` (R2)** — `tests/e2e/telegram_api_stub/app.py` fills python-telegram-bot 21.x required fields on `ChatFullInfo` / `ChatMember` (`accent_color_id`, `max_reaction_count`, full admin permissions defaults). Adds dedicated `handle_get_chat_member_count` returning the bare integer pTB expects.
- **`5676192` (P2c)** — `apiRequest` re-export wrapped to intercept `newContext({storageState, ...})` and inject Authorization from `rh_token`. Closes the third auth-carriage surface (used by BL-107 D.3 spec and others minting contexts outside the test-fixture lifecycle).
- **`9506583` (R1)** — **PRODUCTION FIX.** `/api/analytics/summary` was accepting any `days` query (no validation, no type coercion). Added `days: Annotated[int, Query(ge=1, le=90)] = 30` — FastAPI rejects invalid inputs with 422. Endpoint body unchanged (current aggregate is all-time; param validates a client hint).
- **`d7e0277` (V1)** — 101 visual baselines regenerated after the auth fix chain unblocked rendering.

### PROMPT 45 Extension-of-Extension — final residual sweep (4 commits)

- **`2dfc41c` (R3)** — Spec URL drift: `deep-flows.spec.ts:45` posted to outdated `/api/legal-profile/rules`. Canonical route is `POST /api/contracts/accept-rules` (`src/api/routers/legal_acceptance.py:51`, Phase 1 §1.B.2 carve-out). Same `AcceptRulesRequest` body shape.
- **`24cf68a` (R7)** — **PRODUCTION FIX.** `src/db/models/telegram_chat.py:89-91` declared `blogger_registry_verification_method: Mapped[BloggerRegistryVerificationMethod | None] = mapped_column(nullable=True)` without an explicit `Enum(...)` spec. SQLAlchemy inferred the column type and serialized via member **NAME** (uppercase `"MANUAL_EVIDENCE"`) but the Postgres enum holds member **VALUES** (lowercase `"manual_evidence"`). Insert/update raised `asyncpg.exceptions.InvalidTextRepresentationError`. Fix: declare with explicit `SAEnum(BloggerRegistryVerificationMethod, name="bloggerregistryverificationmethod", values_callable=lambda x: [m.value for m in x])`. Aliased `from sqlalchemy import Enum as SAEnum` to avoid collision with `from enum import Enum` already used by `ChatType`. No migration / schema change — pg enum already correct, only ORM-side serialization config needed.
- **`3615f71` (R8)** — Seed Contract row gap. `scripts/e2e/seed_e2e.py` only set the denormalized `User.platform_rules_accepted_at` cache; `contract_service.needs_accept_rules` reads `ContractRepo.get_latest_acceptance(user_id, contract_type='platform_rules')` (authoritative source). Without a Contract row the frontend `RulesGuard` redirected every protected route to `/accept-rules`, and PROMPT 45's V1 regen captured 101 baselines of the gate page rather than per-route content. Added idempotent `_upsert_platform_rules_acceptance` (template_version=`CONTRACT_TEMPLATE_VERSION`, signature_method=`button_accept`); re-regenerated 99 baselines now capturing real per-route content (spot-checked `/analytics`, `/admin/users`).
- **`fe33654` (R9)** — D.3 cross-project state pollution. Seed creates a singleton `e2e_test_channel`; Playwright runs projects sequentially within one `make test-e2e` invocation, so the first project verified the channel and the next two hit `409 "Channel already verified"`. No backend unverify endpoint exists; spec-only fix branches on `is_blogger_registry_verified` (detected via admin verified-list since `ChannelResponse` omits the field): first project runs the full happy-path, subsequent projects run an idempotent re-assertion (submit → 409 + verified-list contains channel). Common verified-list assertion in both branches.

## Production code changes — audit summary

Three production-code commits, all root-cause-aligned with framework patterns already in use, all surfaced through ci-local / test-e2e gates and re-verified after fix:

| SHA | File | Defect class | Surfaced by |
|---|---|---|---|
| `ef26f68` | `src/core/services/gates/owner_gates.py` | Async eager-load missing on `session.get` | ci-local (PROMPT 44) — gate fired at transition path |
| `9506583` | `src/api/routers/analytics.py` | Latent unvalidated query parameter | test-e2e — spec exercised contract |
| `24cf68a` | `src/db/models/telegram_chat.py` | SQLAlchemy `Mapped[StrEnum]` serializes via NAME, not VALUE | test-e2e D.3 spec — only end-to-end exposure |

R7 in particular illustrates the general pattern: implicit `Mapped[T]` where `T` is a `StrEnum` defaults to serializing member names, but Alembic-generated pg enums hold member values. The fix is a one-line column declaration; the audit pattern is captured as a new BL entry (Mapped[StrEnum] sweep). Memory entry `project_sqlalchemy_strenum_pitfall.md` documents the pattern for future investigation.

## Final state

| Gate | Result |
|---|---|
| `make ci-local` | **PASS** — 1204 passed, 2 skipped, 0 failed, 0 errors |
| `make test-e2e` API contract | 0 failed |
| `make test-e2e` UI Playwright | 13 failed / 251 passed / 15 skipped |
| BL-107 own 4 specs × 3 browsers | **12 / 12 PASS** |
| Net delta from PROMPT 44 baseline | **−128 fails, +128 passes** |

13 residuals categorize cleanly as pre-existing baseline / test-infra:

| Class | Cases | Type | BACKLOG |
|---|---|---|---|
| R4 ticket-login `rh_token` not persisted | 3 | frontend auth bug | new BL |
| R5 wizard step indicator missing | 3 | frontend regression (S-47 phase 5) | new BL |
| R6 channel-settings price string vs number | 3 | backend Decimal serialization | new BL |
| R10 visual baseline flake on 4 routes | 4 | test-infra (seed-time content drift) | new BL |

## Architecture decisions echoed (Marina-locked from Phase A2 design)

- **Q1** — Single helper `LegalComplianceService.check_gates_for_channel_add` invoked from both API and bot call sites.
- **Q2** — Parallel registry `_CHANNEL_CONTEXT_GATE_CHECKERS` with `(session, user, channel_data)` signature. G19 dual registration (placement-side + channel-context) for defence-in-depth against pre-G19 channels.
- **Q3** — Field naming `member_count_*` (NOT `subscriber_count_*`) — channel state reflected in TelegramChat naming convention.
- **Q4** — `member_count_at_verification` snapshot field naming applied consistently across schema, gate body, and audit fields.
- **Q5** — Lazy cache + env override for Trustchannelbot ID resolution (NOT boot-time fetch, NOT manual-only) with `asyncio.Lock` for concurrent-safe resolution.
- **Q6** — `AuditLog.action` is free-form `String(64)`, NOT an enum. Used snake_case strings (`blogger_registry_evidence_submitted`, `blogger_registry_verified_by_admin`, `blogger_registry_rejected_by_admin`, `blogger_registry_auto_unverified`).
- **Q7** — Pagination convention `limit/offset` (matches existing admin endpoints). O.7 carve-out closed in Phase B.7 — bot path `is_test` parity with API capability.
- **Q15** — Sidebar position between Споры and Обращения (semantically groups admin moderation tasks).
- **Q17** — Periodic task in dedicated `channel_registry_tasks.py` rather than appending to `parser_tasks.py` (1400+ lines, topic-bound).
- **Q18** — Only `TRUSTCHANNELBOT_ADMIN` channels re-checked periodically; `MANUAL_EVIDENCE` excluded by design (admin judgement is stable).
- **R4-L1/L2/L3** — Production guard against test-mode telegram-stub URL leakage: Pydantic model_validator (hard fail), startup logger.warning + Sentry breadcrumb (observability), deploy-script assertion (deferred operational).

## L-next learnings canonized

- **L-next-1 — Gate framework additions need full caller-chain coverage.** Adding G19 to `_TRANSITION_GATES` exposed a missing `selectinload` only when ci-local exercised the transition end-to-end. Unit tests with `AsyncMock` shaped sessions never hit the eager-load path. Future gate additions: a transition-path integration test is part of the sub-block, not deferred.
- **L-next-2 — Auth carriage has multiple Playwright surfaces.** The `request` fixture (Pattern 2), `browser.newContext({storageState}).request` (P2b), and `apiRequest.newContext({storageState})` (P2c) are three distinct `APIRequestContext` types. Fixing one does not fix the others. Future auth-fixture work: explicitly enumerate which surface is being touched.
- **L-next-3 — Mock-leakage coincidental pass.** G19 unit tests passed under PROMPT 44 because `MagicMock(spec=AsyncSession).get(...)` returned another `MagicMock` with attribute access that didn't blow up; under real async + eager-load mismatch, production raised `MissingGreenlet`. Mock contracts should be at least production-shaped (`MagicMock(spec=TelegramChat)` rather than bare).
- **L-next-4 — Cross-project test state pollution emerges only after logic-level fixes.** R9 (channel verification persists across browser projects) was masked by R7 (enum error fired uniformly first). Each upstream fix unmasks the next downstream surface; expect residual surfaces to multiply transiently before stabilising.
- **L-next-5 — Visual baseline regen requires authoritative seed.** R8 — 101 baselines captured a rules-gate page because seed set the denormalized cache but not the authoritative Contract row read by `RulesGuard`. Before regen: assert the seed contract layer matches the production read path, not just the surface field.
- **L-next-6 — SQLAlchemy `Mapped[StrEnum]` pitfall.** Implicit `Mapped[T] = mapped_column(nullable=True)` where `T` is a `StrEnum` infers the column type and serializes via member **name**, not value. Alembic-generated pg enum types hold member **values**. Always pair `Mapped[StrEnum]` with explicit `Enum(T, name=..., values_callable=lambda x: [m.value for m in x])`. Audit grep: `grep -rn "Mapped\[.*Method\]\|Mapped\[.*Status\]" src/db/models/`.

## References

### Source CHANGES docs consolidated (13)

| Phase | Path |
|---|---|
| B.1 | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b1-schema.md` |
| B.2 | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b2-gate-framework.md` |
| B.3 | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b3-telegram-api.md` |
| B.4 | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b4-channel-add-hookup.md` |
| B.5a | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b5a-admin-review-backend.md` |
| B.5b | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b5b-frontend.md` |
| B.6 | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b6-periodic-check.md` |
| B.7 | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b7-bot-is-test-parity.md` |
| B.8 | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b8-mock-infrastructure.md` |
| B.9.A | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b9a-vitest-infra.md` |
| B.9.B | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b9b-component-tests.md` |
| B.9.C | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b9c-playwright-unblock.md` |
| B.9.D | `reports/docs-architect/discovery/CHANGES_2026-05-14_bl107-b9d-e2e-coverage.md` |

### Design + probe references

- `BL-107_DESIGN_2026-05-14.md` @ `38dbc94` — Phase A2 Marina-locked decisions Q1-Q22
- `BL-107_PROBE_2026-05-14.md` @ `14db543` — original surface probe

### BLs closed

- **BL-107** — this workstream (Phase B.1 through B.9 + CI gate rounds)
- **BL-002** — channel-add via Telegram bot verification (Phase B.8 mock infra + Phase B.9.C unblock + Pattern 2/P2c auth)
- **O.7** — bot path `is_test` admin carve-out (Phase B.7)

### BLs newly filed

Residuals R4 / R5 / R6 / R10 plus 6 workstream surfaces (TS 7.0 migration, landing deps pinning, vite `resolve.tsconfigPaths`, `.claude/` hook persistence, gate framework integration test pattern, SQLAlchemy `Mapped[StrEnum]` audit). See `reports/docs-architect/BACKLOG.md` § BL-116 through BL-125.

🔍 Verified against: pre-merge HEAD `fe33654` | 📅 Created: 2026-05-15
