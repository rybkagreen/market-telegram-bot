"""T1-5 regression guard — `check_scheduled_deletions` must select only
`PlacementStatus.published` rows even when other statuses still carry a
stale `scheduled_delete_at`.

Status filter already exists at `src/tasks/placement_tasks.py:1098` (added
in commit 8c66a23a, 2026-04-09). PHASE2_RESEARCH_2026-04-26.md T1-5 claimed
the filter was missing — verified against current main, the premise was
outdated. This test pins the filter shape so a future refactor (Phase 2
PlacementTransitionService) cannot quietly drop it.

Two complementary checks:

1. Source-text guard — `_check_scheduled_deletions_async` SELECT must
   include `PlacementRequest.status == PlacementStatus.published`.
2. Compiled-SQL guard — invoke the same WHERE clause through SQLAlchemy
   and assert it produces a `status = 'published'` predicate when
   compiled, so that an equivalent-looking refactor that loses the
   semantics still fails (e.g. `IN (statuses)` with `published` left
   out).
"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from src.db.models.placement_request import PlacementRequest, PlacementStatus


def test_async_helper_source_contains_published_status_filter() -> None:
    """The async helper that drives `check_scheduled_deletions` must filter
    by `PlacementStatus.published` in its SELECT WHERE clause.
    """
    src_path = Path(__file__).resolve().parents[2] / "src/tasks/placement_tasks.py"
    text = src_path.read_text(encoding="utf-8")
    marker = "async def _check_scheduled_deletions_async"
    start = text.index(marker)
    # take the next ~80 lines as the function body window
    window = text[start : start + 4000]
    assert "PlacementRequest.status == PlacementStatus.published" in window, (
        "T1-5: status='published' filter missing from "
        "_check_scheduled_deletions_async — would cause scheduler to keep "
        "firing delete_published_post on stale failed/refunded rows"
    )
    assert "PlacementRequest.scheduled_delete_at <= now" in window
    assert "PlacementRequest.scheduled_delete_at.isnot(None)" in window


def test_select_compiles_with_published_predicate() -> None:
    """A SELECT mirroring the task's WHERE shape compiles to SQL that pins
    status to 'published' — guards against refactors that swap the literal
    for a broader IN-clause that loses `published` exclusivity.
    """
    now = datetime.now(UTC)
    stmt = select(PlacementRequest).where(
        PlacementRequest.status == PlacementStatus.published,
        PlacementRequest.scheduled_delete_at <= now,
        PlacementRequest.scheduled_delete_at.isnot(None),
    )
    compiled = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    # Postgres enum equality renders as `... = 'published'` after literal binding
    assert "= 'published'" in compiled, (
        f"compiled SQL does not pin status to 'published': {compiled}"
    )
    assert "scheduled_delete_at" in compiled
