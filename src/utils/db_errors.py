"""Helpers for SQLAlchemy error introspection.

Encapsulates driver-API divergence between asyncpg (production) and
aiosqlite (unit tests). asyncpg's IntegrityError exposes diagnostic
information via ``e.orig.diag.constraint_name``; aiosqlite's does not.

Phase 3b 5b.7b: introduced for X-Idempotency-Key strict-distinguish error
handling (Marina Q5=(б)). Single-purpose helper; do not extend beyond
IntegrityError input without separate review.
"""

from sqlalchemy.exc import IntegrityError


def extract_constraint_name(error: IntegrityError) -> str | None:
    """Extract PostgreSQL constraint name from an IntegrityError if available.

    Returns the constraint name (str) when extractable from
    ``error.orig.diag.constraint_name`` (asyncpg shape).

    Returns None when:

    * ``error.orig`` is None
    * ``error.orig`` has no ``diag`` attribute (e.g. aiosqlite)
    * ``diag`` has no ``constraint_name`` attribute
    * ``constraint_name`` is None or empty string

    Caller convention: None means "cannot identify which constraint
    was violated" → caller should treat as no-match and re-raise (per
    strict-distinguish semantics, Marina Q5=(б)).
    """
    diag = getattr(getattr(error, "orig", None), "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) and name else None
