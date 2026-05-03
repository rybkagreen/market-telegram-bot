# Engineering Principles — codified in CLAUDE.md

**Date**: 2026-05-02
**Branch**: chore/engineering-principles
**Files**: 1 (CLAUDE.md) + 1 (this CHANGES)
**Origin**: Marina decision following Phase 3a Foundation closure; lessons L8-L13 surfaced need for standing principles document, not per-prompt repetition.

## Context

Phase 3a Foundation surfaced six lessons (L8-L13) that share a common
shape: they are not project-specific facts, they are agent-workflow
principles. Codifying them per-prompt scaled poorly — each prompt
repeated them, drift accumulated, and one missed prompt (Block 3
original) led to a discovery miss that required reframing.

These principles belong in CLAUDE.md as standing rules visible to
every future agent session, not in one-shot prompts.

## Change

Added top-level section "Engineering Principles" к CLAUDE.md:

| Principle | Summary |
|---|---|
| 1 | Architectural cleanliness over schedule (within sub-block) |
| 2 | Three-phase workflow (Investigate → Re-evaluate → Execute) for non-trivial tasks |
| 3 | No workarounds (operational definition + escape hatch via root-cause investigation) |
| 4 | Once-correctly over twice-iteratively |
| 5 | Conflict handling (safety + S-48 + Marina decisions win; time heuristics lose) |

Plus auditing self-check the agent runs before each commit.

Minor consistency edits:

- BL-013 stop-hook relay: defer options (b)/(c) now explicitly scope-marked
  to documentation bundling, not code quality
- "No autonomous multi-phase delegation" memo: updated to reflect sub-block
  autonomy boundaries when prompt-authorized; default remains stop-at-sub-block

## Out of scope (deferred)

- (M) Architectural fitness test — unchanged, post-Phase-3 investment
- L8-L11, L13 codification (memory-only lessons that have not yet hit
  CLAUDE.md) — Phase 3 closure batch territory; this commit codifies
  the meta-principles, not each individual L lesson
- BACKLOG.md updates — Phase 3 closure batch
- Adjustments to project-specific BLs (BL-007, BL-016 hook acks, BL-028)
  — out of scope; this is process meta-rules only

## No code change

CLAUDE.md + CHANGES file only. No production code, no tests, no
migrations. Pure process documentation.

## Notes

This sits alongside S-48 three-pattern taxonomy (added by
`chore/clarify-s48-patterns` earlier this cycle) as the second of two
standing-rules edits to CLAUDE.md в Phase 3a window. Future sessions
inherit both without per-prompt restatement.
