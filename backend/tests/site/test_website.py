"""The PPCWay script on a merchant's website, end to end.

What arrives from the script is public and untrusted, so a good part of this is
about what it cannot do: get past an unknown key, keep a password or a card
number, bury the real leads under copies. The rest is the merchant's side:
where visits came from, the leads, and a lead marked as a job going to Google
Ads against the click that brought it -- or waiting, with the reason, when
Google is not ready or writes are stopped.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import conversions as conv
from ppcway.ads.models import AdsConnection
from ppcway.api import app as api_module
from ppcway.api.app import create_app
from ppcway.auth.models import UserAccount
from ppcway.auth.sessions import sign_in_existing
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.gateway import send as sending
from ppcway.gateway import switch
from ppcway.gateway.port import Applied, Batch, Refused, Uploaded
from ppcway.org.models import Membership, Role
from ppcway.org.places import home_for
from ppcway.site import jobs
from ppcway.site.collect import key_for, parse, take, where_from
from ppcway.site.models import SiteLead, SiteVisit
from ppcway.site.stats import overview
from ppcway.staff import models as _staff  # noqa: F401 - registers its table

BROWSER = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Safari/604.1"
SITE = "https://alphaplumbing.ca"
CUSTOMER = "2580586343"


@pytest.fixture
def factory() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def _business(session: Session) -> tuple[UserAccount, Any]:
    owner = UserAccount(google_sub="g-owner", email="owner@alphaplumbing.ca", name="Dana")
    session.add(owner)
    session.flush()
    place = home_for(session, owner)
    return owner, place


def _event(key: str, kind: str = "view", **extra: Any) -> Any:
    raw = {"key": key, "t": kind, "v": "visit-0001", "u": "visitor-01", "url": f"{SITE}/"}
    raw.update(extra)
    event = parse(raw)
    assert event is not None
    return event


# --- where a visit came from -------------------------------------------------


@pytest.mark.parametrize(
    ("url", "referrer", "source"),
    [
        (f"{SITE}/?gclid=Cj0KCQ", "https://www.google.com/", "google_ads"),
        (f"{SITE}/?gbraid=0AAAA", "", "google_ads"),
        (f"{SITE}/?utm_source=google&utm_medium=cpc", "", "google_ads"),
        (f"{SITE}/", "https://www.google.ca/", "google"),
        (f"{SITE}/", "https://www.bing.com/search?q=plumber", "bing"),
        (f"{SITE}/?fbclid=IwAR", "https://l.facebook.com/", "facebook"),
        (f"{SITE}/?utm_medium=email&utm_source=newsletter", "", "email"),
        (f"{SITE}/", "https://homestars.com/companies/alpha", "referral"),
        (f"{SITE}/", "", "direct"),
        (f"{SITE}/contact", f"{SITE}/", "direct"),
    ],
)
def test_where_a_visit_came_from(url: str, referrer: str, source: str) -> None:
    assert where_from(url, referrer)["source"] == source


# --- taking events in --------------------------------------------------------


def test_a_visit_counts_its_pages_and_a_form_becomes_a_lead(
    factory: sessionmaker[Session],
) -> None:
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        ad = f"{SITE}/?gclid=Cj0KCQ-test&utm_campaign=Emergency"
        assert take(session, _event(key, url=ad), address="1.2.3.4", user_agent=BROWSER) == "view"
        assert (
            take(session, _event(key, url=f"{SITE}/contact"), address="1.2.3.4", user_agent=BROWSER)
            == "view"
        )
        sent = _event(
            key,
            "lead",
            url=f"{SITE}/contact",
            k="form",
            n="contact",
            f=[
                ["First name", "Sam"],
                ["Last name", "Patel"],
                ["Email", "sam@example.com"],
                ["Phone", "(416) 555-0199"],
                ["Message", "My basement is flooding"],
            ],
        )
        assert take(session, sent, address="1.2.3.4", user_agent=BROWSER) == "lead"

        visit = session.scalars(sa.select(SiteVisit)).one()
        lead = session.scalars(sa.select(SiteLead)).one()
    assert visit.views == 2
    assert visit.source == "google_ads" and visit.campaign == "Emergency"
    assert visit.landing == "/"
    assert lead.name == "Sam Patel"
    assert lead.email == "sam@example.com"
    assert lead.phone == "(416) 555-0199"
    assert lead.source == "google_ads" and lead.gclid == "Cj0KCQ-test"
    assert lead.clicked_at is not None
    assert ["Message", "My basement is flooding"] in lead.fields


def test_a_password_or_a_card_number_is_never_kept(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        sent = _event(
            key,
            "lead",
            k="form",
            f=[
                ["Email", "sam@example.com"],
                ["Password", "hunter2hunter2"],
                ["Card number", "4111 1111 1111 1111"],
                ["Notes", "4111111111111111"],
            ],
        )
        take(session, sent, address="1.2.3.4", user_agent=BROWSER)
        lead = session.scalars(sa.select(SiteLead)).one()
    assert lead.fields == [["Email", "sam@example.com"]]


def test_a_browser_that_asks_not_to_be_tracked_is_counted_but_not_read(
    factory: sessionmaker[Session],
) -> None:
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        take(
            session,
            _event(key, "lead", k="form", p=1, f=[["Email", "sam@example.com"]]),
            address="1.2.3.4",
            user_agent=BROWSER,
        )
        lead = session.scalars(sa.select(SiteLead)).one()
    assert lead.fields == [] and lead.email == ""


def test_a_tapped_phone_number_is_a_call_lead_and_a_second_tap_is_the_same_one(
    factory: sessionmaker[Session],
) -> None:
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        tap = _event(key, "lead", k="call", h="tel:+14165550100")
        assert take(session, tap, address="1.2.3.4", user_agent=BROWSER) == "lead"
        assert take(session, tap, address="1.2.3.4", user_agent=BROWSER) == "repeat"
        lead = session.scalars(sa.select(SiteLead)).one()
    assert lead.kind == "call" and lead.phone == "+14165550100"


def test_unknown_keys_robots_and_junk_are_dropped(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        assert take(session, _event("pw_nobody"), address="", user_agent=BROWSER) == "unknown key"
        assert take(session, _event(key), address="", user_agent="Googlebot/2.1") == "robot"
        assert session.scalar(sa.select(sa.func.count()).select_from(SiteVisit)) == 0
    assert parse({"key": key, "t": "view", "v": "visit-0001", "url": "javascript:alert(1)"}) is None
    assert parse({"key": key, "t": "lead", "v": "visit-0001", "url": SITE, "k": "x"}) is None
    assert parse("not an event") is None


def test_one_visit_cannot_make_more_than_five_leads(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        said = [
            take(
                session,
                _event(key, "lead", k="form", f=[["Message", f"try {n}"]]),
                address="1.2.3.4",
                user_agent=BROWSER,
            )
            for n in range(7)
        ]
    assert said == ["lead"] * 5 + ["visit limit"] * 2


# --- the numbers -------------------------------------------------------------


def test_the_overview_counts_visits_and_leads_by_source_and_leaves_spam_out(
    factory: sessionmaker[Session],
) -> None:
    now = datetime.now(UTC)
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        for n, (url, ref) in enumerate(
            [
                (f"{SITE}/?gclid=a", ""),
                (f"{SITE}/", "https://www.google.ca/"),
                (f"{SITE}/", ""),
            ]
        ):
            take(
                session,
                _event(key, v=f"visit-000{n}", url=url, r=ref),
                address="1.2.3.4",
                user_agent=BROWSER,
                now=now,
            )
        take(
            session,
            _event(key, "lead", v="visit-0000", k="call", h="tel:+14165550100"),
            address="1.2.3.4",
            user_agent=BROWSER,
            now=now,
        )
        take(
            session,
            _event(key, "lead", v="visit-0002", k="form", f=[["Message", "buy cheap pills"]]),
            address="5.6.7.8",
            user_agent=BROWSER,
            now=now,
        )
        spam = session.scalars(sa.select(SiteLead).where(SiteLead.kind == "form")).one()
        spam.status = "spam"
        session.commit()
        said = overview(session, place.id, days=7, now=now)
    assert said["visits"] == 3 and said["leads"] == 1
    assert said["rate"] == 33.3
    assert said["kinds"] == {"form": 0, "call": 1, "email": 0}
    by_source = {row["source"]: (row["visits"], row["leads"]) for row in said["sources"]}
    assert by_source == {"google_ads": (1, 1), "google": (1, 0), "direct": (1, 0)}
    assert len(said["by_day"]) == 7 and said["by_day"][-1]["visits"] == 3


# --- jobs --------------------------------------------------------------------


def _lead(**overrides: Any) -> SiteLead:
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        "organization_id": None,
        "created_at": now - timedelta(days=2),
        "kind": "form",
        "gclid": "Cj0KCQ-test",
        "clicked_at": now - timedelta(days=2),
        "upload": "",
    }
    values.update(overrides)
    return SiteLead(**values)


def test_a_job_from_an_ad_waits_to_be_sent_and_one_without_a_click_says_why() -> None:
    from_ad = _lead()
    jobs.mark(from_ad, status="job", value=450, currency="CAD", by=None, sending=True)
    assert from_ad.upload == "waiting" and from_ad.value == 450

    not_from_ad = _lead(gclid="", clicked_at=None)
    jobs.mark(not_from_ad, status="job", value=450, currency="CAD", by=None, sending=True)
    assert not_from_ad.upload == "no_click"
    assert "did not come from a Google ad" in not_from_ad.upload_note

    too_old = _lead(clicked_at=datetime.now(UTC) - timedelta(days=91))
    jobs.mark(too_old, status="job", value=450, currency="CAD", by=None, sending=True)
    assert too_old.upload == "no_click"

    switched_off = _lead()
    jobs.mark(switched_off, status="job", value=450, currency="CAD", by=None, sending=False)
    assert switched_off.upload == ""


def test_a_job_already_sent_stays_sent() -> None:
    lead = _lead(upload="sent")
    jobs.mark(lead, status="not_job", value=None, currency="", by=None, sending=True)
    assert lead.upload == "sent" and lead.status == "not_job"


def test_the_conversion_google_is_sent() -> None:
    lead = _lead(gbraid="0AAA", value=450.0, currency="CAD", marked_at=datetime.now(UTC))
    lead.id = uuid.uuid4()
    sent = jobs.click_conversion(lead, "customers/1/conversionActions/2")
    assert sent["gclid"] == "Cj0KCQ-test" and "gbraid" not in sent, "one click id, the gclid first"
    assert sent["conversionValue"] == 450.0 and sent["currencyCode"] == "CAD"
    assert sent["orderId"] == str(lead.id)
    assert sent["conversionDateTime"].endswith("+00:00")


def test_what_google_said_about_each_job() -> None:
    now = datetime.now(UTC)
    leads = [
        _lead(upload="waiting", marked_at=now),
        _lead(upload="waiting", marked_at=now),
        _lead(upload="waiting", marked_at=now - timedelta(days=4)),
        _lead(upload="waiting", marked_at=now),
        _lead(upload="waiting", marked_at=now),
    ]
    outcome = jobs.read_outcome(
        leads,
        (True, False, False, False, False),
        {
            1: ("conversionUploadError.TOO_RECENT_EVENT", "too recent"),
            2: ("conversionUploadError.EVENT_NOT_FOUND", "not found"),
            3: ("conversionUploadError.ORDER_ID_ALREADY_IN_USE", "already"),
            4: ("conversionUploadError.UNPARSEABLE_GCLID", "The click id is not valid."),
        },
        now=now,
    )
    assert [lead.upload for lead in leads] == ["sent", "waiting", "failed", "sent", "failed"]
    assert leads[4].upload_note == "The click id is not valid."
    assert outcome == jobs.Outcome(sent=2, later=1, failed=2)


def test_old_leads_and_visits_are_deleted(factory: sessionmaker[Session]) -> None:
    now = datetime.now(UTC)
    with factory() as session:
        _, place = _business(session)
        key = key_for(session, place.id).key
        old = now - jobs.KEEP - timedelta(days=1)
        take(session, _event(key, v="visit-old1"), address="", user_agent=BROWSER, now=old)
        take(
            session,
            _event(key, "lead", v="visit-old1", k="call", h="tel:1"),
            address="",
            user_agent=BROWSER,
            now=old,
        )
        take(session, _event(key, v="visit-new1"), address="", user_agent=BROWSER, now=now)
        assert jobs.purge(session, now=now) == {"leads": 1, "visits": 1}
        assert session.scalar(sa.select(sa.func.count()).select_from(SiteVisit)) == 1


# --- through the endpoints the Website screen calls -------------------------


@dataclass
class FakeGoogle:
    """Google Ads, as far as these tests need it: creating the jobs action and
    taking uploads, with what each was handed kept for the asserts."""

    batches: list[Batch] = field(default_factory=list)
    uploads: list[tuple[dict[str, Any], ...]] = field(default_factory=list)
    refuse_upload: str = ""

    def mutate(self, batch: Batch) -> Applied:
        self.batches.append(batch)
        return Applied(landed=(f"customers/{CUSTOMER}/conversionActions/777",), operations_used=1)

    def upload_clicks(self, customer_id: str, conversions: tuple[dict[str, Any], ...]) -> Uploaded:
        self.uploads.append(conversions)
        if self.refuse_upload:
            return Uploaded(
                landed=tuple(False for _ in conversions),
                refused=tuple(
                    Refused(at=i, code=self.refuse_upload, message="no")
                    for i in range(len(conversions))
                ),
            )
        return Uploaded(landed=tuple(True for _ in conversions))


@pytest.fixture
def world(
    monkeypatch: pytest.MonkeyPatch, factory: sessionmaker[Session]
) -> Iterator[tuple[FastAPI, dict[str, str], FakeGoogle, sessionmaker[Session]]]:
    google = FakeGoogle()
    key = Fernet.generate_key()
    monkeypatch.setattr(api_module, "fresh_access_token", lambda *a, **k: "an-hour")
    monkeypatch.setattr(sending, "doors", lambda settings: lambda connection: google)
    monkeypatch.setattr(conv, "measurement", lambda *a, **k: {"actions": []})
    app = create_app(
        Settings(
            environment="test",
            app_base_url="https://app.ppcway.com",
            google_oauth_client_id="test-client",
            google_oauth_client_secret=SecretStr("test-secret"),
            google_ads_developer_token=SecretStr("test-token"),
            google_oauth_token_key=SecretStr(key.decode()),
            ads_writes_enabled=True,
            sync_key=SecretStr("the-sync-key"),
        )
    )

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    with factory() as session:
        owner, place = _business(session)
        session.add(
            AdsConnection(
                account_id=owner.id,
                organization_id=place.id,
                ciphertext=Fernet(key).encrypt(b"refresh").decode(),
                customer_id=CUSTOMER,
                customer_name="Alpha Plumbing",
                currency="CAD",
                time_zone="America/Toronto",
                account_status="ENABLED",
            )
        )
        session.commit()
        token = sign_in_existing(session, owner)
    yield app, {"x-session-token": token}, google, factory


def _collect(client: TestClient, body: dict[str, Any]) -> int:
    return client.post(
        "/v1/site/collect",
        content=json.dumps(body),
        headers={"x-visitor-address": "1.2.3.4", "x-visitor-agent": BROWSER},
    ).status_code


def test_install_collect_and_read_back(world: Any) -> None:
    app, owner, _, _ = world
    with TestClient(app) as client:
        setup = client.get("/v1/site", headers=owner).json()
        assert setup["installed"] is False
        assert setup["snippet"] == (
            f'<script async src="https://app.ppcway.com/t.js" data-key="{setup["key"]}"></script>'
        )
        key = setup["key"]
        assert _collect(client, {"key": key, "t": "view", "v": "visit-0001", "url": SITE}) == 204
        assert (
            _collect(
                client,
                {
                    "key": key,
                    "t": "lead",
                    "v": "visit-0001",
                    "url": f"{SITE}/contact",
                    "k": "form",
                    "f": [["Email", "sam@example.com"]],
                },
            )
            == 204
        )
        # Junk and unknown keys get the same empty answer.
        assert (
            _collect(client, {"key": "pw_nobody", "t": "view", "v": "x" * 10, "url": SITE}) == 204
        )
        assert client.post("/v1/site/collect", content=b"{not json").status_code == 204

        assert client.get("/v1/site", headers=owner).json()["installed"] is True
        stats = client.get("/v1/site/stats?days=7", headers=owner).json()
        assert stats["visits"] == 1 and stats["leads"] == 1
        leads = client.get("/v1/site/leads", headers=owner).json()["leads"]
        assert leads[0]["email"] == "sam@example.com"


def test_jobs_go_to_google_ads_against_their_click(world: Any) -> None:
    app, owner, google, _ = world
    with TestClient(app) as client:
        key = client.get("/v1/site", headers=owner).json()["key"]
        _collect(client, {"key": key, "t": "view", "v": "visit-0001", "url": f"{SITE}/?gclid=abc"})
        _collect(
            client,
            {"key": key, "t": "lead", "v": "visit-0001", "url": SITE, "k": "call", "h": "tel:1"},
        )
        lead_id = client.get("/v1/site/leads", headers=owner).json()["leads"][0]["id"]

        turned_on = client.post("/v1/site/settings", json={"send_jobs": True}, headers=owner)
        assert turned_on.status_code == 200, turned_on.text
        assert turned_on.json()["job_action"].endswith("/conversionActions/777")
        (made,) = google.batches
        assert made.operations[0].fields["type"] == "UPLOAD_CLICKS"
        assert made.operations[0].fields["name"] == jobs.JOB_ACTION_NAME

        marked = client.post(
            f"/v1/site/leads/{lead_id}", json={"status": "job", "value": "450"}, headers=owner
        )
    assert marked.status_code == 200, marked.text
    assert marked.json()["upload"] == "sent"
    ((sent,),) = google.uploads
    assert sent["gclid"] == "abc" and sent["conversionValue"] == 450.0
    assert sent["currencyCode"] == "CAD" and sent["orderId"] == lead_id


def test_with_writes_stopped_a_job_waits_and_says_why(world: Any) -> None:
    app, owner, google, factory = world
    with TestClient(app) as client:
        key = client.get("/v1/site", headers=owner).json()["key"]
        _collect(client, {"key": key, "t": "view", "v": "visit-0001", "url": f"{SITE}/?gclid=abc"})
        _collect(
            client,
            {"key": key, "t": "lead", "v": "visit-0001", "url": SITE, "k": "call", "h": "tel:1"},
        )
        lead_id = client.get("/v1/site/leads", headers=owner).json()["leads"][0]["id"]
        client.post("/v1/site/settings", json={"send_jobs": True}, headers=owner)
        with factory() as session:
            switch.set_gate(session, is_open=False, because="paused for a test", set_by=None)
        marked = client.post(f"/v1/site/leads/{lead_id}", json={"status": "job"}, headers=owner)
    assert marked.json()["upload"] == "waiting"
    assert marked.json()["upload_note"]
    assert google.uploads == []


def test_google_not_ready_yet_leaves_the_job_for_the_hourly_pass(
    world: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, owner, google, factory = world
    google.refuse_upload = "conversionUploadError.TOO_RECENT_CONVERSION_ACTION"
    with TestClient(app) as client:
        key = client.get("/v1/site", headers=owner).json()["key"]
        _collect(client, {"key": key, "t": "view", "v": "visit-0001", "url": f"{SITE}/?gclid=abc"})
        _collect(
            client,
            {"key": key, "t": "lead", "v": "visit-0001", "url": SITE, "k": "call", "h": "tel:1"},
        )
        lead_id = client.get("/v1/site/leads", headers=owner).json()["leads"][0]["id"]
        client.post("/v1/site/settings", json={"send_jobs": True}, headers=owner)
        marked = client.post(f"/v1/site/leads/{lead_id}", json={"status": "job"}, headers=owner)
        assert marked.json()["upload"] == "waiting"

        # An hour later Google is ready, and the scheduler's pass sends it.
        google.refuse_upload = ""
        monkeypatch.setattr(api_module, "session_factory", lambda: factory)
        assert client.post("/v1/internal/site").status_code == 403
        passed = client.post("/v1/internal/site", headers={"x-sync-key": "the-sync-key"})
        assert passed.status_code == 200, passed.text
        assert passed.json()["sent"] == 1
        lead = client.get("/v1/site/leads", headers=owner).json()["leads"][0]
    assert lead["upload"] == "sent"


def test_somebody_who_cannot_approve_cannot_mark_jobs(world: Any) -> None:
    app, owner, _, factory = world
    with factory() as session:
        member = UserAccount(google_sub="g-member", email="member@alphaplumbing.ca", name="M")
        session.add(member)
        session.flush()
        place_id = session.scalars(sa.select(Membership.organization_id)).first()
        session.add(Membership(organization_id=place_id, account_id=member.id, role=Role.MEMBER))
        session.commit()
        token = {"x-session-token": sign_in_existing(session, member)}
    with TestClient(app) as client:
        key = client.get("/v1/site", headers=owner).json()["key"]
        _collect(
            client,
            {"key": key, "t": "lead", "v": "visit-0001", "url": SITE, "k": "call", "h": "tel:1"},
        )
        lead_id = client.get("/v1/site/leads", headers=token).json()["leads"][0]["id"]
        refused = client.post(f"/v1/site/leads/{lead_id}", json={"status": "job"}, headers=token)
        settings = client.post("/v1/site/settings", json={"send_jobs": True}, headers=token)
    assert refused.status_code == 403
    assert settings.status_code == 403


def test_the_script_is_told_only_the_conversions_the_merchant_chose(world: Any) -> None:
    app, owner, _, _ = world
    with TestClient(app) as client:
        key = client.get("/v1/site", headers=owner).json()["key"]
        assert client.get(f"/v1/site/config?k={key}").json() == {"tag": "", "form": "", "call": ""}
        bad = client.post("/v1/site/settings", json={"form_send_to": "<script>"}, headers=owner)
        assert bad.status_code == 422
        client.post(
            "/v1/site/settings", json={"form_send_to": "AW-123456789/AbCdEfGh"}, headers=owner
        )
        said = client.get(f"/v1/site/config?k={key}").json()
    assert said == {"tag": "AW-123456789", "form": "AW-123456789/AbCdEfGh", "call": ""}
