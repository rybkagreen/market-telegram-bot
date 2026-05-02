# Clarify S-48 — three-pattern taxonomy

**Date**: 2026-05-02
**Branch**: chore/clarify-s48-patterns
**Files**: 1 (CLAUDE.md)
**Origin**: Phase 3a Block 3 caller audit findings (tmp/PHASE3A_BLOCK3_CALLER_AUDIT_2026-05-02.md)

## Context

Block 3 caller audit revealed that the S-48 contract in CLAUDE.md, as
written, did not distinguish three distinct session-lifecycle patterns
coexisting in production code. The previous formulation conflated all three
into "services don't commit", which:

- Misclassified `badge_service` self-contained sites (lines 79, 229, 379) as
  S-48 violations
- Did not document the external-boundary pattern at all (it lived only as a
  Russian inline comment at `publication_service.py:308`)
- Caused a planner-side discovery miss when grep alone was used to identify
  "violations"

## Change

Restructured the S-48 section in CLAUDE.md to name three canonical patterns:

| Pattern | When | Marker required |
|---|---|---|
| 1 — Caller-owns | Default; service receives session, never commits | No |
| 2 — Self-contained | Method opens own session via `async_session_factory()` | `# S-48: self-contained pattern` |
| 3 — External-boundary | Commit pairs with external system idempotency | `# S-48: external-boundary (<reason>)` |

Each pattern documents its rationale, when to use, examples in code, and how
to mark commit sites in code (patterns 2 and 3).

Auditing guidance added: classify by session ownership, not by grep output.

## Out of scope (deferred)

- (M) Architectural fitness test (`tests/architecture/test_s48_compliance.py`,
  AST walk verifying every commit() matches a canonical pattern) — post-Phase-3
  investment, requires stable taxonomy first.
- In-code marker application — Block 3.2 (4 sites: badge_service × 3,
  publication_service × 1).
- Audit of other commit() sites in codebase against new taxonomy — Phase 3
  closure batch.

## No code change

This commit modifies CLAUDE.md only. No production code, no tests, no
migrations. Pure documentation refinement.
