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

### C15 method rename + API drift (T1.2.2.3) — DEFERRED

- **Status:** deferred к T1.2.5 или T1.2.6 (sub-block owner TBD)
- **File:** `tests/test_channel_settings_repo.py` (path corrected — `tests/` root)
- **Type/Count:** 3F deferred (NOT closed in T1.2.2)
- **Reason:** Pre-fix verification revealed audit shape drift. Audit classified as "method rename"; actual is deeper API drift:
  - Production `ChannelSettingsRepo.get_or_create(self, channel_id: int)` — single arg, no `owner_id`
  - `ChannelSettings` model has no `owner_id` column (only `channel_id`)
  - `upsert` method не существует на repo
  - 3 tests pass `channel_id=..., owner_id=owner_user.id` к `get_or_create_default(...)`; 1 test calls `upsert(channel_id=..., owner_id=..., price_per_post=...)`.
- **Decision required (sub-block owner):** should production grow API (`upsert` + `owner_id` ownership-scope) OR should tests rewrite expectations к current `get_or_create(channel_id)` semantics? Production-source change запрещён в T1.2.2 sub-block prohibitions.
- **L44 pattern:** another audit-classified-mechanical cluster hiding deeper drift. Shape verification per cluster pre-fix остаётся mandatory.

### C14 enum split + token mock (T1.2.2.4)

- **Commit:** `<this commit SHA — placeholder; canonical в Шаге 8 commits index>`
- **File:** `tests/unit/test_sender.py`
- **Type/Count:** 3F → 0
- **Sub-fixes:**
  - **1F enum split** (`test_send_message_forbidden`): production `_handle_forbidden` (sender.py:118) routes `TelegramForbiddenError` к `SendStatus.CHAT_BLOCKED` (split from former conflated `FAILED`). Updated assertion `SendStatus.FAILED` → `SendStatus.CHAT_BLOCKED`. Existing `"forbidden" in error_message.lower()` assertion still passes (`error_message="ChatWriteForbidden: ..."` contains "forbidden").
  - **2F token mock** (`test_create_sender`, `test_sender_close`): production `create_sender` refactored — теперь uses `from src.bot.session_factory import new_bot` (local import inside function); `Bot` no longer referenced at module level в `sender.py`. Tests patched `src.utils.telegram.sender.Bot` — patch resolved nothing, real `Bot("test_token")` instantiation raised `TokenValidationError`. Updated patch target к `src.bot.session_factory.new_bot`. Updated `mock_bot_class.assert_called_once_with` → `mock_new_bot.assert_called_once_with`.
- **Production references:** `src/utils/telegram/sender.py:44-53` (SendStatus enum), `:118` (`CHAT_BLOCKED` branch), `:236-248` (`create_sender` → `new_bot`); `src/bot/session_factory.py:17` (`new_bot`).
- **Re-baseline post:** TBD (final table в Шаг 8).

### C8 URL drift + field rename (T1.2.2.5) — PARTIAL CLOSURE

- **Commit:** `<this commit SHA — placeholder; canonical в Шаге 8 commits index>`
- **File:** `tests/test_api_channel_settings.py` (path corrected — `tests/` root)
- **Type/Count:** 5F production-drift fixed; 5F infra-gap deferred (same count post-fix, error mode changes)
- **Production drift fixed:**
  - 5 URLs: `/api/v1/channels/{id}/settings/` → `/api/channel-settings/?channel_id={id}`
  - 1 field: `start_time`/`end_time` → `publish_start_time`/`publish_end_time` (в `test_patch_invalid_time_order_422`)
  - Verified via 5.1 belt-and-suspenders: mount at `src/api/main.py:195`, router `APIRouter(tags=[...])` без `prefix=`, GET/PATCH `/`, `channel_id: int` — query param (FastAPI default for non-path), Pydantic `extra="ignore"` silently drops unknown fields → field-rename semantic bug surfaced (test asserted 422 но получало 200 после URL fix без field rename).
- **Real failure mode (post-mechanical fix):** `ConnectionRefused 127.0.0.1:5432`. Mechanical drift fix is correct; tests still fail because `tests/conftest.py::api_client_with_auth` (line 472) НЕ устанавливает `app.dependency_overrides[get_db_session]` к test container engine. ASGITransport routes requests in-process; `Depends(get_db_session)` resolves к prod settings.
- **Existing override pattern:** per-test в 3 examples (`tests/integration/test_needs_accept_rules_endpoint.py:48`, `test_api_legal_profile.py:48`, `test_ticket_bridge_e2e.py:159`).
- **Deferred к T1.2.4 (test infra territory):** extension of `api_client_with_auth` fixture с db override OR alternative pattern (per-test override / new fixture). Infra decision needs sub-block owner analysis (impact на other callers, fixture composition strategy).
- **Re-baseline post Шаг 5:** expect 80F → 80F (5F same count, error mode changed from 404 к ConnectionRefused). Production drift work preserved; infra gap transitions к T1.2.4.
- **L44 pattern:** audit-classified-mechanical cluster hiding deeper drift (URL + field + infra). Pre-fix verification + post-fix empirical re-baseline остаются mandatory.

