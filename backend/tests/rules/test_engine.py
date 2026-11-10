"""The daily pass: what it offers, what it holds back, and when it refuses to run."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, MirrorAd, SearchTermDay, SyncRun, term_key
from ppcway.auth.models import UserAccount  # noqa: F401 - a foreign key target
from ppcway.db.base import Base
from ppcway.opt.models import OptimizationAction, Status
from ppcway.org.models import Organization
from ppcway.rules.catalogue import rule
from ppcway.rules.engine import MOST_A_WEEK, Pass, run
from ppcway.rules.recommend import Impact, Recommendation, in_order

TODAY = date(2026, 10, 30)
NOW = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)
TARGET = 40.0


@pytest.fixture
def db() -> Iterator[DbSession]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def a_good_sync(db: DbSession, *, status: str = "done", hours_ago: int = 2) -> None:
    db.add(
        SyncRun(
            id=uuid.uuid4(),
            customer_id="1",
            kind="today",
            status=status,
            started_at=NOW - timedelta(hours=hours_ago + 1),
            finished_at=None if status != "done" else NOW - timedelta(hours=hours_ago),
            trouble="quota exhausted" if status == "failed" else "",
        )
    )
    db.commit()


def wasteful(db: DbSession, term: str, *, spend: float = 90.0, clicks: int = 140) -> None:
    db.add(
        SearchTermDay(
            id=uuid.uuid4(),
            customer_id="1",
            campaign_id="11",
            ad_group_id="21",
            day=date(2026, 10, 20),
            term=term,
            term_hash=term_key(term),
            status="NONE",
            clicks=clicks,
            cost_micros=round(spend * MICRO),
            conversions=0.0,
            refreshed_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()


def a_refused_ad(db: DbSession, ad_id: str, *, ad_group_id: str = "21") -> None:
    db.add(
        MirrorAd(
            id=uuid.uuid4(),
            customer_id="1",
            resource_name=f"customers/1/adGroupAds/{ad_group_id}~{ad_id}",
            ad_id=ad_id,
            ad_group_id=ad_group_id,
            campaign_id="11",
            status="ENABLED",
            approval="DISAPPROVED",
            headlines=["Refused headline"],
            seen_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()


def already_changed(db: DbSession, how_many: int, *, status: str = Status.APPLIED.value) -> None:
    place = Organization(name="Alpha Plumbing")
    db.add(place)
    db.flush()
    for n in range(how_many):
        db.add(
            OptimizationAction(
                id=uuid.uuid4(),
                organization_id=place.id,
                customer_id="1",
                kind="add_negative_keyword",
                status=status,
                created_at=NOW - timedelta(days=1),
                target_id=f"earlier-{n}",
            )
        )
    db.commit()


def _run(db: DbSession, **over: object) -> Pass:
    kwargs: dict[str, object] = {
        "currency": "CAD",
        "target_cost_per_lead": TARGET,
        "today": TODAY,
        "now": NOW,
    }
    kwargs.update(over)
    return run(db, "1", **kwargs)  # type: ignore[arg-type]


def test_a_pass_offers_what_the_rules_found(db: DbSession) -> None:
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    a_refused_ad(db, "901")
    said = _run(db)
    assert said.ok
    assert said.ran == ("R1", "R4", "R6", "R7")
    assert len(said.offered) == 2
    assert said.held_back == ()


def test_the_rules_the_client_has_not_specified_are_named_and_not_run(
    db: DbSession,
) -> None:
    """So a status screen can be honest about what is missing."""
    a_good_sync(db)
    said = _run(db)
    assert said.not_specified == ("R2", "R3", "R5")
    assert "R2" not in said.ran


def test_nothing_is_ever_emitted_for_an_unimplemented_rule(db: DbSession) -> None:
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    said = _run(db)
    emitted = {found.rule.id for found in said.offered}
    assert emitted <= {"R1", "R4"}
    for found in said.offered:
        assert rule(found.rule.id).implemented


def test_ten_a_week_is_the_most_a_merchant_is_asked_to_read(db: DbSession) -> None:
    """Forty cards on a neglected account is how an inbox stops being opened."""
    a_good_sync(db)
    for n in range(14):
        wasteful(db, f"wasteful search {n}", spend=90.0 + n)
    said = _run(db)
    assert len(said.offered) == MOST_A_WEEK
    assert len(said.held_back) == 4
    assert said.room_left == MOST_A_WEEK


def test_changes_already_made_this_week_use_up_the_allowance(db: DbSession) -> None:
    a_good_sync(db)
    already_changed(db, 7)
    for n in range(6):
        wasteful(db, f"wasteful search {n}", spend=90.0 + n)
    said = _run(db)
    assert said.used_this_week == 7
    assert len(said.offered) == 3
    assert len(said.held_back) == 3


def test_a_proposal_still_waiting_counts_against_the_allowance(db: DbSession) -> None:
    """It is a card the merchant has already been asked to read."""
    a_good_sync(db)
    already_changed(db, 10, status=Status.PROPOSED.value)
    wasteful(db, "boiler repair jobs")
    said = _run(db)
    assert said.used_this_week == 10
    assert said.offered == ()
    assert len(said.held_back) == 1


def test_a_refused_change_does_not_use_up_the_allowance(db: DbSession) -> None:
    """It never happened. Counting it would spend a merchant's allowance on nothing."""
    a_good_sync(db)
    already_changed(db, 10, status=Status.REJECTED.value)
    wasteful(db, "boiler repair jobs")
    said = _run(db)
    assert said.used_this_week == 0
    assert len(said.offered) == 1


