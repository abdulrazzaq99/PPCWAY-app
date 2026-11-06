"""What day it is for an account: its own date, not UTC's.

Google files an account's figures under dates in the account's time zone, so
"yesterday" for its screens has to be yesterday there. Until 6 November it was
yesterday in UTC, and a new campaign's first day appeared at an hour that meant
nothing to the merchant.

Dates are taken from the clock and only the hour is set, so these hold on any
day they are run.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, time, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from ppcway.ads.clock import account_today, local_today, zone_of
from ppcway.ads.models import AdsConnection
from ppcway.ads.numbers import account_numbers
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.org.models import Organization  # noqa: F401 - a foreign key target

TODAY = datetime.now(UTC).date()
CUSTOMER = "2580586343"


def at(hour: int) -> datetime:
    """Today, at this hour UTC."""
    return datetime.combine(TODAY, time(hour, 0), tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[Session]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def connected(db: Session, time_zone: str) -> None:
    person = UserAccount(google_sub=str(uuid.uuid4()), email="dana@alphaplumbing.ca")
    db.add(person)
    db.flush()
    db.add(
        AdsConnection(
            account_id=person.id, ciphertext="locked", customer_id=CUSTOMER, time_zone=time_zone
        )
    )
    db.commit()


def test_in_the_small_hours_utc_it_is_still_yesterday_in_toronto() -> None:
    """02:00 UTC is 21:00 or 22:00 the evening before in Toronto."""
    assert local_today("America/Toronto", at(2)) == TODAY - timedelta(days=1)


def test_late_in_the_utc_evening_it_is_already_tomorrow_in_karachi() -> None:
    """21:00 UTC is 02:00 the next morning in Karachi."""
    assert local_today("Asia/Karachi", at(21)) == TODAY + timedelta(days=1)


@pytest.mark.parametrize("unread", ["", "Mars/Olympus_Mons"])
def test_a_zone_not_read_or_not_known_is_dated_in_utc_as_before(unread: str) -> None:
    """A wrong guess at a zone would be worse than the old behaviour."""
    assert local_today(unread, at(2)) == TODAY


def test_an_account_is_dated_in_the_zone_held_for_it(db: Session) -> None:
    connected(db, "America/Toronto")
    assert zone_of(db, CUSTOMER) == "America/Toronto"
    assert account_today(db, CUSTOMER, at(2)) == TODAY - timedelta(days=1)
    assert account_today(db, "someone-else", at(2)) == TODAY, "no zone held, so UTC"


def test_the_window_ends_at_the_account_s_yesterday(db: Session) -> None:
    """What the Campaigns page prints as "Oct 7 to Nov 5" comes from here."""
    connected(db, "Asia/Karachi")
    held = account_numbers(db, CUSTOMER, days=30, today=None)
    expected_last = account_today(db, CUSTOMER) - timedelta(days=1)
    assert held.ends_on == expected_last.isoformat()
    assert held.starts_on == (expected_last - timedelta(days=29)).isoformat()
