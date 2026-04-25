# CHANGES 2026-04-25 — Meta rules: objections, phase discipline, raise-vs-defer

## Scope

Documentation-only update to project-wide collaboration rules. No `src/`,
`tests/`, `mini_app/`, `web_portal/`, schema, migration, or runtime
behaviour changes. No public API contract changes.

Triggered by Phase 0 research-stop-point review where the consolidation
report was found to (a) rubber-stamp a known-imprecise plan directive
(STUB-ERID vs TEST-ERID) and (b) propose a "WARN-and-accept" legacy JWT
fallback that defeats the purpose of the new `aud` claim. User feedback
demanded explicit rules so future research reports surface objections
loudly instead of disguising them as confirmation questions.

## Affected files

- `CLAUDE.md` — new section **"Research reports — Objections section
  (MANDATORY)"** inserted before **"Documentation & Changelog Sync"**.
  Three sub-sections:
  - The base rule: research reports must contain a "Возражения и риски"
    section *before* the "Вопросы для подтверждения" section. Five
    explicit categories of issues are listed (security holes, internal
    contradictions, missed edge cases, bad naming, API ergonomics traps).
    Disguising objections as clarifying questions is explicitly
    prohibited.
  - **Phase mode discipline** — codifies two operating modes:
    *research/planning* (be critical, dispute decisions with reasoning)
    and *implementation* (execute the agreed plan, stop only on blocking
    issues, no scope creep). The expected output of each mode is named.
  - **Raise-vs-defer split rule** — four categories of issues that must
    be raised explicitly (security, bugs, contradictions, future-
    maintenance burden) versus five categories that go into a single-line
    "возможные дальнейшие улучшения, не требуют действий сейчас" footnote
    (cosmetic refactors, style nits, untouched-code coverage gaps,
    unmeasured perf optimisations, naming preferences). The split rule:
    "if a future maintainer would shrug at the issue, defer it; if they
    would have to redo significant work or hit a real incident, raise it."

- `IMPLEMENTATION_PLAN_ACTIVE.md` — same three rules mirrored into the
  "Общие правила (копируются в каждую сессию)" block at the top of the
  plan, so each phase's resume prompt picks them up automatically without
  depending on `CLAUDE.md` being re-read.

- `IMPLEMENTATION_PLAN_ACTIVE.md` — Phase 0 sections (0.A, 0.B.1, 0.B.2,
  0.B.3, 0.C, 0.D) rewritten to bake in the security-hardened decisions
  produced during the consolidation review (separate change of substance,
  documented under its own header below).

## Phase 0 plan revisions (separate from the rule additions)

The plan's Phase 0 was edited to reflect concrete decisions made during
the consolidation review. Substantive changes vs. the prior plan text:

- **0.A.bis (new)** — research findings frozen so the next session does
  not re-run the three Explore agents.
- **0.B.1** — explicit file/line targets:
  - delete `src/config/__init__.py` entirely (verified dead — zero `from
    src.config import` callers across `src/` and `tests/`);
  - delete `environment` field + `is_development/is_production/is_testing`
    properties from `src/config/settings.py`;
  - replace `if settings.environment == "testing"` at
    `src/api/main.py:193` with `if settings.enable_e2e_auth`;
  - new `enable_e2e_auth: bool` setting with `ENABLE_E2E_AUTH` alias;
  - drop `ENVIRONMENT=` from `.env`, `.env.example`, `.env.test`,
    `.env.test.example`;
  - remove `environment` key from `/health` JSON response.
- **0.B.2** —
  - constants location: `src/constants/erid.py` inside the existing
    `src/constants/` package (option A from the consolidation report).
    *Not* `src/core/constants.py` as the original plan literally said —
    no parallel package.
  - `ERID_STUB_PREFIX = "STUB-ERID-"` retained as the canonical name.
    The original plan asked to rename to `TEST-ERID-`; this is rejected
    on semantic grounds (STUB describes the *provider type*, TEST would
    describe the *placement mode* — two different concepts. Phase 5 is
    the right place to introduce a placement-mode marker if needed).
  - typo fix `rekhaborbot.ru → rekharbor.ru` in `src/constants/legal.py`
    (4 occurrences at lines 53, 83, 107, 108) — surfaced by the inventory
    agent.
  - frontend: remove the `|| 'https://rekharbor.ru/portal'` fallback in
    both `mini_app/src/screens/common/LegalProfile{Setup,Prompt}.tsx:8`
    and add `VITE_PORTAL_URL` to `mini_app/.env`, `mini_app/.env.example`,
    and the `nginx/Dockerfile` build args. Verified the env var is not
    set anywhere today, so the fallback is the actual production URL —
    a hidden hardcode masquerading as configuration.
