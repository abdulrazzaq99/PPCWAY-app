"""Two ceilings, a transcript, and twelve months.

The two ceilings are different things and the tests keep them apart: a message
cap is about fairness between merchants on the same plan, and a spend ceiling
is about PPCWay's own solvency. One question about a year of search terms can
cost more than two hundred short ones, so a message cap alone does not bound
the bill -- which is the whole reason the brief asks for the second.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.chat.plans import ASSUMED, PLANS, WARN_AT, cost_of, plan_for
from ppcway.chat.transcript import (
    KEEP_MONTHS,
    Conversation,
    Turn,
    crossed_a_line,
    forget_old,
    open_conversation,
    record_turn,
    this_month,
)
from ppcway.db.base import Base
from ppcway.model.jobs import HAIKU, OPUS, SONNET
from ppcway.org.models import Organization

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )

    # SQLite does not enforce foreign keys unless told to, per connection, and
    # it ignores the pragma inside a transaction -- so it has to go on connect.
    # Production is Postgres, where a foreign key always bites; this is purely
    # so the cascade can be tested here at all.
    @sa.event.listens_for(engine, "connect")
    def _keys(connection: object, _record: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


@pytest.fixture
def world(db: sessionmaker[Session]) -> tuple[sessionmaker[Session], uuid.UUID, uuid.UUID]:
    with db() as session:
        place = Organization(name="Alpha Plumbing", plan="starter")
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add_all([place, person])
        session.commit()
        return db, place.id, person.id


def test_the_figures_are_still_ours_and_say_so() -> None:
    """The client's brief lists the caps and the AI ceiling as an open item for
    their call. Nobody should come to believe these were agreed."""
    assert ASSUMED is True


def test_an_unrecognised_plan_gets_the_most_cautious_one() -> None:
    """A business whose plan string was mistyped should be limited, not free."""
    assert plan_for("enterprise").name == "Starter"
    assert plan_for("").name == "Starter"
    assert plan_for("GROWTH").name == "Growth"


def test_a_bigger_plan_includes_more_of_both() -> None:
    starter, growth, agency = PLANS["starter"], PLANS["growth"], PLANS["agency"]
    assert starter.questions_a_month < growth.questions_a_month < agency.questions_a_month
    assert starter.spend_ceiling_usd < growth.spend_ceiling_usd < agency.spend_ceiling_usd


@pytest.mark.parametrize("model", [SONNET, HAIKU, OPUS])
def test_every_model_this_platform_uses_has_a_price(model: str) -> None:
    assert cost_of(model, input_tokens=1_000_000, output_tokens=0) > 0


def test_a_model_nobody_priced_costs_nothing_rather_than_guessing() -> None:
    """Zero is wrong and obvious. A made-up rate is wrong and invisible."""
    assert cost_of("claude-something-new", input_tokens=1_000_000, output_tokens=100) == 0.0


def test_cached_input_is_cheaper_not_extra() -> None:
    """Anthropic reports cached tokens separately from fresh ones. Adding them
    on top of the input count would overstate every cached call."""
    fresh = cost_of(SONNET, input_tokens=10_000, output_tokens=100)
    mostly_cached = cost_of(SONNET, input_tokens=1_000, output_tokens=100, cached=9_000)
    assert mostly_cached < fresh


def test_haiku_is_far_cheaper_than_opus() -> None:
    """The whole reason the jobs are split across three models."""
    same = {"input_tokens": 100_000, "output_tokens": 2_000}
    assert cost_of(HAIKU, **same) * 10 < cost_of(OPUS, **same)


def test_a_turn_is_written_down_with_what_it_took(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="2580586343",
            about="why did my cost per lead go up?",
            now=NOW,
        )
        turn = record_turn(
            session,
            conversation_id=held.id,
            organization_id=place,
            question="why did my cost per lead go up?",
            answer="Fewer of your clicks got in touch.",
            answer_from="model",
            tools_used=["get_metrics", "explain_change"],
            figure_ids=["cost_per_lead:account:2026-10-04..2026-11-02"],
            invented=[],
            model=SONNET,
            input_tokens=4_000,
            output_tokens=150,
            cached_tokens=3_000,
            took_ms=2_400,
            now=NOW,
        )
    assert turn.tools_used == {"tools": ["get_metrics", "explain_change"]}
    assert turn.figures is not None and turn.figures["ids"]
    assert turn.cost_usd > 0
    assert turn.answer_from == "model"


def test_which_tools_ran_is_kept_because_a_dispute_turns_on_it(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """Was the model wrong, or the mirror? Without the lookups, unanswerable."""
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW,
        )
        turn = record_turn(
            session,
            conversation_id=held.id,
            organization_id=place,
            question="how many leads?",
            answer="Thirty.",
            answer_from="model",
            tools_used=["get_metrics"],
            figure_ids=["leads:account:2026-10-04..2026-11-02"],
            invented=[],
            now=NOW,
        )
    assert turn.tools_used == {"tools": ["get_metrics"]}


def test_a_refused_turn_is_recorded_too(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """A transcript of the answers that worked is not a transcript, and the
    turns that failed are the ones somebody asks about."""
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW,
        )
        turn = record_turn(
            session,
            conversation_id=held.id,
            organization_id=place,
            question="what are my competitors bidding?",
            answer="I could not write that up reliably.",
            answer_from="template",
            tools_used=["get_auction_insights"],
            figure_ids=[],
            invented=[4200.0],
            now=NOW,
        )
    assert turn.answer_from == "template"
    assert turn.invented == {"numbers": [4200.0]}


def test_the_month_counts_both_ceilings(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW,
        )
        for _ in range(3):
            record_turn(
                session,
                conversation_id=held.id,
                organization_id=place,
                question="q",
                answer="a",
                answer_from="model",
                tools_used=[],
                figure_ids=[],
                invented=[],
                model=SONNET,
                input_tokens=10_000,
                output_tokens=200,
                now=NOW,
            )
        spend = this_month(session, place, now=NOW)
    assert spend.questions == 3
    assert spend.questions_allowed == PLANS["starter"].questions_a_month
    assert spend.used_usd > 0
    assert spend.may_ask


def test_running_out_of_questions_says_so_without_blaming_the_merchant(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW,
        )
        for _ in range(PLANS["starter"].questions_a_month):
            record_turn(
                session,
                conversation_id=held.id,
                organization_id=place,
                question="q",
                answer="a",
                answer_from="model",
                tools_used=[],
                figure_ids=[],
                invented=[],
                now=NOW,
            )
        spend = this_month(session, place, now=NOW)
    assert spend.out_of_questions
    assert not spend.may_ask
    assert "starts again next month" in spend.because


def test_reaching_the_spend_ceiling_does_not_say_the_merchant_overspent(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """They have spent nothing. It is PPCWay's own ceiling, and the wording
    must not read as a bill they have run up."""
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW,
        )
        record_turn(
            session,
            conversation_id=held.id,
            organization_id=place,
            question="q",
            answer="a",
            answer_from="model",
            tools_used=[],
            figure_ids=[],
            invented=[],
            model=OPUS,
            # Enough tokens to pass a twelve-dollar ceiling in one turn.
            input_tokens=4_000_000,
            output_tokens=100_000,
            now=NOW,
        )
        spend = this_month(session, place, now=NOW)
    assert spend.spent_out
    assert not spend.may_ask
    assert "nothing about your ads has changed" in spend.because
    assert "you have spent" not in spend.because.lower()


def test_last_month_does_not_count_against_this_one(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW,
        )
        record_turn(
            session,
            conversation_id=held.id,
            organization_id=place,
            question="q",
            answer="a",
            answer_from="model",
            tools_used=[],
            figure_ids=[],
            invented=[],
            model=SONNET,
            input_tokens=100_000,
            output_tokens=1_000,
            now=NOW - timedelta(days=40),
        )
        spend = this_month(session, place, now=NOW)
    assert spend.questions == 0 and spend.used_usd == 0.0


@pytest.mark.parametrize("line", WARN_AT)
def test_each_threshold_is_noticed_once_as_it_is_crossed(line: float) -> None:
    """The brief's half and four fifths. Compared before and after rather than
    read from a flag, so there is no counter to keep in step."""
    from ppcway.chat.transcript import Spend

    before = Spend(used_usd=line * 10 - 0.01, ceiling_usd=10.0, questions=1, questions_allowed=100)
    after = Spend(used_usd=line * 10, ceiling_usd=10.0, questions=2, questions_allowed=100)
    assert crossed_a_line(before, after) == line
    assert crossed_a_line(after, after) is None, "and not again once past it"


def test_twelve_months_is_the_window() -> None:
    assert KEEP_MONTHS == 12


def test_transcripts_past_a_year_are_forgotten(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW - timedelta(days=400),
        )
        recent = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="y",
            now=NOW,
        )
        for when, into in ((NOW - timedelta(days=400), held), (NOW, recent)):
            record_turn(
                session,
                conversation_id=into.id,
                organization_id=place,
                question="q",
                answer="a",
                answer_from="model",
                tools_used=[],
                figure_ids=[],
                invented=[],
                now=when,
            )

        gone = forget_old(session, now=NOW)
        session.commit()
        left_turns = session.scalars(sa.select(Turn)).all()
        left_talks = session.scalars(sa.select(Conversation)).all()

    assert gone == 1
    assert len(left_turns) == 1
    assert len(left_talks) == 1, "and the emptied conversation went with its turns"


def test_deleting_a_business_takes_its_transcripts(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """By a foreign key, not a job: a sweep that is paused breaks the promise."""
    db, place, person = world
    with db() as session:
        held = open_conversation(
            session,
            organization_id=place,
            account_id=person,
            customer_id="1",
            about="x",
            now=NOW,
        )
        record_turn(
            session,
            conversation_id=held.id,
            organization_id=place,
            question="q",
            answer="a",
            answer_from="model",
            tools_used=[],
            figure_ids=[],
            invented=[],
            now=NOW,
        )
        # Core rather than raw text, so the UUID binds in whatever shape the
        # dialect stores it: the first version of this used a text DELETE with
        # the dashed form, matched nothing on SQLite, and "nothing cascaded"
        # looked exactly like "the cascade is broken". Core rather than the ORM
        # so the database does the cascading rather than SQLAlchemy.
        session.execute(sa.delete(Organization).where(Organization.id == place))
        session.commit()
        # The rows are gone from the database; the session still holds them in
        # its identity map, which would make this pass or fail for the wrong
        # reason either way.
        session.expire_all()
        assert session.get(Organization, place) is None, "the business really went"
        assert session.scalars(sa.select(Turn)).all() == []
        assert session.scalars(sa.select(Conversation)).all() == []
