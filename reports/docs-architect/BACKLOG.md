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

_Last updated: 2026-04-28 23:10_

## Active items

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

**Status:** Open (16.x territory)
**Found:** `PII_AUDIT_2026-04-28.md` § O.1
**Severity:** Critical (FZ-152, three-way violation)

Bot `src/bot/handlers/payout/payout.py:281-351` accepts 16-digit card /
phone via `message.text`, echoes plaintext в Telegram chat (line 347),
stores plaintext в БД. Triple violation: bot inbound, bot outbound,
plaintext at rest.

**Architectural decision pending Marina:** должен ли bot вообще принимать
payout requisites? По правилу "mini_app never touches ПД" — bot тоже
не должен. Predicted решение → bot payout flow удаляется, web_portal
становится единственным местом для payout setup, в bot — кнопка
"Открыть в портале" по образцу `OpenInWebPortal`.

**Pickup:** серия 16.x.

### BL-046 — CRIT-2: /api/payouts/* accepts mini_app JWT

**Status:** Open (16.x territory)
**Found:** `PII_AUDIT_2026-04-28.md` § O.2
**Severity:** Critical (FZ-152)

`/api/payouts/*` endpoints используют `CurrentUser` (both audiences).
`PayoutResponse.requisites` flows в mini_app JSON heap on `getPayouts()`.
Screen не renders, но в payload есть.

**Fix:** pin endpoints к web_portal-only auth (Phase 1 pattern,
mechanical).

**Pickup:** серия 16.x (mini-серия 16.1, mechanical fix).

### BL-047 — HIGH-3: DocumentUpload.ocr_text plaintext at rest

**Status:** Open (16.x territory)
**Found:** `PII_AUDIT_2026-04-28.md` § O.3
**Severity:** High (FZ-152)

`DocumentUpload.ocr_text` field stores 10K chars passport OCR text
plaintext. Existing `EncryptedString` infrastructure (legal_profile) —
applicable.

**Fix:** migrate field type → `EncryptedString`.

**Pickup:** серия 16.x.

### BL-048 — HIGH-4: PayoutRequest.requisites plaintext at rest

**Status:** Open (16.x territory)
**Found:** `PII_AUDIT_2026-04-28.md` (Часть 1.2 + § 2.2)
**Severity:** High (FZ-152)

`PayoutRequest.requisites` plaintext в БД. Bank details + card numbers.

**Fix:** migrate field type → `EncryptedString`.

**Pickup:** серия 16.x.

### BL-049 — MED-5: /api/admin/* not pinned к web_portal

**Status:** Open (16.x territory)
**Found:** `PII_AUDIT_2026-04-28.md` § O.4
**Severity:** Medium (FZ-152)

`/api/admin/legal-profiles`, `/users`, `/platform-settings`, `/payouts`
authenticate через `AdminUser → get_current_user` (both audiences).
Должны быть pinned к web_portal-only.

**Fix:** Phase 1 mechanical pattern.

**Pickup:** серия 16.x (mini-серия 16.1).

### BL-050 — MED-6: UserResponse referral leak

**Status:** Open (16.x territory)
**Found:** `PII_AUDIT_2026-04-28.md` § 2.2 (line 115)
**Severity:** Medium (FZ-152)

`UserResponse.first_name/last_name` exposed обоим audiences. Own name
OK, но `GET /api/users/me/referrals` returns other users'
`first_name/last_name` = ПД leak.

**Fix:** filtered serializer для referral context (return только
анонимизированный display name либо username).

**Pickup:** серия 16.x.

### BL-051 — PII audit LOW findings batch

**Status:** Open (16.x territory, low priority)
**Found:** `PII_AUDIT_2026-04-28.md` §§ O.6-O.10
**Severity:** Low

LOW findings batch:
- Dead `LegalProfileStates` (15 states, 0 handlers).
- `mini_app/src/api/payouts.ts::createPayout` exported but unused
  (loaded gun).
- `log_sanitizer` (11 keys) ↔ Sentry scrub (16 keys) divergence.
- `notify_admins_new_feedback` echoes user-typed feedback text.
- YooKassa webhook stores full payload (over-collection).
- `src/bot/handlers/shared/login_code.py:50` logs one-time login code
  in plaintext (CRITICAL по строгости, но out-of-scope PII audit —
  относится к auth, не к данным пользователя).

**Fix:** batched cleanup в серии 16.x mini-task.

**Pickup:** серия 16.x cleanup phase (16.5).

## Closed items

_(none yet)_
