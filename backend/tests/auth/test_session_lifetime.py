"""Staying signed in, and stopping being signed in.

A session that expires a fixed thirty days after sign-in signs out somebody who
has used it every day of those thirty days. Nobody reports that as a bug; they
just resent it. Using a session renews it; leaving it alone does not.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.auth.google import GoogleIdentity, hash_session_token
from ppcway.auth.models import Session
from ppcway.auth.sessions import sign_in, sign_out, sign_out_everywhere, whoever_holds
from ppcway.db.base import Base

DANA = GoogleIdentity(
    sub="google-dana",
    email="dana@alphaplumbing.ca",
    email_verified=True,
    name="Dana",
    picture="",
)


@pytest.fixture
def factory() -> Iterator[sessionmaker[DbSession]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def held(session: DbSession, token: str) -> Session:
    return session.scalars(
        sa.select(Session).where(Session.token_hash == hash_session_token(token))
    ).one()


def test_using_a_session_rolls_its_expiry_forward(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        _, token = sign_in(session, DANA)
        # Yesterday's session, three days from running out.
        row = held(session, token)
        row.last_used_at = datetime.now(UTC) - timedelta(days=1)
        row.expires_at = datetime.now(UTC) + timedelta(days=3)
        session.commit()

        assert whoever_holds(session, token) is not None
        after = held(session, token)
        assert after.expires_at > datetime.now(UTC) + timedelta(days=29), "not renewed"


def test_a_session_in_constant_use_is_not_written_on_every_page(
    factory: sessionmaker[DbSession],
) -> None:
    """Every screen asks who is signed in. A write per page view costs more than
    it is worth, so the renewal happens at most twice a day."""
    with factory() as session:
        _, token = sign_in(session, DANA)
        whoever_holds(session, token)
        first = held(session, token).expires_at

        whoever_holds(session, token)
        assert held(session, token).expires_at == first, "renewed twice in a moment"


def test_a_session_left_alone_stops_working(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        _, token = sign_in(session, DANA)
        row = held(session, token)
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()
        assert whoever_holds(session, token) is None


def test_signing_out_here_leaves_the_other_browser_alone(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        _, laptop = sign_in(session, DANA)
        _, phone = sign_in(session, DANA)
        sign_out(session, laptop)
        assert whoever_holds(session, laptop) is None
        assert whoever_holds(session, phone) is not None


def test_signing_out_everywhere_ends_every_session(factory: sessionmaker[DbSession]) -> None:
    """What somebody wants when they have lost a laptop."""
    with factory() as session:
        person, laptop = sign_in(session, DANA)
        _, phone = sign_in(session, DANA)
        _, tablet = sign_in(session, DANA)

        assert sign_out_everywhere(session, person) == 3
        for token in (laptop, phone, tablet):
            assert whoever_holds(session, token) is None


def test_signing_out_everywhere_counts_only_the_live_ones(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        person, laptop = sign_in(session, DANA)
        sign_in(session, DANA)  # the phone, still signed in
        sign_out(session, laptop)
        assert sign_out_everywhere(session, person) == 1
