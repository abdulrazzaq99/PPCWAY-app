"""Launching a drafted campaign: the switches, Google's check, and the record.

Google is faked at the door. What these hold is the order -- switches, quota,
Google checks it, then it is created -- and that what the merchant is told and
what the draft records are what actually happened.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.builder.campaign import CampaignPlan, Place, Theme
from ppcway.builder.launch import launch_draft
from ppcway.builder.models import CampaignDraft
from ppcway.db.base import Base
from ppcway.gateway import quota, switch
from ppcway.gateway.port import Created, GoogleRefused, Together
from ppcway.org.models import Organization

CUSTOMER = "2580586343"
NOW = datetime.now(UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def plan(**over: object) -> CampaignPlan:
    fields: dict[str, object] = {
        "name": "PDF tools",
        "daily_budget": 20.0,
        "currency": "USD",
        "final_url": "https://pdfezy.com/",
        "places": [Place("geoTargetConstants/2616", "Poland", "Country")],
        "language": Place("languageConstants/1000", "English"),
        "themes": [
            Theme(
                name="pdf to word",
                keywords=[{"text": "pdf to word", "monthly": 9000}],
                headlines=[f"Headline {n}" for n in range(10)],
                descriptions=["One description.", "Another description."],
            )
        ],
        "not_political": True,
        "ai_written": True,
    }
    fields.update(over)
    return CampaignPlan(**fields)  # type: ignore[arg-type]


def drafted(db: sessionmaker[Session], **over: object) -> uuid.UUID:
    with db() as session:
        place = Organization(name="PDFezy")
        person = UserAccount(email="owner@pdfezy.com", name="Owner")
        session.add_all([place, person])
        session.flush()
        row = CampaignDraft(
            organization_id=place.id,
            customer_id=CUSTOMER,
            created_by=person.id,
            plan=plan(**over).as_dict(),
        )
        session.add(row)
        session.commit()
        return row.id


class Google:
    """A door that records each request and answers as told."""

    def __init__(self, refuse_check: str = "", refuse_create: str = "") -> None:
        self.sent: list[Together] = []
        self.refuse_check = refuse_check
        self.refuse_create = refuse_create

    def mutate_together(self, together: Together) -> Created:
        self.sent.append(together)
        if together.validate_only:
            if self.refuse_check:
                raise GoogleRefused(self.refuse_check)
            return Created(names=(), checked_only=True)
        if self.refuse_create:
            raise GoogleRefused(self.refuse_create)
        return Created(
            names=tuple(
                f"customers/{CUSTOMER}/campaigns/777"
                if op.resource_type == "campaign"
                else f"customers/{CUSTOMER}/{op.resource_type}s/{n}"
                for n, op in enumerate(together.operations)
            )
        )


def _launch(
    db: sessionmaker[Session], draft_id: uuid.UUID, google: Google, *, gate_open: bool = True
) -> object:
    with db() as session:
        draft = session.get(CampaignDraft, draft_id)
        assert draft is not None
        return launch_draft(
            session, draft, door=google, gate_open=gate_open, account_id=None, now=NOW
        )


def _row(db: sessionmaker[Session], draft_id: uuid.UUID) -> CampaignDraft:
    with db() as session:
        row = session.get(CampaignDraft, draft_id)
        assert row is not None
        return row


def test_google_checks_the_whole_campaign_and_then_it_is_created(
    db: sessionmaker[Session],
) -> None:
    draft = drafted(db)
    google = Google()
    said = _launch(db, draft, google)
    assert said.live is True  # type: ignore[attr-defined]
    assert [t.validate_only for t in google.sent] == [True, False], "checked first, then made"
    assert google.sent[0].operations == google.sent[1].operations, "the same request both times"
    row = _row(db, draft)
    assert row.status == "launched"
    assert row.campaign_resource == f"customers/{CUSTOMER}/campaigns/777"
    assert row.outcome is not None and len(row.outcome["created"]) == google.sent[1].how_many
    assert "drafted by Otto" in said.words  # type: ignore[attr-defined]


def test_a_refusal_at_the_check_creates_nothing_and_says_google_s_reason(
    db: sessionmaker[Session],
) -> None:
    draft = drafted(db)
    google = Google(refuse_check="Google refused an ad: Too many exclamation marks (policyError.X)")
    said = _launch(db, draft, google)
    assert said.live is False  # type: ignore[attr-defined]
    assert "Too many exclamation marks" in said.words  # type: ignore[attr-defined]
    assert "Nothing was created" in said.words  # type: ignore[attr-defined]
    assert [t.validate_only for t in google.sent] == [True], "the real request never went"
    row = _row(db, draft)
    assert row.status == "draft", "still there to be changed and tried again"
    assert row.outcome is not None and "exclamation" in row.outcome["refused"]


def test_nothing_is_sent_while_writes_are_off(db: sessionmaker[Session]) -> None:
    draft = drafted(db)
    google = Google()
    said = _launch(db, draft, google, gate_open=False)
    assert said.live is False  # type: ignore[attr-defined]
    assert "not writing to Google Ads" in said.words  # type: ignore[attr-defined]
    assert google.sent == []


def test_a_stop_on_the_account_holds_a_launch_too(db: sessionmaker[Session]) -> None:
    """ "Stop every write" has to mean every write, a merchant's own included."""
    draft = drafted(db)
    with db() as session:
        switch.stop(session, customer_id=CUSTOMER, because="Checking a billing problem.")
    google = Google()
    said = _launch(db, draft, google)
    assert "billing problem" in said.words  # type: ignore[attr-defined]
    assert google.sent == []


def test_what_the_plan_is_missing_is_said_before_google_is_asked(
    db: sessionmaker[Session],
) -> None:
    draft = drafted(db, not_political=False)
    google = Google()
    said = _launch(db, draft, google)
    assert said.live is False  # type: ignore[attr-defined]
    assert "political advertising" in said.words  # type: ignore[attr-defined]
    assert google.sent == []


def test_a_launch_is_counted_against_the_day(db: sessionmaker[Session]) -> None:
    draft = drafted(db)
    google = Google()
    _launch(db, draft, google)
    with db() as session:
        used = quota.room_today(session, CUSTOMER, today=NOW.date()).used
    assert used == google.sent[1].how_many


def test_a_full_day_creates_nothing(db: sessionmaker[Session]) -> None:
    draft = drafted(db)
    with db() as session:
        quota.spend(session, CUSTOMER, quota.A_DAY, today=NOW.date())
        session.commit()
    google = Google()
    said = _launch(db, draft, google)
    assert "allowance" in said.words  # type: ignore[attr-defined]
    assert google.sent == []


def test_launching_twice_creates_one_campaign(db: sessionmaker[Session]) -> None:
    draft = drafted(db)
    google = Google()
    _launch(db, draft, google)
    again = _launch(db, draft, google)
    assert again.words == "That campaign is already live."  # type: ignore[attr-defined]
    assert len(google.sent) == 2, "only the first launch's check and create"
