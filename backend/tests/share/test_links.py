"""A link that needs no login: what opens it, and what must not.

This is the only part of PPCway that answers without anybody signing in, so the
tests here are the boundary itself.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.auth.models import UserAccount  # noqa: F401
from ppcway.db.base import Base
from ppcway.org.models import Organization  # noqa: F401
from ppcway.share.links import fingerprint, make_link, open_link, revoke
from ppcway.share.models import ShareLink

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def test_the_token_is_handed_over_once_and_never_stored(db: DbSession) -> None:
    link, token = make_link(db, kind="report", subject="123", now=NOW)

    assert token
    assert link.token_hash == fingerprint(token)
    # Nothing in the row is the token itself, so a copy of this table is not a
    # set of working links.
    stored = db.scalars(sa.select(ShareLink)).one()
    assert token not in str(stored.__dict__.values())


def test_a_link_opens_and_counts_every_opening(db: DbSession) -> None:
    link, token = make_link(db, kind="report", subject="123", now=NOW)

    first = open_link(db, token, kind="report", now=NOW + timedelta(hours=1))
    second = open_link(db, token, kind="report", now=NOW + timedelta(hours=2))

    assert first is not None and first.id == link.id
    assert second is not None
    assert second.opened == 2
    # SQLite forgets the time zone on the way back out; Postgres does not.
    assert second.last_opened_at is not None
    assert second.last_opened_at.replace(tzinfo=UTC) == NOW + timedelta(hours=2)


def test_an_expired_link_does_not_open(db: DbSession) -> None:
    _, token = make_link(db, kind="report", subject="123", days=14, now=NOW)

    assert open_link(db, token, kind="report", now=NOW + timedelta(days=13)) is not None
    assert open_link(db, token, kind="report", now=NOW + timedelta(days=15)) is None


def test_a_revoked_link_does_not_open(db: DbSession) -> None:
    link, token = make_link(db, kind="report", subject="123", now=NOW)
    revoke(db, link, now=NOW)

    assert open_link(db, token, kind="report", now=NOW + timedelta(hours=1)) is None
    # The record that it existed stays.
    assert db.scalars(sa.select(ShareLink)).one().revoked_at is not None


def test_a_token_for_one_kind_cannot_open_the_other(db: DbSession) -> None:
    _, token = make_link(db, kind="report", subject="123", now=NOW)

    assert open_link(db, token, kind="fixes", now=NOW) is None


def test_a_token_nobody_issued_opens_nothing(db: DbSession) -> None:
    make_link(db, kind="report", subject="123", now=NOW)

    assert open_link(db, "not-a-token", kind="report", now=NOW) is None


def test_two_links_never_share_a_token(db: DbSession) -> None:
    _, first = make_link(db, kind="report", subject="123", now=NOW)
    _, second = make_link(db, kind="report", subject="123", now=NOW)

    assert first != second
