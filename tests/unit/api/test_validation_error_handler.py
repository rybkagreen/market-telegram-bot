"""
Regression tests for `sanitized_validation_error_handler` — locks in
T1.2.4b B1 fix.

Pydantic 2 places `Decimal` instances inside `ValidationError.errors()` —
specifically in `ctx['ge'/'le'/'gt'/'lt']` for any Decimal-typed field with
a numeric constraint, and in `input` when the upstream raw value was Decimal.
Starlette's `JSONResponse.render` uses bare `json.dumps` without a Decimal
default callable, so passing raw `exc.errors()` as `content` raises
`TypeError`. The handler must wrap content via `jsonable_encoder` (matches
FastAPI's default `request_validation_exception_handler`).
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from src.api.middleware.log_sanitizer import sanitized_validation_error_handler


class _DecimalConstraintRequest(BaseModel):
    """Loudest trigger: Decimal field with Decimal-literal `ge` constraint.

    Pydantic stores `Decimal('100')` in `ctx['ge']` regardless of input type,
    so every numeric-out-of-range payload exposes the bug if the handler
    forwards raw `exc.errors()` to `JSONResponse`.
    """

    price: Decimal = Field(..., ge=Decimal("100"))


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(
        RequestValidationError,
        sanitized_validation_error_handler,  # type: ignore[arg-type]
    )

    @app.post("/echo")
    async def _echo(payload: _DecimalConstraintRequest) -> dict[str, str]:
        return {"price": str(payload.price)}

    return app


@pytest.mark.parametrize(
    "payload",
    [
        {"price": 50},
        {"price": "50"},
        {"price": "50.5"},
        {"price": 50.5},
    ],
)
def test_decimal_ge_constraint_returns_422_not_500(payload: dict) -> None:
    """Numeric-out-of-range on a Decimal field must serialize to 422.

    Before T1.2.4b B1 fix: handler raised TypeError on `json.dumps(exc.errors())`,
    Starlette returned 500. After fix: `jsonable_encoder` converts Decimal
    occurrences in `ctx`/`input` to int/float before `JSONResponse.render`.
    """
    client = TestClient(_make_app(), raise_server_exceptions=True)
    response = client.post("/echo", json=payload)

    assert response.status_code == 422, (
        f"Expected 422 for {payload!r}, got {response.status_code}: {response.text}"
    )

    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    assert len(body["detail"]) == 1

    error = body["detail"][0]
    assert error["type"] == "greater_than_equal"
    assert error["loc"] == ["body", "price"]

    ctx_ge = error["ctx"]["ge"]
    assert not isinstance(ctx_ge, str) or ctx_ge.replace(".", "").replace("-", "").isdigit(), (
        f"ctx.ge must be JSON number-compatible, got {ctx_ge!r} of {type(ctx_ge).__name__}"
    )
    assert isinstance(ctx_ge, (int, float)), (
        f"jsonable_encoder converts Decimal to int/float; got {type(ctx_ge).__name__}"
    )

    json.dumps(body)


def test_handler_does_not_crash_when_input_itself_is_decimal() -> None:
    """When upstream code passes a Decimal instance directly into a model,
    Pydantic preserves it in `errors()['input']`. The handler must serialise
    cleanly — the integration path triggers this when nested validators emit
    Decimal before outer validation runs.
    """
    pyd_errors = [
        {
            "type": "greater_than_equal",
            "loc": ("body", "price"),
            "msg": "Input should be greater than or equal to 100",
            "input": Decimal("50"),
            "ctx": {"ge": Decimal("100")},
            "url": "https://errors.pydantic.dev/2.12/v/greater_than_equal",
        }
    ]
    exc = RequestValidationError(errors=pyd_errors)

    import asyncio

    class _FakeRequest:
        method = "POST"

        class _URL:
            path = "/echo"

        url = _URL()

        async def json(self) -> dict:
            return {"price": Decimal("50")}

    response = asyncio.run(sanitized_validation_error_handler(_FakeRequest(), exc))  # type: ignore[arg-type]
    assert response.status_code == 422

    body = json.loads(response.body)
    assert body["detail"][0]["input"] == 50
    assert body["detail"][0]["ctx"]["ge"] == 100
