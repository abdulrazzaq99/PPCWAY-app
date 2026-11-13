"""What the PPCWay script reports from a merchant's website, and what came of it.

Three tables. `SiteKey` is the merchant's script: the public key in the tag and
their choices about it. `SiteVisit` is one visit to their site, with where it
came from. `SiteLead` is somebody getting in touch from it -- a form sent, a
phone number tapped, an email address clicked -- and, once the merchant says
so, whether it became a job and what the job was worth.

A lead holds what the person typed into the form, which is personal
information about somebody who never signed up to PPCWay. It is kept for
`site.jobs.KEEP_LEADS` and then deleted, and only the merchant's own business
can read it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


class SiteKey(Base):
    """One business's script: its public key, and what it is allowed to do.

    The key is not a secret. It sits in the page source of the merchant's
    website for anybody to read, and all it does is say which business an
    event belongs to. That is why nothing a key unlocks is readable, only
    writable, and why what it can write is limited (see `site.collect`).
    """

    __tablename__ = "site_key"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization.id"), unique=True, index=True
    )
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #: The last time the script reported anything, and from where: how the
    #: Website screen knows the script is installed and still working.
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_url: Mapped[str] = mapped_column(String(500), default="")
    #: Whether leads marked as jobs are sent to Google Ads. Off until somebody
    #: who may approve changes switches it on, because it creates a conversion
    #: action in their account and counts it towards bidding.
    send_jobs: Mapped[bool] = mapped_column(Boolean, default=False)
    #: The "Jobs from PPCWay leads" conversion action, once it exists.
    job_action: Mapped[str] = mapped_column(String(200), default="")
    #: Google Ads conversions the script fires itself, as Google's `send_to`
    #: ("AW-123456789/AbC-dEfGh"). Empty: the script fires nothing at Google.
    form_send_to: Mapped[str] = mapped_column(String(100), default="")
    call_send_to: Mapped[str] = mapped_column(String(100), default="")


class SiteVisit(Base):
    """One visit to the merchant's website, and where it came from."""

    __tablename__ = "site_visit"
    __table_args__ = (UniqueConstraint("organization_id", "visit", name="uq_site_visit_visit"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    #: Made up by the browser: random, and meaningless outside this table.
    visit: Mapped[str] = mapped_column(String(40))
    visitor: Mapped[str] = mapped_column(String(40), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    landing: Mapped[str] = mapped_column(String(500), default="")
    referrer: Mapped[str] = mapped_column(String(200), default="")
    #: One word for where it came from: google_ads, google, bing, facebook,
    #: instagram, email, referral, direct, other.
    source: Mapped[str] = mapped_column(String(20), default="direct")
    campaign: Mapped[str] = mapped_column(String(100), default="")
    #: Google's click ids. Whichever of the three the ad click carried.
    gclid: Mapped[str] = mapped_column(String(200), default="")
    gbraid: Mapped[str] = mapped_column(String(200), default="")
    wbraid: Mapped[str] = mapped_column(String(200), default="")
    device: Mapped[str] = mapped_column(String(10), default="")
    views: Mapped[int] = mapped_column(Integer, default=1)


class SiteLead(Base):
    """Somebody getting in touch from the website, and what became of it."""

    __tablename__ = "site_lead"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("site_visit.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    #: form, call or email.
    kind: Mapped[str] = mapped_column(String(10))
    page: Mapped[str] = mapped_column(String(500), default="")
    #: The form's own name or id, so two forms on one site can be told apart.
    form: Mapped[str] = mapped_column(String(100), default="")
    #: What was typed, as [label, value] pairs. Empty when the browser asked
    #: not to be tracked (Global Privacy Control).
    fields: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=list
    )
    #: Picked out of the fields, or the number or address that was tapped.
    name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    #: Copied from the visit, so a lead says where it came from after its
    #: visit is deleted and so a job can be sent to Google with its click.
    source: Mapped[str] = mapped_column(String(20), default="direct")
    campaign: Mapped[str] = mapped_column(String(100), default="")
    gclid: Mapped[str] = mapped_column(String(200), default="")
    gbraid: Mapped[str] = mapped_column(String(200), default="")
    wbraid: Mapped[str] = mapped_column(String(200), default="")
    #: When the ad was clicked, for Google's "a conversion cannot come before
    #: its click" and its 90-day window.
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: A hash of the sender's address and the business, for counting how many
    #: leads one sender makes in an hour. Never the address itself.
    sender: Mapped[str] = mapped_column(String(64), default="", index=True)
    #: new, job, not_job or spam.
    status: Mapped[str] = mapped_column(String(10), default="new")
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="")
    marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("account.id"), nullable=True)
    #: Sending a job to Google Ads: "" (not a job, or not sending), waiting,
    #: sent, failed, or no_click (nothing to send it with).
    upload: Mapped[str] = mapped_column(String(10), default="")
    upload_note: Mapped[str] = mapped_column(String(300), default="")
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
