"""The report as a PDF, and the changes it lists.

A downloaded report is printed the moment it is asked for, from the web app's
own A4 page, signed in as the person asking: never a stored copy, which would
be out of date by the next sync. These hold the endpoint to that, and the list
of changes to the report's own dates.

Dates come from the clock: a pinned day stops being inside the window as soon
as the calendar passes it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.ads.mirror import MICRO, CampaignDay, MirrorCampaign
from ppcway.api import app as app_module
from ppcway.api.app import create_app, period_words
from ppcway.audit.paper import NotPrinted
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.opt.models import OptimizationAction
from ppcway.org.places import home_for
from ppcway.rules.offered import changes_between
from ppcway.staff import models as _staff  # noqa: F401 - registers its table

KEY = Fernet.generate_key()
C = "2580586343"
OWNER = "owner@pdfezy.com"
NOW = datetime.now(UTC)
TODAY = NOW.date()

World = tuple[FastAPI, sessionmaker[Session], list[dict[str, object]]]


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def whoever(credential: str, *a: object, **k: object) -> dict[str, object]:
        return {"sub": "google-owner", "email": OWNER, "email_verified": True, "name": "Owner"}

    monkeypatch.setattr(google.id_token, "verify_oauth2_token", whoever)
    printed: list[dict[str, object]] = []

    def printer(url: str, **how: object) -> bytes:
        printed.append({"url": url, **how})
        return b"%PDF-1.7 the report"

    monkeypatch.setattr(app_module, "to_pdf", printer)
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
    yield app, factory, printed
    Base.metadata.drop_all(engine)


def _signed_in_with_figures(client: TestClient, factory: sessionmaker[Session]) -> dict[str, str]:
    """The owner of PDFezy, connected, with thirty days of spend and leads."""
    reply = client.post("/v1/auth/google", json={"credential": "x" * 24})
    assert reply.status_code == 200, reply.text
    token = str(reply.json()["token"])
    with factory() as session:
        me = session.scalar(sa.select(UserAccount).where(UserAccount.email == OWNER))
        assert me is not None
        session.add(
            ads_models.AdsConnection(
                account_id=me.id,
                organization_id=home_for(session, me).id,
                ciphertext=Fernet(KEY).encrypt(b"a-lasting-permission").decode(),
                customer_id=C,
                customer_name="PDFezy",
                currency="USD",
            )
        )
        session.add(
            MirrorCampaign(
                customer_id=C,
                resource_name=f"customers/{C}/campaigns/12",
                campaign_id="12",
                name="PDFezy | Search",
                status="ENABLED",
                budget_micros=20 * MICRO,
            )
        )
        for back in range(1, 31):
            session.add(
                CampaignDay(
                    customer_id=C,
                    campaign_id="12",
                    day=TODAY - timedelta(days=back),
                    cost_micros=4 * MICRO,
                    forms=10.0,
                    conversions=10.0,
                    clicks=20,
                    impressions=400,
                )
            )
        session.commit()
    return {"x-session-token": token}


def _change(
    factory: sessionmaker[Session], *, label: str, applied: datetime | None, status: str
) -> None:
    with factory() as session:
        me = session.scalar(sa.select(UserAccount).where(UserAccount.email == OWNER))
        assert me is not None
        session.add(
            OptimizationAction(
                id=uuid.uuid4(),
                organization_id=home_for(session, me).id,
                customer_id=C,
                kind="add_negative_keyword",
                rule_id="R1",
                target_kind="search_term",
                target_id=label,
                target_label=label,
                payload={"change": "add_negative", "text": label},
                status=status,
                created_at=(applied or NOW) - timedelta(hours=2),
                approved_at=(applied or NOW) - timedelta(hours=1),
                applied_at=applied,
            )
        )
        session.commit()


# ---------- the PDF ----------


def test_the_pdf_is_printed_from_the_report_page_signed_in_as_the_asker(world: World) -> None:
    app, factory, printed = world
    with TestClient(app) as client:
        owner = _signed_in_with_figures(client, factory)
        reply = client.get("/v1/reports/pdf?days=30", headers=owner)

    assert reply.status_code == 200, reply.text
    assert reply.headers["content-type"] == "application/pdf"
    assert reply.content.startswith(b"%PDF")
    (job,) = printed
    assert job["url"] == "https://app.ppcway.com/reports/pdf?days=30"
    assert job["session_cookie"] == ("ppcway_session", owner["x-session-token"])
    assert "pageNumber" in str(job["footer"]) and "PDFezy" in str(job["footer"])


def test_the_pdf_is_never_kept(world: World) -> None:
    app, factory, printed = world
    with TestClient(app) as client:
        owner = _signed_in_with_figures(client, factory)
        client.get("/v1/reports/pdf?days=30", headers=owner)
        reply = client.get("/v1/reports/pdf?days=30", headers=owner)
    assert len(printed) == 2, "each download is printed fresh"
    assert reply.headers["cache-control"] == "no-store"


def test_the_file_is_named_for_the_business_and_the_dates(world: World) -> None:
    app, factory, _ = world
    with TestClient(app) as client:
        owner = _signed_in_with_figures(client, factory)
        reply = client.get("/v1/reports/pdf?days=7", headers=owner)
    said = unquote(reply.headers["content-disposition"])
    starts, ends = TODAY - timedelta(days=7), TODAY - timedelta(days=1)
    assert said.startswith("attachment;")
    assert "PPCWay report - PDFezy - " in said
    assert f"{ends.day} {ends:%b} {ends.year}.pdf" in said
    assert f"{starts.day} {starts:%b}" in said


def test_an_odd_period_is_read_as_thirty_days(world: World) -> None:
    app, factory, printed = world
    with TestClient(app) as client:
        owner = _signed_in_with_figures(client, factory)
        client.get("/v1/reports/pdf?days=11", headers=owner)
    assert printed[0]["url"] == "https://app.ppcway.com/reports/pdf?days=30"


def test_nobody_signed_in_gets_nothing(world: World) -> None:
    app, _, printed = world
    with TestClient(app) as client:
        reply = client.get("/v1/reports/pdf?days=30")
    assert reply.status_code == 401
    assert printed == []


def test_a_page_that_will_not_print_says_so(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    app, factory, _ = world

    def broken(url: str, **how: object) -> bytes:
        raise NotPrinted("the browser gave up")

    monkeypatch.setattr(app_module, "to_pdf", broken)
    with TestClient(app) as client:
        owner = _signed_in_with_figures(client, factory)
        reply = client.get("/v1/reports/pdf?days=30", headers=owner)
    assert reply.status_code == 503
    assert "could not be made into a PDF" in reply.json()["detail"]


def test_the_dates_are_written_the_way_people_say_them() -> None:
    assert period_words("2026-10-12", "2026-11-10") == "12 Oct to 10 Nov 2026"
    assert period_words("2025-12-12", "2026-01-10") == "12 Dec 2025 to 10 Jan 2026"


# ---------- the changes it lists ----------


def test_the_report_lists_the_changes_made_inside_its_dates(world: World) -> None:
    app, factory, _ = world
    with TestClient(app) as client:
        owner = _signed_in_with_figures(client, factory)
        _change(
            factory, label="pdf to word free", applied=NOW - timedelta(days=3), status="applied"
        )
        _change(factory, label="merge pdf", applied=NOW - timedelta(days=10), status="applied")
        _change(factory, label="old one", applied=NOW - timedelta(days=60), status="applied")
        said = client.get("/v1/reports?days=30", headers=owner).json()

    assert [c["target"]["label"] for c in said["changes"]] == ["pdf to word free", "merge pdf"]
    assert said["changes_in_all"] == 2


def test_a_change_somebody_said_no_to_is_not_a_change_made(world: World) -> None:
    app, factory, _ = world
    with TestClient(app) as client:
        owner = _signed_in_with_figures(client, factory)
        _change(factory, label="declined", applied=None, status="rejected")
        said = client.get("/v1/reports?days=30", headers=owner).json()
    assert said["changes"] == []


def test_a_long_list_stops_and_says_how_many_there_were(world: World) -> None:
    app, factory, _ = world
    with TestClient(app) as client:
        _signed_in_with_figures(client, factory)
        for n in range(65):
            _change(
                factory,
                label=f"search {n}",
                applied=NOW - timedelta(days=2, minutes=n),
                status="applied",
            )
        with factory() as session:
            me = session.scalar(sa.select(UserAccount).where(UserAccount.email == OWNER))
            assert me is not None
            listed, in_all = changes_between(
                session,
                organization_id=home_for(session, me).id,
                starts_on=TODAY - timedelta(days=30),
                ends_on=TODAY - timedelta(days=1),
            )
    assert len(listed) == 60 and in_all == 65
    assert listed[0]["target"]["label"] == "search 0", "newest first"
