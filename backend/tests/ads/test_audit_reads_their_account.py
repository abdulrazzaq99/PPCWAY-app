"""An audit run by somebody who connected their account reads it too.

This is the join between the two halves of the product: the free audit sees what
Google shows the public, and their own account answers the four checks it cannot.
Everybody else's audit must be unaffected, which is most of what is tested here.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.api import app as api_module
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.org.places import home_for

KEY = Fernet.generate_key()

READING = {
    "customer_id": "2580586343",
    "window_days": 30,
    "spend": {"cost": 47.18, "clicks": 603},
    "wasted": {"read": True, "trouble": "", "cost": 7.0, "terms": []},
}


@pytest.fixture
def factory() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def settings() -> Settings:
    return Settings(
        google_oauth_client_id="test-client",
        google_oauth_client_secret=SecretStr("test-secret"),
        google_ads_developer_token=SecretStr("test-token"),
        google_oauth_token_key=SecretStr(KEY.decode()),
    )


def a_run(
    factory: sessionmaker[Session],
    *,
    signed_in: bool = True,
    connected: bool = True,
    chosen: str | None = "2580586343",
) -> uuid.UUID:
    with factory() as session:
        owner: uuid.UUID | None = None
        if signed_in:
            person = UserAccount(
                google_sub="google-dana", email="dana@alphaplumbing.ca", name="Dana"
            )
            session.add(person)
            session.flush()
            owner = person.id
            if connected:
                session.add(
                    ads_models.AdsConnection(
                        account_id=person.id,
                        organization_id=home_for(session, person).id,
                        ciphertext=Fernet(KEY).encrypt(b"a-lasting-permission").decode(),
                        customer_id=chosen,
                    )
                )
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
        run = AuditRun(request_id=asked.id, site="https://alphaplumbing.ca/", status="running")
        session.add(run)
        session.commit()
        return run.id


@pytest.fixture(autouse=True)
def google(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Google's part, and a note of which account was actually read."""
    read: list[str] = []
    monkeypatch.setattr(api_module, "fresh_access_token", lambda *a, **k: "an-hour")

    class Reading:
        def as_dict(self) -> dict[str, Any]:
            return READING

    def record(customer_id: str, **kw: Any) -> Reading:
        read.append(customer_id)
        return Reading()

    monkeypatch.setattr(api_module, "read_account", record)
    return read


def test_their_chosen_account_is_read_and_kept_with_the_report(
    factory: sessionmaker[Session], google: list[str]
) -> None:
    found = api_module._their_ads(a_run(factory), settings(), factory)
    assert google == ["2580586343"]
    assert found == READING


def test_a_stranger_running_the_free_audit_is_not_read(
    factory: sessionmaker[Session], google: list[str]
) -> None:
    assert api_module._their_ads(a_run(factory, signed_in=False), settings(), factory) is None
    assert google == []


def test_signed_in_without_connecting_is_not_read(
    factory: sessionmaker[Session], google: list[str]
) -> None:
    assert api_module._their_ads(a_run(factory, connected=False), settings(), factory) is None
    assert google == []


def test_connected_without_choosing_an_account_is_not_read(
    factory: sessionmaker[Session], google: list[str]
) -> None:
    """Which account their ads run in is theirs to say; we do not guess."""
    assert api_module._their_ads(a_run(factory, chosen=None), settings(), factory) is None
    assert google == []


def test_a_revoked_permission_is_not_used_again(
    factory: sessionmaker[Session], google: list[str]
) -> None:
    run_id = a_run(factory)
    with factory() as session:
        connection = session.scalars(sa.select(ads_models.AdsConnection)).one()
        connection.revoked_at = sa.func.now()
        session.commit()
    assert api_module._their_ads(run_id, settings(), factory) is None
    assert google == []


def test_a_refusal_from_google_leaves_the_audit_standing(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The website half of the report is finished by then. It goes out."""
    from ppcway.ads.oauth import AdsConnectionRefused

    def refuse(*a: Any, **k: Any) -> str:
        raise AdsConnectionRefused("Google refused the connection: invalid_grant")

    monkeypatch.setattr(api_module, "fresh_access_token", refuse)
    assert api_module._their_ads(a_run(factory), settings(), factory) is None
