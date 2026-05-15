"""In-memory state store for multi-step stub scenarios.

Tracks side-effects produced by bots (sent messages, chat actions) so that
Playwright/pytest scenarios can assert against observable outcomes without
hitting the real Telegram API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class StubState:
    """Mutable side-effect log shared across stub handlers.

    All collections are guarded by a single Lock — aiohttp's default
    cooperative scheduling means callers run on one event loop, but
    standalone Docker runs can still process concurrent requests, so
    snapshot reads must be consistent.
    """

    sent_messages: list[dict[str, Any]] = field(default_factory=list)
    chat_actions: list[dict[str, Any]] = field(default_factory=list)
    webhook_deletions: int = 0
    menu_button_sets: list[dict[str, Any]] = field(default_factory=list)
    method_calls: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_call(self, method: str) -> None:
        with self._lock:
            self.method_calls[method] = self.method_calls.get(method, 0) + 1

    def record_sent_message(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.sent_messages.append(payload)

    def record_chat_action(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.chat_actions.append(payload)

    def record_webhook_deletion(self) -> None:
        with self._lock:
            self.webhook_deletions += 1

    def record_menu_button(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.menu_button_sets.append(payload)

    def reset(self) -> None:
        """Wipe state — call between independent test scenarios."""
        with self._lock:
            self.sent_messages.clear()
            self.chat_actions.clear()
            self.webhook_deletions = 0
            self.menu_button_sets.clear()
            self.method_calls.clear()

    def snapshot(self) -> dict[str, Any]:
        """Return frozen copy of recorded state (safe to JSON-serialize)."""
        with self._lock:
            return {
                "sent_messages": list(self.sent_messages),
                "chat_actions": list(self.chat_actions),
                "webhook_deletions": self.webhook_deletions,
                "menu_button_sets": list(self.menu_button_sets),
                "method_calls": dict(self.method_calls),
            }
