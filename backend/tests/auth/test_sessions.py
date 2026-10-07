"""Signing in, staying signed in, and signing out, against a database in memory."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.auth.google import GoogleIdentity, hash_session_token
from ppcway.auth.models import Session, UserAccount
from ppcway.auth.sessions import sign_in, sign_out, whoever_holds
from ppcway.db.base import Base


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def who(sub: str = "g-1", email: str = "owner@alphaplumbing.ca") -> GoogleIdentity:
    return GoogleIdentity(sub=sub, email=email, name="Dana", picture="", email_verified=True)


def test_the_first_sign_in_makes_the_account_and_the_second_finds_it(db: DbSession) -> None:
    account, token = sign_in(db, who())
    again, other = sign_in(db, who())
    assert again.id == account.id, "the same Google account is the same person"
    assert other != token, "every sign-in gets its own session"
    assert db.scalar(sa.select(sa.func.count()).select_from(UserAccount)) == 1


def test_a_changed_name_or_address_follows_google(db: DbSession) -> None:
    sign_in(db, who(email="old@alphaplumbing.ca"))
    account, _ = sign_in(db, GoogleIdentity("g-1", "new@alphaplumbing.ca", "Dana Smith", "p", True))
    assert account.email == "new@alphaplumbing.ca" and account.name == "Dana Smith"


def test_the_token_is_never_stored_only_its_hash(db: DbSession) -> None:
    _, token = sign_in(db, who())
    held = db.scalar(sa.select(Session))
    assert held is not None
    assert held.token_hash == hash_session_token(token)
    assert token not in held.token_hash


def test_a_cookie_finds_its_person_and_a_wrong_one_finds_nobody(db: DbSession) -> None:
    account, token = sign_in(db, who())
    assert whoever_holds(db, token) is not None
    assert whoever_holds(db, token).id == account.id  # type: ignore[union-attr]
    assert whoever_holds(db, "not-a-token") is None
    assert whoever_holds(db, None) is None


def test_signing_out_ends_that_session_and_leaves_the_others(db: DbSession) -> None:
    _, phone = sign_in(db, who())
    _, laptop = sign_in(db, who())
    sign_out(db, phone)
    assert whoever_holds(db, phone) is None, "the one signed out is finished"
    assert whoever_holds(db, laptop) is not None, "the other browser stays signed in"


def test_an_expired_session_is_nobody(db: DbSession) -> None:
    _, token = sign_in(db, who())
    held = db.scalar(sa.select(Session))
    assert held is not None
    held.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert whoever_holds(db, token) is None
