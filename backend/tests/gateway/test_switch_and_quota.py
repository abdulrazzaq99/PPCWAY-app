"""The three switches, and the tally that counts what Google counts."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.db.base import Base
from ppcway.gateway import quota, switch
from ppcway.gateway.quota import A_DAY, SHOUT_AT

CUSTOMER = "2580586343"
TODAY = date(2026, 11, 2)
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def test_nothing_writes_while_the_gate_is_shut(db: sessionmaker[Session]) -> None:
    """The default in code is the safe one, not the convenient one."""
    with db() as session:
        said = switch.may_write(session, customer_id=CUSTOMER, gate_open=False)
    assert not said.may_write
    assert said.stopped_by == "gate"
    assert "not writing to Google Ads yet" in said.because


def test_with_the_gate_open_and_nothing_pulled_writes_are_allowed(
    db: sessionmaker[Session],
) -> None:
    with db() as session:
        assert switch.may_write(session, customer_id=CUSTOMER, gate_open=True).may_write


def test_one_account_can_be_stopped_without_stopping_the_others(
    db: sessionmaker[Session],
) -> None:
    with db() as session:
        switch.stop(session, customer_id=CUSTOMER, because="Checking a rule.")
        theirs = switch.may_write(session, customer_id=CUSTOMER, gate_open=True)
        somebody_else = switch.may_write(session, customer_id="999", gate_open=True)
    assert not theirs.may_write and theirs.stopped_by == "account"
    assert "Checking a rule." in theirs.because
    assert somebody_else.may_write


def test_everything_can_be_stopped_at_once(db: sessionmaker[Session]) -> None:
    """The morning a rule turns out to be wrong across three hundred accounts."""
    with db() as session:
        switch.stop(session, because="A rule is misbehaving.", ours=True)
        said = switch.may_write(session, customer_id=CUSTOMER, gate_open=True)
    assert not said.may_write
    assert said.stopped_by == "global"


def test_the_global_answer_is_given_before_the_account_one(
    db: sessionmaker[Session],
) -> None:
    """ "Stopped on your account" when it is stopped everywhere sends a merchant
    to the wrong conversation."""
    with db() as session:
        switch.stop(session, customer_id=CUSTOMER, because="theirs")
        switch.stop(session, because="everybody")
        said = switch.may_write(session, customer_id=CUSTOMER, gate_open=True)
    assert said.stopped_by == "global"


def test_pulling_a_switch_twice_does_not_stack_two(db: sessionmaker[Session]) -> None:
    """So releasing it once is enough, and "still stopped" cannot be a duplicate."""
    with db() as session:
        first = switch.stop(session, customer_id=CUSTOMER, because="one")
        again = switch.stop(session, customer_id=CUSTOMER, because="two")
        assert first.id == again.id
        switch.release(session, customer_id=CUSTOMER)
        assert switch.may_write(session, customer_id=CUSTOMER, gate_open=True).may_write


def test_a_merchant_cannot_release_a_switch_ppcway_pulled(
    db: sessionmaker[Session],
) -> None:
    """The one case it exists for would be a case they could overrule."""
    with db() as session:
        switch.stop(session, customer_id=CUSTOMER, because="We are looking at this.", ours=True)
        with pytest.raises(switch.WritesStopped, match="talk to us"):
            switch.release(session, customer_id=CUSTOMER)
        assert not switch.may_write(session, customer_id=CUSTOMER, gate_open=True).may_write


def test_staff_can_release_their_own_switch(db: sessionmaker[Session]) -> None:
    with db() as session:
        switch.stop(session, customer_id=CUSTOMER, because="looking", ours=True)
        released = switch.release(session, customer_id=CUSTOMER, staff=True)
        assert released is not None and released.released_at is not None
        assert switch.may_write(session, customer_id=CUSTOMER, gate_open=True).may_write


def test_a_released_switch_stays_in_the_record(db: sessionmaker[Session]) -> None:
    """That writes were once stopped is part of the account's history."""
    with db() as session:
        switch.stop(session, customer_id=CUSTOMER, because="one")
        switch.release(session, customer_id=CUSTOMER, released_by=uuid.uuid4())
        rows = session.scalars(sa.select(switch.KillSwitch)).all()
    assert len(rows) == 1
    assert rows[0].released_at is not None


def test_releasing_nothing_says_nothing_was_set(db: sessionmaker[Session]) -> None:
    with db() as session:
        assert switch.release(session, customer_id=CUSTOMER) is None


def test_the_tally_counts_operations_not_requests(db: sessionmaker[Session]) -> None:
    """One mutate carrying four hundred keywords spends four hundred."""
    with db() as session:
        quota.spend(session, CUSTOMER, 400, today=TODAY)
        session.commit()
        room = quota.room_today(session, CUSTOMER, today=TODAY)
    assert room.used == 400
    assert room.left == A_DAY - 400


def test_a_day_with_nothing_spent_has_the_whole_allowance(
    db: sessionmaker[Session],
) -> None:
    with db() as session:
        assert quota.room_today(session, CUSTOMER, today=TODAY).left == A_DAY


def test_each_day_starts_again(db: sessionmaker[Session]) -> None:
    with db() as session:
        quota.spend(session, CUSTOMER, 400, today=TODAY)
        session.commit()
        assert quota.room_today(session, CUSTOMER, today=date(2026, 11, 3)).used == 0


def test_the_eighty_percent_alert_fires_once_a_day(db: sessionmaker[Session]) -> None:
    """The brief's threshold. Once, not once a batch."""
    nearly = int(A_DAY * SHOUT_AT)
    with db() as session:
        quiet = quota.spend(session, CUSTOMER, nearly - 1, today=TODAY)
        assert not quiet.say_something

        loud = quota.spend(session, CUSTOMER, 1, today=TODAY)
        assert loud.say_something, "crossing the threshold says so"
        assert loud.share_used >= SHOUT_AT

        again = quota.spend(session, CUSTOMER, 10, today=TODAY)
        assert not again.say_something, "and says it once"
        session.commit()


def test_two_accounts_have_their_own_allowances(db: sessionmaker[Session]) -> None:
    with db() as session:
        quota.spend(session, CUSTOMER, 500, today=TODAY)
        quota.spend(session, "999", 10, today=TODAY)
        session.commit()
        assert quota.room_today(session, CUSTOMER, today=TODAY).used == 500
        assert quota.room_today(session, "999", today=TODAY).used == 10


def test_a_day_cannot_go_backwards(db: sessionmaker[Session]) -> None:
    """Quota is not given back: the honest error is to think we used more."""
    with db() as session:
        quota.spend(session, CUSTOMER, 100, today=TODAY)
        quota.spend(session, CUSTOMER, -50, today=TODAY)
        session.commit()
        assert quota.room_today(session, CUSTOMER, today=TODAY).used == 100
