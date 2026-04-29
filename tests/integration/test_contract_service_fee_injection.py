"""Integration tests: ContractService.render_platform_rules injects
fee percentages and edition header from constants/fees.py + legal.py.

Promt 15.8 — verifies that rendered platform_rules HTML contains the
current canonical fee percentages, edition header, version 1.1, and the
new § 18 (115-FZ) / § 19 (jurisdiction) sections.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.contract_service import ContractService

pytestmark = pytest.mark.asyncio


async def test_platform_rules_contains_current_commission_percentages(
    db_session: AsyncSession,
) -> None:
    """Rendered platform_rules contains 20% / 80% / 1,5% / 78,8%."""
    service = ContractService(db_session)
    html = await service.render_platform_rules()

    assert "20%" in html, "PLATFORM_COMMISSION_RATE 20% missing"
    assert "80%" in html, "OWNER_SHARE_RATE 80% missing"
    assert "1,5%" in html, "SERVICE_FEE_RATE 1,5% missing"
    assert "78,8%" in html, "owner_net 78,8% missing"


async def test_platform_rules_contains_edition_header(
    db_session: AsyncSession,
) -> None:
    """Rendered platform_rules contains edition date + version 1.1."""
    service = ContractService(db_session)
    html = await service.render_platform_rules()

    assert "Редакция от 28 апреля 2026 г." in html
    assert "версия 1.1" in html


async def test_platform_rules_contains_115fz_section(
    db_session: AsyncSession,
) -> None:
    """§ 18 (115-FZ) anti-money-laundering section is present."""
    service = ContractService(db_session)
    html = await service.render_platform_rules()

    assert "115-ФЗ" in html
    assert "противодействи" in html.lower()


async def test_platform_rules_contains_jurisdiction_section(
    db_session: AsyncSession,
) -> None:
    """§ 19 (jurisdiction) section is present."""
    service = ContractService(db_session)
    html = await service.render_platform_rules()

    assert "Юрисдикция" in html
    assert "Российской Федерации" in html
