# CHANGES — BL-080 8d: Caption budget implementation

**Date:** 2026-05-13
**Branch:** `feature/bl080-8d-caption-budget`
**Base:** develop @ `4e3e4b5` (post-8c trio + Fix A + Fix B closure)

## Closes

- **BL-080 8d** — final BL-080 sub-block. Caption budget logic (Option A truncate) для media posts (photo / video). Completes the BL-080 cycle: 8a (provider unification + DI) → 8b (status enum + deterministic logic) → 8c (idempotency + correlation_id + audit + retry) → 8d (caption budget).

## Decisions applied

- **Q1 (Marina, post-research 2026-05-13)** — Caption budget strategy chosen per `BL080_8d_LEGAL_RESEARCH_2026-05-13.md` + `BL080_8d_EXTENDED_RESEARCH_2026-05-13.md`:
  - **(A) truncate** — photo / video with long ad_text → word-boundary truncate + full disclaimer preserved.
  - **(B) separate message** для video notes — **DROPPED in 8d** (см. Phase A finding ниже).
  - **(D) overlay** — deferred to post-launch (separate BL).
- **Q-8d-A (Marina, 2026-05-13)** — Option B disposition = **B1 (skip)**. Phase A read-only probe confirmed:
  - `media_type` field — `String(10)` с comment "MediaType: none/photo/video"
  - No `video_note` value supported в data model
  - Advertiser bot UI flow assigns только `"none"` / `"video"` (никогда `"photo"` literal — pre-existing legacy handler)
  - `_send_message_for_placement` dispatcher has no video_note branch
  - `grep -rn 'send_video_note\|video_note' src/` → 0 matches
  Adding defensive `NotImplementedError` branch (B2) was rejected per CLAUDE.md Principle 3 (no workarounds / dead code). Full video note support (B3) was rejected per Principle 1 (out of single sub-block scope).
- **Hook point placement** — caller responsibility via `for_media_caption: bool` flag passed to `_build_marked_text`. Caller (`publish_placement`) determines flag based on `media_type ∈ ("photo", "video")`. Rationale: `_build_marked_text` already owns disclaimer + tracking composition, so budget math stays in one place; caller decides _when_ to truncate; SRP preserved.

## Summary

Caption budget enforced для media posts. When `placement.media_type ∈ ("photo", "video")`, the
publication pipeline trims `ad_text` so the composed text (ad_text + disclaimer + optional tracking
URL) fits within `TELEGRAM_CAPTION_LIMIT = 1024`. Disclaimer + tracking URL are always preserved —
ФЗ-38 / ORD legal requirement; `ad_text` is the only sacrificable component. Word-boundary truncate
с trailing ellipsis "…".

**New module:** `src/utils/telegram_limits.py` exports `TELEGRAM_CAPTION_LIMIT` (1024),
`TELEGRAM_MESSAGE_LIMIT` (4096), and `truncate_ad_text(text, max_chars) -> str` helper. Constants
reflect Telegram Bot API limits (not configurable). Truncate helper:
- `len(text) <= max_chars` → return unchanged.
- Otherwise → cut at last whitespace within `max_chars - 1` + append "…". If no whitespace fits,
  hard cut + "…".
- Non-positive budget → return empty string (degenerate edge).

**`_build_marked_text` refactor:** new param `for_media_caption: bool = False`. Composition split
into three parts (disclaimer, tracking, base_text) for cleaner budget math. When
`for_media_caption=True`, calculates `budget = 1024 - len(disclaimer) - len(tracking)` and applies
`truncate_ad_text(base_text, budget)` before composition. Default `False` preserves text-only path
behaviour (4096 limit via Telegram natively). All existing 8b deterministic logic preserved
(stub+no-erid, non-stub+no-erid raise, erid+disclaimer paths) — refactor changes only the
intermediate variable structure, not the final composed output for `for_media_caption=False`.

**`publish_placement` callsite:** computes `for_media_caption = placement.media_type in ("photo",
"video")` and passes to `_build_marked_text`. Text-only placements (`media_type="none"`) get
`for_media_caption=False` — unchanged behaviour.

**Video note path not implemented** — see Q-8d-A above. Out of scope per data model audit. Tracked
as separate BL (см. ниже).

## Changed files

- `src/utils/telegram_limits.py` — **new file**, 51 lines. Constants + `truncate_ad_text` helper.
- `src/core/services/publication_service.py` — `_build_marked_text` accepts `for_media_caption`
  flag (signature change, default `False` preserves existing callsites); `publish_placement`
  passes `for_media_caption` based on `media_type`.
