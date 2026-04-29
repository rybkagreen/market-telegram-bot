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


# ==================== HTML TEMPLATE LINT (Промт 15.8) ====================

import re  # noqa: E402

TEMPLATES_ROOT = SRC_ROOT / "templates"

# Canonical-fee percentages (from src/constants/fees.py). Hits in legal HTML
# templates (outside Jinja `{{ ... }}` expressions) are forbidden — they
# must be rendered through `_build_fee_context()` vars.
#
# Deliberately narrow set: only canonical 15.7 model values. Cancel splits
# (50/40/10) and tax rates (6/15/85) appear in scenario-specific legacy
# language too often to lint reliably; we cover them via Jinja injection
# + integration tests, not regex.
FORBIDDEN_PCT_PATTERNS_HTML: list[str] = [
    r"\b20\s*%",         # PLATFORM_COMMISSION_RATE
    r"\b80\s*%",         # OWNER_SHARE_RATE
    r"\b1[.,]5\s*%",     # SERVICE_FEE_RATE / PAYOUT_FEE_RATE
    r"\b78[.,][58]\s*%",  # OWNER_NET_RATE (78,8% or 78,5% legacy)
    r"\b21[.,]2\s*%",    # PLATFORM_TOTAL_RATE
    r"\b3[.,]5\s*%",     # YOOKASSA_FEE_RATE
]

# Files exempt entirely — reference tax law / accounting / NDFL rates that
# fall outside platform's centralized fee model. They legitimately contain
# things like "20% НДС", "НПД 6%", etc.
TEMPLATE_EXEMPT_FILES: set[str] = {
    "src/templates/acts/act_owner_fl.html",                       # NDFL
    "src/templates/acts/act_owner_np.html",                       # NPD/НДФЛ fallback
    "src/templates/acts/act_owner_ie.html",                       # USN/VAT
    "src/templates/acts/act_owner_le.html",                       # VAT
    "src/templates/contracts/owner_service_individual.html",      # NDFL scale
    "src/templates/contracts/owner_service_self_employed.html",   # NPD
    "src/templates/contracts/owner_service_ie.html",              # USN/VAT
    "src/templates/invoices/invoice_b2b.html",                    # VAT
    "src/templates/kudir/kudir_book.html",                        # accounting
}

# Per-line opt-out marker. When a line contains this string, the lint
# skips it. Use sparingly with an inline reason — e.g. legacy cancel
# scenarios pending a separate centralization.
NOQA_MARKER = "noqa-fees"


def _strip_jinja_expressions(content: str) -> str:
    """Remove {{ ... }} and {% ... %} blocks so they don't trigger the lint."""
    content = re.sub(r"\{\{.*?\}\}", "", content, flags=re.DOTALL)
    content = re.sub(r"\{%.*?%\}", "", content, flags=re.DOTALL)
    return content


def test_no_hardcoded_percentages_in_legal_templates() -> None:
    """Legal HTML templates must use Jinja2 vars for canonical fee percentages.

    Skips:
    - Files in TEMPLATE_EXEMPT_FILES (tax-law rates outside platform control).
    - Content inside `{{ ... }}` / `{% ... %}` (Jinja expressions, by design).
    - Lines containing `noqa-fees` (per-line opt-out for documented exceptions).
    """
    violations: list[str] = []

    for tmpl in TEMPLATES_ROOT.rglob("*.html"):
        rel = tmpl.relative_to(SRC_ROOT.parent)
        rel_str = str(rel).replace("\\", "/")

        if rel_str in TEMPLATE_EXEMPT_FILES:
            continue

        try:
            raw = tmpl.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for lineno, line in enumerate(raw.splitlines(), start=1):
            if NOQA_MARKER in line:
                continue
            stripped = _strip_jinja_expressions(line)
            for pattern in FORBIDDEN_PCT_PATTERNS_HTML:
                m = re.search(pattern, stripped)
                if m:
                    violations.append(
                        f"  {rel_str}:{lineno} — '{m.group()}' "
                        f"(use {{{{ var }}}}% from ContractService._build_fee_context())"
                    )

    assert not violations, (
        "Hardcoded canonical-fee percentages found in legal templates. "
        "Use Jinja2 vars from ContractService._build_fee_context() instead.\n\n"
        "Violations:\n" + "\n".join(violations)
    )
