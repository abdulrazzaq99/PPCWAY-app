"""The three mirrors the recommendation engine reads, and nothing else.

Phase 0.3. A rule that proposes excluding a wasteful search term is the only
change the client will let run unattended, so what it reads has to be right:
the words a person actually typed, whether that term is already handled, what
each keyword did on each day, and how much of the auction we were in.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import CampaignDay, KeywordDay, SearchTermDay, term_key
from ppcway.ads.sync import sync_days, sync_keyword_days, sync_search_terms
from ppcway.db.base import Base

NOW = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)
SINCE = date(2026, 10, 28)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def account(answers: dict[str, list[dict]]) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        for mark, rows in answers.items():
            if mark in query:
                return httpx.Response(200, json={"results": rows})
        return httpx.Response(200, json={"results": []})

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")


def a_term(
    term: str = "emergency plumber ennis",
    *,
    status: str = "NONE",
    day: str = "2026-10-29",
    impressions: str = "120",
    clicks: str = "9",
    cost: str = "14_300_000",
    conversions: float = 0.0,
) -> dict:
    return {
        "searchTermView": {"searchTerm": term, "status": status},
        "segments": {"date": day, "keyword": {"info": {"text": "plumber ennis"}}},
        "campaign": {"id": "11"},
        "adGroup": {"id": "21"},
        "metrics": {
            "impressions": impressions,
            "clicks": clicks,
            "costMicros": cost.replace("_", ""),
            "conversions": conversions,
            "conversionsValue": 0.0,
        },
    }


def _terms(db: DbSession, rows: list[dict]) -> object:
    return sync_search_terms(
        db,
        "1",
        since=SINCE,
        access_token="a",
        developer_token="d",
        client=account({"search_term_view": rows}),
        now=NOW,
    )


def test_what_people_typed_is_stored_per_day(db: DbSession) -> None:
    report = _terms(db, [a_term(), a_term(day="2026-10-30", clicks="4")])
    assert report.counts["rows"] == 2
    assert report.counts["search_terms"] == 1, "one term, two days"

    rows = db.scalars(sa.select(SearchTermDay).order_by(SearchTermDay.day)).all()
    assert [r.day for r in rows] == [date(2026, 10, 29), date(2026, 10, 30)]
    assert rows[0].term == "emergency plumber ennis"
    assert rows[0].matched_keyword == "plumber ennis"
    assert rows[0].cost == 14.30
    assert rows[0].campaign_id == "11" and rows[0].ad_group_id == "21"


@pytest.mark.parametrize(
    ("status", "handled"),
    [
        ("NONE", False),
        ("UNKNOWN", False),
        ("ADDED", True),
        ("EXCLUDED", True),
        ("ADDED_EXCLUDED", True),
    ],
)
def test_whether_a_term_is_already_handled_is_kept(
    db: DbSession, status: str, handled: bool
) -> None:
    """Recommending an exclusion a merchant has already made loses their trust."""
    _terms(db, [a_term(status=status)])
    row = db.scalars(sa.select(SearchTermDay)).one()
    assert row.status == status
    assert row.already_handled is handled


def test_a_term_that_only_matched_is_not_stored(db: DbSession) -> None:
    """Google reports rows with no impressions. They are storage without signal."""
    report = _terms(db, [a_term(impressions="0"), a_term(term="real one")])
    assert report.counts["rows"] == 1
    assert db.scalars(sa.select(SearchTermDay)).one().term == "real one"


def test_the_same_words_spelled_differently_are_one_term(db: DbSession) -> None:
    """Otherwise one term's spend splits in two, each half under the threshold."""
    _terms(db, [a_term(term="Emergency  Plumber   Ennis"), a_term(term="emergency plumber ennis")])
    rows = db.scalars(sa.select(SearchTermDay)).all()
    assert len(rows) == 1, "one row, because the hash is case-folded and space-collapsed"
    assert rows[0].term_hash == term_key("emergency plumber ennis")


def test_reading_again_rewrites_rather_than_duplicates(db: DbSession) -> None:
    """Conversions arrive late, so the nightly pass re-reads the last few days."""
    _terms(db, [a_term(clicks="9", conversions=0.0)])
    _terms(db, [a_term(clicks="11", conversions=1.0)])
    row = db.scalars(sa.select(SearchTermDay)).one()
    assert (row.clicks, row.conversions) == (11, 1.0)


def test_a_refusal_is_carried_rather_than_half_written(db: DbSession) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "no permission"}})

    report = sync_search_terms(
        db,
        "1",
        since=SINCE,
        access_token="a",
        developer_token="d",
        client=httpx.Client(transport=httpx.MockTransport(refuse), base_url="https://x"),
        now=NOW,
    )
    assert not report.ok
    assert report.trouble
    assert db.scalars(sa.select(SearchTermDay)).all() == []


