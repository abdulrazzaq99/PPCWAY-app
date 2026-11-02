"""How much of the day's allowance has been spent, and when to say so.

Google counts operations, not requests: one mutate carrying four hundred
keywords spends four hundred. A platform that counted requests would believe
it had used three of fifteen thousand on the morning it used twelve hundred,
and would find out when Google started refusing.

The client's brief asks for an alert at 80%. The number here is the figure the
guardrails' tenth check reads, so until this exists that check is answering
from an assumption -- a true one, because nothing had mutated anything, but an
assumption. This makes it a count.

**Counted before the call, not after.** An operation that Google refuses still
spends quota, and a crash between the call and the counting would hide what was
spent. So the day's figure is raised first and is not given back: the honest
error is to think we have used slightly more than we have, never less.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Final

from sqlalchemy import Date, Integer, String, UniqueConstraint, Uuid, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from ppcway.db.base import Base

log = logging.getLogger(__name__)

#: Google's daily operations allowance for an account with Basic access. The
#: number PPCWay is held to today; Standard access raises it, and this moves
#: when that application is approved rather than being guessed at now.
A_DAY: Final = 15_000

#: Where the brief asks us to start saying something.
SHOUT_AT: Final = 0.80


class QuotaDay(Base):
    """One account, one day, and the operations spent on it."""

    __tablename__ = "ads_quota_day"
    __table_args__ = (UniqueConstraint("customer_id", "day", name="one_tally_a_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    #: Operations, not requests. Google counts the former.
    used: Mapped[int] = mapped_column(Integer, default=0)
    #: How many times we have been told the account is near its limit, so the
    #: alert goes once a day rather than once a batch.
    warned: Mapped[int] = mapped_column(Integer, default=0)


@dataclass(frozen=True, slots=True)
class Room:
    """What is left today, and whether that is worth mentioning."""

    used: int
    allowance: int
    #: True the first time a day crosses the threshold, so a caller sends one
    #: alert rather than one per batch.
    say_something: bool = False

    @property
    def left(self) -> int:
        return max(0, self.allowance - self.used)

    @property
    def share_used(self) -> float:
        return round(self.used / self.allowance, 4) if self.allowance else 1.0

    @property
    def room_for(self) -> int:
        return self.left


def room_today(
    session: Session,
    customer_id: str,
    *,
    today: date | None = None,
    allowance: int = A_DAY,
) -> Room:
    """What this account has left today. Reads, counts nothing."""
    day = today or datetime.now(UTC).date()
    tally = _tally(session, customer_id, day)
    return Room(used=tally.used if tally else 0, allowance=allowance)


def spend(
    session: Session,
    customer_id: str,
    operations: int,
    *,
    today: date | None = None,
    allowance: int = A_DAY,
) -> Room:
    """Count operations against the day, before they are sent.

    Returns the day's standing afterwards, with `say_something` set once per
    day when the account crosses the threshold -- the caller sends the alert,
    because sending email is not this module's business and a quota counter
    that could send email would be one nothing could test quietly.
    """
    day = today or datetime.now(UTC).date()
    tally = _tally(session, customer_id, day)
    if tally is None:
        tally = QuotaDay(customer_id=customer_id, day=day, used=0)
        session.add(tally)
        session.flush()
    tally.used += max(0, operations)

    crossed = tally.used >= allowance * SHOUT_AT
    first_time = crossed and tally.warned == 0
    if first_time:
        tally.warned = 1
        log.warning(
            "account %s has used %d of %d operations today",
            customer_id,
            tally.used,
            allowance,
        )
    session.flush()
    return Room(used=tally.used, allowance=allowance, say_something=first_time)


def _tally(session: Session, customer_id: str, day: date) -> QuotaDay | None:
    return session.scalars(
        select(QuotaDay).where(QuotaDay.customer_id == customer_id, QuotaDay.day == day)
    ).first()
