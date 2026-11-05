"""Sending approved changes: straight after a yes, and on the scheduled pass.

Until this existed nothing called the gateway, so an approved change sat
approved for ever while the merchant had been told Otto would make it. These
hold the two callers to the same rules: nothing leaves while a switch is shut,
nothing is unlocked to find that out, one change goes once, and every outcome
is said in words.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.mirror import MirrorKeyword
from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.gateway import send as sending
from ppcway.gateway import switch
from ppcway.gateway.google import GoogleRefused
from ppcway.gateway.port import Applied, Batch
from ppcway.opt.models import GuardrailConfig, OptimizationAction, Status
from ppcway.org.models import Organization

CUSTOMER = "2580586343"
NOW = datetime.now(UTC)
GROUP = f"customers/{CUSTOMER}/adGroups/21"


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


@pytest.fixture
def place(db: sessionmaker[Session]) -> uuid.UUID:
    with db() as session:
        business = Organization(name="Alpha Plumbing")
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add_all([business, person])
        session.flush()
        session.add(
            AdsConnection(
                account_id=person.id,
                organization_id=business.id,
                ciphertext="locked",
                customer_id=CUSTOMER,
                currency="CAD",
                account_status="ENABLED",
                status_read_at=NOW - timedelta(hours=1),
            )
        )
        for n in range(50):
            session.add(
                MirrorKeyword(
                    customer_id=CUSTOMER,
                    resource_name=f"customers/{CUSTOMER}/adGroupCriteria/21~{n}",
                    criterion_id=str(n),
                    ad_group_id="21",
                    campaign_id="11",
                    status="ENABLED",
                    seen_at=NOW,
                )
            )
        session.add(GuardrailConfig(organization_id=business.id, version=1))
        session.commit()
        return business.id


class Door:
    """A door that records what it was asked to send and answers as told."""

    def __init__(self, answer: Applied | Exception | None = None) -> None:
        self.answer = answer
        self.sent: list[Batch] = []

    def mutate(self, batch: Batch) -> Applied:
        self.sent.append(batch)
        if isinstance(self.answer, Exception):
            raise self.answer
        if self.answer is not None:
            return self.answer
        return Applied(
            landed=tuple(
                f"customers/{CUSTOMER}/adGroupCriteria/21~{900 + n}" for n in range(batch.how_many)
            ),
            operations_used=batch.how_many,
        )


class Doors:
    """Hands out one `Door` and counts how often it was asked for one."""

    def __init__(self, door: Door | None = None, refuse: str = "") -> None:
        self.door = door or Door()
        self.refuse = refuse
        self.opened = 0

    def __call__(self, connection: AdsConnection) -> Door:
        self.opened += 1
        if self.refuse:
            raise sending.NoDoor(self.refuse)
        return self.door


def approved(
    db: sessionmaker[Session],
    place: uuid.UUID,
    *,
    text: str = "pdf to word",
    payload: dict[str, Any] | None = None,
    approved_minutes_ago: int = 5,
    taken_minutes_ago: int | None = None,
) -> uuid.UUID:
    with db() as session:
        row = OptimizationAction(
            organization_id=place,
            customer_id=CUSTOMER,
            kind="add_negative_keyword",
            target_kind="search_term",
            target_id=f"hash-{text}",
            target_label=text,
            before={"excluded": False},
            after={"excluded": True},
            payload=(
                payload
                if payload is not None
                else {
                    "change": "exclude_search",
                    "text": text,
                    "match_type": "EXACT",
                    "ad_groups": [GROUP],
                    "resources": [GROUP],
                }
            ),
            reason=f"Nobody who searched {text} got in touch.",
            evidence={
                "figures": [{"id": "spend", "as_of": (NOW - timedelta(hours=8)).isoformat()}]
            },
            rule_id="R1",
            rule_version=1,
            route="owner",
            risk="low",
            status=Status.APPROVED.value,
            approved_at=NOW - timedelta(minutes=approved_minutes_ago),
            taken_at=(
                NOW - timedelta(minutes=taken_minutes_ago)
                if taken_minutes_ago is not None
                else None
            ),
        )
        session.add(row)
        session.flush()
        row.idempotency_key = f"R1:{row.id}"
        session.commit()
        return row.id


def _send(
    db: sessionmaker[Session], action_id: uuid.UUID, doors: Doors, *, gate_open: bool = True
) -> sending.Sent:
    with db() as session:
        action = session.get(OptimizationAction, action_id)
        assert action is not None
        connection = sending.connection_for(session, action)
        assert connection is not None
        return sending.send(
            session, action, connection=connection, gate_open=gate_open, door_for=doors, now=NOW
        )


def _row(db: sessionmaker[Session], action_id: uuid.UUID) -> OptimizationAction:
    with db() as session:
        row = session.get(OptimizationAction, action_id)
        assert row is not None
        return row


def test_a_yes_is_made_there_and_then_when_writes_are_on(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    action = approved(db, place)
    doors = Doors()
    said = _send(db, action, doors)
    assert said.status == Status.APPLIED.value
    assert said.words == 'Searches for "pdf to word" no longer show your ads.'
    (batch,) = doors.door.sent
    assert batch.operations[0].fields["keyword"] == {"text": "pdf to word", "matchType": "EXACT"}
    assert _row(db, action).outcome["landed"] == [  # type: ignore[index]
        f"customers/{CUSTOMER}/adGroupCriteria/21~900"
    ]


def test_with_the_gate_shut_nothing_is_unlocked_and_nothing_sent(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    """No permission is decrypted and no token asked for just to learn that
    writes are off."""
    action = approved(db, place)
    doors = Doors()
    said = _send(db, action, doors, gate_open=False)
    assert said.held and said.stopped_by == "gate"
    assert doors.opened == 0
    row = _row(db, action)
    assert row.status == Status.APPROVED.value
    assert row.taken_at is None


def test_a_kill_switch_holds_it_and_says_why(db: sessionmaker[Session], place: uuid.UUID) -> None:
    action = approved(db, place)
    with db() as session:
        switch.stop(session, customer_id=CUSTOMER, because="The owner paused changes.")
    doors = Doors()
    said = _send(db, action, doors)
    assert said.held and said.stopped_by == "account"
    assert "The owner paused changes." in said.words
    assert doors.opened == 0


def test_a_permission_that_stopped_working_leaves_the_change_waiting(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    """A connection problem is not Google refusing the change. Reconnecting
    is what it needs, and then the next pass sends it."""
    action = approved(db, place)
    said = _send(db, action, Doors(refuse="Reconnect it in Settings."))
    assert said.held
    assert "Reconnect" in said.words
    row = _row(db, action)
    assert (row.status, row.taken_at) == (Status.APPROVED.value, None)


def test_a_row_that_describes_nothing_sendable_is_refused_once_with_its_reason(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    """Left approved, every pass would trip over it for ever."""
    action = approved(db, place, payload={})
    said = _send(db, action, Doors())
    assert said.status == Status.REJECTED.value
    row = _row(db, action)
    assert row.status == Status.REJECTED.value
    assert row.outcome is not None and row.outcome["unsendable"] is True


def test_google_s_refusal_is_said_in_its_words(db: sessionmaker[Session], place: uuid.UUID) -> None:
    action = approved(db, place)
    said = _send(db, action, Doors(Door(GoogleRefused("Google refused the request: 400 bad"))))
    assert said.status == Status.FAILED.value
    assert "400 bad" in said.words


def test_the_pass_holds_everything_while_the_gate_is_shut(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    approved(db, place, text="pdf to word")
    approved(db, place, text="free plumbing course")
    doors = Doors()
    done = sending.send_waiting(
        db, SimpleNamespace(ads_writes_enabled=False), door_for=doors, now=NOW
    )  # type: ignore[arg-type]
    assert (done.waiting, done.held, done.applied) == (2, 2, 0)
    assert done.held_because == [
        (
            "PPCWay is not writing to Google Ads yet. Changes are proposed and recorded;"
            " nothing is applied."
        )
    ]
    assert doors.opened == 0


def test_the_pass_sends_what_is_waiting_oldest_yes_first(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    newer = approved(db, place, text="pdf to word", approved_minutes_ago=5)
    older = approved(db, place, text="free plumbing course", approved_minutes_ago=50)
    doors = Doors()
    done = sending.send_waiting(
        db, SimpleNamespace(ads_writes_enabled=True), door_for=doors, now=NOW
    )  # type: ignore[arg-type]
    assert (done.waiting, done.applied, done.held) == (2, 2, 0)
    sent = [b.operations[0].fields["keyword"]["text"] for b in doors.door.sent]
    assert sent == ["free plumbing course", "pdf to word"]
    assert doors.opened == 1, "one access token per account per pass"
    assert _row(db, older).status == _row(db, newer).status == Status.APPLIED.value


def test_the_pass_leaves_a_taken_change_alone_and_reports_one_never_answered(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    """Taken and unanswered means a send was interrupted. Only a person
    looking at Google Ads can say whether it landed, so it is never resent."""
    stuck = approved(db, place, taken_minutes_ago=30)
    doors = Doors()
    done = sending.send_waiting(
        db, SimpleNamespace(ads_writes_enabled=True), door_for=doors, now=NOW
    )  # type: ignore[arg-type]
    assert done.waiting == 0
    assert done.stuck == 1
    assert doors.door.sent == []
    assert _row(db, stuck).status == Status.APPROVED.value


def test_one_change_going_wrong_does_not_cost_the_rest_their_turn(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    approved(db, place, text="pdf to word", approved_minutes_ago=50)
    fine = approved(db, place, text="free plumbing course", approved_minutes_ago=5)

    class Breaks(Door):
        def mutate(self, batch: Batch) -> Applied:
            if batch.operations[0].fields["keyword"]["text"] == "pdf to word":
                raise RuntimeError("something nobody expected")
            return super().mutate(batch)

    done = sending.send_waiting(
        db, SimpleNamespace(ads_writes_enabled=True), door_for=Doors(Breaks()), now=NOW
    )  # type: ignore[arg-type]
    assert done.applied == 1
    assert done.held == 1
    assert _row(db, fine).status == Status.APPLIED.value


def test_a_change_only_goes_through_its_own_business_s_connection(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    """One Google Ads account can be connected to two businesses."""
    action = approved(db, place)
    with db() as session:
        other = Organization(name="Somebody Else")
        person = UserAccount(email="someone@else.ca", name="Someone")
        session.add_all([other, person])
        session.flush()
        session.add(
            AdsConnection(
                account_id=person.id,
                organization_id=other.id,
                ciphertext="theirs",
                customer_id=CUSTOMER,
            )
        )
        session.commit()
        row = session.get(OptimizationAction, action)
        assert row is not None
        found = sending.connection_for(session, row)
        assert found is not None and found.organization_id == place


@pytest.mark.parametrize(
    ("sent", "undoing", "says"),
    [
        (
            sending.Sent("applied", "The ad is paused."),
            False,
            "Done. The ad is paused. You can undo",
        ),
        (sending.Sent("applied", "Back on."), True, "Done. Back on."),
        (
            sending.Sent("approved", "", held=True, stopped_by="gate"),
            False,
            (
                "Approved. PPCWay is not making changes in Google Ads yet, so nothing in"
                " your account has changed."
            ),
        ),
        (
            sending.Sent("approved", "Paused by PPCWay.", held=True, stopped_by="global"),
            False,
            "Approved. Changes to Google Ads are stopped right now: Paused by PPCWay.",
        ),
        (sending.Sent("failed", "Google would not make that change: no."), False, "Google would"),
    ],
)
def test_the_words_after_a_yes_never_promise_more_than_happened(
    sent: sending.Sent, undoing: bool, says: str
) -> None:
    assert sending.words_for(sent, undoing=undoing).startswith(says)


def test_the_pass_follows_the_panel_switch_not_only_the_deployment_setting(
    db: sessionmaker[Session], place: uuid.UUID
) -> None:
    """Writes switched on in the panel, with the deployment's setting off:
    the switch wins, and what was approved while writes were off goes out."""
    approved(db, place)
    with db() as session:
        switch.set_gate(session, is_open=True, because="testing the write path", set_by=None)
    doors = Doors()
    done = sending.send_waiting(
        db,
        SimpleNamespace(ads_writes_enabled=False),  # type: ignore[arg-type]
        door_for=doors,
        now=NOW,
    )
    assert (done.waiting, done.applied) == (1, 1), done.as_dict()

    approved(db, place, text="free plumbing course")
    with db() as session:
        switch.set_gate(session, is_open=False, because="done testing", set_by=None)
    done = sending.send_waiting(
        db,
        SimpleNamespace(ads_writes_enabled=True),  # type: ignore[arg-type]
        door_for=doors,
        now=NOW,
    )
    assert (done.waiting, done.held, done.applied) == (1, 1, 0), "switched off in the panel wins"
    assert len(doors.door.sent) == 1
    with db() as session:
        assert sending.waiting_count(session) == 1