def a_keyword_day(day: str = "2026-10-29", clicks: str = "40", conversions: float = 0.0) -> dict:
    return {
        "adGroupCriterion": {
            "criterionId": "301",
            "keyword": {"text": "emergency plumber", "matchType": "PHRASE"},
        },
        "adGroup": {"id": "21"},
        "campaign": {"id": "11"},
        "segments": {"date": day},
        "metrics": {
            "impressions": "900",
            "clicks": clicks,
            "costMicros": "86410000",
            "conversions": conversions,
            "conversionsValue": 0.0,
        },
    }


def _keywords(db: DbSession, rows: list[dict]) -> object:
    return sync_keyword_days(
        db,
        "1",
        since=SINCE,
        access_token="a",
        developer_token="d",
        client=account({"keyword_view": rows}),
        now=NOW,
    )


def test_one_keyword_one_day(db: DbSession) -> None:
    report = _keywords(db, [a_keyword_day(), a_keyword_day(day="2026-10-30")])
    assert report.counts["keywords"] == 1
    assert report.counts["rows"] == 2
    row = db.scalars(sa.select(KeywordDay).order_by(KeywordDay.day)).first()
    assert row is not None
    assert (row.text, row.match_type, row.clicks) == ("emergency plumber", "PHRASE", 40)
    assert row.cost == 86.41


def test_enough_days_answer_whether_a_keyword_is_a_loser(db: DbSession) -> None:
    """The guardrail asks for 100 clicks or 1.5x the target cost per lead."""
    _keywords(db, [a_keyword_day(day=f"2026-10-{d}", clicks="40") for d in (28, 29, 30)])
    spent, clicks, got = db.execute(
        sa.select(
            sa.func.sum(KeywordDay.cost_micros),
            sa.func.sum(KeywordDay.clicks),
            sa.func.sum(KeywordDay.conversions),
        ).where(KeywordDay.criterion_id == "301")
    ).one()
    assert clicks == 120, "over a hundred clicks, so there is enough to judge"
    assert got == 0.0, "and nothing to show for it"
    assert round(spent / 1_000_000, 2) == 259.23


def a_campaign_day(**metrics: object) -> dict:
    figures: dict[str, object] = {
        "impressions": "900",
        "clicks": "40",
        "costMicros": "86410000",
        "conversions": 2,
        "conversionsValue": 300.0,
    }
    figures.update(metrics)
    return {
        "campaign": {"id": "11"},
        "segments": {"date": "2026-10-29"},
        "metrics": figures,
    }


def _days(db: DbSession, rows: list[dict]) -> object:
    return sync_days(
        db,
        "1",
        since=SINCE,
        access_token="a",
        developer_token="d",
        client=account({"FROM campaign": rows}),
        now=NOW,
    )


def test_how_much_of_the_auction_we_were_in_is_read(db: DbSession) -> None:
    _days(
        db,
        [
            a_campaign_day(
                searchImpressionShare=0.42,
                searchBudgetLostImpressionShare=0.31,
                searchRankLostImpressionShare=0.27,
                searchAbsoluteTopImpressionShare=0.12,
            )
        ],
    )
    row = db.scalars(sa.select(CampaignDay)).one()
    assert (row.search_share, row.lost_to_budget, row.lost_to_rank, row.top_share) == (
        0.42,
        0.31,
        0.27,
        0.12,
    )
    assert not row.share_is_capped


def test_a_share_google_did_not_report_is_unknown_and_not_zero(db: DbSession) -> None:
    """Zero would read as "you were in none of the auctions". That is a different claim."""
    _days(db, [a_campaign_day()])
    row = db.scalars(sa.select(CampaignDay)).one()
    assert row.search_share is None
    assert row.lost_to_budget is None
    assert row.lost_to_rank is None
    assert not row.share_is_capped, "unknown is not capped either"


def test_ninety_percent_means_ninety_or_better_and_says_so(db: DbSession) -> None:
    """Google caps the figure. A screen printing 90% states what Google refused to."""
    _days(db, [a_campaign_day(searchImpressionShare=0.9)])
    assert db.scalars(sa.select(CampaignDay)).one().share_is_capped


def test_losing_to_budget_and_losing_to_rank_are_kept_apart(db: DbSession) -> None:
    """One is fixed by spending more. The other is not, and that matters."""
    _days(db, [a_campaign_day(searchBudgetLostImpressionShare=0.55)])
    row = db.scalars(sa.select(CampaignDay)).one()
    assert row.lost_to_budget == 0.55
    assert row.lost_to_rank is None, "nothing was said about rank, so nothing is claimed"
