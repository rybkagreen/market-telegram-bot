"""Lint: prevent revival of dead BillingService and YooKassaService methods.

Fail loudly if any of the methods deleted in fix/billing-rewrite-items-4-5
get re-added by mistake.
"""
import ast
from pathlib import Path


BILLING_SERVICE_PATH = (
    Path(__file__).parent.parent.parent
    / "src" / "core" / "services" / "billing_service.py"
)
YOOKASSA_SERVICE_PATH = (
    Path(__file__).parent.parent.parent
    / "src" / "core" / "services" / "yookassa_service.py"
)

DEAD_BILLING_METHODS = frozenset({
    "add_balance_rub",
    "deduct_balance_rub",
    "apply_referral_bonus",
    "apply_referral_signup_bonus",
    "apply_referral_first_campaign_bonus",
    "get_referral_stats",
    "freeze_campaign_funds",
    "refund_escrow_credits",
    # Промт-15: moved to YooKassaService.create_topup_payment with caller-controlled session
    "create_payment",
})

DEAD_YOOKASSA_METHODS = frozenset({
    "handle_webhook",
    "_credit_user",
})


def _get_method_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    methods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    methods.add(item.name)
    return methods


def test_no_dead_billing_methods_revived():
    """Dead BillingService methods must stay dead."""
    actual = _get_method_names(BILLING_SERVICE_PATH)
    revived = actual & DEAD_BILLING_METHODS
    assert not revived, (
        f"Dead BillingService methods were re-added: {revived}. "
        f"See BILLING_REWRITE_PLAN_2026-04-28.md items 4 and 6 — these were deleted "
        f"intentionally. Topup creation now lives in "
        f"YooKassaService.create_topup_payment with caller-controlled session "
        f"(Промт-15). Other dead methods route through PlanChangeService "
        f"(not yet introduced) or appropriate caller-controlled alternatives. "
        f"Do not re-add."
    )


def test_no_dead_yookassa_methods_revived():
    """Dead YooKassaService methods must stay dead."""
    actual = _get_method_names(YOOKASSA_SERVICE_PATH)
    revived = actual & DEAD_YOOKASSA_METHODS
    assert not revived, (
        f"Dead YooKassaService methods were re-added: {revived}. "
        f"Live webhook path is api/routers/billing.py::yookassa_webhook → "
        f"BillingService.process_topup_webhook. Do not re-add handle_webhook "
        f"or _credit_user."
    )


def test_billing_singleton_not_at_module_level():
    """The module-level singleton was dropped — verify it's not back."""
    src = BILLING_SERVICE_PATH.read_text(encoding="utf-8")
    lines = [
        line for line in src.splitlines()
        if line.strip().startswith("billing_service = BillingService(")
    ]
    assert not lines, (
        "Module-level singleton `billing_service = BillingService()` was re-added. "
        "Use BillingService() per call-site instead."
    )
