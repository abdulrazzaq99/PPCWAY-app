"""The account as we last saw it, held in our own database.

Every screen reads Google live today, which costs a round trip to California on
each page and makes the two-second dashboard in the requirements impossible. So
the account is mirrored here: the campaigns, the ad groups, the keywords, the
ads, and a row of numbers per campaign per day.

Three things make this a mirror rather than a cache.

  The resource name is the identity. Google's own name for a thing, kept as the
  unique key, so a rename does not create a second row and a re-sync does not
  duplicate anything.

  The fingerprint is the version we last saw. A hash of the fields we track,
  compared on every sync: if it moves and PPCway did not move it, somebody
  changed that thing in Google Ads, and `ExternalChange` records it in plain
  words. Nothing we hold is silently overwritten without that record.

  Nothing is deleted. A campaign that disappears from Google's answer is marked
  gone rather than removed, because a mirror that forgets cannot be compared
  against yesterday.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base

#: Micros are Google's unit: a millionth of the account's currency.
MICRO = 1_000_000


def fingerprint(fields: dict[str, Any]) -> str:
    """The version of a thing, as a hash of the fields we track.

    Sorted and separator-fixed, so the same account read twice fingerprints the
    same and a change in a field we do not track is not reported as a change.
    """
    raw = json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class Mirrored:
    """What every mirrored thing carries, whatever kind of thing it is."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: Which advertising account this belongs to, as Google writes it.
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    #: Google's own name for the thing, such as `customers/123/campaigns/456`.
    resource_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    #: The fields we track, hashed. The version we last saw.
    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    #: Who last changed it: "google" for a change made in Google Ads, "ppcway"
    #: for one of ours. Everything is "google" until PPCway can write.
    source: Mapped[str] = mapped_column(String(10), default="google")
    #: The last sync that found it still there.
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #: The last sync that found it different.
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Set when Google stops returning it. The row stays, so yesterday can still
    #: be compared with today.
    gone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MirrorCampaign(Mirrored, Base):
    """A campaign, with the budget that is the thing most often changed."""

    __tablename__ = "ads_campaign"
    campaign_id: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="")
    channel: Mapped[str] = mapped_column(String(30), default="")
    bidding: Mapped[str] = mapped_column(String(40), default="")
    budget_micros: Mapped[int] = mapped_column(Integer, default=0)
    #: Google's own words, "yyyy-MM-dd HH:mm:ss" in the account's time zone. In
    #: v25 the date-only fields are gone, so this is a moment, not a day.
    starts_at: Mapped[str] = mapped_column(String(25), default="")
    ends_at: Mapped[str] = mapped_column(String(25), default="")

    @property
    def budget(self) -> float:
        return round(self.budget_micros / MICRO, 2)


class MirrorAdGroup(Mirrored, Base):
    __tablename__ = "ads_ad_group"
    ad_group_id: Mapped[str] = mapped_column(String(20), index=True)
    campaign_id: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="")
    cpc_bid_micros: Mapped[int] = mapped_column(Integer, default=0)


class MirrorKeyword(Mirrored, Base):
    """A keyword, positive or negative, with Google's own Quality Score."""

    __tablename__ = "ads_keyword"
    criterion_id: Mapped[str] = mapped_column(String(20), index=True)
    ad_group_id: Mapped[str] = mapped_column(String(20), index=True)
    campaign_id: Mapped[str] = mapped_column(String(20), index=True)
    text: Mapped[str] = mapped_column(String(255), default="")
    match_type: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="")
    negative: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    cpc_bid_micros: Mapped[int] = mapped_column(Integer, default=0)


class MirrorAd(Mirrored, Base):
    """An ad, with its headlines and what Google's policy review made of it."""

    __tablename__ = "ads_ad"
    ad_id: Mapped[str] = mapped_column(String(20), index=True)
    ad_group_id: Mapped[str] = mapped_column(String(20), index=True)
    campaign_id: Mapped[str] = mapped_column(String(20), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="")
    approval: Mapped[str] = mapped_column(String(30), default="")
    headlines: Mapped[list[str]] = mapped_column(JSON, default=list)
    descriptions: Mapped[list[str]] = mapped_column(JSON, default=list)
    final_urls: Mapped[list[str]] = mapped_column(JSON, default=list)


