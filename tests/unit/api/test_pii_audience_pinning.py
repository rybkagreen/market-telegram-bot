"""
Regression tests for series 16.1 (Group A — PII audience pinning).

Closes:
    * BL-046 (CRIT-2) — `/api/payouts/*` accepted mini_app JWT.
    * BL-049 (MED-5) — `/api/admin/*` not pinned к web_portal-only.

Cross-references PII_AUDIT_2026-04-28.md §§ O.2, O.4 and Phase 1 pattern
(contracts.py, legal_profile.py).

Approach:
    * Use real `get_current_user_from_web_portal` dep with stubbed DB
      (мirroring `test_jwt_aud_claim.py`) — full audience-decode path.
    * Real mini_app JWT → request returns 403 на каждом обстреливаемом
      эндпоинте.
    * Real web_portal JWT → не-admin user → 403 (admin gate работает),
      admin user → 200 / 4xx по бизнес-логике (не аутентификации).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.auth_utils import JwtSource, create_jwt_token
from src.api.dependencies import get_db_session, get_redis
from src.api.main import app


class _FakeRedis:
    """Minimal Redis stub — auth chain uses get for jti / setex для rate-limit."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._ttl: dict[str, float] = {}

    async def setex(self, key: str, ttl: int, value: str | bytes) -> None:
        if isinstance(value, str):
            value = value.encode()
        self._store[key] = value
        self._ttl[key] = datetime.now(UTC).timestamp() + ttl

    async def incr(self, key: str) -> int:
        cur = int(self._store.get(key, b"0") or b"0") + 1
        self._store[key] = str(cur).encode()
        return cur

    async def expire(self, key: str, ttl: int) -> None:
        self._ttl[key] = datetime.now(UTC).timestamp() + ttl

    async def get(self, key: str) -> bytes | None:
        if key not in self._store:
            return None
        if self._ttl.get(key, float("inf")) < datetime.now(UTC).timestamp():
            self._store.pop(key, None)
            return None
        return self._store[key]

    async def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._store:
                self._store.pop(k, None)
                self._ttl.pop(k, None)
                n += 1
        return n


def _make_user(*, user_id: int, is_admin: bool) -> Any:
    user = MagicMock()
    user.id = user_id
    user.telegram_id = 100_000 + user_id
    user.is_active = True
    user.is_admin = is_admin
    plan = MagicMock()
    plan.value = "free"
    user.plan = plan
    user.legal_profile = None
    return user


