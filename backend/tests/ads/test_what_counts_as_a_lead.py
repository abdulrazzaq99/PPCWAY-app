"""What counts as a lead, wherever conversions are read from Google.

Google counts whatever an account tells it to, page views included. These hold
every read to one definition (`ads.leads`): the day mirror, the search-term
mirror, the live campaign tabs and the audit. They also hold the runner to
re-reading days stored before the split, so a month of figures does not carry
page views as leads for a month.

Google is faked at the edge of each read. Its split queries are told apart by
the conversion category they ask for, which is the only thing that marks them.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.ads import runner
from ppcway.ads.leads import is_call, is_lead, leads_by
from ppcway.ads.mirror import CampaignDay, SearchTermDay
from ppcway.ads.stats import NO_ENQUIRIES_COUNTED, read_account
from ppcway.ads.summary import campaign_detail
from ppcway.ads.sync import Report, sync_days, sync_search_terms
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.org.models import Organization  # noqa: F401 - a foreign key target

NOW = datetime.now(UTC)
TODAY = NOW.date()
DAY = (TODAY - timedelta(days=2)).isoformat()
SPLIT = "conversion_action_category"


@pytest.fixture
def db() -> Any:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def google(answer: Any) -> httpx.Client:
    """Every query answered by `answer(query)`, a list of rows or a refusal."""

    def handle(request: httpx.Request) -> httpx.Response:
        said = answer(json.loads(request.content)["query"])
        if said is None:
            return httpx.Response(403, json={"error": {"code": 403, "message": "refused"}})
        return httpx.Response(200, json={"results": said})

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")


def split_row(category: str, conversions: float, **more: Any) -> dict[str, Any]:
    segments = {"date": DAY, "conversionActionCategory": category}
    return {"segments": segments, "metrics": {"conversions": conversions}, **more}


# ---------- the definition ----------


def test_page_views_and_basket_steps_are_not_leads() -> None:
    for category in ("PAGE_VIEW", "ENGAGEMENT", "ADD_TO_CART", "BEGIN_CHECKOUT"):
        assert not is_lead(category), category


def test_enquiries_calls_and_sales_are_leads() -> None:
    for category in (
        "SUBMIT_LEAD_FORM",
        "CONTACT",
        "SIGNUP",
        "REQUEST_QUOTE",
        "BOOK_APPOINTMENT",
        "PHONE_CALL_LEAD",
        "PURCHASE",
    ):
        assert is_lead(category), category
    assert is_call("PHONE_CALL_LEAD") and not is_call("SUBMIT_LEAD_FORM")


def test_a_category_nobody_chose_counts_rather_than_hiding_a_real_form() -> None:
    """ "Other" is where an enquiry form lands when its category was never set.
    Not counting it would make searches that bring enquiries look wasted."""
    assert is_lead("DEFAULT") and is_lead("UNKNOWN") and is_lead("")


def test_counted_but_no_leads_is_zero_not_missing() -> None:
    rows = [split_row("PAGE_VIEW", 9.0, campaign={"id": "11"})]
    assert leads_by(rows, lambda r: r["campaign"]["id"]) == {"11": 0.0}


# ---------- the day mirror ----------


def _days(db: DbSession, split: list[dict[str, Any]] | None) -> Report:
    money = [
        {
            "campaign": {"id": "11"},
            "segments": {"date": DAY},
            "metrics": {"impressions": "900", "clicks": "38", "costMicros": "20480000"},
        }
    ]
    return sync_days(
        db,
        "1",
        since=TODAY - timedelta(days=3),
        until=TODAY,
        access_token="a",
        developer_token="d",
        client=google(lambda q: split if SPLIT in q else money),
        now=NOW,
    )


def test_a_day_s_page_views_are_set_aside_not_counted_as_forms(db: DbSession) -> None:
    """PDFezy's new campaign: 38 clicks and 38 "leads", every one a page view."""
    _days(
        db,
        [
            split_row("PAGE_VIEW", 37.0, campaign={"id": "11"}),
            split_row("SUBMIT_LEAD_FORM", 1.0, campaign={"id": "11"}),
        ],
    )
    day = db.scalar(sa.select(CampaignDay))
    assert day is not None
    assert day.forms == 1.0 and day.calls == 0.0
    assert day.not_leads == 37.0


