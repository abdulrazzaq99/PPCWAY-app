"""Making an approved change: the order, and the line about partial failure.

The important one is `test_nine_of_ten_is_not_applied`. A batch where most
operations landed is the shape of failure Blueprint §5.6 warns about, and
calling it "applied" is how a platform comes to believe it created four hundred
things when it created three hundred and eighty-six.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.gateway import quota, switch
from ppcway.gateway.apply import UNDO_FOR, CannotApply, apply_now, may_undo
from ppcway.gateway.google import GoogleRefused
from ppcway.gateway.port import Applied, Batch, Doing, Operation, Refused
from ppcway.opt.models import GuardrailConfig, OptimizationAction, Status
from ppcway.org.models import Organization

CUSTOMER = "2580586343"
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


class Saying:
    """A door that answers however a test needs it to."""

    def __init__(self, answer: Applied | Exception) -> None:
        self.answer = answer
        self.sent: list[Batch] = []

    def mutate(self, batch: Batch) -> Applied:
        self.sent.append(batch)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def ops(how_many: int = 1) -> Batch:
    return Batch(
        customer_id=CUSTOMER,
        operations=tuple(
            Operation(
                resource_type="ad_group_criterion",
                doing=Doing.CREATE,
                fields={"keyword": {"text": f"waste {n}"}},
            )
            for n in range(how_many)
        ),
        idempotency_key="R1:abc",
    )


@pytest.fixture
def world(
    db: sessionmaker[Session],
) -> Iterator[tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID]]:
    with db() as session:
        place = Organization(name="Alpha Plumbing")
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add_all([place, person])
        session.flush()
        connection = AdsConnection(
            account_id=person.id,
            organization_id=place.id,
            ciphertext="locked",
            customer_id=CUSTOMER,
            currency="CAD",
            account_status="ENABLED",
            status_read_at=NOW - timedelta(hours=2),
        )
        # A live keyword, so the blast-radius check has a denominator.
        from ppcway.ads.mirror import MirrorKeyword

        session.add(connection)
        for n in range(50):
            session.add(
                MirrorKeyword(
                    id=uuid.uuid4(),
                    customer_id=CUSTOMER,
                    resource_name=f"customers/{CUSTOMER}/adGroupCriteria/21~{n}",
                    criterion_id=str(n),
                    ad_group_id="21",
                    campaign_id="11",
                    status="ENABLED",
                    seen_at=NOW,
                )
            )
        session.add(GuardrailConfig(organization_id=place.id, version=1, max_daily_budget=100.0))
        session.commit()
        yield db, place.id, connection, person.id


def approved(
    db: sessionmaker[Session],
    place: uuid.UUID,
    *,
    status: str = Status.APPROVED.value,
    undo_of: uuid.UUID | None = None,
    figures_age_hours: int = 2,
    payload: dict[str, object] | None = None,
) -> uuid.UUID:
    with db() as session:
        row = OptimizationAction(
            organization_id=place,
            customer_id=CUSTOMER,
            kind="add_negative_keyword",
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
            rule_id="R1",
            rule_version=1,
            guardrail_config_version=1,
            route="owner",
            risk="low",
            status=status,
            undo_of=undo_of,
            approved_at=NOW - timedelta(minutes=5),
            payload=payload,
        )
        session.add(row)
        session.commit()
        return row.id


def _apply(
    db: sessionmaker[Session],
    place: uuid.UUID,
    connection: AdsConnection,
    action_id: uuid.UUID,
    door: Saying,
    *,
    gate_open: bool = True,
    how_many: int = 1,
) -> object:
    with db() as session:
        action = session.get(OptimizationAction, action_id)
        assert action is not None
        held = session.get(AdsConnection, connection.id)
        return apply_now(
            session,
            action,
            ops(how_many),
            door=door,
            connection=held,
            organization_id=place,
            gate_open=gate_open,
            now=NOW,
        )


def test_everything_landing_is_applied(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    db, place, connection, _person = world
    action = approved(db, place)
    door = Saying(Applied(landed=("customers/1/adGroupCriteria/21~900",)))
    said = _apply(db, place, connection, action, door)
    assert said.status is Status.APPLIED  # type: ignore[attr-defined]
    assert said.action.applied_at == NOW  # type: ignore[attr-defined]
    assert len(door.sent) == 1


def test_nine_of_ten_is_not_applied(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """The line Blueprint §5.6 is about. Most is not all."""
    db, place, connection, _person = world
    action = approved(db, place)
    landed: tuple[str | None, ...] = tuple(
        f"customers/1/adGroupCriteria/21~{n}" for n in range(9)
    ) + (None,)
    door = Saying(
        Applied(
            landed=landed,
            refused=(Refused(at=9, code="criterion.DUPLICATE", message="already there"),),
        )
    )
    said = _apply(db, place, connection, action, door, how_many=10)
    assert said.status is Status.FAILED  # type: ignore[attr-defined]
    assert "accepted 9 of 10" in said.words  # type: ignore[attr-defined]
    assert "already there" in said.words  # type: ignore[attr-defined]
    assert said.action.applied_at is None  # type: ignore[attr-defined]


def test_nothing_is_sent_while_the_gate_is_shut(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """And the change stays approved, because nothing was attempted."""
    db, place, connection, _person = world
    action = approved(db, place)
    door = Saying(Applied(landed=("a",)))
    with pytest.raises(CannotApply, match="not writing to Google Ads yet"):
        _apply(db, place, connection, action, door, gate_open=False)
    assert door.sent == []
    with db() as session:
        again = session.get(OptimizationAction, action)
        assert again is not None and again.status == Status.APPROVED.value


def test_nothing_is_sent_while_a_kill_switch_is_pulled(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    db, place, connection, _person = world
    action = approved(db, place)
    with db() as session:
        switch.stop(session, because="A rule is misbehaving.", ours=True)
    door = Saying(Applied(landed=("a",)))
    with pytest.raises(CannotApply, match="misbehaving"):
        _apply(db, place, connection, action, door)
    assert door.sent == []


def test_the_guardrails_run_once_more_before_sending(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """A job can sit in a queue, and time is what makes a change unsafe."""
    db, place, connection, _person = world
    action = approved(db, place, figures_age_hours=150)
    door = Saying(Applied(landed=("a",)))
    said = _apply(db, place, connection, action, door)
    assert said.status is Status.REJECTED  # type: ignore[attr-defined]
    assert "checked once more before sending" in said.words  # type: ignore[attr-defined]
    assert door.sent == [], "nothing reached Google"


def test_quota_is_counted_before_the_call_not_after(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """An operation Google refuses still spends it."""
    db, place, connection, _person = world
    action = approved(db, place)
    door = Saying(GoogleRefused("Google refused the request: 400 bad keyword"))
    said = _apply(db, place, connection, action, door, how_many=5)
    assert said.status is Status.FAILED  # type: ignore[attr-defined]
    with db() as session:
        assert quota.room_today(session, CUSTOMER, today=date(2026, 11, 2)).used == 5


def test_a_whole_refusal_from_google_is_failed_not_rejected(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """Google saying no is nobody's decision, and must not read as a rejection."""
    db, place, connection, _person = world
    action = approved(db, place)
    door = Saying(GoogleRefused("Google refused the request: 403 no permission"))
    said = _apply(db, place, connection, action, door)
    assert said.status is Status.FAILED  # type: ignore[attr-defined]
    assert "would not make that change" in said.words  # type: ignore[attr-defined]


