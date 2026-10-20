"""The dashboard's numbers, read from our own mirror.

`summary.py` asks Google the same questions live. That costs four round trips to
California on every page load, which is why the requirements' two-second
dashboard was not reachable, and it cannot afford the one question the client's
design asks on every screen: *and how does that compare with before?* Doubling
a live read to answer it doubles the wait.

Reading the mirror instead makes the comparison free. Everything here is one
pass over `ads_campaign_day`, bucketed in Python, plus two small reads for the
things that need somebody's attention.

Two decisions worth knowing:

  The window ends yesterday. "Last thirty days" means the thirty days up to and
  including yesterday, which is what Google's own `LAST_30_DAYS` means, so a
  merchant holding our screen beside the Google Ads interface sees one number
  and not two. Today is still mirrored hourly; it is simply not in that sum.

  A campaign that has gone from Google still counts. It spent real money while
  it ran, and a total that quietly drops it cannot be reconciled with a bank
  statement. It is listed, marked gone, and left in the sum.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import (
    MICRO,
    CampaignDay,
    ExternalChange,
    MirrorAd,
    MirrorAdGroup,
    MirrorCampaign,
    MirrorKeyword,
    SyncRun,
)

log = logging.getLogger(__name__)

#: Below this, a campaign that has brought nothing back is not worth a line on
#: the dashboard: a few dollars of a new campaign finding its feet is normal.
WORTH_SAYING = 20.0

#: An average month, for turning daily budgets into the monthly figure a
#: merchant actually thinks in.
MONTH = 30.4

#: Google's approval words that mean the ad is running. Everything else means a
#: person has to do something before it will show.
RUNNING = {"APPROVED", "APPROVED_LIMITED", ""}

#: How far back the activity list and the "somebody changed this" line look.
RECENTLY = 7


@dataclass
class Day:
    """One day of one thing: what it cost, and what it brought back."""

    date: str
    calls: float = 0.0
    forms: float = 0.0
    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0

    @property
    def leads(self) -> float:
        return round(self.calls + self.forms, 2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "calls": round(self.calls, 2),
            "forms": round(self.forms, 2),
            "leads": self.leads,
            "cost": round(self.cost, 2),
            "clicks": self.clicks,
            "impressions": self.impressions,
        }


@dataclass
class Row:
    """One campaign over the window, with its own days for the sparkline."""

    campaign_id: str
    name: str = ""
    status: str = ""
    serving: str = ""
    budget: float = 0.0
    leads: float = 0.0
    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0
    #: Google's own "yyyy-MM-dd HH:mm:ss", which is what the Learning chip counts from.
    starts_at: str = ""
    gone: bool = False
    days: list[Day] = field(default_factory=list)

    @property
    def cost_per_lead(self) -> float:
        return round(self.cost / self.leads, 2) if self.leads else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "status": self.status,
            "serving": self.serving or self.status,
            "budget": round(self.budget, 2),
            "leads": round(self.leads, 2),
            "cost": round(self.cost, 2),
            "clicks": self.clicks,
            "impressions": self.impressions,
            "cost_per_lead": self.cost_per_lead,
            "starts_at": self.starts_at,
            "gone": self.gone,
            "days": [d.as_dict() for d in self.days],
        }


@dataclass
class Need:
    """One thing on the dashboard's "needs you" list, in plain words."""

    kind: str
    label: str
    what: str
    campaign_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "what": self.what,
            "campaign_id": self.campaign_id,
        }


@dataclass
class Change:
    """Something somebody changed in Google Ads, for the activity list."""

    kind: str
    label: str
    summary: str
    when: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "summary": self.summary,
            "when": self.when.isoformat() if self.when else None,
        }