def test_a_day_google_would_not_split_stays_marked_unsplit(db: DbSession) -> None:
    _days(db, None)
    day = db.scalar(sa.select(CampaignDay))
    assert day is not None
    assert day.not_leads is None, "so the next backfill tries again"


# ---------- the search-term mirror ----------


def a_term(term: str, conversions: float) -> dict[str, Any]:
    return {
        "searchTermView": {"searchTerm": term, "status": "NONE"},
        "segments": {"date": DAY, "keyword": {"info": {"text": "pdf"}}},
        "campaign": {"id": "11"},
        "adGroup": {"id": "21"},
        "metrics": {
            "impressions": "300",
            "clicks": "40",
            "costMicros": "22000000",
            "conversions": conversions,
        },
    }


def term_split(term: str, category: str, conversions: float) -> dict[str, Any]:
    return split_row(
        category, conversions, searchTermView={"searchTerm": term}, adGroup={"id": "21"}
    )


def _terms(db: DbSession, terms: list[dict[str, Any]], split: Any) -> dict[str, float | None]:
    sync_search_terms(
        db,
        "1",
        since=TODAY - timedelta(days=3),
        until=TODAY,
        access_token="a",
        developer_token="d",
        client=google(lambda q: split if SPLIT in q else terms),
        now=NOW,
    )
    return {row.term: row.leads for row in db.scalars(sa.select(SearchTermDay))}


def test_each_search_keeps_how_many_of_its_conversions_were_leads(db: DbSession) -> None:
    held = _terms(
        db,
        [a_term("pdf editor jobs", 40.0), a_term("pdf to word", 41.0), a_term("free pdf", 0.0)],
        [
            term_split("pdf editor jobs", "PAGE_VIEW", 40.0),
            term_split("pdf to word", "PAGE_VIEW", 40.0),
            term_split("pdf to word", "SIGNUP", 1.0),
        ],
    )
    assert held == {"pdf editor jobs": 0.0, "pdf to word": 1.0, "free pdf": 0.0}


def test_a_refused_split_leaves_leads_unknown_never_zero(db: DbSession) -> None:
    """Zero would tell R1 that nobody got in touch, which is not known."""
    held = _terms(db, [a_term("pdf to word", 41.0), a_term("free pdf", 0.0)], None)
    assert held == {"pdf to word": None, "free pdf": 0.0}


def test_a_search_the_split_did_not_mention_is_unknown(db: DbSession) -> None:
    held = _terms(db, [a_term("pdf to word", 41.0)], [])
    assert held == {"pdf to word": None}


# ---------- re-reading what was stored before the split ----------


