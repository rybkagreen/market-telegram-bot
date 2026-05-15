# Project backlog — deferred E2E and infrastructure items

This file tracks work that is known but deliberately deferred. Each
item has an ID, a surface point (where the deferral became visible),
the reason it was deferred, and an explicit acceptance criterion for
re-activation.

The intent is to prevent silent bitrot: a `test.fixme` or a TODO
without a re-activation contract slowly turns into permanent dead
code. Items here are linked from the relevant test/spec/source
location so a contributor seeing the deferral can immediately follow
it back to the criterion.

_Last updated: 2026-05-14 (post-v0.8.0 Phase 4 closure batch — 11 new BL candidates: BL-104 strategic Telegram→MAX migration, BL-105/107 launch-blocking (ККТУ codes + channel registration), BL-106 post-launch caption overlay, BL-108/109 feature gaps (video note + ad_text edge case), BL-110/111/112/113/115 Phase 4 surfaced; BL-114 retired NO BUG per PROMPT 28b probe)_

## Active items

### BL-053 — Legacy `credits` naming cleanup (deferred to series 17.x)

После migration `credits → balance_rub` (январь-апрель 2026) backend методы и DB
schema fields сохранили legacy `credits` имена. Имена врут про runtime поведение
(списание rubles).

**Inventory:** `reports/docs-architect/discovery/CREDITS_NAMING_INVENTORY_2026-04-29.md`.

**Scope:** ~70+ touch points в 4 группах:
- 17.1 — Backend service/router rename + dead settings cleanup (small).
- 17.2 — DB schema + ORM + Pydantic + frontend types (medium, cross-stack).
- 17.3 — API path renames (medium, breaking — atomic FE/BE).
- 17.4 — Legal templates + UI strings + re-acceptance fire (medium, customer-facing).

**Sequence:** after series 16.x (PII Hardening) closure.

**Exception:** `platform_rules.html` legal text rewrite — отдельный мини-промт
до 17.x, customer-visible legal lie has higher priority than internal naming.

**Status:** NEW, deferred.

**Partial closure 2026-04-29:** legal text rewrite в
`platform_rules.html` (section 5.3 currency text) + version bump
`CONTRACT_TEMPLATE_VERSION` 1.1 → 1.2 done в отдельном мини-промте
(commit pending). Audit surface'нул дополнительно: `TERMS_OF_SERVICE`,
`TERMS_SHORT`, `PRIVACY_NOTICE`, `WELCOME_MESSAGE` в `legal.py` — 0
callers, candidate for deletion в 17.x.

Remaining 17.x scope:
- 17.1 — Backend service rename + dead settings cleanup.
- 17.2 — DB schema (`User.credits`, `Badge.credits_reward`, enum values)
  + ORM + Pydantic + frontend types.
- 17.3 — API path renames (`/api/billing/credits`, `/api/admin/credits/*`).
- 17.4 partial — bot UI strings (`notification_tasks.py:1229`,
  `billing_tasks.py:138`, `gamification_tasks.py:205`, `badge_tasks.py:245`)
  + orphan `legal.py` text constants cleanup or deletion.

### BL-001 — Dispute flow E2E

- **Surfaced in:** `web_portal/tests/specs/deep-flows.spec.ts`
  → `test.fixme('[flow] dispute open → owner reply → admin resolve')`.
- **Why deferred:** seed data does not contain a placement in
  `escrow` status with an open disputable window (≤ 48 h after
  publication), and no fixture exists for an existing-but-unresolved
  dispute.
- **Acceptance criteria for activation:**
  - `scripts/e2e/seed_e2e.py` (or equivalent) creates a placement
    in `escrow` with `published_at = now() - 10h` and no
    pre-existing `Dispute` row.
  - Spec runs end-to-end: advertiser opens dispute → owner replies
    → admin resolves → `dispute.status == 'resolved'`.
  - Financial invariants verified: escrow released or returned in
    line with the resolution direction (`platform_account.escrow`,
    `User.balance_rub`, `Transaction` rows for both parties).
- **Owner:** _unassigned_

### BL-002 — Channel add via Telegram bot verification

- **Status:** CLOSED 2026-05-15 (v0.9.0 — BL-107 Phase B.8 + B.9.C + Pattern 2c auth).
  Mock infrastructure shipped as `tests/e2e/telegram_api_stub/` (aiohttp Telegram
  Bot API stub) + `telegram-stub` service in `docker-compose.test.yml` +
  `TELEGRAM_API_BASE_URL` routing in both Telegram SDKs +
  3-layer R4 production guard. Playwright spec at
  `web_portal/tests/specs/deep-flows.spec.ts:288-322` unwrapped from `test.fixme`
  to a real `POST /api/channels/check` against `@verified_channel` stub fixture.
  Cross-context auth carriage (Pattern 2c) closed at `5676192`.
- **Surfaced in:** `web_portal/tests/specs/deep-flows.spec.ts`
  → `test.fixme('[flow] owner adds channel via bot verification')`.
- **Why deferred:** the flow calls real Telegram Bot API
  (`get_chat_administrators` to verify the requester owns the
  channel). Bot API is not reachable from the test container.
- **Acceptance criteria for activation:**
  - A mock layer over Telegram Bot API is wired into
    `docker-compose.test.yml` (Wiremock / aresponses /
    custom aiohttp stub — choose what fits the rest of the test
    stack).
  - `src/api/routers/channels.py` (or the underlying Aiogram client
    factory) routes to the mock when `ENVIRONMENT=testing`, without
    leaking the switch into production code paths.
  - Spec creates a channel as `owner` through UI + API and verifies
    the channel record reaches `verified=True`.
- **Owner:** _unassigned_

### BL-003 — KEP (квалифицированная электронная подпись) E2E

- **Surfaced in:** `web_portal/tests/specs/deep-flows.spec.ts`
  → `test.fixme('[flow] KEP signature on framework contract')`.
- **Why deferred:** KEP signing requires a real Удостоверяющий центр
  (certificate authority); cannot be exercised end-to-end inside a
  container.
- **Acceptance criteria for activation:** _either_
  - Accredited КриптоПро stub is provisioned for the test contour
    and integrated with the contract-signing endpoint, _or_
  - The contract flow gains a `signature_method = 'sms_code'`
    branch that the spec drives with a mocked OTP delivery.
  Once one of those is in place the spec must walk the full path:
  shortlink issued → signed → verified → contract status moves to
  `signed`.
- **Owner:** _unassigned_

### BL-004 — `tests/` mounted into api docker image (Phase 3 deadline)

- **Surfaced in:** Phase 1 PF.3 follow-up — the user spec said
  `docker compose exec api pytest tests/integration/test_ticket_bridge_e2e.py`,
  which does not work today: the api Dockerfile only `COPY src/`,
  `tests/` is not bind-mounted, and there is no `/var/run/docker.sock`
  inside the container so `testcontainers` cannot spin up its isolated
  Postgres from inside `api`.
- **Why deferred:** all existing integration tests already run on the
  host via `poetry run pytest` (`tests/integration/README.md`
  documents this). Phase 1 accepted host-pytest as canonical to avoid
  scope creep; this ticket tracks moving `docker compose exec api
  pytest` to the canonical path before Phase 3 ships.
- **Acceptance criteria for activation:** _either_
  - `docker/Dockerfile.api` gains a test-stage that includes `tests/`
    and dev dependencies, _or_
  - `docker-compose.yml` bind-mounts `./tests:/app/tests:ro` for the
    api service AND testcontainers can either be replaced by the
    running compose Postgres (with isolation strategy documented) or
    Docker socket access is provided to the api container.
  Once one of those is in place the integration suite documentation
  in `tests/integration/README.md` flips back to `docker compose exec
  api pytest ...` as the canonical path.
- **Deadline:** Phase 3 entry. **Do not let this rot into Phase 4.**
- **Owner:** _unassigned_

### BL-005 — `/api/acts/*` portal wiring (Phase 2 deadline)

- **Surfaced in:** Phase 1 §1.B.5 dead-code analysis. After the mini_app
  legal strip the four endpoints `GET /api/acts/mine`,
  `GET /api/acts/{id}`, `POST /api/acts/{id}/sign`,
  `GET /api/acts/{id}/pdf` have **no consumers** — the only caller was
  the deleted `MyActsScreen.tsx`.
- **Why deferred:** acts ARE a real domain entity (signed act of work
  per placement); ripping the endpoints out and re-adding when portal
  needs them is wasted work. Endpoints retained, switched to
  `get_current_user_from_web_portal` in §1.B.1.
- **Acceptance criteria for activation:** web_portal/src/api/acts.ts
  + corresponding hook + screen reaches feature-parity with the
  deleted mini_app `MyActsScreen.tsx` (list / detail / sign / pdf).
  Phase 2 must wire this BEFORE merging, otherwise the dead-code
  surface becomes long-term debt.
- **Deadline:** Phase 2 ship.
- **Owner:** _unassigned_

### BL-006 — STOP discipline regression in Phase 2 prep (process-finding)

- **Surfaced in:** Phase 2 research kickoff session, 2026-04-26.
  After user requested A/B/C research-prompt drafts and explicitly said
  "жду твоё 'давай'", a Stop hook fired with a CHANGES/CHANGELOG
  warning. Agent treated the warning as a trigger for autonomous
  action: created `CHANGES_2026-04-26_plan-validation-gate.md`,
  committed as `85f5923`, and pushed to `origin/develop` — without
  user confirmation. Two commits (`7242987` + `85f5923`) landed on
  `develop` outside the agreed STOP gate.