@dataclass
class Held:
    """One account over one window, as the home screen needs it."""

    read: bool = False
    trouble: str = ""
    customer_id: str = ""
    currency: str = ""
    days: int = 30
    #: The window these figures cover, as dates. On the screen rather than
    #: computed there: a header that says "to today" over a window that ends
    #: yesterday is a small lie that costs somebody an afternoon.
    starts_on: str = ""
    ends_on: str = ""
    leads: float = 0.0
    calls: float = 0.0
    forms: float = 0.0
    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0
    #: The window immediately before this one, which is what "better or worse"
    #: on every figure is measured against.
    leads_before: float = 0.0
    cost_before: float = 0.0
    cost_per_lead_before: float = 0.0
    #: This calendar month, including today, which is what a budget is judged against.
    month_cost: float = 0.0
    month_day: int = 0
    month_days: int = 31
    monthly_budget: float = 0.0
    series: list[Day] = field(default_factory=list)
    campaigns: list[Row] = field(default_factory=list)
    needs: list[Need] = field(default_factory=list)
    activity: list[Change] = field(default_factory=list)
    #: When the last finished sync finished, and how many days we hold. Both are
    #: on the screen, because a number from our database has to say how old it is.
    looked_at: datetime | None = None
    held_days: int = 0

    @property
    def cost_per_lead(self) -> float:
        return round(self.cost / self.leads, 2) if self.leads else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "read": self.read,
            "trouble": self.trouble,
            "customer_id": self.customer_id,
            "currency": self.currency,
            "days": self.days,
            "starts_on": self.starts_on,
            "ends_on": self.ends_on,
            "leads": round(self.leads, 2),
            "calls": round(self.calls, 2),
            "forms": round(self.forms, 2),
            "cost": round(self.cost, 2),
            "clicks": self.clicks,
            "impressions": self.impressions,
            "cost_per_lead": self.cost_per_lead,
            "leads_before": round(self.leads_before, 2),
            "cost_before": round(self.cost_before, 2),
            "cost_per_lead_before": self.cost_per_lead_before,
            "month_cost": round(self.month_cost, 2),
            "month_day": self.month_day,
            "month_days": self.month_days,
            "monthly_budget": round(self.monthly_budget, 2),
            "series": [d.as_dict() for d in self.series],
            "campaigns": [c.as_dict() for c in self.campaigns],
            "needs": [n.as_dict() for n in self.needs],
            "activity": [c.as_dict() for c in self.activity],
            "looked_at": self.looked_at.isoformat() if self.looked_at else None,
            "held_days": self.held_days,
            #: So a screen can say where the figure came from, and so the
            #: difference from a live read is never invisible.
            "source": "mirror",
        }


def plain_money(amount: float, currency: str = "") -> str:
    """Money as the account's own country writes it.

    Here rather than in a screen or a letter, because the same sentence is read
    on the dashboard and in the Monday email, and the two must not disagree
    about what a dollar looks like.
    """
    if not currency or currency in {"CAD", "USD"}:
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def _month_length(day: date) -> int:
    """How many days this month has, found by stepping into the next and back."""
    next_month = day.replace(day=28) + timedelta(days=4)
    return (next_month - timedelta(days=next_month.day)).day


