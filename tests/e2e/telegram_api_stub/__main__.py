"""Standalone entry point: `python -m tests.e2e.telegram_api_stub`.

Reads PORT (default 8081) and STUB_FIXTURES_PATH (optional) from env.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from aiohttp import web

from tests.e2e.telegram_api_stub.app import build_app
from tests.e2e.telegram_api_stub.fixtures import default_fixtures, load_fixtures
from tests.e2e.telegram_api_stub.state import StubState


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    port = int(os.getenv("STUB_PORT", "8081"))
    host = os.getenv("STUB_HOST", "0.0.0.0")  # noqa: S104 — test stub, intentionally listens on all
    fixtures_path = os.getenv("STUB_FIXTURES_PATH")

    fixtures = load_fixtures(Path(fixtures_path)) if fixtures_path else default_fixtures()
    state = StubState()
    app = build_app(fixtures, state)

    logging.getLogger(__name__).info(
        "Telegram API stub starting on %s:%s (fixtures=%s)", host, port, fixtures_path or "default"
    )
    web.run_app(app, host=host, port=port, print=None)


if __name__ == "__main__":
    main()
