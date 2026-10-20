"""What has already been sent, so nothing is sent twice.

The weekly post goes out on a clock, and a clock gets called twice: a scheduler
retries, a deploy overlaps, somebody runs the command by hand to check. One row
a week per account is what makes that harmless.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


class WeeklyPost(Base):
    """One week's summary, to one person, sent or attempted."""

    __tablename__ = "mail_weekly_post"
    __table_args__ = (UniqueConstraint("account_id", "week_start", name="one_post_a_week"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"), index=True)
    #: Which advertising account it was about.
    customer_id: Mapped[str] = mapped_column(String(20), default="", index=True)
    #: The Monday of the week it was sent in, which is what makes it one a week.
    week_start: Mapped[date] = mapped_column(Date, index=True)
    to_address: Mapped[str] = mapped_column(String(320), default="")
    #: "sent" or "failed". A failed row is tried again; a sent one never is.
    status: Mapped[str] = mapped_column(String(10), default="sent")
    trouble: Mapped[str] = mapped_column(Text, default="")
    #: The subject line, kept so support can see what somebody was told.
    subject: Mapped[str] = mapped_column(String(255), default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
