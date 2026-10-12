"""The account and the session. Both are ours; Google only says who the person is."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


class UserAccount(Base):
    """One person, known by the Google account they signed in with.

    Named `account`, not `user_account`: the proof of concept's own tables share
    this database, and `user_account` is one of them.
    """

    __tablename__ = "account"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: Google's own id for the person, when they came that way. Stable even if
    #: they change their address. Empty for somebody who signed up with a password.
    google_sub: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    #: Argon2, or empty for somebody who only ever signs in with Google.
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    #: When they proved the address is theirs. Google's sign-in proves it for us.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    picture: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LinkToken(Base):
    """A one-time link sent by email: confirming an address, or resetting a password.

    Held as a hash, like a session. A copy of this table is a list of expired
    opportunities, not a set of keys.
    """

    __tablename__ = "account_link"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"), index=True)
    #: "verify" or "reset".
    purpose: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    """A signed-in browser. The cookie holds the token; this holds only its hash."""

    __tablename__ = "account_session"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    #: Set when they sign out, so the row stays as a record of the session.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: The last time this cookie was presented. A session in daily use rolls its
    #: expiry forward; one left alone for a month stops working, as it should.
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
