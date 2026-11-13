"""Signing in, or up, with six digits sent by email.

The code is a way into somebody's account, so most of these tests are about
what it cannot do: work twice, work late, survive five wrong guesses, outlive
the code sent after it, or be read back out of the database. The rest are
about the two ways it is used: an address PPCWay knows signs in to the account
it already has, and an address it does not know becomes a new account.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.api import app as app_module
from ppcway.api.app import create_app
from ppcway.auth.accounts import register
from ppcway.auth.codes import (
    COOLDOWN,
    GOOD_FOR,
    MOST_PER_HOUR,
    MOST_TRIES,
    Answer,
    check_code,
    post_code,
    sign_in_by_code,
)
from ppcway.auth.google import GoogleIdentity
from ppcway.auth.models import SignInCode, UserAccount
from ppcway.auth.sessions import sign_in
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.mail.send import Letter, NotSent, Post

DANA = "dana@alphaplumbing.ca"


@pytest.fixture
def factory() -> Iterator[sessionmaker[DbSession]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def _wrong(code: str) -> str:
    """A six-digit code that is certainly not this one."""
    return f"{(int(code) + 1) % 10**6:06d}"


def test_a_new_address_becomes_an_account_only_when_the_code_comes_back(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        posted = post_code(session, " Dana@AlphaPlumbing.ca ")
        assert posted.sent and re.fullmatch(r"\d{6}", posted.code)
        # Asking for a code makes no account: anybody can type any address.
        assert session.scalar(sa.select(sa.func.count()).select_from(UserAccount)) == 0

        answer, account = sign_in_by_code(session, DANA, posted.code, name="Dana Reid")

    assert answer is Answer.RIGHT
    assert account is not None
    assert account.email == DANA
    assert account.name == "Dana Reid"
    assert account.email_verified_at is not None
    assert account.password_hash == ""


def test_the_code_is_never_stored_as_itself(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        posted = post_code(session, DANA)
        row = session.scalars(sa.select(SignInCode)).one()
    assert posted.code not in row.code_hash
    assert row.code_hash.startswith("$argon2")


def test_a_known_address_signs_in_to_the_account_it_already_has(
    factory: sessionmaker[DbSession],
) -> None:
    """Google first, code later: one person, one account."""
    with factory() as session:
        first, _ = sign_in(
            session,
            GoogleIdentity(
                sub="google-dana", email=DANA, name="Dana", picture="", email_verified=True
            ),
        )
        posted = post_code(session, DANA.upper())
        answer, account = sign_in_by_code(session, DANA.upper(), posted.code, name="Someone Else")
        count = session.scalar(sa.select(sa.func.count()).select_from(UserAccount))

    assert answer is Answer.RIGHT
    assert account is not None and account.id == first.id
    assert account.name == "Dana", "a sign-in does not rename anybody"
    assert count == 1


def test_a_password_account_can_also_use_a_code_and_keeps_its_password(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        made, _ = register(session, email=DANA, password="roofing-in-oakville", name="Dana")
        posted = post_code(session, DANA)
        answer, account = sign_in_by_code(session, DANA, posted.code)
    assert answer is Answer.RIGHT
    assert account is not None and account.id == made.id
    assert account.password_hash, "the password still works"
    assert account.email_verified_at is not None, "reading the code proves the address"


def test_a_code_works_once(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        posted = post_code(session, DANA)
        assert check_code(session, DANA, posted.code) is Answer.RIGHT
        assert check_code(session, DANA, posted.code) is Answer.SPENT


def test_a_code_stops_working_after_ten_minutes(factory: sessionmaker[DbSession]) -> None:
    sent = datetime.now(UTC)
    with factory() as session:
        posted = post_code(session, DANA, now=sent)
        late = sent + GOOD_FOR + timedelta(seconds=1)
        assert check_code(session, DANA, posted.code, now=late) is Answer.EXPIRED
        assert check_code(session, DANA, posted.code, now=sent + GOOD_FOR / 2) is Answer.RIGHT


def test_five_wrong_guesses_spend_the_code_even_for_the_right_one_after(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        posted = post_code(session, DANA)
        said = [check_code(session, DANA, _wrong(posted.code)) for _ in range(MOST_TRIES)]
        assert said == [Answer.WRONG] * (MOST_TRIES - 1) + [Answer.SPENT]
        assert check_code(session, DANA, posted.code) is Answer.SPENT


def test_a_newer_code_retires_the_one_before(factory: sessionmaker[DbSession]) -> None:
    first_at = datetime.now(UTC) - COOLDOWN - timedelta(seconds=5)
    with factory() as session:
        first = post_code(session, DANA, now=first_at)
        second = post_code(session, DANA)
        assert second.sent
        if first.code != second.code:
            assert check_code(session, DANA, first.code) is Answer.WRONG
        assert check_code(session, DANA, second.code) is Answer.RIGHT


def test_a_code_for_one_address_does_not_open_another(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        posted = post_code(session, DANA)
        assert check_code(session, "someone@else.ca", posted.code) is Answer.NONE


def test_spaces_and_dashes_in_what_is_typed_do_not_matter(
    factory: sessionmaker[DbSession],
) -> None:
    """The email shows the digits; people copy them however they copy them."""
    with factory() as session:
        posted = post_code(session, DANA)
        typed = f" {posted.code[:3]} - {posted.code[3:]} "
        assert check_code(session, DANA, typed) is Answer.RIGHT


def test_another_code_waits_a_minute(factory: sessionmaker[DbSession]) -> None:
    at = datetime.now(UTC)
    with factory() as session:
        assert post_code(session, DANA, now=at).sent
        soon = post_code(session, DANA, now=at + timedelta(seconds=20))
        assert not soon.sent and 39 <= soon.wait_seconds <= 41
        assert not soon.for_the_hour
        assert post_code(session, DANA, now=at + COOLDOWN).sent


def test_no_more_than_five_codes_an_hour(factory: sessionmaker[DbSession]) -> None:
    """So the button cannot be used to fill somebody's inbox."""
    at = datetime.now(UTC)
    with factory() as session:
        for n in range(MOST_PER_HOUR):
            assert post_code(session, DANA, now=at + n * COOLDOWN).sent
        refused = post_code(session, DANA, now=at + MOST_PER_HOUR * COOLDOWN)
        assert not refused.sent and refused.for_the_hour
        # The first one leaving the hour frees a place.
        assert refused.wait_seconds == 3600 - MOST_PER_HOUR * 60
        assert post_code(session, DANA, now=at + timedelta(hours=1, seconds=1)).sent


