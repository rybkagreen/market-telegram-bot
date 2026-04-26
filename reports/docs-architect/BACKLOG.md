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

## Closed items

_(none yet)_
