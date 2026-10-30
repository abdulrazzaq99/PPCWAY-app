"""Choosing which Google Ads account we read.

Somebody with three accounts has to say which one their ads run in, and the
number they end up with must be one Google agrees they can reach. A number typed
by hand, or one belonging to somebody else, is not storable.
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
from ppcway.ads.accounts import AdsAccount
from ppcway.api import app as api_module
from ppcway.api.app import create_app
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.org.places import home_for

#: The deployment's encryption key, so a stored permission is a real one.
KEY = Fernet.generate_key()

THEIRS = AdsAccount(
    customer_id="2580586343",
    name="Byte9",
    is_manager=False,
    currency="CAD",
    time_zone="America/Toronto",
)


@pytest.fixture
def app_and_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    monkeypatch.setattr(
        google.id_token,  # type: ignore[attr-defined]
        "verify_oauth2_token",
        lambda credential, *a, **k: {
            "sub": "google-dana",
            "email": "dana@alphaplumbing.ca",
            "email_verified": True,
            "name": "Dana",
        },
    )
    # Google's part: an hour of access, and the one account this permission reaches.
    monkeypatch.setattr(api_module, "fresh_access_token", lambda *a, **k: "an-hour")
    monkeypatch.setattr(api_module, "accessible_accounts", lambda **k: [THEIRS])

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


def connected(client: TestClient, factory: sessionmaker[Session]) -> str:
    """Somebody signed in whose Google Ads permission is already stored."""
    token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
    with factory() as session:
        account = session.scalars(sa.select(UserAccount)).one()
        session.add(
            ads_models.AdsConnection(
                account_id=account.id,
                organization_id=home_for(session, account).id,
                ciphertext=Fernet(KEY).encrypt(b"a-lasting-permission").decode(),
                customer_id=None,
            )
        )
        session.commit()
    return str(token)


def test_choosing_an_account_is_remembered(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        chose = client.post(
            "/v1/ads/choose",
            json={"customer_id": "258-058-6343"},
            headers={"x-session-token": token},
        )
        assert chose.status_code == 200, chose.text
        assert chose.json()["customer_name"] == "Byte9"

        # And it is what the home page is told from then on.
        status = client.get("/v1/ads/status", headers={"x-session-token": token}).json()
        assert status["customer_id"] == "2580586343"
        assert status["customer_name"] == "Byte9"


def test_an_account_google_does_not_grant_cannot_be_stored(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        chose = client.post(
            "/v1/ads/choose",
            json={"customer_id": "9999999999"},
            headers={"x-session-token": token},
        )
        assert chose.status_code == 404
        status = client.get("/v1/ads/status", headers={"x-session-token": token}).json()
        assert not status["customer_id"]


def test_choosing_without_a_connection_says_to_connect_first(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _ = app_and_db
    with TestClient(app) as client:
        token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
        chose = client.post(
            "/v1/ads/choose",
            json={"customer_id": "2580586343"},
            headers={"x-session-token": token},
        )
        assert chose.status_code == 404


def test_choosing_while_signed_out_is_refused(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _ = app_and_db
    with TestClient(app) as client:
        assert client.post("/v1/ads/choose", json={"customer_id": "2580586343"}).status_code == 401
