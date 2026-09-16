"""Alembic for this repository's own tables.

The Neon database also carries the proof of concept's schema under the default
`alembic_version` table. This chain keeps its own version table so the two never
fight over a single head, and it only ever adds tables beside the old ones.
"""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

import ppcway.audit.models  # noqa: F401 - registers the tables on Base.metadata
from ppcway.config import load_settings
from ppcway.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
_settings = load_settings()
if _settings.is_sqlite:
    # A first run has no data/ directory yet; SQLite will not create it.
    _path = _settings.database_url.removeprefix("sqlite:///")
    if _path and not _path.startswith(":memory:"):
        Path(_path).parent.mkdir(parents=True, exist_ok=True)
config.set_main_option("sqlalchemy.url", _settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata
VERSION_TABLE = "alembic_version_app"


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