def account_numbers(
    session: Session,
    customer_id: str,
    *,
    days: int = 30,
    currency: str = "",
    today: date | None = None,
) -> Held:
    """Add up what the mirror holds for one account over one window."""
    now = today or datetime.now(UTC).date()
    last = now - timedelta(days=1)
    start = now - timedelta(days=days)
    was_start = start - timedelta(days=days)
    month_start = now.replace(day=1)

    held = Held(
        customer_id=customer_id,
        currency=currency,
        days=days,
        starts_on=start.isoformat(),
        ends_on=last.isoformat(),
        month_day=now.day,
        month_days=_month_length(now),
    )

    campaigns = list(
        session.scalars(select(MirrorCampaign).where(MirrorCampaign.customer_id == customer_id))
    )
    held.held_days = (
        session.scalar(
            select(func.count(func.distinct(CampaignDay.day))).where(
                CampaignDay.customer_id == customer_id
            )
        )
        or 0
    )
    if not campaigns and not held.held_days:
        held.trouble = "We have not read this account yet."
        return held

    # One pass over every day either window or this month can need.
    from_day = min(was_start, month_start)
    rows = list(
        session.scalars(
            select(CampaignDay)
            .where(
                CampaignDay.customer_id == customer_id,
                CampaignDay.day >= from_day,
                CampaignDay.day <= now,
            )
            .order_by(CampaignDay.day)
        )
    )

    whole: dict[str, Day] = {}
    per_campaign: dict[str, Row] = {}
    for row in rows:
        if month_start <= row.day <= now:
            held.month_cost += row.cost
        if not (start <= row.day <= last):
            if was_start <= row.day < start:
                held.leads_before += row.calls + row.forms
                held.cost_before += row.cost
            continue
        stamp = row.day.isoformat()
        day = whole.setdefault(stamp, Day(date=stamp))
        day.calls += row.calls
        day.forms += row.forms
        day.cost += row.cost
        day.clicks += row.clicks
        day.impressions += row.impressions
        mine = per_campaign.setdefault(row.campaign_id, Row(campaign_id=row.campaign_id))
        mine.leads += row.calls + row.forms
        mine.cost += row.cost
        mine.clicks += row.clicks
        mine.impressions += row.impressions
        mine.days.append(
            Day(
                date=stamp,
                calls=row.calls,
                forms=row.forms,
                cost=row.cost,
                clicks=row.clicks,
                impressions=row.impressions,
            )
        )

    held.series = [whole[k] for k in sorted(whole)]
    held.calls = round(sum(d.calls for d in held.series), 2)
    held.forms = round(sum(d.forms for d in held.series), 2)
    held.leads = round(held.calls + held.forms, 2)
    held.cost = round(sum(d.cost for d in held.series), 2)
    held.clicks = sum(d.clicks for d in held.series)
    held.impressions = sum(d.impressions for d in held.series)
    held.cost_before = round(held.cost_before, 2)
    held.leads_before = round(held.leads_before, 2)
    held.cost_per_lead_before = (
        round(held.cost_before / held.leads_before, 2) if held.leads_before else 0.0
    )
    held.month_cost = round(held.month_cost, 2)

    # The campaign the numbers belong to, so a row can carry its name and budget.
    known = {c.campaign_id: c for c in campaigns}
    for campaign_id, shown in per_campaign.items():
        it = known.get(campaign_id)
        if it is None:
            # Numbers for a campaign we have never read the shape of. It still
            # spent the money, so it is shown by its id rather than dropped.
            shown.name = f"Campaign {campaign_id}"
            continue
        shown.name = it.name
        shown.status = it.status
        shown.serving = it.status
        shown.budget = it.budget
        shown.starts_at = it.starts_at
        shown.gone = it.gone_at is not None

    # An enabled campaign with nothing in the window is still on the screen: a
    # campaign that started yesterday is the one most likely to need an eye.
    for it in campaigns:
        if it.campaign_id in per_campaign or it.gone_at is not None or it.status != "ENABLED":
            continue
        per_campaign[it.campaign_id] = Row(
            campaign_id=it.campaign_id,
            name=it.name,
            status=it.status,
            serving=it.status,
            budget=it.budget,
            starts_at=it.starts_at,
        )

    held.campaigns = sorted(per_campaign.values(), key=lambda r: (-r.cost, r.name))
    held.monthly_budget = round(
        sum(c.budget for c in campaigns if c.status == "ENABLED" and c.gone_at is None) * MONTH, 2
    )

    held.needs = _needs(session, customer_id, held, campaigns)
    held.activity = [
        Change(kind=c.kind, label=c.label, summary=c.summary, when=c.noticed_at)
        for c in session.scalars(
            select(ExternalChange)
            .where(ExternalChange.customer_id == customer_id)
            .order_by(ExternalChange.noticed_at.desc())
            .limit(8)
        )
    ]
    held.looked_at = session.scalar(
        select(SyncRun.finished_at)
        .where(SyncRun.customer_id == customer_id, SyncRun.status == "done")
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )
    held.read = True
    return held


