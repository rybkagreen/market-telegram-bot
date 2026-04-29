"""Integration: GET /api/users/needs-accept-rules surfaces version-aware result.

Promt 15.9 — both audiences (mini_app + web_portal) hit the same carve-out
endpoint. We exercise the web_portal audience here; the service-level coverage
in test_acceptance_flow.py validates the underlying logic for both.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db_session
from src.api.main import app
from src.constants.legal import CONTRACT_TEMPLATE_VERSION
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


async def _seed_user(db_session: AsyncSession) -> User:
    user = User(
        telegram_id=998877001,
        first_name="Endpoint Probe",
        referral_code="endpoint_probe",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def test_needs_accept_rules_endpoint_returns_true_for_new_user(
    db_session: AsyncSession,
) -> None:
    """A user with no prior signed acceptance → endpoint returns needs_accept=True."""
    user = await _seed_user(db_session)

    async def _override_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    async def _override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/users/needs-accept-rules")
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "needs_accept" in body
    assert isinstance(body["needs_accept"], bool)
    assert body["needs_accept"] is True
    assert CONTRACT_TEMPLATE_VERSION
