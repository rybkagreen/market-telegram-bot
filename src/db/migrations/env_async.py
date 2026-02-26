"""
Alembic migrations configuration for async SQLAlchemy.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, async_engine_from_config

from src.config.settings import settings
from src.db.base import Base
from src.db.models import *  # noqa: F401, F403 - Import all models for Alembic

# Alembic Config object
config = context.config

# Override sqlalchemy.url with settings from .env
config.set_main_option("sqlalchemy.url", str(settings.database_url))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def run_async_migrations(connection: AsyncConnection) -> None:
        """Run migrations asynchronously."""

        def do_configure(conn: Connection) -> None:
            """Configure context."""
            context.configure(
                connection=conn,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                include_schemas=True,
            )

        await connection.run_sync(do_configure)

        with context.begin_transaction():
            context.run_migrations()

    async def main() -> None:
        """Main async function."""
        async with connectable.connect() as connection:
            await run_async_migrations(connection)
        await connectable.dispose()

    asyncio.run(main())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
