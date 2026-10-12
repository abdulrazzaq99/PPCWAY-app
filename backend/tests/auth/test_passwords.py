"""Signing up with an address and a password, and everything around it.

Two rules run through these tests. A stranger is never told whether an address
has an account, and a link in an email works once.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.auth.accounts import (
    AlreadyHere,
    by_email,
    finish_reset,
    fresh_verification,
    register,
    sign_in_with_password,
    start_reset,
    verify,
)
from ppcway.auth.google import GoogleIdentity, hash_session_token
from ppcway.auth.models import LinkToken, UserAccount
from ppcway.auth.passwords import WeakPassword, hash_password, password_matches
from ppcway.auth.sessions import sign_in
from ppcway.db.base import Base

GOOD = "roofing-in-oakville"


@pytest.fixture
def factory() -> Iterator[sessionmaker[DbSession]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def test_a_password_is_never_stored_as_it_was_typed() -> None:
    stored = hash_password(GOOD)
    assert GOOD not in stored
    assert stored.startswith("$argon2")
    assert password_matches(stored, GOOD)
    assert not password_matches(stored, GOOD + "!")


def test_a_short_password_is_refused_with_a_reason() -> None:
    with pytest.raises(WeakPassword) as refused:
        hash_password("short")
    assert "10 characters" in str(refused.value)


def test_signing_up_makes_an_unverified_account_and_a_link(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        account, secret = register(
            session, email="Dana@AlphaPlumbing.ca", password=GOOD, name="Dana Reid"
        )
        assert account.email == "dana@alphaplumbing.ca", "the address was not folded"
        assert account.email_verified_at is None
        assert secret, "no verification link was made"

        assert verify(session, secret) is not None
        session.refresh(account)
        assert account.email_verified_at is not None


def test_a_verification_link_works_once(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        _, secret = register(session, email="dana@x.ca", password=GOOD)
        assert verify(session, secret) is not None
        assert verify(session, secret) is None


def test_an_expired_link_is_no_use(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        _, secret = register(session, email="dana@x.ca", password=GOOD)
        held = session.scalars(
            sa.select(LinkToken).where(LinkToken.token_hash == hash_session_token(secret))
        ).one()
        held.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()
        assert verify(session, secret) is None


def test_asking_again_retires_the_first_link(factory: sessionmaker[DbSession]) -> None:
    """Otherwise a link in an old email keeps working after a new one is sent."""
    with factory() as session:
        account, first = register(session, email="dana@x.ca", password=GOOD)
        second = fresh_verification(session, account)
        assert verify(session, first) is None
        assert verify(session, second) is not None


def test_signing_in_needs_the_right_password(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        register(session, email="dana@x.ca", password=GOOD)
        assert sign_in_with_password(session, email="dana@x.ca", password=GOOD) is not None
        assert sign_in_with_password(session, email="dana@x.ca", password="wrong-one-here") is None
        assert sign_in_with_password(session, email="nobody@x.ca", password=GOOD) is None


def test_the_same_address_cannot_sign_up_twice(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        register(session, email="dana@x.ca", password=GOOD)
        with pytest.raises(AlreadyHere):
            register(session, email="DANA@x.ca", password=GOOD)


def test_somebody_who_came_through_google_can_add_a_password(
    factory: sessionmaker[DbSession],
) -> None:
    """Not a second account: the same one, with another way in."""
    with factory() as session:
        sign_in(
            session,
            GoogleIdentity(
                sub="google-dana",
                email="dana@x.ca",
                email_verified=True,
                name="Dana",
                picture="",
            ),
        )
        account, secret = register(session, email="dana@x.ca", password=GOOD)

        assert account.google_sub == "google-dana"
        assert secret == "", "Google already proved the address; no link needed"
        assert len(session.scalars(sa.select(UserAccount)).all()) == 1
        assert sign_in_with_password(session, email="dana@x.ca", password=GOOD) is not None


def test_a_reset_says_nothing_about_whether_the_account_exists(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        register(session, email="dana@x.ca", password=GOOD)
        assert start_reset(session, "dana@x.ca") is not None
        assert start_reset(session, "nobody@x.ca") is None, "the caller answers the same either way"


def test_a_reset_sets_the_password_and_proves_the_address(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        register(session, email="dana@x.ca", password=GOOD)
        found = start_reset(session, "dana@x.ca")
        assert found is not None
        _, secret = found

        account = finish_reset(session, token=secret, password="a-whole-new-one")
        assert account is not None
        assert account.email_verified_at is not None, "reading the inbox proves the address"
        assert sign_in_with_password(session, email="dana@x.ca", password="a-whole-new-one")
        assert sign_in_with_password(session, email="dana@x.ca", password=GOOD) is None


def test_a_reset_link_cannot_be_used_twice(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        register(session, email="dana@x.ca", password=GOOD)
        found = start_reset(session, "dana@x.ca")
        assert found is not None
        _, secret = found
        assert finish_reset(session, token=secret, password="a-whole-new-one") is not None
        assert finish_reset(session, token=secret, password="another-one-again") is None


def test_a_weak_password_is_refused_at_reset_too(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        register(session, email="dana@x.ca", password=GOOD)
        found = start_reset(session, "dana@x.ca")
        assert found is not None
        with pytest.raises(WeakPassword):
            finish_reset(session, token=found[1], password="short")


def test_finding_somebody_ignores_how_they_typed_their_address(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        register(session, email="dana@x.ca", password=GOOD)
        assert by_email(session, "  DANA@X.ca ") is not None
