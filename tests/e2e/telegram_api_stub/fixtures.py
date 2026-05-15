"""Canonical fixture data for the Telegram Bot API stub.

Fixtures describe the response payloads the stub should return — bot identity,
chats keyed by username or id, and per-(chat,user) membership records.

Default fixtures provide the minimum set required by BL-107 flows:
 - `@verified_channel` — 15k subscribers, Trustchannelbot is an admin → passes
   blogger-registry verification (ФЗ-303).
 - `@not_verified_channel` — 5k subscribers, no Trustchannelbot admin → fails
   verification (or below threshold, depending on test).
 - `@empty_channel` — chat-not-found scenario for negative paths.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Fixtures:
    """Container holding all stub fixture data.

    Lookup helpers normalize chat identifier shape — Telegram accepts both
    numeric `chat_id` (e.g. -1001234567890) and `@username` references, and
    the stub honors either.
    """

    bot: dict[str, Any] = field(default_factory=dict)
    chats: dict[str, dict[str, Any]] = field(default_factory=dict)
    members: dict[str, dict[str, Any]] = field(default_factory=dict)

    def resolve_chat(self, chat_ref: str | int | None) -> dict[str, Any] | None:
        """Return chat dict for either `@username`, plain `username`, or numeric id."""
        if chat_ref is None:
            return None
        if isinstance(chat_ref, int) or (
            isinstance(chat_ref, str) and chat_ref.lstrip("-").isdigit()
        ):
            chat_id = int(chat_ref)
            for chat in self.chats.values():
                if chat.get("id") == chat_id:
                    return chat
            return None
        normalized = chat_ref.lstrip("@")
        return self.chats.get(f"@{normalized}") or self.chats.get(normalized)

    def get_admins(self, chat: dict[str, Any]) -> list[dict[str, Any]]:
        """Return administrator list for a chat — empty if none configured."""
        admins = chat.get("_admins", [])
        result: list[dict[str, Any]] = []
        for admin_ref in admins:
            if isinstance(admin_ref, dict):
                result.append(admin_ref)
            else:
                result.append({
                    "status": "administrator",
                    "user": {
                        "id": hash(admin_ref) & 0x7FFFFFFF,
                        "is_bot": admin_ref.endswith("bot"),
                        "username": str(admin_ref).lstrip("@"),
                        "first_name": str(admin_ref).lstrip("@"),
                    },
                })
        return result

    def get_member(self, chat: dict[str, Any], user_id: int) -> dict[str, Any] | None:
        """Return membership record by chat_id + user_id, falling back to admins."""
        key = f"{chat.get('id')}:{user_id}"
        if key in self.members:
            return self.members[key]
        for admin in self.get_admins(chat):
            if admin.get("user", {}).get("id") == user_id:
                return admin
        return None


def default_fixtures() -> Fixtures:
    """Built-in fixture set covering BL-107 happy/sad paths.

    Used when STUB_FIXTURES_PATH is unset or when fixtures.json is missing.
    """
    bot_id = 7000000001
    trustchannelbot_id = 7000000002
    owner_id = 5000000001

    return Fixtures(
        bot={
            "id": bot_id,
            "is_bot": True,
            "first_name": "RekHarborTestBot",
            "username": "rekharbor_test_bot",
            "can_join_groups": True,
            "can_read_all_group_messages": False,
            "supports_inline_queries": False,
        },
        chats={
            "@verified_channel": {
                "id": -1001111111111,
                "title": "Verified 15k Channel",
                "type": "channel",
                "username": "verified_channel",
                "member_count": 15000,
                "_admins": [
                    {
                        "status": "administrator",
                        "user": {
                            "id": trustchannelbot_id,
                            "is_bot": True,
                            "username": "Trustchannelbot",
                            "first_name": "Trustchannelbot",
                        },
                    },
                    {
                        "status": "creator",
                        "user": {
                            "id": owner_id,
                            "is_bot": False,
                            "username": "channel_owner",
                            "first_name": "Owner",
                        },
                    },
                    {
                        "status": "administrator",
                        "user": {
                            "id": bot_id,
                            "is_bot": True,
                            "username": "rekharbor_test_bot",
                            "first_name": "RekHarborTestBot",
                        },
                    },
                ],
            },
            "@not_verified_channel": {
                "id": -1002222222222,
                "title": "Not Verified 5k Channel",
                "type": "channel",
                "username": "not_verified_channel",
                "member_count": 5000,
                "_admins": [
                    {
                        "status": "creator",
                        "user": {
                            "id": owner_id,
                            "is_bot": False,
                            "username": "channel_owner",
                            "first_name": "Owner",
                        },
                    },
                    {
                        "status": "administrator",
                        "user": {
                            "id": bot_id,
                            "is_bot": True,
                            "username": "rekharbor_test_bot",
                            "first_name": "RekHarborTestBot",
                        },
                    },
                ],
            },
        },
        members={},
    )


def load_fixtures(path: Path | str) -> Fixtures:
    """Load fixtures from a JSON file at `path`.

    Falls back to `default_fixtures()` if the path is missing or malformed —
    surfacing the error to stdout but keeping the stub usable in a smoke test.
    """
    p = Path(path)
    if not p.exists():
        return default_fixtures()
    try:
        raw = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return default_fixtures()
    return Fixtures(
        bot=raw.get("bot", {}),
        chats=raw.get("chats", {}),
        members=raw.get("members", {}),
    )
