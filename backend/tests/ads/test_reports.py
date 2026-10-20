"""The report, and the arithmetic that stops it reading noise as news.

Eleven leads last month and eight this month is not a thirty per cent collapse;
it is eleven and eight. These tests are mostly about the cases where the honest
answer is "nobody can tell from this", because that is the answer a report
built from an arrow would never give.
"""

from __future__ import annotations

from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, CampaignDay, MirrorCampaign
from ppcway.ads.reports import DEFINITIONS, report_for
from ppcway.db.base import Base

TODAY = date(2026, 10, 15)
#: One day inside each of the three windows a report compares.
IN_WINDOW = date(2026, 10, 14)
IN_BEFORE = date(2026, 9, 10)
IN_YEAR_AGO = date(2025, 10, 14)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def campaign(db: DbSession) -> None:
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


def day(
    db: DbSession,
    on: date,
    *,
    cost: float = 0.0,
    leads: float = 0.0,
    clicks: int = 0,
    impressions: int = 0,
) -> None:
    db.add(
        CampaignDay(
            customer_id="1",
            campaign_id="11",
            day=on,
            cost_micros=round(cost * MICRO),
            forms=leads,
            conversions=leads,
            clicks=clicks,
            impressions=impressions,
        )
    )
    db.commit()


def figure(report: object, key: str) -> object:
    return next(f for f in report.figures if f.key == key)  # type: ignore[attr-defined]


def test_a_difference_too_big_for_chance_is_called_a_real_change(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=40, clicks=200)
    day(db, IN_BEFORE, cost=400.0, leads=20, clicks=200)

    report = report_for(db, "1", days=30, currency="CAD", today=TODAY)
    leads = figure(report, "leads")

    assert report.read is True
    assert leads.value == 40
    assert leads.before == 20
    assert leads.verdict == "real"
    assert "up" in leads.words
    assert leads.test == "two Poisson counts"
    assert leads.change == 100.0


def test_a_small_move_at_a_small_volume_is_within_the_normal_range(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=120.0, leads=12, clicks=60)
    day(db, IN_BEFORE, cost=100.0, leads=10, clicks=55)

    leads = figure(report_for(db, "1", days=30, currency="CAD", today=TODAY), "leads")

    assert leads.verdict == "normal"
    assert "normal range" in leads.words
    # The arrow would have said twenty per cent up. The verdict says otherwise.
    assert leads.change == 20.0


def test_too_few_leads_says_nobody_can_tell(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=90.0, leads=3, clicks=30)
    day(db, IN_BEFORE, cost=60.0, leads=2, clicks=25)

    leads = figure(report_for(db, "1", days=30, currency="CAD", today=TODAY), "leads")

    assert leads.verdict == "thin"
    assert "Too few leads" in leads.words


def test_with_no_earlier_period_it_does_not_pretend_to_compare(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=40, clicks=200)

    leads = figure(report_for(db, "1", days=30, currency="CAD", today=TODAY), "leads")

    assert leads.verdict == "none"
    assert leads.before is None
    assert "no earlier period" in leads.words


def test_spend_gets_no_verdict_and_says_why(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=40, clicks=200)
    day(db, IN_BEFORE, cost=200.0, leads=20, clicks=200)

    spend = figure(report_for(db, "1", days=30, currency="CAD", today=TODAY), "cost")

    assert spend.verdict == "none"
    assert "a decision, not a measurement" in spend.words
    assert spend.value == 400.0
    assert spend.before == 200.0


def test_the_lead_rate_is_tested_against_the_clicks_of_both_periods(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=30, clicks=200)
    day(db, IN_BEFORE, cost=400.0, leads=10, clicks=200)

    rate = figure(report_for(db, "1", days=30, currency="CAD", today=TODAY), "lead_rate")

    assert rate.value == 15.0
    assert rate.before == 5.0
    assert rate.verdict == "real"
    assert "better" in rate.words
    assert rate.test == "two proportions"


def test_a_rate_on_a_handful_of_clicks_is_not_judged(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=40.0, leads=3, clicks=20)
    day(db, IN_BEFORE, cost=40.0, leads=1, clicks=20)

    rate = figure(report_for(db, "1", days=30, currency="CAD", today=TODAY), "lead_rate")

    assert rate.verdict == "thin"
    assert "Too few clicks" in rate.words


def test_year_on_year_appears_only_when_a_year_is_held(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=40, clicks=200)

    thin = report_for(db, "1", days=30, currency="CAD", today=TODAY)
    assert thin.year_held is False
    assert figure(thin, "leads").year_ago is None

    day(db, IN_YEAR_AGO, cost=300.0, leads=25, clicks=150)
    full = report_for(db, "1", days=30, currency="CAD", today=TODAY)

    assert full.year_held is True
    assert figure(full, "leads").year_ago == 25
    assert figure(full, "cost").year_ago == 300.0


def test_the_cost_per_lead_follows_the_leads_underneath_it(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=40, clicks=200)
    day(db, IN_BEFORE, cost=400.0, leads=20, clicks=200)

    each = figure(report_for(db, "1", days=30, currency="CAD", today=TODAY), "cost_per_lead")

    assert each.value == 10.0
    assert each.before == 20.0
    assert each.verdict == "real"
    assert "leads underneath it" in each.words


def test_the_period_is_named_and_said_in_one_sentence(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=40, clicks=200)

    report = report_for(db, "1", days=30, currency="CAD", today=TODAY)

    assert report.starts_on == "2026-09-15"
    assert report.ends_on == "2026-10-14"
    assert report.sentence == (
        "You spent $400.00 and it brought 40 enquiries, which is $10.00 each."
    )


def test_money_spent_with_nothing_counted_is_said_plainly(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, clicks=200)

    report = report_for(db, "1", days=30, currency="CAD", today=TODAY)

    assert "counted no enquiries at all" in report.sentence
    assert "the tracking" in report.sentence


def test_the_definitions_travel_with_the_report(db: DbSession) -> None:
    campaign(db)
    day(db, IN_WINDOW, cost=400.0, leads=40, clicks=200)

    said = report_for(db, "1", days=30, currency="CAD", today=TODAY).as_dict()

    assert said["definitions"] == DEFINITIONS
    assert any(d["term"] == "A real change" for d in said["definitions"])
    assert any(d["term"] == "Why spend has no verdict" for d in said["definitions"])


def test_an_account_we_have_not_read_says_so(db: DbSession) -> None:
    report = report_for(db, "1", days=30, today=TODAY)

    assert report.read is False
    assert "not read" in report.trouble.lower()
    assert report.figures == []
