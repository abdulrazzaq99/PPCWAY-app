"""The phase-one gate, counted rather than claimed.

A gate that reports itself as passed because nobody counted is worse than no
gate at all, so the test that matters most here is the one where we are running
on two accounts and it says two.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.gate import gate_report
from ppcway.ads.mirror import SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.org.models import Organization  # noqa: F401 - a connection points at one

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def account(db: DbSession, customer_id: str, name: str) -> AdsConnection:
    person = UserAccount(email=f"{customer_id}@example.ca", name=name)
    db.add(person)
    db.commit()
    connection = AdsConnection(
        account_id=person.id, ciphertext="x", customer_id=customer_id, customer_name=name
    )
    db.add(connection)
    db.commit()
    return connection


def clean_week(db: DbSession, customer_id: str, *, days: int = 7, skip: int = 0) -> None:
    for back in range(1, days + 1):
        if back == skip:
            continue
        db.add(
            SyncRun(
                customer_id=customer_id,
                kind="today",
                status="done",
                started_at=NOW - timedelta(days=back),
                finished_at=NOW - timedelta(days=back),
            )
        )
    db.commit()


def test_seven_clean_days_passes_for_that_account(db: DbSession) -> None:
    account(db, "1", "Byte9")
    clean_week(db, "1")

    gate = gate_report(db, now=NOW)

    assert gate.accounts[0].clean_days == 7
    assert gate.accounts[0].passing is True
    assert gate.passing == 1


def test_a_day_with_no_read_at_all_is_a_gap_not_a_pass(db: DbSession) -> None:
    account(db, "1", "Byte9")
    clean_week(db, "1", skip=3)

    gate = gate_report(db, now=NOW)

    assert gate.accounts[0].clean_days == 6
    assert gate.accounts[0].silent_days == [(NOW.date() - timedelta(days=3)).isoformat()]
    assert gate.accounts[0].passing is False


def test_a_failure_spoils_the_day_even_with_a_success_beside_it(db: DbSession) -> None:
    account(db, "1", "Byte9")
    clean_week(db, "1")
    db.add(
        SyncRun(
            customer_id="1",
            kind="structure",
            status="failed",
            trouble="That permission was refused",
            started_at=NOW - timedelta(days=2),
        )
    )
    db.commit()

    gate = gate_report(db, now=NOW)

    assert gate.accounts[0].clean_days == 6
    assert gate.accounts[0].failed_days == [(NOW.date() - timedelta(days=2)).isoformat()]
    assert gate.accounts[0].trouble == "That permission was refused"


def test_the_sentence_says_two_of_five_when_that_is_the_truth(db: DbSession) -> None:
    for n in (1, 2):
        account(db, str(n), f"Account {n}")
        clean_week(db, str(n))

    gate = gate_report(db, now=NOW)

    assert gate.passed is False
    assert gate.said == (
        "2 of the 5 accounts the gate asks for have 7 clean days. "
        "It is running on 2 connected accounts. The gate is not passed."
    )


def test_five_clean_accounts_pass_the_gate(db: DbSession) -> None:
    for n in range(1, 6):
        account(db, str(n), f"Account {n}")
        clean_week(db, str(n))

    gate = gate_report(db, now=NOW)

    assert gate.passed is True
    assert gate.said == "5 accounts have 7 clean days of syncing. The gate is passed."


def test_nothing_connected_says_there_is_nothing_to_measure(db: DbSession) -> None:
    gate = gate_report(db, now=NOW)

    assert gate.passed is False
    assert "nothing to measure" in gate.said


def test_a_disconnected_account_is_not_counted(db: DbSession) -> None:
    connection = account(db, "1", "Byte9")
    clean_week(db, "1")
    connection.revoked_at = NOW
    db.commit()

    assert gate_report(db, now=NOW).accounts == []


def test_today_is_not_counted_because_the_day_is_not_over(db: DbSession) -> None:
    account(db, "1", "Byte9")
    clean_week(db, "1")
    db.add(SyncRun(customer_id="1", kind="today", status="done", started_at=NOW))
    db.commit()

    # Still seven: a run today cannot make an eighth clean day in a seven-day window.
    assert gate_report(db, now=NOW).accounts[0].clean_days == 7