def test_only_an_approved_change_is_sent(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    db, place, connection, _person = world
    action = approved(db, place, status=Status.AWAITING_APPROVAL.value)
    door = Saying(Applied(landed=("a",)))
    with pytest.raises(CannotApply, match="only an approved change"):
        _apply(db, place, connection, action, door)
    assert door.sent == []


def test_a_successful_undo_marks_what_it_reversed(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """Written here, because until this moment nothing had been put back."""
    db, place, connection, _person = world
    original = approved(db, place, status=Status.APPLIED.value)
    with db() as session:
        row = session.get(OptimizationAction, original)
        assert row is not None
        row.applied_at = NOW - timedelta(days=1)
        session.commit()

    putting_back = approved(db, place, undo_of=original)
    door = Saying(Applied(landed=("customers/1/adGroupCriteria/21~1",)))
    said = _apply(db, place, connection, putting_back, door)
    assert said.status is Status.APPLIED  # type: ignore[attr-defined]

    with db() as session:
        was = session.get(OptimizationAction, original)
        assert was is not None
        assert was.status == Status.REVERTED.value
        assert was.reverted_at is not None
        # SQLite hands back a naive timestamp; the value is the one we wrote.
        assert was.reverted_at.replace(tzinfo=UTC) == NOW


def test_a_failed_undo_leaves_the_original_applied(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    db, place, connection, _person = world
    original = approved(db, place, status=Status.APPLIED.value)
    putting_back = approved(db, place, undo_of=original)
    door = Saying(GoogleRefused("400"))
    _apply(db, place, connection, putting_back, door)
    with db() as session:
        was = session.get(OptimizationAction, original)
        assert was is not None and was.status == Status.APPLIED.value


def test_the_undo_window_runs_from_when_the_change_was_made() -> None:
    """Not from when it was proposed: a change that waited six days for a yes
    would otherwise lose six days of its thirty."""
    made = OptimizationAction(
        customer_id=CUSTOMER,
        kind="add_negative_keyword",
        status=Status.APPLIED.value,
        reversible=True,
        created_at=NOW - timedelta(days=36),
        applied_at=NOW - timedelta(days=29),
    )
    assert may_undo(made, now=NOW)
    made.applied_at = NOW - UNDO_FOR - timedelta(hours=1)
    assert not may_undo(made, now=NOW)


def test_what_was_never_applied_has_no_undo_window() -> None:
    waiting = OptimizationAction(
        customer_id=CUSTOMER,
        kind="add_negative_keyword",
        status=Status.AWAITING_APPROVAL.value,
        reversible=True,
    )
    assert not may_undo(waiting, now=NOW)


def test_what_cannot_be_reversed_has_no_undo_window() -> None:
    spent = OptimizationAction(
        customer_id=CUSTOMER,
        kind="increase_daily_budget",
        status=Status.APPLIED.value,
        reversible=False,
        applied_at=NOW,
    )
    assert not may_undo(spent, now=NOW)


def test_an_undo_is_not_refused_as_thrashing(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """Found while building this: the velocity limit counted a change and its
    own reversal as two changes to the same thing, so undoing was refused.

    A limit that stops a merchant reversing a mistake traps them in it. Four
    checks are skipped for an undo, and `SKIP_FOR_UNDO` says which and why.
    """
    db, place, connection, _person = world
    # Two changes to this target today already, which is the per-entity limit.
    original = approved(db, place, status=Status.APPLIED.value)
    approved(db, place, status=Status.APPLIED.value)

    putting_back = approved(db, place, undo_of=original)
    door = Saying(Applied(landed=("customers/1/adGroupCriteria/21~1",)))
    said = _apply(db, place, connection, putting_back, door)
    assert said.status is Status.APPLIED, said.words  # type: ignore[attr-defined]


def test_an_undo_still_has_to_be_for_this_account(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """Skipping four checks is not skipping all of them."""
    from ppcway.opt.guardrails import SKIP_FOR_UNDO

    assert "scope" not in SKIP_FOR_UNDO
    assert "hard_spend_limits" not in SKIP_FOR_UNDO
    assert "blast_radius" not in SKIP_FOR_UNDO
    assert "link_valid" not in SKIP_FOR_UNDO
    assert "account_serviceable" not in SKIP_FOR_UNDO
    assert "quota" not in SKIP_FOR_UNDO


def test_a_skipped_check_says_it_was_skipped(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """The log keeps which checks ran. Silence would read as "it passed"."""
    from ppcway.opt.answer import _as_proposal
    from ppcway.opt.context import limits_for, standing_for
    from ppcway.opt.guardrails import judge

    db, place, connection, _person = world
    original = approved(db, place, status=Status.APPLIED.value)
    putting_back = approved(db, place, undo_of=original)
    with db() as session:
        action = session.get(OptimizationAction, putting_back)
        held = session.get(AdsConnection, connection.id)
        assert action is not None and held is not None
        said = judge(
            _as_proposal(action),
            standing_for(session, held, organization_id=place, now=NOW),
            limits_for(session, place),
            now=NOW,
        )
    assert "velocity_limits:skipped_for_undo" in said.ran
    assert "scope" in said.ran, "and the ones that still apply are named plainly"


def test_what_google_created_is_kept_on_the_row(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """Only Google knows the id of the negative keyword it made, and putting
    the change back is a remove of exactly that."""
    db, place, connection, _person = world
    action = approved(db, place)
    made = "customers/2580586343/adGroupCriteria/21~900"
    _apply(db, place, connection, action, Saying(Applied(landed=(made,), operations_used=1)))
    with db() as session:
        row = session.get(OptimizationAction, action)
        assert row is not None and row.outcome is not None
        assert row.outcome["landed"] == [made]
        assert row.outcome["refused"] == []
        assert row.taken_at is not None


def test_google_s_reason_is_kept_when_it_refuses(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """A failed change is explained from the row, not left as a bare status."""
    db, place, connection, _person = world
    action = approved(db, place)
    _apply(db, place, connection, action, Saying(GoogleRefused("403 no permission")))
    with db() as session:
        row = session.get(OptimizationAction, action)
        assert row is not None and row.outcome is not None
        assert row.outcome["refused_whole"] == "403 no permission"
        assert "would not make that change" in row.outcome["words"]


def test_a_change_another_sender_has_taken_is_not_sent_again(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """The request that approved it and the scheduled pass can both reach one
    change. Only the one that takes it sends it."""
    db, place, connection, _person = world
    action = approved(db, place)
    with db() as session:
        row = session.get(OptimizationAction, action)
        assert row is not None
        row.taken_at = NOW - timedelta(seconds=2)
        session.commit()
    door = Saying(Applied(landed=("a",)))
    with pytest.raises(CannotApply, match="already being sent"):
        _apply(db, place, connection, action, door)
    assert door.sent == []
    with db() as session:
        assert quota.room_today(session, CUSTOMER, today=date(2026, 11, 2)).used == 0, (
            "nothing is counted for a change this sender did not send"
        )


def test_sending_twice_sends_once(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    db, place, connection, _person = world
    action = approved(db, place)
    door = Saying(Applied(landed=("customers/1/adGroupCriteria/21~900",)))
    _apply(db, place, connection, action, door)
    with pytest.raises(CannotApply, match="only an approved change"):
        _apply(db, place, connection, action, door)
    assert len(door.sent) == 1


def test_a_full_day_leaves_the_change_approved_for_tomorrow(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """Read before taking it: a change taken on a full day would be stuck."""
    db, place, connection, _person = world
    action = approved(db, place)
    with db() as session:
        quota.spend(session, CUSTOMER, quota.A_DAY, today=date(2026, 11, 2))
        session.commit()
    door = Saying(Applied(landed=("a",)))
    with pytest.raises(CannotApply, match="allowance for today"):
        _apply(db, place, connection, action, door)
    assert door.sent == []
    with db() as session:
        row = session.get(OptimizationAction, action)
        assert row is not None
        assert row.status == Status.APPROVED.value
        assert row.taken_at is None, "free to go out tomorrow"


def test_a_last_moment_refusal_keeps_its_reason(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    db, place, connection, _person = world
    action = approved(db, place, figures_age_hours=150)
    _apply(db, place, connection, action, Saying(Applied(landed=("a",))))
    with db() as session:
        row = session.get(OptimizationAction, action)
        assert row is not None and row.outcome is not None
        assert row.outcome["ruling"]["check"] == "data_freshness"
        assert row.taken_at is None, "refused before it was taken"


def test_putting_an_exclusion_back_is_not_counted_as_a_pause(
    world: tuple[sessionmaker[Session], uuid.UUID, AdsConnection, uuid.UUID],
) -> None:
    """Removing a negative keyword lets a search back in and stops nothing.
    Counted as a pause, on an account with three live things it was a third
    of the account, and the blast-radius check refused the undo."""
    db, place, connection, _person = world
    from ppcway.ads.mirror import MirrorKeyword

    with db() as session:
        for keyword in session.scalars(sa.select(MirrorKeyword)).all()[3:]:
            keyword.gone_at = NOW
        session.commit()
    original = approved(db, place, status=Status.APPLIED.value)
    made = "customers/2580586343/adGroupCriteria/21~900"
    putting_back = approved(
        db,
        place,
        undo_of=original,
        payload={"change": "remove_exclusions", "criteria": [made]},
    )
    removal = Batch(
        customer_id=CUSTOMER,
        operations=(
            Operation(resource_type="ad_group_criterion", doing=Doing.REMOVE, resource_name=made),
        ),
    )
    with db() as session:
        action = session.get(OptimizationAction, putting_back)
        assert action is not None
        said = apply_now(
            session,
            action,
            removal,
            door=Saying(Applied(landed=(made,))),
            connection=session.get(AdsConnection, connection.id),
            organization_id=place,
            gate_open=True,
            now=NOW,
        )
    assert said.status is Status.APPLIED, said.words