def test_the_most_expensive_finding_comes_first(db: DbSession) -> None:
    a_good_sync(db)
    wasteful(db, "small waste", spend=70.0, clicks=105)
    wasteful(db, "large waste", spend=600.0, clicks=900)
    said = _run(db)
    assert said.offered[0].target_label == "large waste"


def test_something_that_has_stopped_working_sorts_ahead_of_any_saving(
    db: DbSession,
) -> None:
    """An ad group showing nothing is not a saving of any size."""
    a_good_sync(db)
    wasteful(db, "large waste", spend=600.0, clicks=900)
    a_refused_ad(db, "901")
    said = _run(db)
    first = said.offered[0]
    assert first.rule.id == "R4"
    assert first.impact.blocking
    assert first.priority == 0.0, "and it gets there on the flag, not on a made-up figure"


@pytest.mark.parametrize(
    ("status", "says"),
    [("failed", "last read of this account failed"), ("running", "half a picture")],
)
def test_nothing_is_proposed_while_the_sync_is_in_trouble(
    db: DbSession, status: str, says: str
) -> None:
    """The brief: no decision while sync is failing."""
    a_good_sync(db, status=status)
    wasteful(db, "boiler repair jobs")
    said = _run(db)
    assert not said.ok
    assert says in said.stopped
    assert said.offered == ()


def test_nothing_is_proposed_on_figures_older_than_the_limit(db: DbSession) -> None:
    a_good_sync(db, hours_ago=40)
    wasteful(db, "boiler repair jobs")
    said = _run(db)
    assert not said.ok
    assert "36-hour limit" in said.stopped


def test_an_account_never_read_proposes_nothing(db: DbSession) -> None:
    wasteful(db, "boiler repair jobs")
    said = _run(db)
    assert not said.ok
    assert "never been read" in said.stopped


def test_the_whole_pass_is_refused_rather_than_forty_cards_one_at_a_time(
    db: DbSession,
) -> None:
    """Every figure being stale for the same reason is one refusal, not forty."""
    a_good_sync(db, status="failed")
    for n in range(14):
        wasteful(db, f"wasteful search {n}")
    said = _run(db)
    assert said.offered == () and said.held_back == ()


def test_the_pass_writes_nothing(db: DbSession) -> None:
    """Phase 1 is "shown not applied". The log records a decision not made here."""
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    _run(db)
    assert db.scalars(sa.select(OptimizationAction)).all() == []


def test_a_recommendation_narrows_into_what_the_guardrails_judge(db: DbSession) -> None:
    a_good_sync(db)
    a_refused_ad(db, "901")
    said = _run(db).offered[0]
    proposal = said.to_proposal()
    assert proposal.kind == "pause_ad"
    assert proposal.customer_id == "1"
    assert proposal.pauses == 1
    assert proposal.metrics_as_of == said.as_of
    assert proposal.new_daily_budget is None, "pausing an ad touches no number"


