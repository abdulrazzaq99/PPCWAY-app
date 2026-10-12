"""Signing up and signing in with an address and a password.

Google's button is the quick way in; this is the one a business owner uses when
they do not want another Google account, and the one their staff use when the
owner invites them.

Two rules run through all of it. An address is never confirmed or denied to a
stranger — "no account with that address" tells somebody whether their neighbour
is a customer — and a link is a one-time thing, held as a hash.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ppcway.auth.google import hash_session_token
from ppcway.auth.models import LinkToken, UserAccount
from ppcway.auth.passwords import (
    RESET_HOURS,
    VERIFY_HOURS,
    expiry,
    hash_password,
    needs_rehash,
    new_link_token,
    password_matches,
)


class AlreadyHere(ValueError):
    """That address already has an account."""


def by_email(session: DbSession, email: str) -> UserAccount | None:
    """Find somebody by address, however they capitalised it."""
    return session.scalar(
        select(UserAccount).where(func.lower(UserAccount.email) == email.strip().lower())
    )


def register(
    session: DbSession, *, email: str, password: str, name: str = ""
) -> tuple[UserAccount, str]:
    """Make an account, and return the secret for the verification link.

    Somebody who already signed in with Google and now wants a password is not a
    new account: the password is added to the one they have.
    """
    address = email.strip().lower()
    existing = by_email(session, address)
    if existing is not None:
        if existing.password_hash:
            raise AlreadyHere(address)
        # Google first, password second. The address is already proven theirs.
        existing.password_hash = hash_password(password)
        if name and not existing.name:
            existing.name = name
        session.commit()
        return existing, ""

    account = UserAccount(
        google_sub=None,
        email=address,
        name=name.strip(),
        password_hash=hash_password(password),
    )
    session.add(account)
    session.flush()
    secret = _issue(session, account, "verify", VERIFY_HOURS)
    session.commit()
    return account, secret


def sign_in_with_password(session: DbSession, *, email: str, password: str) -> UserAccount | None:
    """The account, or None. Wrong address and wrong password look the same."""
    account = by_email(session, email)
    if account is None or not account.password_hash:
        return None
    if not password_matches(account.password_hash, password):
        return None
    if needs_rehash(account.password_hash):
        # Their password is right; store it again under today's settings.
        account.password_hash = hash_password(password)
    account.last_seen_at = datetime.now(UTC)
    session.commit()
    return account


def _issue(session: DbSession, account: UserAccount, purpose: str, hours: int) -> str:
    """One live link of each kind per account: a new one retires the last."""
    for old in session.scalars(
        select(LinkToken).where(
            LinkToken.account_id == account.id,
            LinkToken.purpose == purpose,
            LinkToken.used_at.is_(None),
        )
    ):
        old.used_at = datetime.now(UTC)
    secret, digest = new_link_token()
    session.add(
        LinkToken(
            account_id=account.id,
            purpose=purpose,
            token_hash=digest,
            expires_at=expiry(hours),
        )
    )
    return secret


def _spend(session: DbSession, token: str, purpose: str) -> UserAccount | None:
    """Use a link once, or None if it is spent, expired or not that kind."""
    if not token:
        return None
    held = session.scalar(
        select(LinkToken).where(
            LinkToken.token_hash == hash_session_token(token), LinkToken.purpose == purpose
        )
    )
    if held is None or held.used_at is not None:
        return None
    expires = held.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        return None
    held.used_at = datetime.now(UTC)
    return session.get(UserAccount, held.account_id)


def fresh_verification(session: DbSession, account: UserAccount) -> str:
    """Another verification link, for somebody who lost the first."""
    secret = _issue(session, account, "verify", VERIFY_HOURS)
    session.commit()
    return secret


def verify(session: DbSession, token: str) -> UserAccount | None:
    """Confirm an address. Doing it twice is not an error, it is just done."""
    account = _spend(session, token, "verify")
    if account is None:
        return None
    if account.email_verified_at is None:
        account.email_verified_at = datetime.now(UTC)
    session.commit()
    return account


def start_reset(session: DbSession, email: str) -> tuple[UserAccount, str] | None:
    """A reset link, or None when there is no such account.

    The caller answers the same either way. Whether an address has an account is
    not a stranger's business.
    """
    account = by_email(session, email)
    if account is None:
        return None
    secret = _issue(session, account, "reset", RESET_HOURS)
    session.commit()
    return account, secret


def finish_reset(session: DbSession, *, token: str, password: str) -> UserAccount | None:
    """Set a new password from a reset link, and verify the address with it.

    Somebody who can read that inbox owns the address, which is the same thing
    the verification link proves.
    """
    account = _spend(session, token, "reset")
    if account is None:
        return None
    account.password_hash = hash_password(password)
    if account.email_verified_at is None:
        account.email_verified_at = datetime.now(UTC)
    session.commit()
    return account
