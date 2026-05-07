# T1.2.5g — Content_filter stability mini

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07
**Pre-state HEAD:** f133c74
**Pre-state baseline:** 12F / 981P / 3S / 0E + 7 lint (conftest) / 0 format / 4 mypy (mediakit)
**Post-state HEAD:** 2379531 (test file mock); closure commit appends docs only
**Post-state baseline:** 12F / 981P / 3S / 0E + 7 / 0 / 4 / exit 2 (unchanged — flake eliminated, baseline preserved)
**Status:** closed

## Marina decision

Option (a.1) — inline `patch` per affected test. Scope confined к `tests/unit/test_content_filter.py`. No `src/` change, no new dependencies, no mark conventions.

Rejected alternatives + rationale: (b) flaky-retry workaround conflicts с Principle 3, (c) skip loses valid coverage, (d) integration-marker practically equivalent к skip (no CI runner per BL-017), (e) MISTRAL_STUB в src/ has security concerns + biggest scope, (f.x) variants — see `tmp/t1_2_5g_design_options.md`.

## Commits

### Commit 1 — `docs(t1.2.5g): create placeholder CHANGES для interleaved updates`
- Hash: 4c404e6
- Files: reports/docs-architect/discovery/CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md (NEW, +31 LOC)

### Commit 2 — `test(content_filter): mock Mistral L3 в 3 LLM-dependent tests (a.1)`
- Hash: 2379531
- Files: tests/unit/test_content_filter.py (+31/-6 LOC)
- Mock target: `src.core.services.mistral_ai_service.MistralAIService.moderate_content` (class-level patch — inherited by lazy singleton). Empirically verified via `pytest tests/unit/test_content_filter.py -v` → 30/30 PASSED.
- Tests deflaked: `test_check_blocked_text`, `test_check_mixed_text`, `test_check_case_insensitive`.
- Other 27 tests in file: unchanged (5 deterministic by L1/empty early-exit; 22 sync regex/morph/dataclass).
- Verify gate after commit 2: pytest 12F / 981P / 3S / 0E, lint 7, format 0, mypy 4, ci-local exit 2 — **baseline preserved.**

### Commit 3 — `docs(t1.2.5g): closure CHANGES finalize + tmp cleanup`
- Hash: <set during commit>
- Files: reports/docs-architect/discovery/CHANGES_2026-05-07_t1-2-5g-content-filter-stability.md (modified — finalization), tmp/t1_2_5g_*.md (4 files DELETED).

## Deferred to production launch

- **`src/constants/content_filter.py` drift** — declares `LEVEL2_THRESHOLD = 0.3`, `LEVEL3_THRESHOLD = 0.5`, but `filter.py` overrides к `0.15 / 0.7`. Constants file unused (verified: not imported by `filter.py`). Investigation для отдельного sub-block: либо delete file (preferred), либо align values + import-from-constants pattern. Surface only — не related к flake.

- **`MistralAIService.moderate_content` blanket-except → fail-open** (mistral_ai_service.py:194-252) — catches ВСЕ `Exception` types и returns `MistralModerationResult(passed=True, score=0.0, categories=[], analysis="")` fallback. Создаёт second failure mode для `test_check_blocked_text` beyond L3 timeout. Investigation для отдельного sub-block: должен ли catch только specific exceptions (rate limit, network, parse)? Sentry capture без silent fallback? Production behavior implication.

- **Future LLM-dependent tests should use same `(a.1) inline patch` pattern.** Marker convention (e.g. `@pytest.mark.requires_external_llm`) deferred until second LLM-test surface emerges (YAGNI).

## Verification footer

🔍 Verified against: 2379531 | 📅 Updated: 2026-05-07T22:00:00Z
