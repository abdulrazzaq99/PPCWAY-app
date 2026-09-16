from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ppcway.config import load_settings


@lru_cache(maxsize=1)
def engine() -> Engine:
    settings = load_settings()
    if settings.is_sqlite:
        path = settings.database_url.removeprefix("sqlite:///")
        if path and not path.startswith(":memory:"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # FastAPI runs handlers and background tasks on worker threads.
        return create_engine(settings.database_url, connect_args={"check_same_thread": False}, future=True)
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
