"""Saying yes, saying no, and putting something back.

The test that matters most is the one where a yes is overturned. A proposal
written six days ago and approved today is approved against figures that have
aged past the freshness rule, and the brief's requirement that the guardrails
run again at approval only means something if that case is refused.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.opt.answer import (
    NotAllowed,
    NotAnswerable,
    approve,
    reject,
    undo,
)
from ppcway.opt.models import GuardrailConfig, OptimizationAction, ProposedBy, Status
from ppcway.org.models import Organization, Role

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


@pytest.fixture
def world(
    db: sessionmaker[Session],
) -> tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection]:
    """A business with a healthy connected account and nothing proposed yet."""
    with db() as session:
        place = Organization(name="Alpha Plumbing")
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add_all([place, person])
        session.flush()
        connection = AdsConnection(
            account_id=person.id,
            organization_id=place.id,
            ciphertext="locked",
            customer_id="2580586343",
            customer_name="Alpha Plumbing",
            currency="CAD",
            account_status="ENABLED",
            status_read_at=NOW - timedelta(hours=2),
        )
        session.add(connection)
        session.add(GuardrailConfig(organization_id=place.id, version=1, max_daily_budget=100.0))
        session.commit()
        return db, place.id, person.id, connection


def a_change(
    db: sessionmaker[Session],
    place: uuid.UUID,
    *,
    status: str = Status.AWAITING_APPROVAL.value,
    route: str = "owner",
    figures_age_hours: int = 2,
    expires_in_days: int = 6,
    kind: str = "add_negative_keyword",
    reversible: bool = True,
) -> uuid.UUID:
    with db() as session:
        row = OptimizationAction(
            organization_id=place,
            customer_id="2580586343",
            kind=kind,
            target_kind="search_term",
            target_id="abc123",
            target_label="boiler repair jobs",
            before={"excluded": False},
            after={"excluded": True},
            reason="Nobody who searched that got in touch.",
            evidence={
                "figures": [
                    {
                        "id": "search_term_spend:search_term-abc123:2026-10-01..2026-10-30",
                        "as_of": (NOW - timedelta(hours=figures_age_hours)).isoformat(),
                    }
                ]
            },
            expected_impact={"money_a_month": 91.2, "currency": "CAD"},
            undo_plan="Remove the negative keyword.",
            rule_id="R1",
            rule_version=1,
            guardrail_config_version=1,
            route=route,
            risk="low",
            status=status,
            reversible=reversible,
            decided_by="autonomy_level",
            decided_because="You asked to be asked.",
            created_at=NOW - timedelta(days=1),
            expires_at=NOW + timedelta(days=expires_in_days),
        )
        session.add(row)
        session.commit()
        return row.id


def test_a_yes_is_recorded_with_who_said_it(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    db, place, person, connection = world
    action = a_change(db, place)
    with db() as session:
        said = approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            connection=connection,
            now=NOW,
        )
    assert said.status is Status.APPROVED
    assert said.action.approved_by == person
    assert said.action.approved_at == NOW
    assert said.action.rechecked is not None, "the second ruling is recorded even when it passes"
    assert said.action.rechecked_at == NOW


def test_a_yes_is_overturned_when_the_figures_have_gone_stale(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """The whole reason the guardrails run again. Six days is past 36 hours."""
    db, place, person, connection = world
    action = a_change(db, place, figures_age_hours=150)
    with db() as session:
        said = approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            connection=connection,
            now=NOW,
        )
    assert said.status is Status.REJECTED
    assert said.refused_by == "data_freshness"
    assert "checked again before making the change" in said.words
    assert said.action.approved_at is None, "nothing was approved"


def test_the_first_ruling_is_not_overwritten_by_the_second(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """Both happened, at different times, and a refusal has to say which refused."""
    db, place, person, connection = world
    action = a_change(db, place, figures_age_hours=150)
    with db() as session:
        said = approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            connection=connection,
            now=NOW,
        )
    assert said.action.decided_by == "autonomy_level"
    assert said.action.decided_because == "You asked to be asked."
    assert said.action.rechecked is not None
    assert said.action.rechecked["check"] == "data_freshness"


def test_a_suspended_account_stops_a_change_that_was_already_approved(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    db, place, person, connection = world
    action = a_change(db, place)
    with db() as session:
        held = session.get(AdsConnection, connection.id)
        assert held is not None
        held.account_status = "SUSPENDED"
        session.commit()
        said = approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            connection=held,
            now=NOW,
        )
    assert said.status is Status.REJECTED
    assert said.refused_by == "account_serviceable"


def test_a_status_read_too_long_ago_is_not_an_answer(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """A fortnight-old reading is not a current one, and the check refuses."""
    db, place, person, connection = world
    action = a_change(db, place)
    with db() as session:
        held = session.get(AdsConnection, connection.id)
        assert held is not None
        held.status_read_at = NOW - timedelta(days=14)
        session.commit()
        said = approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            connection=held,
            now=NOW,
        )
    assert said.status is Status.REJECTED
    assert said.refused_by == "account_serviceable"


def test_an_expert_routed_change_cannot_be_approved_by_the_owner(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """Not a missing permission. A different kind of person is needed."""
    db, place, person, connection = world
    action = a_change(db, place, route="expert")
    with db() as session, pytest.raises(NotAllowed, match="PPCWay expert has to sign it off"):
        approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            connection=connection,
            now=NOW,
        )


def test_an_expert_can_approve_an_expert_routed_change(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    db, place, person, connection = world
    action = a_change(db, place, route="expert")
    with db() as session:
        said = approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.EXPERT,
            connection=connection,
            now=NOW,
        )
    assert said.status is Status.APPROVED


@pytest.mark.parametrize("role", [Role.MEMBER, Role.CLIENT_VIEWER, None])
def test_somebody_who_may_not_answer_is_refused(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
    role: Role | None,
) -> None:
    db, place, person, connection = world
    action = a_change(db, place)
    with db() as session, pytest.raises(NotAllowed):
        approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=role,
            connection=connection,
            now=NOW,
        )


def test_another_business_change_does_not_exist_as_far_as_this_caller_is_concerned(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """Whether a change exists is itself something to know."""
    db, place, person, connection = world
    with db() as session:
        other = Organization(name="Beta Dental")
        session.add(other)
        session.commit()
        theirs = a_change(db, other.id)
        with pytest.raises(LookupError):
            approve(
                session,
                theirs,
                organization_id=place,
                account_id=person,
                role=Role.OWNER,
                connection=connection,
                now=NOW,
            )


def test_an_offer_past_its_date_expires_rather_than_being_approved(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    db, place, person, connection = world
    action = a_change(db, place, expires_in_days=-1)
    with db() as session:
        with pytest.raises(NotAnswerable, match="has expired"):
            approve(
                session,
                action,
                organization_id=place,
                account_id=person,
                role=Role.OWNER,
                connection=connection,
                now=NOW,
            )
        session.expire_all()
        again = session.get(OptimizationAction, action)
        assert again is not None and again.status == Status.EXPIRED.value


@pytest.mark.parametrize(
    ("status", "says"),
    [
        (Status.APPROVED.value, "already been approved"),
        (Status.APPLIED.value, "already been made"),
        (Status.REJECTED.value, "already declined"),
        (Status.EXPIRED.value, "expired before anybody answered"),
    ],
)
def test_a_change_already_settled_says_what_happened_instead(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
    status: str,
    says: str,
) -> None:
    db, place, person, connection = world
    action = a_change(db, place, status=status)
    with db() as session, pytest.raises(NotAnswerable, match=says):
        approve(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            connection=connection,
            now=NOW,
        )


def test_saying_no_needs_no_guardrails(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """Nobody needs permission to decline a change to their own account."""
    db, place, person, _connection = world
    action = a_change(db, place, figures_age_hours=150)
    with db() as session:
        said = reject(
            session,
            action,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            because="We want that traffic.",
            now=NOW,
        )
    assert said.status is Status.REJECTED
    assert said.action.rechecked is not None
    assert said.action.rechecked["check"] == "person"
    assert "We want that traffic." in said.action.rechecked["because"]


def test_declining_without_a_reason_still_records_that_a_person_did_it(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    db, place, person, _connection = world
    action = a_change(db, place)
    with db() as session:
        said = reject(
            session, action, organization_id=place, account_id=person, role=Role.OWNER, now=NOW
        )
    assert said.action.rechecked is not None
    assert "owner declined" in said.action.rechecked["because"]


def test_an_undo_is_a_new_row_with_the_change_the_other_way_round(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """The brief: a revert is a new row."""
    db, place, person, _connection = world
    action = a_change(db, place, status=Status.APPLIED.value)
    with db() as session:
        said = undo(
            session, action, organization_id=place, account_id=person, role=Role.OWNER, now=NOW
        )
    assert said.action.id != action
    assert said.action.undo_of == action
    assert said.action.before == {"excluded": True}
    assert said.action.after == {"excluded": False}
    assert said.action.proposed_by == ProposedBy.OWNER.value
    assert not said.action.reversible


def test_the_original_stays_applied_until_the_undo_has_been_made(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """A log that said "reverted" on request would claim something had happened."""
    db, place, person, _connection = world
    action = a_change(db, place, status=Status.APPLIED.value)
    with db() as session:
        undo(session, action, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        session.expire_all()
        original = session.get(OptimizationAction, action)
    assert original is not None
    assert original.status == Status.APPLIED.value


def test_a_change_that_was_never_made_cannot_be_put_back(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    db, place, person, _connection = world
    action = a_change(db, place)
    with db() as session, pytest.raises(NotAnswerable, match="actually made"):
        undo(session, action, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)


def test_what_cannot_be_put_back_says_so_plainly(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    """Structure reverts. Money spent and Google's learning do not."""
    db, place, person, _connection = world
    action = a_change(db, place, status=Status.APPLIED.value, reversible=False)
    with db() as session, pytest.raises(NotAnswerable, match="cannot be put back"):
        undo(session, action, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)


def test_asking_twice_does_not_queue_two_undos(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID, AdsConnection],
) -> None:
    db, place, person, _connection = world
    action = a_change(db, place, status=Status.APPLIED.value)
    with db() as session:
        undo(session, action, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        with pytest.raises(NotAnswerable, match="already being put back"):
            undo(
                session,
                action,
                organization_id=place,
                account_id=person,
                role=Role.OWNER,
                now=NOW,
            )
