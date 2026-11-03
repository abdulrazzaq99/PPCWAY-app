"""Who works for PPCWay, and the record of what they looked at.

**This is not `Role.ADMIN`.** That role already exists and means something
completely different: the admin *of one merchant's own account*, a person the
merchant invited. It is the single most dangerous confusion available in this
codebase, because wiring the internal panel to `Role.ADMIN` would hand every
merchant's own admin a window into every other merchant's business. So staff
is a separate table, keyed on the account, with no path from a membership to a
staff level and no role string shared between them.

**Granting is append-only, like the action log.** A row is written when access
is given and a second row when it is taken away; nothing is updated in place
and nothing is deleted. "Who could see this account in March" is a question
somebody will eventually have to answer -- a merchant asking, or a regulator --
and a mutable table cannot answer it.

**Three levels, because "admin" is not one thing.** Reading somebody's figures
to answer a support ticket, and switching off the thing that writes to their
Google Ads account, are not the same act and should not need the same
authority. Blueprint §8.3 makes the same argument about autonomy.

**Every read of a merchant's data by staff is written down.** Not every page
view -- the record would be noise -- but every time a member of staff opens one
named business. The brief's own privacy commitment is that a merchant's data is
theirs; an internal panel is the one place that promise is routinely bent, so
it is the one place the bending has to be visible.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


def _written_now() -> datetime:
    """The moment this row is written, to the microsecond.

    Set in Python rather than by `server_default=func.now()`, and that is not a
    style preference -- it is the difference between these tables working and
    not. Postgres's `now()` is the *transaction's* start time, identical for
    every row written in one transaction, and SQLite's `CURRENT_TIMESTAMP` has
    one-second granularity. Either way a grant and the withdrawal that follows
    it can land on the same timestamp, and then "the latest row" falls through
    to the tiebreak -- which was a random UUID.

    A withdrawal that silently loses a coin-toss against the grant it was
    meant to revoke is the worst bug this file could have. The tests found it:
    `test_withdrawing_is_a_row_and_not_a_deletion` failed with the access
    still granted.
    """
    return datetime.now(UTC)


class Level(str, enum.Enum):
    """What a member of PPCWay staff may do, in order.

    Spelled out rather than numbered for the reason `org.Role` is: a level
    appears in the record, and a reader should not have to look up what a 2
    meant.
    """

    #: Reads a merchant's figures to answer a question. Changes nothing.
    SUPPORT = "support"
    #: Reads everything support can, plus the platform's own health, and may
    #: re-run a job or clear a stuck one. Still cannot touch a merchant's
    #: Google Ads account or the switches that govern it.
    ENGINEER = "engineer"
    #: The kill switch, the feature gates, and granting staff access.
    PRINCIPAL = "principal"


#: What each level may do. Read as "may this level do this", and nothing else:
#: a capability absent here is refused, so adding a power is deliberate. The
#: shape deliberately mirrors `org.models.CAN`, because a reader who has
#: understood one should not have to learn a second idea.
MAY: dict[Level, frozenset[str]] = {
    Level.SUPPORT: frozenset({"read_merchant", "read_support_queue"}),
    Level.ENGINEER: frozenset(
        {
            "read_merchant",
            "read_support_queue",
            "read_platform",
            "run_job",
            "read_errors",
        }
    ),
    Level.PRINCIPAL: frozenset(
        {
            "read_merchant",
            "read_support_queue",
            "read_platform",
            "run_job",
            "read_errors",
            "stop_writes",
            "set_flags",
            "grant_staff",
        }
    ),
}

#: Ordered weakest first, so one level can be compared to another.
LADDER: tuple[Level, ...] = (Level.SUPPORT, Level.ENGINEER, Level.PRINCIPAL)


def may(level: Level, capability: str) -> bool:
    """Whether this level has this capability. The only way to ask."""
    return capability in MAY[level]


def at_least(held: Level, wanted: Level) -> bool:
    """Whether `held` is `wanted` or stronger."""
    return LADDER.index(held) >= LADDER.index(wanted)


class StaffGrant(Base):
    """One grant or withdrawal of staff access. Append-only.

    Two rows make a history: `granted=True` when access is given, `granted=False`
    when it is taken away. The current state is the latest row for an account,
    which is what `staff.guard.level_of` reads.
    """

    __tablename__ = "staff_grant"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: The person this is about.
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("account.id", ondelete="CASCADE"), index=True
    )
    #: Their level while this row is the latest one. Kept on a withdrawal too,
    #: so the record says what was taken away rather than only that something was.
    level: Mapped[str] = mapped_column(String(20))
    #: True for a grant, False for a withdrawal.
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    #: Who did it. Null only for the first principal, who has to come from
    #: somewhere -- a migration or the CLI -- because nobody exists to grant it.
    by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("account.id", ondelete="SET NULL"), nullable=True
    )
    #: Why, in words. Required: a grant with no stated reason is a grant nobody
    #: can review, and this table exists to be reviewed.
    because: Mapped[str] = mapped_column(Text, default="")
    #: Written in Python, to the microsecond. See `_written_now`: ordering by
    #: this is how the current level is decided, so it has to distinguish two
    #: rows written in one transaction. `server_default` is kept only so a row
    #: inserted by raw SQL still gets a time.
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_written_now, server_default=func.now()
    )


class StaffLook(Base):
    """One member of staff opening one named business. Append-only.

    Not a page-view log. This records the act the merchant would care about:
    somebody at PPCWay looked at *their* account. Blueprint §8.4 asks the same
    of automated changes, and the argument is the same -- a record written only
    when it is convenient is not a record.
    """

    __tablename__ = "staff_look"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("account.id", ondelete="CASCADE"), index=True
    )
    #: The business looked at. Not cascaded to deletion: if an organisation is
    #: removed, the fact that staff looked at it does not stop being true.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("organization.id", ondelete="SET NULL"), nullable=True, index=True
    )
    #: Kept as text as well as a key, so the record still names the business
    #: after the row it pointed at is gone.
    organization_name: Mapped[str] = mapped_column(String(200), default="")
    #: What they were doing: "merchant", "change-log", "support". Short and
    #: readable rather than an enum, because this is a record and not a switch.
    looked_at: Mapped[str] = mapped_column(String(40), default="merchant")
    level: Mapped[str] = mapped_column(String(20), default=Level.SUPPORT.value)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_written_now, server_default=func.now()
    )
