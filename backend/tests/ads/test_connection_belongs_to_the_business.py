"""Fix F3: the Google Ads connection belongs to the business, not to one person.

The model has said so since it was written -- "a connection outlives the person
who granted it: staff leave, and the account they connected stays" -- while the
query asked for `account_id`. So a business whose owner connected Google Ads
looked unconnected to every colleague they invited, and the whole roles feature
stopped at the one screen that matters most.

The brief's test is "an invited admin, member and expert each see the Google Ads
connection", so that is what these ask, through the endpoint the interface
actually calls rather than through the helper.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.api.app import create_app
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.org.models import Role
from ppcway.org.places import home_for, invite

KEY = Fernet.generate_key()

#: Who signs in, in the order they arrive. The owner connects Google Ads; the
#: other three are invited afterwards and never touch Google themselves.
PEOPLE = {
    "dana@alphaplumbing.ca": ("google-dana", "Dana"),
    "sam@alphaplumbing.ca": ("google-sam", "Sam"),
    "ravi@alphaplumbing.ca": ("google-ravi", "Ravi"),
    "nina@consultancy.example": ("google-nina", "Nina"),
}


@pytest.fixture
def app_and_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def whoever(credential: str, *a: object, **k: object) -> dict[str, object]:
        # The credential is the address, so one fake stands in for four people.
        sub, name = PEOPLE[credential]
        return {"sub": sub, "email": credential, "email_verified": True, "name": name}

    monkeypatch.setattr(
        google.id_token,  # type: ignore[attr-defined]
        "verify_oauth2_token",
        whoever,
    )
    settings = Settings(
        google_signin_client_id="test-client",
        google_oauth_client_id="test-client",
        google_oauth_client_secret=SecretStr("test-secret"),
        google_ads_developer_token=SecretStr("test-token"),
        google_oauth_token_key=SecretStr(KEY.decode()),
    )
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


def _sign_in(client: TestClient, email: str) -> str:
    reply = client.post("/v1/auth/google", json={"credential": email})
    assert reply.status_code == 200, reply.text
    return str(reply.json()["token"])


def _owner_connects(client: TestClient, factory: sessionmaker[Session]) -> str:
    """Dana signs in and her Google Ads permission is stored against her business."""
    token = _sign_in(client, "dana@alphaplumbing.ca")
    with factory() as session:
        dana = session.scalar(
            sa.select(UserAccount).where(UserAccount.email == "dana@alphaplumbing.ca")
        )
        assert dana is not None
        session.add(
            ads_models.AdsConnection(
                account_id=dana.id,
                organization_id=home_for(session, dana).id,
                ciphertext=Fernet(KEY).encrypt(b"a-lasting-permission").decode(),
                customer_id="2580586343",
                customer_name="Byte9",
                currency="CAD",
            )
        )
        session.commit()
    return token


def _joins(client: TestClient, factory: sessionmaker[Session], email: str, role: Role) -> str:
    """Invite somebody to Dana's business, and have them take it up."""
    with factory() as session:
        dana = session.scalar(
            sa.select(UserAccount).where(UserAccount.email == "dana@alphaplumbing.ca")
        )
        assert dana is not None
        secret = invite(session, home_for(session, dana), by=dana, email=email, role=role)
    token = _sign_in(client, email)
    taken = client.post(
        "/v1/org/accept", json={"token": secret}, headers={"x-session-token": token}
    )
    assert taken.status_code == 200, taken.text
    return token


@pytest.mark.parametrize(
    ("email", "role"),
    [
        ("sam@alphaplumbing.ca", Role.ADMIN),
        ("ravi@alphaplumbing.ca", Role.MEMBER),
        ("nina@consultancy.example", Role.EXPERT),
    ],
)
def test_an_invited_colleague_sees_the_connected_account(
    app_and_db: tuple[FastAPI, sessionmaker[Session]], email: str, role: Role
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        _owner_connects(client, factory)
        token = _joins(client, factory, email, role)

        status = client.get("/v1/ads/status", headers={"x-session-token": token})
        assert status.status_code == 200, status.text
        said = status.json()
        assert said["connected"] is True, f"a {role.value} could not see the connection"
        assert said["customer_id"] == "2580586343"
        assert said["customer_name"] == "Byte9"


def test_somebody_in_another_business_sees_nothing(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The scope is the business, which is not the same as no scope at all."""
    app, factory = app_and_db
    with TestClient(app) as client:
        _owner_connects(client, factory)
        # Signs in, is invited to nothing, and so gets a business of their own.
        alone = _sign_in(client, "nina@consultancy.example")
        status = client.get("/v1/ads/status", headers={"x-session-token": alone}).json()
        assert status["connected"] is False
        assert not status.get("customer_id")


def test_the_owner_still_sees_their_own_connection(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = _owner_connects(client, factory)
        status = client.get("/v1/ads/status", headers={"x-session-token": token}).json()
        assert status["connected"] is True
        assert status["customer_id"] == "2580586343"
