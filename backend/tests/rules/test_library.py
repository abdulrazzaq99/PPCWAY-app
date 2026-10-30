"""R1 and R4 against a real mirror: what they find, and what they leave alone.

The leaving-alone half is most of the value. A rule that proposes excluding a
brand term, or a search somebody actually converted on, or something the
merchant excluded last week, is a rule they turn off.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, MirrorAd, SearchTermDay, term_key
from ppcway.auth.models import UserAccount  # noqa: F401 - a foreign key target
from ppcway.org.models import Organization  # noqa: F401 - a foreign key target
from ppcway.rules.catalogue import Risk, rule
from ppcway.rules.library import _confidence, disapproved_ads, wasteful_terms
from ppcway.rules.recommend import Recommendation

TODAY = date(2026, 10, 30)
AT = datetime(2026, 10, 30, 6, 0, tzinfo=UTC)
#: Enough that 1.5 x it is 60, so a 100-click term and a 60-spend term both
#: qualify and the two thresholds can be told apart.
TARGET = 40.0


@pytest.fixture
def db() -> Iterator[DbSession]:
    engine = sa.create_engine("sqlite://")
    from ppcway.db.base import Base

    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def a_term(
    db: DbSession,
    term: str,
    *,
    clicks: int = 120,
    spend: float = 90.0,
    conversions: float = 0.0,
    status: str = "NONE",
    day: date = date(2026, 10, 20),
    ad_group_id: str = "21",
) -> None:
    db.add(
        SearchTermDay(
            id=uuid.uuid4(),
            customer_id="1",
            campaign_id="11",
            ad_group_id=ad_group_id,
            day=day,
            term=term,
            term_hash=term_key(term),
            status=status,
            clicks=clicks,
            cost_micros=round(spend * MICRO),
            conversions=conversions,
            refreshed_at=AT,
        )
    )
    db.commit()


def _found(db: DbSession, **over: object) -> list[Recommendation]:
    kwargs: dict[str, object] = {
        "currency": "CAD",
        "target_cost_per_lead": TARGET,
        "today": TODAY,
    }
    kwargs.update(over)
    return wasteful_terms(db, "1", **kwargs)  # type: ignore[arg-type]


def test_a_search_that_cost_money_and_brought_nothing_is_found(db: DbSession) -> None:
    a_term(db, "boiler repair apprenticeship salary", clicks=140, spend=96.0)
    found = _found(db)
    assert len(found) == 1
    said = found[0]
    assert said.rule.id == "R1"
    assert said.target_label == "boiler repair apprenticeship salary"
    assert "none of them got in touch" in said.reason.lower()
    assert said.risk is Risk.LOW
    assert said.after == {"excluded": True, "match_type": "EXACT", "level": "ad_group"}


def test_a_search_somebody_converted_on_is_left_alone(db: DbSession) -> None:
    """The single most expensive mistake this rule could make."""
    a_term(db, "emergency plumber ennis", clicks=140, spend=96.0, conversions=2.0)
    assert _found(db) == []


@pytest.mark.parametrize("status", ["ADDED", "EXCLUDED", "ADDED_EXCLUDED"])
def test_a_search_the_merchant_has_already_handled_is_left_alone(
    db: DbSession, status: str
) -> None:
    """Recommending what somebody already did is how they stop reading the inbox."""
    a_term(db, "plumber jobs", clicks=140, spend=96.0, status=status)
    assert _found(db) == []


def test_the_latest_status_wins_not_any_status(db: DbSession) -> None:
    """Excluded last week means handled now, whatever it was a fortnight ago."""
    a_term(db, "plumber jobs", clicks=70, spend=48.0, status="NONE", day=date(2026, 10, 10))
    a_term(db, "plumber jobs", clicks=70, spend=48.0, status="EXCLUDED", day=date(2026, 10, 25))
    assert _found(db) == []


def test_pennies_are_not_worth_a_card(db: DbSession) -> None:
    """A cheap account with a low target must not start excluding trifles."""
    a_term(db, "plumber near me cheap", clicks=400, spend=12.0)
    assert _found(db) == []


def test_a_term_under_both_thresholds_is_not_called_a_loser(db: DbSession) -> None:
    """The brief's minimum: 1.5x the target in spend, or a hundred clicks."""
    a_term(db, "plumbing advice", clicks=40, spend=25.0)
    assert _found(db) == []


def test_enough_clicks_alone_qualifies(db: DbSession) -> None:
    a_term(db, "plumbing advice", clicks=110, spend=25.0)
    assert len(_found(db)) == 1


def test_enough_wasted_money_alone_qualifies(db: DbSession) -> None:
    """1.5 x 40 is 60, so 70 qualifies on nine clicks."""
    a_term(db, "plumbing advice", clicks=9, spend=70.0)
    assert len(_found(db)) == 1


def test_a_brand_term_is_protected_even_when_it_wastes_money(db: DbSession) -> None:
    a_term(db, "alpha plumbing ennis reviews", clicks=400, spend=200.0)
    assert _found(db, protected=["Alpha Plumbing"]) == []
    assert len(_found(db)) == 1, "and is found when nothing protects it"


def test_the_clients_blocked_list_is_honoured(db: DbSession) -> None:
    a_term(db, "boiler grant scheme", clicks=400, spend=200.0)
    assert _found(db, blocked=["grant"]) == []


