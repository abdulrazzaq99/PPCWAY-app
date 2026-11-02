"""Writing a judged proposal into the log, and letting an unanswered one lapse.

The ordering is the property: a row exists, with `before` captured, before
anybody acts. These check what the row says, and that what it says is enough
to explain the change months later without the code that produced it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.metric.figures import Figure, Period, Scope, Unit
from ppcway.opt.consent import give
from ppcway.opt.guardrails import Judgement, Ruling, Verdict
from ppcway.opt.models import (
    APPROVAL_EXPIRES_DAYS,
    Autonomy,
    OptimizationAction,
    ProposedBy,
    Risk,
    Status,
)
from ppcway.opt.record import expire_old, waiting_for, write_proposal
from ppcway.org.models import Organization, Role
from ppcway.rules.catalogue import CATALOGUE
from ppcway.rules.recommend import Impact, Recommendation

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
WINDOW = Period.last(30, until=date(2026, 11, 1))


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def a_business(session: Session) -> uuid.UUID:
    place = Organization(name="Alpha Plumbing")
    session.add(place)
    session.flush()
    return place.id


def a_card(rule_id: str = "R1") -> Recommendation:
    spec = CATALOGUE[rule_id]
    return Recommendation(
        rule=spec,
        customer_id="2580586343",
        target_kind="search_term",
        target_label="boiler repair jobs",
        target_id="abc123",
        reason="Nobody who searched that got in touch.",
        impact=Impact(
            money_a_month=91.2,
            currency="CAD",
            confidence=0.8,
            words="Excluding it stops about 91.20 CAD a month.",
        ),
        figures=(
            Figure(
                name="search_term_spend",
                value=90.0,
                unit=Unit.MONEY,
                currency="CAD",
                period=WINDOW,
                scope=Scope(kind="search_term", id="abc123"),
                as_of=NOW - timedelta(hours=2),
            ),
        ),
        undo="Remove the negative keyword and it can match again.",
        before={"excluded": False},
        after={"excluded": True},
        as_of=NOW - timedelta(hours=2),
    )


def allowed() -> Judgement:
    return Judgement(Ruling(Verdict.APPROVED, "", "Within every limit set for this account."))


def needs_a_person() -> Judgement:
    return Judgement(Ruling(Verdict.REQUIRES_APPROVAL, "autonomy_level", "You asked to be asked."))


def refused() -> Judgement:
    return Judgement(Ruling(Verdict.REJECTED, "hard_spend_limits", "Past the daily ceiling."))


def _write(db: sessionmaker[Session], said: Judgement, **over: object) -> OptimizationAction:
    with db() as session:
        place = a_business(session)
        kwargs: dict[str, object] = {
            "organization_id": place,
            "guardrail_config_version": 3,
            "job_run": "nightly-2026-11-02",
            "now": NOW,
        }
        kwargs.update(over)
        row = write_proposal(session, a_card(), said, **kwargs)  # type: ignore[arg-type]
        session.commit()
        return row


def test_the_row_can_explain_itself_months_later(db: sessionmaker[Session]) -> None:
    """Everything the brief lists, present without the code that produced it."""
    row = _write(db, needs_a_person())

    assert row.kind == "add_negative_keyword"
    assert row.before == {"excluded": False} and row.after == {"excluded": True}
    assert row.reason
    assert row.evidence and row.evidence["figures"][0]["id"].startswith("search_term_spend:")
    assert row.evidence["figures"][0]["as_of"]
    assert row.expected_impact and row.expected_impact["money_a_month"] == 91.2
    assert row.undo_plan.startswith("Remove the negative keyword")
    assert (row.rule_id, row.rule_version) == ("R1", 1)
    assert row.guardrail_config_version == 3
    assert row.window_start == WINDOW.start and row.window_end == WINDOW.end
    assert row.risk == Risk.LOW.value
    assert row.route == "owner"
    assert row.proposed_by == ProposedBy.RULE.value
    assert row.job_run == "nightly-2026-11-02"


def test_which_guardrail_decided_and_why_is_kept(db: sessionmaker[Session]) -> None:
    row = _write(db, refused())
    assert row.status == Status.REJECTED.value
    assert row.decided_by == "hard_spend_limits"
    assert "daily ceiling" in row.decided_because


def test_approve_first_is_the_default_even_when_the_guardrails_allow_it(
    db: sessionmaker[Session],
) -> None:
    """The guardrails saying yes is not a merchant saying yes."""
    row = _write(db, allowed())
    assert row.status == Status.AWAITING_APPROVAL.value


def test_five_things_must_agree_before_a_change_goes_unasked(
    db: sessionmaker[Session],
) -> None:
    """The guardrails, the flag, the autonomy level, the change type, and a
    live consent record that covers it. All five, and this is all five."""
    with db() as session:
        place = a_business(session)
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add(person)
        session.flush()
        give(
            session,
            organization_id=place,
            account_id=person.id,
            role=Role.OWNER,
            ip="203.0.113.7",
        )
        row = write_proposal(
            session,
            a_card(),
            allowed(),
            organization_id=place,
            guardrail_config_version=3,
            autonomy=Autonomy.FULL_AUTO.value,
            auto_apply_flag=True,
            now=NOW,
        )
        session.commit()
    assert row.status == Status.APPROVED.value


@pytest.mark.parametrize(
    ("missing", "says"),
    [
        ("flag", "not making changes on its own yet"),
        ("autonomy", "without being asked first"),
        ("consent", "Nobody has agreed"),
    ],
)
def test_any_one_of_the_five_missing_means_a_person_is_asked(
    db: sessionmaker[Session], missing: str, says: str
) -> None:
    """And the row says which one, because otherwise the most common status in
    the log would carry no explanation at all."""
    with db() as session:
        place = a_business(session)
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add(person)
        session.flush()
        if missing != "consent":
            give(
                session,
                organization_id=place,
                account_id=person.id,
                role=Role.OWNER,
            )
        row = write_proposal(
            session,
            a_card(),
            allowed(),
            organization_id=place,
            guardrail_config_version=3,
            autonomy=(
                Autonomy.APPROVE_FIRST.value if missing == "autonomy" else Autonomy.FULL_AUTO.value
            ),
            auto_apply_flag=missing != "flag",
            now=NOW,
        )
        session.commit()
    assert row.status == Status.AWAITING_APPROVAL.value
    assert says in row.decided_because


def test_a_type_the_client_has_not_named_still_waits_for_a_person(
    db: sessionmaker[Session],
) -> None:
    """Full auto is not a blanket permission: it covers the named types only."""
    with db() as session:
        place = a_business(session)
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add(person)
        session.flush()
        give(session, organization_id=place, account_id=person.id, role=Role.OWNER)
        # A rule that is not auto-eligible, with everything else identical.
        card = replace(a_card(), rule=CATALOGUE["R2"])
        row = write_proposal(
            session,
            card,
            allowed(),
            organization_id=place,
            guardrail_config_version=3,
            autonomy=Autonomy.FULL_AUTO.value,
            auto_apply_flag=True,
            now=NOW,
        )
        session.commit()
    assert row.status == Status.AWAITING_APPROVAL.value
    assert "always needs a person" in row.decided_because


def test_an_offer_is_given_seven_days(db: sessionmaker[Session]) -> None:
    row = _write(db, needs_a_person())
    assert row.expires_at == NOW + timedelta(days=APPROVAL_EXPIRES_DAYS)


def test_a_refusal_has_nothing_to_wait_for(db: sessionmaker[Session]) -> None:
    assert _write(db, refused()).expires_at is None


def test_a_retry_cannot_apply_the_same_change_twice(db: sessionmaker[Session]) -> None:
    row = _write(db, needs_a_person())
    assert row.idempotency_key == f"R1:{row.id}"


def test_an_offer_nobody_answered_lapses(db: sessionmaker[Session]) -> None:
    with db() as session:
        place = a_business(session)
        for days, status in (
            (8, Status.AWAITING_APPROVAL.value),
            (8, Status.PROPOSED.value),
            (1, Status.AWAITING_APPROVAL.value),
            (8, Status.APPLIED.value),
        ):
            session.add(
                OptimizationAction(
                    id=uuid.uuid4(),
                    organization_id=place,
                    customer_id="1",
                    kind="add_negative_keyword",
                    status=status,
                    created_at=NOW - timedelta(days=days + 7),
                    expires_at=NOW - timedelta(days=days - 7)
                    if days > 7
                    else NOW + timedelta(days=6),
                )
            )
        session.commit()

        how_many = expire_old(session, now=NOW)
        session.commit()
        left = {row.status for row in session.scalars(sa.select(OptimizationAction)).all()}

    assert how_many == 2, "the two past their date, and only those"
    assert Status.EXPIRED.value in left
    assert Status.APPLIED.value in left, "an applied change does not expire"


def test_expiring_is_written_down_rather_than_worked_out_on_read(
    db: sessionmaker[Session],
) -> None:
    """Two readers comparing a row against their own clocks would disagree."""
    row = _write(db, needs_a_person())
    assert row.status == Status.AWAITING_APPROVAL.value
    with db() as session:
        assert expire_old(session, now=NOW + timedelta(days=1)) == 0
        assert expire_old(session, now=NOW + timedelta(days=8)) == 1
        session.commit()
        session.expire_all()
        again = session.get(OptimizationAction, row.id)
        assert again is not None and again.status == Status.EXPIRED.value


def test_what_a_business_has_been_asked_and_not_answered(db: sessionmaker[Session]) -> None:
    with db() as session:
        place = a_business(session)
        for status in (
            Status.AWAITING_APPROVAL.value,
            Status.AWAITING_APPROVAL.value,
            Status.APPLIED.value,
            Status.REJECTED.value,
        ):
            session.add(
                OptimizationAction(
                    id=uuid.uuid4(),
                    organization_id=place,
                    customer_id="1",
                    kind="pause_ad",
                    status=status,
                )
            )
        session.commit()
        assert len(waiting_for(session, place)) == 2


def test_nothing_here_talks_to_google(db: sessionmaker[Session]) -> None:
    """Writing the row and doing the thing are separate steps, in that order."""
    import ast
    import pathlib

    source = pathlib.Path("src/ppcway/opt/record.py").read_text()
    reached: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            reached.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            reached.add(node.module)
    assert not any(
        name.startswith(("httpx", "google.ads", "ppcway.ads.oauth", "ppcway.ads.sync"))
        for name in reached
    )