def _needs(
    session: Session,
    customer_id: str,
    held: Held,
    campaigns: list[MirrorCampaign],
) -> list[Need]:
    """What wants a person, in the order a person would care about it."""
    needs: list[Need] = []

    for row in held.campaigns:
        if row.gone or row.leads or row.cost < WORTH_SAYING:
            continue
        needs.append(
            Need(
                kind="spend_no_leads",
                label=row.name,
                what=(
                    f"Spent {plain_money(row.cost, held.currency)} over {held.days} days "
                    "and counted no calls or forms."
                ),
                campaign_id=row.campaign_id,
            )
        )

    gone = {c.campaign_id for c in campaigns if c.gone_at is not None}
    named = {c.campaign_id: c.name for c in campaigns}
    refused = session.scalars(
        select(MirrorAd).where(
            MirrorAd.customer_id == customer_id,
            MirrorAd.gone_at.is_(None),
            MirrorAd.approval.not_in(RUNNING),
        )
    )
    for ad in refused:
        if ad.campaign_id in gone:
            continue
        headline = next((h for h in (ad.headlines or []) if h), f"Ad {ad.ad_id}")
        where = named.get(ad.campaign_id, f"campaign {ad.campaign_id}")
        needs.append(
            Need(
                kind="ad_refused",
                label=headline,
                what=f"Google will not show this ad in {where} until it is fixed.",
                campaign_id=ad.campaign_id,
            )
        )

    since = datetime.now(UTC) - timedelta(days=RECENTLY)
    hands = (
        session.scalar(
            select(func.count())
            .select_from(ExternalChange)
            .where(
                ExternalChange.customer_id == customer_id,
                ExternalChange.noticed_at >= since,
            )
        )
        or 0
    )
    if hands:
        thing = "change" if hands == 1 else "changes"
        needs.append(
            Need(
                kind="changed_in_google",
                label="Changed in Google Ads",
                what=(
                    f"{hands} {thing} {'was' if hands == 1 else 'were'} made directly in Google "
                    f"Ads in the last {RECENTLY} days. Nothing of ours overwrote them."
                ),
            )
        )
    return needs


@dataclass
class CampaignHeld:
    """One campaign, as its five tabs need it, read from the mirror.

    The numbers, the day-by-day trend and the comparison with the period before
    are ours. So are the keywords, the ads and the change history. What is not
    ours yet is the per-keyword and per-ad performance and the search terms:
    those are Google's own reporting, read live and merged on top of this, and
    the page says so when they cannot be read rather than showing a zero.
    """

    read: bool = False
    trouble: str = ""
    campaign_id: str = ""
    name: str = ""
    status: str = ""
    currency: str = ""
    days: int = 30
    budget: float = 0.0
    starts_at: str = ""
    gone: bool = False
    leads: float = 0.0
    calls: float = 0.0
    forms: float = 0.0
    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0
    leads_before: float = 0.0
    cost_before: float = 0.0
    cost_per_lead_before: float = 0.0
    series: list[Day] = field(default_factory=list)
    keywords: list[dict[str, Any]] = field(default_factory=list)
    ads: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    history: list[Change] = field(default_factory=list)
    #: Google's live reporting, merged on by the endpoint when it answers.
    terms: list[dict[str, Any]] = field(default_factory=list)
    lost_to_budget: float = 0.0
    lost_to_rank: float = 0.0
    impression_share: float = 0.0
    #: False when Google's own reporting could not be read, so the tabs that
    #: need it can say that instead of showing nothing and implying zero.
    metrics_read: bool = False

    @property
    def cost_per_lead(self) -> float:
        return round(self.cost / self.leads, 2) if self.leads else 0.0

    @property
    def lead_rate(self) -> float:
        """Clicks that became an enquiry, as a percentage."""
        return round((self.leads / self.clicks) * 100, 1) if self.clicks else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "read": self.read,
            "trouble": self.trouble,
            "campaign_id": self.campaign_id,
            "name": self.name,
            "status": self.status,
            "currency": self.currency,
            "days": self.days,
            "budget": round(self.budget, 2),
            "starts_at": self.starts_at,
            "gone": self.gone,
            "leads": round(self.leads, 2),
            "calls": round(self.calls, 2),
            "forms": round(self.forms, 2),
            "cost": round(self.cost, 2),
            "clicks": self.clicks,
            "impressions": self.impressions,
            "cost_per_lead": self.cost_per_lead,
            "lead_rate": self.lead_rate,
            "leads_before": round(self.leads_before, 2),
            "cost_before": round(self.cost_before, 2),
            "cost_per_lead_before": self.cost_per_lead_before,
            "lost_to_budget": self.lost_to_budget,
            "lost_to_rank": self.lost_to_rank,
            "impression_share": self.impression_share,
            "series": [d.as_dict() for d in self.series],
            "keywords": self.keywords,
            "ads": self.ads,
            "groups": self.groups,
            "terms": self.terms,
            "history": [c.as_dict() for c in self.history],
            "metrics_read": self.metrics_read,
            "source": "mirror",
        }


