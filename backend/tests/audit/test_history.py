"""The audit over time: the line, the markers, and what moved since last time.

One reading is a number. Two are an answer, and the answer a small business
most needs is "did the thing I paid somebody to fix actually get fixed".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.audit.history import score_history, score_of, what_changed
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.auth.models import UserAccount  # noqa: F401 - a request points at one
from ppcway.db.base import Base
from ppcway.org.models import Organization

SITE = "https://alphaplumbing.ca"
NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def findings(counting: str, speed: str = "good") -> dict[str, object]:
    return {
        "findings": [
            {
                "key": "counting",
                "title": "Counting calls and forms",
                "status": counting,
                "summary": "Nothing tells Google when somebody calls.",
            },
            {
                "key": "speed",
                "title": "Speed on a phone",
                "status": speed,
                "summary": "Nine seconds.",
            },
            {"key": "mobile", "title": "Works on a phone", "status": "unknown", "summary": ""},
        ]
    }


def place(db: DbSession, name: str = "Alpha Plumbing") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    return org


def run(
    db: DbSession,
    org: Organization,
    *,
    when: datetime,
    counting: str,
    speed: str = "good",
    kind: str = "asked",
) -> AuditRun:
    asked = AuditRequest(
        name="Dana",
        email="dana@alphaplumbing.ca",
        phone="",
        business_name="Alpha Plumbing",
        site=SITE,
        consent_text="yes",
        organization_id=org.id,
    )
    db.add(asked)
    db.commit()
    row = AuditRun(
        request_id=asked.id,
        site=SITE,
        status="done",
        kind=kind,
        report=findings(counting, speed),
        finished_at=when,
    )
    db.add(row)
    db.commit()
    return row


def test_the_score_counts_only_the_checks_it_could_judge(db: DbSession) -> None:
    org = place(db)
    row = run(db, org, when=NOW, counting="needs_you")

    # Two checks could be judged; one of them is good.
    assert score_of(row) == 50


def test_the_history_is_oldest_first_with_the_fix_marked_where_it_landed(
    db: DbSession,
) -> None:
    org = place(db)
    run(db, org, when=NOW - timedelta(days=2), counting="needs_you")
    run(db, org, when=NOW - timedelta(days=1), counting="needs_you")
    run(db, org, when=NOW, counting="good", kind="scheduled")

    points = score_history(db, SITE, organization_id=org.id)

    assert [p.score for p in points] == [50, 50, 100]
    assert points[0].fixed == []
    assert points[1].fixed == []
    assert points[2].fixed == ["Counting calls and forms"]
    assert points[2].kind == "scheduled"
    assert points[2].needs == 0


def test_something_that_breaks_is_marked_too(db: DbSession) -> None:
    org = place(db)
    run(db, org, when=NOW - timedelta(days=1), counting="good")
    run(db, org, when=NOW, counting="needs_you")

    points = score_history(db, SITE, organization_id=org.id)

    assert points[1].broke == ["Counting calls and forms"]
    assert points[1].fixed == []


def test_what_changed_names_what_was_fixed_and_what_is_still_waiting(
    db: DbSession,
) -> None:
    org = place(db)
    run(db, org, when=NOW - timedelta(days=1), counting="needs_you", speed="needs_you")
    run(db, org, when=NOW, counting="good", speed="needs_you")

    changed = what_changed(db, SITE, organization_id=org.id)

    assert changed.first is False
    assert changed.quiet is False
    assert [f["title"] for f in changed.fixed] == ["Counting calls and forms"]
    assert [f["title"] for f in changed.still] == ["Speed on a phone"]
    assert changed.broke == []
    assert changed.score == 50
    assert changed.score_before == 0


def test_a_quiet_week_says_so_rather_than_showing_nothing(db: DbSession) -> None:
    org = place(db)
    run(db, org, when=NOW - timedelta(days=1), counting="needs_you")
    run(db, org, when=NOW, counting="needs_you")

    changed = what_changed(db, SITE, organization_id=org.id)

    assert changed.quiet is True
    assert [f["title"] for f in changed.still] == ["Counting calls and forms"]


def test_the_first_reading_does_not_pretend_to_compare(db: DbSession) -> None:
    org = place(db)
    run(db, org, when=NOW, counting="needs_you")

    changed = what_changed(db, SITE, organization_id=org.id)

    assert changed.first is True
    assert changed.fixed == []
    assert changed.score_before is None
    assert [f["title"] for f in changed.still] == ["Counting calls and forms"]


def test_another_business_auditing_the_same_address_sees_its_own_history(
    db: DbSession,
) -> None:
    mine = place(db, "Alpha Plumbing")
    theirs = place(db, "An agency")
    run(db, mine, when=NOW - timedelta(days=1), counting="needs_you")
    run(db, mine, when=NOW, counting="good")
    run(db, theirs, when=NOW, counting="needs_you")

    assert len(score_history(db, SITE, organization_id=mine.id)) == 2
    assert len(score_history(db, SITE, organization_id=theirs.id)) == 1
