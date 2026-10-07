"""A merchant's connected Google Ads account, and the trip to Google that made it."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


class AdsConnection(Base):
    """One account's permission to read their Google Ads, encrypted at rest.

    Named `ads_connection`: the proof of concept's `google_ads_link` shares this
    database and means something else, a link between a manager and a client.
    """

    __tablename__ = "ads_connection"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"), index=True)
    #: The refresh token, encrypted. Never read anywhere but the one door.
    ciphertext: Mapped[str] = mapped_column(Text)
    #: Which advertising account they chose, once they have chosen.
    customer_id: Mapped[str] = mapped_column(String(20), default="")
    customer_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #: Set when they disconnect. The row stays as a record that it happened.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConsentTrip(Base):
    """A trip to Google that has not come back yet.

    The state is held here rather than in a cookie so a reply carrying somebody
    else's state cannot be made to look like this browser's.
    """

    __tablename__ = "ads_consent_trip"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    state: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
