# CHANGES — 2026-04-29 — PII pinning /api/payouts/* + /api/admin/* (16.1)

## Summary

Серия 16.x kickoff — Group A. Все endpoints в `/api/payouts/*` и
`/api/admin/*` pinned к web_portal-only audience. Mini_app JWT теперь
возвращает 403 на этих роутах (ФЗ-152). Повтор Phase 1 mechanical
pattern; контракты Pydantic не затронуты.

Closes:
- BL-046 (CRIT-2: `/api/payouts/*` принимал mini_app JWT, `requisites`
  пролетал в mini_app heap).
- BL-049 (MED-5: `/api/admin/*` через `AdminUser → get_current_user` без
  `aud` pin; admin endpoint'ы покрывают PII — legal-profiles, users,
  platform-settings, payouts).

§ O.5 (PII_AUDIT — `/api/admin/platform-settings` plaintext bank fields в
response) полностью закрыт audience pin'ом — audit явно говорит "Same
web_portal-binding fix as O.4". Отдельный BL не заводился.

## What changed

### /api/payouts/* (CRIT-2 / BL-046 closed)

`src/api/routers/payouts.py` — 3 endpoint'а + 1 helper:

| Endpoint | Line | Before | After |
|----------|------|--------|-------|
| `GET /api/payouts/` | 63 | `current_user: CurrentUser` | `current_user: Annotated[User, Depends(get_current_user_from_web_portal)]` |
| `GET /api/payouts/{payout_id}` | 90 | `current_user: CurrentUser` | `current_user: Annotated[User, Depends(get_current_user_from_web_portal)]` |
| `POST /api/payouts/` | 123 | `current_user: CurrentUser` | `current_user: Annotated[User, Depends(get_current_user_from_web_portal)]` |
| helper `_get_payout_or_404` | 33 | `current_user: CurrentUser` | `current_user: User` (signature не auth-dep, тип сужен) |

Imports: `CurrentUser` → `get_current_user_from_web_portal`, добавлен
`from src.db.models.user import User`.

### /api/admin/* (MED-5 / BL-049 closed) — Strategy A

`src/api/dependencies.py:191` — `get_current_admin_user` теперь wraps
`get_current_user_from_web_portal` вместо `get_current_user`. Это
автоматически pin'ит:

- `src/api/routers/admin.py` — 20 endpoint'ов через `AdminUser` alias
  (`/stats`, `/users`, `/users/{id}`, `/users/{id}/legal-profile`,
  `/legal-profiles`, `/legal-profiles/{id}/verify|unverify`,
  `/audit-logs`, `/platform-settings` GET/PUT, `/tax/summary`,
  `/contracts`, `/payouts`, `/payouts/{id}/approve|reject`, и др.)
- `src/api/routers/feedback.py` — 4 admin endpoint'а через
  `Depends(get_current_admin_user)`.
- `src/api/routers/disputes.py` — 2 admin endpoint'а
  (`/admin/disputes/*`).

Mini_app JWT отбивается на audience-несовпадении ДО проверки `is_admin`
(возвращается 403 с message "Invalid token audience"). Web_portal JWT
для не-admin'а по-прежнему отбивается на is_admin gate (403,
"admin access required") — admin-gate сохранён.

`CurrentUser` alias и `get_current_user` остаются нетронутыми — они
используются для общих эндпоинтов где mini_app валидное authentication
(billing balance, places, channels и т.п.).

### Tests

`tests/unit/api/test_admin_payouts.py` — fixture update:
- `admin_client` дополнительно override'ит
  `get_current_user_from_web_portal` (для случаев, где override
  `get_current_admin_user` не сработает — например, прямой dep'енденс
  не через AdminUser alias).
- `advertiser_client` теперь override'ит
  `get_current_user_from_web_portal` (раньше только `get_current_user`).
  Без обновления `test_advertiser_gets_403` падал бы 401 (missing
  Authorization), потому что `get_current_admin_user` ныне ходит
  через web_portal dep.

`tests/unit/api/test_pii_audience_pinning.py` (новый, 10 тестов):
- `TestPayoutsRejectMiniAppJwt` (3) — GET /, GET /{id}, POST / →
  mini_app JWT → 403.
- `TestAdminRejectMiniAppJwt` (4) — `/admin/users`, `/admin/payouts`,
  `/admin/platform-settings`, `/admin/legal-profiles` → mini_app JWT
  (даже с is_admin=True) → 403 на audience-gate.
- `TestWebPortalJwtPassesAudienceGate` (3) — sanity:
  - web_portal JWT не отбивается audience-gate'ом для payouts/admin.
  - web_portal JWT + non-admin → 403 от is_admin gate (а не audience).

### Not changed

- Pydantic response schemas — auth dep transparent.
- Бизнес-логика в payout/admin сервисах.
- DB schema, migrations.
- `accept-rules` carve-out (Phase 1 §1.B.2 — non-PII, оба audience'а,
  intentional).
- Bot payout flow (FSM-handlers) — будет removed в 16.3.
- `EncryptedString` migrations для `PayoutRequest.requisites` /
  `DocumentUpload.ocr_text` / `PlatformAccount.bank_*` — 16.2 scope.
- `UserResponse` referral leak — 16.4 scope.
- `tests/integration/conftest.py` (DB-only test infrastructure, не
  связан с auth dep'ами).

## CI baseline

Local `make ci-local` proxy via `poetry run mypy src/` + `poetry run
ruff check src/` + `poetry run pytest tests/unit/api/`:

| Check | Before | After |
|-------|--------|-------|
| mypy src/ (errors) | 10 | 10 |
| mypy src/ (files) | 5 | 5 |
| ruff src/ (errors) | 21 | 21 |
| pytest tests/unit/api/ | 49 passed | 59 passed (+10 regression) |
| pytest tests/unit/api/test_admin_payouts.py | 9 passed | 9 passed |

Pre-existing failures **не связанные** с этим PR (присутствуют на
develop @ 8eab3ba):
- `tests/unit/test_main_menu.py` — collection error
  (`role_select_kb` import).
- `tests/unit/test_start_and_role.py` — 11 failures
  (`async_session_factory` mock на несуществующий attribute).
- ~50 prochих unit-failures в bot-side suites, верифицированы как
  pre-existing через git stash + bare develop run.

## Smoke / verification

API-level integration через FastAPI `dependency_overrides` + ASGI
`AsyncClient` — покрыто 10 regression-тестами в
`test_pii_audience_pinning.py`. Реальный production smoke (curl с JWT)
выполняется на Шаге 9.4 deploy (см. STOP report).

## Origins

- `reports/docs-architect/discovery/PII_AUDIT_2026-04-28.md` §§ O.2
  (CRIT-2 payouts), O.4 (MED-5 admin), O.5 (platform-settings — same
  fix path).
- BL-046, BL-049 в `reports/docs-architect/BACKLOG.md`.
- Phase 1 §1.B.1 mechanical pattern (`legal_profile.py`, `contracts.py`,
  `acts.py`, `document_validation.py`).

🔍 Verified against: feature/16-1-pin-payouts-admin-web-portal HEAD
📅 Updated: 2026-04-29