def test_risk_only_breaks_ties_and_does_not_reorder_the_list() -> None:
    """Money dominates. A safe change is slightly preferred at equal money."""
    from ppcway.rules.catalogue import CATALOGUE

    def made_up(money: float, rule_id: str) -> Recommendation:
        return Recommendation(
            rule=CATALOGUE[rule_id],
            customer_id="1",
            target_kind="x",
            target_id="x",
            target_label="x",
            reason="x",
            impact=Impact(money_a_month=money, currency="CAD", confidence=1.0, words="x"),
            figures=(),
            undo="x",
        )

    big_risky, small_safe = made_up(500.0, "R1"), made_up(10.0, "R1")
    assert in_order([small_safe, big_risky])[0] is big_risky


def an_answer(
    db: DbSession,
    term: str,
    status: str,
    *,
    days_ago: float = 1,
    by_a_person: bool = False,
    applied_days_ago: float | None = None,
    reverted_days_ago: float | None = None,
) -> None:
    """A row in the log for one search, in whatever state a test needs."""
    place = Organization(name=f"Alpha Plumbing {uuid.uuid4().hex[:6]}")
    db.add(place)
    db.flush()
    db.add(
        OptimizationAction(
            organization_id=place.id,
            customer_id="1",
            kind="add_negative_keyword",
            target_kind="search_term",
            target_id=term_key(term),
            target_label=term,
            status=status,
            rule_id="R1",
            created_at=NOW - timedelta(days=days_ago),
            rechecked={"verdict": "rejected", "check": "person"} if by_a_person else None,
            applied_at=(
                NOW - timedelta(days=applied_days_ago) if applied_days_ago is not None else None
            ),
            reverted_at=(
                NOW - timedelta(days=reverted_days_ago) if reverted_days_ago is not None else None
            ),
        )
    )
    db.commit()


def _terms(said: Pass) -> list[str]:
    return [one.target_label for one in said.offered]


@pytest.mark.parametrize(
    "status",
    [Status.PROPOSED.value, Status.AWAITING_APPROVAL.value, Status.APPROVED.value],
)
def test_a_change_already_offered_or_approved_is_not_offered_again(
    db: DbSession, status: str
) -> None:
    """Until 5 November every night offered the same search again beside the
    card already waiting -- and, once changes are sent, beside the approved
    one, which would be two attempts at one exclusion."""
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    an_answer(db, "boiler repair jobs", status, days_ago=20)
    assert _terms(_run(db)) == []


def test_a_change_declined_this_week_is_not_offered_again(db: DbSession) -> None:
    """The inbox tells somebody who says no: "Otto will not propose that one
    again this week." Nothing made that true."""
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    an_answer(db, "boiler repair jobs", Status.REJECTED.value, days_ago=2, by_a_person=True)
    assert _terms(_run(db)) == []


def test_a_change_declined_more_than_a_week_ago_may_be_offered_again(db: DbSession) -> None:
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    an_answer(db, "boiler repair jobs", Status.REJECTED.value, days_ago=8, by_a_person=True)
    assert _terms(_run(db)) == ["boiler repair jobs"]


def test_a_change_a_guardrail_refused_may_be_offered_again(db: DbSession) -> None:
    """Refused on yesterday's figures, it may pass on today's."""
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    an_answer(db, "boiler repair jobs", Status.REJECTED.value, days_ago=1)
    assert _terms(_run(db)) == ["boiler repair jobs"]


def test_an_offer_nobody_answered_is_offered_again(db: DbSession) -> None:
    """Expired is not declined: "Otto will propose it again if it is still worth doing"."""
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    an_answer(db, "boiler repair jobs", Status.EXPIRED.value, days_ago=8)
    assert _terms(_run(db)) == ["boiler repair jobs"]


def test_a_change_just_made_or_just_put_back_is_left_alone(db: DbSession) -> None:
    """Made: Google's report can take days to show the search as excluded.
    Put back: the merchant undid it, and offering it again would be arguing."""
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    wasteful(db, "free plumbing course")
    an_answer(db, "boiler repair jobs", Status.APPLIED.value, days_ago=3, applied_days_ago=2)
    an_answer(
        db,
        "free plumbing course",
        Status.REVERTED.value,
        days_ago=9,
        applied_days_ago=8,
        reverted_days_ago=4,
    )
    assert _terms(_run(db)) == []


def test_a_change_google_refused_is_not_retried_every_night(db: DbSession) -> None:
    a_good_sync(db)
    wasteful(db, "boiler repair jobs")
    an_answer(db, "boiler repair jobs", Status.FAILED.value, days_ago=2)
    assert _terms(_run(db)) == []
