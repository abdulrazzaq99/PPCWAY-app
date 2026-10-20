"""The six things worth interrupting somebody for, and the ones that are not.

Alerts are the part of a product that teaches people to ignore it, so most of
these tests are about silence: the quiet account, the small jump, the second
look at the same refused ad.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, CampaignDay, MirrorAd, MirrorCampaign, SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.mail.alerts import AlertSent, look, post_alerts
from ppcway.mail.send import Post
from ppcway.org.models import Organization

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
TODAY = NOW.date()
LIVE = Post(sender="PPCway <hello@ppcway.com>", provider="resend", api_key="key")


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def provider(status: int = 200) -> tuple[httpx.Client, list[dict[str, object]]]:
    sent: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(status, json={"id": "abc"} if status < 300 else {"message": "no"})

    return httpx.Client(transport=httpx.MockTransport(handle)), sent


def settings() -> Settings:
    return Settings(
        email_provider="resend",
        email_from="PPCway <hello@ppcway.com>",
        app_base_url="https://app.ppcway.com",
    )


def connected(db: DbSession, *, confirmed: bool = True) -> AdsConnection:
    org = Organization(name="Alpha Plumbing")
    db.add(org)
    db.commit()
    person = UserAccount(
        email="dana@alphaplumbing.ca",
        name="Dana Reyes",
        email_verified_at=NOW if confirmed else None,
    )
    db.add(person)
    db.commit()
    connection = AdsConnection(
        account_id=person.id,
        organization_id=org.id,
        ciphertext="x",
        customer_id="1",
        customer_name="Alpha Plumbing",
        currency="CAD",
    )
    db.add(connection)
    db.add(
        MirrorCampaign(
            customer_id="1",
            resource_name="customers/1/campaigns/11",
            campaign_id="11",
            name="Emergency plumbing",
            status="ENABLED",
            budget_micros=20 * MICRO,
        )
    )
    db.commit()
    return connection


def day(db: DbSession, on: date, *, cost: float, leads: float = 0.0) -> None:
    db.add(
        CampaignDay(
            customer_id="1",
            campaign_id="11",
            day=on,
            cost_micros=round(cost * MICRO),
            forms=leads,
            conversions=leads,
            clicks=10,
            impressions=100,
        )
    )
    db.commit()


def test_a_spend_that_doubled_yesterday_is_worth_saying(db: DbSession) -> None:
    connection = connected(db)
    for back in range(2, 16):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=1)
    day(db, TODAY - timedelta(days=1), cost=120.0, leads=1)

    alarms = look(db, connection, now=NOW)

    jump = next(a for a in alarms if a.kind == "spend_jump")
    assert "$120.00" in jump.subject
    assert "$30.00 a day" in jump.lines[1]


def test_an_ordinary_day_is_not_an_alert(db: DbSession) -> None:
    connection = connected(db)
    for back in range(1, 16):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=1)

    assert [a.kind for a in look(db, connection, now=NOW)] == []


def test_a_few_dollars_doubling_is_still_a_few_dollars(db: DbSession) -> None:
    connection = connected(db)
    for back in range(2, 16):
        day(db, TODAY - timedelta(days=back), cost=2.0, leads=1)
    day(db, TODAY - timedelta(days=1), cost=8.0, leads=1)

    assert [a.kind for a in look(db, connection, now=NOW)] == []


def test_leads_stopping_is_said_with_what_it_used_to_bring(db: DbSession) -> None:
    connection = connected(db)
    for back in range(4, 11):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=1)
    for back in range(1, 4):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=0)

    stopped = next(a for a in look(db, connection, now=NOW) if a.kind == "leads_stopped")

    assert "no enquiries for three days" in stopped.subject
    assert "$90.00" in stopped.lines[0]
    assert "it counted 7" in stopped.lines[1]
    assert "form that has stopped working" in stopped.lines[2]


def test_an_account_that_never_brought_leads_cannot_have_stopped(db: DbSession) -> None:
    connection = connected(db)
    for back in range(1, 11):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=0)

    assert [a.kind for a in look(db, connection, now=NOW)] == []


def test_a_refused_ad_is_named_with_its_campaign(db: DbSession) -> None:
    connection = connected(db)
    db.add(
        MirrorAd(
            customer_id="1",
            resource_name="customers/1/adGroupAds/21~41",
            ad_id="41",
            ad_group_id="21",
            campaign_id="11",
            status="ENABLED",
            approval="DISAPPROVED",
            headlines=["24 hour plumber"],
        )
    )
    db.commit()

    refused = next(a for a in look(db, connection, now=NOW) if a.kind == "ad_refused")

    assert "Emergency plumbing" in refused.subject
    assert "24 hour plumber" in refused.lines[0]


def test_three_failed_syncs_in_a_row_is_our_fault_said_out_loud(db: DbSession) -> None:
    connection = connected(db)
    for back in range(3):
        db.add(
            SyncRun(
                customer_id="1",
                kind="today",
                status="failed",
                trouble="That permission was refused",
                started_at=NOW - timedelta(hours=back + 1),
            )
        )
    db.commit()

    failing = next(a for a in look(db, connection, now=NOW) if a.kind == "sync_failing")

    assert "cannot read your Google Ads account" in failing.subject
    assert "That permission was refused" in failing.lines[1]
    assert "nothing of yours is lost" in failing.lines[2]


def test_two_failures_and_a_success_is_not_a_fault(db: DbSession) -> None:
    connection = connected(db)
    db.add(SyncRun(customer_id="1", kind="today", status="failed", started_at=NOW))
    db.add(
        SyncRun(customer_id="1", kind="today", status="done", started_at=NOW - timedelta(hours=1))
    )
    db.add(
        SyncRun(customer_id="1", kind="today", status="failed", started_at=NOW - timedelta(hours=2))
    )
    db.commit()

    assert [a.kind for a in look(db, connection, now=NOW)] == []


def test_a_permission_that_has_ended_silences_everything_else(db: DbSession) -> None:
    connection = connected(db)
    for back in range(2, 16):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=1)
    day(db, TODAY - timedelta(days=1), cost=300.0)
    connection.revoked_at = NOW
    db.commit()

    alarms = look(db, connection, now=NOW)

    assert [a.kind for a in alarms] == ["permission_gone"]
    assert "Connect again" in alarms[0].todo


def test_a_check_that_was_good_and_is_not_any_more_is_an_alert(db: DbSession) -> None:
    connection = connected(db)
    asked = AuditRequest(
        name="Dana",
        email="dana@alphaplumbing.ca",
        phone="",
        business_name="Alpha Plumbing",
        site="https://alphaplumbing.ca",
        consent_text="yes",
        organization_id=connection.organization_id,
    )
    db.add(asked)
    db.commit()
    for when, status in (
        (NOW - timedelta(days=1), "good"),
        (NOW, "needs_you"),
    ):
        db.add(
            AuditRun(
                request_id=asked.id,
                site="https://alphaplumbing.ca",
                status="done",
                report={
                    "findings": [
                        {
                            "key": "counting",
                            "title": "Counting calls and forms",
                            "status": status,
                            "summary": "Nothing tells Google when somebody calls.",
                        }
                    ]
                },
                finished_at=when,
            )
        )
    db.commit()

    dropped = next(a for a in look(db, connection, now=NOW) if a.kind == "score_dropped")

    assert "alphaplumbing.ca" in dropped.subject
    assert "Counting calls and forms" in dropped.lines[0]
    assert dropped.about == "counting"


def test_the_same_thing_is_not_said_twice_in_a_day(db: DbSession) -> None:
    connected(db)
    for back in range(2, 16):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=1)
    day(db, TODAY - timedelta(days=1), cost=120.0, leads=1)
    client, sent = provider()

    with client:
        first = post_alerts(db, settings(), now=NOW, post=LIVE, client=client)
        second = post_alerts(db, settings(), now=NOW + timedelta(hours=1), post=LIVE, client=client)

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["held"] == 1
    assert len(sent) == 1
    assert db.scalars(sa.select(AlertSent)).one().kind == "spend_jump"


def test_an_unconfirmed_address_is_never_alerted(db: DbSession) -> None:
    connected(db, confirmed=False)
    for back in range(2, 16):
        day(db, TODAY - timedelta(days=back), cost=30.0, leads=1)
    day(db, TODAY - timedelta(days=1), cost=120.0, leads=1)
    client, sent = provider()

    with client:
        counts = post_alerts(db, settings(), now=NOW, post=LIVE, client=client)

    assert counts == {"sent": 0, "failed": 0, "held": 0, "skipped": 1}
    assert sent == []
