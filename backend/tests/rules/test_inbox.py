"""The inbox: the cards, their order, and what an empty one says.

An empty inbox is three different situations and a merchant deserves to know
which. "Nothing to do" for all three would be wrong twice.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, SearchTermDay, SyncRun, term_key
from ppcway.auth.models import UserAccount  # noqa: F401 - a foreign key target
from ppcway.db.base import Base
from ppcway.model.jobs import SONNET, Job
from ppcway.opt.models import OptimizationAction, Status
from ppcway.org.models import Organization
from ppcway.rules.inbox import cards_for
from ppcway.rules.words import FROM_MODEL, FROM_TEMPLATE

TODAY = date(2026, 10, 30)
NOW = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[DbSession]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def read_ok(db: DbSession, *, status: str = "done") -> None:
    db.add(
        SyncRun(
            id=uuid.uuid4(),
            customer_id="1",
            kind="today",
            status=status,
            started_at=NOW - timedelta(hours=3),
            finished_at=NOW - timedelta(hours=2),
            trouble="quota exhausted" if status == "failed" else "",
        )
    )
    db.commit()


def wasteful(db: DbSession, term: str, *, spend: float = 90.0) -> None:
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
            clicks=140,
            cost_micros=round(spend * MICRO),
            conversions=0.0,
            refreshed_at=NOW - timedelta(hours=2),
        )
    )
    db.commit()


def used_up(db: DbSession, how_many: int) -> None:
    place = Organization(name="Alpha")
    db.add(place)
    db.flush()
    for n in range(how_many):
        db.add(
            OptimizationAction(
                id=uuid.uuid4(),
                organization_id=place.id,
                customer_id="1",
                kind="add_negative_keyword",
                status=Status.APPLIED.value,
                created_at=NOW - timedelta(days=1),
                target_id=f"earlier-{n}",
            )
        )
    db.commit()


class Saying:
    def __init__(self, text: str) -> None:
        self.text = text
        self.asked = 0

    def ask(self, job: Job, **kwargs: object) -> object:
        from ppcway.model.service import Answer

        self.asked += 1
        return Answer(text=self.text, model=SONNET, prompt_version="otto-test")


def _inbox(db: DbSession, **over: object) -> object:
    kwargs: dict[str, object] = {
        "currency": "CAD",
        "target_cost_per_lead": 40.0,
        "today": TODAY,
        "now": NOW,
    }
    kwargs.update(over)
    return cards_for(db, "1", **kwargs)  # type: ignore[arg-type]


def test_a_card_carries_everything_the_brief_asks_for(db: DbSession) -> None:
    """Reason, evidence, expected impact, risk route and undo plan."""
    read_ok(db)
    wasteful(db, "boiler repair jobs")
    said = _inbox(db).cards[0].as_dict()  # type: ignore[attr-defined]
    assert said["reason"]
    assert said["evidence"] and all(cite["id"] and cite["as_of"] for cite in said["evidence"])
    assert said["impact"]["money_a_month"] > 0
    assert said["impact"]["words"]
    assert said["risk"] == "low"
    assert said["route"] == "owner"
    assert said["undo"]
    assert said["rule_id"] == "R1" and said["rule_version"] == 1


def test_without_a_model_the_computed_words_are_used(db: DbSession) -> None:
    """Opening the inbox never waits on a model."""
    read_ok(db)
    wasteful(db, "boiler repair jobs")
    card = _inbox(db).cards[0]  # type: ignore[attr-defined]
    assert card.words.source == FROM_TEMPLATE
    assert card.words.is_ours
    assert card.words.asked == 0, "nothing was asked of a model"
    assert "boiler repair jobs" in card.words.text


def test_given_a_model_the_words_are_rewritten_and_checked(db: DbSession) -> None:
    read_ok(db)
    wasteful(db, "boiler repair jobs")
    models = Saying("140 clicks on that search cost you 90.00 CAD and nobody rang.")
    card = _inbox(db, models=models).cards[0]  # type: ignore[attr-defined]
    assert card.words.source == FROM_MODEL
    assert models.asked == 1
    assert card.as_dict()["reason_is_ours"] is False


def test_an_invented_figure_from_the_model_never_reaches_a_card(db: DbSession) -> None:
    read_ok(db)
    wasteful(db, "boiler repair jobs")
    models = Saying("That search cost 90.00 CAD and lost you 14 leads.")
    card = _inbox(db, models=models).cards[0]  # type: ignore[attr-defined]
    assert card.words.source == FROM_TEMPLATE
    assert "14 leads" not in card.words.text
    assert card.as_dict()["reason_is_ours"] is True


def test_nothing_found_says_so_plainly(db: DbSession) -> None:
    read_ok(db)
    said = _inbox(db)
    assert said.cards == ()  # type: ignore[attr-defined]
    assert said.nothing_because == "We looked and found nothing worth changing."  # type: ignore[attr-defined]


def test_an_empty_inbox_because_the_week_is_full_says_that_instead(
    db: DbSession,
) -> None:
    """Different silence, different sentence."""
    read_ok(db)
    used_up(db, 10)
    wasteful(db, "boiler repair jobs")
    said = _inbox(db)
    assert said.cards == ()  # type: ignore[attr-defined]
    assert said.held_back == 1  # type: ignore[attr-defined]
    assert "already used" in said.nothing_because  # type: ignore[attr-defined]


def test_an_empty_inbox_because_the_read_failed_says_that(db: DbSession) -> None:
    read_ok(db, status="failed")
    wasteful(db, "boiler repair jobs")
    said = _inbox(db)
    assert said.cards == ()  # type: ignore[attr-defined]
    assert "last read of this account failed" in said.nothing_because  # type: ignore[attr-defined]


def test_the_inbox_says_which_rules_ran_and_which_are_missing(db: DbSession) -> None:
    """So a status screen can be honest rather than implying five of five."""
    read_ok(db)
    said = _inbox(db).as_dict()  # type: ignore[attr-defined]
    assert said["ran"] == ["R1", "R4"]
    assert said["not_specified"] == ["R2", "R3", "R5"]


def test_the_best_card_is_first(db: DbSession) -> None:
    read_ok(db)
    wasteful(db, "small waste", spend=70.0)
    wasteful(db, "large waste", spend=600.0)
    said = _inbox(db)
    assert said.cards[0].found.target_label == "large waste"  # type: ignore[attr-defined]


def test_the_inbox_writes_nothing(db: DbSession) -> None:
    read_ok(db)
    wasteful(db, "boiler repair jobs")
    _inbox(db)
    assert db.scalars(sa.select(OptimizationAction)).all() == []
