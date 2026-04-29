# CHANGES — 2026-04-29 — Legal text "кредиты" → "рубли" + version bump 1.2

## Summary

Customer-visible legal text в `platform_rules.html` переписан с "кредиты"
на "рубли" — terminology aligned с реальной post-migration single-currency
моделью. `CONTRACT_TEMPLATE_VERSION` 1.1 → 1.2 → re-acceptance loop fires
для existing users (DB пустая → latent в production).

Origin: credits naming inventory 2026-04-29 (BL-053). Этот fix — отдельный
от серии 17.x потому что customer-facing legal lie имеет приоритет.

## Decision (from Шаг 1 audit)

**Mixed (c).**

Reasoning:
- `platform_rules.html` rendered via `ContractService.render_platform_rules()`
  и виден customer'у на `GET /api/contracts/platform-rules/text` — must fix.
- `legal.py:3` docstring "двухвалютной системы" stale, self-contradicts
  module reality — fix (cheap, prevents future maintainer confusion).
- `legal.py` text constants `TERMS_OF_SERVICE`, `TERMS_SHORT`, `PRIVACY_NOTICE`,
  `WELCOME_MESSAGE` — **0 callers найдено в src/ или tests/**. Orphan dead
  code; "кредит" mentions inside (lines 23-26, 91, 143-144) не render'ятся
  и не impacrt customers. Defer to series 17.x cleanup per BL-053.
- `CONTRACT_TEMPLATE_VERSION` bump 1.1 → 1.2 fires re-acceptance via
  existing 15.9 infrastructure (`ContractService.needs_accept_rules`).

## What changed

### Legal text rewrites
- `src/templates/contracts/platform_rules.html:90` — section 5.3:
  - Before: "Валюта расчётов — кредиты (1 кредит = 1 ₽). Пополнение — через YooKassa..."
  - After: "Валюта расчётов — рубли (₽). Пополнение баланса осуществляется через YooKassa..."
- `src/constants/legal.py:1-7` — module docstring переписан, документирует
  single-currency model + явная пометка про orphan constants для 17.x.

### Version bump
- `src/constants/legal.py:121` — `CONTRACT_TEMPLATE_VERSION = "1.2"` (было `"1.1"`).
- 15.9 re-acceptance loop fires при `accepted_version != "1.2"` для existing
  users в DB. Реально DB пустая → no-op в production.

### Tests
- `tests/integration/test_contract_service_fee_injection.py` — assertion
  `"версия 1.1" in html` parameterized on `CONTRACT_TEMPLATE_VERSION` constant
  (стало version-agnostic, не сломается на следующем bump).
- `tests/unit/test_contract_template_version.py` — new (2 tests):
  - `test_contract_template_version_is_1_2`.
  - `test_platform_rules_template_uses_rubles_not_credits` (template
    content guard against "кредит" regression).

### Not changed
- Public API contract: routes, response shapes, status codes — все
  без изменений. Меняется только rendered template content.
- `BillingService`, `YookassaService` — out of scope.
- Bot UI strings (`notification_tasks.py:1229`, `billing_tasks.py:138`,
  `gamification_tasks.py:205`, `badge_tasks.py:245`) — 17.4 scope per BL-053.
- DB schema, models, enums — 17.2 scope.
- API path renames — 17.3 scope.
- Orphan `legal.py` text constants (TERMS_OF_SERVICE, TERMS_SHORT,
  PRIVACY_NOTICE, WELCOME_MESSAGE) — 17.x scope (with deletion option
  since 0 callers).

## Audit surprise

`legal.py` text constants `TERMS_OF_SERVICE`, `TERMS_SHORT`, `PRIVACY_NOTICE`,
`WELCOME_MESSAGE` — **all 0 callers** в src/ or tests/. Likely dead since
mini_app/web_portal заменили в-bot legal flow на template-based contract
rendering (`platform_rules.html`). Surface'нуто в BL-053 для series 17.x —
candidate for outright deletion rather than rewrite.

## Re-acceptance smoke

Existing 15.9 infrastructure verified:
- `ContractService.needs_accept_rules` (`contract_service.py:309`):
  `return latest.template_version != CONTRACT_TEMPLATE_VERSION`.
- 6 acceptance flow tests pass (`test_acceptance_flow.py` x5,
  `test_needs_accept_rules_endpoint.py` x1).
- DB пустая в production → loop fires latently, no real users impacted.

## CI baseline

| Check | Before | After | Note |
|-------|--------|-------|------|
| pytest -k legal/platform_rules/acceptance/template_version | 110 pass / 2 fail / 3 errors | 112 pass + same pre-existing 502 noise | 1 fix (version 1.1→1.2 assertion) + 2 new + 0 regressions |
| ruff src/ | 21 | 21 (unchanged) |  |
| mypy src/ | 10 | 10 (unchanged) |  |

Pre-existing collection error в `tests/unit/test_main_menu.py` (unrelated
import error) и Privoxy 502 на `legal-profile/me` e2e тестах — оба out of
scope.

## Plan + BACKLOG updates

- `reports/docs-architect/BACKLOG.md`: BL-053 partial closure note added
  (legal text rewrites done; bot UI strings + DB schema + API paths
  remain deferred к 17.x).

## Files changed

- `src/templates/contracts/platform_rules.html` (1 line, section 5.3 rewrite)
- `src/constants/legal.py` (docstring + version bump)
- `tests/integration/test_contract_service_fee_injection.py` (1 fixture
  + module docstring)
- `tests/unit/test_contract_template_version.py` (new — 2 tests)
- `reports/docs-architect/BACKLOG.md` (BL-053 partial closure note)
- `reports/docs-architect/discovery/CHANGES_2026-04-29_legal-rub-rewrite-v1-2.md` (this file)
- `CHANGELOG.md` (Unreleased entry)

## Origins

- Credits naming inventory 2026-04-29 (BL-053, серия 17.x scope, 17.4
  partial closure).

🔍 Verified against: develop @ c992eda | 📅 Updated: 2026-04-29