- `tests/unit/test_caption_truncate.py` — **new file**, 17 unit tests (8 direct `truncate_ad_text`
  + 9 `_build_marked_text` end-to-end including edge cases).

## Test coverage

| Test class | Count | Coverage |
|---|---|---|
| `TestTruncateAdText` | 8 | `truncate_ad_text` direct: short / exact-limit / over-limit / word-boundary / hard-cut / empty / non-positive / newline boundary |
| `TestBuildMarkedTextCaptionBudget` | 9 | `_build_marked_text` end-to-end: short + media flag / long text truncate / tracking URL fits / advertiser_name size reduces budget / text-only no-truncate / exactly-at-limit / tracking pushes-over triggers truncate / fallback advertiser_name / stub+no-erid+media |

All 17 new tests pass. `make ci-local` pytest: **1046 passed / 2 skipped / 7 warnings** (baseline
1033 + 13 from initial Шаг 2 + 4 from edge cases Шаг 4). Format-check / typecheck clean. Lint stable
at 7-error baseline (BL-024).

Existing `tests/test_publication_service.py` (8 tests on `_build_marked_text` deterministic logic
from 8b) all continue to pass — refactor is signature-compatible (default `for_media_caption=False`
preserves prior behaviour bit-for-bit).

## Verification

`make ci-local` pytest portion clean (1046 passed). `make ci-local` target-level exit non-zero —
**expected** per BL-057 (lint baseline halts the target before all gates complete). No regression
vs baseline `1033 passed / 2 skipped` numbers.

L71 runtime debug gate должен пройти перед declaring BL-080 closed — applies to Phase C step
(merge into develop + container rebuild + smoke check). Caption budget is logic-only change, not
infrastructure, so L71 risk is low.

## Deferred to production launch

- **(D) Overlay variant** — image-pipeline approach (rendering disclaimer onto image, no caption
  budget pressure). Out of 8d scope; separate post-launch BL when Pillow / image processing
  dependency is justified.
- **BL-105 candidate (ККТУ codes UI integration)** — separate scope, accumulate.
- **BL-104 candidate (Telegram → MAX migration strategy)** — separate strategic decision,
  accumulate.

## New BL candidates from 8d findings

- **BL-108 candidate — Video note (kruzhok) placement type addition.** Phase A confirmed no
  `video_note` value в `media_type` field, no bot UI flow, no `_send_message_for_placement`
  dispatcher branch. Option B (separate-message marker after `sendVideoNote`) becomes
  implementable when this BL adds:
  1. Migration: extend `media_type` field comment / VARCHAR length if needed; add `video_note`
     value.
  2. Advertiser bot UI: add kruzhok upload step в `bot/handlers/advertiser/campaigns.py`.
  3. Placement model: optional separate `video_note_file_id` field или re-use `video_file_id`.
  4. Dispatcher: `_send_message_for_placement` branch invoking `bot.send_video_note(...)` →
     `bot.send_message(..., reply_parameters=...)`.
  5. ORD: `media_type="video_note"` mapping в `yandex_ord_provider.py:200-202`.
- **BL-109 candidate — Text-only post overflow handling.** `ad_text` API max=5000 chars
  (`campaigns.py:62`) but Telegram text-only send_message limit=4096. Placements с
  `media_type="none"` AND `ad_text > 4096` currently fail с `TelegramBadRequest` → transition к
  `failed`. Pre-existing behaviour, not 8d scope (Q1 explicitly про media caption budget 1024).
  Could be addressed: validate at API boundary (max=4096 - typical disclaimer overhead), или
  enable truncate on text-only path with `TELEGRAM_MESSAGE_LIMIT`.

## L71 protocol applicability

L71 runtime debug gate **applies** for BL-080 closure (after 8d merge into develop):
- Container rebuild + healthcheck pass
- API startup OK
- Celery worker startup OK
- Migration apply OK на empty DB
- Smoke test: placement creation → publication → ERID flow integrity

8d itself is logic-only (no schema / startup / dependency changes), so L71 risk is low. The
applicability follows from BL-080 closure scope — combined trio (8a/8b/8c) + 8d + Fix A + Fix B
forms the full closure delta against `f866b2f` (v0.6.0).

🔍 Verified against: `7692528` (Шаг 4 commit) | 📅 Updated: 2026-05-13
