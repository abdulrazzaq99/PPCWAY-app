"""Which audits are due, and which parts of them are worth paying for again.

The cadence is the whole feature: a website read daily, the parts Google
charges for read weekly, and nothing started twice because a clock fired twice.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.audit.watch import due_audits
from ppcway.auth.models import UserAccount  # noqa: F401 - a request points at one
from ppcway.db.base import Base
from ppcway.org.models import Organization

#: Already tidy, which is how a run is stored: the endpoint that starts an audit
#: normalises the address before writing it. Only the request keeps the typing.
SITE = "https://alphaplumbing.ca/"
NOW = datetime(2026, 10, 20, 2, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def place(db: DbSession, name: str = "Alpha Plumbing") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    return org


def asked_for(db: DbSession, org: Organization | None, site: str = SITE) -> AuditRequest:
    request = AuditRequest(
        name="Dana",
        email="dana@alphaplumbing.ca",
        phone="",
        business_name="Alpha Plumbing",
        site=site,
        consent_text="yes",
        organization_id=org.id if org else None,
    )
    db.add(request)
    db.commit()
    return request


def ran(
    db: DbSession,
    request: AuditRequest,
    *,
    when: datetime,
    status: str = "done",
    demand: bool = False,
) -> AuditRun:
    row = AuditRun(
        request_id=request.id,
        site=request.site,
        status=status,
        report={"findings": [], **({"demand": {"searches": 100}} if demand else {})},
        finished_at=when if status == "done" else None,
        created_at=when,
    )
    db.add(row)
    db.commit()
    return row


def test_a_site_never_audited_is_due(db: DbSession) -> None:
    org = place(db)
    asked_for(db, org)

    due = due_audits(db, now=NOW)

    assert [d.site for d in due] == [SITE]
    assert due[0].because == "never audited"
    assert due[0].with_demand is True


def test_a_site_read_today_is_not_due(db: DbSession) -> None:
    org = place(db)
    request = asked_for(db, org)
    ran(db, request, when=NOW - timedelta(hours=6), demand=True)

    assert due_audits(db, now=NOW) == []


def test_a_site_read_yesterday_is_due_again(db: DbSession) -> None:
    org = place(db)
    request = asked_for(db, org)
    ran(db, request, when=NOW - timedelta(days=2), demand=True)

    due = due_audits(db, now=NOW)

    assert [d.site for d in due] == [SITE]
    assert "last read" in due[0].because


def test_the_part_google_charges_for_is_re_read_weekly_not_nightly(
    db: DbSession,
) -> None:
    org = place(db)
    request = asked_for(db, org)
    # Read two days ago, with the paid part in it.
    ran(db, request, when=NOW - timedelta(days=2), demand=True)

    assert due_audits(db, now=NOW)[0].with_demand is False

    # Eight days later, the paid part is stale too.
    later = NOW + timedelta(days=8)
    assert due_audits(db, now=later)[0].with_demand is True


def test_a_run_already_in_flight_is_left_alone(db: DbSession) -> None:
    org = place(db)
    request = asked_for(db, org)
    ran(db, request, when=NOW - timedelta(days=3))
    ran(db, request, when=NOW - timedelta(minutes=5), status="running")

    assert due_audits(db, now=NOW) == []


def test_a_site_belonging_to_nobody_is_not_audited_on_a_schedule(
    db: DbSession,
) -> None:
    # Somebody ran the free audit without signing in. There is no business to
    # show a history to, so there is nothing to re-run for.
    asked_for(db, None)

    assert due_audits(db, now=NOW) == []


def test_two_businesses_at_the_same_address_are_each_due(db: DbSession) -> None:
    mine = place(db, "Alpha Plumbing")
    theirs = place(db, "An agency")
    asked_for(db, mine)
    asked_for(db, theirs)

    due = due_audits(db, now=NOW)

    assert len(due) == 2
    assert {d.organization_id for d in due} == {mine.id, theirs.id}


def test_only_so_many_are_started_in_one_pass(db: DbSession) -> None:
    for n in range(5):
        asked_for(db, place(db, f"Business {n}"), site=f"https://site{n}.ca")

    assert len(due_audits(db, now=NOW, most=3)) == 3


def test_a_run_interrupted_hours_ago_stops_blocking_its_site(db: DbSession) -> None:
    # A Cloud Run instance recycled mid-audit leaves a row saying "running" that
    # nothing will finish. Without this the site is never audited again, and the
    # only symptom is silence.
    org = place(db)
    request = asked_for(db, org)
    ran(db, request, when=NOW - timedelta(days=3))
    ran(db, request, when=NOW - timedelta(hours=5), status="running")

    due = due_audits(db, now=NOW)

    assert [d.site for d in due] == [SITE]


def test_one_website_typed_two_ways_is_one_audit(db: DbSession) -> None:
    # Somebody pasted their own address out of a Google Ads report, with the
    # tracking parameter still on it. It is the same website.
    org = place(db)
    asked_for(db, org, site="alpha-plumbing.ca/?utm_campaign=gmb")
    asked_for(db, org, site="https://alpha-plumbing.ca")

    due = due_audits(db, now=NOW)

    assert [d.site for d in due] == ["https://alpha-plumbing.ca/"]
