"""Opening the free audit to everybody while the rest stays on the latch.

The point of the launch is that a stranger can run an audit and get a real
report, and cannot get into anything else. The test that matters most here is
the last one: the audit still runs with no account at all.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ppcway.api import app as api_module
from ppcway.api.app import create_app
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.auth.opening import NOT_YET, may_come_in, open_to_everybody
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.org.models import Invitation, Organization

LIST = "dana@alphaplumbing.ca, @byte9.ca"


def test_nothing_named_means_open_to_everybody() -> None:
    assert open_to_everybody("") is True
    assert open_to_everybody("   ") is True
    assert may_come_in("anybody@example.com", open_to="") is True


def test_a_named_address_comes_in_and_a_stranger_does_not() -> None:
    assert may_come_in("dana@alphaplumbing.ca", open_to=LIST) is True
    assert may_come_in("DANA@AlphaPlumbing.ca ", open_to=LIST) is True
    assert may_come_in("stranger@example.com", open_to=LIST) is False


def test_a_whole_domain_can_be_let_in() -> None:
    """So a client's staff are not each named by hand."""
    assert may_come_in("anyone@byte9.ca", open_to=LIST) is True
    assert may_come_in("anyone@byte9.ca.evil.com", open_to=LIST) is False


def test_somebody_invited_from_inside_comes_in_unnamed() -> None:
    assert may_come_in("new.hire@example.com", open_to=LIST, invited=True) is True


@pytest.fixture
def latched(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    monkeypatch.setattr(
        google.id_token,  # type: ignore[attr-defined]
        "verify_oauth2_token",
        lambda credential, *a, **k: {
            "sub": "google-stranger",
            "email": "stranger@example.com",
            "email_verified": True,
            "name": "A Stranger",
        },
    )
    # The audit itself is somebody else's test; here it only has to be allowed.
    monkeypatch.setattr(api_module, "_run", lambda *a, **k: None)

    app = create_app(
        Settings(google_signin_client_id="test-client", open_to=LIST, environment="test")
    )

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory
    Base.metadata.drop_all(engine)


def test_a_stranger_cannot_make_an_account(latched: tuple[FastAPI, sessionmaker[Session]]) -> None:
    app, _ = latched
    with TestClient(app) as client:
        said = client.post(
            "/v1/auth/register",
            json={"email": "stranger@example.com", "password": "a-long-enough-one", "name": "No"},
        )
    assert said.status_code == 403
    assert said.json()["detail"] == NOT_YET


def test_a_stranger_cannot_sign_in_with_google(
    latched: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The quietest way in, and the one most likely to be forgotten."""
    app, _ = latched
    with TestClient(app) as client:
        said = client.post("/v1/auth/google", json={"credential": "d" * 40})
    assert said.status_code == 403
    assert said.json()["detail"] == NOT_YET


def test_a_stranger_cannot_sign_in_with_a_password(
    latched: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _ = latched
    with TestClient(app) as client:
        said = client.post(
            "/v1/auth/password",
            json={"email": "stranger@example.com", "password": "whatever-they-try"},
        )
    assert said.status_code == 403


def test_a_named_address_still_gets_in(latched: tuple[FastAPI, sessionmaker[Session]]) -> None:
    app, _ = latched
    with TestClient(app) as client:
        said = client.post(
            "/v1/auth/register",
            json={
                "email": "dana@alphaplumbing.ca",
                "password": "a-long-enough-one",
                "name": "Dana",
            },
        )
    assert said.status_code == 200, said.text
    assert said.json()["person"]["email"] == "dana@alphaplumbing.ca"


def test_somebody_invited_from_inside_gets_in(
    latched: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = latched
    with factory() as session:
        host = UserAccount(google_sub=None, email="dana@alphaplumbing.ca", name="Dana")
        place = Organization(name="Alpha Plumbing")
        session.add_all([host, place])
        session.flush()
        session.add(
            Invitation(
                organization_id=place.id,
                email="new.hire@example.com",
                invited_by=host.id,
                token_hash="x" * 64,
                expires_at=datetime.now(UTC) + timedelta(days=3),
            )
        )
        session.commit()

    with TestClient(app) as client:
        said = client.post(
            "/v1/auth/register",
            json={"email": "new.hire@example.com", "password": "a-long-enough-one", "name": "New"},
        )
    assert said.status_code == 200, said.text


def test_the_screens_can_ask_whether_anybody_may_join(
    latched: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _ = latched
    with TestClient(app) as client:
        assert client.get("/v1/open").json() == {"open": False}


def test_the_free_audit_runs_for_a_stranger_with_no_account(
    latched: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The whole point of the launch. If this ever fails, nothing else matters."""
    app, _ = latched
    with TestClient(app) as client:
        said = client.post(
            "/v1/audits",
            json={"business_name": "Alpha Plumbing", "site": "alphaplumbing.ca"},
        )
    assert said.status_code == 202, said.text
    assert said.json()["status"] == "queued"
