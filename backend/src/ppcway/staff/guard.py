"""Whether the person asking works here, and what they may do.

Everything in this file fails closed. A question it cannot answer is answered
"no": an unknown level, a withdrawn grant, a missing row, a level string the
code does not recognise. The internal panel is the one surface where a mistake
leaks one merchant's data to another, so "we could not tell" has to mean "then
you may not".

**No path from a membership to a staff level.** `org.Role.ADMIN` is a
merchant's own admin and must never reach this panel; `level_of` reads only
`staff_grant`, and the test
`test_a_merchants_own_admin_is_not_ppcway_staff` holds that.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.auth.models import UserAccount
from ppcway.org.models import Organization
from ppcway.staff.models import Level, StaffGrant, StaffLook, at_least, may

log = logging.getLogger(__name__)


class NotStaff(PermissionError):
    """The person asking does not work here, or no longer does."""


class NotAllowed(PermissionError):
    """They work here, but not at a level that may do this."""


def level_of(session: Session, account: UserAccount | uuid.UUID | None) -> Level | None:
    """The level this account holds now, or None.

    "Now" is the latest `staff_grant` row for the account. A withdrawal is a
    row like any other, so a person whose access was taken away reads as None
    without anything having been deleted.
    """
    if account is None:
        return None
    account_id = account if isinstance(account, uuid.UUID) else account.id
    latest = session.scalars(
        select(StaffGrant)
        .where(StaffGrant.account_id == account_id)
        .order_by(StaffGrant.at.desc(), StaffGrant.id.desc())
        .limit(1)
    ).first()
    if latest is None or not latest.granted:
        return None
    try:
        return Level(latest.level)
    except ValueError:
        # A level this code does not know. Refuse rather than guess: a typo in
        # a grant must not become more authority than was intended.
        log.warning("staff grant %s holds an unknown level %r", latest.id, latest.level)
        return None


def require(session: Session, account: UserAccount | None, capability: str) -> Level:
    """The caller's level, having checked they may do this. Raises otherwise.

    Returns the level rather than True, because the caller almost always needs
    it next -- to record what was done, or to decide how much to show.
    """
    held = level_of(session, account)
    if held is None:
        raise NotStaff("This is PPCWay's internal panel and you do not have access to it.")
    if not may(held, capability):
        raise NotAllowed(
            f"{held.value.title()} access cannot {capability.replace('_', ' ')}."
            " Ask somebody with principal access."
        )
    return held


def require_level(session: Session, account: UserAccount | None, wanted: Level) -> Level:
    """Like `require`, but by level rather than by named capability."""
    held = level_of(session, account)
    if held is None:
        raise NotStaff("This is PPCWay's internal panel and you do not have access to it.")
    if not at_least(held, wanted):
        raise NotAllowed(f"This needs {wanted.value} access and you have {held.value}.")
    return held


def grant(
    session: Session,
    *,
    account_id: uuid.UUID,
    level: Level,
    by_account_id: uuid.UUID | None,
    because: str,
) -> StaffGrant:
    """Give somebody staff access, with a reason on the record.

    The reason is required rather than optional. A grant nobody can review is
    the one kind this table cannot tolerate, and "because" is the whole review.
    """
    if not because.strip():
        raise ValueError(
            "a staff grant needs a stated reason: this table exists to be reviewed,"
            " and a row that does not say why cannot be."
        )
    row = StaffGrant(
        account_id=account_id,
        level=level.value,
        granted=True,
        by_account_id=by_account_id,
        because=because.strip(),
    )
    session.add(row)
    session.flush()
    log.info("staff access granted at %s by %s", level.value, by_account_id)
    return row


def withdraw(
    session: Session,
    *,
    account_id: uuid.UUID,
    by_account_id: uuid.UUID | None,
    because: str,
) -> StaffGrant | None:
    """Take staff access away. A row, not a deletion.

    None where they had none, which is not an error: asking twice should be
    safe, and the second ask has nothing to record.
    """
    held = level_of(session, account_id)
    if held is None:
        return None
    row = StaffGrant(
        account_id=account_id,
        # The level they held, so the record says what was taken away rather
        # than only that something was.
        level=held.value,
        granted=False,
        by_account_id=by_account_id,
        because=(because or "").strip() or "withdrawn",
    )
    session.add(row)
    session.flush()
    log.info("staff access at %s withdrawn by %s", held.value, by_account_id)
    return row


def note_look(
    session: Session,
    *,
    account: UserAccount,
    level: Level,
    place: Organization | None,
    looked_at: str = "merchant",
) -> StaffLook:
    """Write down that staff opened one named business.

    Called by the endpoint that serves the merchant view, not by the view
    itself: a record written where it is convenient is a record that goes
    missing when somebody adds a second caller.
    """
    row = StaffLook(
        account_id=account.id,
        organization_id=place.id if place is not None else None,
        organization_name=(place.name if place is not None else "") or "",
        looked_at=looked_at,
        level=level.value,
    )
    session.add(row)
    session.flush()
    return row


def who_looked(
    session: Session, *, organization_id: uuid.UUID, most: int = 50
) -> Sequence[StaffLook]:
    """Every time staff opened this business, newest first.

    Here so a merchant can be shown it. The promise that their data is theirs
    is worth more if they can see the exceptions.
    """
    return list(
        session.scalars(
            select(StaffLook)
            .where(StaffLook.organization_id == organization_id)
            .order_by(StaffLook.at.desc())
            .limit(most)
        )
    )