class CampaignDay(Base):
    """One campaign, one day: what it cost and what it brought back.

    The grain the dashboard needs. A month is thirty of these added up, "against
    the previous period" is sixty, and the sparkline on each row is this table
    and nothing else.

    `conversions` is Google's own total; `calls` and `forms` are the split, which
    has to be read by a second query because Google refuses to report the
    conversion category beside clicks, cost or impressions.
    """

    __tablename__ = "ads_campaign_day"
    __table_args__ = (UniqueConstraint("customer_id", "campaign_id", "day", name="one_row_a_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    campaign_id: Mapped[str] = mapped_column(String(20), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_value_micros: Mapped[int] = mapped_column(Integer, default=0)
    calls: Mapped[float] = mapped_column(Float, default=0.0)
    forms: Mapped[float] = mapped_column(Float, default=0.0)
    #: How much of the available auction this campaign actually appeared in, and
    #: where the rest went. Google reports these as a share between 0 and 1, and
    #: caps anything above 0.9 at 0.9 for competitive reasons -- so "90%" here
    #: means "90% or better" and no recommendation may read it as exact.
    #:
    #: These live on this table rather than in a mirror of their own because the
    #: grain is identical: one campaign, one day. A separate table would be a
    #: join for every screen that already reads this one, and two refresh paths
    #: that could disagree about the same afternoon.
    #:
    #: Null, not zero, when Google did not report them. A campaign that is not
    #: a Search campaign has no search impression share, and a day with no
    #: impressions has none either; zero would read as "you appeared in none of
    #: the auctions", which is a different and much more alarming claim.
    search_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: The share lost because the daily budget ran out. This is the number
    #: behind the only recommendation that asks a merchant to spend more, so it
    #: is kept separately from rank rather than rolled into one "lost" figure.
    lost_to_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: The share lost because the ad was not good enough or the bid too low.
    #: Spending more does not fix this one, and telling the two apart is the
    #: difference between useful advice and expensive advice.
    lost_to_rank: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: How often it was the very first result, which is what a merchant means
    #: when they ask why they cannot see themselves.
    top_share: Mapped[float | None] = mapped_column(Float, nullable=True)

    #: The last time this day was re-read. Yesterday's row is rewritten for three
    #: nights, because conversions arrive late.
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def cost(self) -> float:
        return round(self.cost_micros / MICRO, 2)

    @property
    def share_is_capped(self) -> bool:
        """Google reported 90% or better and will not say which.

        A screen that prints "90%" from a capped figure is stating something
        Google refused to state. Anything reading `search_share` for a
        merchant has to check this first.
        """
        return self.search_share is not None and self.search_share >= 0.9


class SyncRun(Base):
    """One pass over one account, and what it found.

    Kept rather than logged, for three reasons: the dashboard says when it last
    looked, the first sync has something to show while it runs, and the
    requirements' phase-1 gate is seven days of these with nothing wrong in them.
    """

    __tablename__ = "ads_sync_run"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    #: "structure", "today", "backfill" or "first".
    kind: Mapped[str] = mapped_column(String(20), default="structure")
    #: "running", "done" or "failed".
    status: Mapped[str] = mapped_column(String(10), default="running", index=True)
    #: What it is doing now, in the words the waiting screen shows.
    stage: Mapped[str] = mapped_column(String(60), default="")
    #: Counts by kind of thing, for the screen and for the gate.
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    #: Why it failed, in Google's words made plain.
    trouble: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalChange(Base):
    """Something that changed in Google Ads, not here.

    The requirements ask that a change made directly in Google Ads is noticed,
    recorded as theirs, and not silently overwritten. This is that record. It is
    also what stops PPCway from later proposing a change somebody has already
    made by hand.
    """

    __tablename__ = "ads_external_change"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    #: "campaign", "ad_group", "keyword" or "ad".
    kind: Mapped[str] = mapped_column(String(20))
    resource_name: Mapped[str] = mapped_column(String(255), index=True)
    #: Which campaign it happened in, so a campaign can show its own history
    #: without matching resource names against everything we hold.
    campaign_id: Mapped[str] = mapped_column(String(20), default="", index=True)
    #: What the thing is called, so the record reads without a second lookup.
    label: Mapped[str] = mapped_column(String(255), default="")
    #: One line a person can read: "Daily budget raised from $5.00 to $12.00".
    summary: Mapped[str] = mapped_column(Text, default="")
    before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    noticed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SearchTermDay(Base):
    """What somebody actually typed, per day, and what it cost.

    Not the same thing as a keyword. A keyword is what the merchant bid on; a
    search term is what a person really searched for, and the gap between the
    two is where most wasted money in a small account lives -- a plumber
    bidding broadly on "boiler repair" paying for "boiler repair apprenticeship
    salary". Rule R1, the only change the client will let run unattended, reads
    nothing but this table.

    Kept per day rather than summed over a window, for the same reason
    `CampaignDay` is: a rule asking "thirty days of this" and a rule asking
    "seven" must not need two tables, and the freshness guardrail needs to know
    *when* a figure was true rather than only what it was.

    `status` is why this is not merely a metrics table. Google says whether a
    term is already a keyword, already excluded, or neither, and a rule that
    proposes excluding something already excluded is a rule the merchant stops
    trusting on the second day.
    """

    __tablename__ = "ads_search_term_day"
    __table_args__ = (
        UniqueConstraint("customer_id", "ad_group_id", "term_hash", "day", name="one_term_a_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    campaign_id: Mapped[str] = mapped_column(String(20), index=True, default="")
    ad_group_id: Mapped[str] = mapped_column(String(20), index=True, default="")
    day: Mapped[date] = mapped_column(Date, index=True)

    #: What was typed. Long: people type sentences, and Google does not
    #: truncate them, so neither does this.
    term: Mapped[str] = mapped_column(String(1000))
    #: The term, hashed, because it is part of the uniqueness of a row and a
    #: thousand-character column cannot be indexed on either Postgres or MySQL.
    #: Set from `term` by `term_key`, never written by hand.
    term_hash: Mapped[str] = mapped_column(String(64), index=True)
    #: Google's own word: "ADDED", "EXCLUDED", "ADDED_EXCLUDED", "NONE", or
    #: "UNKNOWN" where it would not say. Kept as Google writes it rather than
    #: mapped to a boolean, because "added and also excluded" is a real state
    #: and a boolean cannot hold it.
    status: Mapped[str] = mapped_column(String(20), default="")
    #: The keyword that matched it, where Google reported one.
    matched_keyword: Mapped[str] = mapped_column(String(255), default="")

    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_value_micros: Mapped[int] = mapped_column(Integer, default=0)

    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def cost(self) -> float:
        return round(self.cost_micros / MICRO, 2)

    @property
    def already_handled(self) -> bool:
        """Already a keyword, or already excluded. Nothing to propose here."""
        return self.status in {"ADDED", "EXCLUDED", "ADDED_EXCLUDED"}


class KeywordDay(Base):
    """One keyword, one day: what it cost and what it brought back.

    The grain the guardrails need. "Minimum data to call a loser: 1.5 times the
    target cost per lead in spend, or 100 clicks" is a question about one
    keyword over a window, and answering it from the structure mirror alone is
    impossible -- that holds what a keyword *is*, not what it did.

    Quality Score is deliberately not here. It lives on `MirrorKeyword`,
    because Google reports it as a current property of the keyword rather than
    as a daily metric, and copying it onto every day's row would invent a
    history Google never gave us.
    """

    __tablename__ = "ads_keyword_day"
    __table_args__ = (
        UniqueConstraint("customer_id", "criterion_id", "day", name="one_keyword_a_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    criterion_id: Mapped[str] = mapped_column(String(20), index=True)
    ad_group_id: Mapped[str] = mapped_column(String(20), index=True, default="")
    campaign_id: Mapped[str] = mapped_column(String(20), index=True, default="")
    day: Mapped[date] = mapped_column(Date, index=True)

    #: The words and the match type, copied here so a report reads without a
    #: second lookup and still reads after the keyword has been removed.
    text: Mapped[str] = mapped_column(String(255), default="")
    match_type: Mapped[str] = mapped_column(String(20), default="")

    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_value_micros: Mapped[int] = mapped_column(Integer, default=0)

    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def cost(self) -> float:
        return round(self.cost_micros / MICRO, 2)


def term_key(term: str) -> str:
    """The hash that makes a search term's row unique.

    Case-folded and space-collapsed first: Google reports search terms already
    lowercased, but "boiler  repair" and "boiler repair" arriving on different
    days as different rows would split one term's spend in two and put it under
    whichever rule threshold it was closest to.
    """
    tidy = " ".join(term.lower().split())
    return hashlib.sha256(tidy.encode()).hexdigest()
