"""The models and the migrations have to describe the same database.

They are two descriptions of one thing, written in different places at
different times, and nothing makes them agree. When they drift, the tests pass
against one schema and production runs on the other — which is the worst
possible place to find out.

This was not hypothetical: a unique constraint lived in a migration and not in
the model that it came from, so production enforced it and every test ran
without it.

What is compared is what must match — the tables, their columns, and whether a
column is actually unique. Not how uniqueness is spelled: a unique index and a
named unique constraint do the same job, and the codebase uses both.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

# Importing every model module is the point: the metadata is only as complete
# as what has been imported.
from ppcway.ads import mirror as _mirror  # noqa: F401
from ppcway.ads import models as _ads  # noqa: F401
from ppcway.audit import models as _audit  # noqa: F401
from ppcway.auth import models as _auth  # noqa: F401
from ppcway.db.base import Base
from ppcway.mail import models as _mail  # noqa: F401
from ppcway.model import log as _prompt_log  # noqa: F401
from ppcway.opt import models as _opt  # noqa: F401
from ppcway.org import models as _org  # noqa: F401
from ppcway.share import models as _share  # noqa: F401

#: Alembic's own bookkeeping, which no model describes.
ITS_OWN = {"alembic_version", "alembic_version_app"}


@pytest.fixture(scope="module")
def migrated(tmp_path_factory: pytest.TempPathFactory) -> Iterator[sa.Engine]:
    """A database built the way production is: by running every migration.

    The migrations read the address from the environment rather than from the
    config handed to them, so that is where it has to be put — and put back,
    because a leaked DATABASE_URL would point the rest of the suite somewhere
    it should not go.
    """
    where = tmp_path_factory.mktemp("schema") / "migrated.db"
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))

    before = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{where}"
    try:
        command.upgrade(config, "head")
    finally:
        if before is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = before
    yield sa.create_engine(f"sqlite:///{where}")


@pytest.fixture(scope="module")
def declared() -> sa.Engine:
    """A database built the way the tests build it: from the models."""
    engine = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool)
    Base.metadata.create_all(engine)
    return engine


def unique_columns(inspector: sa.Inspector, table: str) -> set[frozenset[str]]:
    """Which sets of columns are unique, however that was expressed."""
    found = {frozenset(u["column_names"]) for u in inspector.get_unique_constraints(table)}
    found |= {
        frozenset(i["column_names"])  # type: ignore[arg-type]
        for i in inspector.get_indexes(table)
        if i.get("unique") and i.get("column_names")
    }
    return found


def test_the_same_tables_exist_on_both_sides(declared: sa.Engine, migrated: sa.Engine) -> None:
    mine = set(sa.inspect(declared).get_table_names())
    theirs = set(sa.inspect(migrated).get_table_names()) - ITS_OWN
    assert mine == theirs, (
        f"only in the models: {sorted(mine - theirs)}; "
        f"only in the migrations: {sorted(theirs - mine)}"
    )


def test_every_table_has_the_same_columns(declared: sa.Engine, migrated: sa.Engine) -> None:
    mine, theirs = sa.inspect(declared), sa.inspect(migrated)
    wrong: list[str] = []
    for table in sorted(set(mine.get_table_names()) - ITS_OWN):
        a = {c["name"] for c in mine.get_columns(table)}
        b = {c["name"] for c in theirs.get_columns(table)}
        if a != b:
            wrong.append(
                f"{table}: only in models {sorted(a - b)}, only in migrations {sorted(b - a)}"
            )
    assert not wrong, "\n".join(wrong)


def test_the_same_things_are_unique(declared: sa.Engine, migrated: sa.Engine) -> None:
    """The bug this file was written for."""
    mine, theirs = sa.inspect(declared), sa.inspect(migrated)
    wrong: list[str] = []
    for table in sorted(set(mine.get_table_names()) - ITS_OWN):
        a = unique_columns(mine, table)
        b = unique_columns(theirs, table)
        if a != b:
            wrong.append(
                f"{table}: unique in models {sorted(map(sorted, a))}, "
                f"unique in migrations {sorted(map(sorted, b))}"
            )
    assert not wrong, "\n".join(wrong)
