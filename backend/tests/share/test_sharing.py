"""Sharing a report and a fix list with somebody who has no account.

These two endpoints are the only ones in PPCway that answer without anybody
signing in, so what they refuse matters more than what they return.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.ads.mirror import MICRO, CampaignDay, MirrorCampaign
from ppcway.api import app as api_module
from ppcway.api.app import create_app
from ppcway.audit.models import AuditRun
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.org.places import home_for

KEY = Fernet.generate_key()
TODAY = datetime.now(UTC).date()

REPORT = {
    "findings": [
        {
            "key": "counting",
            "title": "Counting calls and forms",
            "status": "needs_you",
            "summary": "Nothing on this site tells Google when somebody calls.",
            "detail": ["No conversion tag on the contact page"],
            "fix": "Add the Google Ads conversion tag to the thank-you page.",
        },
        {
            "key": "speed",
            "title": "Speed on a phone",
            "status": "needs_you",
            "summary": "The home page takes nine seconds on a phone.",
            "detail": ["Largest image is 2.4 MB"],
            "fix": "Compress the hero image and serve it as WebP.",
        },
        {
            "key": "mobile",
            "title": "Works on a phone",
            "status": "good",
            "summary": "The site works on a phone.",
            "detail": [],
            "fix": "",
        },
    ]
}


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
    # Nothing here should reach Google: the report is read from the mirror.
    monkeypatch.setattr(api_module, "fresh_access_token", lambda *a, **k: "an-hour")

    settings = Settings(
        google_signin_client_id="test-client",
        google_oauth_client_id="test-client",
        google_oauth_client_secret=SecretStr("test-secret"),
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
    yield app, factory
    Base.metadata.drop_all(engine)


def signed_in(client: TestClient, factory: sessionmaker[Session]) -> str:
    """Somebody signed in, with an account connected and a week in the mirror."""
    token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
    with factory() as session:
        account = session.scalars(sa.select(UserAccount)).one()
        session.add(
            ads_models.AdsConnection(
                account_id=account.id,
                organization_id=home_for(session, account).id,
                ciphertext=Fernet(KEY).encrypt(b"a-lasting-permission").decode(),
                customer_id="2580586343",
                customer_name="Byte9",
                currency="CAD",
            )
        )
        session.add(
            MirrorCampaign(
                customer_id="2580586343",
                resource_name="customers/2580586343/campaigns/11",
                campaign_id="11",
                name="Emergency plumbing",
                status="ENABLED",
                budget_micros=20 * MICRO,
            )
        )
        for back in range(1, 8):
            session.add(
                CampaignDay(
                    customer_id="2580586343",
                    campaign_id="11",
                    day=TODAY - timedelta(days=back),
                    cost_micros=40 * MICRO,
                    forms=2,
                    conversions=2,
                    clicks=20,
                    impressions=300,
                )
            )
        session.commit()
    return str(token)


def finished_audit(factory: sessionmaker[Session]) -> str:
    with factory() as session:
        run = AuditRun(
            site="https://alphaplumbing.ca",
            status="done",
            report=REPORT,
            finished_at=datetime.now(UTC),
        )
        session.add(run)
        session.commit()
        return str(run.id)


def test_a_report_can_be_shared_and_read_with_no_account(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = signed_in(client, factory)
        made = client.post(
            "/v1/reports/share", json={"days": 14}, headers={"x-session-token": token}
        )
        assert made.status_code == 201, made.text
        url = made.json()["url"]
        assert url.startswith("https://app.ppcway.com/r/")
        secret = url.rsplit("/", 1)[1]

        # No session header at all: this is the whole point of the link.
        shared = client.get(f"/v1/public/report/{secret}")
        assert shared.status_code == 200, shared.text
        said = shared.json()
        assert said["read"] is True
        assert said["business"] == "Byte9"
        assert said["shared"] is True
        assert any(f["key"] == "leads" for f in said["figures"])
        # And nothing about the people behind it travels with it.
        assert "dana@alphaplumbing.ca" not in json.dumps(said)


def test_a_shared_report_stops_working_when_it_is_revoked(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = signed_in(client, factory)
        made = client.post("/v1/reports/share", json={}, headers={"x-session-token": token}).json()
        secret = made["url"].rsplit("/", 1)[1]
        assert client.get(f"/v1/public/report/{secret}").status_code == 200

        stopped = client.delete(
            f"/v1/reports/share/{made['id']}", headers={"x-session-token": token}
        )
        assert stopped.status_code == 204
        assert client.get(f"/v1/public/report/{secret}").status_code == 404


def test_a_token_nobody_issued_is_refused_flatly(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _ = app_and_db
    with TestClient(app) as client:
        refused = client.get("/v1/public/report/not-a-real-token")
        assert refused.status_code == 404
        # The same words whether it is wrong, expired or revoked.
        assert "expired or does not exist" in refused.json()["detail"]


def test_the_report_lists_its_own_live_links(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = signed_in(client, factory)
        client.post("/v1/reports/share", json={}, headers={"x-session-token": token})
        mine = client.get("/v1/reports?days=30", headers={"x-session-token": token}).json()

        assert len(mine["shares"]) == 1
        assert mine["shares"][0]["opened"] == 0
        assert mine["business"] == "Byte9"
        assert mine["sentence"]


def test_the_fix_list_goes_to_a_web_person_with_no_login(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = signed_in(client, factory)
        run_id = finished_audit(factory)
        made = client.post(
            f"/v1/audits/{run_id}/share",
            json={"email": "dev@webshop.ca"},
            headers={"x-session-token": token},
        )
        assert made.status_code == 201, made.text
        said = made.json()
        assert said["url"].startswith("https://app.ppcway.com/fixes/")
        # No email provider is configured here, so the letter did not go. The
        # link still exists, which is what stops the feature failing silently.
        assert said["emailed"] is False

        secret = said["url"].rsplit("/", 1)[1]
        got = client.get(f"/v1/public/fixes/{secret}")
        assert got.status_code == 200, got.text
        fixes = got.json()
        assert fixes["site"] == "https://alphaplumbing.ca"
        assert [job["title"] for job in fixes["jobs"]] == [
            "Counting calls and forms",
            "Speed on a phone",
        ]
        assert fixes["jobs"][0]["fix"].startswith("Add the Google Ads conversion tag")
        assert [f["title"] for f in fixes["fine"]] == ["Works on a phone"]
        assert fixes["score"] == 33


def test_a_report_token_cannot_open_a_fix_list(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = signed_in(client, factory)
        made = client.post("/v1/reports/share", json={}, headers={"x-session-token": token}).json()
        secret = made["url"].rsplit("/", 1)[1]

        assert client.get(f"/v1/public/fixes/{secret}").status_code == 404


def test_an_unfinished_audit_cannot_be_shared(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = signed_in(client, factory)
        with factory() as session:
            run = AuditRun(site="https://alphaplumbing.ca", status="running")
            session.add(run)
            session.commit()
            run_id = str(run.id)

        refused = client.post(
            f"/v1/audits/{run_id}/share", json={}, headers={"x-session-token": token}
        )
        assert refused.status_code == 404


def test_sharing_needs_somebody_signed_in(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _ = app_and_db
    with TestClient(app) as client:
        assert client.post("/v1/reports/share", json={}).status_code == 401
