"""AST lint: forbid hardcoded fee literals outside src/constants/fees.py.

Scans `src/` Python files for `Decimal("0.20")`, `Decimal("0.80")`, etc.
Top-level UPPER_SNAKE_CASE constant assignments in `src/constants/*.py` are
allowed (those modules are constant-definition by design). Tax / scoring /
config modules outside the constants area are explicitly allowlisted —
their literals are non-fee semantic concepts (income tax rates, scoring
weights, post-lifetime ratios) deferred to a separate migration.

TS / HTML / template scanning — separate test files in промтах 15.8 / 15.10.
"""

import ast
from pathlib import Path

# Source root
SRC_ROOT = Path(__file__).parent.parent.parent / "src"

# Files allowed to contain matching literals.
# - fees.py: canonical home.
# - other constants/*.py: define non-fee rate constants (velocity, format
#   multipliers, plan prices) which legitimately use Decimal literals.
# - tax / scoring / config: distinct semantic concepts; migration is out
#   of scope for Промт 15.7 — surfaced as finding, deferred.
ALLOWED_FILES = {
    SRC_ROOT / "constants" / "fees.py",
    SRC_ROOT / "constants" / "payments.py",
    SRC_ROOT / "constants" / "legal.py",
    SRC_ROOT / "constants" / "ai.py",
    SRC_ROOT / "constants" / "content_filter.py",
    SRC_ROOT / "constants" / "tariffs.py",
    SRC_ROOT / "constants" / "expense_categories.py",
    SRC_ROOT / "constants" / "erid.py",
    SRC_ROOT / "constants" / "parser.py",
    SRC_ROOT / "constants" / "__init__.py",
    # Tax computation modules — 0.15/0.06 here is income tax rate, not
    # placement commission. Pending separate migration to fees.py.
    SRC_ROOT / "db" / "repositories" / "tax_repo.py",
    SRC_ROOT / "core" / "services" / "tax_aggregation_service.py",
    SRC_ROOT / "db" / "models" / "platform_quarterly_revenue.py",
    # Reputation/review scoring weights — NOT fees.
    SRC_ROOT / "core" / "services" / "review_service.py",
    # Config defaults (post-lifetime ratio, etc.) — NOT fees.
    SRC_ROOT / "config" / "settings.py",
}

# Decimal literal strings that look like fee rates the new model manages.
FORBIDDEN_DECIMAL_LITERALS = {
    "0.20",
    "0.80",  # placement commission split
    "0.15",
    "0.85",  # OLD platform commission — must not appear post-rewrite
    "0.06",  # OLD platform tax rate (also USN — but USN lives in fees.py)
    "0.035",  # YooKassa fee rate
    "0.015",  # service fee rate (also: PAYOUT_FEE_RATE — defined in payments.py)
    "0.50",
    "0.40",
    "0.10",  # cancel splits
    "0.788",
    "0.212",  # computed owner net / platform total
}

# Float literals UNAMBIGUOUSLY fee-related — values unlikely to appear in
# PDF coordinates, AI temperatures, scoring weights, or thresholds. The
# common values (0.5, 0.4, 0.1, 0.2, 0.15, 0.85, 0.06, 0.10) are too noisy
# at the float level; the Decimal-based lint above catches the
# money-handling cases reliably.
FORBIDDEN_FLOATS: set[float] = {
    0.035,  # YooKassa fee — extremely specific
    0.788,  # computed owner net — extremely specific
    0.212,  # computed platform total — extremely specific
}


def _find_decimal_literals(tree: ast.AST) -> list[tuple[str, int]]:
    """Find Decimal("...") calls with literal string args."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Decimal"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            found.append((node.args[0].value, node.lineno))
    return found


def _iter_python_files(skip_allowed: bool = True) -> list[Path]:
    files: list[Path] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        if skip_allowed and py_file in ALLOWED_FILES:
            continue
        files.append(py_file)
    return files


def test_no_hardcoded_fee_decimal_literals_in_python_src() -> None:
    """No `Decimal("0.20")` etc. outside src/constants/fees.py + allowlist."""
    violations: list[str] = []

    for py_file in _iter_python_files():
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for literal, lineno in _find_decimal_literals(tree):
            if literal in FORBIDDEN_DECIMAL_LITERALS:
                rel = py_file.relative_to(SRC_ROOT.parent)
                violations.append(f"  {rel}:{lineno} — Decimal(\"{literal}\")")

    assert not violations, (
        "Hardcoded fee Decimal literals found in src/. Use imports from "
        "src/constants/fees.py instead.\n\nViolations:\n"
        + "\n".join(violations)
    )


def test_no_hardcoded_fee_float_literals_in_python_src() -> None:
    """No bare float literals like 0.20 or 0.035 (use Decimal from constants)."""
    violations: list[str] = []

    for py_file in _iter_python_files():
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, float)
                and node.value in FORBIDDEN_FLOATS
            ):
                rel = py_file.relative_to(SRC_ROOT.parent)
                violations.append(f"  {rel}:{node.lineno} — {node.value}")

    assert not violations, (
        "Hardcoded fee float literals in src/.\n\nViolations:\n"
        + "\n".join(violations)
    )
