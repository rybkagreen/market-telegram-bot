"""Unit tests: каждый act-template parse + render успешно с minimal ctx.

Промт 15.11: после wire 5 dead act-templates через get_act_template — нужно
verified что все 6 templates действительно рендерятся (Jinja syntax valid,
required vars присутствуют в _build_fee_context / minimal ctx).

Также проверяем что edition header (15.8) присутствует в каждом template.
"""
from __future__ import annotations

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.services.act_service import (
    ACT_TEMPLATE_ADVERTISER,
    ACT_TEMPLATE_MAP_OWNER,
    ACT_TEMPLATE_PLATFORM,
    TEMPLATES_DIR,
)
from src.core.services.contract_service import _build_fee_context


@pytest.fixture
def jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _minimal_ctx() -> dict[str, object]:
    """Minimal context covering all vars referenced by 6 act templates."""
    return {
        # Common
        "act_number": "АКТ-001-PREVIEW",
        "act_date": "29.04.2026",
        # Advertiser
        "advertiser_name": "Иван Иванов",
        "advertiser_inn": "771234567890",
        "advertiser_legal_status": "individual",
        # Owner (covers FL/NP/IE/LE)
        "owner_name": "Пётр Петров",
        "owner_inn": "770987654321",
        "owner_legal_status": "self_employed",
        "owner_passport_series": "4500",
        "owner_passport_number": "123456",
        "owner_passport_issued_by": "ОВД",
        "owner_passport_issue_date": "01.01.2020",
        "owner_kpp": "770101001",
        "owner_ogrnip": "320770000000001",
        "owner_vat_applicable": False,
        "owner_bank_name": "Сбербанк",
        "owner_bank_account": "40817810000000000001",
        "owner_bank_bik": "044525225",
        # Channel
        "channel_name": "Test Channel",
        "channel_id": 1,
        # Placement
        "final_price": 1000.00,
        "publication_format": "post_24h",
        "published_at": "29.04.2026",
        "deleted_at": "29.04.2026",
        "erid": "erid_test_PREVIEW",
        "ad_text": "Test ad text",
        # Platform requisites
        "platform_legal_name": "ООО РекХарбор",
        "platform_inn": "7701234567",
        "platform_kpp": "770101001",
        "platform_ogrn": "1027700000001",
        "platform_address": "Москва, ул. Тверская, 1",
        "platform_bank_name": "Сбербанк",
        "platform_bank_account": "40702810000000000001",
        "platform_bank_bik": "044525225",
        "platform_bank_corr_account": "30101810400000000225",
        # Fee + edition vars (15.8)
        **_build_fee_context(),
    }


def test_platform_act_template_renders(jinja_env: Environment) -> None:
    template = jinja_env.get_template(ACT_TEMPLATE_PLATFORM)
    html = template.render(**_minimal_ctx())
    assert html
    assert "Редакция от 28 апреля 2026 г." in html
    assert "Заказчик" in html  # advertiser party header


def test_advertiser_act_template_renders(jinja_env: Environment) -> None:
    template = jinja_env.get_template(ACT_TEMPLATE_ADVERTISER)
    html = template.render(**_minimal_ctx())
    assert html
    assert "Редакция от 28 апреля 2026 г." in html
    assert "Заказчик" in html


def test_owner_fl_template_renders_with_ndfl_marker(jinja_env: Environment) -> None:
    template = jinja_env.get_template(ACT_TEMPLATE_MAP_OWNER["individual"])
    html = template.render(**_minimal_ctx())
    assert html
    assert "Редакция от 28 апреля 2026 г." in html
    assert "НДФЛ" in html
    assert "13%" in html


def test_owner_np_template_renders_with_npd_marker(jinja_env: Environment) -> None:
    template = jinja_env.get_template(ACT_TEMPLATE_MAP_OWNER["self_employed"])
    html = template.render(**_minimal_ctx())
    assert html
    assert "Редакция от 28 апреля 2026 г." in html
    assert "НПД" in html


def test_owner_ie_template_renders_with_ie_marker(jinja_env: Environment) -> None:
    template = jinja_env.get_template(ACT_TEMPLATE_MAP_OWNER["individual_entrepreneur"])
    html = template.render(**_minimal_ctx())
    assert html
    assert "Редакция от 28 апреля 2026 г." in html
    assert "ИП" in html
    assert "ОГРНИП" in html


def test_owner_le_template_renders_with_le_marker(jinja_env: Environment) -> None:
    template = jinja_env.get_template(ACT_TEMPLATE_MAP_OWNER["legal_entity"])
    html = template.render(**_minimal_ctx())
    assert html
    assert "Редакция от 28 апреля 2026 г." in html
    assert "ОГРН" in html or "КПП" in html
