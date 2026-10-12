"""Signing in, staying signed in, and signing out.

The browser holds a random token in a cookie; this holds its hash, who it belongs
to and when it stops working. A token is never written down anywhere else, so a
copy of the database is not a drawer of keys.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ppcway.auth.google import (
    SESSION_DAYS,
    GoogleIdentity,
    hash_session_token,
    new_session_token,
)
from ppcway.auth.models import Session, UserAccount


def sign_in(session: DbSession, who: GoogleIdentity) -> tuple[UserAccount, str]:
    """Find or make the account, start a session, and hand back its token once."""
    account = session.scalar(select(UserAccount).where(UserAccount.google_sub == who.sub))
    if account is None:
        account = UserAccount(google_sub=who.sub, email=who.email)
        session.add(account)
    # Their name, picture and address are Google's to change, so they are refreshed
    # on every sign-in rather than kept as they first arrived.
    account.email = who.email
    account.name = who.name
    account.picture = who.picture
    account.last_seen_at = datetime.now(UTC)
    session.flush()

    token = new_session_token()
    session.add(
        Session(
            token_hash=hash_session_token(token),
            user_id=account.id,
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    session.commit()
    return account, token


#: How long a session lasts from the last time it was used, not from sign-in. A
#: fixed window from sign-in signs out somebody who has been here every day.
#: Rolling it forward on use is what "stay signed in" actually means.
ROLL_AFTER = timedelta(hours=12)


def _aware(when: datetime) -> datetime:
    """SQLite hands back naive datetimes; Postgres does not."""
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def whoever_holds(session: DbSession, token: str | None) -> UserAccount | None:
    """The account a cookie belongs to, or None: expired, revoked and unknown all
    look the same from outside, because they mean the same thing.

    Using a session also renews it. The renewal is written at most twice a day,
    because every page in the app asks this question and a write per page view
    would cost more than it is worth.
    """
    if not token:
        return None
    held = session.scalar(select(Session).where(Session.token_hash == hash_session_token(token)))
    if held is None or held.revoked_at is not None:
        return None
    now = datetime.now(UTC)
    if _aware(held.expires_at) <= now:
        return None

    last = _aware(held.last_used_at) if held.last_used_at else None
    if last is None or now - last >= ROLL_AFTER:
        held.last_used_at = now
        held.expires_at = now + timedelta(days=SESSION_DAYS)
        session.commit()
    return session.get(UserAccount, held.user_id)


def sign_out_everywhere(session: DbSession, account: UserAccount) -> int:
    """Revoke every session this person has, on every device. Returns how many.

    What somebody wants when they have lost a laptop, and the only honest answer
    to "am I signed in anywhere else?".
    """
    now = datetime.now(UTC)
    live = session.scalars(
        select(Session).where(Session.user_id == account.id, Session.revoked_at.is_(None))
    ).all()
    for held in live:
        held.revoked_at = now
    session.commit()
    return len(live)


def sign_out(session: DbSession, token: str | None) -> None:
    """Revoke that one session. The row stays, as a record that it existed."""
    if not token:
        return
    held = session.scalar(select(Session).where(Session.token_hash == hash_session_token(token)))
    if held is not None and held.revoked_at is None:
        held.revoked_at = datetime.now(UTC)
        session.commit()
