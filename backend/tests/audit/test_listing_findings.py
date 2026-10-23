"""The Google listing, checked on the server where the kind can reach it.

The case this exists for: "six businesses nearby are open twenty four hours"
reaches an emergency plumber and never reaches a law firm. The last test drives
the real run and asserts both.
"""

from __future__ import annotations

import uuid
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
from ppcway.audit.listing import listing_findings, rival_findings
from ppcway.audit.models import AuditRun
from ppcway.audit.places import Listing
from ppcway.audit.types import AuditReport
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session


def a_listing(**over: Any) -> Listing:
    fields: dict[str, Any] = {
        "place_id": "p1",
        "name": "Alpha Plumbing",
        "address": "12 King St, Mississauga",
        "short_address": "12 King St, Mississauga",
        "category": "Plumber",
        "status": "OPERATIONAL",
        "service_area_only": False,
        "maps_url": "",
        "rating": 4.6,
        "reviews": 120,
        "website": "https://alphaplumbing.ca",
        "phone": "+1 905 555 0100",
        "open_now": None,
        "lat": None,
        "lng": None,
        "photos": 12,
        "hours_set": True,
        "open_24h": False,
        "primary_type": "plumber",
        "types": ("plumber",),
    }
    fields.update(over)
    return Listing(**fields)


def keys(found: list[Any]) -> list[str]:
    return [f.key for f in found]


def test_a_listing_with_everything_set_says_so() -> None:
    found = listing_findings(a_listing(), [])
    assert keys(found) == [
        "listing_reviews",
        "listing_photos",
        "listing_hours",
        "listing_category",
    ]
    assert all(f.status == "good" for f in found)


def test_what_is_missing_is_named_one_thing_at_a_time() -> None:
    found = listing_findings(
        a_listing(
            reviews=0, rating=None, photos=0, hours_set=False, website="", phone="", category=""
        ),
        [],
    )
    assert set(keys(found)) == {
        "listing_reviews",
        "listing_photos",
        "listing_hours",
        "listing_website",
        "listing_phone",
        "listing_category",
    }
    assert all(f.status == "needs_you" for f in found)
    assert all(f.fix for f in found)


def test_the_night_question_is_its_own_check() -> None:
    """Separate from "are your hours set", so a kind can drop one and keep the other."""
    rivals = [a_listing(place_id="r1", open_24h=True), a_listing(place_id="r2", open_24h=True)]
    found = listing_findings(a_listing(), rivals)

    hours = next(f for f in found if f.key == "listing_hours")
    assert hours.status == "good"
    night = next(f for f in found if f.key == "listing_24h")
    assert "open twenty four hours" in night.summary
    assert "two businesses" in night.summary


def test_a_business_already_open_all_night_is_not_told_to_open() -> None:
    rivals = [a_listing(place_id="r1", open_24h=True)]
    found = listing_findings(a_listing(open_24h=True), rivals)
    assert "listing_24h" not in keys(found)


def test_competitors_are_compared_on_what_can_be_seen() -> None:
    rivals = [
        a_listing(place_id="r1", reviews=400, photos=30, rating=4.9),
        a_listing(place_id="r2", reviews=50, photos=2, rating=4.1),
    ]
    found = rival_findings(a_listing(), rivals)
    assert set(keys(found)) == {"rivals_reviews", "rivals_photos"}
    assert "One plumber has more reviews than you" in found[0].title


def test_with_nobody_nearby_there_is_nothing_to_compare() -> None:
    assert rival_findings(a_listing(), []) == []


# --- and the whole point, through the real run ----------------------------


@pytest.fixture
def app_and_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    bare = AuditReport(site="example.ca", started_at=datetime.now(UTC))
    monkeypatch.setattr(api_module, "run_audit", lambda site, settings, on_stage=None: bare)
    monkeypatch.setattr(api_module, "to_pdf", lambda url, **k: b"%PDF-1.4")
    monkeypatch.setattr(api_module, "session_factory", lambda: factory)
    # One listing, and two competitors who never close.
    monkeypatch.setattr(api_module, "place_details", lambda place_id, **k: a_listing())
    monkeypatch.setattr(
        api_module,
        "nearby_rivals",
        lambda mine, **k: [
            a_listing(place_id="r1", open_24h=True),
            a_listing(place_id="r2", open_24h=True),
        ],
    )

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


def stored_keys(factory: sessionmaker[Session], audit_id: str) -> list[str]:
    with factory() as session:
        run = session.get(AuditRun, uuid.UUID(audit_id))
        assert run is not None, "no run"
        assert run.status == "done", run.error
        return [f["key"] for f in (run.report or {}).get("findings", [])]


def run_as(client: TestClient, kind: str) -> str:
    said = client.post(
        "/v1/public/audits",
        json={
            "business_name": "Example",
            "site": "example.ca",
            "kind": kind,
            "place_id": "p1",
        },
    )
    assert said.status_code == 202, said.text
    return str(said.json()["audit_id"])


def test_an_emergency_business_is_told_its_competitors_never_close(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        found = stored_keys(factory, run_as(client, "emergency"))

    assert "listing_24h" in found
    assert "rivals_24h" in found


def test_a_law_firm_is_never_told_any_such_thing(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The same listing, the same competitors, the right advice for the business."""
    app, factory = app_and_db
    with TestClient(app) as client:
        found = stored_keys(factory, run_as(client, "professional"))

    assert "listing_24h" not in found
    assert "rivals_24h" not in found
    # It still gets everything that does apply to it.
    assert "listing_reviews" in found
    assert "listing_hours" in found


def test_an_online_store_is_asked_nothing_about_a_listing_at_all(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        found = stored_keys(factory, run_as(client, "ecommerce"))

    assert not [k for k in found if k.startswith(("listing_", "rivals_"))]
