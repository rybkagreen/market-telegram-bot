# CHANGES — Legal templates Jinja2 fee injection + version 1.1 (Промт 15.8 / 2 of 5)

## What

Second of 5-prompt fee model consistency rewrite (BL-038).

Legal templates (12 files: 6 contracts + 6 acts) now read fee
percentages, version, and edition date through Jinja2 injection from
`src/constants/fees.py` + `src/constants/legal.py` via
`ContractService._build_fee_context()`. CONTRACT_TEMPLATE_VERSION
bumped to **1.1**. Edition header added. § 18 (115-ФЗ) и § 19
(юрисдикция) added to platform_rules.html as legally-reviewable
placeholders.

## Code changes

### `src/constants/legal.py`

- `CONTRACT_TEMPLATE_VERSION` "1.0" → "1.1".
- New constant `CONTRACT_EDITION_DATE = "28 апреля 2026 г."`.

### `src/core/services/contract_service.py`

- New imports from `src.constants.fees`: rate constants + derived
  `OWNER_NET_RATE` / `PLATFORM_TOTAL_RATE`.
- New module-level helper `_format_pct(rate, decimals)` — returns
  bare number string (no `%`), Russian comma decimal.
- New module-level helper `_build_fee_context()` — returns dict of
  Jinja vars: percentages, cancel splits, version, edition date.
- `_render_template()` injects `**_build_fee_context()` into ctx for
  all contract types (advertiser / owner_service / platform_rules /
  privacy_policy).
- `render_platform_rules()` injects same.

### `src/core/services/act_service.py`

- Imports `_build_fee_context` from `contract_service` (separate
  Jinja env from ContractService — see drift note below).
- `_render_act_template()` merges `**_build_fee_context()` into ctx
  so act templates can render the edition header.

### `src/templates/contracts/platform_rules.html`

- Edition header replaced "Редакция от {{ contract_date }} · Версия 1.0"
  → "Редакция от {{ contract_edition_date }}, версия {{ contract_template_version }}".
- § 5 (Комиссия) полностью переписан:
  - 5.1 — `{{ platform_commission_pct }}%` / `{{ owner_share_pct }}%`.
  - 5.2 — `{{ service_fee_pct }}%` сервисный сбор + `{{ owner_net_pct }}%` /
    `{{ platform_total_pct }}%` эффективные ставки.
  - 5.3 — `{{ yookassa_fee_pct }}%` без надбавок.
  - 5.5 — cancel splits через `{{ cancel_advertiser_pct }}%` /
    `{{ cancel_owner_pct }}%` / `{{ cancel_platform_pct }}%`.
- § 18 (115-ФЗ боиlerplate) — placeholder, помечен `[ПЛЕЙСХОЛДЕР —
  требует review юристом]`.
- § 19 (юрисдикция, применимое право, делимость) — placeholder.

### `src/templates/contracts/advertiser_campaign.html`

- Edition header добавлен после `<h1>`.
- § 5.1 (Отмена кампании) — pre-publish split через cancel-Jinja vars.
- § 5.3 (досрочное удаление РИМ — post-publication 80%/40%) —
  оставлено как есть с `<!-- noqa-fees -->` маркерами; reconciled в
  Промт 15.11.5.
- § 6.1 хардкод 80%/20% → `{{ owner_share_pct }}%` /
  `{{ platform_commission_pct }}%` + упоминание `{{ service_fee_pct }}%`.

### 4× `src/templates/contracts/owner_service_*.html`

- Edition header добавлен после `<h1>`.
- § 7.1 хардкод 80%/20% → Jinja vars + полная цепочка с сервисным
  сбором (1,5%) и эффективной выплатой (78,8%).
- `owner_service_individual.html` § 7.4 — обновлён "не входят в
  {{ owner_share_pct }}% стоимости задания".

### 6× `src/templates/acts/*.html`

- Edition header добавлен после `<h1>`.
- Только `act_placement.html` активно используется в
  ActService.generate_for_completed_placement; остальные 5
  unused/dead до Промта 15.11. Headers добавлены unconditionally —
  inert text.

### `tests/unit/test_no_hardcoded_fees.py`

- Новая функция `test_no_hardcoded_percentages_in_legal_templates`.
- Сканирует `src/templates/**/*.html` на canonical-fee percentages
  (`20%`, `80%`, `1,5%`, `78,8%`, `21,2%`, `3,5%`) outside Jinja
  expressions.
