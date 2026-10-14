"""Reading an account into the mirror, twice, with a hand in it in between.

The second read is where the value is. A mirror that only works on an empty
database is a cache; what the requirements ask for is that a change made
directly in Google Ads is noticed, recorded as theirs, and not silently
overwritten.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import (
    CampaignDay,
    ExternalChange,
    MirrorAd,
    MirrorAdGroup,
    MirrorCampaign,
    MirrorKeyword,
)
from ppcway.ads.sync import backfill_since, sync_days, sync_structure
from ppcway.db.base import Base

NOW = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def campaign(budget: int = 5_000_000, status: str = "ENABLED", name: str = "Emergency") -> dict:
    return {
        "campaign": {
            "resourceName": "customers/1/campaigns/11",
            "id": "11",
            "name": name,
            "status": status,
            "advertisingChannelType": "SEARCH",
            "biddingStrategyType": "MAXIMIZE_CONVERSIONS",
            "startDateTime": "2026-09-01 00:00:00",
        },
        "campaignBudget": {"amountMicros": str(budget)},
        "customer": {"currencyCode": "CAD"},
    }


AD_GROUP = {
    "adGroup": {
        "resourceName": "customers/1/adGroups/21",
        "id": "21",
        "name": "Drains",
        "status": "ENABLED",
        "cpcBidMicros": "2000000",
    },
    "campaign": {"id": "11"},
}

KEYWORD = {
    "adGroupCriterion": {
        "resourceName": "customers/1/adGroupCriteria/21~31",
        "criterionId": "31",
        "keyword": {"text": "blocked drain oakville", "matchType": "PHRASE"},
        "status": "ENABLED",
        "qualityInfo": {"qualityScore": 7},
        "cpcBidMicros": "1500000",
    },
    "adGroup": {"id": "21"},
    "campaign": {"id": "11"},
}

AD = {
    "adGroupAd": {
        "resourceName": "customers/1/adGroupAds/21~41",
        "ad": {
            "id": "41",
            "type": "RESPONSIVE_SEARCH_AD",
            "responsiveSearchAd": {
                "headlines": [{"text": "Blocked drain?"}, {"text": "Same day"}],
                "descriptions": [{"text": "Oakville plumber"}],
            },
            "finalUrls": ["https://alpha-plumbing.ca/drains"],
        },
        "status": "ENABLED",
        "policySummary": {"approvalStatus": "APPROVED"},
    },
    "adGroup": {"id": "21"},
    "campaign": {"id": "11"},
}


def account(answers: dict[str, list[dict]]) -> httpx.Client:
    """An account answering each query with the rows named for it."""

    def handle(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        for mark, rows in answers.items():
            if mark in query:
                return httpx.Response(200, json={"results": rows})
        return httpx.Response(200, json={"results": []})

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")


def structure(db: DbSession, client: httpx.Client, now: datetime = NOW) -> object:
    return sync_structure(db, "1", access_token="a", developer_token="d", client=client, now=now)


def test_a_first_read_mirrors_the_whole_account(db: DbSession) -> None:
    report = structure(
        db,
        account(
            {
                "FROM campaign": [campaign()],
                "FROM ad_group ": [AD_GROUP],
                "ad_group_criterion": [KEYWORD],
                "ad_group_ad": [AD],
            }
        ),
    )
    assert report.counts == {"campaigns": 1, "ad_groups": 1, "keywords": 1, "ads": 1}
    assert report.changes == [], "nothing changed; this is the first look"
    held = db.scalar(sa.select(MirrorCampaign))
    assert held is not None and held.name == "Emergency" and held.budget == 5.0
    assert db.scalar(sa.select(MirrorAdGroup)) is not None
    word = db.scalar(sa.select(MirrorKeyword))
    assert word is not None and word.text == "blocked drain oakville" and word.quality_score == 7
    ad = db.scalar(sa.select(MirrorAd))
    assert ad is not None and ad.headlines == ["Blocked drain?", "Same day"]


def test_reading_twice_changes_nothing_and_says_so(db: DbSession) -> None:
    """A sync that finds no news must not invent any, or every row would look touched."""
    answers = {"FROM campaign": [campaign()], "FROM ad_group ": [AD_GROUP]}
    structure(db, account(answers))
    first = db.scalar(sa.select(MirrorCampaign))
    assert first is not None
    stamp = first.changed_at

    report = structure(db, account(answers), now=datetime(2026, 10, 14, 10, tzinfo=UTC))
    assert report.changes == []
    again = db.scalar(sa.select(MirrorCampaign))
    assert again is not None and again.changed_at == stamp, "an unchanged row is not re-stamped"
    assert db.scalar(sa.select(sa.func.count()).select_from(ExternalChange)) == 0
    assert db.scalar(sa.select(sa.func.count()).select_from(MirrorCampaign)) == 1, "no duplicate"


def test_a_budget_raised_in_google_ads_is_noticed_and_named(db: DbSession) -> None:
    structure(db, account({"FROM campaign": [campaign(budget=5_000_000)]}))
    report = structure(db, account({"FROM campaign": [campaign(budget=12_000_000)]}))

    assert report.changes == ["Emergency: Daily budget changed from 5.00 CAD to 12.00 CAD"]
    change = db.scalar(sa.select(ExternalChange))
    assert change is not None
    assert change.kind == "campaign" and change.label == "Emergency"
    assert change.before["budget_micros"] == 5_000_000
    assert change.after["budget_micros"] == 12_000_000
    held = db.scalar(sa.select(MirrorCampaign))
    assert held is not None and held.budget_micros == 12_000_000, "the mirror follows the account"


def test_a_campaign_paused_by_hand_reads_as_a_sentence(db: DbSession) -> None:
    structure(db, account({"FROM campaign": [campaign()]}))
    report = structure(db, account({"FROM campaign": [campaign(status="PAUSED")]}))
    assert report.changes == ["Emergency: Paused in Google Ads, from enabled"]


def test_a_campaign_that_disappears_is_marked_gone_not_deleted(db: DbSession) -> None:
    """A mirror that forgets cannot be compared with yesterday."""
    structure(db, account({"FROM campaign": [campaign()]}))
    report = structure(db, account({"FROM campaign": []}))

    assert report.changes == ["Emergency is no longer in the account"]
    held = db.scalar(sa.select(MirrorCampaign))
    assert held is not None and held.gone_at is not None, "kept, with the date it went"


def test_a_refused_read_keeps_what_it_can_and_says_what_it_could_not(db: DbSession) -> None:
    """One kind of thing can be refused while the others are readable."""

    def handle(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        if "ad_group_criterion" in query:
            return httpx.Response(403, json={"error": {"message": "no permission"}})
        if "FROM campaign" in query:
            return httpx.Response(200, json={"results": [campaign()]})
        return httpx.Response(200, json={"results": []})

    report = structure(
        db, httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")
    )
    assert report.counts["campaigns"] == 1, "the campaign still landed"
    assert "keywords" not in report.counts
    assert report.trouble, "and the refusal is carried, not swallowed"


def test_the_days_are_one_row_a_campaign_a_day(db: DbSession) -> None:
    money = [
        {
            "campaign": {"id": "11"},
            "segments": {"date": "2026-10-13"},
            "metrics": {
                "impressions": "900",
                "clicks": "40",
                "costMicros": "86410000",
                "conversions": 2,
                "conversionsValue": 300.0,
            },
        }
    ]
    split = [
        {
            "campaign": {"id": "11"},
            "segments": {"date": "2026-10-13", "conversionActionCategory": "PHONE_CALL_LEAD"},
            "metrics": {"conversions": 1.5},
        },
        {
            "campaign": {"id": "11"},
            "segments": {"date": "2026-10-13", "conversionActionCategory": "SUBMIT_LEAD_FORM"},
            "metrics": {"conversions": 0.5},
        },
    ]

    def handle(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        return httpx.Response(
            200, json={"results": split if "conversion_action_category" in query else money}
        )

    report = sync_days(
        db,
        "1",
        since=date(2026, 10, 13),
        until=date(2026, 10, 13),
        access_token="a",
        developer_token="d",
        client=httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x"),
        now=NOW,
    )
    assert report.counts == {"days": 1, "rows": 1}
    day = db.scalar(sa.select(CampaignDay))
    assert day is not None
    assert day.cost == 86.41 and day.clicks == 40
    assert day.calls == 1.5 and day.forms == 0.5, "the split is merged onto the money"


def test_a_day_read_again_is_rewritten_not_doubled(db: DbSession) -> None:
    """Conversions arrive late, so the last three days are re-read every night."""

    def answering(conversions: float) -> httpx.Client:
        def handle(request: httpx.Request) -> httpx.Response:
            query = json.loads(request.content)["query"]
            if "conversion_action_category" in query:
                return httpx.Response(200, json={"results": []})
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "campaign": {"id": "11"},
                            "segments": {"date": "2026-10-13"},
                            "metrics": {"costMicros": "86410000", "conversions": conversions},
                        }
                    ]
                },
            )

        return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")

    for amount in (1.0, 3.0):
        sync_days(
            db,
            "1",
            since=date(2026, 10, 13),
            until=date(2026, 10, 13),
            access_token="a",
            developer_token="d",
            client=answering(amount),
            now=NOW,
        )

    assert db.scalar(sa.select(sa.func.count()).select_from(CampaignDay)) == 1
    day = db.scalar(sa.select(CampaignDay))
    assert day is not None and day.conversions == 3.0, "the later reading wins"


def test_the_nightly_pass_reaches_back_three_days() -> None:
    assert backfill_since(date(2026, 10, 14)) == date(2026, 10, 11)


def test_no_page_size_is_sent() -> None:
    """v25 refuses the whole query if a page size is set, which cost a live run."""
    bodies: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"results": []})

    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as db:
        structure(db, httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x"))
    assert bodies and all("pageSize" not in body for body in bodies)
