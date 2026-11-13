"""Signing in, or up, with six digits sent by email.

Somebody types their address, a code arrives, they type the code, and they are
in. The same two steps are a sign-up for an address PPCWay has not seen: the
account is made when the code comes back, because that is the moment the
address is proved to be theirs. Nobody gets an account by typing somebody
else's address.

A code is a way into somebody's account, so it is treated like one:

- **held as an Argon2 hash** (see `SignInCode`), so a copy of the table does
  not hand out the codes still waiting in people's inboxes;
- **ten minutes, once**, and asking for another retires the last, so a code
  read from an older email stops working the moment a newer one is sent;
- **five wrong guesses** spend it. With at most five codes an hour, that is
  twenty-five guesses an hour at a million possibilities;
- **a minute between codes, five an hour**, so the button cannot be used to
  fill somebody's inbox.

The answer to "send me a code" is the same whether or not the address has an
account. Whether somebody is a customer is not a stranger's business, and here
it costs nothing to keep: an unknown address is simply a sign-up.
"""

from __future__ import annotations

import math
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ppcway.auth.accounts import by_email
from ppcway.auth.models import SignInCode, UserAccount

#: Six digits: short enough to read off a phone's lock screen and type.
DIGITS = 6

#: How long a code works for.
GOOD_FOR = timedelta(minutes=10)

#: Wrong guesses before a code is spent.
MOST_TRIES = 5

#: The least time between two codes to one address.
COOLDOWN = timedelta(seconds=60)

#: The most codes one address gets in an hour.
MOST_PER_HOUR = 5

_hasher = PasswordHasher()


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
            Answer.SPENT: "That code cannot be used any more. Ask for a new one.",
            Answer.NONE: "Ask for a code first.",
        }[self]


@dataclass(frozen=True)
class Posted:
    """A code to send, or how long until one may be."""

    code: str = ""
    wait_seconds: int = 0
    #: True when the hour's allowance is used up, rather than the minute's.
    for_the_hour: bool = False

    @property
    def sent(self) -> bool:
        return bool(self.code)


def address(email: str) -> str:
    """One spelling of an address, however it was typed."""
    return email.strip().lower()


def new_code() -> str:
    """Six digits, evenly spread, leading zeros kept."""
    return f"{secrets.randbelow(10**DIGITS):0{DIGITS}d}"


def post_code(session: DbSession, email: str, *, now: datetime | None = None) -> Posted:
    """Make a code for this address, unless one went out too recently.

    The plain code is returned here, once, for the email. The row keeps only
    its hash.
    """
    at = now or datetime.now(UTC)
    to = address(email)

    last = _newest(session, to)
    if last is not None:
        since = at - _aware(last.sent_at)
        if since < COOLDOWN:
            return Posted(wait_seconds=_seconds(COOLDOWN - since))

    hour_ago = at - timedelta(hours=1)
    recent = session.scalars(
        select(SignInCode.sent_at)
        .where(SignInCode.email == to, SignInCode.sent_at > hour_ago)
        .order_by(SignInCode.sent_at.asc())
    ).all()
    if len(recent) >= MOST_PER_HOUR:
        # The oldest of them leaving the hour is when the next one may go.
        free_at = _aware(recent[0]) + timedelta(hours=1)
        return Posted(wait_seconds=_seconds(free_at - at), for_the_hour=True)

    code = new_code()
    session.add(
        SignInCode(
            email=to,
            code_hash=_hasher.hash(code),
            sent_at=at,
            expires_at=at + GOOD_FOR,
        )
    )
    session.commit()
    return Posted(code=code)


def check_code(
    session: DbSession, email: str, given: str, *, now: datetime | None = None
) -> Answer:
    """Whether this is the newest code sent to this address, still good."""
    at = now or datetime.now(UTC)
    code = _newest(session, address(email), lock=True)
    if code is None:
        session.rollback()
        return Answer.NONE
    if code.used_at is not None or code.attempts >= MOST_TRIES:
        session.rollback()
        return Answer.SPENT
    if _aware(code.expires_at) <= at:
        session.rollback()
        return Answer.EXPIRED

    typed = "".join(ch for ch in given if ch.isdigit())
    if len(typed) != DIGITS or not _matches(code.code_hash, typed):
        code.attempts += 1
        session.commit()
        return Answer.SPENT if code.attempts >= MOST_TRIES else Answer.WRONG

    code.used_at = at
    session.commit()
    return Answer.RIGHT


def sign_in_by_code(
    session: DbSession,
    email: str,
    given: str,
    *,
    name: str = "",
    now: datetime | None = None,
) -> tuple[Answer, UserAccount | None]:
    """The account this code opens, made on the spot for a new address.

    An account that came by Google or by password is the same account: the
    address is what is proved, and it is theirs. The address counts as
    confirmed from here on, since reading the code proves exactly that.
    """
    at = now or datetime.now(UTC)
    answer = check_code(session, email, given, now=at)
    if answer is not Answer.RIGHT:
        return answer, None

    account = by_email(session, address(email))
    if account is None:
        account = UserAccount(google_sub=None, email=address(email), name=name.strip()[:200])
        session.add(account)
    if account.email_verified_at is None:
        account.email_verified_at = at
    account.last_seen_at = at
    session.commit()
    return answer, account


def _newest(session: DbSession, email: str, *, lock: bool = False) -> SignInCode | None:
    """The newest code for the address. Taken for update when it is about to
    be checked, so two guesses at once cannot both get the last try."""
    query = (
        select(SignInCode)
        .where(SignInCode.email == email)
        .order_by(SignInCode.sent_at.desc())
        .limit(1)
    )
    if lock:
        query = query.with_for_update()
    return session.scalars(query).first()


def _matches(stored: str, typed: str) -> bool:
    try:
        return _hasher.verify(stored, typed)
    except (VerificationError, InvalidHashError):
        return False


def _seconds(left: timedelta) -> int:
    """Whole seconds to wait, rounded up, never zero."""
    return max(1, math.ceil(left.total_seconds()))


def _aware(when: datetime) -> datetime:
    """SQLite gives naive datetimes back; Postgres does not."""
    return when if when.tzinfo else when.replace(tzinfo=UTC)
