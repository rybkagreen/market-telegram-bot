# CHANGES — Phase 2 closure

## What

Administrative closure of Phase 2 (PlacementTransitionService unified
mutation point). Drains the 16 BACKLOG entries accumulated during Phase 2
into the committed BACKLOG.md, codifies 8 process-findings into CLAUDE.md
as actionable rules, and marks Phase 2 complete in CHANGELOG.

No code under `src/`, `tests/`, `mini_app/`, `web_portal/`, or `landing/`
is touched. Docs-only commit. No migrations, no deploy needed.

## Affected files

- `reports/docs-architect/BACKLOG.md`
  - Already-modified working-tree state (BL-006…BL-027, 16 entries)
    committed as part of this closure.
  - Two new entries appended: BL-028 (pytest baseline scope confusion),
    BL-029 (api container port not host-mapped).
  - Final BL count: 28 entries (BL-001..BL-029, BL-020 historically
    skipped — entry was renumbered during Phase 1).
- `CLAUDE.md`
  - New section "Process discipline (added from Phase 2 lessons)"
    inserted between the existing "Plan validation gate" subsection
    and "Documentation & Changelog Sync" — synthesises 8 BL records
    into actionable rules for future sessions.
- `CHANGELOG.md`
  - Existing `[Unreleased]` heading renamed to
    `[Phase 2 complete — 2026-04-27]` (the block was already populated
    with all Phase 0/1/2 unreleased work — relabelling, not rewriting).
  - New empty `[Unreleased]` heading added on top with the placeholder
    `_(none yet — Phase 3 candidate selection pending)_`.
- `reports/docs-architect/discovery/CHANGES_2026-04-27_phase2-closure.md`
  - This file.

## Commits

- `<SHA>` — `docs: phase 2 closure — backlog drain + claude.md lessons`
  (single docs-only commit on `develop`).
- `<SHA>` — merge commit `develop → main` (`merge: phase 2 closure (docs)`).

## BACKLOG drained

28 entries total at closure (`grep -c "^### BL-" reports/docs-architect/BACKLOG.md` = 28).

Categorised:

- **Process-findings → integrated into CLAUDE.md:** BL-006, BL-007,
  BL-013, BL-015, BL-016, BL-018, BL-024, BL-026, BL-028.
  See "Process discipline (added from Phase 2 lessons)" section in
  CLAUDE.md for the synthesised rules.
- **Test-debt → deferred to Phase 4 test-health epic:** BL-019,
  BL-022, BL-023, BL-027.
- **Latent infra issues → deferred:** BL-021 (`.env` DATABASE_URL
  hostname), BL-025 (DB-level CHECK constraint), BL-029 (api port
  documentation gap — opportunistic).
- **Frontend / mobile E2E (long-standing):** BL-001 (dispute round-trip),
  BL-002 (channel add via bot verify), BL-003 (KEP signature),
  BL-004 (`tests/` mounted into api image), BL-005
  (`/api/acts/*` portal wiring).
- **PII / FZ-152:** BL-009 (audit_logs retention), BL-010 (Sentry
  breadcrumb scrub), BL-011 (rejection_reason review), BL-012
  (Transaction.description drift).
- **Closed / accepted in this session's working tree:** BL-008
  (INVALIDATED 2026-04-26), BL-014 (correlation_id wiring — Phase 3
  scope), BL-017 (GH Actions accepted-inert).
- **Process additions this session:** BL-028 (pytest scope), BL-029
  (api port).

## CLAUDE.md additions

New top-level section `## Process discipline (added from Phase 2 lessons)`
inserted before `## Documentation & Changelog Sync (MANDATORY)`. Six
actionable rule blocks synthesised from BL-006/007/013/015/016/018/024/026/028:

1. **Plan validation gate — extended.** Adds gates (d) ruff baseline
   diff, (e) cross-artifact reference check, (f) test infrastructure
   surface, (g) mutation-audit completeness — extending the existing
   (a/b/c) gates without replacing them. Plus the rule that
   research-agent enumerations are incomplete-by-default and must be
   re-greped at § B.1 of any phase plan.
2. **Stop-hook relay protocol.** Three-way user choice (immediate /
   bundle / defer), loop-firing tolerance (ack twice non-trivially,
   then silent-ignore), STOP gate applies to every commit including
   docs/chore.
3. **Cross-artifact reference fabrication.** `grep` for any cross-ref
   before committing.
4. **Stale plan vs reality.** Plan line numbers are HINTS; sub-agents
   work by signature/content; surface drift explicitly instead of
   silently adapting.
5. **Verification gate language.** "Local `make ci-local` passes
   against baseline X (failed=N1, errored=N2, …)" — not "CI green",
   not bare numbers without invocation.

## CHANGELOG entry

`[Unreleased]` block (which had accumulated all Phase 0 + Phase 1 +
Phase 2 work since the last release) renamed to
`[Phase 2 complete — 2026-04-27]`. New empty `[Unreleased]` heading
added on top as a placeholder for Phase 3 work.

The renamed block contents (unchanged, just relabelled) cover:

- PlacementTransitionService unified mutation point.
- 22+ caller migrations consolidated through the service.
- `placement_status_history` audit table.
- `scripts/check_forbidden_patterns.sh` extended with three Python
  guards (status mutation patterns).
- Three dead modules removed (`dispute_tasks.py`,
  `retry_failed_publication`, `process_publication_success`).
- Pre-Phase-2 hotfixes (expires_at consistency, regression guards,
  data-loss task removal).
- Phase 1 mini_app FZ-152 strip + TicketLogin + OpenInWebPortal bridge
  (kept here because all of it was unreleased).
- Phase 0 env-constants + JWT closure (kept here for the same reason).

## Public contract delta

None. No API/FSM/DB schema change. No new endpoints, no removed
endpoints, no field renames.

## Process-findings carried forward to Phase 4+

Codified in BL-019/021/022/023/025/027 (test-debt and latent infra).
None of these block production. None require Phase 3 attention beyond
opportunistic touch-ups.

## Origins

- Phase 2 implementation per `IMPLEMENTATION_PLAN_ACTIVE.md` § 2.B
  (decisions 1, 2, 4, 5, 10, 11, 12).
- Closure work per project workflow standard
  ("administrative closure of phase before opening next").

🔍 Verified against: `282c39b89e46464c84ec2e2857cd09b51891e390` |
📅 Updated: 2026-04-27T19:15:54Z
