"""Canonical PII / credential key list для Sentry event scrubbing.

Single source of truth для оба Sentry initializations:

- ``src/api/main.py`` — FastAPI process, scrubs ``event["request"]``.
- ``src/tasks/sentry_init.py`` — Celery worker process, scrubs
  ``event["breadcrumbs"]`` + ``event["extra"]``.

Both processes apply the **same** 18-key superset. Earlier divergence (FastAPI
13 keys, Celery 16 keys, symmetric diff 7) was unintentional drift from
independent edits — see series 16.5b CHANGES.

Categories (informational; single flat scrub list applies to всем events):

* **Auth credentials (4):** ``authorization``, ``password``, ``token``,
  ``x-api-key`` — HTTP headers и login bodies. Включены даже в Celery
  events потому что некоторые tasks принимают raw Authorization headers
  через arguments.
* **Identity PII / ФЗ-152 (5):** ``address``, ``email``, ``full_name``,
  ``inn``, ``phone`` — личные данные физических лиц, защищены ФЗ-152.
  Любой leak в Sentry breadcrumb'ах = ФЗ-152 violation.
* **Documents (6):** ``file_id``, ``inn_scan_file_id``,
  ``passport_issued_by``, ``passport_number``, ``passport_scan_file_id``,
  ``passport_series`` — идентификаторы документов и paspport fields.
* **Payment (3):** ``bank_account``, ``bank_corr_account``,
  ``yoomoney_wallet`` — реквизиты для выплат.

Sanitizer divergence note
-------------------------
``src/api/middleware/log_sanitizer.py`` uses an independent 12-key list
(historical decision, body-correct по own rationale). Sanitizer находится
в CLAUDE.md NEVER TOUCH list по решению владельца проекта. Когда / если
NEVER TOUCH будет осознанно lifted, sanitizer должен также import from
this module. Until then, sanitizer↔sentry asymmetry — known-allowed
condition, не drift.

Adding a key
------------
1. Determine category из comment block выше.
2. Add to ``SENTRY_PII_KEYS`` literal в alphabetical order within category.
3. Update count in tests/unit/test_pii_keys_canonical.py.
4. Confirm both Sentry processes pick it up (drift impossible by import).
"""
from __future__ import annotations

# Tuple для immutability + Sentry SDK iteration compatibility.
# Order: alphabetical within categories, categories grouped via comments.
SENTRY_PII_KEYS: tuple[str, ...] = (
    # Auth credentials
    "authorization",
    "password",
    "token",
    "x-api-key",
    # Identity PII / ФЗ-152
    "address",
    "email",
    "full_name",
    "inn",
    "phone",
    # Documents
    "file_id",
    "inn_scan_file_id",
    "passport_issued_by",
    "passport_number",
    "passport_scan_file_id",
    "passport_series",
    # Payment
    "bank_account",
    "bank_corr_account",
    "yoomoney_wallet",
)
"""18-key canonical PII/cred scrub list.

Imported by ``src/api/main.py`` и ``src/tasks/sentry_init.py``. Drift
between the two Sentry inits is impossible by construction.
"""