### C10 field rename + SQLite gap + production bug (T1.2.2.6) — DEFERRED CLOSURE

- **Commit:** `<this commit SHA — placeholder; canonical в Шаге 8 commits index>`
- **File:** `tests/unit/test_bmediakit_comparison.py`
- **Type/Count:** 4F → 4S (mechanical edits applied + all 4 skipped с pointers)
- **Mechanical drift fix applied (preserved in committed code, awaiting unblock):**
  - `test_calculate_comparison_metrics` — drop invalid kwargs (`last_avg_views`, `last_post_frequency`, `price_per_post`), route price via `ChannelSettings(channel_id=chat.id, price_per_post=...)`
  - `test_price_per_1k_subscribers_calculation` — same pattern
  - Field migration verified (model side, TelegramChat:54)
- **All 4 tests skipped с explicit reasons:**
  - `test_calculate_comparison_metrics` + `test_price_per_1k_subscribers_calculation`: SQLite gap (creating ChannelSettings rows hits "no such table: channel_settings")
  - `test_get_mediatkit_data`: production bug pointer (см. Deferred to production fix)
  - `test_get_channels_for_comparison`: SQLite gap per D1
- **Phase B surface (probe underestimate):** probe identified 1 SQLite-blocked test; reality is 3. Mechanical "field rename" fix к 2 tests insufficient because they create ChannelSettings rows → hit same SQLite gap as `test_get_channels_for_comparison`.
- **Re-baseline post Шаг 6:** expect -4F +4S (in-file).
- **Owner of unblock:**
  - 3 SQLite-blocked tests → T1.2.4 (relocation per Marina Q4=(a) или fixture extension decision)
  - 1 production-bug test → consolidates к BACKLOG в T1.2 final closure
- **Production migration verified (model side, TelegramChat):**
  - `last_avg_views` → renamed к `avg_views` (line 54)
  - `last_post_frequency` → removed entirely (НЕ synonym; не на model)
  - `price_per_post` → moved к `ChannelSettings.price_per_post`
- **L44 pattern:** field-rename audit underestimated SQLite dependency surface. Mechanical edits изначально казались self-contained; actual ChannelSettings construction triggered fixture gap.

### Deferred to production fix (consolidates к BACKLOG в T1.2 final closure)

- **mediakit_service migration incomplete** — `src/core/services/mediakit_service.py:111-116` reads `chat.last_avg_views`, `chat.last_post_frequency`, `chat.price_per_post`. Model side migrated:
  - `chat.last_avg_views` → `chat.avg_views` (TelegramChat:54)
  - `chat.last_post_frequency` → field removed entirely (no synonym)
  - `chat.price_per_post` → `chat.channel_settings.price_per_post` (moved to ChannelSettings)
  - Latent runtime bug — anyone calling `mediakit_service.get_mediakit_data()` hits AttributeError.
  - **Surface:** discovered through C10 test verification.
  - **Owner:** production migration sub-block (NOT T1.2.x test cleanup).
  - **Unblock:** `test_get_mediatkit_data` resumes when service migrated.

### C16 mock semantics — patch rename + leakage refactor (T1.2.2.7)

- **Commit:** `<this commit SHA — placeholder; canonical в Шаге 8 commits index>`
- **File:** `tests/tasks/test_placement_escrow.py` (path corrected — `tests/tasks/`, NOT `tests/unit/`)
- **Type/Count:** 3F → 0
- **Sub-fixes:**
  - **(1) Stale patch target rename (2F mechanical):** `test_publish_placement_failure_calls_refund_escrow` (line 298), `test_publish_placement_success_does_not_refund` (line 357). Production renamed `_check_dedup` → `_check_dedup_async` (S-40, `src/tasks/placement_tasks.py:102`). Updated patch target strings (lines 337, 398).
  - **(2) Mock leakage refactor (1F):** `test_check_escrow_stuck_group_a_dispatches_delete_not_refund` (line 245). Previous setup: `mock_session.execute = AsyncMock(return_value=mock_result)`. Production `_check_escrow_stuck_async` calls `session.execute()` **twice** (Group A/B query + Group C query). Shared `return_value` caused Group C path to dispatch a duplicate delete — `apply_async` called 2× instead of 1×. Refactored к `side_effect=[result_AB, result_C]` с empty Group C scalars list. Added `assert mock_session.execute.await_count == 2` lock-in — surfaces production refactors that change query count.
