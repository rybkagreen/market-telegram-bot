"""
Alembic migrations configuration for sync operations (revision generation).
For actual migrations, use the async env.py.
"""

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from src.config.settings import settings
from src.db.base import Base
from src.db.models import *  # noqa: F401,F403,S2208

logger = logging.getLogger(__name__)


def _compare_type(
    ctx: object,
    inspected_column: object,
    metadata_column: object,
    inspected_type: object,
    metadata_type: object,
) -> bool | None:
    """Skip type-drift detection for ORM-level encrypted columns.

    EncryptedString / HashableEncryptedString are stored as plain TEXT/VARCHAR
    in PostgreSQL — the encryption is handled at the ORM layer, not at the DB
    type level.  Alembic would otherwise always report them as needing an ALTER.
    """
    try:
        from src.core.security.field_encryption import EncryptedString, HashableEncryptedString

        if isinstance(metadata_type, (EncryptedString, HashableEncryptedString)):
            return False  # no change needed
    except ImportError:
        pass
    return None  # fall through to default comparison


# Alembic Config object
config = context.config

# Override sqlalchemy.url with settings from .env
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=_compare_type,
        compare_server_default=True,
        compare_comment=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        settings.database_url_sync,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=_compare_type,
            compare_server_default=True,
            compare_comment=False,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
