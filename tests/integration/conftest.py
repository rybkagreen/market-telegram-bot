"""Integration-test fixtures: spin up a real Postgres via testcontainers and
create the full schema once per session. Each test runs inside a transaction
that is rolled back to isolate state.

Overrides `test_engine` and `db_session` from the parent conftest.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Importing the models package populates Base.metadata with every table.
import src.db.models  # noqa: F401
from src.db.base import Base


def _async_url(raw: str) -> str:
    """Coerce a testcontainer URL into asyncpg form."""
    if "+asyncpg" in raw:
        return raw
    return raw.replace("postgresql://", "postgresql+asyncpg://").replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )


def _sync_url(raw: str) -> str:
    """Coerce a testcontainer URL into a sync psycopg2 form for DDL."""
    return raw.replace("+asyncpg", "").replace("postgresql+psycopg2", "postgresql")


_schema_initialized: dict[str, str] = {}


def _init_schema_once(raw: str) -> str:
    """Create the schema once per process (module-level cache), returns async URL."""
    if raw in _schema_initialized:
        return _schema_initialized[raw]
    # Known quirk: some models (e.g. Act) declare the same index both via
    # `Column(..., index=True)` and an explicit `Index(...)` in
    # __table_args__, so MetaData.create_all raises DuplicateTable on the
    # second index. Dedupe by name before create_all so this is a no-op for
    # every other table.
    seen: set[str] = set()
    for table in Base.metadata.tables.values():
        for ix in list(table.indexes):
            if ix.name is not None and ix.name in seen:
                table.indexes.discard(ix)
            elif ix.name is not None:
                seen.add(ix.name)

    sync_engine = sa.create_engine(_sync_url(raw), future=True)
    try:
        with sync_engine.begin() as conn:
            conn.execute(sa.text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(sa.text("CREATE SCHEMA public"))
        with sync_engine.begin() as conn:
            Base.metadata.create_all(conn)
    finally:
        sync_engine.dispose()
    url = _async_url(raw)
    _schema_initialized[raw] = url
    return url


@pytest.fixture(scope="session")
def _schema_ready(postgres_container: Any) -> str:
    """Session fixture that triggers one-time schema initialization."""
    return _init_schema_once(postgres_container.get_connection_url())


@pytest_asyncio.fixture(scope="function")
async def test_engine(_schema_ready: str) -> AsyncGenerator[Any]:
    """Function-scoped async engine against the pre-seeded schema.

    NullPool keeps each call on its own connection so per-test transaction
    rollback cannot leak into the next test via a pooled connection.
    """
    engine = create_async_engine(_schema_ready, echo=False, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: Any) -> AsyncGenerator[AsyncSession]:
    """Session wrapped in a transaction that is always rolled back.

    This gives every test a clean slate without needing to re-create the
    schema between tests.
    """
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        try:
            async_session = async_sessionmaker(
                bind=connection, expire_on_commit=False, class_=AsyncSession
            )
            async with async_session() as session:
                yield session
                await session.close()
        finally:
            await trans.rollback()