- TEMPLATE_EXEMPT_FILES — 9 файлов с tax-law/НДФЛ/НДС/НПД rates.
- Per-line opt-out via `noqa-fees` marker (для post-publication
  refund window scenarios pending 15.11.5).

### `tests/integration/test_contract_service_fee_injection.py` (new)

- 4 integration tests:
  - `test_platform_rules_contains_current_commission_percentages` —
    asserts 20%, 80%, 1,5%, 78,8%.
  - `test_platform_rules_contains_edition_header` — asserts
    "Редакция от 28 апреля 2026 г." и "версия 1.1".
  - `test_platform_rules_contains_115fz_section`.
  - `test_platform_rules_contains_jurisdiction_section`.

## Public contract delta

`GET /api/contracts/platform-rules/text`:

- Response shape unchanged (`{html: ...}`).
- HTML content updated:
  - Edition header.
  - § 5 references 20%, 80%, 1,5%, 78,8%, 21,2%, 3,5%, cancel splits
    50/40/10.
  - § 18 (115-ФЗ) и § 19 (юрисдикция) — placeholders for legal
    review.

## Drift / observations vs prompt v2

Surfaced in Step 0 inventory:

1. **`render_platform_rules(self) -> str`** — takes NO `user_id`
   arg (prompt's Шаг 8 integration tests had `user_id=test_user.id`
   stub which would've failed). Tests adapted to no-arg call.
2. **No `render_advertiser_contract` / `render_owner_contract`** —
   only `_render_template` (private) handles all contract types.
   Single injection point for fee context.
3. **`act_service.py` uses SEPARATE Jinja2 environment** from
   ContractService. Шаг 6.v2 conditional path activated; without
   the import + ctx merge, act_placement.html would've raised
   `UndefinedError: 'contract_edition_date' is undefined` at first
   render.
4. **Only `act_placement.html` is wired** in ActService; the other
   5 act templates are dead until Промт 15.11. Edition headers
   added to all 6 (inert text in unused templates).
5. **`fees.py` already has** `OWNER_NET_RATE`, `PLATFORM_TOTAL_RATE`
   — `_build_fee_context()` reuses those instead of recomputing.

## Critical operational notes

- `CONTRACT_TEMPLATE_VERSION = "1.1"` — но re-acceptance flow НЕ
  active (Промт 15.9 territory). Existing acceptance rows на v1.0
  не invalidate. Dev DB пустая → impact zero сейчас.
- Frontend всё ещё хардкодит `0.035` в
  `mini_app/src/screens/advertiser/TopUpConfirm.tsx:66` — fix в
  Промте 15.10.
- 115-ФЗ + юрисдикция тексты — **placeholders**, не финальный
  legal text. Требуют review юристом перед real prod launch.
- `advertiser_campaign.html` § 5.3 (post-publication refund window
  80%/40%) — legacy scenario вне centralized cancel split, помечен
  `noqa-fees`; reconciled в Промт 15.11.5.

## Gate baseline

Pre → post:

- Forbidden-patterns: 17/17 → 17/17 ✓
- Ruff `src/`: 21 → 21 ✓ (no new errors in changed files)
- Ruff `tests/`: 107 → 107 ✓ (new test files ruff-clean)
- Mypy `src/`: 10 errors / 5 files → 10 errors / 5 files ✓
- Pytest substantive (excluding e2e_api + main_menu):
  - Pre: 76 failed, 17 errors, 651 passed (per CLAUDE.md baseline)
  - Post: 76 failed, 17 errors, 655 passed (4 new integration tests
    added)

## BACKLOG / CHANGELOG

- BL-038 added — `RESOLVED` (this session).
- CHANGELOG entry under `[Unreleased]`.

## Origins

- `PLAN_centralized_fee_model_consistency.md` (Промт 15.8 v2,
  2026-04-28).
- Промт 15.6 inventory gaps:
  - Hardcoded percentages (20/80) в legal templates.
  - No edition header.
  - Missing 115-ФЗ + jurisdiction sections.
- Промт 15.7 introduced `src/constants/fees.py` + `/api/billing/fee-config`
  — backend нашел 78,8/21,2 модель, но templates остались на 85/15.

## Next prompt — 15.9

Acceptance infrastructure: `needs_accept_rules` actually compares
`CONTRACT_TEMPLATE_VERSION` with stored row version → forces
re-accept on version mismatch. mini_app + web_portal + bot redirect
to /accept-rules screen when needed. Sync `User.platform_rules_accepted_at`
(cache) с `Contract` row (authoritative). Sub-stage tracking per
BL-037.

🔍 Verified against: pending commit | 📅 Updated: 2026-04-29
