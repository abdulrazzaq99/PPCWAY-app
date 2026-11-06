"""R1 against what counts as a lead, not against every conversion.

An account that counts page views has a "conversion" on every search with a
click, so R1 -- which offers to exclude searches that brought no leads -- never
fired there. These hold it to leads, to the safe fallback where a day was not
split, and to standing down on an account that counts no enquiries at all.

Dates come from the clock, never pinned: a pinned day stops being inside the
window the moment the calendar moves past it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, CampaignDay, MirrorAd, SearchTermDay, SyncRun, term_key
from ppcway.auth.models import UserAccount  # noqa: F401 - a foreign key target
from ppcway.db.base import Base
from ppcway.org.models import Organization  # noqa: F401 - a foreign key target
from ppcway.rules.engine import Pass, run
from ppcway.rules.inbox import cards_for

NOW = datetime.now(UTC)
TODAY = NOW.date()


@pytest.fixture
def db() -> Iterator[DbSession]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id="1",
                kind="today",
                status="done",
                started_at=NOW - timedelta(hours=3),
                finished_at=NOW - timedelta(hours=2),
            )
        )
        session.commit()
        yield session


def spent(db: DbSession, *, calls: float = 0.0, forms: float = 0.0, not_leads: float = 0.0) -> None:
    """A month's campaign figures: money spent, and what was counted."""
    db.add(
        CampaignDay(
            id=uuid.uuid4(),
            customer_id="1",
            campaign_id="11",
            day=TODAY - timedelta(days=5),
            clicks=300,
            cost_micros=round(150.0 * MICRO),
            conversions=calls + forms + not_leads,
            calls=calls,
            forms=forms,
            not_leads=not_leads,
            refreshed_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()


def a_search(db: DbSession, term: str, *, conversions: float, leads: float | None) -> None:
    """A search with 140 clicks and 90.00 spent: well past R1's minimum."""
    db.add(
        SearchTermDay(
            id=uuid.uuid4(),
            customer_id="1",
            campaign_id="11",
            ad_group_id="21",
            day=TODAY - timedelta(days=5),
            term=term,
            term_hash=term_key(term),
            status="NONE",
            clicks=140,
            cost_micros=round(90.0 * MICRO),
            conversions=conversions,
            leads=leads,
            refreshed_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()


def _run(db: DbSession) -> Pass:
    return run(db, "1", currency="USD", target_cost_per_lead=5.0, today=TODAY, now=NOW)


def test_a_search_whose_only_conversions_were_page_views_is_found(db: DbSession) -> None:
    """The case that never fired: 140 "conversions", every one a page loading."""
    spent(db, forms=12, not_leads=280)
    a_search(db, "pdf editor jobs", conversions=140, leads=0.0)
    said = _run(db)
    assert [one.target_label for one in said.offered] == ["pdf editor jobs"]


def test_a_search_that_brought_a_real_enquiry_is_left_alone(db: DbSession) -> None:
    spent(db, forms=12, not_leads=280)
    a_search(db, "pdf to word", conversions=140, leads=1.0)
    assert _run(db).offered == ()


def test_a_day_never_split_into_leads_falls_back_to_every_conversion(db: DbSession) -> None:
    """Rows read before the split, or a day Google would not split, are not
    read as "no leads". That could only make R1 offer the wrong thing."""
    spent(db, forms=12)
    a_search(db, "pdf to word", conversions=140, leads=None)
    assert _run(db).offered == ()


def test_an_account_that_counts_no_enquiries_is_not_given_exclusions(db: DbSession) -> None:
    """Every search there looks wasted, its busiest first. So R1 stands down
    and says why, rather than offering to stop the searches the business
    lives on."""
    spent(db, not_leads=280)
    a_search(db, "pdf to word", conversions=140, leads=0.0)
    said = _run(db)
    assert said.offered == ()
    assert "R1" not in said.ran
    assert "counted no enquiries" in said.cannot_check
    assert "280 page views" in said.cannot_check


def test_the_other_rules_still_run_when_leads_cannot_be_told(db: DbSession) -> None:
    """A refused ad is a fact from Google, not a judgement about leads."""
    spent(db, not_leads=280)
    db.add(
        MirrorAd(
            id=uuid.uuid4(),
            customer_id="1",
            resource_name="customers/1/adGroupAds/21~5",
            ad_id="5",
            ad_group_id="21",
            campaign_id="11",
            status="ENABLED",
            approval="DISAPPROVED",
            headlines=["Refused headline"],
            seen_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()
    said = _run(db)
    assert "R4" in said.ran
    assert [one.rule.id for one in said.offered] == ["R4"]


def test_the_inbox_says_why_when_it_cannot_check(db: DbSession) -> None:
    spent(db, not_leads=280)
    inbox = cards_for(db, "1", currency="USD", target_cost_per_lead=0.0, today=TODAY, now=NOW)
    assert inbox.cards == ()
    assert inbox.nothing_because.startswith("Google Ads counted no enquiries")
    assert inbox.as_dict()["cannot_check"] == inbox.nothing_because


def test_an_account_that_has_spent_nothing_is_not_called_blind(db: DbSession) -> None:
    assert _run(db).cannot_check == ""


# ---------- the brief's bar, on a small account ----------


def test_on_a_small_account_the_brief_s_own_bar_decides(db: DbSession) -> None:
    """1.5 times the target cost per lead, as the brief says. At a 3.00 target
    that is 4.50, so a search that cost 6.00 and brought nobody is a loser --
    which the old twenty-dollar floor never let a five-dollar-a-day account
    see."""
    spent(db, forms=12)
    db.add(
        SearchTermDay(
            id=uuid.uuid4(),
            customer_id="1",
            campaign_id="11",
            ad_group_id="21",
            day=TODAY - timedelta(days=4),
            term="pdf editor jobs",
            term_hash=term_key("pdf editor jobs"),
            status="NONE",
            clicks=12,
            cost_micros=round(6.0 * MICRO),
            conversions=0.0,
            leads=0.0,
            refreshed_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()
    said = run(db, "1", currency="USD", target_cost_per_lead=3.0, today=TODAY, now=NOW)
    assert [one.target_label for one in said.offered] == ["pdf editor jobs"]
    assert said.offered[0].rule.version == 2


def test_nothing_found_says_what_was_checked_and_how_close_it_came(db: DbSession) -> None:
    spent(db, forms=12)
    a_search(db, "pdf to word", conversions=3, leads=3.0)
    db.add(
        SearchTermDay(
            id=uuid.uuid4(),
            customer_id="1",
            campaign_id="11",
            ad_group_id="21",
            day=TODAY - timedelta(days=4),
            term="merge pdf free",
            term_hash=term_key("merge pdf free"),
            status="NONE",
            clicks=6,
            cost_micros=round(3.1 * MICRO),
            conversions=0.0,
            leads=0.0,
            refreshed_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()
    inbox = cards_for(db, "1", currency="USD", target_cost_per_lead=3.0, today=TODAY, now=NOW)
    assert inbox.cards == ()
    said = inbox.nothing_because
    assert said.startswith("We looked and found nothing worth changing.")
    assert "Otto checked 2 searches from the last 30 days. 1 brought a lead." in said
    assert "None of the other 1 has cost 5.00 USD yet" in said
    assert 'the nearest is 3.10 USD on "merge pdf free"' in said
