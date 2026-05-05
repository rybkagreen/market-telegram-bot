# T1.2.2 closure — mechanical bulk + C16 mock semantics

Date: 2026-05-05
Branch: feature/t1-2-test-failures-cleanup
Predecessor: T1.2.1.2 8dc2357
Status: in-progress (per-cluster sections landed incrementally; final summary appends на Шаг 8)

## Marina decisions (probe → Phase C)

- **D1:** C10 SQLite (1F) deferred к T1.2.4 — architectural cleanliness (relocate territory owns file)
- **D2:** 7 commits one-per-cluster — single shape, bisect-friendly, granular re-baseline
- **D3:** L45 recorded preventively (mock-leakage recipe)
- **D4:** C8 belt-and-suspenders router source read pre-rewrite
- **D5 (Шаг 1 → Шаг 2 mid-execute):** interleaved CHANGES per cluster — replaces "all CHANGES в Шаг 8" approach. Mitigates stop-hook fire spam (см. L46 в Шаге 8).

## Cluster closures

### C6 await (T1.2.2.1)

- **Commit:** `b562acc`
- **File:** `tests/unit/test_content_filter.py`
- **Type/Count:** 7F → 0
- **Fix:** 7 test methods converted к `async def`, 8 await additions (2 в `test_check_case_insensitive`).
- **Production reference:** `ContentFilter.check` confirmed `async def` at `src/utils/content_filter/filter.py:131`.
- **Re-baseline post:** 79F / 947P / 10S / 8E (delta -7F +7P).

### C7 fixture rename (T1.2.2.2)

- **Commit:** `<this commit SHA — placeholder; canonical в Шаге 8 commits index>`
- **File:** `tests/test_counter_offer_flow.py` (path corrected — `tests/` root)
- **Type/Count:** 8E → 0
- **Fix:** rename fixture references `test_advertiser` → `advertiser_user`, `test_owner` → `owner_user`. Conftest exposes both at `tests/conftest.py:378, 390`. Selective replace_all on `test_advertiser,` `test_advertiser.id` `test_owner,` `test_owner.id` patterns — preserves test method names like `test_advertiser_accept_counter_sets_final_price` (followed by `_`, not `,`/`.id`).
- **Path note:** file at `tests/` root (NOT `tests/unit/` — audit path drift confirmed; one of 4 cases extending L44).
- **Re-baseline post:** TBD (final table в Шаг 8).
- **Unmasked F surfaced (out of C7 scope):** 4 NEW failures previously hidden by 8E fixture errors:
  - 2× `AttributeError: 'PlacementRequestRepository' object has no attribute 'counter_offer'` (TestCounterOfferServiceFix1) — repo method drift (C15-similar pattern на different repo)
  - 2× `404 Not Found` для `GET /api/v1/placements/{id}` (TestCounterOfferAPIFix2/Fix7) — URL drift (C8-similar pattern на different endpoint)
  - These are NOT в T1.2.2 audit scope. Hand forward к next sub-block decision (likely T1.2.3 или separate audit cluster). Net delta для Шаг 2: -8E +4F.

<!-- Шаги 3-7 append cluster sections above this comment. Шаг 8 replaces this comment with final summary block. -->
