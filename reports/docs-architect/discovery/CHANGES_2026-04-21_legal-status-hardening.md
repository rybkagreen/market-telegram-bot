# CHANGES 2026-04-21 — Legal status validation hardening

## Scope

Closes the two pre-launch validation gaps that the 2026-04-21 test
suite documented as `xfail`:

1. `LegalProfileService.create_profile` silently accepted any string as
   `legal_status` and the profile was marked `legal_status_completed=True`
   because `get_required_fields` fell through to an empty list
   (`legal_profile_service.py:131-152`).
2. `fns_validation_service.validate_entity_type_match` was too coarse on
   12-digit INN — any combination of `individual / self_employed /
   individual_entrepreneur` passed, regardless of whether the supplied
   documents (OGRNIP, passport, etc.) actually matched the status
   (`fns_validation_service.py:257`).

Both `xfailed` tests flip to `passed` under `strict=True` and are joined
by a parametrised matrix (15 cases) and negative API tests.

## Files affected

### Modified
- `src/core/services/legal_profile_service.py` — added
  `_KNOWN_LEGAL_STATUSES` frozenset, `_require_known_status()` guard,
  `_validate_documents_for_status()` helper. `create_profile` now
  raises `ValueError` for missing / unknown statuses and for documents
  that contradict the declared status. `update_profile` enforces the
  same invariants when `legal_status` is part of the payload.
  `get_required_fields` now raises on unknown statuses (was silently
  returning `_EMPTY_FIELDS`, which was removed).
- `src/core/services/fns_validation_service.py` — added
  `validate_entity_documents(legal_status, *, ogrn, ogrnip,
  passport_series, passport_number)`. Complements the existing
  `validate_entity_type_match` (INN-length check) by enforcing
  status-specific document rules: `legal_entity` requires OGRN,
  `individual_entrepreneur` requires OGRNIP, `self_employed` forbids
  both, `individual` requires passport.
- `src/api/routers/legal_profile.py` — `validate_entity` now calls
  `validate_entity_documents` after the INN-type match succeeds and
  maps errors to the offending field (`ogrn` / `ogrnip` / `documents`).
  `get_required_fields` endpoint wraps `ValueError` in HTTP 422 so an
  unknown status returns a structured error.

### Tests — xfail removed + new matrix
- `tests/unit/test_fns_validation_service.py` — dropped the xfail
  marker; added `TestValidateEntityDocuments` with a 15-row matrix
  covering every `(status, ogrn, ogrnip, passport)` combination plus
  edge cases (empty strings, unknown status passthrough).
- `tests/integration/test_legal_profile_service.py` — dropped the xfail
  marker; added:
  - `test_unknown_legal_status_is_rejected`
  - `test_missing_legal_status_is_rejected`
  - `test_get_required_fields_rejects_unknown`
  - `test_update_profile_rejects_change_to_unknown_status`
  - `test_create_profile_rejects_mismatched_documents`
    (self_employed + OGRNIP → ValueError).
- `tests/integration/test_api_legal_profile.py`:
  - `test_validate_entity_self_employed_with_12_digit_passes` renamed
    to `..._without_ogrnip_passes` and split into a happy + negative
    variant.
  - `test_validate_entity_legal_entity_matches_10_digit_inn` updated to
    supply OGRN (now required for the happy path).
  - New `test_validate_entity_legal_entity_missing_ogrn_is_rejected`.
  - New `test_validate_entity_self_employed_with_ogrnip_is_rejected`.

## Business-logic impact

- **Write-path tightening.** Profiles with unknown `legal_status` or
  document/status mismatches can no longer be persisted through
  `LegalProfileService`. Existing rows are not re-validated on read —
  no migration needed and no behaviour change for well-formed data.
- **Bot/Celery callers protected.** Pydantic's enum validation was
  already enforcing `LegalStatus` at the API layer
  (`src/api/schemas/legal_profile.py:LegalStatus`), so service-layer
  guards are defence-in-depth for handlers that construct profile
  dicts directly (bot FSM flows, admin tooling).
- **API error shape tightened.** `POST /api/legal-profile/validate-entity`
  now returns `is_valid=false` with field-scoped errors for the new
  document-mismatch cases (e.g. `field="ogrnip"`). Error code remains
  200 (the endpoint reports validation results in the body, not via
  HTTP status).
  `GET /api/legal-profile/required-fields?legal_status=<bad>` now
  returns **422** instead of an empty `{fields: [], ...}` body.

## New/changed contracts

No schema changes (DB / Pydantic). One error-shape change:

- `GET /api/legal-profile/required-fields` — unknown status: **200 with
  `_EMPTY_FIELDS`** → **422 with `{detail: "Unknown legal_status: …"}`**.

## Test results

- Affected suite: **129 passed** (unit FNS + integration legal_profile +
  integration API).
- Full 2026-04-21 suite: **223 passed, 4 skipped (pre-existing), 0
  xfailed**. Both strict-xfail markers flipped to passing assertions.
- `ruff check` on touched files: clean.

## Run commands

```bash
# Targeted — the previously xfailed cases + the new matrix
poetry run pytest \
  tests/unit/test_fns_validation_service.py \
  tests/integration/test_legal_profile_service.py \
  tests/integration/test_api_legal_profile.py --no-cov

# Full pre-launch suite
poetry run pytest \
  tests/unit/test_fns_validation_service.py \
  tests/unit/test_contract_template_map.py \
  tests/unit/test_yandex_ord_provider.py \
  tests/unit/test_yandex_ord_org_type_map.py \
  tests/integration/ --no-cov
```

## Follow-ups (out of scope)

- One-off backfill of existing DB rows with mismatched documents —
  needs a separate migration or admin audit script.
- Optional: enforce `self_employed_cert_file_id` presence in
  `check_completeness()` once the scan-upload step is mandatory (today
  the cert is uploaded via `POST /scan` after profile creation and is
  not required for `legal_status_completed=True`).

---

🔍 Verified against: 1237d01873e6a038a0bf97e957f105eb3e71c6bd | 📅 Updated: 2026-04-21T00:00:00Z
