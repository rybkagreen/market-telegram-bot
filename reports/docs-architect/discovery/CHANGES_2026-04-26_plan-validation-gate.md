# CHANGES — 2026-04-26 — Plan Validation Gate (phase-discipline rule)

## Summary

Added a MANDATORY pre-approval gate to CLAUDE.md that any Phase N plan
must pass before "research → STOP → implementation" handoff. Single docs
commit on `develop` (`7242987`), not a separate phase.

This lifts the **process-finding** from
`CHANGES_2026-04-25_phase1-fz152-hardening.md:270-284` (Phase 1 closure
report) into phase-discipline rules in CLAUDE.md, where it is read at
every plan freeze. CHANGES files are discovery artefacts of a specific
phase — through 2 phases nobody opens them. CLAUDE.md is loaded into
context every session, so process-findings live there.

## Affected files

- `CLAUDE.md` — new subsection "Plan validation gate (MANDATORY before
  approving any Phase N plan)" inserted between "What counts as raise
  explicitly vs defer" and the Documentation & Changelog Sync section
  (3 checks, ~34 lines added).

## Rule contents

Three checks before any Phase N plan is approved:

- **(a) `tsc --noEmit` dry-run** with the plan's strip-list applied to
  `mini_app/` and `web_portal/`. Origin: Phase 1 O.1 — plan said
  "delete `contracts.ts`" but 6 portal screens still imported it.
- **(b) Per-endpoint PII classification** for every endpoint the plan
  switches to web_portal-only auth. File-name heuristics not a
  substitute. Origin: Phase 1 A.2 — `accept-rules` lived in
  `contracts.py` but is non-PII boolean ack.
- **(c) Audit of merged decisions from previous phases.** Diff plan
  text against codebase reality on `develop`. Origin: Phase 0 PF.2 —
  Phase 1 plan still said "401 for aud-less" and "don't touch
  audit_middleware.py" after Phase 0 follow-up reversed both.

Output: a short alignment commit `docs(phase-N): align plan with
PF.X / O.Y decisions` on the feature branch **before** any
implementation commit.

## Business logic impact

None — documentation/process rule only. No source code, no API contract,
no DB schema, no frontend code touched.

## API / FSM / DB contracts

No changes. CHANGELOG.md `[Unreleased]` not updated — no public-contract
delta.

## Verification

- `git show 7242987 --stat` → 1 file changed, 34 insertions, 0 deletions
  (CLAUDE.md only).
- `git log --oneline c40e022..develop` → single commit `7242987`.
- `git push origin develop` → pushed to remote (`c40e022..7242987`).
- Rule first applied in current Phase 2 research design: gate (a)/(b)/(c)
  enumerated as objection #7 in pre-research read-through, all three
  checks scheduled into Phase 2 research-phase prompts (Agent A/B/C +
  consolidation).

## Non-changes (explicit)

- `feature/fz152-legal-hardening` not affected (closed by `b8c54e2`).
- `main` not updated — this is a single docs commit on `develop`, not a
  phase completion. `main` will sweep the change up at next phase merge.
- No new tests added — rule is procedural, enforced by reviewer reading
  CLAUDE.md, not by automation. Future automation candidate: pre-commit
  hook that requires "phase-N plan-alignment commit" sha as ancestor of
  any "feat(phase-N)" commit. Not implemented now (premature).

🔍 Verified against: 724298729905768df038588375206481c9c10d17 | 📅 Updated: 2026-04-26T07:57:13Z
