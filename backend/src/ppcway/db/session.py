from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ppcway.config import load_settings

#: The setting every row-level security policy reads. Must match the name in
#: `migrations/versions/20261030_tenant_isolation.py`; a typo here would not
#: fail, it would quietly scope every statement to nothing.
ORG_SETTING = "app.current_org_id"


@lru_cache(maxsize=1)
def engine() -> Engine:
    settings = load_settings()
    if settings.is_sqlite:
        path = settings.database_url.removeprefix("sqlite:///")
        if path and not path.startswith(":memory:"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # FastAPI runs handlers and background tasks on worker threads.
        return create_engine(
            settings.database_url, connect_args={"check_same_thread": False}, future=True
        )
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=engine(), expire_on_commit=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed however the request ends."""
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def org_scope(session: Session, organization_id: UUID) -> Iterator[Session]:
    """Scope every statement in the block to one business, in the database.

    Fix F1. Blueprint §4.6 calls row-level security defence in depth: inside
    this block a missing ``WHERE organization_id = ...`` returns nothing rather
    than another business's data. Unset means NULL means no rows -- fail
    closed -- so a statement that escapes the scope is not a leak either.

    Setting the setting alone would do nothing. The services connect as the
    database owner, and a policy never binds the owner, nor a superuser, even
    with FORCE ROW LEVEL SECURITY. So this also steps down into ``ppcway_app``:
    NOLOGIN, not the owner, granted only DML on the covered tables, and
    therefore the role the policies actually apply to. Every statement in the
    block is genuinely subject to them, not merely scoped by a setting an
    unconstrained role happens to respect.

    On SQLite -- which the test suite uses, and which has no row-level
    security -- this yields the session unchanged. That is a real limitation
    and not a shim: the isolation this provides can only be proven against
    Postgres, which is what ``tests/opt/test_tenant_isolation.py`` does.
    """
    if session.get_bind().dialect.name != "postgresql":
        yield session
        return
    session.execute(
        text(f"SELECT set_config('{ORG_SETTING}', :v, true)"), {"v": str(organization_id)}
    )
    # Transaction-local, like set_config's is_local above: both unwind on their
    # own however this transaction ends.
    session.execute(text("SET LOCAL ROLE ppcway_app"))
    try:
        yield session
    finally:
        # Belt and braces for the case where the block succeeded and the
        # session lives on. If the block raised -- a constraint violation, a
        # write the policy refused -- the transaction is already aborted, and
        # another statement against it would raise InFailedSqlTransaction and
        # replace the caller's real exception. Swallow that: the caller's
        # exception is the one worth seeing, and both of these are already
        # gone regardless. RESET ROLE is always allowed back to the login role.
        try:
            session.execute(text("RESET ROLE"))
            session.execute(text(f"SELECT set_config('{ORG_SETTING}', '', true)"))
        except SQLAlchemyError:
            pass