def campaign_numbers(
    session: Session,
    customer_id: str,
    campaign_id: str,
    *,
    days: int = 30,
    currency: str = "",
    today: date | None = None,
) -> CampaignHeld:
    """One campaign out of the mirror: its numbers, its parts and its history."""
    now = today or datetime.now(UTC).date()
    last = now - timedelta(days=1)
    start = now - timedelta(days=days)
    was_start = start - timedelta(days=days)

    held = CampaignHeld(campaign_id=campaign_id, currency=currency, days=days)
    campaign = session.scalars(
        select(MirrorCampaign).where(
            MirrorCampaign.customer_id == customer_id,
            MirrorCampaign.campaign_id == campaign_id,
        )
    ).first()
    if campaign is None:
        held.trouble = "We have not read that campaign yet."
        return held

    held.name = campaign.name
    held.status = campaign.status
    held.budget = campaign.budget
    held.starts_at = campaign.starts_at
    held.gone = campaign.gone_at is not None

    rows = session.scalars(
        select(CampaignDay)
        .where(
            CampaignDay.customer_id == customer_id,
            CampaignDay.campaign_id == campaign_id,
            CampaignDay.day >= was_start,
            CampaignDay.day <= last,
        )
        .order_by(CampaignDay.day)
    )
    for row in rows:
        if was_start <= row.day < start:
            held.leads_before += row.calls + row.forms
            held.cost_before += row.cost
            continue
        held.series.append(
            Day(
                date=row.day.isoformat(),
                calls=row.calls,
                forms=row.forms,
                cost=row.cost,
                clicks=row.clicks,
                impressions=row.impressions,
            )
        )
    held.calls = round(sum(d.calls for d in held.series), 2)
    held.forms = round(sum(d.forms for d in held.series), 2)
    held.leads = round(held.calls + held.forms, 2)
    held.cost = round(sum(d.cost for d in held.series), 2)
    held.clicks = sum(d.clicks for d in held.series)
    held.impressions = sum(d.impressions for d in held.series)
    held.leads_before = round(held.leads_before, 2)
    held.cost_before = round(held.cost_before, 2)
    held.cost_per_lead_before = (
        round(held.cost_before / held.leads_before, 2) if held.leads_before else 0.0
    )

    groups = {
        row.ad_group_id: row
        for row in session.scalars(
            select(MirrorAdGroup).where(
                MirrorAdGroup.customer_id == customer_id,
                MirrorAdGroup.campaign_id == campaign_id,
            )
        )
    }
    held.groups = [
        {
            "ad_group_id": row.ad_group_id,
            "name": row.name,
            "status": row.status,
            "bid": round(row.cpc_bid_micros / MICRO, 2),
            "gone": row.gone_at is not None,
        }
        for row in sorted(groups.values(), key=lambda g: g.name)
    ]

    keywords = session.scalars(
        select(MirrorKeyword).where(
            MirrorKeyword.customer_id == customer_id,
            MirrorKeyword.campaign_id == campaign_id,
            MirrorKeyword.gone_at.is_(None),
        )
    )
    held.keywords = [
        {
            "keyword": row.text,
            "match": row.match_type.title() if row.match_type else "",
            "status": row.status,
            "negative": row.negative,
            "quality_score": row.quality_score,
            "bid": round(row.cpc_bid_micros / MICRO, 2),
            "ad_group": groups[row.ad_group_id].name if row.ad_group_id in groups else "",
            # Google's own reporting fills these in; the mirror does not hold them.
            "clicks": 0,
            "leads": 0.0,
            "cost": 0.0,
            "cost_per_lead": 0.0,
        }
        for row in sorted(keywords, key=lambda k: (k.negative, k.text))
    ]

    ads = session.scalars(
        select(MirrorAd).where(
            MirrorAd.customer_id == customer_id,
            MirrorAd.campaign_id == campaign_id,
            MirrorAd.gone_at.is_(None),
        )
    )
    held.ads = [
        {
            "ad_id": row.ad_id,
            "ad_group": groups[row.ad_group_id].name if row.ad_group_id in groups else "",
            "headlines": [h for h in (row.headlines or []) if h],
            "descriptions": [d for d in (row.descriptions or []) if d],
            "final_urls": [u for u in (row.final_urls or []) if u],
            "approval": row.approval,
            "status": row.status,
            "impressions": 0,
            "clicks": 0,
            "click_rate": 0.0,
        }
        for row in ads
    ]

    held.history = [
        Change(kind=c.kind, label=c.label, summary=c.summary, when=c.noticed_at)
        for c in session.scalars(
            select(ExternalChange)
            .where(
                ExternalChange.customer_id == customer_id,
                ExternalChange.campaign_id == campaign_id,
            )
            .order_by(ExternalChange.noticed_at.desc())
            .limit(50)
        )
    ]
    held.read = True
    return held


