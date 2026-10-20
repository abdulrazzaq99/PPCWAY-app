"""One campaign, out of the mirror, with Google's reporting laid on top.

The page has five tabs and two sources. What the campaign is made of and what
it did day by day are ours; what each keyword and each ad did is Google's own
reporting. The tests that matter are the ones where one source is missing: the
page has to stand on the other and say which half it could not read.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import (
    MICRO,
    CampaignDay,
    ExternalChange,
    MirrorAd,
    MirrorAdGroup,
    MirrorCampaign,
    MirrorKeyword,
)
from ppcway.ads.numbers import campaign_numbers, merge_live
from ppcway.db.base import Base

TODAY = date(2026, 10, 15)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def shape(db: DbSession) -> None:
    """A campaign with one ad group, two keywords and one ad."""
    db.add(
        MirrorCampaign(
            customer_id="1",
            resource_name="customers/1/campaigns/11",
            campaign_id="11",
            name="Emergency plumbing",
            status="ENABLED",
            budget_micros=20 * MICRO,
            starts_at="2026-10-12 00:00:00",
        )
    )
    db.add(
        MirrorAdGroup(
            customer_id="1",
            resource_name="customers/1/adGroups/21",
            ad_group_id="21",
            campaign_id="11",
            name="Drains",
            status="ENABLED",
            cpc_bid_micros=2 * MICRO,
        )
    )
    for criterion, text, negative in (("31", "emergency plumber", False), ("32", "free", True)):
        db.add(
            MirrorKeyword(
                customer_id="1",
                resource_name=f"customers/1/adGroupCriteria/21~{criterion}",
                criterion_id=criterion,
                ad_group_id="21",
                campaign_id="11",
                text=text,
                match_type="PHRASE",
                status="ENABLED",
                negative=negative,
                quality_score=6,
                cpc_bid_micros=2 * MICRO,
            )
        )
    db.add(
        MirrorAd(
            customer_id="1",
            resource_name="customers/1/adGroupAds/21~41",
            ad_id="41",
            ad_group_id="21",
            campaign_id="11",
            status="ENABLED",
            approval="APPROVED",
            headlines=["24 hour plumber", "Call now", ""],
            final_urls=["https://alphaplumbing.ca/emergency"],
        )
    )
    db.commit()


def day(db: DbSession, on: date, *, cost: float, calls: float = 0.0, forms: float = 0.0) -> None:
    db.add(
        CampaignDay(
            customer_id="1",
            campaign_id="11",
            day=on,
            cost_micros=round(cost * MICRO),
            calls=calls,
            forms=forms,
            conversions=calls + forms,
            clicks=10,
            impressions=100,
        )
    )
    db.commit()


def test_the_campaign_adds_up_its_own_days_and_the_week_before(db: DbSession) -> None:
    shape(db)
    day(db, date(2026, 10, 12), cost=70.0, calls=2, forms=1)
    day(db, date(2026, 10, 5), cost=50.0, forms=1)

    held = campaign_numbers(db, "1", "11", days=7, currency="CAD", today=TODAY)

    assert held.read is True
    assert held.name == "Emergency plumbing"
    assert held.budget == 20.0
    assert held.cost == 70.0
    assert held.leads == 3
    assert held.cost_per_lead == round(70 / 3, 2)
    assert held.lead_rate == 30.0
    assert held.cost_before == 50.0
    assert held.cost_per_lead_before == 50.0
    assert [d.date for d in held.series] == ["2026-10-12"]
    assert held.starts_at == "2026-10-12 00:00:00"


def test_what_the_campaign_is_made_of_comes_from_the_mirror(db: DbSession) -> None:
    shape(db)
    day(db, date(2026, 10, 14), cost=10.0)

    held = campaign_numbers(db, "1", "11", days=30, currency="CAD", today=TODAY)

    assert [g["name"] for g in held.groups] == ["Drains"]
    # Positive keywords first, then the negatives, each alphabetical.
    assert [k["keyword"] for k in held.keywords] == ["emergency plumber", "free"]
    assert held.keywords[0]["match"] == "Phrase"
    assert held.keywords[0]["ad_group"] == "Drains"
    assert held.keywords[1]["negative"] is True
    assert held.ads[0]["headlines"] == ["24 hour plumber", "Call now"]
    assert held.ads[0]["final_urls"] == ["https://alphaplumbing.ca/emergency"]
    # The mirror does not hold per-keyword performance, and does not pretend to.
    assert held.metrics_read is False
    assert held.keywords[0]["clicks"] == 0


def test_the_change_history_is_this_campaign_s_and_newest_first(db: DbSession) -> None:
    shape(db)
    day(db, date(2026, 10, 14), cost=10.0)
    db.add(
        ExternalChange(
            customer_id="1",
            kind="campaign",
            resource_name="customers/1/campaigns/11",
            campaign_id="11",
            label="Emergency plumbing",
            summary="Daily budget raised from 5.00 CAD to 12.00 CAD",
            noticed_at=NOW - timedelta(days=3),
        )
    )
    db.add(
        ExternalChange(
            customer_id="1",
            kind="keyword",
            resource_name="customers/1/adGroupCriteria/21~31",
            campaign_id="11",
            label="emergency plumber",
            summary="Paused in Google Ads, from enabled",
            noticed_at=NOW,
        )
    )
    db.add(
        ExternalChange(
            customer_id="1",
            kind="campaign",
            resource_name="customers/1/campaigns/99",
            campaign_id="99",
            label="Another campaign",
            summary="Something else entirely",
            noticed_at=NOW,
        )
    )
    db.commit()

    held = campaign_numbers(db, "1", "11", days=30, today=TODAY)

    assert [c.summary for c in held.history] == [
        "Paused in Google Ads, from enabled",
        "Daily budget raised from 5.00 CAD to 12.00 CAD",
    ]


def test_a_campaign_we_have_never_read_says_so(db: DbSession) -> None:
    held = campaign_numbers(db, "1", "11", days=30, today=TODAY)

    assert held.read is False
    assert "not read" in held.trouble.lower()


def test_google_s_reporting_is_laid_over_what_we_hold(db: DbSession) -> None:
    shape(db)
    day(db, date(2026, 10, 14), cost=70.0, calls=2)
    held = campaign_numbers(db, "1", "11", days=30, currency="CAD", today=TODAY)

    merged = merge_live(
        held,
        {
            "read": True,
            "currency": "CAD",
            "impression_share": 62.5,
            "lost_to_budget": 12.0,
            "lost_to_rank": 25.5,
            "keywords": [
                {
                    "keyword": "emergency plumber",
                    "match": "Phrase",
                    "quality_score": 8,
                    "clicks": 40,
                    "leads": 2.0,
                    "cost": 70.0,
                    "cost_per_lead": 35.0,
                }
            ],
            "terms": [
                {"term": "plumber near me", "clicks": 3, "leads": 0, "cost": 9.0, "waste": True}
            ],
            "ads": [
                {
                    "ad_group": "Drains",
                    "headlines": ["24 hour plumber", "Call now"],
                    "approval": "APPROVED",
                    "status": "ENABLED",
                    "impressions": 900,
                    "clicks": 40,
                    "click_rate": 4.4,
                }
            ],
        },
    )

    assert merged.metrics_read is True
    assert merged.impression_share == 62.5
    assert merged.terms[0]["term"] == "plumber near me"
    word = next(k for k in merged.keywords if k["keyword"] == "emergency plumber")
    assert word["clicks"] == 40
    assert word["cost_per_lead"] == 35.0
    # Google's quality score is fresher than the one we last mirrored.
    assert word["quality_score"] == 8
    # Our own fields survive the merge.
    assert word["ad_group"] == "Drains"
    assert merged.ads[0]["impressions"] == 900
    # The campaign's own totals stay ours.
    assert merged.cost == 70.0


def test_a_keyword_google_reports_and_we_have_not_mirrored_still_shows(db: DbSession) -> None:
    shape(db)
    day(db, date(2026, 10, 14), cost=70.0)
    held = campaign_numbers(db, "1", "11", days=30, currency="CAD", today=TODAY)

    merged = merge_live(
        held,
        {
            "read": True,
            "keywords": [
                {
                    "keyword": "blocked drain",
                    "match": "Exact",
                    "quality_score": 7,
                    "clicks": 5,
                    "leads": 1.0,
                    "cost": 20.0,
                    "cost_per_lead": 20.0,
                }
            ],
        },
    )

    added = next(k for k in merged.keywords if k["keyword"] == "blocked drain")
    assert added["cost"] == 20.0
    assert added["ad_group"] == ""
    # Dearest first, so the money is at the top of the tab.
    assert merged.keywords[0]["keyword"] == "blocked drain"


def test_a_refusal_from_google_leaves_our_numbers_standing(db: DbSession) -> None:
    shape(db)
    day(db, date(2026, 10, 14), cost=70.0, calls=2)
    held = campaign_numbers(db, "1", "11", days=30, currency="CAD", today=TODAY)

    merged = merge_live(held, {"read": False, "trouble": "That permission was refused."})

    assert merged.read is True
    assert merged.cost == 70.0
    assert merged.metrics_read is False
    assert merged.terms == []


def test_before_the_days_arrive_google_s_totals_beat_showing_zeros(db: DbSession) -> None:
    shape(db)
    held = campaign_numbers(db, "1", "11", days=30, currency="CAD", today=TODAY)
    assert held.cost == 0.0

    merged = merge_live(held, {"read": True, "leads": 4, "cost": 120.0, "clicks": 60})

    assert merged.cost == 120.0
    assert merged.leads == 4
    assert merged.clicks == 60