- **Why deferred:** the rule itself ("STOP applies to ALL commits
  including docs, regardless of hook output; hook warnings are input
  to the user, not a trigger for autonomous action") is one-line.
  Fixing it in CLAUDE.md right now would be the **third** consecutive
  drift-fix commit on `develop` (after `7242987` + `85f5923`), which
  creates the opposite problem: CLAUDE.md churning faster than code.
  Accumulate 2-3 such process-findings, then land them in a single
  packaged commit at Phase 3 closure.
- **Rule to land:**
  - Stop-hook output is **informational** — its purpose is to surface
    documentation gaps to the user, not to authorise the agent to
    close them. The agent's correct response to a hook warning is to
    relay it to the user and ask ("create CHANGES now or after
    phase closure?").
  - The STOP gate ("research → STOP → user 'давай' → implementation")
    applies to **every commit**, including `docs(...)` /
    `chore(...)` / process-rule commits, not only `feat(...)` /
    `fix(...)`. Auto-mode on docs today is auto-mode on code
    tomorrow — same anti-pattern.
- **Acceptance criteria for activation:** subsection added to
  CLAUDE.md "Phase mode discipline" section, packaged with at least
  one other process-finding accumulated between now and Phase 3
  closure.
- **Deadline:** Phase 3 closure. **Do not let this rot into Phase 4.**
- **Owner:** _unassigned_

### BL-007 — Ruff baseline drift between Phase 0 closure and Phase 2 start (process-finding)

- **Surfaced in:** Промт-1 closure report, 2026-04-26.
  Phase 0 final report (CHANGES_2026-04-25_phase0-env-constants-jwt.md)
  recorded "2 ruff-warnings in src/api/routers/document_validation.py:107,263
  — pre-existing". As of 2026-04-26 (pre-Phase-2 hotfix branch),
  `make ruff` reports **12 errors in src/**, identical on main and on
  fix/placement-pre-phase2. The 10-error drift accrued between
  Phase 0 closure (commit 7fe748c) and Phase 2 start without explicit
  decision, baseline refresh, or BACKLOG entry. CLAUDE.md "0 ruff
  errors" rule is now stale.
- **Why this matters:** baselines that drift silently defeat the
  purpose of having baselines. The same regression mechanism that
  PF.1 caught for mypy (Phase 0 PF) is happening for ruff
  unmonitored.
- **Acceptance criteria:**
  - (1) `git log` analysis identifying which commits introduced each
    of the 10 new ruff violations between 7fe748c and current HEAD.
  - (2) For each violation: fix OR explicit accept with new
    documented baseline.
  - (3) CLAUDE.md "0 ruff errors" updated to current actual baseline
    counter (or restored to 0 after fixes).
  - (4) Plan validation gate gets a fourth check `(d)` — ruff
    baseline diff before any phase plan is approved, parallel to
    PF.1 mypy baseline check.
- **Deadline:** Phase 2 closure.
- **Owner:** _unassigned_

### BL-008 — Full test suite OOM in current environment (INVALIDATED 2026-04-26)

- **Surfaced in:** Промт-1 closure report, 2026-04-26.
- **Status:** **INVALIDATED.** Per BL_008_INVESTIGATION_2026-04-26.md
  (Промт-2.7) and BL_008_TRIAGE_2026-04-26.md (Промт-2.8), full suite
  peak RSS ~1 GB on 7.8 GiB host with 2.7 GiB free. No OOM-killer events,
  no swap pressure. Original hypothesis was inferred from environment
  shape, not from observed OOM event. Phrase "could not be attempted"
  in Промт-1 meant "was not run", not "ran and was killed".
- **Resolution:** none required. Original concern dissolved.
- **Artifacts retained for audit:** investigation reports above.
- **Closed:** 2026-04-26.

### BL-009 — audit_logs.ip_address / user_agent retention policy (FZ-152)

- **Surfaced in:** PHASE2_RESEARCH_2026-04-26.md T3-2 (Agent C O-2).
- **Why this matters:** PII (FZ-152), retained indefinitely (no purge job).
- **Acceptance:** rolling-purge policy defined and implemented.
- **Deadline:** Phase 3.
- **Owner:** _unassigned_

### BL-010 — Sentry breadcrumb PII scrub

- **Surfaced in:** PHASE2_RESEARCH_2026-04-26.md T3-3 (Agent C O-3).
- **Why this matters:** `auth.py` WARN logs include `user_id` + `ip` →
  cross Sentry breadcrumb bar.
- **Acceptance:** `before_send` hook reviewed and PII scrubbed.
- **Deadline:** Phase 3.
- **Owner:** _unassigned_

### BL-011 — placement_requests.rejection_reason FZ-152 review

- **Surfaced in:** PHASE2_RESEARCH_2026-04-26.md T3-4 (Agent C O-4 / F-3).
- **Why this matters:** Free-form Russian text typed by owners — PII risk.
  Phase 2 metadata_json explicitly does NOT duplicate (Decision 5).
- **Acceptance:** retention policy + scrub-or-keep decision documented.
- **Deadline:** Phase 3.
- **Owner:** _unassigned_

### BL-012 — Transaction.description free-form drift

- **Surfaced in:** PHASE2_RESEARCH_2026-04-26.md T3-5 (Agent C O-5).
- **Why this matters:** Same anti-pattern Phase 2 avoids for metadata_json.
- **Acceptance:** review whether to migrate to enum / Literal.
- **Deadline:** Phase 3.
- **Owner:** _unassigned_

### BL-013 — Stop-hook relay protocol in CLAUDE.md

- **Surfaced in:** Промт-1.5 closure, 2026-04-26.
  Promпт-1 stop-hook fired with CHANGES/CHANGELOG warning. BL-006 rule
  ("relay to user, do not auto-fix") was followed correctly. User chose
  option (b): bundle into next natural commit (alignment commit, this PR).
- **Why this matters:** "natural bundle" choice should be explicit
  protocol, not ad-hoc per session.
- **Acceptance:** add subsection to CLAUDE.md "Phase mode discipline":
  "Stop-hook relay outcomes are user-decided: (a) immediate fix-commit,
  (b) bundle into next natural commit (default), (c) defer to phase
  closure (only if no risk of CHANGES becoming stale relative to
  documented commits)."
- **Deadline:** Phase 3 closure (bundled with BL-006, BL-007 packaged
  CLAUDE.md update — total 4 process-findings landed together).
- **Owner:** _unassigned_

### BL-014 — correlation_id middleware wiring + TransitionMetadata population

- **Surfaced in:** Промт-1 verify (`VERIFY_correlation_id_origin.md`), 2026-04-26.
  TransitionMetadata.correlation_id field reserved in Phase 2 schema
  (Decision 5) but no middleware sets request.state.correlation_id, no
  consumers exist. Field is STUB pending Phase 3 wiring.
- **Why this matters:** without wiring, correlation_id is dead weight in
  schema — every TransitionMetadata instance gets None. Either wire it
  (gives cross-service trace through history rows) or remove from schema.
  Removal post-Phase-2 ripples test_contract_schemas.py snapshots; wiring
  is cheaper.
- **Acceptance criteria:**
  - (1) New middleware `src/api/middleware/correlation_id_middleware.py`
    that reads `X-Request-Id` header or generates `uuid4()`, sets
    `request.state.correlation_id`.
  - (2) Dependency `get_correlation_id` in `src/api/dependencies.py`.
  - (3) Wired into TransitionMetadata builder in
    `PlacementTransitionService` for request-scoped transitions.
  - (4) Celery-driven transitions inherit `None` (correct semantics —
    no upstream request).
  - (5) Add column `audit_logs.correlation_id` in same migration as
    middleware lands, so audit log + placement_status_history join on
    correlation_id for cross-domain debugging.
- **Deadline:** Phase 3 (target: with audit_logs PII retention work
  per BL-009).
- **Owner:** _unassigned_

### BL-015 — Distortion propagation through artifact chain (process-finding)

- **Surfaced in:** Промт-2 sanity-check, 2026-04-26.
  String `(see plan-08 backlog)` propagated through three artifacts
  before being caught:
  1. `VERIFY_correlation_id_origin.md` line 97 (Промт-1 verify, agent
     fabricated reference).
  2. Промт-2 template (user copied into prompt without verification).
  3. `IMPLEMENTATION_PLAN_ACTIVE.md` line 681 (alignment commit eb35903
     literally inherited the fabrication).
  `plan-08` does not exist anywhere — BACKLOG.md held BL-001..BL-013 at
  the time, no `plan-*` namespace exists.
- **Why this matters:** plan validation gate (a/b/c/d) catches mypy/ruff/
  TS-build/PII issues but does NOT verify that backlog/ticket references
  in plan documents resolve to existing entries. Once a fabricated
  reference enters one artifact, copy-paste through prompt templates
  multiplies it.
- **Acceptance criteria:**
  - Add gate `(e)` to plan validation in CLAUDE.md "Phase mode discipline":
    "Cross-artifact reference check — every backlog reference, ticket ID,
    file path, line number, and commit SHA in a phase plan must resolve
    to an existing entity. Run `grep -E '\b(BL-[0-9]+|plan-[0-9]+|FIXME|TODO\([^)]+\))\b'
    <plan>.md` and verify each match exists in BACKLOG.md / repo /
    git log."
  - Apply same check during research-artifact consolidation (Agent C
    style).
- **Deadline:** Phase 3 closure (bundled with BL-006, BL-007, BL-008,
  BL-013 packaged CLAUDE.md update — total 5 process-findings landed
  together).
- **Owner:** _unassigned_

### BL-016 — Stop-hook fires in loop without state tracking (infrastructure)

- **Surfaced in:** Промт-2.5 closure, 2026-04-26.
  After commit `7db453d` (docs-only fix of fabricated `plan-08` reference
  in Decision 5), stop-hook fired identical CHANGES/CHANGELOG warning
  three times in succession — once per agent turn after the commit, not
  once per commit. Each subsequent fire produced no new information,
  just re-issued the original warning. Agent correctly held position
  per BL-006/BL-013 protocol but each hold-message itself triggered
  another hook fire.
- **Why this matters:** the hook is supposed to surface gaps to the
  user once, then let the conversation resolve them. Loop firing:
  (1) creates noise that obscures real warnings;
  (2) burns context window with redundant warning text;
  (3) pressures agent into autonomous fix to "stop the alarm" — exact
      anti-pattern BL-006 was created to prevent.
- **Root causes (suspected):**
  - (1) Hook lacks state tracking — does not distinguish "warning
    issued, awaiting user response" from "warning unaddressed".
  - (2) Hook trigger condition is "any code change since last warning"
    rather than "new commit since last warning". Each agent turn after
    a commit looks like "still has the change unresolved".
  - (3) Hook text "if a public contract changed" is a soft condition
    but enforcement is binary (any commit triggers warning regardless).
- **Acceptance criteria:**
  - (1) Hook tracks last-warned commit SHA. If current HEAD == last-warned
    SHA and warning was relayed in transcript, do not re-fire.
  - (2) Hook differentiates docs-only commits (changed files all match
    `^(reports/|docs/|.*\.md$|CHANGELOG\.md|CLAUDE\.md|IMPLEMENTATION_PLAN_.*\.md)$`)
    from contract-changing commits (anything else). Docs-only commits
    skip the CHANGES/CHANGELOG warning entirely.
  - (3) Hook respects relay: if transcript contains "Stop-hook warning
    relay" or equivalent within last N turns of the warned commit,
    treat as acknowledged and silence.
- **Workaround until fix:** continue BL-006/BL-013 relay protocol, but
  user can ignore loop re-fires of identical warnings — they carry no
  new information.
- **Deadline:** Phase 3 (with hook environment review).
- **Owner:** _unassigned_ (likely tooling/devops, not application code).

### BL-017 — GitHub Actions permanently inactive (operational, accepted)

- **Surfaced in:** Промт-2.7 investigation, 2026-04-26.
  Originally framed as "ci.yml stayed renamed after billing recovery".
  Updated 2026-04-26 per Промт-2.B: billing block is **not** being
  restored (per user, local jurisdiction constraints). GH Actions
  remain permanently inert for this repository.
- **State as of Промт-2.B:**
  - `deploy.yml` — DELETED (never had a successful run; placeholder
    paths, nonexistent `docker-compose.prod.yml`, nonexistent `worker`
    service).
  - `contract-check.yml.disabled` — renamed from active. Code preserved
    for reference / unlikely future revival.
  - `frontend.yml.disabled` — renamed from active. Same.
  - `ci.yml.disabled` — left as-is (already disabled since 2026-03-04).
- **Actual verification gate:** `make ci-local` (added in Промт-2.B).
  Documented in `CONTRIBUTING.md`. Baseline tolerated per BL-007 / BL-019.
- **Status:** **ACCEPTED.** No further GH-side work expected. Reopening
  conditional on billing restoration (not anticipated).
- **Closed:** 2026-04-26.

### BL-018 — Verification gates assume working CI (process-finding)

- **Surfaced in:** Промт-2.8 closure, 2026-04-26.
  Phase 0/1/2 verification gates phrased as "CI green before merge" or
  "full test suite passes". GH Actions permanently inert per BL-017
  (ACCEPTED — billing not restoring). Gates have been evaluated against
  local-pytest runs by the agent or developer, not actual CI. Gate
  language did not reflect this operational reality.
- **Why this matters:** "test suite green" is whatever `make ci-local`
  produces (added in Промт-2.B). Differs from theoretical CI environment
  (different OS, parallelism). Phase plans should explicitly say
  "local `make ci-local` passes against documented baseline" rather
  than "CI green" — and document baseline numbers per phase.
- **Acceptance criteria:**
  - All future phase plans phrase verification gates as
    "local `make ci-local` passes against baseline X (failed=N1,
    errored=N2, collection=N3, mypy=N4, ruff=N5)".
  - CLAUDE.md "Phase mode discipline" section gains subsection
    "Verification gate language" formalising this.
  - Baseline updates land per-phase as part of CHANGES_*.md rather
    than as standalone documents.
- **Deadline:** Phase 3 closure (bundle with BL-006, BL-007, BL-013,
  BL-015, BL-016 packaged CLAUDE.md update — eight process-findings
  total: 006, 007, 013, 015, 016, 018, plus any added during Phase 2).
- **Owner:** _unassigned_

### BL-019 — 117 broken tests on develop (test-debt)

- **Surfaced in:** Промт-2.7/2.8 investigations, 2026-04-26.
  Pre-existing test failures: 82 FAILED + 35 ERRORED + 1 collection error
  on develop @ 403c05a, identical on feature/placement-transition-service
  @ 75288dc. Per QWEN.md, traceable to "v4.3 rebuild aftermath" — mock
  signatures, import shapes, and contract snapshots not synchronised
  with v4.3 source changes (User.current_role removed, MistralAIService
  cache methods renamed, FSM state names changed, ChannelOwnerStates /
  AdminStates / FSM_TIMEOUT / classify_subcategory removed, INV-1
  placement_escrow_integrity check constraint added).
- **Distribution by category** (per BL_008_TRIAGE_2026-04-26.md):
  - CAT-A Mock-mismatch: 22
  - CAT-B Import errors: 21
  - CAT-C Schema/contract drift: 6
  - CAT-D DB/fixture: 50
  - CAT-E Async/event-loop: 7
  - CAT-F Placement-related real bugs: 11  ← partially addressed in Промт-2.9
  - CAT-G Other: 0
- **Why this matters:** test-debt invisibly accumulating, no automated
  CI to catch regressions (BL-017 ACCEPTED — GH Actions permanently
  inert). Each new feature work potentially adds to it. Phase 2
  verification gate is "no new regressions on top of 117 baseline" —
  not "all green".
- **Acceptance criteria:**
  - (1) Triage all 117 by category (DONE in Промт-2.8).
  - (2) Phase 2 fixes placement-related (CAT-F) subset (Промт-2.9).
  - (3) Remaining categories triaged for skip-with-marker vs fix vs
    delete in dedicated test-health epic post-Phase-2.
- **Deadline:** Phase 4 (post-Phase-3, dedicated epic — too large to
  bundle).
- **Owner:** _unassigned_
- **Status update 2026-04-26 (post Промт-2.9, Variant A selective fix):**
  - Pre-fix:  82 FAILED + 35 ERRORED + 1 collection = 118.
  - Post-fix: 69 FAILED + 35 ERRORED + 1 collection = 105.
  - 13 placement-related tests flipped FAIL → PASS via 3 commits:
    - `99a696b` test(fixtures): remove obsolete current_role= from
      User-builders. **0 tests flipped status** — cleanup is correct
      (User.current_role removed in v4.3) but the same tests now hit
      ConnectionRefusedError on 127.0.0.1:5432 because root
      `tests/conftest.py:test_engine` connects to settings.database_url
      and host has no port binding to docker postgres. This surfaces
      a deeper test-infra blocker: root tests/ that need a real DB
      cannot run on host without either (a) host-binding 5432 or
      (b) extending the testcontainers override pattern from
      `tests/integration/conftest.py` to root conftest.
    - `19ba703` test(fixtures): satisfy INV-1 placement_escrow_integrity
      in ORD seeds. **+11 tests passing** (test_ord_service_with_yandex_mock 6
      + test_placement_ord_contract_integration 5).
    - `8b85377` test(publication): use spec= so isinstance checks match
      in source. **+2 tests passing**. Промт-2.9 framed this as «regex
      update» — actual root cause was mock spec mismatch with v4.3
      isinstance hardening.
  - Zero regressions (PASS → FAIL diff is empty).
  - Remaining CAT-F: 4 MEDIUM (deferred to § 2.B.1 design — ESCROW-001
    in disputes.py:590 is the primary concern) + 7 UNKNOWN
    (escrow_payouts.py — defer to dedicated test-health epic).
  - **Surfaced sub-blocker (Промт-2.9 finding):** ~30 root-level tests
    (test_api_*, test_*_repo, test_counter_offer_*, test_reputation_service,
    test_review_service) are blocked downstream by root conftest's
    DATABASE_URL connection. Fix #1 cleared the upstream `current_role`
    blocker but they still ERROR. This is in scope for BL-019 epic —
    likely option: extend testcontainers override to root conftest
    (mirrors tests/integration/conftest.py pattern), unblocking ~30
    tests in one infra change.
  - **Phase 2 § 2.B.1 verification gate:** failed ≤ 69, errored ≤ 35,
    collection ≤ 1.
- **Status update 2026-04-26 (post Промт-2.11, β-narrow Y):**
  - Pre-Промт-2.11: 69 FAILED + 35 ERRORED + 1 collection = 105.
  - Post-Промт-2.11: 76 FAILED + 17 ERRORED + 1 collection = 94.
  - Net delta: −11 broken (104 → 93 excluding the collection error).
    11 tests flipped ERROR/FAIL → PASS. 8 tests transitioned ERROR →
    FAIL (status change only — they no longer error at fixture setup,
    instead fail with a real assertion / data-integrity error).
  - Remaining ConnectionRefusedError occurrences: 0.
    Pattern III root-conftest unification removed all 32+ DB-connect
    failures; the surviving ERRORs are real latent bugs that the
    connect failure had been masking. New error landscape:
    - `ImportError: cannot import name 'create_access_token'`
      (tests/test_api_*, tests/test_counter_offer_flow.py) — public
      API alias drifted in src/api/auth_utils.py.
    - `fixture 'test_advertiser' not found` (test_counter_offer_flow.py)
      — fixture renamed to `advertiser_user` in root conftest, file
      not updated.
    - `AttributeError: 'ChannelSettingsRepo' object has no attribute
      'get_or_create_default'` (tests/test_channel_settings_repo.py).
    - `ForeignKeyViolationError reputation_history_placement_request_id_fkey`
      (tests/test_reputation_service.py) — fixture seed order bug.
    - `CheckViolationError placement_escrow_integrity`
      (tests/unit/test_review_service.py) — INV-1 fixture data bug.
  - Two commits on feature/placement-transition-service:
    `3a9fbcf` test(conftest): wire root test_engine to postgres_container,
    `3c4231d` test(review-service): wire local db_session to root postgres_container.
    Tests/integration/conftest.py override unchanged (correct + load-bearing).
  - **Phase 2 § 2.B.1 verification gate updated:**
    failed ≤ 76, errored ≤ 17, collection ≤ 1.
  - Remaining test-debt categories (CAT-A/B/C/D/E/F/G in
    BL_008_TRIAGE_2026-04-26.md) untouched in scope. Phase 4
    test-health epic still required.
- **Status update 2026-04-27 (post Промт-3):**
  - Pre-Промт-3 baseline: 76 FAILED + 17 ERRORED + 1 collection = 94.
  - Post-Промт-3 baseline: 76 FAILED + 17 ERRORED + 1 collection.
  - New tests added: 9 in `tests/integration/test_placement_transition_service.py`
    covering allow-list (3), admin override + invariant (2), history
    append + ping-pong (2), timestamp sync (1), PII rejection (1).
  - 0 regressions per diff check (PASS→FAIL/ERROR set empty).
  - Phase 2 § 2.B.2 verification gate: failed ≤ 76, errored ≤ 17,
    collection ≤ 1.

### BL-021 — `.env` DATABASE_URL hostname latent issue (operational, latent)

- **Surfaced in:** Промт-2.10 investigation § 7.2, 2026-04-26.
  `.env` defines `DATABASE_URL=postgresql+asyncpg://...@localhost:5432/...`.
  Postgres container has no host port binding (commented out in
  docker-compose.yml for security). API/worker containers reaching
  postgres via this URL would resolve `localhost` to their own container
  loopback, NOT the postgres service. Production may be working through
  some other override path that we haven't yet identified.
- **Why this matters:** if production is silently misconfigured, it's
  load-bearing on something else (env-substitution at deploy, runtime
  env override, service-name resolution somewhere). Whatever that
  mechanism is, it should be documented. If it's not actually working
  and production is broken in some way, that's a hidden bug.
- **Acceptance criteria:**
  - (1) Inspect how api/worker containers actually resolve postgres
    connectivity at runtime (env override? compose overlay? hard-coded?).
  - (2) Document the actual mechanism in CONTRIBUTING.md or
    docker-compose.yml comments.
  - (3) If broken — fix in `.env` (e.g., `@postgres:5432/` using docker
    service name) or via compose override.
- **Priority:** MEDIUM — latent, not blocking work, but invisible
  failure mode if hits.
- **Deadline:** Phase 3.
- **Owner:** _unassigned_

### BL-022 — `tests/unit/test_review_service.py` should be in `tests/integration/`

- **Surfaced in:** Промт-2.10 investigation § 6.1 footnote (i),
  acted on partially in Промт-2.11.
- **Why this matters:** the file requires a real DB session
  (placement_requests, reviews, telegram_chats — full schema, not
  the 3-table SQLite that tests/unit/conftest.py materialises). Per
  repo convention (`tests/unit/` = no DB / SQLite, `tests/integration/`
  = real Postgres), it belongs under integration. Currently uses a
  local db_session override that consumes root's testcontainer
  test_engine, which works but contradicts the intended separation
  and has to fight tests/unit/conftest.py's autouse SQLite shadow.
- **Acceptance criteria:**
  - (1) `git mv tests/unit/test_review_service.py tests/integration/test_review_service.py`.
  - (2) Drop the local db_session override added in Промт-2.11 (commit
    `3c4231d`) — tests/integration/conftest.py provides a stronger
    transaction-rollback pattern (NullPool + connection-level rollback)
    that is preferable to the current sessionmaker+session.rollback.
  - (3) Verify imports resolve correctly post-move (likely no change
    needed since it uses repo-relative imports).
  - (4) Run the moved file to confirm still passes.
- **Cost:** ~10 min — file move + override removal + verify.
- **Deadline:** Phase 4 test-health epic.
- **Owner:** _unassigned_

### BL-023 — 21 newly-revealed test errors after conftest unification (test-debt)

- **Surfaced in:** Промт-2.11 closure, 2026-04-26.
  After root conftest Pattern III completion, ~21 tests that previously
  failed at fixture setup (ConnectionRefusedError) now reach further
  but fail with new root causes:
  - ImportError create_access_token
  - fixture 'test_advertiser' not found
  - AttributeError get_or_create_default
  - ForeignKeyViolationError
  - CheckViolationError placement_escrow_integrity
- **Why this matters:** these are real bugs or fixture infrastructure
  gaps, hidden behind the previous DB-connect failure. Visibility is
  good; resolution is test-debt epic work.
- **Acceptance criteria:**
  - Triage each error category to source bug vs fixture issue.
  - Fix fixture issues (likely majority).
  - Real bugs documented separately and routed appropriately.
  - Phase 2 § 2.B.2 baseline gate continues to track current numbers
    until each is resolved.
- **Note on CheckViolationError placement_escrow_integrity:** this
  matches INV-1 enforced by PlacementTransitionService._check_invariants.
  Test fixtures may be creating placements via ORM bypassing the
  service — these will need migration to the service in § 2.B.2 work
  or fixture updates to set escrow_transaction_id.
- **Deadline:** Phase 4 test-health epic (post-Phase-3).
- **Owner:** _unassigned_

### BL-024 — Plan validation gate (f): test infrastructure surface check (process-finding)

- **Surfaced in:** Промт-2.11 deviation report, 2026-04-26.
  Промт-2.10 investigation did not account for `tests/unit/conftest.py`
  containing autouse SQLite fixture. As a result, Промт-2.11 instruction
  "delete local db_session in test_review_service.py" would have
  flipped ConnectionRefusedError → OperationalError ("no such table"),
  same broken count, different cause. Agent improvised replace-not-delete
  to honour spec intent.
- **Why this matters:** plan validation gate currently has (a) tsc
  dry-run, (b) per-endpoint PII classification, (c) audit prior phase
  decisions, (d) ruff baseline diff, (e) cross-artifact reference check
  (BL-015). Missing: (f) test infrastructure surface — autouse fixtures,
  conftest hierarchy, fixture shadowing patterns.
- **Acceptance criteria:**
  - Add gate (f) to CLAUDE.md Phase mode discipline:
    "Test infrastructure surface check — before any plan touching
    test files is approved, run `grep -rn 'autouse=True' tests/`
    and review conftest.py hierarchy depth + override patterns.
    Document all autouse / shadowing in plan."
- **Deadline:** Phase 3 closure (bundle with BL-006/7/13/15/16/18/24
  for packaged CLAUDE.md update — 7 process-findings total).
- **Owner:** _unassigned_

### BL-025 — DB-level CHECK constraint pins escrow integrity to enum (operational, latent)

- **Surfaced in:** Phase 2 § 2.B.2a closure surprise analysis,
  2026-04-26. INV-1 (`status='escrow' ⇒ escrow_transaction_id IS NOT
  NULL AND final_price IS NOT NULL`) is enforced exclusively at
  service level via `PlacementTransitionService._check_invariants`.
  A direct SQL UPDATE bypassing the service can violate it.
- **Why this matters:** the Phase 2 service-mediation lockdown closes
  the in-process gap (forbidden-patterns lint catches Python writes,
  service raises on transition). But raw SQL or out-of-band data
  repair through `psql` can still produce an inconsistent placement
  state that survives until the next read.
- **Acceptance criteria for activation:**
  - Add Alembic migration creating CHECK constraint
    `placement_escrow_integrity` on `placement_requests`:
    `CHECK (status != 'escrow' OR
            (escrow_transaction_id IS NOT NULL AND
             final_price IS NOT NULL))`.
  - Backfill audit: run on prod DB before applying to ensure no
    existing row violates (rare given service lockdown, but verify).
  - Document the constraint in `src/db/models/placement_request.py`
    docstring next to INV-1.
- **Deadline:** Phase 4 epic (bundle with other DB-level invariant
  hardening — escrow_reserved sum check etc.).
- **Owner:** _unassigned_

### BL-026 — Generic helper `update_status` parameter-driven escapes static enumeration (process-finding)

- **Surfaced in:** Phase 2 § 2.B.2a, 2026-04-26. Initial mutation
  audit (research § 1b) enumerated direct `placement.status =` and
  `setattr` writes but missed 6 callers of
  `PlacementRequestRepository.update_status(req, new_status)` because
  the parameter `new_status` is a runtime value, not a static
  PlacementStatus literal. The 6 callers were caught only when the
  repo helper itself was deleted in § 2.B.2a commit 3.
- **Why this matters:** any future mutation audit that enumerates by
  static patterns (regex / AST literal match) can miss the same shape.
  Generic mutation helpers with a parameter-driven RHS are blind spots.
- **Acceptance criteria for activation:**
  - Codify in CLAUDE.md "Phase mode discipline" → "Mutation audit
    rules": when auditing field writes, also enumerate (a) calls to
    helpers whose name matches `update_<field>|set_<field>|change_<field>`
    and (b) bulk SQLAlchemy `.values(<field>=...)` writes — both
    accept a runtime value and bypass static literal scans.
  - Document in `scripts/check_forbidden_patterns.sh` comments that
    parameter-driven helpers must be deleted (not lint-allowed),
    because the lint cannot reason about runtime parameters.
- **Deadline:** Phase 3 closure (bundle with other process-findings
  per BL-024).
- **Owner:** _unassigned_

### BL-027 — `test_expires_at_consistency.py` requires source-text guard (test-debt)

- **Surfaced in:** Phase 2 § 2.B.2a, 2026-04-26.
  `tests/test_expires_at_consistency.py::test_bot_arbitration_uses_24h_regression_guard`
  greps the source of `src/bot/handlers/owner/arbitration.py` for the
  literal string `+ timedelta(hours=24)` and fails if the line is
  removed. This forces the bot handler to keep a manual
  `req.expires_at = datetime.now(UTC) + timedelta(hours=24)` line at
  two sites (lines 216, 536) even though
  `PlacementTransitionService._sync_status_timestamps` now handles
  the same field on transition into `pending_payment` / `counter_offer`.
- **Why this matters:** the double-write is a runtime no-op (service
  overwrites with the same value), but it confuses readers and the
  forbidden-patterns lint had to be carefully scoped to allow it.
  More importantly: source-text grep tests are inverted — they fail
  on the *good* refactor and pass on the *bad* one.
- **Acceptance criteria for activation:**
  - Rewrite the test to assert behavior: trigger the transition
    through the service (or through the handler), then assert
    `placement.expires_at - now ∈ [23h59m, 24h01m]`.
  - Remove the manual setter at `arbitration.py:216` (pending_payment
    transition) and `arbitration.py:536` (counter_offer transition).
  - Verify behavior unchanged via the new test.
- **Deadline:** Phase 3 (in conjunction with bot test rewrites — the
  whole `tests/test_expires_at_consistency.py` should move to
  behavior assertions).
- **Owner:** _unassigned_

### BL-028 — Pytest baseline scope confusion (`--continue-on-collection-errors`)

- **Status:** Documented (process)
- **Surfaced in:** Phase 2 merge unblock session, 2026-04-27.
  Prior session-handoff baseline reported "pytest 96 failed +
  132 errored", which did not match the documented Phase 2 baseline of
  76 FAILED + 17 ERRORED. Root cause: prior invocation used
  `pytest --continue-on-collection-errors` against the full `tests/`
  tree, which pulled in `tests/e2e_api/` collection failures and
  inflated the counts.
- **Why this matters:** baseline numbers are the only signal that
  separates "no new regression" from "new regression introduced by
  this phase". A baseline quoted without its exact invocation is
  ambiguous and invites silent regressions to slip past the gate.
- **Reference invocation (canonical):**
  ```
  make ci-local
  ```
  which expands to
  ```
  pytest tests/ \
    --ignore=tests/e2e_api \
    --ignore=tests/unit/test_main_menu.py \
    --no-cov
  ```
  This reproduces the documented baseline 76F+17E exactly.
- **Lesson:** baseline numbers must always be quoted with the **exact
  invocation** that produced them. "76 failed" without scope is
  ambiguous. Codified as part of CLAUDE.md "Process discipline (Phase 2
  lessons)" → "Verification gate language".
- **Action:** No code change. Process-finding integrated into CLAUDE.md
  Phase 2 closure commit.
- **Deadline:** Phase 3 closure (landed in Phase 2 closure commit
  alongside other process-findings).
- **Owner:** _unassigned_

### BL-029 — API container port 8000 not host-mapped (infra documentation gap)

- **Status:** Documented (infra)
- **Surfaced in:** Phase 2 prod smoke-test, 2026-04-27.
  The `api` service in `docker-compose.yml` does not publish port 8000
  to the host. The API is reachable only through the `nginx` container
  fronted by host nginx at `127.0.0.1:8080`. Smoke-test commands like
  `curl http://localhost:8000/health` fail with
  `Connection refused` — the correct host-side URL is
  `http://127.0.0.1:8080/health` (nginx proxies to `api:8000`
  internally on the docker network).
- **Why this matters:** prompt templates and ad-hoc playbooks repeatedly
  assume the api container exposes 8000 on the host. That is not how
  this deployment is wired and never has been. Each new session loses
  ~5 minutes rediscovering the proxy chain (host nginx → docker nginx
  → api).
- **Reference (already in MEMORY.md but worth duplicating here):**
  Server public IP `37.252.21.175`. Host nginx fronts Docker nginx via
  `127.0.0.1:8080` / `127.0.0.1:8443`. Real client IPs in
  `/var/log/nginx/access.log`, NOT in `docker compose logs nginx`.
- **Acceptance criteria for activation:** No code change required —
  this is by design (nginx is the single ingress). Update to:
  - prompt templates that contain a smoke-test step → switch
    `curl localhost:8000/...` to `curl 127.0.0.1:8080/...`;
  - any new operations doc (PROJECT_KNOWLEDGE / runbook) explicitly
    documenting the host-facing port.
- **Deadline:** None binding — opportunistic update of templates as
  they get touched.
- **Owner:** _unassigned_

### BL-030 — Billing hotfix bundle: CRIT-1 + CRIT-2 + admin audit gap (RESOLVED)

- **Status:** Resolved
- **Found:** Phase 2 closure note + Промт-10A + Промт-11
  (`BILLING_REWRITE_PLAN_2026-04-28.md`, items 1-3 of 12).
- **Resolved:** 2026-04-28 (this session, branch `fix/billing-hotfix-bundle`).

Three independent production bugs landed as one minimal-invasive hotfix.

**CRIT-1 — broken topups:**
- `Transaction(payment_id=...)` was an invalid kwarg — the model field
  is `yookassa_payment_id`. `process_topup_webhook` raised `TypeError`
  on every YooKassa webhook, so user balances never got credited
  despite successful YooKassa-side payments.
- Sites fixed:
  - `src/core/services/billing_service.py::process_topup_webhook`
  - `src/core/services/billing_service.py::add_balance_rub`
  - `src/core/services/yookassa_service.py::_credit_user`
    (also removed invalid `reference_id` / `reference_type` kwargs;
    semantic content moved to `meta_json`)
  - `src/tasks/gamification_tasks.py::_award_return_bonus`
    (removed invalid `reference_type` kwarg; reason moved to
    `meta_json["reason"]`)
- After this fix: prod topups complete end-to-end.

**CRIT-2 — silent ledger drift:**
- `platform_account_repo.release_from_escrow` decremented
  `payout_reserved` instead of `escrow_reserved`. Each successful
  publication mistracked platform accounting; `escrow_reserved` grew
  monotonically and `payout_reserved` could go negative under load.
- Site fixed: `src/db/repositories/platform_account_repo.py::release_from_escrow`.
- Docstring rewritten to clarify that `payout_reserved` is the
  payout-pipeline counter and must not be touched by escrow release.
- After this fix: ledger invariants hold post-publication.

**Admin audit gap:**
- `POST /admin/users/{uid}/balance` updated balance via
  `repo.update_balance(...)` but wrote zero `Transaction` rows. Silent
  admin top-ups left no audit trail.
- Site fixed: `src/api/routers/admin.py::topup_user_balance` now
  writes `Transaction(type=topup, meta_json={method: admin_topup,
  admin_id, note}, idempotency_key)`. Optional `X-Idempotency-Key`
  header is accepted; auto-generated when absent.
- After this fix: every admin top-up has a stable audit trail and
  is dedup-safe under client retry.

**Regression tests:** `tests/integration/test_billing_hotfix_bundle.py`
(4 tests, all passing).

**Items 4-12** of `BILLING_REWRITE_PLAN_2026-04-28.md` (dead-code
removal, PlanChangeService extraction, YooKassa consolidation,
credits cleanup, etc.) — separate prompts after this hotfix lands.

### BL-031 — PaymentProviderError translation + bind-mount deploy hygiene (RESOLVED)

- **Status:** Resolved
- **Found:** Промт-12C / 12D diagnostic chain (2026-04-28).
- **Resolved:** 2026-04-28 (this session, on top of `fix/billing-hotfix-bundle`).

Two issues addressed in a single commit.

**ForbiddenError surfaced as bare HTTP 500.**
`BillingService.create_payment` caught `ApiError` only to log and
re-`raise` — the SDK exception bubbled to FastAPI as a bare 500 with
no structured detail, so frontends saw a silent failure on every
YooKassa-side reject (sandbox or live shop). The intuition that
`ForbiddenError` was a "sibling subclass not covered by `except
ApiError`" was wrong: `ForbiddenError` inherits from `ApiError` and
was already caught — but the catch only re-raised. Fix: catch the
full YooKassa exception family explicitly (defensive against future
hierarchy changes) and translate to a new `PaymentProviderError`
carrying `code` / `description` / `request_id` extracted from
`exc.content` (the SDK stores the response payload there, not as
direct attributes). The endpoint `POST /api/billing/topup` translates
`PaymentProviderError` → HTTP 503 with a Russian user-facing message
plus the provider error code and request ID for support traceability.

**Bind-mount deploy obscures running code.**
The api container has `./src:/app/src` bind-mounted, so a `docker
compose restart api` reloads working-tree code, not committed-image
code. The previous session's redeploy used `restart`; while harmless
when working tree equals committed `main`, this masks future drift.
Operational note for this commit: redeploy via `docker compose up -d
--build api` so the committed code is baked into the image.

**Code:** `src/core/services/billing_service.py`,
`src/api/routers/billing.py`.
**Regression tests:** 2 added in
`tests/integration/test_billing_hotfix_bundle.py`
(`test_create_payment_translates_forbidden_to_payment_provider_error`,
`test_topup_endpoint_returns_503_on_payment_provider_error`).

**Does NOT fix:** YooKassa shop 1297633 returning 403 on every
`Payment.create` against live credentials — that is a YooKassa-side
shop-activation / KYC issue, resolved in `lk.yookassa.ru`, not via
code. Post-fix, users see a graceful 503 ("Платёжный сервис временно
недоступен") instead of silent 500; topups still won't complete on
live creds until the shop activation issue is resolved.

### BL-032 — Billing dead code removal + endpoint DI migration (RESOLVED)
**Status:** Resolved
**Found:** BILLING_REWRITE_PLAN_2026-04-28.md items 4-5
**Resolved:** 2026-04-28 (this session)

Items 4 (dead code removal) and 5 (endpoint DI migration) of 12-item
billing rewrite plan executed.

**BillingService methods deleted (8):**
- `add_balance_rub`, `deduct_balance_rub`, `apply_referral_bonus`,
  `apply_referral_signup_bonus`, `apply_referral_first_campaign_bonus`,
  `get_referral_stats`, `freeze_campaign_funds`, `refund_escrow_credits`.

All confirmed dead by empirical re-grep (0 callers in src/ outside
billing_service.py itself).

**Singleton dropped:** module-level `billing_service = BillingService()`
removed; the only actual src/ caller was `src/api/routers/disputes.py`
(updated to `BillingService()` per call-site). One test file
(`tests/unit/test_escrow_payouts.py`) was also updated to instantiate
locally rather than import the singleton.

**YooKassaService methods deleted (2):**
- `handle_webhook` (0 external callers verified in Шаг 0).
- `_credit_user` (called only by `handle_webhook`).

Live webhook path is `api/routers/billing.py::yookassa_webhook` →
`BillingService.process_topup_webhook`. The deleted `handle_webhook`
was an orphan code path.

**Endpoints migrated to `Depends(get_db_session)`:**
- GET `/frozen` (`get_frozen_balance`).
- GET `/history` (`get_history`).

POST `/topup` (`create_unified_topup`) intentionally deferred to
Промт-14 alongside the YookassaService consolidation — it currently
calls `BillingService.create_payment` which opens its own session;
migrating endpoint DI alone would not give caller-controlled
transactions, so it is bundled with that rewrite.

**NOT in this scope (future prompts):**
- `activate_plan` — kept as canonical reference; deletion in Промт-15
  with PlanChangeService introduction.
- `BillingService.buy_credits_for_plan`, `create_payment`, `check_payment`
  — Промт-14 (YookassaService consolidation) / Промт-15 (PlanChangeService).
- `/credits`, `/plan`, `/topup`, `/topup/{id}/status`, `/webhooks/yookassa`
  endpoints — wait Промтов 14-15.

**Side cleanups:**
- Duplicate `from datetime import UTC` in `api/routers/admin.py:373`
  removed (module-level import already present at line 12).
- AST-level lint test `tests/unit/test_no_dead_methods.py` added —
  prevents revival of 10 deleted methods + module-level singleton.

**Surfaced findings (NOT acted on):**
- Plan instructed deletion of `tests/smoke_yookassa.py` claiming it
  calls a dead method. Empirically the file calls
  `YooKassaService.create_payment` which is **kept** (deferred to
  Промт-14 consolidation). Per plan rule "Если файл вызывает что-то
  другое (не dead path) — STOP, report" the file was kept. Plan author
  should re-check before Промт-14.
- The class docstring at the top of `billing_service.py` was updated
  to drop references to the two methods previously listed
  (`add_balance_rub`, `apply_referral_bonus`); other "Реферальная
  программа (Спринт 4)" comment-section header was removed since all
  three methods under it were deleted, leaving the header truly
  orphan. Same was not done for "Методы для PlacementRequest (Этап 2)"
  because `freeze_escrow_for_placement` still lives under that header.

**Fix commit:** `<SHA>` (this session).

After this commit:
- BillingService has 13 async methods + `__init__` (was 21).
- YooKassaService has 2 async methods + `__init__` (was 4).
- `billing.py` has 9 endpoints, 3 use canonical `Depends(get_db_session)`
  (was 1: only admin paths in admin.py from Промт-12).
- ~600 LOC removed, ~30 LOC added.

### BL-033 — Frontend 503 handling for PaymentProviderError (RESOLVED)
**Status:** Resolved
**Found:** Промт-12D — backend started returning structured 503 with
`{detail: {message, provider_error_code, provider_request_id}}` on YooKassa
upstream failures, but frontend either silently failed (web_portal) or
showed only a generic toast (mini_app) → Marina saw "ничего не происходит".
**Resolved:** 2026-04-28 (this session)

`mini_app` and `web_portal` topup flows now distinguish HTTP 503
PaymentProviderError from generic errors. User sees a graceful modal
с user-readable Russian message + copyable `provider_request_id` for
support quoting.

**Code changes (frontend-only):**
- `mini_app/src/lib/types.ts`: new `PaymentProviderErrorDetail` +
  `PaymentProviderErrorResponse` types.
- `mini_app/src/lib/errors.ts`: new `extractPaymentProviderError(err)`
  helper — async, parses ky `HTTPError.response.clone().json()` for the
  503 detail shape, returns `null` otherwise.
- `mini_app/src/components/ui/PaymentErrorModal.tsx` + `.module.css`:
  new modal built on existing `Modal` + `Notification` + `Button` (no
  new UI deps).
- `mini_app/src/components/ui/index.ts`: export added.
- `mini_app/src/hooks/queries/useBillingQueries.ts`: `useCreateTopUp`
  no longer attaches a generic-toast `onError`; the screen now owns
  error UX (so payment-provider modal and generic toast don't double-fire).
- `mini_app/src/screens/common/TopUpConfirm.tsx`: `onError` callback
  extracts payment provider detail → modal; otherwise falls back to a
  generic toast.
- Symmetric set in `web_portal/src/`: types, `lib/errors.ts`,
  `shared/ui/PaymentErrorModal.tsx`, `shared/ui/index.ts`,
  `screens/shared/TopUp.tsx` (added inline `<Notification type="danger">`
  for generic errors + modal mount). `useInitiateTopup` was already
  bare — only screen wiring changed.

**Fix commit:** `<SHA>` (this session, branch `fix/frontend-503-handling`).

After this commit:
- User on a 503 from `/api/billing/topup` sees a modal с translated
  message ("Платёжный сервис временно недоступен…") + the YooKassa
  `provider_request_id` (UUID) с кнопкой "📋 Копировать".
- Backend already supplies this shape since Промт-12D
  `PaymentProviderError → HTTP 503` mapping.
- YooKassa shop activation (live 403) still requires lk.yookassa.ru
  action — out of scope.

### BL-034 — YookassaService consolidation 14a (RESOLVED)
**Status:** Resolved
**Found:** BILLING_REWRITE_PLAN_2026-04-28.md item 6 (split into 14a/14b).
**Resolved:** 2026-04-28 (this session, Промт-15).

Item 6 14a executed: topup creation logic moved from BillingService to
YooKassaService with caller-controlled session (S-48).

**Code changes:**
- `YooKassaService.create_topup_payment` (new): caller-controlled session,
  YooKassa SDK call kept OUTSIDE DB transaction, raises
  `PaymentProviderError` on YK errors, persists `YookassaPayment` +
  pending `Transaction` via session.flush.
- `BillingService.create_payment` (deleted) — logic moved.
- POST `/api/billing/topup` migrated to `Depends(get_db_session)` + new
  service method. PaymentProviderError → HTTP 503 translation preserved.
  Added explicit `ValueError → HTTP 400` translation.
- `tests/unit/test_no_dead_methods.py` — `create_payment` added to
  `DEAD_BILLING_METHODS`. Не добавлено в `DEAD_YOOKASSA_METHODS` (см.
  open finding ниже).
- `tests/integration/test_billing_hotfix_bundle.py` — two Промт-12D tests
  rewired to mock `YooKassaService.create_topup_payment` and pass
  `session` to endpoint call.
- `tests/integration/test_yookassa_create_topup_payment.py` (new): 4
  integration tests covering happy path, ForbiddenError translation,
  user-not-found short-circuit, endpoint call shape.

**Critical operational invariant** preserved: SDK `Payment.create()` runs
**before** any DB write in `create_topup_payment`. Future modifications
must not move the SDK call into `session.begin()` or after
`session.flush()` — that would create a "real charge, no local record"
footgun if rollback fires after SDK success.

**NOT in this scope (deferred to 14b — Промт-16):**
- Webhook consolidation: `BillingService.process_topup_webhook` →
  `YooKassaService.process_webhook`.
- `BillingService.check_payment` removal.
- GET `/topup/{id}/status` migration to direct repo read.
- POST `/webhooks/yookassa` rewiring.

**Fix commit:** `<SHA>` (this session, branch
`fix/billing-rewrite-item-6a-yookassa-consolidation`).

After this commit:
- BillingService method count: 13 → 12.
- POST `/topup` on canonical `Depends(get_db_session)` DI pattern.
- Frontend 503 modal (Промт-14) works unchanged on the same shape.

#### Open findings surfaced during 14a — status update (Промт-15.5, 2026-04-28)

**Finding 1: RESOLVED** — bot `topup_pay` migrated to
`YooKassaService.create_topup_payment` (Промт-15.5, Marina chose option a).
Dead `YooKassaService.create_payment` removed. `tests/smoke_yookassa.py`
removed. AST lint extended (`create_payment` added to
`DEAD_YOOKASSA_METHODS`). 2 new integration tests in
`tests/integration/test_bot_topup_handler.py`.

**Finding 2: INVESTIGATED, decision pending Промт-15.7** — fee model
investigation report in
`CHANGES_2026-04-28_bot-topup-migration-fee-investigation.md`. Report is
factual: lists every site that uses each constant, traces 100 ₽ topup
through code, inventories all UI fee strings. No recommendation —
Marina's product decision (option I/II/III/IV in CHANGES file).

**Finding 1 — bot/handlers/billing/billing.py:60 `topup_pay` is broken-but-reachable**

`topup_pay` callback handler is registered live via
`@router.callback_query(F.data == "topup:pay", ...)`. It calls
`yookassa_service.create_payment(amount_rub=..., user_id=...)` which
points at the dead `YooKassaService.create_payment` method. The dead
method instantiates `YookassaPayment(amount_rub=..., credits=...,
description=..., confirmation_url=..., idempotency_key=...)` — but the
model has none of those fields (real fields: `gross_amount`,
`desired_balance`, `fee_amount`, `payment_url`, etc.). Result: any
Telegram user clicking "💰 Оплатить" hits a `TypeError`, caught by the
handler's `except Exception`, gets a generic error message.

Pre-existing (NOT introduced by 14a). Plan §0.5 classified `topup_pay`
as "dead" and asked the agent to remove the underlying dead method.
Empirical verification showed the handler is registered, so per plan
instruction the agent stopped and surfaced the finding. Marina chose
**Option A** (defer dead-method removal AND keep `tests/smoke_yookassa.py`).
The dead `YooKassaService.create_payment` remains in the codebase.

**Decision required (separate prompt):** either
- (a) migrate `topup_pay` to `create_topup_payment(session=...)`
  (handler already gets `session` via DI; would need to switch from
  passing `gross` to passing `amount`, since new method computes fee
  internally), or
- (b) delete `topup_pay` + the entire bot topup flow (web_portal is the
  primary topup path post-Промт-12D/14), or
- (c) leave as-is and accept the latent bug until either of the above
  is decided.

**Finding 2 — Bot UI displays 3.5% fee but billing applies 6%**

Pre-existing inconsistency. Bot keyboard text in
`src/bot/handlers/billing/billing.py:55` shows
`"Комиссия: {Decimal(amount) * Decimal('0.035'):.2f} ₽"` (3.5%), but
`src/constants/payments.py` defines two separate constants:
- `YOOKASSA_FEE_RATE = Decimal("0.035")` — actual YooKassa SDK fee.
- `PLATFORM_TAX_RATE = Decimal("0.06")` — ИП УСН 6% added on top of
  `desired_balance` to compute `gross`.

Both removed `BillingService.create_payment` and new
`YooKassaService.create_topup_payment` apply `PLATFORM_TAX_RATE` (6%).
The 3.5% bot UI text was written for `YOOKASSA_FEE_RATE` semantics; the
6% billing code was written for `PLATFORM_TAX_RATE` semantics. User-
facing display ≠ what is actually charged. Out of scope for 14a; flagged
for product/UX decision (which rate is the "real" fee, and what does the
user see?). Same parity preserved in `create_topup_payment` to avoid
silent behavior change in this prompt.

### BL-035 — Centralized fee config + new fee model (RESOLVED)
**Status:** Resolved
**Found:** Промт 15.6 inventory (legal-template ↔ code drift) + Marina decision
**Resolved:** 2026-04-28 (this session)

Промт 15.7 (1 of 5 in PLAN_centralized_fee_model_consistency.md).

**Code changes:**
- New `src/constants/fees.py` — single source of truth for all fee rates.
- Removed obsolete `PLATFORM_COMMISSION` (0.15), `OWNER_SHARE` (0.85),
  `PLATFORM_TAX_RATE` (0.06) from `payments.py`. `YOOKASSA_FEE_RATE`
  (0.035) and `NPD_RATE_FROM_*` moved to `fees.py`.
- Renamed and re-valued: `PLATFORM_COMMISSION_RATE = 0.20`,
  `OWNER_SHARE_RATE = 0.80`.
- Added `SERVICE_FEE_RATE = 0.015` (1.5% withheld from owner share at
  escrow release).
- `BillingService.release_escrow` updated: owner gets 78.8%,
  platform 21.2% of `final_price`; `meta_json` records full breakdown
  (final_price / owner_gross / service_fee / owner_net /
  platform_commission / platform_total).
- `BillingService.refund_escrow` `after_confirmation` scenario:
  was 50/42.5/7.5, now 50/40/10 via `CANCEL_REFUND_*_RATE` constants.
- `YooKassaService.create_topup_payment` uses 3.5% YooKassa rate
  (was 6% — old `PLATFORM_TAX_RATE`). Fixes BL-034 Finding 2 partially
  (UI now matches reality on topup; frontend hardcodes are 15.10).
- `PayoutService.payout_percentage` / `platform_percentage` now use new
  20%/80% constants (was 15%/85%).
- New endpoint `GET /api/billing/fee-config` for frontend consumption,
  no auth (public knowledge).
- AST lint `tests/unit/test_no_hardcoded_fees.py` — Decimal-literal
  scan over `src/`; allowlists constants files plus tax/scoring/config
  modules whose literals are non-fee semantic concepts.
- Constants consistency test `tests/unit/test_fee_constants.py` —
  invariants (sums == 1.00, computed rates, concrete 1000-₽ traces).

**Public contract delta:**
- Topup: user pays `desired × 1.035` (was `× 1.06`).
- Placement release: owner gets 78.8% (was 85%), platform 21.2%
  (was 15%).
- Cancel `after_confirmation`: 50/40/10 (was 50/42.5/7.5).

**Surfaced findings (deferred):**
- `BillingService.refund_escrow` scenario `after_escrow_before_confirmation`
  still gives 100/0/0 (matches `before_escrow`). Marina's "post-escrow
  pre-publish = 50/40/10" rule is not yet wired here. Bot UI in
  `placement.py:632` displays "Возврат 50%" but service credits 100%.
  Pre-existing UI/backend drift — defer to BL or follow-up prompt.
- `BillingService.refund_escrow` `after_confirmation` scenario semantically
  is post-publish (per docstring: "after publication confirmation"). Marina's
  rule says post-publish = 0% refund. Currently returns 50/40/10 — defer.
- VAT rate `Decimal("0.22")` still hardcoded at billing_service.py:790
  (`vat_amount = platform_fee * 0.22`) — separate concept (НДС). Lint
  literal `0.22` not in forbidden set; defer.
- Tax modules (`tax_repo.py`, `tax_aggregation_service.py`) use
  `Decimal("0.15")` for income tax — different concept, allowlisted in
  AST lint. Pending separate migration if/when fees.py grows tax constants.
- Reputation/review scoring weights (0.15 etc.) and PDF coords (0.5
  etc.) allowlisted to keep the lint signal-to-noise ratio high.
- `analytics_service.py` aggregates historical `final_price *
  OWNER_SHARE_RATE` — switching constant retroactively re-displays old
  earnings at 80% instead of 85%. Acceptable pre-prod (no real users
  per `MIGRATION STRATEGY` in CLAUDE.md). Surface for awareness only.

**Out of scope (next prompts):**
- 15.8 — Legal templates Jinja2 injection + version bump 1.0 → 1.1.
- 15.9 — Acceptance infrastructure (re-accept on version bump).
- 15.10 — Frontend updates (consume `/fee-config` endpoint; remove
  hardcoded `3.5%`/`6%`).
- 15.11 — Dead act-templates wire через `legal_status`.

**Fix commit:** see CHANGELOG / merge SHAs (this session).

### BL-036 — Промт 15.7 follow-up: rate doc + frontend sync (RESOLVED)
**Status:** Resolved
**Found:** Marina directive «не хардкодить, использовать формулы» applied beyond Промт 15.7 backend scope.
**Resolved:** 2026-04-28 (this session).

Computed helpers (`OWNER_NET_RATE = 0.788`, `PLATFORM_TOTAL_RATE = 0.212`)
добавлены в `src/constants/fees.py` рядом с `format_rate_pct()`. TS аналоги
(`OWNER_NET_RATE`, `PLATFORM_TOTAL_RATE`, `computePlacementSplit`,
`formatRatePct`, `CANCEL_REFUND_*`) добавлены в `mini_app/src/lib/constants.ts`,
`web_portal/src/lib/constants.ts`, `landing/src/lib/constants.ts`. Frontend
screens + docs обновлены чтобы использовать computed values вместо хардкодов.

**Code/template changes:**
- `src/constants/fees.py` — derived rates + `format_rate_pct()` helper.
- 3× frontend constants files — TS analogues + helpers.
- `src/bot/handlers/placement/placement.py`, `src/bot/handlers/admin/disputes.py`,
  `src/bot/handlers/shared/start.py`, `src/api/routers/disputes.py`,
  `src/core/services/tax_aggregation_service.py` — UI-strings + docstring через
  `format_rate_pct(...)`.
- 5× `mini_app/` and `web_portal/` screens — `computePlacementSplit` /
  `OWNER_NET_RATE` instead of literal `0.85` / `0.788`.
- `landing/src/components/{FAQ,HowItWorks}.tsx` — formula-derived strings.
- Docs: `CLAUDE.md`, `QWEN.md`, `README.md`, `docs/AAA-01..04`, `AAA-08`,
  `.qwen/agents/{backend-core,docs-architect-aaa}.md` — sync на новую model;
  v4.2 «15/85» помечена как историческая.

**Public contract delta:**
- None. No new endpoints, no schema changes. Same fee numbers as BL-035.
- UI displays теперь consistent (78,8% / 21,2% / 50% / 40% / 10%) — раньше
  drift между gross-constants и effective rates показывал legacy 85%/15%.

**Effect:** устраняет drift между gross constants (20% / 80% / 1.5%) и
effective rates (78.8% / 21.2%) — последние всегда выводятся formula,
никогда не хардкодятся. Reduces scope of upcoming Промт 15.10 (frontend) и
Промт 15.12 (docs cleanup) — большая часть уже сделана.

**Verification:**
- `poetry run ruff check src/`: 0 errors.
- `poetry run pytest tests/unit/test_no_hardcoded_fees.py
   tests/unit/test_fee_constants.py`: 10 passed.
- TS rebuild через `docker compose build nginx` — Vite собирает 3 фронта.

**Out of scope:**
- 15.8 — Legal templates Jinja2 injection (next).
- 15.9 — Acceptance infrastructure.
- 15.10 — Frontend `/fee-config` consumption (большая часть hardcode уже снята
  этим follow-up, остаётся только хардкоды `3.5%` / `6%` где не покрыто).

**Fix commit:** see CHANGELOG / merge SHAs (this session).

### BL-037 — Timeline должен tracking все sub-stages с fail-fast STOP
**Status:** Open
**Found:** 2026-04-28 (Claude.ai session, обсуждение flow diagram)
**Category:** Architecture / Process discipline / Observability

**Контекст.** Текущая визуализация placement+billing+legal flow
показывает только high-level stages (8 этапов от регистрации до
выплаты). Реальный flow включает множество sub-stages внутри каждого
этапа — `ord_registration` SDK call, generation document'ов,
acceptance gates, escrow freeze, notification dispatch, KUDIR record
creation, и т.д.

**Требование.** Система должна tracking каждый sub-stage жизненного
цикла placement (не только основные этапы), и fail-fast STOP на любом
сбое sub-stage. Никакого partial state advancement — если sub-step
упал, весь flow останавливается на текущем шаге, состояние явно
зафиксировано как `<stage>_failed:<reason>`, требует ручного /
автоматического recovery либо rollback.

Это противоположность текущему "best-effort" pattern'у где Celery
task может частично выполниться, оставив flow в неопределённом
состоянии (escrow frozen но Transaction не записана, ERID получен но
publication не произошла, и т.д.).

**Зачем.**
1. Audit trail completeness — каждый sub-stage оставляет след
   (Transaction row, status update, structured log).
2. Recovery without forensics — явный state позволяет resume с
   конкретного места без угадывания "а что уже произошло".
3. Legal compliance — если flow остановился до получения ERID, мы
   гарантированно НЕ опубликовали без маркировки.
4. Money safety — silent partial flows главный источник ledger drift
   (пример: CRIT-2 в Промте-12). Atomic STOP исключает класс таких
   багов.

**Sub-stage примеры (где требуется явная granularity).**

Stage 4 (Принятие заявки): 4a. owner click accept; 4b.
freeze_escrow_for_placement (lock + balance check + decrement
advertiser → increment platform_account.escrow_reserved); 4c.
Transaction(type=escrow_freeze) + idempotency_key; 4d.
PlacementRequest status → escrow_frozen; 4e. act_placement.html
generated; 4f. notification dispatched. Если 4b succeeded но 4c failed
(e.g. DB constraint violation) — STOP, escrow rollback, status revert.
Не continue к 4d.

Stage 5 (ОРД регистрация): 5a. submit creative payload; 5b. receive
ERID; 5c. persist ERID on PlacementRequest; 5d. verify ERID format.
Если 5a timed out или 5b returned error — STOP. Не continue к
publication. Status → erid_pending или erid_failed. Никогда publication
без verified ERID.

Stage 7 (Завершение): 7a. trigger condition met; 7b. release_escrow
(advertiser unchanged, owner.earned_rub +788, platform escrow_reserved
−1000, +212 commission + service fee); 7c. Transaction × 2; 7d.
act_advertiser.html; 7e. act_owner_<status>.html (по
owner.legal_status); 7f. KUDIR records appended; 7g. notifications.
Любой из 7b-7g failed → STOP, status release_failed:<sub_stage>,
PlacementRequest stays in published, manual review.

**Implementation hints.**
- State machine с явными transitions: PlacementTransitionService уже
  задаёт паттерн. Расширить для всех stages, sub-stages как explicit
  state transitions (не inline mutations внутри одной Celery task).
- Atomic units: каждый sub-stage — caller-controlled session boundary
  с явным commit / rollback.
- Status enum gradacии: escrow_freeze_pending, escrow_frozen,
  escrow_freeze_failed:<reason>, erid_pending, erid_received,
  erid_failed:<reason>, published, release_pending, released,
  release_failed:<sub_stage>. Текущий narrow enum (draft, submitted,
  escrow_frozen, published, completed, cancelled) недостаточен.
- Recovery jobs: Celery beat tasks per *_pending status, retry с
  backoff + max attempts → escalate to admin.
- Observability: structured logs с placement_id, stage, sub_stage,
  status, error_class, error_message, retry_count.

**Scope.** Placement lifecycle (extending PlacementTransitionService);
ОРД integration; document generation pipeline; acceptance flows
(re-accept loop on version bump); payout pipeline; dispute resolution
(новый DisputeResolutionService — design сразу с этим pattern'ом).

**Связанные.** Phase 2 PlacementTransitionService — baseline.
Промт-12 CRIT-2 — пример класса багов которые pattern предотвратил бы.
BILLING_REWRITE_PLAN_2026-04-28.md item 7 (PlanChangeService) + item
16 (PlacementCancelService + DisputeResolutionService) — должны быть
design'ed с sub-stage tracking сразу.

**Resolution criteria.** Audit всех flows на atomicity sub-stages;
granular status enums; каждый sub-stage как explicit transition с
error handling; recovery jobs для *_pending statuses; documented
invariants; smoke tests где sub-stage failure verified to STOP всё
дальше. Realistic timeline — Phase 3+ после billing rewrite +
legal templates + fee model consistency завершены. Должен быть разбит
на под-промты.

### BL-038 — Legal templates Jinja2 fee injection + version 1.1 (RESOLVED)

**Status:** Resolved
**Found:** PLAN_centralized_fee_model_consistency.md (Промт 15.8)
**Resolved:** 2026-04-29 (this session)

Промт 15.8 (2 of 5 in fee model consistency rewrite). Templates на
старой fee modelи + хардкод процентов; backend на новой (Промт 15.7).

**Code/template changes:**

- `src/constants/legal.py`: `CONTRACT_TEMPLATE_VERSION` "1.0" → "1.1";
  added `CONTRACT_EDITION_DATE = "28 апреля 2026 г."`.
- `src/core/services/contract_service.py`: new module-level
  `_format_pct()` + `_build_fee_context()` helpers inject fee
  percentages, version, and edition date as Jinja2 vars. Both
  `_render_template()` (contracts) and `render_platform_rules()`
  (preview) wired.
- `src/core/services/act_service.py`: imports `_build_fee_context`
  and merges it into `_render_act_template` ctx (separate Jinja env
  from ContractService — see CLAUDE.md drift report).
- `src/templates/contracts/platform_rules.html`:
  - Edition header "Редакция от 28 апреля 2026 г., версия 1.1".
  - § 5 (Комиссия) переписан с упоминанием 1,5% сервисного сбора,
    78,8% эффективной выплаты, и cancel splits 50/40/10.
  - § 18 (115-ФЗ) добавлен — boilerplate placeholder.
  - § 19 (юрисдикция) добавлен — boilerplate placeholder.
- `src/templates/contracts/advertiser_campaign.html`:
  - § 6.1 хардкод 80%/20% → Jinja vars + 1,5% сервисный сбор.
  - § 5.1 cancel split → Jinja vars (cancel_advertiser_pct / owner_pct
    / platform_pct).
  - § 5.3 (legacy 80%/40% post-publication refund window) — оставлено
    как есть с `noqa-fees` маркерами; reconciled в 15.11.5.
  - Edition header добавлен.
- 4× `src/templates/contracts/owner_service_*.html`: § 7.1 хардкод
  80%/20% → Jinja vars + 1,5%/78,8% полная цепочка. Edition headers.
- 6× `src/templates/acts/*.html`: edition headers added (только
  act_placement.html активно используется; остальные dead до 15.11).
- `tests/unit/test_no_hardcoded_fees.py`: extended новой функцией
  `test_no_hardcoded_percentages_in_legal_templates` — scans HTML
  templates на canonical-fee percentages outside Jinja expressions.
  Per-line `noqa-fees` opt-out для документированных исключений.
- `tests/integration/test_contract_service_fee_injection.py` (new):
  4 integration tests — commission %, edition header, 115-ФЗ section,
  jurisdiction section.

**Public contract delta:**

- `GET /api/contracts/platform-rules/text` — response shape
  unchanged (`{html: ...}`). HTML content updated:
  - Edition header.
  - § 5 references 20%/80%/1,5%/78,8%/cancel splits.
  - § 18 (115-ФЗ) и § 19 (юрисдикция) — placeholders, помечены для
    legal review.

**Critical caveats:**

- Templates на новой fee model + backend (после 15.7) тоже на новой —
  legal vs code consistent.
- Frontend `mini_app/src/screens/advertiser/TopUpConfirm.tsx:66`
  всё ещё хардкодит `0.035` — Промт 15.10.
- Re-acceptance loop при version bump НЕ active в этом промте —
  `CONTRACT_TEMPLATE_VERSION = "1.1"` но existing acceptance rows
  (если есть) на v1.0 не invalidate. Dev DB пустая → impact zero
  сейчас. Полная реализация — Промт 15.9.
- 115-ФЗ + юрисдикция тексты — **placeholders**, требуют review
  юристом до real prod launch.

**Out of scope (next prompts in PLAN_centralized_fee_model_consistency.md):**

- 15.9 — Acceptance infrastructure (re-accept loop при version
  mismatch).
- 15.10 — Frontend updates (consume `/fee-config` + fix
  TopUpConfirm.tsx hardcode).
- 15.11 — Dead act-templates wire через legal_status.
- 15.11.5 — Backend cancel scenarios fix (legacy 80%/40%
  post-publication refund window in advertiser_campaign.html § 5.3).

### BL-039 — Acceptance infrastructure: re-accept loop при version mismatch (RESOLVED)

**Status:** Resolved
**Found:** PLAN_centralized_fee_model_consistency.md (Промт 15.9)
**Resolved:** 2026-04-29 (this session)

Промт 15.9 (3 of 5+ in fee model consistency rewrite). Templates говорят
v1.1 (15.8) и backend знает v1.1, но needs_accept_rules делал только
truthy-check `User.platform_rules_accepted_at is None` — version mismatch
silently игнорировался.

**Code/template changes:**

- `src/db/repositories/contract_repo.py`: новый
  `ContractRepo.get_latest_acceptance(user_id, contract_type)` — order by
  `signed_at DESC`, фильтр `contract_status='signed'`.
- `src/core/services/contract_service.py`:
  - `needs_accept_rules(user_id)` (новый, read-only) — fetches latest
    signed acceptance, returns True если none OR
    `latest.template_version != CONTRACT_TEMPLATE_VERSION`. Sub-stages
    4a-4c (BL-037).
  - `accept_platform_rules(user_id)` — sub-stages 5a-5e (BL-037);
    UPDATE branch теперь refreshes `template_version` (был bug — old
    rows оставались на v1.0 после re-accept). S-48 compliant: caller
    commits.
- `src/api/routers/users.py`:
  - `GET /api/users/needs-accept-rules` теперь делает version-aware
    compare через ContractService (был inline truthy-check).
  - Pydantic `NeedsAcceptRulesResponse` (`{needs_accept: bool}`,
    `frozen=True`).
- `web_portal/src/components/guards/RulesGuard.tsx`: switched from
  `useMe` truthy-check к `useNeedsAcceptRules` (version-aware).
- `web_portal/src/hooks/useUserQueries.ts`: `useNeedsAcceptRules`
  staleTime 5 min → 0 + refetchOnWindowFocus (re-accept должен
  surface immediately).
- `web_portal/src/hooks/useContractQueries.ts`: `useAcceptRules`
  invalidates `['user', 'needs-accept-rules']` + `['user', 'me']`.
- `web_portal/src/components/layout/PortalShell.tsx`: removed
  redundant accept-rules banner — RulesGuard hard redirect uniquely
  governs the gate.
- `mini_app/src/api/users.ts` + `mini_app/src/hooks/queries/useUserQueries.ts`:
  added `checkNeedsAcceptRules` + `useNeedsAcceptRules`.
- `mini_app/src/components/RulesGuard.tsx`: switched from `useMe`
  truthy-check к `useNeedsAcceptRules` (version-aware).
- `mini_app/src/hooks/useLegalAcceptance.ts`: invalidates
  `['user', 'needs-accept-rules']` after accept.
- `src/bot/middlewares/acceptance_middleware.py` (новый): blocks bot
  interaction с accept-prompt (callback button + WebApp deep link).
  Sub-stages 10a-10d. **Fail-open** на DB errors. Exempt: /start,
  terms:*, contract:accept_rules.
- `src/bot/main.py`: middleware registered после RoleCheck, до
  FSMTimeout.
- `tests/integration/test_acceptance_flow.py` (новый): 5 tests —
  new user / current version / old version / atomic update / version
  bump simulation.
- `tests/integration/test_needs_accept_rules_endpoint.py` (новый): 1
  endpoint smoke test (web_portal audience через
  `app.dependency_overrides`).

**Public contract delta:**

- **Modified endpoint:** `GET /api/users/needs-accept-rules` — body
  shape unchanged (`{needs_accept: bool}`), но result теперь reflects
  version-aware compare, не truthy-check.
- **Existing endpoint:** `POST /api/contracts/accept-rules` — internal
  logic upgraded (UPDATE branch now refreshes template_version);
  response shape unchanged.

**Sub-stage tracking (BL-037 first applied):**

- `accept_platform_rules`: 5a (capture now+version) → 5b (upsert
  authoritative platform_rules) → 5c (mirror legacy privacy_policy)
  → 5d (sync User cache) → 5e (flush, caller commits).
- `needs_accept_rules`: 4a (fetch latest) → 4b (none → True) → 4c
  (version compare).
- Bot middleware: 10a (extract user_id) → 10b (DB lookup) → 10c (call
  service, fail-open on exception) → 10d (block + send prompt).

**Critical caveats:**

- DB пустая, no real users → impact zero on deploy.
- Bot middleware **fail-open**: DB error → user *not* blocked. Marina
  decision pending: prod может предпочесть fail-closed (безопаснее)
  vs текущий fail-open (robust к transient infra glitches).
- `/api/contracts/platform-rules/text` carve-out comment **не
  добавлен** — 15.10 territory (per плана).
- Frontend `TopUpConfirm.tsx:66` всё ещё хардкодит 0.035 — 15.10.

**Gate baseline (pre → post):**

- Forbidden-patterns: 17/17 → 17/17.
- Ruff src/: 21 → 21 (at ceiling, no regression).
- Mypy: 10 → 10 (at ceiling, no regression).
- Pytest substantive: 76F + 17E + 655P → 76F + 17E + 661P (+6 new).

**Out of scope (next prompts):**

- 15.10 — Frontend `/fee-config` consumption + TopUpConfirm hardcode
  + carve-out comment in `/contracts/platform-rules/text` route.
- 15.11 — Dead act-templates wire через legal_status.
- 15.11.5 — Backend cancel scenarios fix.

**Fix commit:** see git log on `fix/acceptance-infrastructure`.

### BL-040 — Frontend fee-config consume + bot handler scenario fix + middleware fail-closed (RESOLVED)
**Status:** Resolved
**Found:** PLAN_centralized_fee_model_consistency.md (combined Промт 15.10 + 15.11.5)
**Resolved:** 2026-04-29 (combined deployable checkpoint)

Combined промт closing three related findings as a single PR. Marina
chose option (A) for Часть B after inventory surfaced that the
prompt-as-written would break 4 callers (auto-cancel paths +
disputes "partial" flow). The actual cancel-scenarios bug was a
single-character mis-routing in the bot handler, **not** a
BillingService rewrite.

1. **Часть A (15.10) — Frontend /fee-config consume.** Constants in
   `web_portal/src/lib/constants.ts`, `mini_app/src/lib/constants.ts`
   and `landing/src/lib/constants.ts` now consumed by all screens
   that previously hardcoded `0.035` / `0.015` / `1,5%` / `3,5%` /
   `78,8%` / `21,2%`. Priority finding `TopUpConfirm.tsx:66`
   resolved (literal `0.035` → `YOOKASSA_FEE`). New `useFeeConfig`
   hook in both frontends fetches `/api/billing/fee-config` for
   runtime sync. Carve-out inline comment added to
   `src/api/routers/contracts.py::get_platform_rules_text` (Phase 1
   §1.B.2 — text-only legal content, both audiences consume).
2. **Часть B (15.11.5) — Bot handler scenario string corrected.**
   `src/bot/handlers/placement/placement.py` `camp_cancel_after_escrow`
   was passing `scenario="after_escrow_before_confirmation"` (100%
   advertiser refund) while UI promised "Возврат 50%". Replaced with
   `scenario="after_confirmation"` (50/40/10 split — matches UI).
   **Not a billing rewrite**: BillingService logic unchanged,
   auto-cancel tasks (placement_tasks.py — owner-fault refunds at
   100%) and dispute "partial" verdicts (50/40/10) untouched. The
   "should refund 50/40/10 in this scenario" semantics already
   lived in `after_confirmation`, the bot handler was simply
   mis-pointing.
3. **Часть C (mini-fix) — AcceptanceMiddleware fail-closed.** Per
   Marina decision per BL-039 surfaced finding: `needs_accept_rules`
   exception → block + send "Технические проблемы" notice (was: log
   + pass through). Sub-stages re-numbered 13a-13d.

**Code changes:**
- `web_portal/src/api/billing.ts` + `mini_app/src/api/billing.ts`:
  new `getFeeConfig()` + `FeeConfigResponse` types.
- `web_portal/src/hooks/useBillingQueries.ts` +
  `mini_app/src/hooks/queries/useBillingQueries.ts`: new
  `useFeeConfig()` hook (5min staleTime, 30min gcTime).
- Frontend screens consuming constants: `TopUpConfirm.tsx`
  (web_portal + mini_app), `TopUp.tsx`, `OwnPayoutRequest.tsx`,
  `OwnPayouts.tsx` (web_portal + mini_app), `Help.tsx` (web_portal
  + mini_app), `AdvertiserFrameworkContract.tsx`, `Compliance.tsx`.
- `landing/src/lib/constants.ts`: added
  `CANCEL_REFUND_ADVERTISER = 0.50`.
- Removed two stale "Промт 15.7" explanatory comments
  (`OwnRequests.tsx`, `OwnRequestDetail.tsx`) which contained
  hardcoded "1.5%" inside an explanation of `OWNER_NET_RATE` —
  conflicting with the new lint rule.
- `src/api/routers/contracts.py`: inline carve-out comment.
- `src/bot/handlers/placement/placement.py:622`: scenario string
  changed (one-line edit).
- `src/bot/middlewares/acceptance_middleware.py`: fail-closed branch
  + `TECHNICAL_ERROR_TEXT` constant.
- `scripts/check_forbidden_patterns.sh`: 14 new patterns
  (forbidden-patterns count 17 → 31).
- `tests/test_bot_cancel_scenario_consistency.py`: 4 new
  source-inspection tests locking in scenario routing.
- `tests/test_acceptance_middleware_fail_closed.py`: 3 new
  middleware tests (fail-closed, pass-through, block-on-needs).

**Public contract delta:**
- Bot user-cancel-from-escrow now refunds 50% (was: 100% silent
  bonus). UI text and DB write are aligned.
- Bot middleware blocks user with technical-error notice on DB
  error (was: silent pass-through, handler called).
- Auto-cancel paths (publish failure, SLA timeout, stuck escrow
  recovery) UNCHANGED — still 100% advertiser refund, owner is at
  fault. Disputes "partial" verdict UNCHANGED — still 50/40/10.

**Sub-stage tracking (BL-037 application):**
- `AcceptanceMiddleware`: 13a (extract user) → 13b (DB lookup) →
  13c (needs check, block-with-prompt) → 13d (fail-closed branch
  on exception, send technical notice).

**Critical caveats:**
- DB пустая → bot scenario fix has zero impact on existing data.
- Real users появятся → user-initiated cancels из escrow get 50%
  refund instead of 100%. UI matched DB before the fix at the
  user's expense; now they match honestly.
- Middleware fail-closed: users may be blocked during transient
  DB issues. Trade-off accepted per Marina (better than silent
  fail-open in pre-prod).

**Surfaced finding (informational):**
- The semantic naming `after_escrow_before_confirmation` vs
  `after_confirmation` in `BillingService.refund_escrow` is
  confusing — `after_confirmation` actually means "after the
  advertiser confirmed THEIR cancellation" (= post-escrow
  pre-publish), not "after publication confirmation". Two callers
  use each scenario correctly given the actual semantics; the bug
  was purely in the bot handler. Renaming the scenarios for
  clarity is deferred — out of scope here, would touch
  BillingService + 4 callers + dispute flow.

**Gate baseline (pre → post):**
- Forbidden-patterns: 17/17 → 31/31 (+14).
- Ruff src/: 21 → 21 (at ceiling, no regression).
- Mypy: 10 → 10 (at ceiling, no regression).
- Pytest substantive: 76F + 17E + 661P → 76F + 17E + 668P (+7
  new — 4 cancel scenario + 3 middleware).

**Out of scope (next prompts):**
- 15.11 — Dead act-templates wire (5 templates: act_advertiser,
  act_owner_{fl,ie,le,np}).
- 15.12 — Documentation cleanup.
- 15.13 — Webhook consolidation 14b.
- 16.x series — PII Hardening (separate epic).

**Fix commit:** see git log on `fix/fee-config-consume-and-cancel-scenarios`.

### BL-041 — Process rule: verify CLAUDE.md before "fix latent bug" promts

**Status:** Resolved (process rule codified)
**Found:** Промт 15.10 STOP (Шаг 0 caught semantic conflict between prompt
narrative and CLAUDE.md authoritative section)
**Resolved:** 2026-04-29 (this session — process rule + entry)

When a prompt instructs "fix latent bug" or "correct semantic mismatch",
first step of Шаг 0 MUST be: cross-check authoritative source
(`CLAUDE.md` / `PROJECT_KNOWLEDGE`) for canonical semantics. If the
prompt and CLAUDE.md disagree → STOP, escalate Marina decision before
any code change.

**Why:** в Промте 15.10+15.11.5 combined I (Claude.ai) interpreted
`after_confirmation` semantically as "after publication confirmation" →
proposed 0% refund. Agent в Шаге 0 поднял CLAUDE.md — фактическая
семантика "after [advertiser's cancellation] confirmation" с 50/40/10
split (логика уже была correct в BillingService). Real bug — bot
handler передавал wrong scenario string (UI lies). One-line fix vs
proposed BillingService rewrite.

**How to apply:**
- Future "fix latent bug" promts: explicit step "verify CLAUDE.md
  semantics for [topic]" before any code change.
- If conflict — STOP gate, escalate Marina.
- Empirical verification gate (h) extension — applies к "fix latent bug"
  promts equally as к diagnostic findings.
- BL-026 pattern (research enumeration пропускает callers) — agent
  enumerated 4 callers `refund_escrow` в Шаге 0, prompt не упоминал.
  Same blind-spot.

### BL-042 — Cancel scenario naming refactor (deferred)

**Status:** Deferred
**Found:** Промт 15.10 surfaced finding (Шаг 0 inventory of
`refund_escrow` callers)
**Deferred for:** breaking change — touches `BillingService` + 4 callers
+ dispute flow.

Current scenario names в `BillingService.refund_escrow` confuse
semantically:
- `before_escrow`: 100% advertiser refund (pre-escrow).
- `after_escrow_before_confirmation`: 100% advertiser (= "system-initiated
  cancel" — auto-recovery).
- `after_confirmation`: 50/40/10 split (= "advertiser confirmed THEIR
  cancellation").

Naming suggests "before/after publication" semantics, but actual axis =
"system vs advertiser actor". Future refactor — rename для clarity:
- `before_escrow` → `pre_escrow` (no change).
- `after_escrow_before_confirmation` → `system_auto_cancel` (e.g. owner
  failed, SLA timeout, stuck escrow recovery).
- `after_confirmation` → `advertiser_cancel_post_escrow` (advertiser
  confirmed their decision).

**Acceptance:**
- Rename `CancelScenario` enum values consistently.
- Update 4 callers + `disputes.py`.
- Integration tests adapted.

**Why deferred:**
- Breaking change для existing callers.
- Не блокирует real users (DB пустая).
- Pattern works correctly с current naming, only confusing для future
  readers.
- Не приоритет vs Phase 3 / 16.x scoping.

**Pickup:** во время Phase 3 cleanup или после real users появятся,
когда necessitates more deliberate semantic clarity.

### BL-043 — Bot AcceptanceMiddleware fail-mode review для prod (deferred)

**Status:** Deferred (Marina decision before real users launch)
**Found:** Промт 15.9 surfaced finding, 15.10 implemented fail-closed
**Deferred for:** review timing — fail-closed appropriate for pre-prod,
may need adjustment when real users появятся.

Current state (post-15.10): `AcceptanceMiddleware` fails closed на DB
error — blocks user, sends "Технические проблемы" message. Aligned с
Marina decision (better than fail-open silent pass-through).

**Trade-off:**
- Fail-closed: safe (user не получает access во время transient issues),
  но blocks user если DB temporarily unreachable.
- Fail-open: robust к transient issues, но silently miss stale acceptance
  detection.

**Pre-prod (current):** fail-closed appropriate — DB пустая, no real
load, errors visible.

**Real prod considerations:**
- Если DB issues become recurring → fail-closed может frustrate users.
- Alternative: circuit breaker pattern (fail-closed первые N seconds,
  fallback to fail-open after threshold).
- Alternative: stale-while-revalidate (use cached needs_accept_rules
  result на short TTL if query fails).

**Pickup:** review pre real-users-launch (Phase 3 / 4 timeframe).

### BL-044 — PII audit findings surfaced as BL entries (gap closure)

**Status:** Resolved (this session — entries created BL-045..BL-051)
**Found:** `PII_AUDIT_2026-04-28.md` (read-only audit during 15.x session)
**Resolved:** 2026-04-29

PII audit (2026-04-28, read-only) выявил CRIT/HIGH/MED findings которые
**не были записаны** как BL entries — gap that this entry closes.

Findings live в `reports/docs-architect/discovery/PII_AUDIT_2026-04-28.md`.
After this session — surfaced как individual BL entries (BL-045..BL-051)
для tracking при открытии серии 16.x (PII Hardening).

DB пустая → findings latent сейчас, fix должен пройти до real users
launch.

### BL-045 — CRIT-1: Bot payout FSM accepts financial PII

**Status:** CLOSED 2026-04-30 (серия 16.3 / Group C)
**Found:** `PII_AUDIT_2026-04-28.md` § O.1
**Severity:** Critical (FZ-152, three-way violation)

Bot `src/bot/handlers/payout/payout.py:281-351` accepts 16-digit card /
phone via `message.text`, echoes plaintext в Telegram chat (line 347),
stores plaintext в БД. Triple violation: bot inbound, bot outbound,
plaintext at rest.

**Architectural decision (Marina, 2026-04-30):** Полное удаление
bot payout flow. Web_portal — единственное место для payout setup.

**Fix:** Удалены `src/bot/handlers/payout/` (351 LOC, 7 функций),
`src/bot/states/payout.py` (PayoutStates FSM), `src/bot/keyboards/payout/`
(dead helpers). Entry-point кнопки в `own_menu.py`, `cabinet.py`,
`notifications.py` переключены на `WebAppInfo` → mini_app
placeholder `/own/payouts/request` → `OpenInWebPortal` → web_portal.

Архитектурное отклонение от промта: вместо нового server-side
`build_portal_deeplink` (требовал бы parallel "bot-to-portal" exchange,
поскольку `/exchange-miniapp-to-portal` требует mini_app JWT) —
переиспользована существующая Phase 1 цепочка через mini_app
placeholder. Net effect identical, audit surface не расширен.

**Closure detail:** `CHANGES_2026-04-30_remove-bot-payout-flow.md`.
Regression coverage: `tests/unit/test_fsm_middlewares.py::TestNoBotPayoutFlow`
(`test_payout_handler_module_absent`, `test_payout_states_module_absent`).

### BL-046 — CRIT-2: /api/payouts/* accepts mini_app JWT

**Status:** CLOSED 2026-04-29 (серия 16.1 / Group A)
**Found:** `PII_AUDIT_2026-04-28.md` § O.2
**Severity:** Critical (FZ-152)

`/api/payouts/*` endpoints использовали `CurrentUser` (both audiences).
`PayoutResponse.requisites` пролетал в mini_app JSON heap on
`getPayouts()`. Screen не renders, но в payload присутствовал.

**Fix:** Все 3 endpoint'а в `src/api/routers/payouts.py` переведены на
`Depends(get_current_user_from_web_portal)`. Mini_app JWT возвращает
403 на audience-несовпадении.

**Closure detail:** `CHANGES_2026-04-29_pii-pinning-payouts-admin.md`.
Regression coverage: `tests/unit/api/test_pii_audience_pinning.py`
(3 теста для payouts).

### BL-047 — HIGH-3: DocumentUpload.ocr_text plaintext at rest

**Status:** CLOSED 2026-04-30 (серия 16.2 / Group B)
**Found:** `PII_AUDIT_2026-04-28.md` § O.3
**Severity:** High (FZ-152)

`DocumentUpload.ocr_text` field stored 10K chars passport OCR text
plaintext.

**Fix:** column type `Text` → `EncryptedString(50000)` в
`src/db/models/document_upload.py:47`. Migration column kept `sa.Text()`
(unbounded — encryption ORM-level only, per existing
`legal_profile`/`platform_account` convention).

**Closure detail:** `CHANGES_2026-04-30_pii-encryption-at-rest.md`.
Regression coverage: `tests/integration/test_pii_encryption_at_rest.py`
(`test_document_upload_ocr_text_encrypted_at_rest`).

### BL-048 — HIGH-4: PayoutRequest.requisites plaintext at rest

**Status:** CLOSED 2026-04-30 (серия 16.2 / Group B)
**Found:** `PII_AUDIT_2026-04-28.md` (Часть 1.2 + § 2.2)
**Severity:** High (FZ-152)

`PayoutRequest.requisites` stored bank details + card numbers plaintext.

**Fix:** column type `String(512)` → `EncryptedString(2048)` в
`src/db/models/payout.py:41`. Migration column `sa.String(512)` →
`sa.String(2048)` to fit Fernet token (~ 4/3 base64 expansion).

**Closure detail:** `CHANGES_2026-04-30_pii-encryption-at-rest.md`.
Regression coverage: `tests/integration/test_pii_encryption_at_rest.py`
(`test_payout_request_requisites_encrypted_at_rest`).

### BL-049 — MED-5: /api/admin/* not pinned к web_portal

**Status:** CLOSED 2026-04-29 (серия 16.1 / Group A)
**Found:** `PII_AUDIT_2026-04-28.md` § O.4 (+ § O.5 covered as side-effect)
**Severity:** Medium (FZ-152)

`/api/admin/legal-profiles`, `/users`, `/platform-settings`, `/payouts`,
`/audit-logs`, `/contracts`, и др. authenticate'ились через
`AdminUser → get_current_user` (both audiences).

**Fix (Strategy A — global):** `src/api/dependencies.py:191`
`get_current_admin_user` теперь wraps `get_current_user_from_web_portal`.
Auto-applies к admin.py (20 endpoint'ов via `AdminUser`), feedback.py
(4 admin endpoint'а via `Depends(get_current_admin_user)`), и
disputes.py (2 admin endpoint'а). Mini_app JWT отбивается до проверки
`is_admin`. Web_portal non-admin по-прежнему получает 403 от is_admin
gate.

**§ O.5 closure:** `/api/admin/platform-settings` plaintext bank fields
exposure также закрыт этим audience pin'ом (per audit: "Same
web_portal-binding fix as O.4"). Отдельный BL не заведён.

**Closure detail:** `CHANGES_2026-04-29_pii-pinning-payouts-admin.md`.
Regression coverage: `tests/unit/api/test_pii_audience_pinning.py`
(4 admin-теста + 3 sanity-теста).

### BL-050 — MED-6: UserResponse referral leak

**Status:** Closed 2026-04-30 (16.4)
**Found:** `PII_AUDIT_2026-04-28.md` § 2.2 (line 115)
**Severity:** Medium (FZ-152)

`UserResponse.first_name/last_name` exposed обоим audiences. Own name
OK, но `GET /api/users/me/referrals` returns other users'
`first_name/last_name` = ПД leak.

**Resolution:** actual leak surface was `ReferralItem` (separate schema
in `src/api/routers/users.py`), not `UserResponse` itself.
`UserResponse` is only used for self-context endpoints (`/me`, `/auth/me`,
`/auth/login`) — own data, not a leak. Fix dropped `first_name` from
`ReferralItem`, renamed `joined_at` → `created_at` (align with frontend
convention), updated frontend type + display fallback (`User #{r.id}`
вместо never-returned `telegram_id`). Regression test in
`tests/unit/test_pii_referral_isolation.py`. Detail в
`CHANGES_2026-04-30_userresponse-referral-leak-fix.md`.

### BL-054 — Pre-existing test failures: bot-side suite + main_menu collection error

**Status:** NEW, deferred (out of scope for series 16.x security work)
**Surfaced in:** 16.1 closure отчёт (verified pre-existing via `git stash`)
+ 16.2 closure (re-verified `test_escrow_payouts.py` failure pre-existing
on `develop`, identical signature: `sqlite3.OperationalError: no such
table: placement_requests`).

**What:** test infrastructure debt accumulating in three buckets:

1. `tests/unit/test_main_menu.py` — collection error (cannot import).
2. `tests/unit/test_start_and_role.py` + several other bot-handler
   files — ~62 failures (precise count from 16.1 closure observations).
3. `tests/unit/test_escrow_payouts.py` — SQLite-backed unit tests
   missing schema initialisation (`no such table` on INSERT). Fix likely
   requires switching to `tests/integration/conftest.py`-style
   testcontainers + `Base.metadata.create_all`, OR explicit DDL in the
   unit-test fixture.

**Why deferred:** out of PII / fee model / legal scope. Tests are
broken at infrastructure level, not runtime — production behaviour
unaffected. Accumulating → surface for dedicated test infra cleanup
prompt.

**Acceptance:** all three buckets either pass or are deleted as dead
code if the underlying handler/menu module is no longer wired.

**Pickup:** post-16.x or as a standalone "test infra hardening"
mini-promt.

### BL-051 — PII audit LOW findings batch

**Status:** Closed 2026-04-30 (series 16.x — sub-tasks split across 16.5a/b/c)
**Found:** `PII_AUDIT_2026-04-28.md` §§ O.6-O.10
**Severity:** Low

LOW findings batch:
- ✅ Dead `LegalProfileStates` (15 states, 0 handlers) — closed 16.5a.
- ✅ `mini_app/src/api/payouts.ts::createPayout` exported but unused
  (loaded gun) — closed 16.5a.
- ✅ `log_sanitizer` ↔ Sentry scrub divergence — closed 16.5b. Шаг 0
  inventory found 3 lists, не 2: log_sanitizer 12 keys, api/main Sentry
  13 keys, tasks/sentry_init Celery Sentry 16 keys. Decision: option
  (c) Sentry-only merge — log_sanitizer untouched per CLAUDE.md NEVER
  TOUCH. Resolution: canonical 18-key list в `src/utils/pii_keys.py`
  imported by both Sentry inits (BL-056 surfaced and closed inline).
- ✅ `notify_admins_new_feedback` — surface'нулась как dead code (0
  callers); deleted целиком в 16.5a + grep guard.
- ✅ YooKassa webhook over-collection — closed 16.5c. Persist site
  router-level (`api/routers/billing.py:731` →
  `YookassaPayment.yookassa_metadata`). Resolution: canonical projection
  via `src/utils/yookassa_payload.py`; PII (customer email/phone, card
  fragments) и transport fields (recipient, payment_method, confirmation,
  merchant_customer_id) no longer persist.
- ✅ `src/bot/handlers/shared/login_code.py:50` plaintext one-time
  code logging — closed 16.5a (HIGH within LOW; auth-bypass surface).

**Closure summary (2026-04-30, series 16.x):** все 6 sub-tasks done.
- 16.5a: 4 sub-tasks (dead states, unused export, dead notify, plaintext code).
- 16.5b: 1 sub-task (Sentry parity, BL-056 surfaced + closed inline).
- 16.5c: 1 sub-task (YooKassa over-collection trim).

Backfill для existing rows pre-2026-04-30 surfaced как BL-059 (Phase 3
candidate, not blocking).

CHANGES reports: `CHANGES_2026-04-30_low-batch-16-5a.md`,
`CHANGES_2026-04-30_16-5b-pii-keys-canonical.md`,
`CHANGES_2026-04-30_16-5c-yookassa-canonical-projection.md`.

### BL-055 — Direct bot-to-portal ticket exchange (avoid mini_app intermediate)

**Status:** NEW, deferred (post-series 16.x)
**Surfaced in:** 16.3 closure отчёт; re-confirmed в 16.4 inventory.
**Severity:** Low (architectural improvement, not a fix)

**Context:** В 16.3 bot payout entry deeplink поведение было:

1. Bot inline button → `WebAppInfo(url=mini_app_url + "/own/payouts/request")`.
2. Mini_app screen `OwnPayoutRequest` (Phase 1 placeholder, no PII) →
   existing `exchange-miniapp-to-portal` call → portal redirect.

Это работает functionally, но добавляет mini_app в payout-setup flow как
intermediate redirect. Cleaner architecture: direct bot → portal path
через новый endpoint `/api/auth/exchange-bot-token-to-portal` который
verifies Telegram bot user_id (через bot token signing) и возвращает
ticket напрямую.

**Acceptance:**
- New endpoint `/api/auth/exchange-bot-token-to-portal` с Telegram-bot
  authentication (verify init data signature or bot context).
- Bot keyboard helper `build_portal_deeplink` calls this endpoint
  server-side, возвращает direct URL
  `<portal>/login/ticket?ticket=<jwt>&redirect=<path>`.
- Mini_app `OwnPayoutRequest` placeholder больше не required в payout flow.
- New endpoint pinned through аналогичный audit (Phase 1 PII rules).

**Why deferred:** не блокирует launch. Текущая реализация functionally
correct, mini_app в этом flow — pure redirect, no PII surface. Direct
exchange — это improvement, не fix.

**Pickup:** post-series 16.x.

### BL-056 — Sentry init PII keys: divergence between FastAPI and Celery

**Status:** Closed 2026-04-30 (16.5b, materialized inline)
**Surfaced:** 2026-04-29 (during 16.5b plan validation gate)
**Severity:** Low (operational hygiene; no live PII leak)

Two separate Sentry init callsites (`src/api/main.py` и
`src/tasks/sentry_init.py`) declared local PII keys literals для
denylist. Symmetric diff = 7 keys (5 missing in FastAPI + 2 extra:
`password`, `x-api-key` — legitimate HTTP-layer creds Celery не
имеет). Independent edits over time → unintentional drift.

**Resolution:** canonical extraction в `src/utils/pii_keys.py` —
18-key superset с category docstring (auth credentials / identity PII /
documents / payment). Both inits import canonical; local literals
removed (Case A — full removal). `log_sanitizer.py` оставлен с own
12-key list per CLAUDE.md NEVER TOUCH (sanitizer↔sentry asymmetry —
known-allowed condition, не drift).

**Tests:** 8 structure tests (`tests/unit/test_pii_keys_canonical.py`)
+ 3 behavioral smoke tests (`tests/unit/test_sentry_inits_use_canonical.py`).

CHANGES: `CHANGES_2026-04-30_16-5b-pii-keys-canonical.md`.

### BL-057 — Makefile lint/test split: verify gates де-факто были lint-only

**Status:** Closed 2026-04-30 (materialized inline)
**Surfaced:** 2026-04-30 (during 16.5b verify gate sweep)
**Severity:** Process-finding (no production impact, но verification
discipline gap)

`make ci-local` halted on 128 ruff baseline. Test phase **никогда не
выполнялся в CI gate** на этом repo. Все 16.x verify gates были
de-facto lint-only — claim "ci-local clean (only pre-existing
failures)" был misnomer. Behavioral coverage держался на manual
pytest каждой серии.

**Resolution:** split `ci-local` в 5 stages aggregate (check-forbidden,
lint, format-check, typecheck, test) через shell pattern. Exit code
non-zero если any stage failed, но не halts on first. Test phase
actually runs.

Standalone `make test` aligned via DRY recursion: ci-local зовёт
`$(MAKE) --no-print-directory test`. Identical output на обоих paths
(76 failed / 725 passed / 7 skipped / 17 errors baseline at time
of split, 736 passed после 16.5b merge, 753 passed после 16.5c merge).

**Lesson (process):** plan validation gate (g) — verify command
actually does what naming implies. Use `make -n` dry-run перед
declaring команду как gate.

CHANGES: `CHANGES_2026-04-30_makefile-split.md`.

### BL-058 — Ruff/format baseline cleanup batch

**Status:** SURFACED — deferred until series 16.x closure (recommended next mini-promt)
**Surfaced:** 2026-04-30 (visible после BL-057 split made baselines explicit)
**Severity:** Low (code hygiene, not behavioral)

После BL-057 ci-local actually exposed lint/format baselines:

- 128 ruff errors (mostly UP017, simple lint rules).
- 82 files needing `ruff format` (post-16.5c: was 83, billing.py
  incidental clean during 16.5c).

**Estimate:** ~1-2 hours mechanical. `ruff check --fix --select
<safe rules>` + `ruff format` сделают большую часть автоматически.
Manual review остатков.

**Why deferred:** mechanical scope, no domain decisions. After cleanup,
ci-local gates real clean (not "noisy baseline holds"). Cheap mechanical
win — recommended next step после series 16.x closure.

**Pickup:** standalone mini-promt; post-series 16.x.

### BL-059 — YookassaPayment retroactive PII minimization (backfill)

**Status:** SURFACED — Phase 3 candidate (legal compliance gates)
**Surfaced:** 2026-04-30 (during 16.5c implementation)
**Severity:** Medium (ФЗ-152 retroactive scope; depends on prod data state)

16.5c обрезает only **new** writes к
`YookassaPayment.yookassa_metadata` (BL-051 sub-task 6). Existing rows
persisted pre-2026-04-30 содержат полный YooKassa webhook payload
включая `receipt.customer.{full_name,inn,email,phone}`, card fragments
(`payment_method.card.{first6,last4}`), `recipient`/`payment_method`
internal IDs.

ФЗ-152 minimization recommends backfill для already-collected PII
once new collection is curtailed.

**Scope:** one-shot migration script через
`extract_persistable_metadata()` over all existing `YookassaPayment`
rows. ~20 min implementation.

**Pre-step requirement (Phase 3):** audit DB state — real customer
rows vs test/sandbox only. If only test rows — может skip с
documentation note. If real — backfill blocking Phase 3 legal gate.

**Why deferred:** natural fit с Phase 3 retention/legal review
(other PII data lifecycles will be assessed simultaneously). Avoiding
piecemeal backfill scripts.

**Refs:** BL-051 sub-task 6, 16.5c, ФЗ-152.

### BL-072 — Phase 3b Tier 1 production launch blockers (8 items)

**Status:** OPEN — production launch blocked until ALL Tier 1 resolved
**Created:** 2026-05-03
**Source:** Phase 3b closure audit `tmp/PHASE3B_CLOSURE_AUDIT_2026-05-03.md` D6 Tier 1

8 hard blockers — production launch CANNOT ship until ALL resolved.
Each requires Phase 3c / Phase 4 / Phase 5 work; none can be fixed inline
within current sub-block charter.

#### T1.1 — Phase 3c: PlacementTransitionService gate enforcement wiring

- **Status:** ✅ CLOSED (paper-only) — 2026-05-04
- **Resolution:** Phase 3c.1 commits `075637a` / `e71a676` /
  (3c.1.3 docs commit) on `feature/phase3c-transition-wiring`; merged
  to `develop` --no-ff.
- **Closure note:** Wiring is in place; AuditLog entry on decline; admin
  override remains universal carve-out; `bypass_gates: bool = False`
  flag for test/admin contexts. **HOWEVER** G07 PHASE4_PENDING marker
  fires on every `pending_owner | counter_offer → pending_payment`
  transition (Marina Q6=(a) accept-blocker decision); this constraint
  is removed only when Phase 4 (T1.6) ships G07 real body. Phase 3c
  closure is therefore "paper-only" — gate framework wiring is
  load-bearing, but production placement flow is **halted** at the
  payment step until Phase 4.
- **Source:** L39 (5b.7d closure)
- **Closure docs:** `CHANGES_2026-05-04_phase3c-1-transition-wiring.md`

#### T1.2 — Pre-existing test infrastructure debt (81 fails / 17 errors)

- **Status:** ✅ CLOSED — 2026-05-08
- **Resolution:** T1.2 series (sub-blocks T1.2.1 — T1.2.8) on
  `feature/t1-2-test-failures-cleanup`; merged to `develop` --no-ff,
  then `develop` → `main` --no-ff (atomic FE+BE deploy moment).
- **Closure metrics:** Pre-series baseline 81 fails / 17 errors (audit
  expansion to 99 entries during T1.2.0 probe). Post-series baseline
  **0 fails / 993 passing / 3 skipped / 0 errors** + 7 lint (intentional
  `tests/unit/conftest.py` asyncio policy ordering — BL-024 prohibits
  modification) + 0 format + 4 mypy (`mediakit_service.py` deferred per
  Q2=c — see BL-076).
- **Sub-block index (closure CHANGES files):**
  - T1.2.1 — auth refactor cleanup (`CHANGES_2026-05-04_t1-2-1-auth-refactor-cleanup.md`)
  - T1.2.2 — mechanical bulk + C16 (`CHANGES_2026-05-05_t1-2-2-mechanical-bulk-and-c16.md`)
  - T1.2.3 — audit_logs production fix (`CHANGES_2026-05-07_t1-2-3-audit-logs-production-fix.md`)
  - T1.2.4 — fixture decision (`CHANGES_2026-05-07_t1-2-4-fixture-decision.md`)
  - T1.2.4b — Pydantic Decimal + auth-DI refactor (`CHANGES_2026-05-07_t1-2-4b-decimal-and-auth-di.md`)
  - T1.2.5 Phase C-1 — surgical/wholesale deletes (`CHANGES_2026-05-07_t1-2-5-phase-c1.md`)
  - T1.2.5 Phase C-2 — surgical pruning (`CHANGES_2026-05-07_t1-2-5-phase-c2.md`)
  - D4 — admin_payouts test relocation to integration (`CHANGES_2026-05-07_d4-admin-client-relocation.md`)
  - T1.2.5e — payout dead-code cleanup (`CHANGES_2026-05-07_t1-2-5e-payout-cleanup.md`)
  - T1.2.5g — content_filter Mistral mock (`CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md`)
  - T1.2.6 — placement-flow cluster (`CHANGES_2026-05-07_t1-2-6-placement-flow-cluster.md`)
  - T1.2.7 — counter_offer cleanup (`CHANGES_2026-05-07_t1-2-7-counter-offer-cleanup.md`)
  - T1.2.8 — bot_factory cleanup (`CHANGES_2026-05-07_t1-2-8-bot-factory-cleanup.md`)
  - Master closure: `CHANGES_2026-05-08_t1-2-series-closure.md`
- **Production-code side effects (within T1.2 sub-blocks):** audit_logs
  production fix (action varchar(20) → varchar(64) + SAVEPOINT pattern in
  `AuditLogRepo.log` — T1.2.3), Pydantic Decimal 422 + `_resolve_user_for_audience`
  DI refactor (T1.2.4b), 11 dead `PayoutService` methods + 3 S-48 violations
  removed + `PayoutComplianceService` skeleton deleted (T1.2.5e), mini_app
  payout screens deleted (BL-055 redirect-only — T1.2.5e), `xp_service`
  Pattern 1 refactor (T1.2.4 C4), `ReputationAction` enum case fix
  (T1.2.6 Wave 0).
- **Note:** sub-block T1.2.5f (topup normalize — apply payout deeplink
  pattern to topup) deferred as separate future workstream pending Marina
  UX decisions. T1.2.4d (B3 full elimination of `async_session_factory()`
  outside `db/session.py`) deferred as separate future workstream.
- **Deferred items:** see BL-076 для consolidated list.
- **Source closures:** all 10 5b.X (relative-baseline-stability gate operational)

#### T1.3 — Phase 5: PayoutCompliance wiring at routers/payouts.py

- **Source:** Pre-closure audit O.7 / 5b.7b D4.11
- **Issue:** Today payout creation bypasses compliance entirely. No G06
  validation, no G13-G18 enforcement at create_payout. PayoutComplianceService
  skeleton exists (5b.7b) but registries empty + no callsite invokes it.
- **Note (per audit O.3):** until Phase 5 ships, `PayoutComplianceService`
  is "claimed but not enforced" — callers must use
  `LegalComplianceService.check_gate()` for any G13-G18 lookups. Do not
  treat half-baked PayoutCompliance service as enforced.
- **Compliance impact:** real payouts proceed without compliance check
- **Source closures:** `CHANGES_2026-05-03_phase3b-5b7b-payout-compliance-skeleton-idempotency.md`

#### T1.4 — G17 real body (счёт-фактура generation для legal_entity owners)

- **Source:** D4.04
- **Issue:** PHASE5_PENDING marker shipped 5b.6; real body Phase 5
- **Compliance impact:** НК РФ / Russian VAT compliance
- **Source closures:** `CHANGES_2026-05-03_phase3b-5b6-payout-gates.md`

#### T1.5 — G18 real body (real ORD provider; monthly turnover aggregation)

- **Source:** D4.05
- **Issue:** PHASE5_PENDING marker shipped 5b.6; real body Phase 5/6
- **Compliance impact:** ФЗ-38 advertising compliance
- **Source closures:** `CHANGES_2026-05-03_phase3b-5b6-payout-gates.md`

#### T1.6 — G07 real body (supplementary agreement КЭП verification, МES Acts API)

- **Source:** D4.01
- **Issue:** PHASE4_PENDING marker shipped 5b.7d; real body Phase 4
- **Compliance impact:** ГК РФ ст.432 / КЭП legal validity
- **Source closures:** `CHANGES_2026-05-03_phase3b-5b7d-marker-uniformization.md`

#### T1.7 — G15 real body (Act both-side КЭП verification)

- **Source:** D4.02
- **Issue:** PHASE4_PENDING marker shipped 5b.7d; real body Phase 4
- **Compliance impact:** КЭП crypto integration; Act signing legal validity
- **Source closures:** `CHANGES_2026-05-03_phase3b-5b7d-marker-uniformization.md`

#### T1.8 — G16 real body (Мой налог real receipt issuance)

- **Source:** D4.03
- **Issue:** PHASE4_PENDING marker shipped 5b.7d; real body Phase 4
- **Compliance impact:** ФЗ-Налог for self-employed
- **Source closures:** `CHANGES_2026-05-03_phase3b-5b7d-marker-uniformization.md`

**Refs:** Phase 3b closure batch (BL-073, BL-074); audit `tmp/PHASE3B_CLOSURE_AUDIT_2026-05-03.md`.

### BL-073 — Phase 3b Tier 2 production launch quality (7 items)

**Status:** OPEN — quality issues; не strict launch blockers, но required для ship
**Created:** 2026-05-03
**Source:** Phase 3b closure audit D6 Tier 2

#### T2.1 — DBSessionMiddleware explicit rollback path

- **Source:** D4.25 / 5b.7c O.3 (DEFERRED)
- **Issue:** `src/bot/middlewares/db_session.py:21-25` lacks `try/except`
  around handler invocation. On exception, `await session.commit()` doesn't
  run, but `async with async_session_factory()` exits via `__aexit__` →
  `session.close()` → SQLAlchemy 2.x async session implicit rollback. Works
  but asymmetric к `get_db_session` (which has explicit `try/except`).
- **Source closure:** `CHANGES_2026-05-03_phase3b-5b7c-s48-hygiene.md`

#### T2.2 — Pragmatic session.rollback() в bot handlers (S-48 contract tension)

- **Source:** D4.26 / 5b.7c O.5 (DEFERRED)
- **Issue per audit O.5 escalation:** Pattern 1 strict reading bans
  `session.rollback()` в handlers, но operational reality (next
  `session.execute()` raises `InFailedSQLTransactionError` after exception
  в nested op) makes it necessary. Confirmed sites: `arbitration.py:321,
  545`. Closure cites "multiple handlers".
- **Action required:** ESCALATED from "deferred to launch" → "S-48 contract
  decision needed before next bot-handler refactor session". Not a strict
  launch blocker per se, but a decision blocker для future bot handler work.
- **Source closure:** `CHANGES_2026-05-03_phase3b-5b7c-s48-hygiene.md`

#### T2.3 / T2.4 — payout_service.create_payout dead code + S-48 violation

- **Sources:** D4.14 + D4.15 / 5b.7a O.2/Q7 + 5b.7b O.H + 5b.7c
- **Issue:** Dead code (zero callers per 5b.7 A.5) + 3 S-48 violations
  (`async with session.begin()` at L513, L775, L840) поisoning sessions.
  NDFL/NPD/velocity/cooldown logic dead today — production path duplicates
  simpler version without those guards (ФЗ-Налог compliance gap для
  individual owners).
- **Action required per audit O.4:** "three sub-blocks have surfaced this;
  next time the file is touched, full cleanup is mandatory per L33 — not
  optional"
- **Source closures:** all three (5b.7a, 5b.7b, 5b.7c) — see L33 (5b.7b)

#### T2.5 — Frontend addPayout X-Idempotency-Key opt-in

- **Source:** D4.20 / 5b.7b O.G
- **Issue:** Client retry safety = 0 без header; UUID fallback safe-by-default
  but not full retry idempotency. `web_portal/src/api/payouts.ts:11` does
  NOT send header today.
- **Source closure:** `CHANGES_2026-05-03_phase3b-5b7b-payout-compliance-skeleton-idempotency.md`

#### T2.6 — YooKassa Payouts API key mapping (≤64 chars)

- **Source:** D4.23 / 5b.7b O.A
- **Issue:** Our key shape `payout_request:owner={user_id}:nonce={value}`
  ~70 chars > 64-char YooKassa Idempotence-Key limit. Phase 5 needs mapping
  table (hashing or shortening).
- **Source closure:** `CHANGES_2026-05-03_phase3b-5b7b-payout-compliance-skeleton-idempotency.md`

#### T2.7 — G06 provider-validated state

- **Source:** D4.06
- **Issue:** Current `owner_gates.py:check_g06` body checks DB-only
  (5b.7a real-now разморозка); Phase 5 swaps with provider validation
  (YooKassa Payouts recipient-check, SBP, BIK, OAuth).
- **Source closures:** 5b.7a + 5b.7b

**Refs:** Phase 3b closure batch (BL-072, BL-074); audit `tmp/PHASE3B_CLOSURE_AUDIT_2026-05-03.md`.

**Disposition 2026-05-08 (per "архитектурная чистота" review):**

- **T2.1** — DEFER post-launch closure batch (cosmetic asymmetry; implicit rollback works correctly via `__aexit__`).
- **T2.2** — ESCALATED to separate architectural decision session (S-48 contract tension; не code change item).
- **T2.3 / T2.4** — ABSORBED into Phase 4/5 PayoutCompliance recreation scope (dead code + 3 S-48 violations + ФЗ-Налог compliance gap для individual owners; L33 mandate full cleanup at next file touch).
- **T2.5** — ABSORBED into BL-081 launch hardening bundle (frontend addPayout X-Idempotency-Key opt-in).
- **T2.6** — DEFER to Phase 5 (already planned: YooKassa key mapping table).
- **T2.7** — DEFER to Phase 5 (already planned: G06 provider-validated state).

### BL-074 — Phase 3b Tier 3 deferred work (22 items)

**Status:** OPEN — deferred work; не pre-launch strict; eventual hardening
**Created:** 2026-05-03
**Source:** Phase 3b closure audit D6 Tier 3

#### Frontend

- **T3.1** — mini_app declined-channel UX deeplink (5b.7a)
- **T3.2** — web_portal channel-add error UI render `extra.blockers[]` (5b.7a)
- **T3.3** — `/payout-methods` portal route for G06 fail remediation_url (5b.7a)
- **T3.7** — Frontend `addChannel` mutation idempotency convention (5b.7a O.6)

#### Operational

- **T3.4** — Channel-add audit log retention policy (5b.7a)
- **T3.5** — `placement.py:305` retry-safety informational (5b.7c O.2)
- **T3.6** — Bot path `is_test` admin carve-out (5b.7a O.7)
- **T3.10** — G14 Acts pipeline alarming (proactive alarm; gate-time detection only today; 5b.6)

#### Phase 5 PayoutCompliance details (deferred с T1.3 wiring)

- **T3.12** — `_PAYOUT_GATE_CHECKERS` body fills (5b.7b)
- **T3.13** — `_PAYOUT_TRANSITION_GATES` table population (5b.7b)
- **T3.14** — `_PAYOUT_CREATE_GATES` table population (5b.7b)
- **T3.15** — `check_gates_for_payout_create` dispatch design (5b.7b O.I)
- **T3.16** — `PayoutRequest.placement_id` FK schema decision (5b.7b)

#### Documentation hygiene

- **T3.8** — Broader stale module-docstring sweep (5b.7d O.5; closure batch territory deferred)
- **T3.11** — Plan §3.B.1 terminology drift (resolved inline в closure batch via Q9; remaining sweep deferred)
- **T3.21** — `LegalProfileService.check_completeness` side-effects split (pure compute + write; 5b.3 L19)
- **T3.22** — Plan §3.B.6 admin test-mode carve-out language (resolved inline в closure batch via Q9; future plan revisions monitor)

#### Code hygiene (deferred)

- **T3.9** — 4 pre-existing ruff `src/` errors (`document_validation.py:107/263`,
  `channel_owner.py:82`, `placement_tasks.py:380`) — pre-existing, не Phase 3b debt
- **T3.17** — L20 dead code: skeleton `YandexOrdProvider` removal (`src/core/services/ord_yandex_provider.py`; real impl `yandex_ord_provider.py` per 5b.5 L20)
- **T3.18** — `_global_provider` module-state в `ord_service.py:48` (5b.5)
- **T3.19** — `OrdRegistration.status` String(20) → Enum migration (5b.5)
- **T3.20** — `Contract.contract_type` rename "advertiser_framework" → "framework" (5b.3 L18)

**Refs:** Phase 3b closure batch (BL-072, BL-073); audit `tmp/PHASE3B_CLOSURE_AUDIT_2026-05-03.md`.

**Disposition 2026-05-08 (per "архитектурная чистота" review):**

**Frontend:**
- **T3.1, T3.2, T3.3, T3.7** — ABSORBED into BL-081 launch hardening bundle.

**Operational:**
- **T3.4, T3.5, T3.6, T3.10** — DEFER post-launch (ops/admin tooling, не user-facing).

**Phase 5 PayoutCompliance:**
- **T3.12-T3.16** — DEFER to Phase 5 (already planned).

**Documentation hygiene:**
- **T3.8** — DEFER post-launch closure batch.
- **T3.11** — RESOLVED inline в Q9 closure batch (sweep deferred).
- **T3.21** — ABSORBED into BL-081 launch hardening bundle (compute/writes split refactor).
- **T3.22** — RESOLVED inline в Q9 closure batch.

**Code hygiene:**
- **T3.9** — FOLD into next T1.2.x cleanup commit (4 pre-existing ruff `src/` errors).
- **T3.17** — CLOSED by 5b.5 / BL-080 absorbs (yandex skeleton dead code).
- **T3.18** — ABSORBED into BL-080 scope expansion (`_global_provider` module-state).
- **T3.19** — ABSORBED into BL-080 scope expansion (`OrdRegistration.status` enum migration).
- **T3.20** — ABSORBED into BL-081 launch hardening bundle (`Contract.contract_type` rename).

### BL-075 — `_TRANSITION_GATES` does not enforce G01-G06 at any placement transition

**Status:** OPEN — Tier 2 (quality / architectural completeness gap)
**Created:** 2026-05-04
**Source:** Phase 3c Phase A+B investigation O.2

**Statement:** `_TRANSITION_GATES` (populated 5b.2) currently maps `(from, to)`
pairs only to G07-G12. G01-G06 (advertiser/owner legal profile, framework
contract, payout method) are enforced ONLY at channel-add (5b.7a
`_USER_GATE_CHECKERS`), NOT at any placement transition. Implication: an
advertiser without a legal profile or framework contract can create a
placement and transition it through escrow / published; only G07
PHASE4_PENDING marker blocks `pending_payment`, but advertiser-side
compliance is **not** verified at transition-time. Owner side is
verified at channel-add — but if owner status drifts later (e.g.,
contract revoked, payout method invalidated) the placement transitions
proceed without re-validation.

**Closure trigger:** dedicated future sub-block expanding
`_TRANSITION_GATES` for G01-G06 inclusion at appropriate transitions.
Suggested initial mapping (Marina decision required):

- `pending_owner → pending_payment`: add `{G01, G02, G03, G07}` for
  advertiser side (so missing legal profile blocks payment, not only
  G07 marker).
- `created → pending_owner` (if added to allow-list): may require
  `{G04, G05, G06}` for owner side.

**Compliance impact:** ФЗ-152 / ГК РФ ст.432 — advertiser without legal
profile or framework contract should not be able to fund placements;
current Phase 3c wiring catches this only at channel-add for owners.

**References:**
- `tmp/PHASE3C_INVESTIGATION_2026-05-04.md` O.2
- `CHANGES_2026-05-04_phase3c-1-transition-wiring.md` (Phase 3c closure)
- 5b.2 closure (table populated):
  `CHANGES_2026-05-02_phase3b-5b2-gate-resolution.md`

**Refs:** Phase 3c closure (BL-072 T1.1).

### BL-076 — T1.2 series test cleanup deferred items

**Status:** OPEN — accumulated deferred entries from T1.2.1 — T1.2.8 sub-blocks
**Created:** 2026-05-08 (T1.2 series closure batch)
**Source:** consolidated `## Deferred to production launch` / `## Deferred to BACKLOG` sections from all T1.2 sub-block CHANGES files

T1.2 series closed pre-existing test infrastructure debt (99 audit entries
→ 0F / 993P / 3S / 0E baseline). During the series, sub-blocks surfaced
production-bugs, architectural cleanups, and coverage gaps that were
explicitly carved out of T1.2 cleanup scope. Per project closure policy
(no inline BACKLOG commits during sub-block work), entries accumulate
here.

#### T1.2-D1 — `mediakit_service.py` stale fields production bug

- **Surface:** T1.2.2 C10, T1.2.4 Q3=a, T1.2.5e Q2=c
- **Source CHANGES:**
  - `CHANGES_2026-05-05_t1-2-2-mechanical-bulk-and-c16.md`
  - `CHANGES_2026-05-07_t1-2-4-fixture-decision.md`
  - `CHANGES_2026-05-07_t1-2-5e-payout-cleanup.md`
- **Issue:** `src/core/services/mediakit_service.py:111-116` reads
  `chat.last_avg_views`, `chat.last_post_frequency`, `chat.price_per_post`.
  Model side migrated:
  - `chat.last_avg_views` → `chat.avg_views` (`TelegramChat:54`)
  - `chat.last_post_frequency` → field removed entirely (no synonym)
  - `chat.price_per_post` → `chat.channel_settings.price_per_post`
    (moved to ChannelSettings)
- **Symptom:** `mediakit_service.get_mediakit_data()` raises AttributeError
  at runtime; surfaces 4 mypy errors (residual T1.2 baseline).
- **Companion test:** `tests/test_bmediakit_comparison.py::TestMediakitService::test_get_mediatkit_data` SKIPPED with refreshed pointer
  to BACKLOG.
- **Investigation options:**
  - (a) Compute from existing fields (`avg_views` exists; derive
    `last_post_frequency` from publication history)
  - (b) Drop dead code path entirely (mediakit feature may not be
    production-bound)
  - (c) Add fields with migration
- **Priority:** medium — runtime AttributeError under any caller. Marina
  decision required before scope.
- **CLOSED 2026-05-11** via BL-078 Phase B execution. Path (a)
  compute-from-existing-fields chosen: `MediakitService.get_mediakit_data`
  reads `chat.avg_views` directly + derives `post_frequency` from
  `PlacementRequest` count over 30-day window
  (`POST_FREQUENCY_WINDOW_DAYS = 30` module constant) + reads
  `price_per_post` from `chat.channel_settings` (via `selectinload`).
  4 mypy errors eliminated. Test `test_get_mediakit_data` un-skipped via
  fix-forward в B.3. See `CHANGES_2026-05-11_bl-078-b1-mediakit-service-rewrite.md`
  + `CHANGES_2026-05-11_bl-078-b3-tests-and-counter-refactor.md`.

#### T1.2-D2 — `tests/unit/conftest.py` 7 lint suppression

- **Surface:** T1.2.5e Q1=a (deferred to T1.2 closure or dedicated sub-block)
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5e-payout-cleanup.md`
- **Issue:** 7 ruff errors in `tests/unit/conftest.py` (1× SIM105 line 12 +
  6× E402 lines 20-26) accepted as known residual. Errors are intentional
  asyncio policy ordering (must precede aiogram imports); BL-024 prohibits
  modification of `tests/unit/conftest.py` core logic.
- **Suppression options:**
  - (a) Add `# ruff: noqa: E402, SIM105` shim at file top — single line,
    preserves logic intact, lint baseline → 0
  - (b) Reshape asyncio policy ordering pattern — bigger refactor
- **Priority:** low — cosmetic baseline cleanup; no functional impact.

#### T1.2-D3 — PayoutComplianceService recreation для Phase 5 / 5b.7

- **Surface:** T1.2.5e (skeleton deletion in `17d8f1f`)
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5e-payout-cleanup.md`
- **Issue:** 5b.7b SKELETON deleted in `refactor(payout): delete
  PayoutComplianceService skeleton + clean stale comments`. Empty
  registries (`_PAYOUT_TRANSITION_GATES`, `_PAYOUT_CREATE_GATES`) and zero
  production callers. Phase 5 / 5b.7 implementor must recreate with:
  - G13-G18 transition resolver
    (publication_period_elapsed → act_generated → act_signed →
    tax_receipt → vat → ord_reported)
  - Create-time gate registry для payout-request creation
  - Same dispatch architecture as `LegalComplianceService` (sibling coordinator)
- **Reference:** `git show 17d8f1f^:src/core/services/payout_compliance_service.py`
  для original structure. Test reference:
  `git show 17d8f1f^:tests/unit/test_payout_compliance_service.py`.
- **Note:** gate-checker bodies в `src/core/services/gates/payout_gates.py`
  (G13-G18) intact and should be wired into the new coordinator's
  transition resolution table.
- **Priority:** high — required for Phase 5 payout compliance enforcement
  (T1.3 / BL-072 T1.3 dependency).

#### T1.2-D4 — AUDIT-LOG-1: SAVEPOINT pattern audit across other side-effect repos

- **Surface:** T1.2.3 (audit_logs production fix)
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-3-audit-logs-production-fix.md`
- **Issue:** `AuditLogRepo.log` now wraps writes in SAVEPOINT
  (`session.begin_nested()`) — the originally-intended fire-and-forget
  semantics. Audit other "best-effort" side-effect writes to verify
  they don't share the same broken Python-except-only pattern that
  T1.2.3 surfaced.
- **Candidate scan target:** any repo method whose docstring claims
  "fire and forget" or "never blocks" without a SAVEPOINT wrap.
- **Priority:** medium — latent risk surface; may hide identical
  poisoned-transaction failure modes downstream of other failed writes.

#### T1.2-D5 — AUDIT-LOG-2: Action vocabulary documentation

- **Surface:** T1.2.3
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-3-audit-logs-production-fix.md`
- **Issue:** `audit_logs.action` column was originally designed as a
  4-value enum (READ/WRITE/DELETE/ADMIN_READ); vocabulary has grown
  organically to 12 values. Consider documenting the action taxonomy or
  formalizing as a Postgres ENUM in a future migration once vocabulary
  stabilizes.
- **Priority:** low — documentation hygiene; no functional impact.

#### T1.2-D6 — `constants/content_filter.py` drift

- **Surface:** T1.2.5g
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md`
- **Issue:** `src/constants/content_filter.py` declares
  `LEVEL2_THRESHOLD = 0.3`, `LEVEL3_THRESHOLD = 0.5`, but `filter.py`
  overrides к `0.15 / 0.7`. Constants file unused (verified: not imported
  by `filter.py`).
- **Investigation options:** либо delete file (preferred), либо align
  values + import-from-constants pattern. Surface only — не related к
  flake.
- **Priority:** low — drift hygiene; values are correctly applied
  inline in `filter.py`.

#### T1.2-D7 — `MistralAIService.moderate_content` blanket-except production-bug surface

- **Surface:** T1.2.5g
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md`
- **Issue:** `mistral_ai_service.py:194-252` catches ВСЕ `Exception`
  types и returns
  `MistralModerationResult(passed=True, score=0.0, categories=[], analysis="")`
  fallback. Создаёт second failure mode для `test_check_blocked_text`
  beyond L3 timeout.
- **Investigation:** должен ли catch только specific exceptions (rate
  limit, network, parse)? Sentry capture без silent fallback?
  Production behavior implication — fail-open поведение для blanket
  exceptions может пропускать blocked content при transient backend
  issues.
- **Priority:** medium — fail-open security implication for content
  moderation pipeline.

#### T1.2-D8 — Future LLM-test marker convention (YAGNI)

- **Surface:** T1.2.5g
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md`
- **Issue:** Future LLM-dependent tests should use the same `(a.1) inline
  patch` pattern adopted in T1.2.5g. Marker convention (e.g.
  `@pytest.mark.requires_external_llm`) deferred until second LLM-test
  surface emerges.
- **Priority:** low — YAGNI; revisit when 2nd LLM-test surface appears.

#### T1.2-D9 — Coverage for current FSM topology (replaces deleted C3 internal tests)

- **Surface:** T1.2.5 Phase C-2
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5-phase-c2.md`
- **Issue:** C3 surgical removed 9 tests asserting internal FSM topology
  elements (state names, middleware constants, init signatures). Public
  surface coverage (FSM transition behavior, throttling effect, admin
  filter gating) is NOT covered by surviving tests (which only verify
  imports work).
- **Future sub-block:** behavioral tests on FSM transitions + middleware
  effects.
- **Priority:** medium — coverage gap on FSM behavior.

#### T1.2-D10 — Coverage for current `cmd_start` / `cb_tos_*` / `go_to_*_menu` public surface (replaces deleted C2 internal tests)

- **Surface:** T1.2.5 Phase C-2
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5-phase-c2.md`
- **Issue:** C2 surgical removed 11 tests on `_handle_start` /
  `safe_callback_edit` / `async_session_factory` (all internal helpers).
  Public entry points (`cmd_start` command handler, `cb_tos_accept` /
  `cb_tos_decline` callback handlers, role-selection callback handler)
  have NO behavioral test coverage post-deletion. Surviving tests cover
  only role validation constants + callback string format.
- **Priority:** medium — first-touch user flow has zero behavioral
  coverage.

#### T1.2-D11 — Gamification coverage (replaces deleted C4 internal tests)

- **Surface:** T1.2.5 Phase C-2
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5-phase-c2.md`
- **Issue:** If production has live gamification logic
  (`src/tasks/gamification_tasks.py`, `src/tasks/badge_tasks.py`,
  `src/core/services/badge_service.py`), fresh tests against actual
  current surface would close coverage gap.
- **Priority:** low — gamification is feature-flag-able; revisit when
  feature is production-bound.

#### T1.2-D12 — `MistralAIService` unit test coverage

- **Surface:** T1.2.5 Phase C-1, Phase C-2 (carried)
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-5-phase-c1.md`,
  `CHANGES_2026-05-07_t1-2-5-phase-c2.md`
- **Issue:** Coverage for current
  `src/core/services/mistral_ai_service.py` deleted along with
  `tests/unit/test_ai_service.py` (C1). Resurrection = rewrite from
  scratch against actual public surface. Out of T1.2 cleanup scope.
- **Priority:** medium — moderation L3 surface lacks unit-level
  coverage post-cleanup.

#### T1.2-D13 — Project-wide `__init__.py` audit (L61 follow-up)

- **Surface:** D4 (admin_payouts relocation)
- **Source CHANGES:** `CHANGES_2026-05-07_d4-admin-client-relocation.md`
- **Issue:** Pytest «sub-package without parent» collision (L61)
  surfaced when adding `tests/integration/api/__init__.py` triggered 9
  ModuleNotFoundError on existing `tests/unit/api/test_*.py` files. Root
  cause: `tests/unit/` had no `__init__.py` while `tests/unit/api/` did
  — pytest `prepend` import mode registered `tests/unit/api/test_*` as
  top-level package `api`, conflicting when `tests/integration/api/`
  added the same name.
- **Audit candidate:** check `tests/<layer>/<subdir>/__init__.py` chain
  для other sub-package-without-parent collisions waiting for trigger.
  E.g. `tests/unit/services/__init__.py` без `tests/unit/__init__.py` =
  same problem class.
- **Long-term option:** switch `pyproject.toml` pytest addopts к
  `--import-mode=importlib` — modern pattern избегает namespace fights
  целиком, но требует separate validation pass.
- **Priority:** low — latent bug, only fires when adding new test
  directories with conflicting names.

#### T1.2-D14 — `test_review_service.py` local fixtures cleanup (BL-022 legacy)

- **Surface:** T1.2.6
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-6-placement-flow-cluster.md`
- **Issue:** `tests/unit/test_review_service.py` defines local
  `db_session` (Postgres-backed override of SQLite default), `advertiser`
  (telegram_id 900111001), `owner` (telegram_id 900111002), `channel`,
  `published_placement` fixtures. These duplicate root
  `tests/conftest.py` fixtures (`advertiser_user`, `owner_user`,
  `test_channel`). Heritage of BL-022 SQLite-shadow refactor — local
  fixtures were added when file inherited SQLite db_session from
  `tests/unit/conftest.py`. Now that file overrides к Postgres, root
  fixtures could be reused, но это broader refactor (~30-50 LOC).
- **Priority:** low — duplication / hygiene; no functional impact.

#### T1.2-D15 — ESCROW invariant evolution (allowlist maintenance)

- **Surface:** T1.2.6
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-6-placement-flow-cluster.md`
- **Issue:** Текущий `test_release_escrow_only_in_approved_callsites`
  allows 2 callsites (`publication_service.py` + `disputes.py`). If в
  Phase 4/5 будут добавлены legitimate callsites (e.g.
  PayoutComplianceService bulk-release flow, refund_escrow inverse),
  allowlist должен быть updated. Test docstring documents the invariant
  maintenance requirement; future updates per architectural changes.
- **Priority:** documentation — invariant is maintained, this is a
  pointer для future refactor authors.

#### T1.2-D16 — Counter-offer flow gate-enforcement coverage

- **Surface:** T1.2.7
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-7-counter-offer-cleanup.md`
- **Issue:** If broader integration tests are required для verifying
  production legal-compliance flow (i.e. NOT bypassing gates), need test
  fixture creating real `Contract` + `SupplementaryAgreement` records
  satisfying G07. Out of T1.2.7 scope. Recorded для test-health epic
  Phase 4 backlog.
- **Priority:** medium — depends on Phase 4 G07 real body landing
  (T1.6 / BL-072 T1.6).

#### T1.2-D17 — Test infra debt: `PlacementRequestService` boilerplate (T1.2.7) + `_reset_factory` autouse (T1.2.8)

- **Surface:** T1.2.7, T1.2.8
- **Source CHANGES:**
  - `CHANGES_2026-05-07_t1-2-7-counter-offer-cleanup.md`
  - `CHANGES_2026-05-07_t1-2-8-bot-factory-cleanup.md`
- **Issue (T1.2.7):** Both test methods construct `PlacementRequestService`
  inline с identical 4-arg invocation. Could be extracted к shared
  fixture. Out of scope (KISS).
- **Issue (T1.2.8):** Tests call `_reset_factory()` в
  `setup_method`/`teardown_method` для clear singleton state. Could be
  elevated к pytest fixture с autouse.
- **Priority:** low — DRY / hygiene improvements; functional behavior
  intact.

#### T1.2-D18 — Bot factory invariant INV-3 lint enforcement

- **Surface:** T1.2.8
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-8-bot-factory-cleanup.md`
- **Issue:** Per `src/bot/session_factory.py` docstring: `Bot()` is
  created only в `session_factory.py` и `_bot_factory.py` (which
  delegates). If new direct callsites появляются, INV-3 invariant broken.
  Could be enforced via lint (similar к ESCROW-001 в
  `tests/unit/test_release_escrow_callsites.py` from T1.2.6).
- **Priority:** medium — invariant currently relies on docstring +
  reviewer attention; lint promotion would lock the contract.

#### T1.2-D19 — `xp_service` helpers Pattern 2 sweep candidate

- **Surface:** T1.2.4 (carried beyond Q6=(i') scope)
- **Source CHANGES:** `CHANGES_2026-05-07_t1-2-4-fixture-decision.md`
- **Issue:** `badge_service.award_badge` is also Pattern 2 (opens own
  session via `async_session_factory`). Out of T1.2.4 Q6=(i') scope.
  Future S-48 sweep candidate.
- **Priority:** low — operational; Pattern 2 self-contained correctness
  preserved (commits with `# S-48: self-contained pattern` marker).

**Refs:** T1.2 series closure (BL-072 T1.2 closed — see
`CHANGES_2026-05-08_t1-2-series-closure.md`).

### BL-077 — Middleware registration: specific observers vs `dp.update`

**Status:** OPEN — engineering practice / pre-PR check guidance
**Created:** 2026-05-08
**Source:** T1.2.5f post-Phase-C live debug (commit `f82852d`, v0.5.2 release)

**Lesson:** aiogram middleware can be registered на
`dp.update.middleware()` (receives все `Update` events) или specific
observers (`dp.message.middleware()`, `dp.callback_query.middleware()`,
etc.). Registration target must match what middleware logic expects.

**Symptom (silent failure mode):** middleware uses
`isinstance(event, Message)` / `isinstance(event, CallbackQuery)` checks,
но registered на `dp.update.middleware()` → checks always evaluate False
(Update is not Message/CallbackQuery) → middleware silently swallows
updates без error. Affected users get no response, никакого log entry
кроме generic "Update is not handled" warning.

**Pre-existing instance (fixed):** `AcceptanceMiddleware` (commit
`f82852d`) — was registered на `dp.update.middleware()` но использовал
Message / CallbackQuery isinstance checks. Result: users без
`terms_accepted_at` flag completely locked out (не могли reach /start
handler nor see acceptance prompt).

**Recommended pre-PR check для future middleware:**

1. Если middleware uses `isinstance(event, ConcreteType)` — register на
   matching observer (`dp.<type>.middleware()`), не
   `dp.update.middleware()`.
2. Если middleware needs Update-level access — accept Update event
   explicitly, без isinstance check downstream.
3. Add unit test asserting handler runs after middleware passes through
   (не только middleware logic в isolation). E.g. fake exempt update +
   verify handler invoked.

**Files exemplifying correct pattern post-fix:**

- `src/bot/main.py` — `AcceptanceMiddleware` теперь на
  `dp.message.middleware()` + `dp.callback_query.middleware()`
  (event-type-specific).
- Other middlewares (DBSession, Throttling, FSMTimeout, RoleCheck) на
  `dp.update.middleware()` — они event-type-agnostic by design, не
  затронуты.

**Priority:** medium — passive check для new middleware additions; не
blocks current work.

**Refs:** AcceptanceMiddleware fix `f82852d`; CHANGELOG `[v0.5.2]` Fixed
section; `CHANGES_2026-05-08_t1-2-5f-topup-normalize.md` (middleware fix
appended via commit `fa85a38`).

### BL-078 — Mediakit feature полная реализация

**Status:** IN-PHASE-CLOSED 2026-05-11 — Phase B implementation complete (B.1-B.6.2 closure batch). Residual polish tracked under BL-086 (logo resolver), BL-087 (theme_color tinting). Phase 8 may revisit для deeper feature work.
**Created:** 2026-05-08

**Surface:** BL-076 probe report `tmp/bl076_mediakit_probe.md`. Schema `channel_mediakits` (`0001_initial_schema.py:586-628`, fields: `owner_user_id`, `logo_file_id`, `theme_color`). `MediakitService` + `mediakit_pdf.py` существуют как orphan stubs без production callers (zero refs в `src/api/routers/`, `src/bot/handlers/`). `ChannelService.get_or_create_mediakit` / `update_mediakit` — duplicate dead surface (lines 89-122).

**Issue:** Owner-side artifact — брендированный PDF канала (logo + theme color + статистика канала + цены) для отправки рекламодателю как portfolio. Ранний concept без API/UI integration. Текущий код out of sync с current schema:

- `chat.last_avg_views` → `chat.avg_views` (`telegram_chat.py:54`)
- `chat.last_post_frequency` → field удалён (need derive from publication history)
- `chat.price_per_post` → `chat.channel_settings.price_per_post` (`channel_settings.py:24`, relationship `telegram_chat.py:74`)

**Decision (Marina, 2026-05-08):** Path (a) full rewrite — dead code на launch несовместим с архитектурной чистотой. Schema invested + feature имеет owner-side business value. ChannelService duplicate methods (`get_or_create_mediakit` / `update_mediakit`) **deleted** as part of BL-078 — single canonical surface через MediakitService.

**Scope:**

- **Service rewrite** в `MediakitService` — data assembly с current schema. `post_frequency` derived from `PublicationLog` history (count posts в окне N days).
- **API endpoint:** `GET /api/channels/{id}/mediakit/pdf` (owner-only, ownership check).
- **PDF rendering:** logo (resolve `logo_file_id` → file storage), theme color (`theme_color` accent), stats block, sample posts (optional sub-block). Use existing PDF generation pattern (act/contract templates как modeled).
- **UI web_portal:** `web_portal/src/screens/owner/ChannelMediakit.tsx` + download button на `OwnChannels` channel detail.
- **UI mini_app:** read-only preview card. PDF download только через web_portal — bot/web split convention (mobile clients render PDF poorly + report lab is server-side). NO ФЗ-152 implication — mediakit content carries no PII.
- **ChannelService cleanup:** `get_or_create_mediakit` + `update_mediakit` методы **deleted** (duplicate dead surface, replaced by MediakitService).
- **Schema:** existing `channel_mediakits` table — no migration needed (pre-existing, BL-061 forward-only respected).

**Acceptance:**

- Owner может скачать брендированный PDF канала через web_portal.
- BL-076 T1.2-D1 closed (4 mypy errors gone, schema-code drift resolved).
- `tests/test_bmediakit_comparison.py::test_get_mediatkit_data` un-skipped + passing с rewritten service.
- Existing analytics screen (S-47, `/analytics`) untouched.
- ChannelService.get_or_create_mediakit / update_mediakit **gone** (verified via grep).

**Compliance impact:** none. Mediakit content (logo + theme + channel stats + price) carries no PII. ФЗ-152 не релевант.

**Priority:** medium-high — launch prerequisite per архитектурная чистота policy (dead code unacceptable on launch).

**Blocks:** none.

**Closes:** BL-076 T1.2-D1 (when BL-078 ships).

**Deadline:** Phase 8 (new — Creative content lifecycle, см. plan placement note).

**References:**

- `tmp/bl076_mediakit_probe.md` — probe findings (input для design).
- BL-076 T1.2-D1 — current dead code surface (will be edited to "stale dead-code drift" wording when BL-078 lands).
- `0001_initial_schema.py:586-628` — `channel_mediakits` table.
- `tests/test_bmediakit_comparison.py:108-114` — skip reason update needed.

---

### BL-079 — Campaign creation media file upload (UI/feature gap)

**Status:** OPEN — launch prerequisite (Marina decision O5, 2026-05-08).
**Created:** 2026-05-08

**Surface:** Marina observation 2026-05-08 — campaign creation wizard содержит toggle "добавить медиафайлы" (фото/видео), но поле для upload отсутствует. Switcher либо dead UI, либо partial implementation в early phase.

**Issue:** Advertiser создаёт campaign, видит option "с медиа", но не может прикрепить файл. User expectation broken. Publication composes plain-text post, media never persisted.

**Scope to investigate (probe required first — Phase 8.B Agent A):**

- Identify switcher source: `web_portal/src/screens/advertiser/campaign/*.tsx` (likely `CampaignText.tsx` или wizard step), mini_app analog.
- Determine current state — is media field hidden behind switcher, or absent entirely? Is switcher wired anywhere?
- DB schema audit: `placement_request.media_files` (или similar) — exists?
- Telegram Bot API publication: `send_photo` / `send_video` / `send_media_group` requirements + caption length limits (1024 chars vs 4096 plain text).

**Design decisions (decided ahead — not deferred to probe):**

- **Storage backend (default):** S3/MinIO/local volume с copy strategy. **Telegram file_id passthrough explicitly NOT recommended** — file_ids are bot-scoped (different bots can't access each other's IDs), can become invalid (rare but documented), break ФЗ-38 audit retention если original message deleted.
- **Media + ERID composition:** decided в BL-080 design (caption budget edge case — BL-080 scope item).

**Implementation scope:**

- DB migration (если нужна — `placement_request.media_attachments` table или `media_files` JSONB).
- Storage service abstraction (`src/core/services/media_storage.py` или extend existing).
- Upload endpoint: `POST /api/placements/{id}/media` (multipart) или separate `POST /api/media/upload` returning file IDs.
- UI field в campaign wizard step (web_portal + mini_app where allowed).
- Publication composition: media + marked text (per BL-080 decision на caption budget).
- Audit trail: media files reference в `placement_status_history.metadata_json` или dedicated `media_audit_log`.
- File validation: size limits, allowed extensions (`.jpg`, `.png`, `.mp4`, etc.), virus scanning policy (defer to ops если не in stack).

**Acceptance:**

- Advertiser uploads фото/видео в campaign creation wizard.
- Files persist в configured storage backend.
- Publication composes media + marked text согласно BL-080 caption budget decision.
- Integration test: campaign created с media → `send_photo/video/media_group` called с правильными args + ERID disclaimer.
- ФЗ-38 audit retention: media file retrievable post-publication. **Retention period defined per ФЗ-38 / ОРД tech spec** (typical 1 year for advertising materials — exact requirement confirmed during probe + storage policy aligned).

**Compliance impact:**

- **ФЗ-38** — рекламные креативы с media require ОРД маркировку. Interaction details — BL-080 design item.
- **ФЗ-152** — applies **conditionally**: если uploaded media содержит identifiers of natural persons (faces, names, contact info), требуется storage encryption + access control + retention policy. Pure-product creatives (product photo, brand asset без people) — standard business-asset handling sufficient. Probe-time classification required (per upload metadata flag или per campaign settings).

**Priority:** high — launch prerequisite (Marina decision O5).

**Blocks:** none.

**Blocked by:** BL-080 (ERID flow) — нужен caption budget decision + composition pattern перед implementation.

**Deadline:** Phase 8 (new — Creative content lifecycle).

**References:**

- Marina observation 2026-05-08.
- `IMPLEMENTATION_PLAN_ACTIVE.md` Phase 6.B.3 — ORD hardening (BL-080 dependency).
- Telegram Bot API docs: caption length 1024, text 4096.

---

### BL-080 — ERID marking flow completion + Phase 6.B.3 scope additions

**Status:** OPEN — launch prerequisite (ФЗ-38 legal compliance).
**Created:** 2026-05-08

**Surface:** Marina observation 2026-05-08 — flow с маркированием ERID не полностью проработан. `StubOrdProvider` + `YandexOrdProvider` существуют, `_build_marked_text` есть в `publication_service.py:106`, но end-to-end gaps remain.

**Issue:** ОРД (Оператор Рекламных Данных) integration частично implemented:

- Provider abstraction есть (`OrdProvider` protocol).
- ERID registration через `ord_service.py`.
- Marked text composition через `_build_marked_text`.
- Phase 6.B.3 (existing plan slot) covers: `ord_provider` literal, deterministic block logic, `_build_marked_text` rewrite, gate G08 alignment, КЭП fallback.

**Phase 6.B.3 already covers (no need to duplicate в BL-080):**

- `ord_provider: Literal["stub", "yandex", "vk", "ozon"]` в settings.
- Removal `ord_block_publication_without_erid` в favor deterministic logic.
- `_build_marked_text` block-on-no-erid for non-stub providers.
- Gate G08 deterministic alignment.

**BL-080 scope = scope additions to Phase 6.B.3 + dead code cleanup. Не duplicate existing plan items, а extend.**

**Scope items (BL-080 specific):**

1. **Duplicate yandex provider cleanup** (closes BL-074 T3.17). Two files exist: `src/core/services/ord_yandex_provider.py:13` (skeleton) + `src/core/services/yandex_ord_provider.py:36` (real impl per 5b.5 L20). **Both define `class YandexOrdProvider(OrdProvider)`** — same name, two implementations. Whichever import path runs first wins, the other shadowed silently. **Delete `ord_yandex_provider.py`** (skeleton) — keep `yandex_ord_provider.py` as canonical. Closes BL-074 T3.17.

2. **Caption budget design (media + ERID composition).** Telegram limits: 4096 chars text-only, 1024 chars media caption. ERID disclaimer (`Реклама. {advertiser_name}\nerid: {token}`) + ad text + URL fits 4096 comfortably but easily overruns 1024 в caption. Design decision (impacts BL-079):
   - **Option A:** Caption с truncated ad text + full ERID disclaimer (preserves legal marker, sacrifices content).
   - **Option B:** Separate text message under media (`send_media_group` then `send_message` reply-to) — preserves content + marker. **Requires ОРД legal review** — ФЗ-38 + ОРД technical spec typically require marker visible together с advertising creative within same publication unit. Separate message может быть legally separable from creative + Telegram readers can miss second message (mobile UX, scroll ordering). Decision must NOT be made on UX/cost grounds alone.
   - **Option C:** Media-with-text composition pattern (`InputMediaPhoto.caption` constrained, follow-up message с ERID).
   - **Decision required при probe** — affects user expectations, Telegram delivery cost, ФЗ-38 marker placement compliance.

3. **ERID idempotency on retry.** Re-calling provider on retry may double-register same creative (different ERIDs returned for what is logically one ad). Provider may or may not enforce idempotency upstream. Implementation: stable internal `idempotency_key` per creative + EXISTS-check pattern (mirror of S-48 financial transactions). Update `ord_service.py` register call с idempotency guard.

4. **Registration retry policy.** Define max attempts, backoff, escalation path. `ord_blocked` status recovery: admin override через Phase 5 mechanism + retry button.

5. **Audit trail completion (split per agent O3):**
   - **(a)** Verify `OrdRegistration` model captures full event history (request payload, response, ERID, timestamp, attempt number).
   - **(b)** Link `OrdRegistration` ↔ `placement_status_history` via `placement_id` + `correlation_id` для cross-domain debugging.

6. **Failure paths enumeration:** provider down, ERID rejected, registration timeout, marking errors. Each requires explicit status + recovery path.

7. **Media-aware marking** (interaction with BL-079): how ERID disclaimer renders когда post содержит media. См. item 2 above (caption budget design).

**Scope expansion 2026-05-08 (BL-074 disposition review):** absorbs BL-074 T3.18 (`_global_provider` module-state в `src/core/services/ord_service.py:48` cleanup) + T3.19 (`OrdRegistration.status` String(20) → Enum migration). Natural fit с ERID flow completion / ord_service touchpoints.

**Phase A research scope:**

- Read full ERID flow: `publication_service.py:_build_marked_text:106`, `ord_service.py`, `ord_yandex_provider.py`, `yandex_ord_provider.py`, `stub_ord_provider.py`, `OrdProvider` protocol.
- Cross-reference Phase 6.B.3 plan — gap delta between plan + BL-080 additions.
- ФЗ-38 + ОРД technical spec compliance check (gap analysis vs requirements).
- Test coverage audit: `test_ord_*`, `test_publication_*` — gaps.

**Acceptance:**

- Single `YandexOrdProvider` class (one file, skeleton deleted).
- Caption budget design decision recorded + implemented.
- ERID registration idempotent on retry (no double-registration).
- Retry policy + recovery paths defined and tested.
- `OrdRegistration` audit trail complete + linked to placement_status_history.
- Integration test: full ERID flow including failure paths.
- Phase 6.B.3 acceptance items + BL-080 items both pass.

**Compliance impact:** **HIGH** — ФЗ-38 рекламное законодательство. Publication без verified ERID = legal risk. Marker placement must comply с ОРД technical spec.

**Priority:** high — launch blocker (legal compliance).

**Blocks:** BL-079 (campaign media upload — requires media+ERID composition decision from item 2).

**Closes:** BL-074 **T3.17 sub-item** (yandex provider skeleton deletion). Parent BL-074 остаётся OPEN с T2.3 / T2.4 / T3.18 / T3.19 / T3.20 unaddressed.

**Deadline:** Phase 6 (existing slot Phase 6.B.3 expanded with BL-080 scope).

**References:**

- Marina observation 2026-05-08.
- `IMPLEMENTATION_PLAN_ACTIVE.md` Phase 6.B.3 — ORD production hardening (existing slot).
- BL-074 T3.17 — yandex skeleton dead code (BL-080 absorbs).
- `src/core/services/publication_service.py:106` — `_build_marked_text`.
- `src/core/services/ord_service.py`, `ord_yandex_provider.py:13`, `yandex_ord_provider.py:36`, `stub_ord_provider.py`.
- Telegram Bot API docs: caption length 1024, text 4096, `InputMediaPhoto`, `send_media_group`.

### BL-081 — Phase 3b launch hardening bundle

**Status:** OPEN — launch prerequisite per "архитектурная чистота" policy
**Created:** 2026-05-08
**Source:** BL-073/BL-074 disposition review 2026-05-08

Bundle of 7 launch absorption items from BL-073/BL-074 Tier 2/3 review (Marina decision 2026-05-08: priority shift "не экономия бюджета → архитектурная чистота + полная готовность включая всплывающее"). Each item ships before launch; BL-081 closes when все 7 done.

#### Frontend UX gaps (5)

- **T2.5** — Frontend `addPayout` send `X-Idempotency-Key` header (`web_portal/src/api/payouts.ts:11`); client retry safety
- **T3.1** — mini_app declined-channel UX deeplink (originally 5b.7a)
- **T3.2** — web_portal channel-add error UI render `extra.blockers[]` (originally 5b.7a)
- **T3.3** — `/payout-methods` portal route для G06 fail `remediation_url` (originally 5b.7a)
- **T3.7** — Frontend `addChannel` mutation idempotency convention (originally 5b.7a O.6)

#### Refactor / schema (2)

- **T3.20** — `Contract.contract_type` rename "advertiser_framework" → "framework" (originally 5b.3 L18; mechanical clean naming)
- **T3.21** — `LegalProfileService.check_completeness` side-effects split: pure compute + write (originally 5b.3 L19)

**Refs:** BL-073 disposition (T2.5), BL-074 disposition (T3.1-T3.3, T3.7, T3.20, T3.21).

### BL-082 — `User` type 3 sources of truth (drift risk)

**Status:** OPEN — latent (DX / type-drift, no current breakage)
**Created:** 2026-05-11
**Source:** PROMPT_23 web_portal/ probe 2026-05-11, § 11 surprise #2

**Statement:** Three independent `User` type declarations coexist in `web_portal/`:

- `web_portal/src/stores/authStore.ts` exposes `User` (10 fields — intentionally
  minimal subset для store state)
- `web_portal/src/lib/types.ts` exposes `User` (legacy aggregate types file,
  7959 bytes)
- `web_portal/src/lib/types/user.ts` exposes `User` (23 fields — modular, likely
  canonical: `plan_expires_at`, `credits`, `advertiser_xp/level`, `owner_xp/level`,
  `referral_code`, `legal_status_completed`, `has_legal_profile`,
  `platform_rules_accepted_at`, `privacy_policy_accepted_at`, etc.)

Risk: type drift over time, inconsistent field access patterns, false-positive
imports from wrong module.

**Closure trigger:** consolidate to single canonical (likely
`lib/types/user.ts`); refactor `authStore.User` to import & alias subset via
`Pick<User, ...>`; deprecate `lib/types.ts:User` and update all importers; add
eslint rule preventing direct re-declarations.

**Effort:** Small (~2-4 hours: audit imports + replace + lint clean + verify
build).

**Refs:** PROMPT_23 probe (`tmp/web_portal_probe.md` § 5 + § 11).

### BL-083 — TanStack Query devtools не mounted в `App.tsx`

**Status:** OPEN — latent (DX-only)
**Created:** 2026-05-11
**Source:** PROMPT_23 web_portal/ probe 2026-05-11, § 11 surprise #8

**Statement:** `@tanstack/react-query-devtools` присутствует в
`web_portal/package.json` `devDependencies` (`v5.91.3`) но не imported / mounted
в `web_portal/src/App.tsx`. DX-loss — нельзя inspect query cache, debug stale
data, observe network в dev режиме.

**Closure trigger:**

```tsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

// inside <QueryClientProvider>:
<QueryClientProvider client={queryClient}>
  <RouterProvider router={router} />
  {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
</QueryClientProvider>
```

**Effort:** Trivial (~5 lines, <10 minutes).

**Refs:** PROMPT_23 probe (`tmp/web_portal_probe.md` § 4 + § 11).

### BL-084 — `authStore` без `persist` middleware — manual localStorage sync

**Status:** OPEN — latent (cross-tab edge case)
**Created:** 2026-05-11
**Source:** PROMPT_23 web_portal/ probe 2026-05-11, § 11 surprise #5

**Statement:** `web_portal/src/stores/authStore.ts` использует vanilla zustand
БЕЗ `persist` middleware. `setAuth`/`logout` manually write to BOTH store state
AND `localStorage` (keys `rh_token`, `rh_user`). Cross-tab sync работает только
при initial `localStorage.getItem(...)` at store creation — нет `storage` event
listener для live cross-tab updates.

**Risk (edge case):** user opens 2 tabs → logs out в tab A → tab B continues
showing logged-in state until refresh/navigation. No current user reports.

**Closure trigger (variants):**

- (a) Refactor к `zustand/middleware persist` — drops manual writes, gives
  automatic localStorage sync. Refactor ~30 min, contained surgery.
- (b) Add `storage` event listener — surgical (~10 min), live cross-tab updates;
  keeps current manual-write pattern.

**Effort:** Small.

**Refs:** PROMPT_23 probe (`tmp/web_portal_probe.md` § 5 + § 11).

### BL-085 — Sentry `afterResponse` auto-captures non-ok — noise на known 4xx

**Status:** OPEN — latent (observability noise)
**Created:** 2026-05-11
**Source:** PROMPT_23 web_portal/ probe 2026-05-11, § 11 surprise #4

**Statement:** `afterResponse` hook на ky instance (`web_portal/src/shared/api/client.ts`)
вызывает `Sentry.captureException(new Error(\`[API] Error: ${response.status} ${response.url}\`))`
для каждого `!response.ok`. Известные ожидаемые 4xx (404 на download
not-found, 403 на not-owner attempts, 401 → handled by redirect) шумят в Sentry
без actionable signal.

Affected endpoints today: acts PDF download, kudir export (admin), mediakit PDF
download (B.4 ships 2026-05-11).

**Closure trigger (variants):**

- (a) Filter by URL pattern в `afterResponse` — skip Sentry capture для известных
  download endpoints на 4xx.
- (b) Filter by status code — skip 401 (already handled by redirect) and 403/404
  globally; keep 5xx и unexpected.
- (c) Add Sentry `beforeSend` global hook с filtered list.

**Effort:** Small (~10 lines с tests of filter logic).

**Priority note:** Low-medium — escalate if Sentry quota / signal-to-noise
becomes operational pain.

**Refs:** PROMPT_23 probe (`tmp/web_portal_probe.md` § 3 + § 11); BL-076 T1.2-D1
(mediakit B.1-B.4 series).

### BL-086 — Mediakit logo resolver / Telegram file_id image proxy

**Status:** OPEN — feature gap (frontend image proxy infrastructure)
**Created:** 2026-05-11
**Source:** PROMPT_28 B.5 mini_app preview screen CHANGES (deferred section); also surfaced PROMPT_24/PROMPT_25 B.4 download path.

**Statement:** `ChannelMediakit.logo_file_id` хранит Telegram file_id
(bot-scoped reference). Frontends (web_portal owner cabinet PDF preview,
mini_app advertiser preview screen) сейчас не могут рендерить logo image —
нет endpoint'а / proxy, отдающего bytes по file_id. Backend PDF generator
(`mediakit_pdf.py`) принимает `logo_bytes` argument, но `logo_file_id →
bytes` resolver не реализован (B.2 ships с `logo_bytes=None` per Q3 defer).

Broader concern: file_id → image bytes pattern also applies к channel
avatars (currently not displayed) и future post media attachments (BL-079
scope).

**Closure trigger (variants):**

- (a) `GET /api/files/telegram/{file_id}` endpoint — `getFile` +
  `downloadFile` + auth + cache. Frontend `<TelegramImage file_id={...}>`
  component для shared use.
- (b) Pre-resolve URL: signed-proxy с TTL; backend job заранее resolves
  and caches.
- (c) S3/MinIO mirror: on mediakit logo upload (Phase 8 feature surface),
  copy bytes к internal storage + serve via standard CDN.

**Effort:** medium (endpoint + cache + frontend component + tests; ~1-2 days).

**Priority note:** low — cosmetic (mediakit functional без logo); Phase 8
candidate если broader image-proxy infrastructure planned.

**Refs:** `CHANGES_2026-05-11_b5-mediakit-advertiser-preview.md` § "Deferred
to B.6 / BACKLOG"; B.2 endpoint в `src/api/routers/channels.py:1302-1342`;
`mediakit_pdf.py:58` `logo_bytes` guard.

### BL-087 — Mediakit theme_color tinting

**Status:** OPEN — UX polish (visual identity передача)
**Created:** 2026-05-11
**Source:** PROMPT_28 B.5 mini_app preview screen CHANGES (deferred section).

**Statement:** `MediakitAdvertiserResponse.theme_color` (hex string,
defaults к `"#1a73e8"` после B.3 hotfix) возвращается frontend'у но не
applied as visual tint в mini_app preview screen. Currently screen uses
neutral Tailwind tokens (`var(--rh-space-*)`). Channel-owner brand identity
не передаётся в advertiser-facing preview.

Web_portal PDF rendering уже использует `theme_color` через
`reportlab.lib.colors.HexColor` в `mediakit_pdf.py` — mini_app preview
parity отсутствует.

**Closure trigger:** apply `theme_color` к specific UI elements в
`mini_app/src/screens/advertiser/ChannelMediakitView.tsx`: e.g. heading
underline, card border accent, или CTA button background. Pattern: inline
`style={{ borderColor: theme_color }}` per element, либо CSS variable
injection через React context.

**Effort:** small (~30 LOC, single screen).

**Priority note:** low — cosmetic polish; mediakit content readable без
tinting.

**Refs:** `CHANGES_2026-05-11_b5-mediakit-advertiser-preview.md` § "Deferred
to B.6 / BACKLOG"; `mini_app/src/screens/advertiser/ChannelMediakitView.tsx`;
`MediakitAdvertiserResponse.theme_color` (`src/api/schemas/mediakit.py`).

### BL-088 — `landing/` frontend surface probe

**Status:** OPEN — operational / observability gap
**Created:** 2026-05-11
**Source:** Phase B mediakit workstream — third frontend dir untouched + unprobed.

**Statement:** Repository contains three frontend directories: `mini_app/`,
`web_portal/`, `landing/`. Phase B mediakit work (B.4 + B.5) probed
`web_portal/` (PROMPT_23) and `mini_app/` (PROMPT_26) before touching,
surfacing baseline issues (BL-082..085 from web_portal probe; B.5 deferrals
from mini_app probe). `landing/` (RekHarbor static landing page per
`landing-dev` skill metadata) was NOT touched during Phase B, also NOT
probed.

Stack/scope/deps/build state unknown today: `package.json` deps, lint
baseline, vite/Tailwind v4 config, deployed surface, integration с other
frontends (auth, deeplinks), bundle size, motion/react usage.

**Closure trigger:** deep-dive probe session — inventory
`landing/package.json` deps + `landing/src/` screens/components + `npm run
lint` baseline + `npm run build` artifact + verify CSP/font/motion
conventions per CLAUDE.md landing-specific rules.

**Effort:** small (~probe session, no implementation).

**Priority note:** low — no immediate functional gap; insurance against
repeat issues от prior `web_portal/`/`mini_app/` probes when next
`landing/` touch comes.

**Refs:** `CHANGES_2026-05-11_b5-1-mediakit-advertiser-endpoint.md` mentions
`landing/: untouched` baseline preservation as evidence of probe gap;
CLAUDE.md § "Landing-specific rules" lists conventions; `landing-dev` skill
scoped to `/opt/market-telegram-bot/landing/`.

### BL-089 — `@telegram-apps/sdk-react` unused dep в `mini_app/`

**Status:** OPEN — dep hygiene (cosmetic)
**Created:** 2026-05-11
**Source:** PROMPT_26 mini_app probe surprise #1 (referenced в B.5 CHANGES "Deferred" section).

**Statement:** Package `@telegram-apps/sdk-react` declared в
`mini_app/package.json` dependencies, но не imported anywhere в
`mini_app/src/`. Verified through grep during PROMPT_26 probe — zero
`from '@telegram-apps/sdk-react'` references. Adds:

- Bundle weight (unused code в dist).
- npm install time / lockfile churn.
- Cognitive overhead (future developer might assume it's wired).

Likely artifact of early Telegram WebApp integration exploration, abandoned
in favor of custom auth/ky-based pattern.

**Closure trigger:** `cd mini_app && npm uninstall @telegram-apps/sdk-react`
+ verify build still clean (`npm run build`) + verify no transitive
consumers (`grep -r telegram-apps mini_app/src/`).

**Effort:** trivial (~5 minutes).

**Priority note:** low — cosmetic / hygiene; not blocking.

**Refs:** `CHANGES_2026-05-11_b5-mediakit-advertiser-preview.md` § "Deferred
to B.6 / BACKLOG"; PROMPT_26 probe transcript (`tmp/mini_app_probe.md` if
preserved).

### BL-090 — Stop-hook fires loop on Phase A research-only outputs

**Status:** OPEN — UX noise (no functional impact)
**Created:** 2026-05-11
**Source:** PROMPT_28 B.5 Phase A (~500+ fires); PROMPT_30 B.6.2 Phase A (~9 fires). Recurrence confirmed; L71 candidate pattern.

**Statement:** Prompts using Phase A (read-only research →
`tmp/<slug>_research.md` output) → STOP gate → Phase B (mutations + CHANGES
file landed same-commit с docs edits в Шаге 6) trigger repeated stop-hook
fires at Phase A boundary complaining `CHANGES_<date>_<desc>.md` NOT
created в `reports/docs-architect/discovery/`. BL-016 silent-ignore
protocol handles agent-side after first non-trivial ack; fires continue
as visible noise stream к Marina (chat surface — no agent action).

Pattern reproduces deterministically on L70 design (CHANGES same-commit
pattern, deferred from Phase A boundary). Each STOP gate без CHANGES file
fires the hook; identical fires per BL-016 silent-ignored agent-side but
each fire surfaces к Marina via chat.

**Closure trigger (variants):**

- (a) Server-side hook tuning (Anthropic-side action — not actionable from
  project prompts).
- (b) Hook config в `.claude/` if existing — selectively suppress fires
  when `tmp/<slug>_research.md` exists OR when transcript indicates "Phase
  A research-only STOP gate".
- (c) Accept as known harmless; rely on BL-016 silent-ignore (current
  state). Phase A boundary fires not blocking workflow.

**Effort:** small (option b) / negligible (option c).

**Priority note:** low — UX noise; не affects correctness. Marina-side
annoyance only.

**Refs:** BL-013 (stop-hook relay protocol), BL-016 (stop-hook fires-in-loop
infrastructure), L70 (Phase A boundary deferral pattern), L71 (in-prompt
tracking pattern).

**Post-v0.6.0 observation (2026-05-12):** hook checks **tree state**, not
commit state. PROMPT_31 (release/0.6.0 cut) fired 7 times at Phase A/B
boundaries on branches not containing `CHANGES_*.md` in working tree, then
resolved naturally at fire #8 (post-Шаг 11 boundary): the develop→main merge
propagated existing CHANGES files into main's tree, satisfying the hook check.

**Implication:** pathology is most active in Phase A read-only research
boundaries on feature branches that don't yet contain CHANGES files. Natural
resolution occurs at merge boundaries into targets containing accumulated
CHANGES files.

**Observed totals:** 7 fires (PROMPT_31), 9 fires (PROMPT_30), 1+ fires
(PROMPT_29). BL-016 silent-ignore protocol handled cleanly across all — no
autonomous capitulation.

**Server-side mitigation reassessment:** option (a) (Anthropic-side) may not
be required if pathology resolves at normal merge boundaries; option (c)
accept-as-known-harmless validated through full release cycle
(PROMPT_28..PROMPT_31).

### BL-104 — Telegram→MAX migration strategy + transitional monitoring

**Status:** OPEN — strategic
**Created:** 2026-05-12 (BL-080 8a research surface)
**Source:** ФЗ-72 ч. 10.7 ст. 5 ФЗ-38 — ФАС объявила запрет рекламы в Telegram с 01.01.2027.

**Statement:** Платформа базируется на Telegram. ФЗ-72 запрещает рекламу в Telegram с 01.01.2027. Переходный период до 31.12.2026 — штрафы НЕ применяются. После 01.01.2027 — possible existential risk для платформы. Migration в MAX (МАХ — российский мессенджер) potential mitigation.

**Marina plan (2026-05-13):** Launch в Telegram, миграция в МАХ к концу 2026 в параллель.

**Closure trigger:**
- (a) Provider-pattern abstraction for bot transport (Phase 5 territory) облегчит миграцию — `BotProvider` interface, Telegram = default impl, MAX = alternate impl.
- (b) Strategic monitoring: transitional period штрафы tracking, MAX feature parity audit, business decision на ratio Telegram/MAX к Q4 2026.
- (c) Acceptance: bot transport provider-pattern abstracted + MAX provider stub ready + business strategic decision documented.

**Effort:** large (bot transport abstraction + new MAX integration + parallel ops).
**Priority note:** high (strategic, existential timeline).

**Refs:** Phase 5 (provider pattern), BL-105 (Yandex ORD которая работает в обоих), BL-107.

**Owner:** _unassigned_

### BL-105 — ККТУ codes UI integration (Yandex ORD v7)

**Status:** OPEN — required for production ORD launch
**Created:** 2026-05-12 (BL-080 8a research surface)
**Source:** Yandex ORD API v7 (с 07.11.2025) обязательно требует `kktuCodes` для creative registration.

**Statement:** Yandex ORD v7 requires `kktuCodes` (Классификатор Категорий Товаров и Услуг) for creative registration. Currently platform omits this field — works in stub mode (Phase 5 deferred) but fails real production ORD calls.

**Closure trigger:**
- (a) Add `kktu_codes` column to Campaign model (array of strings or JSONB).
- (b) UI integration в campaign creation flow: ККТУ code picker (dropdown / search) с validation против reference list.
- (c) ORD provider integration: pass `kktuCodes` field в creative registration payload.
- (d) Migration of existing campaigns: default value strategy (NULL? "needs assignment" flag?).

**Effort:** medium (DB schema add + UI integration + ORD payload extension).
**Priority note:** medium-high — launch-blocking for real ORD registration.

**Refs:** BL-080 (ORD hardening, real provider integration in Phase 5+).

**Owner:** _unassigned_

### BL-106 — Overlay variant (D) для caption budget

**Status:** OPEN — post-launch enhancement
**Created:** 2026-05-13 (BL-080 8d closure)
**Source:** BL-080 8d caption budget Option A (truncate) was implemented; Option D (overlay erid on image) deferred.

**Statement:** Best practice per АРИР — render erid поверх image (Pillow pipeline) AND duplicate в caption для ЕРИР робота. Currently we truncate caption (Option A) when erid + ad_text exceeds Telegram limit. Overlay variant ensures erid always visible на изображении plus separately в caption.

**Closure trigger:**
- (a) Pillow image processing pipeline integration (post-launch image processing service).
- (b) Erid text overlay rendering: position, font, opacity, contrast against image background.
- (c) Caption retains duplicated erid for ЕРИР robot indexing (truncate ad_text не erid).
- (d) Tests: visual regression + caption parsing correctness.

**Effort:** medium (image processing infra + rendering + tests).
**Priority note:** low — Option A truncate works correctly per current scope.

**Refs:** BL-080 (ERID marking flow), Q-M.4 carve-out (Phase 4 erid placeholder pattern в ДС).

**Owner:** _unassigned_

### BL-107 — Channel registration verification для каналов ≥10k подписчиков (метка А+)

**Status:** CLOSED 2026-05-15 (v0.9.0 — Phase B.1–B.9 closure)
**Created:** 2026-05-13 (BL-080 8a research surface)
**Closure summary:** Shipped via 21 commits across 9 feature phases + 3 CI gate rounds (PROMPT 44 / 45 / 45-ext / 45-ext-of-ext). Add-time enforcement via G19 + Trustchannelbot auto-verification; manual evidence escape hatch via owner submission + admin review; daily drift detection via periodic Celery task. Three latent production defects caught and fixed (G19 eager-load `ef26f68`; SQLAlchemy `Mapped[StrEnum]` case mismatch `24cf68a`; `/api/analytics/summary` validation `9506583`). Final state: ci-local 1204 passed (0 failed); BL-107 own 12/12 E2E PASS across 3 browser projects. See `reports/docs-architect/discovery/CHANGES_BL107_consolidated_2026-05-15.md`.

**Source:** ФЗ-303 от 08.08.2024 → ч. 10.6 ст. 5 ФЗ-38 + ст. 10.6 ФЗ-149. Реестр блогеров действует с 01.11.2024.

**Statement:** Каналы ≥10000 подписчиков обязаны регистрироваться в реестре Роскомнадзора (Реестр блогеров) и иметь метку А+ (зарегистрирован) в публикациях. Штрафы за размещение рекламы у незарегистрированного блогера ≥10k подписчиков:

- до 100k рублей для граждан;
- до 200k рублей для должностных лиц;
- **до 500k рублей для юридических лиц.**

**Это независимая статья.** Штрафы действуют ВСЕГДА (не в переходном периоде, не ждут 01.01.2027). Платформа подвергается штрафу как facilitator если допускает placement у unregistered channel с ≥10k подписчиков.

**Closure trigger:**
- (a) Bot должен fetch subscriber count при `/add_channel` flow (Telegram Bot API `get_chat`).
- (b) Если subscriber_count ≥10000: required verification — has метка А+ (зарегистрирован); channel owner может представить evidence (link на реестр, screenshot, etc.).
- (c) DECLINE (hard, не warning) если ≥10k без верифицированной регистрации.
- (d) DB schema: `Channel.is_blogger_registry_verified: bool` + `Channel.blogger_registry_verified_at: datetime | None`.
- (e) UI flow: owner submits registry evidence → admin reviews → marks verified, OR bot auto-verifies via Роскомнадзор API (if available).
- (f) Periodic re-check: subscriber growth past threshold without registration → block new placements (decision на existing placements TBD).

**Effort:** medium (bot flow + DB schema + admin verification UI + Roskomnadzor reference if API available).
**Priority note:** **HIGH — LAUNCH-BLOCKING**. Real legal liability ≥500k руб per violation для платформы.

**Refs:** ФЗ-38, ФЗ-149, ФЗ-303. Phase 5 (channel gating territory).

**Owner:** _unassigned_

### BL-108 — Video note (кружок) placement type addition

**Status:** OPEN — feature gap
**Created:** 2026-05-13 (Phase 4 8d Phase A research)
**Source:** PROMPT 8d Phase A finding: `media_type` enum supports `none/photo/video` only, video note (Telegram круглое видео) path не существует в data model.

**Statement:** Telegram supports video notes (короткие круглые видео-сообщения) as a distinct media kind. Current `Placement.media_type` enum has `photo/video/none` but no `video_note`. Implication: cannot offer video note format ad placements. АРИР recommendations suggest video note formats grow in popularity для рекламы.

**Closure trigger:**
- (a) Data model: extend `media_type` enum — add `video_note` value.
- (b) Bot UI flow: support video_note upload + preview.
- (c) Dispatcher branch: route video_note placements to `send_video_note` Telegram API (cannot have caption — separate-message marker via `reply_parameters` only legal path per АРИР).
- (d) Option B (separate-message marker via reply_parameters) — единственный legal путь для video notes.
- (e) Smoke tests + integration test.

**Effort:** medium (data model + bot UI + dispatcher + tests).
**Priority note:** low — current text/photo/video coverage sufficient for MVP.

**Refs:** BL-080 8d (caption budget — Option B dropped per CLAUDE.md P1+P3 from 8d scope due to data model absence).

**Owner:** _unassigned_

### BL-109 — `ad_text` >4096 chars edge case для text-only placements

**Status:** OPEN — pre-existing edge case
**Created:** 2026-05-13 (Phase 4 8d Phase A research)
**Source:** PROMPT 8d Phase A finding: `Placement.ad_text` DB max=5000 chars, Telegram text message limit=4096 chars.

**Statement:** Currently unknown behavior for text-only placement (`media_type=none`) с `ad_text` > 4096 chars. DB allows up to 5000, Telegram text message API rejects >4096. Probe required to determine actual current handling:

- (a) Truncation? Где — admin write-side, bot send-side?
- (b) Error? Какой? Где surfaced?
- (c) Silent acceptance с failure at publication time?

**Closure trigger:**
- (a) Probe + reproduce: create text-only placement с 4500-char `ad_text`, attempt publish, observe behavior.
- (b) Decision: либо reduce DB max=4096 to align с Telegram, либо add explicit pre-validation в campaign creation flow.
- (c) UI: character counter с visual warning at 4096.
- (d) Test: integration test с >4096 char text-only placement.

**Effort:** small (probe + decision + tests).
**Priority note:** medium — affects real users with long ad copy.

**Refs:** None specific.

**Owner:** _unassigned_

### BL-110 — `CLAUDE.md` migration count claim outdated

**Status:** OPEN — documentation drift
**Created:** 2026-05-14 (Phase 4 PROMPT 26 verification)
**Source:** PROMPT 26 Step 1 migration verification — `CLAUDE.md` claims "1 consolidated migration" but reality has 2 files: `0001_initial_schema.py` + `e6a88faa9fa0_add_placement_status_history_table_and_.py` (Phase 2).

**Statement:** `CLAUDE.md` rules section mentions migration immutability per BL-061 с phrase suggesting single consolidated `0001_initial_schema.py`. Reality has 2 migration files. Documentation drift. Pre-prod exception (rewrite of `0001_initial_schema.py`) still valid но applies to specific file, не "the" migration.

**Closure trigger:**
- (a) Edit `CLAUDE.md` migration section: update wording from "1 consolidated migration" to "migrations" (plural), OR explicitly enumerate (`0001_initial_schema.py` pre-prod-mutable + `e6a88faa9fa0_*.py` immutable per BL-061).
- (b) Sanity check: какие other immutable migrations expected? If yes, document expected file count и naming pattern.

**Effort:** small (single doc edit).
**Priority note:** low — documentation accuracy.

**Refs:** BL-061 (migration immutability rule), Phase 2 migration `e6a88faa9fa0_*`.

**Owner:** _unassigned_

### BL-111 — `_partials/contract_signatures.html` dropped from Step 0a refactor

**Status:** OPEN — optional cleanup
**Created:** 2026-05-14 (Phase 4 PROMPT 27 Step 5 finding)
**Source:** PROMPT 26 Step 0a planned 3 partials extraction (`contract_css`, `contract_header`, `contract_signatures`); only 2 extracted (CSS + header). Signature blocks inline в существующих 6 contract templates — agent identified не shared pattern. Phase 4 ДС templates also inline sigs.

**Statement:** Originally Phase 4 Step 0a (template partials refactor per Q-M.1) intended 3 partials. Reality: existing 6 contract templates use distinct signature block layouts per legal_status (individual / IE / LE / etc.). Forced extraction to single partial would require parameterization that breaks DRY benefit. Agent skipped this partial; sigs remain inline.

**Closure trigger (if desired):**
- (a) Audit 6 contract template signature blocks: identify real shared core (e.g., `<table>` structure, "Подпись:" text, IP placeholder).
- (b) Extract minimal shared signature partial с Jinja2 macros for per-legal_status fields.
- (c) Refactor 6 contract templates + 5 ДС templates to use new partial.
- (d) Verify rendering tests pass.

**Effort:** small-medium (template refactor + visual regression check).
**Priority note:** low — current inline sigs work, не violate principles given shared pattern absence.

**Refs:** Phase 4 Step 0a (CSS + header partials extracted).

**Owner:** _unassigned_

### BL-112 — Playwright `sign-supplementary-agreement` seed fixture creation

**Status:** OPEN — full E2E coverage gap
**Created:** 2026-05-14 (Phase 4 PROMPT 28 Step 10 finding)
**Source:** PROMPT 28 Step 10 Playwright spec scoped to smoke level — required seed fixture (placement в `pending_owner` с обоими signed framework contracts + ДС pair generated, both unsigned) не существует в `scripts/e2e/seed_e2e.py`.

**Statement:** Phase 4 acceptance Playwright spec (`web_portal/tests/specs/sign-supplementary-agreement.spec.ts`) currently exercises smoke-level UI rendering only. Full interactive two-session flow (advertiser signs → owner signs → placement progresses) blocked by absence of e2e seed fixture for ДС state.

**Closure trigger:**
- (a) Add seed fixture к `scripts/e2e/seed_e2e.py`:
  - User pair (advertiser + owner) с signed framework contracts (`advertiser_framework` per role — see BL-115);
  - Channel owned by owner;
  - Placement в `pending_owner` state;
  - Two `supplementary_agreement` Contract rows (advertiser + owner) с `contract_status='draft'`;
  - One placement per ДС sign scenario (single, paired, expired etc.).
- (b) Update Playwright spec to use fixture-seeded test placement IDs.
- (c) Add per-viewport assertions: section visibility, button state, post-sign UI updates, two-session sign flow.
- (d) Run в CI (`make ci-local` includes Playwright? — verify).

**Effort:** medium (seed fixture + spec extensions + verify).
**Priority note:** medium — current unit + integration coverage adequate, Playwright closes UI gap.

**Refs:** BL-001, BL-002 (similar Playwright spec deferrals for seed fixture absence).

**Owner:** _unassigned_

### BL-113 — Stop-hook BL-013 deferred bundle detection

**Status:** OPEN — UX noise
**Created:** 2026-05-14 (Phase 4 PROMPT 28 finding)
**Source:** PROMPT 28 final STOP — same stop-hook BL-013 warning fired 12+ times when CHANGES legitimately deferred to PROMPT 29 (Phase closure batch).

**Statement:** Stop-hook checks for CHANGES file presence в working tree fires repeatedly when CHANGES is legitimately deferred to next-prompt closure (per BL-013 default (b) bundle protocol). BL-016 silent-ignore handles agent side correctly (acks 2, silent-ignore identical). Marina sees 12+ fires в chat surface even though agent disciplined correctly.

**Statement extends BL-090** (Stop-hook fires loop on Phase A research-only outputs) с pattern for multi-prompt sub-block work (PROMPT N implementation + PROMPT N+1 closure docs).

**Closure trigger (variants — overlaps BL-090):**
- (a) Hook reads transcript для "deferred to PROMPT X" pattern, suppresses fires.
- (b) Hook checks current commit message для "deferred" / "closure pending" keywords.
- (c) Accept as known (current state) — BL-016 silent-ignore protocol handles agent.

**Effort:** small (hook config) / negligible (accept-known).
**Priority note:** low — UX noise only, не affects correctness.

**Refs:** BL-013 (stop-hook relay protocol), BL-016 (acks bound at 2), BL-090 (Phase A loop variant).

**Owner:** _unassigned_

### BL-114 — RETIRED (NO BUG per probe)

**Status:** RETIRED 2026-05-14
**Created:** would have been 2026-05-14 (Phase 4 PROMPT 28 surface)
**Source:** PROMPT 28 surprise log suggested possible bug в `ContractRepo.get_framework_contract` role filtering.

**Resolution:** PROMPT 28b probe (`tmp/contract_repo_framework_audit_2026-05-14.md`) confirmed **NO BUG**. Method behaves correctly per umbrella naming convention; both read и write paths use `contract_type='advertiser_framework'` literal symmetric; `Contract.role` discriminator handles owner/advertiser distinction. Renaming for clarity captured separately as BL-115.

**Refs:** BL-115 (umbrella rename clarity improvement).

### BL-115 — `"advertiser_framework"` → `"framework"` umbrella `contract_type` rename

**Status:** OPEN — naming cleanup
**Created:** 2026-05-14 (Phase 4 PROMPT 28b probe verdict)
**Source:** PROMPT 28b probe — `ContractRepo.get_framework_contract(user_id, role)` filters `contract_type='advertiser_framework'` for both advertiser AND owner roles; `Contract.role` discriminator distinguishes. Existing docstrings в G02/G05 gate bodies already labelled this as "deferred-cleanup L18 carve-out".

**Statement:** Misleading umbrella name. Framework contracts for both roles use `contract_type='advertiser_framework'` literal — this works correctly (Contract.role discriminates) but the name `advertiser_framework` falsely suggests advertiser-specific. Owner framework contracts also stored as `advertiser_framework` rows. Renaming to `framework` (или similar role-neutral name) would clarify intent.

**Closure trigger:**
- (a) Rename literal `"advertiser_framework"` → `"framework"` across ~12 files:
  - `src/db/repositories/contract_repo.py` (read path — `get_framework_contract`);
  - `src/core/services/contract_service.py` (write path — `get_or_create_framework_contract`, `generate_contract` default mapping, `_CONTRACT_TEMPLATE_MAP`);
  - `src/db/models/contract.py` (если contract_type есть в comment/docstring);
  - `src/api/schemas/legal_profile.py` (`ContractType` enum value);
  - `src/db/migrations/versions/0001_initial_schema.py` (CREATE TABLE default или check constraint);
  - `tests/` fixtures (3+ files seed `advertiser_framework`);
  - Templates (если filename references "advertiser_framework").
- (b) Migration strategy: if pre-prod state preserved (no live customer data) — just update enum + literal. Otherwise data migration UPDATE.
- (c) Update G02/G05 docstrings: remove L18 carve-out notes.
- (d) Snapshot regen.
- (e) Verify integration tests pass post-rename.

**Effort:** medium (~12 files, snapshot regen, smoke verification).
**Priority note:** low — current state functional; rename is documentation-clarity improvement.

**Refs:** PROMPT 28b probe (verdict NO BUG, naming-only). L18 carve-out (G02/G05 docstrings).

**Owner:** _unassigned_

### BL-116 — TypeScript 7.0 full migration sprint

**Status:** OPEN — tech debt
**Created:** 2026-05-15 (BL-107 v0.9.0 closure surface)
**Source:** BL-107 Phase B.9.A pinning surfaced ongoing TS 6.x → 7.0 alignment work.

**Statement:** Both web_portal and mini_app are on TS 6.0.2 (CLAUDE.md landing-specific rules call out the version explicitly). TS 7.0 introduces deferred-evaluation type checks, conditional-type performance improvements, and tightens `verbatimModuleSyntax` ergonomics. Full migration requires coordinated upgrade of @types packages, jsdom (per vitest), and downstream lint rule compatibility.

**Closure trigger:**
- (a) Upgrade typescript to 7.0.x in all 3 frontends (mini_app, web_portal, landing).
- (b) Re-pin @testing-library/* + jsdom to versions compatible with TS 7.0.
- (c) Re-run lint/type-check across all frontends, capture diff to baseline.
- (d) Update CLAUDE.md landing-specific rules version reference.

**Effort:** medium-high — touches all frontends, may surface latent type-narrowing changes.
**Priority note:** low-medium — current TS 6.x is stable; migration is forward-looking hygiene.

**Refs:** BL-107 Phase B.9.A (`6356f4c`), CLAUDE.md "Landing-specific rules".

**Owner:** _unassigned_

### BL-117 — `landing/package.json` `"latest"` deps pinning

**Status:** OPEN — supply-chain hygiene
**Created:** 2026-05-15 (BL-107 v0.9.0 closure surface)
**Source:** Repeat surface during BL-107 Phase B.9.A pinning — landing/ uses `"latest"` for several deps which violates reproducible-build guarantees and exposes the landing to upstream supply-chain risk.

**Statement:** `landing/package.json` declares several dependencies as `"latest"` instead of pinned semver ranges or exact versions. Reproducible builds are compromised; any malicious upstream version published can land in production at the next `npm install`.

**Closure trigger:**
- (a) Audit current `landing/package-lock.json` for actual installed versions, pin those in `package.json`.
- (b) Re-run landing build to confirm no regression.
- (c) Add CI check that fails on `"latest"` in any package.json under the repo.

**Effort:** small.
**Priority note:** low — landing is static and surface area limited, but supply-chain hygiene is a baseline expectation.

**Refs:** BL-107 Phase B.9.A pinning discipline.

**Owner:** _unassigned_

### BL-118 — `mini_app/vite.config.ts` `resolve.tsconfigPaths` invalid option

**Status:** OPEN — config drift (silent no-op)
**Created:** 2026-05-15 (BL-107 v0.9.0 closure surface)
**Source:** Phase B.9.A vitest infrastructure work surfaced an invalid Vite resolve option in mini_app config.

**Statement:** `mini_app/vite.config.ts` includes `resolve.tsconfigPaths` as a config option, but Vite does not recognize this key (the canonical pattern is the `vite-tsconfig-paths` plugin or explicit alias mapping). Vite silently ignores unknown `resolve.*` keys. Currently mini_app builds correctly because aliases are mirrored explicitly in `vitest.config.ts` (Phase B.9.A), but the dead config invites future drift.

**Closure trigger:**
- (a) Either install `vite-tsconfig-paths` plugin and use it, or delete the dead config key.
- (b) Mirror the chosen approach to web_portal if inconsistency exists.

**Effort:** trivial (~5 min).
**Priority note:** low — silent no-op, no functional impact.

**Refs:** BL-107 Phase B.9.A (`6356f4c`).

**Owner:** _unassigned_

### BL-119 — `.claude/` hook persistence between fresh sessions

**Status:** OPEN — infrastructure UX gap
**Created:** 2026-05-15 (BL-107 v0.9.0 closure surface)
**Source:** BL-107 multi-prompt workstream surfaced repeated re-discovery of `.claude/` state across fresh `claude` invocations (PROMPT 42 → 43 → 44 → 45 → 46 chain). Complements BL-113 (stop-hook BL-013 deferred bundle detection).

**Statement:** Fresh `claude` sessions do not inherit `.claude/` hook state or scheduled-task locks consistently. The `.claude/scheduled_tasks.lock` file lingers untracked and was visible in `git status` on every session start. Existing BL-016 silent-ignore + BL-113 deferred-bundle protocols partially mitigate but don't address state hand-off.

**Closure trigger:**
- (a) Standardize a session-start clean-up routine for `.claude/` ephemeral files.
- (b) Distinguish ephemeral lock files from durable hook config (gitignore patterns).
- (c) Document the hand-off expectations in CLAUDE.md "Process discipline" section.

**Effort:** small.
**Priority note:** low — UX cleanliness, no correctness impact.

**Refs:** BL-013 (stop-hook relay protocol), BL-016 (acks bound at 2), BL-090, BL-113.

**Owner:** _unassigned_

### BL-120 — Gate framework — integration test pattern requirement (caller-chain E2E)

**Status:** OPEN — process improvement
**Created:** 2026-05-15 (L-next from BL-107 v0.9.0 closure)
**Source:** PROMPT 44 caught G19 production regression (`ef26f68`) only at ci-local gate, not at sub-block unit tests. AsyncMock-shaped `session.get()` returns coincidentally satisfied production async eager-load expectations.

**Statement:** Adding a new gate to `_TRANSITION_GATES` or `_CHANNEL_CONTEXT_GATE_CHECKERS` requires verifying the gate fires correctly at the full caller-chain (transition path or channel-add path), not just at unit-test scope with mocked sessions. Unit-test coverage with `AsyncMock(spec=AsyncSession)` does not exercise the actual eager-load (`selectinload`) requirements that production paths impose.

**Closure trigger:**
- (a) Document the expectation in `CLAUDE.md` "Engineering Principles" or a new section about gate additions.
- (b) Optionally: add a CI lint rule that flags new entries in `_TRANSITION_GATES` / `_CHANNEL_CONTEXT_GATE_CHECKERS` without a matching integration test.
- (c) Backfill caller-chain integration tests for existing gates where missing.

**Effort:** small (doc) → medium (lint + backfill).
**Priority note:** medium — preventive process improvement; pays off on every future gate addition.

**Refs:** BL-107 Phase B.2 → ef26f68 regression caught at PROMPT 44 ci-local.

**Owner:** _unassigned_

### BL-121 — SQLAlchemy `Mapped[StrEnum]` without `values_callable` — audit pattern

**Status:** OPEN — latent bug audit
**Created:** 2026-05-15 (BL-107 v0.9.0 closure — R7 production fix)
**Source:** R7 production fix (`24cf68a`) — `BloggerRegistryVerificationMethod` column declared as `Mapped[T] = mapped_column(nullable=True)` without explicit `Enum(...)` spec. SQLAlchemy inferred the column and serialized via member NAME (uppercase) while Postgres enum holds member VALUES (lowercase). Produced `InvalidTextRepresentationError` only at the D.3 end-to-end manual-evidence flow; unit tests passed because they did not hit the actual DB write path.

**Statement:** Any column declared as `Mapped[T] | None` where `T` is a `StrEnum` and the column-type is inferred (no explicit `Enum(T, ...)` in `mapped_column(...)`) is suspect. Audit pattern: `grep -rn "Mapped\[.*Method\]\|Mapped\[.*Status\]" src/db/models/`. Each match needs a check whether the underlying Postgres enum type's members are the StrEnum's names (uppercase) or values (lowercase). When values, explicit `Enum(T, name=..., values_callable=lambda x: [m.value for m in x])` is required.

**Closure trigger:**
- (a) Run the audit grep, enumerate all `Mapped[StrEnum]` declarations.
- (b) For each, verify the Postgres enum type definition (Alembic migration) matches the ORM serialization choice.
- (c) Fix any mismatches with explicit `Enum(..., values_callable=...)` ORM declaration. No migration change needed when the pg enum already holds correct values.
- (d) Add a regression test for at least one fixed column verifying round-trip insert/select.

**Effort:** small (audit + fixes, ~30-60 min depending on count).
**Priority note:** medium — silent latent bugs that only manifest in production paths.

**Refs:** R7 fix `24cf68a`, memory entry `project_sqlalchemy_strenum_pitfall.md`.

**Owner:** _unassigned_

### BL-122 — ticket-login `rh_token` not persisted to localStorage (R4)

**Status:** OPEN — auth UX bug (Phase 1 §1.B.3 bridge regression)
**Created:** 2026-05-15 (BL-107 v0.9.0 test-e2e residual R4)
**Source:** PROMPT 45 Extension surfaced — 3 cases (`web_portal/tests/specs/ticket-login.spec.ts:43` × 3 browsers).

**Statement:** Ticket-login spec asserts `localStorage.getItem('rh_token')` is non-empty after consuming a ticket and navigating to `/cabinet`; assertion fails because the token is either not written by `TicketLogin.tsx` or is cleared/overwritten by a competing auth-store reset on the `/cabinet` mount. Spec reaches the assertion (auth chain Pattern 1 + 2 + P2c unblocked it), so the bug is real, not a test-side issue.

**Closure trigger:**
- (a) Probe `web_portal/src/screens/auth/TicketLogin.tsx` consume flow — does it write `rh_token` to localStorage before redirect?
- (b) Probe `useAuth*` hooks for a competing reset on `/cabinet` mount.
- (c) Identify root cause (hypothesis a or b), fix, add regression test.

**Effort:** 30–60 min (depends on hypothesis).
**Priority note:** medium — auth UX bug; ticket-login is a Phase 1 §1.B.3 bridge flow.

**Refs:** BL-107 PROMPT 45 Extension residual R4.

**Owner:** _unassigned_

### BL-123 — Campaign wizard step indicator missing on `/adv/campaigns/new/category` (R5)

**Status:** OPEN — frontend regression (likely S-47 phase 5)
**Created:** 2026-05-15 (BL-107 v0.9.0 test-e2e residual R5)
**Source:** PROMPT 45 Extension surfaced — 3 cases (`web_portal/tests/specs/deep-flows.spec.ts:60` × 3 browsers).

**Statement:** Spec asserts `[data-testid="step-indicator"], nav ol, nav ul` has count > 0 on `/adv/campaigns/new/category`; gets 0. The wizard step indicator component appears to have been removed or unmounted on the category step. Other wizard steps may share the same gap.

**Closure trigger:**
- (a) Inspect `web_portal/src/screens/advertiser/campaigns/wizard/CampaignCategory.tsx` and the wizard layout — is the step indicator imported/rendered?
- (b) Check git history for S-47 phase 5 refactor that may have dropped the wrapping.
- (c) Restore the step indicator; verify all wizard steps render it consistently.

**Effort:** 15–30 min.
**Priority note:** low-medium — UX regression in wizard.

**Refs:** BL-107 PROMPT 45 Extension residual R5.

**Owner:** _unassigned_

### BL-124 — Channel-settings price serialized as string after PATCH round-trip (R6)

**Status:** OPEN — API contract / serialization bug
**Created:** 2026-05-15 (BL-107 v0.9.0 test-e2e residual R6)
**Source:** PROMPT 45 Extension surfaced — 3 cases (`web_portal/tests/specs/deep-flows.spec.ts:89` × 3 browsers).

**Statement:** PATCH `/api/channel-settings/?channel_id=:id` with `{ price_per_post: 1234 }` succeeds; subsequent GET returns `price_per_post: "1234"` (string). Test asserts strict `toBe(1234)` (number) and fails. Likely Decimal-vs-int serialization in `ChannelSettingsResponse` Pydantic model — `Numeric`-typed column serialized as string per Pydantic default for `Decimal`, missing `field_serializer` or `json_schema_extra`.

**Closure trigger:**
- (a) Inspect `src/api/schemas/channel_settings.py` or equivalent — Decimal serialization.
- (b) Inspect `src/api/routers/channel_settings.py:187` PATCH handler return type.
- (c) Inspect `src/db/models/channel_settings.py` column type.
- (d) Add `field_serializer` returning numeric or change column type if appropriate.
- (e) Regenerate contract snapshot if Pydantic schema changes.

**Effort:** 30–60 min.
**Priority note:** medium — API contract bug; downstream frontend may also be coerce-string-to-number client-side, masking the issue.

**Refs:** BL-107 PROMPT 45 Extension residual R6.

**Owner:** _unassigned_

### BL-125 — Visual baseline flake on 4 routes after R8 regen (R10)

**Status:** OPEN — test-infra (visual flake)
**Created:** 2026-05-15 (BL-107 v0.9.0 ext-of-ext residual R10)
**Source:** PROMPT 45 Extension-of-Extension surfaced — 4 cases (`web_portal/tests/specs/visual.spec.ts`): `/analytics` mobile-webkit, `/adv/campaigns/new/channels` mobile-webkit + mobile-chromium, `/admin/users` mobile-webkit.

**Statement:** After R8 fix (`3615f71`) regenerated 99 visual baselines against real per-route content (no longer gate page), 4 baselines flake at `make test-e2e` time. Likely seed-time-dependent content drift: `/analytics` renders "обновлено N мин. назад" relative to `placement.published_at`; `/adv/campaigns/new/channels` and `/admin/users` render dynamic lists whose row order may shift. mobile-webkit historically more visual-diff sensitive than chromium engines.

**Closure trigger:**
- (a) Per-route triage: compare regen-time PNG vs test-e2e-time PNG, identify differing pixel regions.
- (b) Mitigations available: tighten `mask:` regions on dynamic text; freeze `Date.now()` at a fixed timestamp in global setup; sort lists by stable key.
- (c) Re-regenerate baselines after mitigations, verify stable across multiple stack-up cycles.

**Effort:** 1–2 hours (per-route triage).
**Priority note:** low — test-infra flake; not a production regression.

**Refs:** BL-107 PROMPT 45 Extension-of-Extension residual R10, `3615f71` (R8 regen baseline).

**Owner:** _unassigned_

## Closed items

### BL-052 — 15.13.1 micro-cleanup (CLOSED 2026-04-29)

3 surface'нутых из 15.13 closure отчёта, scope-bounded follow-up:

- Renamed `InvalidSignatureError` → `WebhookAuthError`. YooKassa использует
  IP whitelist (not HMAC); previous name implied cryptographic signature,
  misleading future maintainers.
- `YookassaService.get_payment_status` return type honesty: `str` →
  `str | None`. SDK без type stubs возвращал `Any` (mypy молчал, Pyright
  flag'ал после edit). Single caller (`bot/handlers/billing/billing.py`)
  обрабатывает None case явно (warning + "статус неизвестен" UX).
- `amount_paid` unused unpack в `buy_credits` endpoint removed. Verified
  semantics: `BillingService.buy_credits_for_plan` deducts ровно `amount_rub`
  или raises `InsufficientFundsError` — нет partial credit / discount /
  promo logic. Не money-bug; redundant unpack убран целиком (return value
  не нужен, только side effect).

**No baseline reductions claimed** — оба type/unused issues были below
mypy detection threshold (Any-pollution / tuple-unpack F841 gap). Defensive
cleanup + type honesty, not baseline improvement.

**Distortion source:** v1 промта 15.13.1 интерпретировал code observations
из 15.13 closure отчёта как tool-flagged baseline issues и заявлял
`mypy: 10 → 9`, `ruff: 21 → 20`. Шаг 0 empirical verification surface'ил
mismatch; v1 прерван на Шаг 0, v2 переписан без false claims. BL-015
паттерн.

Closed series 15.x окончательно — 9 промтов deployed (15.5–15.13 + 15.13.1).

Closed in commit <sha after Шаг 6>.

### BL-064 — `charge_balance_for_plan` canonical enum alignment + expense analytics fix (CLOSED 2026-05-01)

API path `/api/billing/credits` (`charge_balance_for_plan`) writes
Transaction rows для plan purchases. До этого fix писал
`type=spend` + `meta_json["type"]="plan_payment"` (orphan
discriminator, 0 functional consumers). Bot path
(`bot/handlers/billing/billing.py:275`) уже использовал canonical
`TransactionType.plan_purchase` без meta discriminator — две writer-side
ветки писали один и тот же бизнес-факт по-разному.

Fix:
- Switch enum к `TransactionType.plan_purchase` (match bot path).
- Drop orphan `meta_json["type"]="plan_payment"` key.
  `meta_json["currency"]="rub"` preserved.
- Add `"plan_purchase"` к `_EXPENSE_TX_TYPES` в `analytics.py` —
  раньше plan purchases (как bot- так и API-originated) silently
  invisible cashflow expense reporting (set listed только `"spend"`).

Pre-prod state: `transactions` row count = 0 → no data migration.

Out of scope (deferred): `activate_plan` dead code (lines 191-284) —
аналогичный misfit pattern, 0 callers, slated for deletion в Промт-15
со введением `PlanChangeService`.

Commit: `c9a44d6` (merge `b924e7d`).

### BL-066 — Split bot↔API HMAC secret из BOT_TOKEN (CLOSED 2026-05-01)

Defence-in-depth — раздельные trust boundaries чтобы leak в одном
канале не unlock'ил другой:

- `BOT_TOKEN` — auth между bot и Telegram (aiogram + init_data verify).
  Compromise → attacker speaks к Telegram as the bot.
- `BOT_API_HMAC_SECRET` — auth между bot и local API для
  exchange-bot-token-to-portal call. Compromise → attacker mints
  portal-login URLs.

Scope:
- New required Settings field `bot_api_hmac_secret`.
- Parameter rename `bot_token → hmac_secret` в
  `src/api/auth_bot_hmac.py` (`verify_bot_request_signature`,
  `sign_bot_request`).
- Call-site updates: `src/api/routers/auth.py`,
  `src/bot/utils/portal_deeplink.py`.
- Test refresh, `.env.example` / `.env.test.example` /
  `docs/AAA-09` extended.

**Breaking change для deployment:** production `.env` must provision
`BOT_API_HMAC_SECRET` (`openssl rand -hex 32`) before bot restart;
no fallback to `BOT_TOKEN`.

**Deploy verification (2026-05-01):** production secret provisioned;
bot container Required `docker compose up -d bot` (NOT `restart bot`)
to pick up env_file change. См. BL-071 — process finding o restart vs
up -d divergence.

Commit: `89d0c12` (BL-055 merge `2c0d799`).

### BL-067 — Remove `routers/__init__.py` re-exports (CLOSED 2026-05-01)

Background: re-exporting `from .auth import router as auth` shadowed
submodule path `src.api.routers.auth` — name resolved к APIRouter
object, не к module. Surfaced во время BL-055 implementation когда
integration test нуждался `importlib.import_module(
"src.api.routers.auth")` workaround for monkeypatch resolution.

Scope:
- `src/api/routers/__init__.py` emptied (только module docstring
  explaining convention).
- BL-055 test workaround replaced с idiomatic `from src.api.routers
  import auth as auth_module`.
- Production callers уже использовали explicit imports (verified via
  grep — zero shadowed-name consumers в `src/main.py` и др.).

Module resolution proof: `import src.api.routers.auth; type(...)`
теперь возвращает `<class 'module'>` (был APIRouter перед fix).

Baselines: pytest 76 failed / 780 passed / 6 skipped / 17 errored
exact match с post-BL-066. Ruff/format clean. App startup: 144 routes
registered.

Commit: `379fe8e` (merge `69dbc79`).

### BL-068 — Docs fix: `alembic.docker.ini` → `alembic.ini` references в .md (CLOSED 2026-05-01)

Surfaced во время BL-067 implementation: запуск
`alembic -c alembic.docker.ini upgrade head` внутри api container
fail'нул "script_location not found" — потому что внутри container
file mounted as `/app/alembic.ini` (rename-via-bind-mount), не
`alembic.docker.ini`. Active .md документация (CLAUDE.md, QWEN.md,
docs/AAA-03, docs/AAA-09) misled user относительно правильной
in-container invocation.

Scope (4 files, 10 active instruction replacements):
- `CLAUDE.md`, `QWEN.md`, `docs/AAA-03_DATABASE_REFERENCE.md`,
  `docs/AAA-09_DEPLOYMENT.md`.
- 2 HISTORICAL occurrences оставлены (factual references к существованию
  файла — на тот момент файл всё ещё existed).

Out of scope (handled later):
- BL-069 — docker-compose mount source consolidation.
- BL-070 — `alembic.docker.ini` file deletion + inventory update.
- `.qwen/PROJECT_SKILLS.md:127` missed hit (outside .md glob scope of
  this prompt) — plugged в BL-069.

Commit: `cdc2f7f` (merge `742b9b4`).

### BL-069 — docker-compose mount consolidation на canonical `alembic.ini` (CLOSED 2026-05-01)

PR1 of 2 в alembic config consolidation. Repo had two functionally
identical alembic config files (`alembic.ini` local-dev canonical,
`alembic.docker.ini` Docker mount source) differ только single
comment line near `sqlalchemy.url`. 3 docker-compose mounts (bot, api,
seed-test) bind-mounted `alembic.docker.ini` as `/app/alembic.ini` в
containers (rename-via-mount).

Scope:
- 3 docker-compose mount sources switched: `./alembic.docker.ini` →
  `./alembic.ini` (`docker-compose.yml:60` bot,
  `docker-compose.yml:220` api, `docker-compose.test.yml:56`
  seed-test).
- `alembic.ini` comment uplifted к combined precise: "DATABASE_URL
  from environment, fallback к settings.database_url_sync".
- `.qwen/PROJECT_SKILLS.md:127` plugged (missed hit от BL-068
  cdc2f7f).

Empirical safety:
- `docker compose config --quiet` validation passed both files
  post-edit.
- `ConfigParser` parses `alembic.ini` cleanly (10 sections).
- Container internal path `/app/alembic.ini` unchanged → in-container
  alembic команды не affected source switch.

Aborted-attempt context: ранее в session attempted прямое удаление
`alembic.docker.ini`; Type 4 HARD STOP'нут в research phase когда
discovered file was load-bearing bind-mount source. PR1+PR2 (BL-069 +
BL-070) decoupled path был correct: PR1 makes file legitimately
not-load-bearing, PR2 deletes после empirical post-deploy verification.

Commit: `e577c7d` (merge `6ca5141`).

### BL-070 — Remove orphaned `alembic.docker.ini` + file inventory update (CLOSED 2026-05-01)

PR2 of 2 в alembic config consolidation. После BL-069 production
deploy + смок-проверка in-container alembic
(`alembic -c alembic.ini current` → `e6a88faa9fa0 (head)`,
`alembic -c alembic.ini check` → `No new upgrade operations detected.`),
`alembic.docker.ini` orphaned — no remaining tracked non-.md
references. Safe to delete.

Scope:
- `alembic.docker.ini` deleted (`git rm`); 647 bytes, tracked since
  `97bb7b4` (S-01 initial public stage).
- `01_file_inventory.md:406-407` — row removed (D2 approach (i) —
  flat table, standalone row); `alembic.ini` description uplifted к
  упомянуть "mounted into Docker containers as `/app/alembic.ini`".

Post-deletion verified: только два historical CHANGES files
(`CHANGES_2026-05-01_docker-compose-alembic-ini-consolidation.md`,
`CHANGES_2026-05-01_docs-alembic-ini-fix.md`) ссылаются на имя —
legitimate immutable historical records.

Commit: `5bb291b` (merge `c93cc3c`).

### BL-071 — Process finding: `docker compose restart` does NOT re-read env_file (process-finding)

**Surface:** BL-066 production deploy (2026-05-01) — после
`docker compose restart bot` контейнер всё ещё crash-loop'ил с
`BOT_API_HMAC_SECRET missing`, хотя `.env` корректно содержал secret и
`docker run --env-file .env` (alpine probe) loading'ал переменную
правильно. `docker compose up -d bot` (recreate container) сразу
зафиксил — env_file перечитывается только при создании контейнера, не
при restart существующего.

**Implication для CLAUDE.md и AAA-09 deployment runbook:** правило
"restart bot picks up env_file changes" является false. Корректный
паттерн для env_file changes — `docker compose up -d <service>`
(который recreate'ит контейнер если конфиг изменился).

**Acceptance criteria for closure:**
- AAA-09 / CLAUDE.md deployment section updated с правилом.
- Дополнительный note добавлен к `.env` editing workflow в
  contributor docs.

**Status:** OPEN, low-priority docs fix. Не financial/security
блокер.

**Refs:** BL-066, deploy session 2026-05-01.