def test_days_stored_before_the_split_are_re_read_once_whole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The nightly backfill reads three days. A day stored with page views as
    leads would otherwise stay that way for a month."""
    from types import SimpleNamespace

    from pydantic import SecretStr

    from ppcway.ads import models as ads_models

    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    reached: list[date] = []

    def days(session: DbSession, customer_id: str, *, since: date, **_: Any) -> Report:
        reached.append(since)
        return Report(counts={"days": 1, "rows": 1})

    monkeypatch.setattr(runner, "sync_days", days)
    monkeypatch.setattr(runner, "sync_search_terms", lambda *a, **k: Report())
    monkeypatch.setattr(runner, "sync_keyword_days", lambda *a, **k: Report())
    monkeypatch.setattr(runner, "fresh_access_token", lambda *a, **k: "access")

    class Vault:
        def __init__(self, key: Any) -> None:
            pass

        def unlock(self, ciphertext: str) -> str:
            return "refresh"

    monkeypatch.setattr(runner, "TokenVault", Vault)
    settings: Any = SimpleNamespace(
        google_ads_developer_token=SecretStr("developer"),
        google_oauth_client_id="client",
        google_oauth_client_secret=SecretStr("secret"),
        google_oauth_token_key=None,
        google_ads_api_version="v25",
        google_ads_login_customer_id=None,
    )

    with factory() as session:
        person = UserAccount(google_sub=str(uuid.uuid4()), email="dana@pdfezy.com", name="Dana")
        session.add(person)
        session.flush()
        held = ads_models.AdsConnection(account_id=person.id, ciphertext="x", customer_id="1")
        session.add(held)
        # Read on 1 November, before page views were told apart.
        session.add(
            CampaignDay(
                customer_id="1",
                campaign_id="11",
                day=TODAY - timedelta(days=20),
                forms=38.0,
                not_leads=None,
                refreshed_at=NOW - timedelta(days=5),
            )
        )
        session.commit()

        runner.sync_connection(session, held, settings, kind="backfill", now=NOW)
        runner.sync_connection(session, held, settings, kind="backfill", now=NOW)

    whole = TODAY - timedelta(days=runner.FIRST_DAYS)
    assert reached[0] <= whole, "the first night reaches back the whole window"
    assert reached[1] > whole, "and once healed, back to three days"


# ---------- the live campaign tabs ----------


def test_a_campaign_s_searches_count_leads_and_page_views_do_not_save_them() -> None:
    def answer(query: str) -> list[dict[str, Any]]:
        if "FROM search_term_view" in query and SPLIT in query:
            return [
                term_split("pdf editor jobs", "PAGE_VIEW", 40.0),
                term_split("pdf to word", "SIGNUP", 2.0),
            ]
        if "FROM search_term_view" in query:
            return [
                {**a_term("pdf editor jobs", 40.0)},
                {**a_term("pdf to word", 42.0)},
            ]
        if "FROM campaign" in query and SPLIT not in query:
            return [{"campaign": {"id": "11", "name": "pdfezy"}, "metrics": {"conversions": 82}}]
        return []

    with google(answer) as client:
        found = campaign_detail("1", "11", access_token="a", developer_token="d", client=client)
    by_term = {t["term"]: t for t in found.terms}
    assert by_term["pdf editor jobs"]["leads"] == 0.0
    assert by_term["pdf editor jobs"]["waste"] is True
    assert by_term["pdf to word"]["leads"] == 2.0
    assert by_term["pdf to word"]["waste"] is False


# ---------- the audit ----------


def audit(answer: Any) -> Any:
    with google(answer) as client:
        return read_account("1", access_token="a", developer_token="d", client=client)


def spend_row() -> dict[str, Any]:
    return {
        "metrics": {"costMicros": "150000000", "clicks": 300, "conversions": 300},
        "customer": {"currencyCode": "USD"},
    }


def test_the_audit_does_not_let_page_views_excuse_a_wasted_search() -> None:
    def answer(query: str) -> list[dict[str, Any]]:
        if "FROM customer" in query and SPLIT in query:
            return [split_row("PAGE_VIEW", 298.0), split_row("SUBMIT_LEAD_FORM", 2.0)]
        if "FROM customer" in query:
            return [spend_row()]
        if "FROM search_term_view" in query and SPLIT in query:
            return [term_split("pdf editor jobs", "PAGE_VIEW", 40.0)]
        if "FROM search_term_view" in query:
            return [a_term("pdf editor jobs", 40.0)]
        return []

    reading = audit(answer)
    assert reading.wasted.read is True
    assert [row.term for row in reading.wasted.rows] == ["pdf editor jobs"]


def test_the_audit_says_it_cannot_judge_an_account_that_counts_no_enquiries() -> None:
    def answer(query: str) -> list[dict[str, Any]]:
        if "FROM customer" in query and SPLIT in query:
            return [split_row("PAGE_VIEW", 300.0)]
        if "FROM customer" in query:
            return [spend_row()]
        if "FROM search_term_view" in query and SPLIT in query:
            return [term_split("pdf to word", "PAGE_VIEW", 40.0)]
        if "FROM search_term_view" in query:
            return [a_term("pdf to word", 40.0)]
        return []

    reading = audit(answer)
    assert reading.wasted.read is False
    assert reading.wasted.trouble == NO_ENQUIRIES_COUNTED
    assert reading.wasted.rows == [], "not a list of its best searches called waste"
