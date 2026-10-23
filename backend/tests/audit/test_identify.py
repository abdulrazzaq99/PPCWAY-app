"""Telling the person what kind of business we think they are, before we judge them.

The kind decides which checks are asked, so a wrong one quietly produces a
wrong report. That is why it is shown, why it says how sure it is, and why the
person can overrule it.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.api import app as api_module
from ppcway.api.app import create_app
from ppcway.audit import places as places_module
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.audit.places import Listing
from ppcway.audit.types import AuditReport, Finding
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session


def a_listing(**over: Any) -> Listing:
    fields: dict[str, Any] = {
        "place_id": "p1",
        "name": "Alpha Plumbing",
        "address": "12 King St, Mississauga, ON, Canada",
        "short_address": "12 King St, Mississauga",
        "category": "Plumber",
        "status": "OPERATIONAL",
        "service_area_only": True,
        "maps_url": "",
        "rating": 4.6,
        "reviews": 120,
        "website": "https://alphaplumbing.ca",
        "phone": "",
        "open_now": None,
        "lat": None,
        "lng": None,
        "primary_type": "plumber",
        "types": ("plumber", "point_of_interest", "establishment"),
        "maps_label": "Plumber",
        "open_24h": True,
    }
    fields.update(over)
    return Listing(**fields)


@pytest.fixture
def app_and_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(api_module, "to_pdf", lambda url, **k: b"%PDF-1.4")
    app = create_app(
        Settings(google_maps_api_key=SecretStr("maps-key"), app_base_url="https://app.ppcway.com")
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


def test_a_listing_whose_website_matches_settles_the_kind(
    app_and_db: tuple[FastAPI, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(places_module, "find_businesses", lambda name, **k: [a_listing()])
    app, _ = app_and_db
    with TestClient(app) as client:
        said = client.post(
            "/v1/public/identify",
            json={"business_name": "Alpha Plumbing", "site": "alphaplumbing.ca"},
        ).json()

    assert said["matched"] is True
    assert said["sure"] is True
    # Open round the clock, so this is the one trade the night question suits.
    assert said["kind"] == "emergency"
    assert said["label"] == "Emergency call-outs"
    assert "Plumber" in said["because"]
    # Every kind is offered, so disagreeing is one tap rather than a dead end.
    assert len(said["choices"]) == 14


def test_a_listing_on_another_website_is_offered_but_not_trusted(
    app_and_db: tuple[FastAPI, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two businesses share a name far more often than they share a domain."""
    monkeypatch.setattr(
        places_module,
        "find_businesses",
        lambda name, **k: [a_listing(name="Alpha Plumbing Ltd", website="https://someoneelse.ca")],
    )
    app, _ = app_and_db
    with TestClient(app) as client:
        said = client.post(
            "/v1/public/identify",
            json={"business_name": "Alpha Plumbing", "site": "alphaplumbing.ca"},
        ).json()

    assert said["found"] is True
    assert said["matched"] is False
    assert said["sure"] is False
    assert "Check this is you" in said["because"]


def test_with_no_listing_at_all_it_guesses_and_says_so(
    app_and_db: tuple[FastAPI, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(places_module, "find_businesses", lambda name, **k: [])
    app, _ = app_and_db
    with TestClient(app) as client:
        said = client.post(
            "/v1/public/identify",
            json={"business_name": "Oakville Heating Ltd", "site": "oakvilleheating.ca"},
        ).json()

    assert said["found"] is False
    assert said["sure"] is False
    # Google has no type for heating engineers, so the name is all there is.
    assert said["kind"] == "trades"
    assert said["choices"]


def test_the_kind_the_person_chose_is_what_is_kept(
    app_and_db: tuple[FastAPI, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_module, "_run", lambda *a, **k: None)
    app, factory = app_and_db
    with TestClient(app) as client:
        client.post(
            "/v1/public/audits",
            json={
                "business_name": "Reid & Co",
                "site": "reidlaw.ca",
                "kind": "professional",
                "kind_is_theirs": True,
            },
        )

    with factory() as session:
        asked = session.scalars(sa.select(AuditRequest)).one()
    assert asked.kind == "professional"
    assert asked.kind_is_theirs is True


def test_a_finding_that_does_not_suit_the_business_never_reaches_the_report(
    app_and_db: tuple[FastAPI, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of the whole thing, through the real run."""
    made = AuditReport(site="shop.example", started_at=datetime.now(UTC))
    made.findings = [
        Finding(
            key="local",
            title="The towns you serve",
            status="needs_you",
            summary="No towns listed.",
        ),
        Finding(key="speed", title="Speed on a phone", status="good", summary="Quick."),
    ]
    monkeypatch.setattr(api_module, "run_audit", lambda site, settings, on_stage=None: made)
    app, factory = app_and_db
    # The background run builds its own sessions, so it has to be pointed at
    # the same database the request used.
    monkeypatch.setattr(api_module, "session_factory", lambda: factory)

    with TestClient(app) as client:
        started = client.post(
            "/v1/public/audits",
            json={"business_name": "Shop", "site": "shop.example", "kind": "ecommerce"},
        ).json()

    with factory() as session:
        run = session.get(AuditRun, __import__("uuid").UUID(started["audit_id"]))
        assert run is not None
        assert run.status == "done", run.error
        keys = [f["key"] for f in (run.report or {}).get("findings", [])]

    # An online store has no towns it serves, so it is never asked about them.
    assert keys == ["speed"]
