# CHANGES: Consolidate 36 Alembic migrations into single initial schema

## Affected files

### Deleted (36 files)
All files in `src/db/migrations/versions/` except `__init__.py` — replaced by a single file.

### Created
- `src/db/migrations/versions/0001_initial_schema.py` — consolidated migration

## Business logic impact

**No functional change.** This is purely a database schema management cleanup.

The single migration replaces 36 incremental migrations that had accumulated over
the project history. The resulting database schema is identical to what the 36
migrations would have produced, with one intentional improvement:

**Fix applied:** `legal_profiles.user_id` changed from `BigInteger` → `Integer`
to match `users.id` type, eliminating a pre-existing FK type mismatch that
PostgreSQL silently allowed via implicit casting.

## New/changed DB contracts

None. All 33 tables, indexes, constraints, FK relationships, and ENUM types
remain identical to the schema produced by the original migration chain.

## Alembic state

- Previous head: `t1u2v3w4x5y6` (broken — `s33a001` referenced it but
  resolution was failing with `KeyError`)
- New head: `0001_initial_schema`
- `alembic check`: 0 pending migrations

## ENUM types preserved
`disputereason`, `disputeresolution`, `disputestatus`, `payoutstatus`,
`placementstatus`, `publicationformat`, `reputationaction`, `transactiontype`

---

🔍 Verified against: b39ceaab282f1929a41230272b26a27446c3cf5c | 📅 Updated: 2026-04-10T00:00:00Z
