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

<!-- Шаг 7 appends cluster section above this comment. Шаг 8 replaces this comment with final summary block. -->