# --- through the endpoints the screens call ----------------------------------

Letters = list[Letter]


@pytest.fixture
def world(
    monkeypatch: pytest.MonkeyPatch, factory: sessionmaker[DbSession]
) -> Iterator[tuple[FastAPI, Letters]]:
    letters: Letters = []

    def posted(post: Post, letter: Letter, **k: object) -> None:
        letters.append(letter)

    monkeypatch.setattr(app_module, "send", posted)
    app = create_app(Settings(environment="test", app_base_url="https://app.ppcway.com"))

    def one_session() -> Iterator[DbSession]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, letters


def _code_in(letter: Letter) -> str:
    found = re.search(r"\b(\d{6})\b", letter.subject)
    assert found, letter.subject
    return found.group(1)


def test_sign_up_by_code_end_to_end(world: tuple[FastAPI, Letters]) -> None:
    app, letters = world
    with TestClient(app) as client:
        asked = client.post("/v1/auth/code", json={"email": DANA})
        assert asked.status_code == 200, asked.text
        assert asked.json() == {"sent": True, "wait_seconds": 0, "minutes": 10}

        (letter,) = letters
        assert letter.to == DANA
        code = _code_in(letter)
        assert code in letter.text and code in letter.html
        assert "http" not in letter.text, "a code, not a link that works for anybody"

        signed = client.post(
            "/v1/auth/code/check", json={"email": DANA, "code": code, "name": "Dana Reid"}
        )
        assert signed.status_code == 200, signed.text
        token = signed.json()["token"]
        assert signed.json()["person"]["email"] == DANA

        me = client.get("/v1/auth/me", headers={"x-session-token": token})
        assert me.status_code == 200
        assert me.json()["name"] == "Dana Reid"

        again = client.post("/v1/auth/code/check", json={"email": DANA, "code": code})
        assert again.status_code == 400
        assert again.json()["detail"] == Answer.SPENT.said


