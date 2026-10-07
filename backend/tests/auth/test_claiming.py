"""An audit run before signing in should be waiting inside the account afterwards.

Somebody runs the free audit, likes what it says and makes an account. If the
report they were reading is not there, the account they just made looks empty and
the thing that persuaded them is gone.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ppcway.api.app import create_app
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.auth import google
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session


@pytest.fixture
def app_and_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    """The API on a database of its own, with Google's part stubbed."""
    # StaticPool: an in-memory SQLite is per connection, and the test client runs
    # the app on another thread, which would otherwise find an empty database.
    engine = sa.create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    # Each credential is a different person: the first letter stands for them.
    monkeypatch.setattr(
        google.id_token,
        "verify_oauth2_token",
        lambda credential, *a, **k: {
            "sub": f"google-{credential[:1]}",
            "email": f"{credential[:1]}@alphaplumbing.ca",
            "email_verified": True,
            "name": "Dana",
        },
    )
    settings = Settings(google_signin_client_id="test-client")  # type: ignore[call-arg]
    app = create_app(settings)

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory
    Base.metadata.drop_all(engine)


def an_audit(factory: sessionmaker[Session], *, owner: uuid.UUID | None = None) -> uuid.UUID:
    """A finished audit nobody has claimed, as the free form leaves behind."""
    with factory() as session:
        asked = AuditRequest(
            name="",
            email="",
            phone="",
            business_name="Alpha Plumbing",
            site="alphaplumbing.ca",
            source="landing",
            consent_text="",
            user_id=owner,
        )
        session.add(asked)
        session.flush()
        run = AuditRun(request_id=asked.id, site="https://alphaplumbing.ca/", status="done")
        session.add(run)
        session.commit()
        return run.id


def sign_in(client: TestClient, who: str = "x") -> str:
    return client.post("/v1/auth/google", json={"credential": who * 40}).json()["token"]


def test_an_audit_run_before_signing_in_is_waiting_afterwards(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        run_id = an_audit(factory)
        token = sign_in(client)
        assert client.get("/v1/audits/mine", headers={"x-session-token": token}).json() == []

        claimed = client.post(
            "/v1/audits/claim", json={"ids": [str(run_id)]}, headers={"x-session-token": token}
        )
        assert claimed.json()["claimed"] == 1
        mine = client.get("/v1/audits/mine", headers={"x-session-token": token}).json()
        assert [m["id"] for m in mine] == [str(run_id)]


def test_an_audit_that_already_belongs_to_somebody_cannot_be_taken(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = sign_in(client)
        mine = an_audit(factory)
        client.post(
            "/v1/audits/claim", json={"ids": [str(mine)]}, headers={"x-session-token": token}
        )

        # A second person, knowing the id, gets nothing and sees nothing.
        stranger = sign_in(client, who="y")
        taken = client.post(
            "/v1/audits/claim", json={"ids": [str(mine)]}, headers={"x-session-token": stranger}
        )
        assert taken.json()["claimed"] == 0
        assert client.get("/v1/audits/mine", headers={"x-session-token": stranger}).json() == []


def test_claiming_needs_somebody_signed_in(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        run_id = an_audit(factory)
        assert client.post("/v1/audits/claim", json={"ids": [str(run_id)]}).status_code == 401
