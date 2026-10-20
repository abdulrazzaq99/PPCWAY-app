"""A link that needs no login, and dies on its own.

Two things in PPCway have to reach somebody who will never have an account: the
report an owner wants to send their accountant, and the fix list an owner wants
to send whoever built their website. Both are links, and a link that works
forever is a leak waiting to happen.

So: the token is a secret that is never stored — only its hash, the same way a
password is kept — the link expires on a date, it can be revoked, and every
opening is counted so an owner can see it was used.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


class ShareLink(Base):
    """One login-free link to one thing, for a while."""

    __tablename__ = "share_link"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: SHA-256 of the token. The token itself is handed over once and never kept,
    #: so a copy of this table is not a set of working links.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    #: "report" or "fixes". A token for one kind cannot open the other.
    kind: Mapped[str] = mapped_column(String(20), index=True)
    #: What it points at: the advertising account for a report, the audit run
    #: for a fix list.
    subject: Mapped[str] = mapped_column(String(100), index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization.id"), index=True, nullable=True
    )
    made_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("account.id"), index=True, nullable=True
    )
    #: Who it was sent to, when it was sent by email rather than copied.
    sent_to: Mapped[str] = mapped_column(String(320), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: How many times it has been opened, so an owner can see it was used.
    opened: Mapped[int] = mapped_column(Integer, default=0)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
