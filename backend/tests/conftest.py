"""Shared fixtures, and the one thing the ordinary suite cannot prove.

Every other test in this project runs against in-memory SQLite, which is fast
and which the application supports. Two of the client's blocking fixes cannot
be proven there at all: SQLite has no row-level security and no triggers of the
shape F2 needs, and both live in migrations rather than in `Base.metadata`, so
`create_all` never sees them.

So the fixtures here build a throwaway Postgres database and run the real
migrations into it. That is slower, and it is the only way the claim "one
organisation cannot read another" means anything. It also tests something
nothing else did: that the migration chain applies cleanly to Postgres, which
is what production actually runs.

The database is created fresh, named uniquely, and dropped afterwards. It never
touches an existing one -- the owner's instance holds other projects' data, and
a test suite has no business near it.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine, make_url

#: Where to find a Postgres to borrow. The default is the local instance a
#: developer on macOS gets from Homebrew; CI sets the variable.
ADMIN_URL = os.environ.get("PPCWAY_TEST_POSTGRES", "postgresql+psycopg:///postgres")

WHY_SKIPPED = (
    "needs a Postgres to borrow: row-level security and the append-only triggers"
    " do not exist on SQLite. Set PPCWAY_TEST_POSTGRES to a superuser or"
    f" CREATEDB connection string (tried {ADMIN_URL})."
)


def _reachable() -> bool:
    try:
        engine = sa.create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        engine.dispose()
    except (sa.exc.SQLAlchemyError, OSError):
        # Narrow on purpose rather than bare: a driver or socket failure means
        # "no Postgres here, skip", while anything else is a bug in this file
        # and should not be quietly turned into a skipped test.
        return False
    return True


@pytest.fixture(scope="session")
def pg_engine() -> Iterator[Engine]:
    """A throwaway Postgres with the real migration chain applied."""
    if not _reachable():
        pytest.skip(WHY_SKIPPED)

    name = f"ppcway_test_{secrets.token_hex(6)}"
    admin = sa.create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))

    url = make_url(ADMIN_URL).set(database=name)
    try:
        _migrate(str(url))
        engine = sa.create_engine(url, future=True)
        try:
            yield engine
        finally:
            engine.dispose()
    finally:
        with admin.connect() as conn:
            # Anything still connected would make the drop fail, and a leaked
            # test database is worse than a noisy teardown.
            conn.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                    " WHERE datname = :n AND pid <> pg_backend_pid()"
                ),
                {"n": name},
            )
            conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


def _migrate(url: str) -> None:
    """Run `alembic upgrade head` against one database, in process."""
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    # env.py reads the application settings for its URL; this overrides it for
    # the duration, so a test run cannot touch the configured database.
    was = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(config, "head")
    finally:
        if was is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = was
