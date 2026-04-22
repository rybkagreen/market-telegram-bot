# CHANGES 2026-04-21 — plan-08 E2E fixme tracking

## Scope

Follow-up to `FIX_PLAN_06_followups/plan-08-e2e-fixme-tracking.md`
(P3, housekeeping). Three `test.fixme(true, …)` blocks in
`web_portal/tests/specs/deep-flows.spec.ts` had no trackable owner
and no acceptance criteria for re-activation — they were sliding
toward permanent dead code.

This change formalises them as BL-001 / BL-002 / BL-003 in
`reports/docs-architect/BACKLOG.md` with explicit re-activation
contracts, points the spec back at the BL-IDs, and removes the
empty `test('name', async () => {})` stubs.

Tests / docs / config-only sprint. No `src/` changes.

## Affected files

### New

| File | Purpose |
|---|---|
| `reports/docs-architect/BACKLOG.md` | Top-level project backlog. Three deferred E2E items (BL-001/002/003) with surface point, deferral reason, and acceptance criteria for re-activation. Designed as the single source of truth for "skipped on purpose" work. |
| `reports/docs-architect/discovery/CHANGES_2026-04-21_plan-08-e2e-backlog.md` | this document |

### Modified

| File | Change |
|---|---|
| `.gitignore` | Added `!reports/docs-architect/BACKLOG.md` exception so the new top-level backlog file is tracked despite the broad `reports/*` ignore rule. |
| `web_portal/tests/specs/deep-flows.spec.ts` | All three fixme-describe blocks rewritten: `test.fixme(true, reason)` + empty `test()` → single `test.fixme(title, body)` whose title carries the BL-ID and a path back to BACKLOG.md. The body is reserved for the eventual real implementation; the comment inside it restates the re-activation criterion as a one-line hint. |
| `CLAUDE.md` | Added `## Deferred E2E items (plan-08)` section with the BL-ID table and a rule against adding silent `test.fixme(true, …)` blocks. |

## Why this matters

`test.fixme(true, …)` is a permanent skip with no contract: the
reason field is prose, no one tracks the unblock condition, and
six months later the comment is the only evidence the test ever
existed. The pattern silently degrades the suite — passing CI
makes it look healthier than it is.

The BL-* entries replace prose with executable criteria: each
item names the exact fixture, mock, or refactor that turns the
fixme into a runnable test. A future contributor can pick up
BL-001 without spelunking through git blame.

## Validation

```bash
cd web_portal && npx tsc --noEmit -p tests/tsconfig.json
# → 0 errors

git -C /opt/market-telegram-bot check-ignore reports/docs-architect/BACKLOG.md
# → exit 1 (file is tracked, the !-rule wins)

git status reports/docs-architect/BACKLOG.md
# → ?? reports/docs-architect/BACKLOG.md (visible to git, ready to commit)
```

## Out of scope

- Activating any of the deferred flows. Each unblock task lives in
  its own BL entry and is sized at flow-level effort, not
  housekeeping.
- Migrating BACKLOG to GitHub Issues / Linear. Markdown is good
  enough until the project chooses an external tracker.

🔍 Verified against: a03ddb1 (main) | 📅 Created: 2026-04-21