- **Recipe (L45 — preventive, см. Шаг 8 lessons):** when patching `session.execute()` for production functions calling `execute()` more than once, always use `side_effect=[...]`, never `return_value=`. Pattern not currently widespread в T1.2.2 file scope (other tests use single-execute production paths or already use side_effect).
- **Re-baseline post:** TBD (final table в Шаг 8).

## Re-baseline progression

| Stage | F | P | S | E | Delta |
|-------|---|---|---|---|-------|
| T1.2.1.2 (start) | 86 | 940 | 10 | 8 | — |
| Post Шаг 1 (C6) | 79 | 947 | 10 | 8 | -7F +7P |
| Post Шаг 2 (C7) | 83 | 951 | 10 | 0 | +4F +4P -8E (4F unmasked out-of-scope) |
| Post Шаг 4 (C14) | 80 | 954 | 10 | 0 | -3F +3P |
| Post Шаг 5 (C8 partial) | 80 | 954 | 10 | 0 | 0 net (5F same count, error mode 404 → ConnectionRefused) |
| Post Шаг 6 (C10 deferred) | 76 | 954 | 14 | 0 | -4F +4S |
| Post Шаг 7 (C16) | 73 | 957 | 14 | 0 | -3F +3P |
| **Total Δ** | **-13F** | **+17P** | **+4S** | **-8E** | |

## Commits index

| Шаг | Cluster | SHA | Outcome |
|-----|---------|-----|---------|
| T1.2.2.1 | C6 | `b562acc` | ✅ closed (7F) |
| T1.2.2.2 | C7 + CHANGES seed | `58eaf10` | ✅ closed (8E; 4F unmasked out-of-scope) |
| T1.2.2.3 | C15 | (skipped) | ⏸ deferred to T1.2.5/T1.2.6 (API drift) |
| T1.2.2.4 | C14 | `b73fc24` | ✅ closed (3F) |
| T1.2.2.5 | C8 partial | `3f5c638` | ⏸ partial (URL/field fix preserved; infra → T1.2.4) |
| T1.2.2.6 | C10 deferred | `6ad285f` | ⏸ skipped (mechanical preserved; SQLite + prod bug → T1.2.4 + BACKLOG) |
| T1.2.2.7 | C16 | `5ccf50a` | ✅ closed (3F) |
| T1.2.2.8 | closure docs | `<this SHA>` | — |

## Cluster outcomes summary

| Cluster | Status | Entries closed | Owner of unblock |
|---------|--------|----------------|------------------|
| C6 | ✅ closed | 7F | — |
| C7 | ✅ closed | 8E | — (4F unmasked tests are out-of-scope) |
| C15 | ⏸ deferred | 0 | T1.2.5 или T1.2.6 (API growth vs test rewrite decision) |
| C14 | ✅ closed | 3F | — |
| C8 | ⏸ partial | 0 (5F same count, mode shift) | T1.2.4 (api_client_with_auth db override decision) |
| C10 | ⏸ skipped | 0 (4F → 4S) | T1.2.4 (relocation per Q4=(a)) + BACKLOG (mediakit_service migration) |
| C16 | ✅ closed | 3F | — |

**Fully closed: 4 clusters, 21 entries.**
**Deferred: 3 clusters, ~13 entries (3F C15 + 5F C8 + 4F C10 + 1F SQLite).**

## Out of scope (per audit)

- **C20 collection-error** `tests/unit/test_main_menu.py` (`ImportError: cannot import name 'role_select_kb'`) — deferred к T1.2.5 (delete batch per Marina Q5=(a)). `--ignore=tests/unit/test_main_menu.py` Makefile flag preserved.
- **4 unmasked failures из C7** (post-Шаг 2 +4F shift) — out-of-scope clusters surfaced after fixture rename. Belong to T1.2.5 / other sub-blocks.

## Lessons learned

### L44 (originally T1.2.1) — confirmed extension trail

T1.2.1 surfaced L44 originally ("audit shape can be wrong"). T1.2.2 extended in two dimensions:

1. **Probe phase (Шаг 0 / Phase A+B):** audit **path** wrong в 4 of 8 clusters (`tests/unit/*` claimed → `tests/*` или `tests/tasks/*` actual).
2. **Execution phase (Шаги 3, 5, 6):** audit **depth** wrong — "mechanical" classification hid deeper drift in 3 of 7 clusters (C15 API drift, C8 infra gap, C10 SQLite + production bug).

### L45 — mock-leakage recipe (C16)

When patching `session.execute()` for production functions calling `execute()` more than once: always use `side_effect=[...]`, never `return_value=`. Single `return_value` shared across multiple production calls → mock leakage (same fixture data appears в different code paths, producing duplicate behavior).

**Lock-in pattern:** after `side_effect=[...]` refactor, add `assert mock_session.execute.await_count == N` to lock the contract — surfaces production refactors that change query count.