def test_a_term_outside_the_window_is_not_counted(db: DbSession) -> None:
    a_term(db, "old news", clicks=400, spend=200.0, day=date(2026, 8, 1))
    assert _found(db) == []


def test_the_monthly_figure_is_the_window_scaled_not_the_window_total(
    db: DbSession,
) -> None:
    """A 30-day window is 30.4/30 of a month, so the two differ slightly."""
    a_term(db, "plumbing advice", clicks=140, spend=90.0)
    said = _found(db)[0]
    assert said.impact.money_a_month == pytest.approx(91.2, abs=0.05)
    assert "may move to better searches" in said.impact.words


def test_the_evidence_is_figure_ids_with_as_of_times(db: DbSession) -> None:
    """The brief's own definition of evidence."""
    a_term(db, "plumbing advice", clicks=140, spend=90.0)
    said = _found(db)[0]
    assert len(said.evidence) == 3
    for cite in said.evidence:
        assert cite["id"] and cite["as_of"]
    names = {cite["id"].split(":")[0] for cite in said.evidence}
    assert names == {"search_term_spend", "search_term_clicks", "search_term_leads"}


def test_meeting_the_minimum_is_not_the_same_as_being_certain(db: DbSession) -> None:
    """A card claiming certainty from the least qualifying data overstates itself."""
    assert _confidence(1.0) == pytest.approx(0.6)
    assert _confidence(2.0) == pytest.approx(1.0)
    assert _confidence(10.0) == 1.0, "and never above one"


def test_more_data_means_more_confidence(db: DbSession) -> None:
    a_term(db, "just qualifies", clicks=101, spend=61.0)
    a_term(db, "far past it", clicks=900, spend=600.0, ad_group_id="22")
    by_term = {r.target_label: r for r in _found(db)}
    assert by_term["just qualifies"].impact.confidence < by_term["far past it"].impact.confidence


def test_the_undo_says_what_does_not_come_back(db: DbSession) -> None:
    a_term(db, "plumbing advice", clicks=140, spend=90.0)
    assert "do not come back" in _found(db)[0].undo


def an_ad(
    db: DbSession,
    ad_id: str,
    *,
    approval: str = "DISAPPROVED",
    status: str = "ENABLED",
    ad_group_id: str = "21",
    gone: bool = False,
) -> None:
    db.add(
        MirrorAd(
            id=uuid.uuid4(),
            customer_id="1",
            resource_name=f"customers/1/adGroupAds/{ad_group_id}~{ad_id}",
            ad_id=ad_id,
            ad_group_id=ad_group_id,
            campaign_id="11",
            status=status,
            approval=approval,
            headlines=[f"Headline for {ad_id}"],
            seen_at=AT,
            gone_at=AT if gone else None,
        )
    )
    db.commit()


def test_a_refused_ad_is_found(db: DbSession) -> None:
    an_ad(db, "901")
    found = disapproved_ads(db, "1", currency="CAD", today=TODAY)
    assert len(found) == 1
    said = found[0]
    assert said.rule.id == "R4"
    assert said.after == {"status": "PAUSED"}
    assert said.pauses == 1
    assert said.impact.money_a_month == 0.0, "a refused ad is not spending anything"
    assert said.impact.confidence == 1.0, "Google told us; this is not an inference"


def test_the_only_ad_in_a_group_being_refused_is_blocking(db: DbSession) -> None:
    """Not a saving of any size. A thing that has stopped working."""
    an_ad(db, "901")
    said = disapproved_ads(db, "1", currency="CAD", today=TODAY)[0]
    assert said.impact.blocking
    assert "showing nothing at all" in said.reason
    assert "none of the traffic it is budgeted for" in said.impact.words


def test_a_refused_ad_beside_a_working_one_is_only_tidying(db: DbSession) -> None:
    an_ad(db, "901")
    an_ad(db, "902", approval="APPROVED")
    found = disapproved_ads(db, "1", currency="CAD", today=TODAY)
    assert len(found) == 1
    assert not found[0].impact.blocking
    assert "still running" in found[0].reason


@pytest.mark.parametrize("approval", ["APPROVED", "APPROVED_LIMITED"])
def test_an_approved_ad_is_left_alone(db: DbSession, approval: str) -> None:
    an_ad(db, "901", approval=approval)
    assert disapproved_ads(db, "1", currency="CAD", today=TODAY) == []


def test_an_already_paused_ad_is_not_proposed_again(db: DbSession) -> None:
    an_ad(db, "901", status="PAUSED")
    assert disapproved_ads(db, "1", currency="CAD", today=TODAY) == []


def test_an_ad_google_no_longer_returns_is_not_proposed(db: DbSession) -> None:
    an_ad(db, "901", gone=True)
    assert disapproved_ads(db, "1", currency="CAD", today=TODAY) == []


def test_pause_only_is_what_the_rule_says_it_is(db: DbSession) -> None:
    """The brief: R4, pause only. Nothing here may delete or rewrite an ad."""
    an_ad(db, "901")
    said = disapproved_ads(db, "1", currency="CAD", today=TODAY)[0]
    assert rule("R4").kind == "pause_ad"
    assert said.to_proposal().kind == "pause_ad"
    assert said.reversible
