# CHANGES 2026-04-21 — Testing suite: legal profiles, contracts, placement, Yandex ORD

## Scope

Pre-launch verification of four interconnected flows before switching
`ORD_PROVIDER=stub → yandex`:

1. Legal profiles across all 4 statuses (ЮЛ / ИП / самозанятый / физлицо).
2. Contract generation from legal-profile snapshots (4 owner-service
   templates) with PII-safe `legal_status_snapshot`.
3. Placement ↔ Contract ↔ ORD wiring.
4. Yandex ORD API v7 provider: captured the public-docs contract as
   `httpx.MockTransport` fixtures and covered the provider + full chain.

## Files affected

### Created
- `tests/unit/test_fns_validation_service.py` — INN/OGRN/KPP checksum
  coverage + matrix for `validate_entity_type_match` + xfail for the
  self_employed + OGRNIP gap + static `LegalProfileService.validate_inn`.
- `tests/unit/test_contract_template_map.py` — asserts every
  `(contract_type, legal_status)` → template file mapping and that each
  referenced HTML exists on disk. `ContractService.needs_kep_warning`
  classifier.
- `tests/unit/test_yandex_ord_provider.py` — `httpx.MockTransport`
  driving every method on `YandexOrdProvider` + error matrix
  (401/422/429/500/connect-timeout).
- `tests/unit/test_yandex_ord_org_type_map.py` — pure helpers
  (`ORG_TYPE_MAP`, `_map_org_type`, `_determine_vat_rate`).
- `tests/integration/test_legal_profile_service.py` — CRUD / completeness
  / tax-regime auto-set / inn_hash / encrypted round-trip / scan upload /
  required-fields per status + xfail for unknown legal_status.
- `tests/integration/test_api_legal_profile.py` — ASGI transport against
  the FastAPI app with dependency overrides; all endpoints of
  `/api/legal-profile/*` including bank-account masking and
  validate-entity INN-type matching.
- `tests/integration/test_contract_service.py` — owner_service contract
  for 4 statuses, `_SNAPSHOT_WHITELIST` PII guard, dedup, sign / audit /
  permission error, platform_rules acceptance.
- `tests/integration/test_ord_service_with_yandex_mock.py` —
  `OrdService.register_creative` end-to-end through `YandexOrdProvider` +
  `httpx.MockTransport` (4 endpoints hit in order, erid landed on
  placement, idempotency).
- `tests/integration/test_placement_ord_contract_integration.py` —
  narrow smoke test: advertiser campaign contract bound to placement,
  StubOrdProvider registration lands erid, report_publication transitions
  to "reported".
- `tests/integration/conftest.py` — session-scoped testcontainer Postgres
  + per-test transaction rollback fixture. Works around a model-level
  duplicate-index declaration (Act.placement_request_id via both
  `index=True` and explicit `Index(...)`).
- `tests/fixtures/yandex_ord/*.json` — 13 request/response fixtures
  covering successful flows (organization / platforms / contract /
  creative / status / statistics) and 4 error shapes (missing token / 401
  / 422 / 429 / 500).
- `docs/ord/YANDEX_ORD_API_NOTES.md` — consolidated notes on the
  Yandex ORD API v7 request/response shapes (captured from the provider
  implementation since the docs portal is auth-gated), `orgType` mapping,
  and the sandbox-access procedure required before a real-credentials
  switch.

### Modified
- `tests/conftest.py` — added:
  - Helpers `make_valid_inn10 / make_valid_inn12 / make_valid_ogrn /
    make_valid_ogrnip` that compute valid checksums so tests never hard-
    code brittle literals.
  - `VALID_INN10 / VALID_INN12 / VALID_OGRN / VALID_OGRNIP / VALID_KPP /
    VALID_BIK` shared test values.
  - `legal_profile_data(status)` factory with a known-valid payload for
    each of the 4 legal statuses (valid checksums, correct `tax_regime`
    enum values per `src/api/schemas/legal_profile.py:TaxRegime`).
  - `user_with_legal_profile(status)` async builder.

## Business logic impact

No production code changed. The test suite exercises existing services:

- `LegalProfileService` — `legal_profile_service.py`.
- `fns_validation_service` — `fns_validation_service.py`.
- `ContractService` — `contract_service.py`.
- `OrdService` — `ord_service.py`.
- `YandexOrdProvider` — `yandex_ord_provider.py`.

## New/changed contracts

No public API changes.

## Known gaps surfaced by the suite (documented as xfail)

1. **Unknown `legal_status` silently completes** —
   `LegalProfileService.create_profile("foobar", ...)` falls through to
   `_EMPTY_FIELDS` so `check_completeness()` returns `True`
   (`legal_profile_service.py:131-152`). Test:
   `test_legal_profile_service.py::test_unknown_legal_status_should_not_report_complete`
   (`xfail`).
2. **`validate_entity_type_match` is coarse on 12-digit INN** — any
   12-digit INN validates for `individual / self_employed /
   individual_entrepreneur` interchangeably, even when OGRNIP is present
   (`fns_validation_service.py:257`). Test:
   `test_fns_validation_service.py::TestValidateEntityTypeMatch::test_self_employed_with_ogrnip_should_be_rejected`
   (`xfail`).

Both are documented as pre-launch gaps to tighten before real-money
placements go through.

## Test results

- Full new suite: **198 passed, 4 skipped (pre-existing), 2 xfailed**.
- `ruff check` on new files: clean.
- Test fixtures and helpers only; no migrations, no production code
  changes, no public-API deltas.

## Run commands

```bash
# Unit-only (fast, no Docker needed for the FNS / template-map tests)
poetry run pytest \
  tests/unit/test_fns_validation_service.py \
  tests/unit/test_contract_template_map.py \
  tests/unit/test_yandex_ord_provider.py \
  tests/unit/test_yandex_ord_org_type_map.py \
  --no-cov

# Integration (requires Docker for testcontainers Postgres)
poetry run pytest tests/integration/ --no-cov
```

## Follow-ups

1. Wire the two xfailed tests into the pre-launch blockers list (see
   `CLAUDE.md § Pre-Launch Blockers`).
2. Once Yandex ORD sandbox credentials are provisioned (per
   `docs/ord/YANDEX_ORD_API_NOTES.md § 1`), extend
   `tests/integration/test_ord_service_with_yandex_mock.py` with an
   opt-in real-transport path gated on `ORD_API_KEY` presence.
3. Pre-existing model-level quirk: `Act.placement_request_id` is declared
   with both `Column(..., index=True)` and an explicit `Index(...)` in
   `__table_args__`, which causes `MetaData.create_all()` to duplicate
   the index. The integration conftest dedupes by name as a workaround;
   cleaner fix is to drop one of the two declarations in `src/db/models/act.py`.

---

🔍 Verified against: 1237d01873e6a038a0bf97e957f105eb3e71c6bd | 📅 Updated: 2026-04-21T00:00:00Z
