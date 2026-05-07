# T1.2.6 — Placement-flow cluster + ESCROW false-positive

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07
**Pre-state HEAD:** 773eb38
**Pre-state baseline:** 12F / 981P / 3S / 0E + 7 lint (conftest) / 0 format / 4 mypy (mediakit)
**Status:** in-progress (commit 5 finalizes)

## Marina decisions

- **Cluster 1 (ESCROW invariant):** β — multi-callsite allowlist (publication_service.py + disputes.py advertiser_fault branch); AST or strict-regex comment-strip implementation, agent выбирает по ergonomics.
- **Cluster 2 (reputation FK ×4):** α — root `tests/conftest.py` shared fixture; 4 reputation tests refactored.
- **Cluster 3 (review INV-1 ×1):** α — status switch in test_review_service fixture (1 LOC); KISS, NOT reuse Cluster 2 fixture.

Rejected:
- ε delete (Cluster 1) — invariant still has defensive value via allowlist.
- β AST-only / γ inline (Cluster 2) — fixture sharing wins на reuse + DRY.
- β C5 wholesale / γ Cluster 2 reuse (Cluster 3) — over-engineering.

## Commits

### Commit 1 — `docs(t1.2.6): create placeholder CHANGES для interleaved updates`
- Hash: <set during commit>
- Files: reports/docs-architect/discovery/CHANGES_2026-05-07_t1-2-6-placement-flow-cluster.md (NEW)

### Commit 2 — TBD

### Commit 3 — TBD

### Commit 4 — TBD

### Commit 5 — TBD

## Deferred to production launch

(filled by commit 5 finalizer)

## Verification footer

(filled by commit 5 finalizer)
