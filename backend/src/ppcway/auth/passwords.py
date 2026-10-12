"""Passwords: hashing them, checking them, and the one-time links beside them.

Argon2, with its defaults, because the people who break passwords for a living
recommend it and its cost can be raised as hardware gets faster without touching
anything that was already stored.

Nothing here is reversible. A stored hash cannot be turned back into a password,
and the one-time tokens are held the same way, so a copy of the database is not
a way into anybody's account.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from ppcway.auth.google import hash_session_token

_hasher = PasswordHasher()

#: Long enough to resist a guess, short enough that somebody will use it. Length
#: does more than punctuation, so the rule is length and nothing else.
SHORTEST = 10

#: How long the links in email work for. A verification can wait a couple of
#: days; a password reset should not sit in an inbox for a week.
VERIFY_HOURS = 48
RESET_HOURS = 2


class WeakPassword(ValueError):
    """Says what is wrong in words somebody can act on."""


def check_strength(password: str) -> None:
    """Refuse a password that is too short or obviously guessed."""
    if len(password) < SHORTEST:
        raise WeakPassword(f"Use at least {SHORTEST} characters. Length matters more than symbols.")
    if password.lower() in {
        "password12",
        "password123",
        "1234567890",
        "qwertyuiop",
        "letmein123",
    }:
        raise WeakPassword("That is one of the first passwords anybody tries.")


def hash_password(password: str) -> str:
    check_strength(password)
    return _hasher.hash(password)


def password_matches(stored: str, password: str) -> bool:
    """Whether the password fits the stored hash. False for anything odd."""
    if not stored:
        return False
    try:
        return _hasher.verify(stored, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(stored: str) -> bool:
    """Whether a stored hash was made with weaker settings than today's."""
    try:
        return _hasher.check_needs_rehash(stored)
    except InvalidHashError:
        return False


def new_link_token() -> tuple[str, str]:
    """A secret for an email link, and the hash to store. The secret is shown once."""
    secret = secrets.token_urlsafe(32)
    return secret, hash_session_token(secret)


def expiry(hours: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)