def test_known_and_unknown_addresses_get_the_same_reply(
    world: tuple[FastAPI, Letters], factory: sessionmaker[DbSession]
) -> None:
    app, _ = world
    with factory() as session:
        register(session, email=DANA, password="roofing-in-oakville", name="Dana")
    with TestClient(app) as client:
        known = client.post("/v1/auth/code", json={"email": DANA})
        unknown = client.post("/v1/auth/code", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_asking_again_too_soon_says_how_long_to_wait(world: tuple[FastAPI, Letters]) -> None:
    app, letters = world
    with TestClient(app) as client:
        client.post("/v1/auth/code", json={"email": DANA})
        soon = client.post("/v1/auth/code", json={"email": DANA})
    assert soon.status_code == 200
    assert soon.json()["sent"] is False and soon.json()["wait_seconds"] > 0
    assert len(letters) == 1


def test_a_wrong_code_says_so_and_signs_nobody_in(world: tuple[FastAPI, Letters]) -> None:
    app, letters = world
    with TestClient(app) as client:
        client.post("/v1/auth/code", json={"email": DANA})
        wrong = client.post(
            "/v1/auth/code/check", json={"email": DANA, "code": _wrong(_code_in(letters[0]))}
        )
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == Answer.WRONG.said
    assert "token" not in wrong.json()


def test_when_the_email_cannot_go_the_page_is_told(
    monkeypatch: pytest.MonkeyPatch, world: tuple[FastAPI, Letters]
) -> None:
    app, _ = world

    def refused(post: Post, letter: Letter, **k: object) -> None:
        raise NotSent("email is not set up")

    monkeypatch.setattr(app_module, "send", refused)
    with TestClient(app) as client:
        said = client.post("/v1/auth/code", json={"email": DANA})
    assert said.status_code == 502
    assert said.json()["detail"] == "We could not send that email just now."


# --- on Postgres, where guesses can arrive at once ---------------------------


def test_guesses_at_once_cannot_share_out_more_than_five_tries(pg_engine: sa.Engine) -> None:
    """Eight wrong guesses together still spend the code after five.

    Without the row taken for update, guesses that read the count at the same
    moment each wrote back the same count plus one, and a code meant to take
    five guesses took as many as could be fired at once.
    """
    from concurrent.futures import ThreadPoolExecutor

    pg = sessionmaker(bind=pg_engine, expire_on_commit=False, future=True)
    try:
        with pg() as session:
            posted = post_code(session, DANA)

        def guess(_: int) -> Answer:
            with pg() as session:
                return check_code(session, DANA, _wrong(posted.code))

        with ThreadPoolExecutor(max_workers=8) as pool:
            said = list(pool.map(guess, range(8)))

        assert said.count(Answer.WRONG) == MOST_TRIES - 1
        assert said.count(Answer.SPENT) == 8 - (MOST_TRIES - 1)
        with pg() as session:
            row = session.scalars(sa.select(SignInCode).where(SignInCode.email == DANA)).one()
            assert row.attempts == MOST_TRIES
            assert check_code(session, DANA, posted.code) is Answer.SPENT
            # And the whole sign-up works on the real migrated schema.
            later_at = datetime.now(UTC) + COOLDOWN
            later = post_code(session, DANA, now=later_at)
            answer, account = sign_in_by_code(session, DANA, later.code, now=later_at)
            assert answer is Answer.RIGHT and account is not None
    finally:
        # The Postgres database is shared by the whole run; leave it as found.
        with pg() as session:
            session.execute(sa.delete(SignInCode).where(SignInCode.email == DANA))
            session.execute(sa.delete(UserAccount).where(UserAccount.email == DANA))
            session.commit()
