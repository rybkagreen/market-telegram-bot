"""aiohttp Application for the Telegram Bot API stub.

Route pattern matches the Telegram Bot API surface: `/bot{token}/{method}`.
Methods dispatch through `METHOD_HANDLERS` registry; unknown methods fall back
to a safe catch-all that returns `{"ok": true, "result": {}}`.

Bot API envelope shapes (per https://core.telegram.org/bots/api):
    Success: {"ok": true, "result": <method-specific payload>}
    Error:   {"ok": false, "error_code": <int>, "description": <str>}
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import web

from tests.e2e.telegram_api_stub.fixtures import Fixtures
from tests.e2e.telegram_api_stub.state import StubState


def ok(result: Any) -> web.Response:
    return web.json_response({"ok": True, "result": result})


def err(code: int, description: str) -> web.Response:
    return web.json_response(
        {"ok": False, "error_code": code, "description": description},
        status=code if code in (400, 401, 403, 404, 409, 429) else 200,
    )


async def _params(request: web.Request) -> dict[str, Any]:
    """Merge query string and JSON body into a single dict.

    Telegram allows either GET (query params) or POST (JSON or form-urlencoded);
    aiogram defaults to POST with JSON, python-telegram-bot uses POST as well.
    """
    params: dict[str, Any] = dict(request.query)
    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                body = await request.json()
                if isinstance(body, dict):
                    params.update(body)
            else:
                form = await request.post()
                params.update(dict(form))
        except Exception:
            # Body-less POST is valid for params-only Telegram calls.
            pass
    return params


# ─────────────────────────────────────────────────────────────────────────
# Per-method handlers
# ─────────────────────────────────────────────────────────────────────────


async def handle_get_me(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    return ok(fixtures.bot)


async def handle_get_chat(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    chat_ref = params.get("chat_id")
    chat = fixtures.resolve_chat(chat_ref)
    if chat is None:
        return err(400, f"Bad Request: chat not found ({chat_ref})")
    return ok({k: v for k, v in chat.items() if not k.startswith("_")})


async def handle_get_chat_administrators(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    chat = fixtures.resolve_chat(params.get("chat_id"))
    if chat is None:
        return err(400, "Bad Request: chat not found")
    return ok(fixtures.get_admins(chat))


async def handle_get_chat_member(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    chat = fixtures.resolve_chat(params.get("chat_id"))
    if chat is None:
        return err(400, "Bad Request: chat not found")
    user_id_raw = params.get("user_id")
    try:
        user_id = int(user_id_raw) if user_id_raw is not None else 0
    except (TypeError, ValueError):
        return err(400, "Bad Request: user_id is not a valid integer")
    member = fixtures.get_member(chat, user_id)
    if member is not None:
        return ok(member)
    return ok({
        "status": "left",
        "user": {
            "id": user_id,
            "is_bot": False,
            "first_name": "Unknown",
        },
    })


async def handle_send_message(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    state.record_sent_message(params)
    message_id = len(state.sent_messages)
    return ok({
        "message_id": message_id,
        "date": 1700000000,
        "chat": {"id": params.get("chat_id", 0), "type": "private"},
        "text": params.get("text", ""),
    })


async def handle_send_chat_action(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    state.record_chat_action(params)
    return ok(True)


async def handle_delete_webhook(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    state.record_webhook_deletion()
    return ok(True)


async def handle_set_chat_menu_button(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    state.record_menu_button(params)
    return ok(True)


async def handle_get_updates(
    request: web.Request, fixtures: Fixtures, state: StubState, params: dict[str, Any]
) -> web.Response:
    """Long-polling endpoint — return immediately with empty updates."""
    return ok([])


HandlerFn = Callable[[web.Request, Fixtures, StubState, dict[str, Any]], Awaitable[web.Response]]

METHOD_HANDLERS: dict[str, HandlerFn] = {
    "getMe": handle_get_me,
    "getChat": handle_get_chat,
    "getChatAdministrators": handle_get_chat_administrators,
    "getChatMember": handle_get_chat_member,
    "sendMessage": handle_send_message,
    "sendChatAction": handle_send_chat_action,
    "deleteWebhook": handle_delete_webhook,
    "setChatMenuButton": handle_set_chat_menu_button,
    "getUpdates": handle_get_updates,
}


# ─────────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────────


async def dispatch(request: web.Request) -> web.Response:
    method = request.match_info.get("method", "")
    app = request.app
    fixtures: Fixtures = app["fixtures"]
    state: StubState = app["state"]

    state.record_call(method)
    params = await _params(request)

    handler = METHOD_HANDLERS.get(method)
    if handler is None:
        # Safe noop default — any unknown method returns success with empty result.
        return ok({})
    return await handler(request, fixtures, state, params)


async def handle_state_snapshot(request: web.Request) -> web.Response:
    """Test-only introspection endpoint — returns recorded side-effects."""
    state: StubState = request.app["state"]
    return web.json_response(state.snapshot())


async def handle_state_reset(request: web.Request) -> web.Response:
    """Test-only endpoint to clear state between scenarios."""
    state: StubState = request.app["state"]
    state.reset()
    return web.json_response({"ok": True})


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "telegram-api-stub"})


def build_app(fixtures: Fixtures, state: StubState) -> web.Application:
    app = web.Application()
    app["fixtures"] = fixtures
    app["state"] = state

    app.router.add_get("/health", handle_health)
    app.router.add_get("/__stub__/state", handle_state_snapshot)
    app.router.add_post("/__stub__/reset", handle_state_reset)

    # Telegram-compatible routes.
    app.router.add_route("*", "/bot{token}/{method}", dispatch)
    app.router.add_route("*", "/file/bot{token}/{path:.*}", dispatch)
    return app