def merge_live(held: CampaignHeld, live: dict[str, Any]) -> CampaignHeld:
    """Lay Google's own reporting over what we hold.

    The mirror knows what a campaign is made of; Google knows what each part of
    it did. The two are matched on what a person sees — the keyword and its
    match type, the ad group and the ad's headlines — because Google's reporting
    views do not return the resource names the mirror is keyed on.

    Nothing is overwritten by a refusal. If Google will not answer, the page
    keeps the campaign's own numbers and the tabs that need Google's reporting
    say they could not be read, which is worth more than a zero.
    """
    if not live.get("read"):
        return held

    held.metrics_read = True
    held.terms = list(live.get("terms") or [])
    held.lost_to_budget = float(live.get("lost_to_budget") or 0)
    held.lost_to_rank = float(live.get("lost_to_rank") or 0)
    held.impression_share = float(live.get("impression_share") or 0)
    held.currency = held.currency or str(live.get("currency") or "")

    # The first sync may not have reached the day table yet. Google's totals are
    # better than zeros for the minute that lasts.
    if not held.series:
        held.leads = float(live.get("leads") or 0)
        held.cost = float(live.get("cost") or 0)
        held.clicks = int(live.get("clicks") or 0)
        held.impressions = int(live.get("impressions") or 0)

    did = {
        (str(word.get("keyword", "")).lower(), str(word.get("match", ""))): word
        for word in live.get("keywords") or []
    }
    for word in held.keywords:
        found = did.get((str(word["keyword"]).lower(), str(word["match"])))
        if found is None:
            continue
        word["clicks"] = found.get("clicks", 0)
        word["leads"] = found.get("leads", 0.0)
        word["cost"] = found.get("cost", 0.0)
        word["cost_per_lead"] = found.get("cost_per_lead", 0.0)
        # Google's quality score is fresher in its own reporting than in ours.
        word["quality_score"] = found.get("quality_score") or word["quality_score"]
    already = {(str(w["keyword"]).lower(), str(w["match"])) for w in held.keywords}
    for key, found in did.items():
        if key in already:
            continue
        # Reported by Google and not yet mirrored: a keyword added minutes ago.
        held.keywords.append(
            {
                "keyword": found.get("keyword", ""),
                "match": found.get("match", ""),
                "status": "",
                "negative": False,
                "quality_score": found.get("quality_score", 0),
                "bid": 0.0,
                "ad_group": "",
                "clicks": found.get("clicks", 0),
                "leads": found.get("leads", 0.0),
                "cost": found.get("cost", 0.0),
                "cost_per_lead": found.get("cost_per_lead", 0.0),
            }
        )
    held.keywords.sort(key=lambda w: (-float(w.get("cost") or 0), str(w.get("keyword", ""))))

    ran = {
        (str(ad.get("ad_group", "")), tuple(str(h) for h in (ad.get("headlines") or [])[:3])): ad
        for ad in live.get("ads") or []
    }
    for ad in held.ads:
        found = ran.get((str(ad["ad_group"]), tuple(str(h) for h in ad["headlines"][:3])))
        if found is None:
            continue
        ad["impressions"] = found.get("impressions", 0)
        ad["clicks"] = found.get("clicks", 0)
        ad["click_rate"] = found.get("click_rate", 0.0)
        ad["approval"] = found.get("approval") or ad["approval"]
    held.ads.sort(key=lambda a: -int(a.get("impressions") or 0))
    return held
