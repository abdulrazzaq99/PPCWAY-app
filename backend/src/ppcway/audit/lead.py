"""The gate on the free audit: a lead, and an address they have proved.

The score and the counts are shown to anybody who runs an audit. The findings —
what is wrong, how to fix it, what it is costing — are shown once the person has
proved the email address is theirs. That is the whole bargain of the page, and
the client's requirement: paid traffic in, verified leads out.

What matters here is what the code can and cannot be used for:

- it is **stored as a hash**, like every other secret in this codebase, so a
  stolen database row does not unlock anybody's report;
- it is **tied to the address it was sent to**, so changing the address throws
  the old code away rather than leaving a second way in;
- it **expires**, it **runs out of guesses**, and **asking for another replaces
  the last**, so a code read from an older email stops working the moment a
  newer one is sent.

A wrong code and an expired code are told apart to the person's face, because
they call for different actions — try again, or ask for another.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.audit.models import AuditRequest, EmailCode

log = logging.getLogger(__name__)

#: Six digits, as the design asks. Short enough to read off a phone and type.
DIGITS = 6

#: How long a code is good for.
GOOD_FOR = timedelta(minutes=15)

#: Wrong guesses before this code is spent and a new one has to be asked for.
MOST_TRIES = 5

#: How long before another code may be asked for. Stops the button being a way
#: of posting mail to somebody repeatedly.
COOLDOWN = timedelta(seconds=30)


class Answer(str, Enum):
    """What came of checking a code."""

    RIGHT = "right"
    WRONG = "wrong"
    EXPIRED = "expired"
    SPENT = "spent"
    NONE = "none"

    @property
    def said(self) -> str:
        return {
            Answer.RIGHT: "",
            Answer.WRONG: "That code is not right. Check the email and try again.",
            Answer.EXPIRED: "That code has expired. Ask for a new one.",
            Answer.SPENT: "Too many tries on that code. Ask for a new one.",
            Answer.NONE: "Ask for a code first.",
        }[self]


@dataclass
class Posted:
    """A code that was made, and whether it is this moment's to send."""

    code: str = ""
    sent: bool = False
    wait_seconds: int = 0

    @property
    def too_soon(self) -> bool:
        return not self.sent and self.wait_seconds > 0


def fingerprint(code: str) -> str:
    """What is stored. The code itself is never kept."""
    return hashlib.sha256(code.encode()).hexdigest()


def new_code() -> str:
    """Six digits, evenly spread, leading zeros kept."""
    return f"{secrets.randbelow(10**DIGITS):0{DIGITS}d}"


def take_the_lead(
    session: Session,
    request: AuditRequest,
    *,
    name: str,
    email: str,
    phone: str,
    tips_opt_in: bool = False,
    came_from: dict[str, Any] | None = None,
    consent_text: str = "",
    now: datetime | None = None,
) -> AuditRequest:
    """Keep who asked, before they have proved the address.

    Saved at this point rather than after verifying, deliberately: somebody who
    gives their details and never finishes is still somebody who asked, and
    throwing that away to keep the table tidy would be throwing away the lead
    the page exists to collect. `verified_at` is what tells the two apart.
    """
    at = now or datetime.now(UTC)
    request.name = name.strip()
    request.email = email.strip().lower()
    request.phone = phone.strip()
    if came_from:
        request.came_from = came_from
    if consent_text:
        request.consent_text = consent_text
    if tips_opt_in and not request.tips_opt_in:
        request.tips_opt_in = True
        request.tips_opt_in_at = at
    elif not tips_opt_in:
        request.tips_opt_in = False
        request.tips_opt_in_at = None
    session.commit()
    return request


def live_code(
    session: Session, request_id: Any, *, now: datetime | None = None
) -> EmailCode | None:
    """The newest code for this request, used or not."""
    return session.scalars(
        select(EmailCode)
        .where(EmailCode.request_id == request_id)
        .order_by(EmailCode.sent_at.desc())
    ).first()


def post_a_code(
    session: Session,
    request: AuditRequest,
    *,
    now: datetime | None = None,
    force: bool = False,
) -> Posted:
    """Make a code to send, unless one went out moments ago.

    The plain code is returned once, here, and never again: the row keeps only
    its hash. `force` is for the first send, which no cooldown should block.
    """
    at = now or datetime.now(UTC)
    last = live_code(session, request.id)
    if last is not None and not force:
        since = at - _aware(last.sent_at)
        if since < COOLDOWN:
            return Posted(wait_seconds=int((COOLDOWN - since).total_seconds()) + 1)

    code = new_code()
    session.add(
        EmailCode(
            request_id=request.id,
            code_hash=fingerprint(code),
            sent_to=request.email,
            expires_at=at + GOOD_FOR,
        )
    )
    session.commit()
    return Posted(code=code, sent=True)


def check_code(
    session: Session,
    request: AuditRequest,
    given: str,
    *,
    now: datetime | None = None,
) -> Answer:
    """Is this the code we sent, to the address we sent it to, still in time?"""
    at = now or datetime.now(UTC)
    code = live_code(session, request.id)
    if code is None:
        return Answer.NONE
    if code.used_at is not None:
        return Answer.SPENT
    if code.attempts >= MOST_TRIES:
        return Answer.SPENT
    if _aware(code.expires_at) <= at:
        return Answer.EXPIRED
    # The address moved on after this code was sent, so the code did not.
    if code.sent_to and code.sent_to != request.email:
        return Answer.EXPIRED

    typed = "".join(ch for ch in given if ch.isdigit())
    if not secrets.compare_digest(fingerprint(typed), code.code_hash):
        code.attempts += 1
        session.commit()
        return Answer.SPENT if code.attempts >= MOST_TRIES else Answer.WRONG

    code.used_at = at
    request.verified_at = at
    session.commit()
    return Answer.RIGHT


def _aware(when: datetime) -> datetime:
    """SQLite gives naive datetimes back; Postgres does not. Compare like for like."""
    return when if when.tzinfo else when.replace(tzinfo=UTC)