@pytest_asyncio.fixture
async def stub_user_lookup(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Patch `async_session_factory` в dependencies.py чтобы lookup юзера
    отдавал нашего fake user. is_admin читается из payload sub.
    """

    class _Result:
        def __init__(self, user: Any) -> None:
            self._user = user

        def scalar_one_or_none(self) -> Any:
            return self._user

    class _Session:
        def __init__(self, registry: dict[int, Any]) -> None:
            self._registry = registry

        async def execute(self, _stmt: Any) -> Any:
            user_id = next(iter(self._registry))
            return _Result(self._registry.get(user_id))

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

        async def close(self) -> None:
            return None

        async def get(self, *_args: Any, **_kwargs: Any) -> Any:
            return None

    registry: dict[int, Any] = {}

    @asynccontextmanager
    async def _factory() -> AsyncGenerator[_Session]:
        yield _Session(registry)

    monkeypatch.setattr("src.api.dependencies.async_session_factory", _factory)
    return registry


@pytest_asyncio.fixture
async def client(
    stub_user_lookup: dict[int, Any],
) -> AsyncGenerator[AsyncClient]:
    fake_redis = _FakeRedis()

    async def _override_redis() -> _FakeRedis:
        return fake_redis

    async def _stub_db_session() -> AsyncGenerator[Any]:
        # The endpoint may exercise commit/rollback on success/error paths;
        # an in-memory stub is enough — these tests fence-check the auth dep
        # chain, not DB business logic.
        session = MagicMock()
        session.commit = _async_noop
        session.rollback = _async_noop
        session.close = _async_noop
        session.get = _async_none
        session.execute = _async_empty_result
        session.add = lambda *_a, **_kw: None
        session.refresh = _async_noop
        yield session

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_session] = _stub_db_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Attach registry on client so tests can register users.
            c._stub_user_registry = stub_user_lookup  # type: ignore[attr-defined]
            yield c
    finally:
        app.dependency_overrides.clear()


async def _async_noop(*_args: Any, **_kwargs: Any) -> None:
    return None


async def _async_none(*_args: Any, **_kwargs: Any) -> Any:
    return None


async def _async_empty_result(*_args: Any, **_kwargs: Any) -> Any:
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar.return_value = 0
    result.scalar_one_or_none.return_value = None
    return result


def _register_and_token(
    client: AsyncClient,
    user_id: int,
    *,
    is_admin: bool,
    source: Literal["mini_app", "web_portal"],
) -> str:
    """Создать fake user, положить в registry, вернуть JWT с заданным aud."""
    user = _make_user(user_id=user_id, is_admin=is_admin)
    registry: dict[int, Any] = client._stub_user_registry  # type: ignore[attr-defined]
    registry.clear()
    registry[user_id] = user
    aud: JwtSource = source
    return create_jwt_token(user.id, user.telegram_id, "free", source=aud)


# ─── BL-046: /api/payouts/* отклоняет mini_app JWT ──────────────────


class TestPayoutsRejectMiniAppJwt:
    """`/api/payouts/*` (CRIT-2 / BL-046) — pinned к web_portal-only."""

    async def test_get_my_payouts_with_mini_app_jwt_returns_403(
        self, client: AsyncClient
    ) -> None:
        token = _register_and_token(client, 7001, is_admin=False, source="mini_app")
        resp = await client.get(
            "/api/payouts/", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, resp.text

    async def test_get_payout_by_id_with_mini_app_jwt_returns_403(
        self, client: AsyncClient
    ) -> None:
        token = _register_and_token(client, 7002, is_admin=False, source="mini_app")
        resp = await client.get(
            "/api/payouts/123", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, resp.text

    async def test_create_payout_with_mini_app_jwt_returns_403(
        self, client: AsyncClient
    ) -> None:
        token = _register_and_token(client, 7003, is_admin=False, source="mini_app")
        resp = await client.post(
            "/api/payouts/",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": "1500.00", "payment_details": "40817810000000000001"},
        )
        assert resp.status_code == 403, resp.text


# ─── BL-049: /api/admin/* отклоняет mini_app JWT (даже admin'a) ─────


class TestAdminRejectMiniAppJwt:
    """`/api/admin/*` (MED-5 / BL-049) — `get_current_admin_user` теперь
    wraps `get_current_user_from_web_portal`, поэтому mini_app JWT
    отбивается до проверки is_admin."""

    async def test_admin_users_list_with_mini_app_jwt_returns_403(
        self, client: AsyncClient
    ) -> None:
        # Даже если is_admin=True — audience-несовпадение бьёт раньше.
        token = _register_and_token(client, 9001, is_admin=True, source="mini_app")
        resp = await client.get(
            "/api/admin/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, resp.text

    async def test_admin_payouts_list_with_mini_app_jwt_returns_403(
        self, client: AsyncClient
    ) -> None:
        token = _register_and_token(client, 9002, is_admin=True, source="mini_app")
        resp = await client.get(
            "/api/admin/payouts", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, resp.text

    async def test_admin_platform_settings_with_mini_app_jwt_returns_403(
        self, client: AsyncClient
    ) -> None:
        # § O.5 — bank fields response. После audience pin mini_app не доберётся.
        token = _register_and_token(client, 9003, is_admin=True, source="mini_app")
        resp = await client.get(
            "/api/admin/platform-settings", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, resp.text

    async def test_admin_legal_profiles_with_mini_app_jwt_returns_403(
        self, client: AsyncClient
    ) -> None:
        token = _register_and_token(client, 9004, is_admin=True, source="mini_app")
        resp = await client.get(
            "/api/admin/legal-profiles",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text


# ─── Sanity: web_portal JWT не отбивается аудиенцией ────────────────


class TestWebPortalJwtPassesAudienceGate:
    """Sanity: после pin'а web_portal JWT по-прежнему проходит audience-gate
    (отбиться может на бизнес-логике, но не на 403 audience)."""

    async def test_web_portal_jwt_payouts_does_not_403_on_audience(
        self, client: AsyncClient
    ) -> None:
        token = _register_and_token(client, 7100, is_admin=False, source="web_portal")
        resp = await client.get(
            "/api/payouts/", headers={"Authorization": f"Bearer {token}"}
        )
        # 200/204/4xx-by-business-logic, но не 403 от audience.
        # У не-admin user'а GET /api/payouts/ возвращает свой список → 200.
        assert resp.status_code != 403, resp.text

    async def test_web_portal_admin_jwt_admin_users_does_not_403_on_audience(
        self, client: AsyncClient
    ) -> None:
        # is_admin=True + web_portal aud = и audience и authz пройдены.
        # Endpoint может вернуть 200 либо 5xx из-за заглушенной DB —
        # главное не 403.
        token = _register_and_token(client, 9100, is_admin=True, source="web_portal")
        resp = await client.get(
            "/api/admin/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code != 403, resp.text

    async def test_web_portal_non_admin_jwt_admin_users_returns_403_admin_gate(
        self, client: AsyncClient
    ) -> None:
        # web_portal aud → audience pass → is_admin=False → 403 от
        # is_admin gate (а не от audience). Сообщение должно сослаться на admin.
        token = _register_and_token(client, 7101, is_admin=False, source="web_portal")
        resp = await client.get(
            "/api/admin/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, resp.text
        assert "admin" in resp.json().get("detail", "").lower()
