"""Unit tests for src.utils.db_errors.extract_constraint_name (5b.7b CL-3).

Helper encapsulates asyncpg-vs-aiosqlite IntegrityError diag divergence.
Tests cover the four shapes the helper recognises.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError

from src.utils.db_errors import extract_constraint_name


def _make_error_with_diag(constraint_name: str | None) -> IntegrityError:
    """Build an IntegrityError shaped like asyncpg's (orig.diag.constraint_name)."""
    diag = MagicMock()
    diag.constraint_name = constraint_name
    orig = MagicMock()
    orig.diag = diag
    err = IntegrityError("statement", {}, orig)
    err.orig = orig
    return err


def test_extract_constraint_name_asyncpg_style() -> None:
    """asyncpg-style error: orig.diag.constraint_name yields the name."""
    err = _make_error_with_diag("ix_foo_bar")
    assert extract_constraint_name(err) == "ix_foo_bar"


def test_extract_constraint_name_no_orig() -> None:
    """No underlying driver error → None."""
    err = IntegrityError("statement", {}, None)
    err.orig = None
    assert extract_constraint_name(err) is None


def test_extract_constraint_name_no_diag_attribute() -> None:
    """aiosqlite-style: orig has no diag attribute → None."""
    orig = MagicMock(spec=[])  # spec=[] means no attributes set
    err = IntegrityError("statement", {}, orig)
    err.orig = orig
    assert extract_constraint_name(err) is None


def test_extract_constraint_name_empty_constraint() -> None:
    """diag.constraint_name is empty string → None (treat as not extractable)."""
    err = _make_error_with_diag("")
    assert extract_constraint_name(err) is None
