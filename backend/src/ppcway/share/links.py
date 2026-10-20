"""Making a login-free link, and opening one.

The rules are in one place because they are the only thing standing between a
shared report and the open internet: the right kind, not expired, not revoked.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.share.models import ShareLink

log = logging.getLogger(__name__)

#: How long a shared link lives unless somebody says otherwise. Long enough for
#: a web person to get round to it, short enough that a forwarded email does not
#: become a permanent window into somebody's advertising.
FOR_DAYS = 14

#: 24 bytes of randomness, url-safe. Guessing one is not a strategy.
SIZE = 24


def fingerprint(token: str) -> str:
    """What is stored. The token itself is never kept."""
    return hashlib.sha256(token.encode()).hexdigest()


def make_link(
    session: Session,
    *,
    kind: str,
    subject: str,
    days: int = FOR_DAYS,
    organization_id: uuid.UUID | None = None,
    made_by: uuid.UUID | None = None,
    sent_to: str = "",
    now: datetime | None = None,
) -> tuple[ShareLink, str]:
    """A new link, and the one time its token is readable."""
    at = now or datetime.now(UTC)
    token = secrets.token_urlsafe(SIZE)
    link = ShareLink(
        token_hash=fingerprint(token),
        kind=kind,
        subject=subject,
        organization_id=organization_id,
        made_by=made_by,
        sent_to=sent_to,
        expires_at=at + timedelta(days=days),
    )
    session.add(link)
    session.commit()
    return link, token


def open_link(
    session: Session,
    token: str,
    *,
    kind: str,
    now: datetime | None = None,
) -> ShareLink | None:
    """The link this token opens, or nothing — never a reason why.

    A caller gets None whether the token is wrong, expired, revoked or for
    another kind of thing entirely. Telling somebody which of those it was is
    telling them something about a link they do not hold.
    """
    at = now or datetime.now(UTC)
    link = session.scalars(
        select(ShareLink).where(ShareLink.token_hash == fingerprint(token))
    ).first()
    if link is None or link.kind != kind or link.revoked_at is not None:
        return None
    # SQLite gives back what it was given, without the zone it was given with.
    expires = link.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= at:
        return None
    link.opened += 1
    link.last_opened_at = at
    session.commit()
    return link


def revoke(session: Session, link: ShareLink, *, now: datetime | None = None) -> None:
    """Stop a link working, without deleting the record that it existed."""
    link.revoked_at = now or datetime.now(UTC)
    session.commit()
