"""The dashboard's numbers, added up from our own mirror instead of from Google.

The point of the mirror is that these sums are a database query rather than four
round trips to California, and that they can answer a question a live read
cannot afford: how this period compares with the one before it.

The window is Google's own: "last thirty days" means the thirty days ending
yesterday, the same as the figure in the Google Ads interface, so a merchant
comparing the two screens sees one number and not two.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, CampaignDay, ExternalChange, MirrorAd, MirrorCampaign, SyncRun
from ppcway.ads.numbers import account_numbers
from ppcway.db.base import Base

#: A Thursday in the middle of a month, so no sum lands on a month boundary.
TODAY = date(2026, 10, 15)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def campaign(
    db: DbSession,
    campaign_id: str = "11",
    *,
    name: str = "Emergency plumbing",
    status: str = "ENABLED",
    budget: float = 20.0,
    gone: bool = False,
) -> MirrorCampaign:
    row = MirrorCampaign(
        customer_id="1",
        resource_name=f"customers/1/campaigns/{campaign_id}",
        campaign_id=campaign_id,
        name=name,
        status=status,
        budget_micros=round(budget * MICRO),
        gone_at=NOW if gone else None,
    )
    db.add(row)
    db.commit()
    return row


def day(
    db: DbSession,
    on: date,
    *,
    campaign_id: str = "11",
    cost: float = 0.0,
    calls: float = 0.0,
    forms: float = 0.0,
    clicks: int = 0,
    impressions: int = 0,
) -> None:
    db.add(
        CampaignDay(
            customer_id="1",
            campaign_id=campaign_id,
            day=on,
            cost_micros=round(cost * MICRO),
            calls=calls,
            forms=forms,
            conversions=calls + forms,
            clicks=clicks,
            impressions=impressions,
        )
    )
    db.commit()


def test_the_window_is_added_up_from_the_days_we_hold(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 14), cost=40.0, calls=1, forms=1, clicks=10, impressions=100)
    day(db, date(2026, 10, 13), cost=20.0, calls=1, clicks=5, impressions=60)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert held.read is True
    assert held.cost == 60.0
    assert held.leads == 3
    assert held.calls == 2
    assert held.forms == 1
    assert held.clicks == 15
    assert held.impressions == 160
    assert held.cost_per_lead == 20.0


def test_the_period_before_is_the_same_length_and_ends_where_this_one_starts(
    db: DbSession,
) -> None:
    campaign(db)
    # Seven days of this week, and seven of the week before it.
    day(db, date(2026, 10, 12), cost=100.0, forms=4)
    day(db, date(2026, 10, 5), cost=100.0, forms=2)

    held = account_numbers(db, "1", days=7, today=TODAY)

    assert held.leads == 4
    assert held.cost == 100.0
    assert held.leads_before == 2
    assert held.cost_before == 100.0
    assert held.cost_per_lead == 25.0
    assert held.cost_per_lead_before == 50.0


def test_a_day_older_than_both_windows_is_left_out(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 12), cost=10.0, forms=1)
    day(db, date(2026, 8, 1), cost=999.0, forms=99)

    held = account_numbers(db, "1", days=7, today=TODAY)

    assert held.cost == 10.0
    assert held.leads_before == 0


def test_today_is_not_counted_because_the_day_is_not_over(db: DbSession) -> None:
    campaign(db)
    day(db, TODAY, cost=77.0, forms=3)
    day(db, date(2026, 10, 14), cost=10.0, forms=1)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert held.cost == 10.0
    assert held.leads == 1


def test_each_campaign_row_carries_its_own_days_for_the_sparkline(db: DbSession) -> None:
    campaign(db, "11", name="Emergency plumbing")
    campaign(db, "12", name="Drain cleaning")
    day(db, date(2026, 10, 14), campaign_id="11", cost=30.0, forms=2)
    day(db, date(2026, 10, 13), campaign_id="11", cost=10.0)
    day(db, date(2026, 10, 14), campaign_id="12", cost=5.0, calls=1)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert [c.name for c in held.campaigns] == ["Emergency plumbing", "Drain cleaning"]
    first, second = held.campaigns
    assert first.cost == 40.0
    assert first.leads == 2
    assert first.budget == 20.0
    assert [d.date for d in first.days] == ["2026-10-13", "2026-10-14"]
    assert [d.cost for d in first.days] == [10.0, 30.0]
    assert second.cost == 5.0
    # The whole-account series is every campaign added up, day by day.
    assert [d.cost for d in held.series] == [10.0, 35.0]


def test_a_campaign_that_spent_and_counted_nothing_needs_you(db: DbSession) -> None:
    campaign(db, "11", name="Drain cleaning")
    day(db, date(2026, 10, 14), cost=120.0, clicks=40)

    held = account_numbers(db, "1", days=30, today=TODAY)

    need = next(n for n in held.needs if n.kind == "spend_no_leads")
    assert need.label == "Drain cleaning"
    assert "120.00" in need.what
    assert need.campaign_id == "11"


def test_a_campaign_that_spent_a_little_is_not_worth_waking_somebody_for(db: DbSession) -> None:
    campaign(db, "11")
    day(db, date(2026, 10, 14), cost=2.0, clicks=1)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert [n.kind for n in held.needs] == []


def test_an_ad_google_refused_needs_you(db: DbSession) -> None:
    campaign(db, "11", name="Emergency plumbing")
    db.add(
        MirrorAd(
            customer_id="1",
            resource_name="customers/1/adGroupAds/21~41",
            ad_id="41",
            ad_group_id="21",
            campaign_id="11",
            status="ENABLED",
            approval="DISAPPROVED",
            headlines=["24 hour plumber", "Call now"],
        )
    )
    db.commit()

    held = account_numbers(db, "1", days=30, today=TODAY)

    need = next(n for n in held.needs if n.kind == "ad_refused")
    assert need.label == "24 hour plumber"
    assert "Emergency plumbing" in need.what


def test_an_ad_refused_in_a_campaign_that_is_gone_is_nobody_s_problem(db: DbSession) -> None:
    campaign(db, "11", name="Old campaign", gone=True)
    db.add(
        MirrorAd(
            customer_id="1",
            resource_name="customers/1/adGroupAds/21~41",
            ad_id="41",
            ad_group_id="21",
            campaign_id="11",
            status="ENABLED",
            approval="DISAPPROVED",
            headlines=["Old ad"],
            gone_at=NOW,
        )
    )
    db.commit()

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert [n.kind for n in held.needs] == []


def test_a_hand_in_google_ads_shows_up_in_the_activity(db: DbSession) -> None:
    campaign(db)
    db.add(
        ExternalChange(
            customer_id="1",
            kind="campaign",
            resource_name="customers/1/campaigns/11",
            label="Emergency plumbing",
            summary="Daily budget raised from 5.00 CAD to 12.00 CAD",
            noticed_at=NOW,
        )
    )
    db.commit()

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert len(held.activity) == 1
    assert held.activity[0].summary.startswith("Daily budget raised")
    assert held.activity[0].label == "Emergency plumbing"
    assert next(n for n in held.needs if n.kind == "changed_in_google").what


def test_a_campaign_gone_from_google_still_counts_what_it_spent(db: DbSession) -> None:
    campaign(db, "11", name="Last winter's offer", gone=True)
    day(db, date(2026, 10, 14), cost=50.0, forms=1)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert held.cost == 50.0
    assert [c.name for c in held.campaigns] == ["Last winter's offer"]
    assert held.campaigns[0].gone is True


def test_the_month_is_counted_up_to_and_including_today(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 1), cost=10.0)
    day(db, TODAY, cost=5.0)
    day(db, date(2026, 9, 30), cost=999.0)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert held.month_cost == 15.0
    assert held.month_day == 15
    assert held.month_days == 31
    # Every daily budget the account is running, over an average month.
    assert held.monthly_budget == round(20.0 * 30.4, 2)


def test_nothing_spent_is_not_a_divide_by_zero(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 14), cost=0.0)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert held.read is True
    assert held.cost_per_lead == 0.0


def test_an_account_we_have_never_read_says_so_rather_than_showing_zeros(db: DbSession) -> None:
    held = account_numbers(db, "1", days=30, today=TODAY)

    assert held.read is False
    assert "not read" in held.trouble.lower()


def test_it_says_when_we_last_looked_and_how_much_we_hold(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 14), cost=1.0)
    day(db, date(2026, 9, 15), cost=1.0)
    db.add(
        SyncRun(
            customer_id="1",
            kind="today",
            status="done",
            finished_at=NOW,
        )
    )
    db.add(SyncRun(customer_id="1", kind="today", status="running"))
    db.commit()

    held = account_numbers(db, "1", days=30, today=TODAY)

    # SQLite forgets the time zone on the way back out; Postgres does not.
    assert held.looked_at is not None
    assert held.looked_at.replace(tzinfo=UTC) == NOW
    assert held.held_days == 2
    assert held.currency == ""


def test_the_currency_is_the_one_the_account_was_chosen_with(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 14), cost=1.0)

    held = account_numbers(db, "1", days=30, today=TODAY, currency="CAD")

    assert held.currency == "CAD"
    assert held.as_dict()["currency"] == "CAD"


def test_the_window_carries_the_dates_it_covers(db: DbSession) -> None:
    # The screen used to work these out for itself and got "to today" over a
    # window that ends yesterday.
    campaign(db)
    day(db, date(2026, 10, 14), cost=10.0)

    held = account_numbers(db, "1", days=30, today=TODAY)

    assert held.starts_on == "2026-09-15"
    assert held.ends_on == "2026-10-14"
    assert held.as_dict()["ends_on"] == "2026-10-14"
