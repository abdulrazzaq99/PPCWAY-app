"""An invitation, end to end, through the endpoints the screens call.

The owner signs in and connects Google Ads, invites somebody from the Team
screen, and the letter goes out. The invitee signs in -- by Google or with an
address and password -- and the portal's first load gives them an empty
business of their own, as it did in production on 6 November. They accept with
the token from the letter's link, and every screen after that is the owner's
business, with its Google Ads.

The link reaches the invitee by email and by nothing else. It comes back to the
inviter only when the email could not go, for them to pass on themselves.
"""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.api import app as app_module
from ppcway.api.app import create_app
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.mail.send import Letter, NotSent, Post
from ppcway.org.places import home_for
from ppcway.staff import models as _staff  # noqa: F401 - registers its table

KEY = Fernet.generate_key()
OWNER = "owner@pdfezy.com"
#: Google sign-in is faked: the credential carries the address it stands for.
PEOPLE = {
    OWNER: ("google-owner", "Owner"),
    "webalive@gmail.com": ("google-webalive", "Web Alive"),
    "stranger@gmail.com": ("google-stranger", "Stranger"),
}

Letters = list[Letter]


@pytest.fixture
def world(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[FastAPI, sessionmaker[Session], Letters]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def whoever(credential: str, *a: object, **k: object) -> dict[str, object]:
        email = credential.split("|")[0]
        sub, name = PEOPLE[email]
        return {"sub": sub, "email": email, "email_verified": True, "name": name}

    monkeypatch.setattr(google.id_token, "verify_oauth2_token", whoever)
    letters: Letters = []

    def posted(post: Post, letter: Letter, **k: object) -> None:
        letters.append(letter)

    monkeypatch.setattr(app_module, "send", posted)
    settings = Settings(
        google_signin_client_id="test-client",
        google_oauth_client_id="test-client",
        google_oauth_client_secret=SecretStr("test-secret"),
        google_ads_developer_token=SecretStr("test-token"),
        google_oauth_token_key=SecretStr(KEY.decode()),
        app_base_url="https://app.ppcway.com",
    )
    app = create_app(settings)

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory, letters
    Base.metadata.drop_all(engine)


def _google(client: TestClient, email: str) -> dict[str, str]:
    reply = client.post("/v1/auth/google", json={"credential": f"{email}|{'x' * 20}"})
    assert reply.status_code == 200, reply.text
    return {"x-session-token": str(reply.json()["token"])}


def _owner_with_ads(client: TestClient, factory: sessionmaker[Session]) -> dict[str, str]:
    owner = _google(client, OWNER)
    assert client.post("/v1/org/name", json={"name": "PDFezy"}, headers=owner).status_code == 204
    with factory() as session:
        me = session.scalar(sa.select(UserAccount).where(UserAccount.email == OWNER))
        assert me is not None
        session.add(
            ads_models.AdsConnection(
                account_id=me.id,
                organization_id=home_for(session, me).id,
                ciphertext=Fernet(KEY).encrypt(b"a-lasting-permission").decode(),
                customer_id="2580586343",
                customer_name="PDFezy",
                currency="USD",
            )
        )
        session.commit()
    return owner


def _token_in(letters: Letters) -> str:
    """The token in the latest invitation's link, read the way a click reads it.

    The latest invitation, not the latest letter: making an account with a
    password posts its own confirmation.
    """
    words = (word for letter in reversed(letters) for word in letter.text.split())
    link = next(word for word in words if "/invite?token=" in word)
    return str(parse_qs(urlparse(link).query)["token"][0])


def test_an_emailed_invitation_keeps_its_link_in_the_inbox(
    world: tuple[FastAPI, sessionmaker[Session], Letters],
) -> None:
    app, factory, letters = world
    with TestClient(app) as client:
        owner = _owner_with_ads(client, factory)
        reply = client.post(
            "/v1/org/invite", json={"email": "webalive@gmail.com", "role": "admin"}, headers=owner
        )
        assert reply.status_code == 200, reply.text
        said = reply.json()
        assert said == {"email": "webalive@gmail.com", "role": "admin", "emailed": True}
        (letter,) = letters
        assert letter.to == "webalive@gmail.com"
        assert "PDFezy" in letter.subject
        assert "https://app.ppcway.com/invite?token=" in letter.text


def test_when_the_email_cannot_go_the_inviter_gets_the_link(
    world: tuple[FastAPI, sessionmaker[Session], Letters],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, factory, _ = world

    def refused(post: Post, letter: Letter, **k: object) -> None:
        raise NotSent("the provider said no")

    monkeypatch.setattr(app_module, "send", refused)
    with TestClient(app) as client:
        owner = _owner_with_ads(client, factory)
        said = client.post(
            "/v1/org/invite", json={"email": "webalive@gmail.com", "role": "admin"}, headers=owner
        ).json()
        assert said["emailed"] is False
        assert said["link"].startswith("https://app.ppcway.com/invite?token=")


def test_an_invitee_signing_in_with_google_lands_in_the_owner_s_business(
    world: tuple[FastAPI, sessionmaker[Session], Letters],
) -> None:
    app, factory, letters = world
    with TestClient(app) as client:
        owner = _owner_with_ads(client, factory)
        client.post(
            "/v1/org/invite", json={"email": "webalive@gmail.com", "role": "admin"}, headers=owner
        )
        token = _token_in(letters)

        invitee = _google(client, "webalive@gmail.com")
        first = client.get("/v1/org", headers=invitee).json()
        assert first["name"] != "PDFezy", "the first load gives them a business of their own"

        stranger = _google(client, "stranger@gmail.com")
        taken = client.post("/v1/org/accept", json={"token": token}, headers=stranger)
        assert taken.status_code == 400, "the link is for one address"

        taken = client.post("/v1/org/accept", json={"token": token}, headers=invitee)
        assert taken.status_code == 200, taken.text
        org = client.get("/v1/org", headers=invitee).json()
        assert (org["name"], org["your_role"]) == ("PDFezy", "admin")
        status = client.get("/v1/ads/status", headers=invitee).json()
        assert status["connected"] is True and status["customer_id"] == "2580586343"

        people = client.get("/v1/org", headers=owner).json()["people"]
        assert {p["email"]: p["role"] for p in people}["webalive@gmail.com"] == "admin"

        again = client.post("/v1/org/accept", json={"token": token}, headers=invitee)
        assert again.status_code == 400, "the link works once"
        back = _google(client, "webalive@gmail.com")
        assert client.get("/v1/org", headers=back).json()["name"] == "PDFezy"


def test_an_admin_invites_in_turn_but_never_an_owner(
    world: tuple[FastAPI, sessionmaker[Session], Letters],
) -> None:
    app, factory, letters = world
    with TestClient(app) as client:
        owner = _owner_with_ads(client, factory)
        client.post(
            "/v1/org/invite", json={"email": "webalive@gmail.com", "role": "admin"}, headers=owner
        )
        admin = _google(client, "webalive@gmail.com")
        client.post("/v1/org/accept", json={"token": _token_in(letters)}, headers=admin)

        member = client.post(
            "/v1/org/invite", json={"email": "sam@pdfezy.com", "role": "member"}, headers=admin
        )
        assert member.status_code == 200, member.text
        owner_too = client.post(
            "/v1/org/invite", json={"email": "ravi@pdfezy.com", "role": "owner"}, headers=admin
        )
        assert owner_too.status_code == 400


def test_an_invitee_who_makes_an_account_with_a_password_lands_there_too(
    world: tuple[FastAPI, sessionmaker[Session], Letters],
) -> None:
    app, factory, letters = world
    with TestClient(app) as client:
        owner = _owner_with_ads(client, factory)
        client.post(
            "/v1/org/invite",
            json={"email": "new.person@pdfezy.com", "role": "member"},
            headers=owner,
        )
        made = client.post(
            "/v1/auth/register",
            json={
                "email": "new.person@pdfezy.com",
                "password": "a long enough passphrase 42!",
                "name": "New Person",
            },
        )
        assert made.status_code == 200, made.text
        invitee = {"x-session-token": str(made.json()["token"])}
        client.get("/v1/org", headers=invitee)  # the portal's first load

        taken = client.post("/v1/org/accept", json={"token": _token_in(letters)}, headers=invitee)
        assert taken.status_code == 200, taken.text
        org = client.get("/v1/org", headers=invitee).json()
        assert (org["name"], org["your_role"]) == ("PDFezy", "member")
        assert client.get("/v1/ads/status", headers=invitee).json()["connected"] is True
