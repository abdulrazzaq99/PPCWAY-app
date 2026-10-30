"""Fix F2: the action log is append-only at the database, not by convention.

The models have claimed this since they were written. These prove it, by trying
each way there is to rewrite history and watching the database refuse. Every
refusal here comes from a trigger, so it holds against `psql`, against a
migration, and against application code that has no idea the rule exists.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ppcway.auth.models import UserAccount  # noqa: F401 - the FK target must be mapped
from ppcway.opt.models import Autonomy, GuardrailConfig, OptimizationAction, Status
from ppcway.org.models import Organization


@pytest.fixture
def db(pg_engine: Engine) -> Iterator[sessionmaker[Session]]:
    yield sessionmaker(bind=pg_engine, expire_on_commit=False, future=True)


@pytest.fixture
def logged(db: sessionmaker[Session]) -> tuple[sessionmaker[Session], uuid.UUID, uuid.UUID]:
    """One business and one pending action in the log."""
    with db() as session:
        place = Organization(name=f"Append Only {uuid.uuid4().hex[:8]}")
        session.add(place)
        session.flush()
        action = OptimizationAction(
            organization_id=place.id,
            customer_id="3330000003",
            kind="decrease_daily_budget",
            status=Status.PENDING.value,
            before={"daily_budget": 40.0},
            after={"daily_budget": 32.0},
            rule_id="R3",
            rule_version=1,
            guardrail_config_version=1,
            autonomy=Autonomy.APPROVE_FIRST.value,
        )
        session.add(action)
        session.commit()
        return db, place.id, action.id


def _refuses(db: sessionmaker[Session], statement: str, params: dict[str, object]) -> str:
    """Run one statement in its own transaction and return the refusal."""
    with db() as session, pytest.raises(sa.exc.ProgrammingError) as caught:
        session.execute(sa.text(statement), params)
        session.commit()
    return str(caught.value)


def _allows(db: sessionmaker[Session], statement: str, params: dict[str, object]) -> None:
    with db() as session:
        session.execute(sa.text(statement), params)
        session.commit()


def test_an_action_cannot_be_deleted(
    logged: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, _place, action = logged
    said = _refuses(db, "DELETE FROM optimization_action WHERE id = :i", {"i": action})
    assert "append-only" in said
    with db() as session:
        assert session.get(OptimizationAction, action) is not None


def test_the_log_still_records_what_became_of_a_proposal(
    logged: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """Append-only is not read-only. The one transition the log exists for works."""
    db, _place, action = logged
    _allows(
        db,
        "UPDATE optimization_action SET status = 'applied', applied_at = :t WHERE id = :i",
        {"t": datetime.now(UTC), "i": action},
    )
    with db() as session:
        session.expire_all()
        written = session.get(OptimizationAction, action)
        assert written is not None
        assert written.status == Status.APPLIED.value


@pytest.mark.parametrize(
    ("to", "why"),
    [
        ("pending", "an outcome cannot be reopened"),
        ("rejected", "an applied change was not rejected"),
        ("made_up", "a status nobody defined"),
    ],
)
def test_an_outcome_is_final(
    logged: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID], to: str, why: str
) -> None:
    db, _place, action = logged
    _allows(db, "UPDATE optimization_action SET status = 'applied' WHERE id = :i", {"i": action})
    said = _refuses(
        db, "UPDATE optimization_action SET status = :s WHERE id = :i", {"s": to, "i": action}
    )
    assert "not an allowed transition" in said, why


@pytest.mark.parametrize(
    "column_and_value",
    [
        ("before", "'{\"daily_budget\": 5.0}'"),
        ("after", "'{\"daily_budget\": 500.0}'"),
        ("evidence", "'{\"clicks\": 1}'"),
        ("rule_id", "'R9'"),
        ("rule_version", "99"),
        ("guardrail_config_version", "99"),
        ("autonomy", "'full_auto'"),
        ("customer_id", "'9990000009'"),
        ("kind", "'increase_daily_budget'"),
        ("route", "'expert'"),
        ("created_at", "now()"),
    ],
)
def test_the_evidence_for_an_action_cannot_be_changed(
    logged: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
    column_and_value: tuple[str, str],
) -> None:
    """What justified a change is the whole value of the log in a dispute."""
    db, _place, action = logged
    column, value = column_and_value
    said = _refuses(
        db,
        f"UPDATE optimization_action SET {column} = {value} WHERE id = :i",
        {"i": action},
    )
    assert f"optimization_action.{column} is evidence and may not change" in said


def test_a_moved_action_cannot_be_moved_to_another_business(
    logged: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, _place, action = logged
    said = _refuses(
        db,
        "UPDATE optimization_action SET organization_id = :o WHERE id = :i",
        {"o": uuid.uuid4(), "i": action},
    )
    assert "organization_id is evidence" in said


@pytest.mark.parametrize(
    ("column", "first", "second"),
    [
        ("reason", "'because it wasted money'", "'because I said so'"),
        ("decided_by", "'hard_spend_limits'", "'nobody'"),
        ("decided_because", "'over the ceiling'", "'under it, honestly'"),
    ],
)
def test_a_written_explanation_cannot_be_rewritten(
    logged: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
    column: str,
    first: str,
    second: str,
) -> None:
    """Empty to a value once -- the model may write the words later -- then frozen."""
    db, _place, action = logged
    _allows(db, f"UPDATE optimization_action SET {column} = {first} WHERE id = :i", {"i": action})
    said = _refuses(
        db, f"UPDATE optimization_action SET {column} = {second} WHERE id = :i", {"i": action}
    )
    assert f"optimization_action.{column} was already written" in said


def test_when_a_change_was_applied_cannot_be_backdated(
    logged: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, _place, action = logged
    _allows(
        db,
        "UPDATE optimization_action SET status = 'applied', applied_at = now() WHERE id = :i",
        {"i": action},
    )
    said = _refuses(
        db,
        "UPDATE optimization_action SET applied_at = now() - interval '30 days' WHERE id = :i",
        {"i": action},
    )
    assert "applied_at was already written" in said


def _a_version(db: sessionmaker[Session]) -> tuple[uuid.UUID, uuid.UUID]:
    with db() as session:
        place = Organization(name=f"Limits {uuid.uuid4().hex[:8]}")
        session.add(place)
        session.flush()
        limits = GuardrailConfig(
            organization_id=place.id, version=1, max_daily_budget=50.0, max_change_pct=20.0
        )
        session.add(limits)
        session.commit()
        return place.id, limits.id


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE guardrail_config SET max_daily_budget = 5000 WHERE id = :i",
        "UPDATE guardrail_config SET max_change_pct = 90 WHERE id = :i",
        "UPDATE guardrail_config SET version = 2 WHERE id = :i",
        "DELETE FROM guardrail_config WHERE id = :i",
    ],
)
def test_the_limits_that_authorised_an_action_cannot_be_edited_afterwards(
    db: sessionmaker[Session], statement: str
) -> None:
    """An action cites a version. A version whose numbers could change would
    make every action citing it a lie, so a limit change is a new version."""
    _place, limits = _a_version(db)
    said = _refuses(db, statement, {"i": limits})
    assert "guardrail_config is immutable" in said or "DELETE is forbidden" in said


def test_a_new_version_is_how_limits_change(db: sessionmaker[Session]) -> None:
    """The immutability is not a dead end: the supported move still works."""
    place, _limits = _a_version(db)
    with db() as session:
        session.add(
            GuardrailConfig(
                organization_id=place, version=2, max_daily_budget=80.0, max_change_pct=20.0
            )
        )
        session.commit()
        versions = session.scalars(
            sa.select(GuardrailConfig.version)
            .where(GuardrailConfig.organization_id == place)
            .order_by(GuardrailConfig.version)
        ).all()
    assert list(versions) == [1, 2]
