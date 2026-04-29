"""Unit tests for CONTRACT_TEMPLATE_VERSION + platform_rules.html legal text.

Validates that legal-text rewrite (1.2) removed customer-visible
"кредит" (currency lie) from platform_rules.html, and that version
constant matches expected post-bump value.
"""

from __future__ import annotations

from pathlib import Path


def test_contract_template_version_is_1_2():
    from src.constants.legal import CONTRACT_TEMPLATE_VERSION

    assert CONTRACT_TEMPLATE_VERSION == "1.2"


def test_platform_rules_template_uses_rubles_not_credits():
    template_path = Path(__file__).parent.parent.parent / (
        "src/templates/contracts/platform_rules.html"
    )
    content = template_path.read_text(encoding="utf-8")

    assert "кредит" not in content.lower(), (
        "platform_rules.html содержит 'кредит' — currency lie post `credits → balance_rub` "
        "migration. Текст должен использовать 'рубли' / '₽'."
    )
