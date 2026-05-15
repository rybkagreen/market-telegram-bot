"""BL-107 Phase B.8 / BL-002 — aiohttp Telegram Bot API stub server tests.

Verifies the stub returns Bot-API-shaped envelopes, fixture-backed payloads,
and tracks side-effects in StubState. Runs the stub in-process via
aiohttp.test_utils — no Docker required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from tests.e2e.telegram_api_stub.app import build_app
from tests.e2e.telegram_api_stub.fixtures import Fixtures, default_fixtures, load_fixtures
from tests.e2e.telegram_api_stub.state import StubState


@pytest.fixture
async def stub_client():
    fixtures = default_fixtures()
    state = StubState()
    app = build_app(fixtures, state)
    async with TestClient(TestServer(app)) as client:
        yield client, fixtures, state


TOKEN_PATH = "/bot7000000001:dummy_secret"


async def test_getme_returns_bot_identity(stub_client):
    client, fixtures, _state = stub_client
    resp = await client.get(f"{TOKEN_PATH}/getMe")
    assert resp.status == 200
    body = await resp.json()
    assert body["ok"] is True
    assert body["result"]["id"] == fixtures.bot["id"]
    assert body["result"]["username"] == "rekharbor_test_bot"


async def test_getchat_returns_channel_info_by_username(stub_client):
    client, _fixtures, _state = stub_client
    resp = await client.get(f"{TOKEN_PATH}/getChat", params={"chat_id": "@verified_channel"})
    assert resp.status == 200
    body = await resp.json()
    assert body["ok"] is True
    assert body["result"]["member_count"] == 15000
    # Internal "_admins" key must be stripped from public envelope.
    assert "_admins" not in body["result"]


async def test_getchat_returns_400_for_unknown(stub_client):
    client, _fixtures, _state = stub_client
    resp = await client.get(f"{TOKEN_PATH}/getChat", params={"chat_id": "@nonexistent"})
    assert resp.status == 400
    body = await resp.json()
    assert body["ok"] is False
    assert body["error_code"] == 400
    assert "chat not found" in body["description"]


async def test_getchatadministrators_includes_trustchannelbot_for_verified(stub_client):
    client, _fixtures, _state = stub_client
    resp = await client.get(
        f"{TOKEN_PATH}/getChatAdministrators", params={"chat_id": "@verified_channel"}
    )
    body = await resp.json()
    assert body["ok"] is True
    usernames = {a["user"]["username"].lower() for a in body["result"]}
    assert "trustchannelbot" in usernames


async def test_getchatadministrators_omits_trustchannelbot_for_unverified(stub_client):
    client, _fixtures, _state = stub_client
    resp = await client.get(
        f"{TOKEN_PATH}/getChatAdministrators", params={"chat_id": "@not_verified_channel"}
    )
    body = await resp.json()
    usernames = {a["user"]["username"].lower() for a in body["result"]}
    assert "trustchannelbot" not in usernames


async def test_sendmessage_accepts_post_and_records_state(stub_client):
    client, _fixtures, state = stub_client
    payload = {"chat_id": 12345, "text": "hello world"}
    resp = await client.post(f"{TOKEN_PATH}/sendMessage", json=payload)
    assert resp.status == 200
    body = await resp.json()
    assert body["ok"] is True
    assert body["result"]["text"] == "hello world"
    assert len(state.sent_messages) == 1
    assert state.sent_messages[0]["chat_id"] == 12345


async def test_unknown_method_returns_safe_noop(stub_client):
    client, _fixtures, _state = stub_client
    resp = await client.get(f"{TOKEN_PATH}/setStickerSetTitle")
    assert resp.status == 200
    body = await resp.json()
    assert body == {"ok": True, "result": {}}


async def test_state_snapshot_endpoint(stub_client):
    client, _fixtures, _state = stub_client
    await client.get(f"{TOKEN_PATH}/getMe")
    await client.post(f"{TOKEN_PATH}/sendMessage", json={"chat_id": 1, "text": "x"})
    resp = await client.get("/__stub__/state")
    body = await resp.json()
    assert body["method_calls"]["getMe"] == 1
    assert body["method_calls"]["sendMessage"] == 1
    assert len(body["sent_messages"]) == 1


async def test_load_fixtures_from_disk(tmp_path: Path):
    fixture_data = {
        "bot": {"id": 999, "is_bot": True, "username": "loaded_bot"},
        "chats": {"@x": {"id": -100, "title": "X", "type": "channel", "member_count": 1}},
        "members": {},
    }
    path = tmp_path / "fx.json"
    path.write_text(json.dumps(fixture_data))
    fixtures = load_fixtures(path)
    assert fixtures.bot["username"] == "loaded_bot"
    assert fixtures.resolve_chat("@x") is not None


async def test_load_fixtures_missing_file_falls_back_to_default(tmp_path: Path):
    fixtures = load_fixtures(tmp_path / "does_not_exist.json")
    assert isinstance(fixtures, Fixtures)
    assert fixtures.bot["username"] == "rekharbor_test_bot"
