"""Unit tests for SupplementaryAgreementService template routing and rendering.

Smoke coverage:
1. `_select_template` returns correct path per (role, legal_status) per Q-B.2.
2. Each of 5 ДС templates renders без Jinja2 exception против минимального context.
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.services.supplementary_agreement_service import (
    _TEMPLATE_ADVERTISER,
    _TEMPLATE_OWNER_BY_LEGAL_STATUS,
    SupplementaryAgreementService,
)

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "src" / "templates" / "contracts"


def test_advertiser_role_returns_advertiser_template() -> None:
    assert (
        SupplementaryAgreementService._select_template("advertiser", "individual")
        == _TEMPLATE_ADVERTISER
    )
    assert (
        SupplementaryAgreementService._select_template("advertiser", "legal_entity")
        == _TEMPLATE_ADVERTISER
    )
    assert _TEMPLATE_ADVERTISER == "supplementary_agreement_advertiser.html"


@pytest.mark.parametrize(
    "legal_status,expected_filename",
    [
        ("individual", "supplementary_agreement_owner_individual.html"),
        ("self_employed", "supplementary_agreement_owner_self_employed.html"),
        ("individual_entrepreneur", "supplementary_agreement_owner_ie.html"),
        ("legal_entity", "supplementary_agreement_owner_le.html"),
    ],
)
def test_owner_role_returns_legal_status_specific_template(
    legal_status: str, expected_filename: str
) -> None:
    assert (
        SupplementaryAgreementService._select_template("owner", legal_status) == expected_filename
    )
    assert _TEMPLATE_OWNER_BY_LEGAL_STATUS[legal_status] == expected_filename


def test_owner_role_unknown_legal_status_raises() -> None:
    with pytest.raises(ValueError, match="legal_status invalid"):
        SupplementaryAgreementService._select_template("owner", "unknown_status")


def test_owner_role_none_legal_status_raises() -> None:
    with pytest.raises(ValueError, match="legal_status invalid"):
        SupplementaryAgreementService._select_template("owner", None)


def test_unknown_role_raises() -> None:
    with pytest.raises(ValueError, match="unknown role"):
        SupplementaryAgreementService._select_template("platform", "individual")  # type: ignore[arg-type]


@pytest.fixture
def render_ctx() -> dict[str, object]:
    """Minimal Jinja2 context covering all vars referenced in ДС templates."""
    return {
        # fee context (from _build_fee_context — subset that templates use)
        "platform_commission_pct": "20",
        "owner_share_pct": "80",
        "service_fee_pct": "1,5",
        "owner_net_pct": "78,8",
        "platform_total_pct": "21,2",
        "contract_template_version": "1.0",
        "contract_edition_date": "28 апреля 2026 г.",
        # placement_ctx (from _build_placement_ctx)
        "parent_contract_number": 42,
        "parent_contract_date": "01 мая 2026",
        "parent_contract_type_label": "Рамочный договор рекламодателя",
        "placement_id": 100,
        "placement_format_human": "обычный пост, 24 часа в ленте",
        "placement_duration_hours": 24,
        "placement_scheduled_at": "15.05.2026 12:00",
        "placement_channel_title": "Test Channel",
        "placement_channel_link": "@test_channel",
        "placement_ad_text": "Тестовый рекламный текст",
        "placement_gross_amount": "1 000,00",
        "owner_gross_amount": "800,00",
        "owner_net_amount": "788,00",
        "platform_commission_amount": "200,00",
        "service_fee_amount": "12,00",
        "erid_placeholder": "присваивается при регистрации в ОРД перед публикацией",
        # party + platform reqs
        "contract_id": 999,
        "contract_date": "14 мая 2026",
        "platform_name": "RekHarborBot",
        "legal_name": "Тестовая Сторона",
        "inn": "1234567890",
        "kpp": "",
        "ogrn": "",
        "ogrnip": "",
        "address": "г. Москва, ул. Тестовая, 1",
        "tax_regime": "УСН доходы",
        "bank_name": "ТЕСТ-БАНК",
        "bank_bik": "044525225",
        "legal_status": "individual",
        # platform context (from _get_platform_ctx)
        "platform_legal_name": "ООО «РекХарбор»",
        "platform_inn": "9999999999",
        "platform_kpp": "999901001",
        "platform_ogrn": "1234567890123",
        "platform_address": "г. Москва, ул. Платформенная, 1",
        "platform_bank_name": "ПЛАТФОРМА-БАНК",
        "platform_bank_account": "40702810999999999999",
        "platform_bank_bik": "044525000",
        "platform_bank_corr_account": "30101810000000000000",
    }


@pytest.mark.parametrize(
    "template_name",
    [
        "supplementary_agreement_advertiser.html",
        "supplementary_agreement_owner_individual.html",
        "supplementary_agreement_owner_self_employed.html",
        "supplementary_agreement_owner_ie.html",
        "supplementary_agreement_owner_le.html",
    ],
)
def test_supplementary_template_renders_without_error(
    template_name: str, render_ctx: dict[str, object]
) -> None:
    """Each ДС template must render with the canonical context — no Jinja2 errors."""
    env = Environment(
        loader=FileSystemLoader([str(_TEMPLATES_DIR), str(_TEMPLATES_DIR.parent)]),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_name)
    rendered = template.render(**render_ctx)

    assert "<html" in rendered
    assert "</html>" in rendered
    assert "Дополнительное соглашение" in rendered
    assert str(render_ctx["contract_id"]) in rendered
    assert str(render_ctx["parent_contract_number"]) in rendered
    assert render_ctx["placement_channel_title"] in rendered  # type: ignore[operator]
    assert render_ctx["erid_placeholder"] in rendered  # type: ignore[operator]
    # Financial figures from the shared partial
    assert render_ctx["placement_gross_amount"] in rendered  # type: ignore[operator]
    assert render_ctx["owner_gross_amount"] in rendered  # type: ignore[operator]


def test_advertiser_template_mentions_advertiser_role(render_ctx: dict[str, object]) -> None:
    env = Environment(
        loader=FileSystemLoader([str(_TEMPLATES_DIR), str(_TEMPLATES_DIR.parent)]),
        autoescape=select_autoescape(["html", "xml"]),
    )
    rendered = env.get_template("supplementary_agreement_advertiser.html").render(**render_ctx)
    assert "Рекламодатель" in rendered


@pytest.mark.parametrize(
    "template_name,expected_marker",
    [
        ("supplementary_agreement_owner_individual.html", "НДФЛ"),
        ("supplementary_agreement_owner_self_employed.html", "НПД"),
        ("supplementary_agreement_owner_ie.html", "индивидуальный предприниматель"),
        ("supplementary_agreement_owner_le.html", "юридическое лицо"),
    ],
)
def test_owner_templates_have_legal_status_specific_markers(
    template_name: str, expected_marker: str, render_ctx: dict[str, object]
) -> None:
    env = Environment(
        loader=FileSystemLoader([str(_TEMPLATES_DIR), str(_TEMPLATES_DIR.parent)]),
        autoescape=select_autoescape(["html", "xml"]),
    )
    rendered = env.get_template(template_name).render(**render_ctx)
    assert expected_marker in rendered, f"{template_name} missing {expected_marker!r}"
    assert "Владелец канала" in rendered


def test_placement_ctx_amounts_use_constants() -> None:
    """_build_placement_ctx should compute amounts using fees constants (no inline numbers)."""
    from datetime import datetime as _dt

    from src.constants.fees import (
        OWNER_NET_RATE,
        OWNER_SHARE_RATE,
        PLATFORM_COMMISSION_RATE,
        SERVICE_FEE_RATE,
    )

    # Construct minimum stub of PlacementRequest and Contract
    class _StubChannel:
        title = "Stub"
        username = "stub"
        id = 1

    class _StubPlacement:
        id = 7
        final_price = Decimal("1000.00")
        final_schedule = _dt(2026, 5, 14, 12, 0, tzinfo=UTC)
        publication_format = __import__(
            "src.db.models.placement_request",
            fromlist=["PublicationFormat"],
        ).PublicationFormat.post_24h
        ad_text = "stub"
        channel = _StubChannel()

    class _StubParent:
        id = 11
        role = "advertiser"
        signed_at = _dt(2026, 5, 1, tzinfo=UTC)

    ctx = SupplementaryAgreementService._build_placement_ctx(
        _StubPlacement(),
        _StubParent(),  # type: ignore[arg-type]
    )

    # 1000 * 0.80 = 800.00 — Decimal-aware
    expected_owner_gross = (Decimal("1000.00") * OWNER_SHARE_RATE).quantize(Decimal("0.01"))
    expected_owner_net = (Decimal("1000.00") * OWNER_NET_RATE).quantize(Decimal("0.01"))
    expected_platform = (Decimal("1000.00") * PLATFORM_COMMISSION_RATE).quantize(Decimal("0.01"))
    expected_fee = (expected_owner_gross * SERVICE_FEE_RATE).quantize(Decimal("0.01"))

    # Russian-format check: assert no inline magic, values reflect constants
    assert ctx["owner_gross_amount"] == f"{expected_owner_gross:,.2f}".replace(",", " ").replace(
        ".", ","
    )
    assert ctx["owner_net_amount"] == f"{expected_owner_net:,.2f}".replace(",", " ").replace(
        ".", ","
    )
    assert ctx["platform_commission_amount"] == f"{expected_platform:,.2f}".replace(
        ",", " "
    ).replace(".", ",")
    assert ctx["service_fee_amount"] == f"{expected_fee:,.2f}".replace(",", " ").replace(".", ",")
    assert ctx["placement_format_human"] == "обычный пост, 24 часа в ленте"
    assert ctx["placement_duration_hours"] == 24
    assert ctx["parent_contract_type_label"] == "Рамочный договор рекламодателя"
    assert ctx["erid_placeholder"] == "присваивается при регистрации в ОРД перед публикацией"
