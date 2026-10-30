"""The action log, against a real database.

Blueprint §8.4 states six properties. A schema that merely creates is not the
same as one that can hold them, so these exercise the properties rather than
the columns.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.auth.models import UserAccount  # noqa: F401 - the FK target must be mapped
from ppcway.db.base import Base
from ppcway.opt.models import (
    APPROVAL_EXPIRES_DAYS,
    Autonomy,
    GuardrailConfig,
    OptimizationAction,
    Status,
)
from ppcway.org.models import Organization


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def a_business(session: Session) -> Organization:
    place = Organization(name="Alpha Plumbing")
    session.add(place)
    session.commit()
    return place


def an_action(place: Organization, **over: object) -> OptimizationAction:
    fields: dict[str, object] = {
        "organization_id": place.id,
        "customer_id": "2580586343",
        "kind": "decrease_daily_budget",
        "target_kind": "campaign",
        "target_id": "11",
        "target_label": "Emergency plumbing",
        "before": {"daily_budget": 40.0},
        "after": {"daily_budget": 32.0},
        "reason": "Spend has run ahead of pace for six days.",
        "evidence": {"month_to_date": 612.0, "pace_target": 520.0},
        "rule_id": "budget_pacing",
        "rule_version": 1,
        "guardrail_config_version": 3,
        "autonomy": Autonomy.APPROVE_FIRST.value,
        "job_run": "run-2026-10-26",
    }
    fields.update(over)
    return OptimizationAction(**fields)


def test_a_row_exists_before_anything_is_sent_to_google(db: sessionmaker[Session]) -> None:
    """Written before acting, or it is missing exactly when the crash happened."""
    with db() as session:
        place = a_business(session)
        action = an_action(place)
        session.add(action)
        session.commit()

        kept = session.scalars(sa.select(OptimizationAction)).one()

    assert kept.status == Status.PENDING.value
    assert kept.applied_at is None
    # The world as it stood, captured before the call rather than after it.
    assert kept.before == {"daily_budget": 40.0}


@pytest.mark.parametrize("outcome", [Status.APPLIED, Status.FAILED, Status.REJECTED])
def test_the_one_transition_the_log_allows(db: sessionmaker[Session], outcome: Status) -> None:
    with db() as session:
        place = a_business(session)
        action = an_action(place)
        session.add(action)
        session.commit()

        action.status = outcome.value
        if outcome is Status.APPLIED:
            action.applied_at = datetime.now(UTC)
        session.commit()

        kept = session.scalars(sa.select(OptimizationAction)).one()

    assert kept.status == outcome.value
    # What justified it is unchanged by the outcome.
    assert kept.before == {"daily_budget": 40.0}
    assert kept.rule_id == "budget_pacing"


def test_an_undo_is_an_action_of_its_own_pointing_at_the_first(
    db: sessionmaker[Session],
) -> None:
    """An undo that leaves no trace breaks the property the log exists for."""
    with db() as session:
        place = a_business(session)
        first = an_action(place, status=Status.APPLIED.value, applied_at=datetime.now(UTC))
        session.add(first)
        session.commit()

        # The inverse: before and after swapped, and linked to what it reverses.
        back = an_action(
            place,
            kind="increase_daily_budget",
            before={"daily_budget": 32.0},
            after={"daily_budget": 40.0},
            reason="Put back by Dana.",
            undo_of=first.id,
        )
        session.add(back)
        session.commit()

        rows = session.scalars(
            sa.select(OptimizationAction).order_by(OptimizationAction.created_at)
        ).all()

    assert len(rows) == 2
    assert rows[1].undo_of == rows[0].id
    assert rows[1].after == rows[0].before


def test_what_cannot_be_put_back_says_so(db: sessionmaker[Session]) -> None:
    """Structure reverts. Money spent does not, and nor does Google's learning."""
    with db() as session:
        place = a_business(session)
        session.add(an_action(place, kind="increase_daily_budget", reversible=False))
        session.commit()
        assert session.scalars(sa.select(OptimizationAction)).one().reversible is False


def test_the_limits_that_authorised_a_change_can_be_found_months_later(
    db: sessionmaker[Session],
) -> None:
    """Which limits were in force when this happened is a merchant's question."""
    with db() as session:
        place = a_business(session)
        for version, ceiling in ((1, 20.0), (2, 30.0), (3, 40.0)):
            session.add(
                GuardrailConfig(
                    organization_id=place.id,
                    version=version,
                    max_daily_budget=ceiling,
                    autonomy=Autonomy.APPROVE_FIRST.value,
                )
            )
        session.add(an_action(place, guardrail_config_version=2))
        session.commit()

        action = session.scalars(sa.select(OptimizationAction)).one()
        in_force = session.scalars(
            sa.select(GuardrailConfig).where(
                GuardrailConfig.organization_id == action.organization_id,
                GuardrailConfig.version == action.guardrail_config_version,
            )
        ).one()

    assert in_force.max_daily_budget == 30.0


def test_a_version_is_never_reused(db: sessionmaker[Session]) -> None:
    with db() as session:
        place = a_business(session)
        session.add(GuardrailConfig(organization_id=place.id, version=1))
        session.commit()
        session.add(GuardrailConfig(organization_id=place.id, version=1))
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()


def test_a_proposal_does_not_wait_forever() -> None:
    assert APPROVAL_EXPIRES_DAYS == 7