- **0.B.3** — security-hardened JWT bridge:
  - `decode_jwt_token(token, audience)` — `audience` becomes a *required*
    positional argument (no default). Callers must explicitly decide.
    `audience=None` remains valid as an explicit opt-out for legacy/audit
    helpers but cannot happen by accident.
  - Legacy aud-less JWTs in production dependencies → **401**, not
    "WARN-and-accept". Pre-prod has few users; one re-login is acceptable
    and removes a real auth-confusion vulnerability.
  - `get_current_user_from_web_portal()` always passes
    `audience="web_portal"` — no fallback path that could let a
    mini_app-issued JWT through.
  - `POST /api/auth/consume-ticket` gains rate-limit and replay-protection
    requirements: 10 req/min/IP, 5 fail/5min/user, structured logs on
    every 4xx (`event=ticket_consume_failed`, reason, ip, jti_prefix).
    Implementation must avoid adding `slowapi` if it isn't already a
    dependency — manual Redis `INCR + EXPIRE` is two lines.
  - JTI Redis value upgraded from `"1"` to JSON
    `{"user_id", "issued_at", "ip"}` so future revocation/audit isn't
    blocked on missing context.
  - `audit_middleware.py` not modified this phase, but a `FIXME`
    comment + a `reports/docs-architect/BACKLOG.md` entry must be added
    (the middleware decodes JWTs without signature verification; safe
    today because it runs after auth dependencies, but the technical
    debt should be visible).
- **0.C** — acceptance test count raised from 3 to **8 functional + 2
  rate-limit cases** with each scenario named (legacy aud-less rejected,
  mini_app→web_portal rejected, full flow, expired ticket, replay,
  Redis-flush simulation, IP rate-limit, per-user-fail rate-limit).
  Static checks expanded: `grep` guards on `settings.environment`,
  `rekhaborbot`, in-source `rekharbor.ru` literals.

## Public contracts

None changed by this commit. The Phase 0 implementation (separate later
commits) will introduce:
- `TicketResponse` and `AuthTokenResponse` Pydantic schemas
  (`src/api/schemas/auth.py`).
- Two new endpoints: `POST /api/auth/exchange-miniapp-to-portal` and
  `POST /api/auth/consume-ticket`.
- Revised `decode_jwt_token` and `create_jwt_token` signatures.
- New `get_current_user_from_web_portal` dependency.

These are listed for traceability and will land in their own
`CHANGES_*.md` after 0.B/0.C complete.

## Migration notes

None. This commit edits only project documentation. No DB schema, no
Alembic migration, no Celery task signature, no API contract.

## Why these rules exist (context for future sessions)

The Phase 0 research consolidation initially proposed two
security-relevant compromises (legacy aud-less JWTs accepted with WARN;
unauthenticated `/consume-ticket` without rate-limit) and rubber-stamped
the plan's STUB→TEST rename despite a clear semantic mismatch. The user
flagged all three. The new rules formalise the lesson:

1. Surface *all* objections in their own labelled section, not buried in
   the questions block.
2. Respect mode boundaries — be combative during planning, disciplined
   during implementation.
3. Distinguish blocking issues (raise) from cosmetic ones (defer to a
   one-line footnote) so the signal-to-noise ratio of objections stays
   high.

The intent is to reduce the chance that a future research report quietly
ships a security hole because the reviewer felt obliged to defer to the
plan author.

## Not verified

- Hooks did not run on this commit because no `src/` or test files
  changed. Lint, typecheck, and tests are not applicable.
- These docs files are not consumed by CI or by the Python runtime, so
  there is no executable surface to validate.

🔍 Verified against: 59908b7 | 📅 Updated: 2026-04-25T00:00:00Z
