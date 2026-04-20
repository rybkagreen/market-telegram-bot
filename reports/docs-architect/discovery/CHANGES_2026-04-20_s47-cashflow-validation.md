# CHANGES — S-47 pre-merge — cashflow query validation

**Sprint:** S-47 (UI redesign DS v2)
**Scope:** Backend hotfix surfaced during Phase 8 pre-merge UI review.
The "Финансовая активность" widget (`PerformanceChart`) on `/cabinet`
displayed «Ошибка загрузки данных» on every load.

## Root cause

`GET /api/analytics/cashflow?days=30` consistently returned 422
Unprocessable Content with the following Pydantic error:

```json
{
  "type": "literal_error",
  "loc": ["query", "days"],
  "msg": "Input should be 7, 30 or 90",
  "input": "30",
  "ctx": {"expected": "7, 30 or 90"}
}
```

The handler declared the query param as
`Annotated[Literal[7, 30, 90], Query(...)]`. Pydantic 2 in strict mode
does **not** coerce the raw query-string `"30"` to the integer `30`
for `Literal[int, ...]` types — FastAPI's usual string→int coercion
runs only for plain `int` or `IntEnum`, not for integer Literals.

Consequence: every allowed value (`7`, `30`, `90`) was rejected because
the query-string never reached an integer form. The widget could never
render real data.

This defect predates the S-47 sprint (the endpoint was introduced in
commit `0527d02 feat(api): add 4 Cabinet-widget endpoints for DS v2
redesign`), but only surfaced during Phase 8 because the Cabinet widget
is the first consumer that actually hits this endpoint in a real
browser session.

## Fix

Replaced `Literal[7, 30, 90]` with an `IntEnum`. FastAPI coerces query
strings into `IntEnum` members natively — this is the recommended
pattern for enum-like integer query parameters and also produces a
nicer OpenAPI schema with a proper `enum` declaration.

```python
class CashflowPeriod(IntEnum):
    SEVEN_DAYS = 7
    THIRTY_DAYS = 30
    NINETY_DAYS = 90


@router.get("/cashflow")
async def get_cashflow(
    current_user: CurrentUser,
    days: Annotated[
        CashflowPeriod, Query(description="Период: 7/30/90 дней")
    ] = CashflowPeriod.THIRTY_DAYS,
) -> CashflowResponse:
```

Because `IntEnum` is a subclass of `int`, the body of `get_cashflow`
(`timedelta(days=days)`, `range(days)`, `CashflowResponse(period_days=
days, ...)`) did not require any further changes.

## Files

- `src/api/routers/analytics.py` — added `CashflowPeriod(IntEnum)`;
  changed the `days` parameter type from
  `Annotated[Literal[7, 30, 90], Query(...)]` to
  `Annotated[CashflowPeriod, Query(...)]` with the matching default;
  removed the now-unused `Literal` import.

## Frontend

No change required. `web_portal/src/api/analytics.ts` still declares
`CashflowDays = 7 | 30 | 90` and sends `?days=7|30|90` over the wire;
the contract is identical. The widget in
`src/screens/common/cabinet/PerformanceChart.tsx` simply starts
resolving successfully instead of falling into the error branch.

## Quality gates

- `poetry run ruff check src/api/routers/analytics.py` → All checks passed!
- `poetry run mypy src/api/routers/analytics.py` → 0 new errors on this
  file (the pre-existing 529-error mypy backlog is unchanged).
- Hot-reloaded API (`uvicorn --reload`) → verified:
  - `GET /api/analytics/cashflow` (default) → 200
  - `GET /api/analytics/cashflow?days=7` → 200
  - `GET /api/analytics/cashflow?days=30` → 200
  - `GET /api/analytics/cashflow?days=90` → 200
  - `GET /api/analytics/cashflow?days=5` → 422 with
    `"Input should be 7, 30 or 90"` (correct rejection of invalid values).
- Round-trip via nginx / `https://portal.rekharbor.ru/api/analytics/
  cashflow?days=30` → 200.

## Not changed

- Response schema (`CashflowResponse`, `CashflowDataPoint`) — unchanged.
- SQL query, classification lists (`_INCOME_TX_TYPES`,
  `_EXPENSE_TX_TYPES`), zero-fill logic — unchanged.
- Other `Literal`-typed query parameters — `Grep` confirmed this was
  the only occurrence of `Literal[int, ...]` applied to a query param
  anywhere in `src/`.

🔍 Verified against: `97516bb` | 📅 Updated: 2026-04-20
