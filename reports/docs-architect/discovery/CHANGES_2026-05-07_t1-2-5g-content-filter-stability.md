# T1.2.5g — Content_filter stability mini

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07
**Pre-state HEAD:** f133c74
**Pre-state baseline:** 12F / 981P / 3S / 0E + 7 lint (conftest) / 0 format / 4 mypy (mediakit)
**Status:** in-progress (commit 3 finalizes)

## Marina decision

Option (a.1) — inline `patch` per affected test. Scope confined к `tests/unit/test_content_filter.py`. No `src/` change, no new dependencies, no mark conventions.

Rejected alternatives + rationale: (b) flaky-retry workaround conflicts с Principle 3, (c) skip loses valid coverage, (d) integration-marker practically equivalent к skip (no CI runner per BL-017), (e) MISTRAL_STUB в src/ has security concerns + biggest scope, (f.x) variants — see `tmp/t1_2_5g_design_options.md`.

## Commits

### Commit 1 — `docs(t1.2.5g): create placeholder CHANGES для interleaved updates`
- Hash: <set during commit>
- Files: reports/docs-architect/discovery/CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md (NEW)

### Commit 2 — TBD

### Commit 3 — TBD

## Deferred to production launch

(filled by commit 3 finalizer)

## Verification footer

(filled by commit 3 finalizer)