**Detected:** C16 `test_check_escrow_stuck_group_a_dispatches_delete_not_refund` — Group A/B and Group C queries shared single `mock_result`, dispatching duplicate delete.

### L46 — stop-hook noise mitigation pattern

Original plan deferred CHANGES к single Шаг 8 commit. Stop-hook fired ~150 identical "missing CHANGES_*.md" warnings on Шаг 1 commit, requiring manual user interrupt. BL-016 silent-ignore (bound at 2 acks) practically unmanageable on this fire scale.

**Mitigation applied:** switched к interleaved CHANGES (Marina decision a) — CHANGES file created on Шаг 2, appended each subsequent Шаг. Hook satisfied after Шаг 2.

**Generalization:** for future multi-commit sub-blocks — initialize CHANGES file in first or second commit (not deferred to closure). Per-cluster appends are append-only (compatible with project rule). Subsequent CHANGELOG.md hook (separate trigger): apply explicit warning text per BL-013 (c) deferral; single CHANGELOG entry в closure commit satisfies hook permanently.

### L47 — pre-fix per-cluster empirical verification mandatory

3 of 7 T1.2.2 clusters revealed deeper drift than audit-classified surface:

| Cluster | Audit said | Reality |
|---------|-----------|---------|
| C15 | method rename | + signature drift + missing method (API drift) |
| C8 | URL drift | + field rename + infra gap (api_client_with_auth missing db override) |
| C10 | field rename | + SQLite fixture gap + production bug (mediakit_service migration incomplete) |

**Mitigation:** pre-fix verification per cluster (read production source + run isolated pytest + verify fixture wiring) before declaring fix surface "mechanical". L43 STOP-gate per Шаг enabled mid-execution scope re-evaluation rather than mass commit revert.

**Generalization:** future sub-blocks treat audit cluster classifications as working hypotheses; verify shape + path + depth empirically before locking arithmetic. Marina's "архитектурно чисто" принцип benefits from per-cluster verification — it surfaces architectural decisions that would otherwise be silenced by short-path mechanical commits.

## Cumulative T1.2 progress

- T1.2.1: 9 entries closed (auth migration)
- T1.2.2: 21 entries closed (4 clusters; 3 clusters deferred с pointers)
- **Cumulative: 30 of 99 entries (~30%)**

## Open items handed forward

### To T1.2.4 (relocations + test infra)

- **C8 infra:** `api_client_with_auth` fixture extension с `app.dependency_overrides[get_db_session]` override OR alternative pattern (per-test override / new fixture). Decision needs impact analysis on other callers.
- **C10 SQLite-blocked tests (3 tests in `test_bmediakit_comparison.py`):** mechanical drift fix preserved in committed code; awaits relocation per Marina Q4=(a) или fixture extension.

### To T1.2.5 / T1.2.6 (decision needed)

- **C15 API drift (3F in `test_channel_settings_repo.py`):** decision required — should production grow API (`upsert` + `owner_id` ownership-scope) OR should tests rewrite expectations к current `get_or_create(channel_id)` semantics?
- **C20 collection-error in `test_main_menu.py`:** delete batch territory T1.2.5.

### Deferred to production fix (consolidates к BACKLOG в T1.2 final closure)

- **mediakit_service migration incomplete** — `src/core/services/mediakit_service.py:111-116` reads `chat.last_avg_views`, `chat.last_post_frequency`, `chat.price_per_post`. Model side migrated:
  - `chat.last_avg_views` → `chat.avg_views` (TelegramChat:54)
  - `chat.last_post_frequency` → field removed entirely (no synonym)
  - `chat.price_per_post` → `chat.channel_settings.price_per_post`
  - Latent runtime bug — anyone calling `mediakit_service.get_mediakit_data()` hits AttributeError.
  - **Surface:** discovered through C10 test verification.
  - **Owner:** production migration sub-block (NOT T1.2.x test cleanup).
  - **Unblock:** `test_get_mediatkit_data` resumes when service migrated.

## Process discipline observations

- **L43 STOP-gate compliance:** 7 cluster commits каждый gated by Marina "давай" — no autonomous Шаг advancement. Critical для surfacing C15 / C8 / C10 deeper drift mid-execution rather than committing wrong assumptions.
- **L44/L47 pattern:** empirical path + depth verification замест audit-claim trust — saved 3 wrong-direction commits across C15/C8/C10.
- **L45 recipe** captured before broader pattern emerged — preventive vs reactive recording.
- **L46 hook mitigation:** interleaved CHANGES адаптация preserved D2 architectural decision (one commit per cluster) while satisfying stop-hook discipline.
- **β rule preserved:** "Deferred to production fix" section accumulates discoveries для consolidation в T1.2 final closure — NO inline BACKLOG commits.
