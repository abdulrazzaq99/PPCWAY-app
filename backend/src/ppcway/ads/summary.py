"""The numbers the dashboard home is built from.

The handoff's home screen answers one question — "is it working, and what needs
me?" — in four figures and two charts: leads, cost per lead, spend against
budget, and the day-by-day split between calls and forms.

All of it comes from one account, read live. There is no local mirror yet, so
this is four queries rather than a cheap read of our own database; when the
mirror lands, this module is what it replaces.

A lead is a conversion, split by what Google calls it: a phone call or a form.
That split matters more than the total to somebody who answers the phone.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ppcway.ads.accounts import API, _headers, _plain, _why

log = logging.getLogger(__name__)

MICRO = 1_000_000

#: Google's categories for a conversion that is a phone call. Everything else
#: that counts as a lead is treated as a form.
CALL_KINDS = {"PHONE_CALL_LEAD", "CALL"}


@dataclass
class Day:
    date: str
    calls: float = 0.0
    forms: float = 0.0
    cost: float = 0.0

    @property
    def leads(self) -> float:
        return round(self.calls + self.forms, 2)


@dataclass
class CampaignRow:
    campaign_id: str
    name: str
    status: str
    leads: float
    cost: float
    budget: float
    #: Google's own word: ENABLED, PAUSED, REMOVED.
    serving: str = ""

    @property
    def cost_per_lead(self) -> float:
        return round(self.cost / self.leads, 2) if self.leads else 0.0


@dataclass
class Summary:
    """One account over one window, as the home screen needs it."""

    read: bool = False
    trouble: str = ""
    customer_id: str = ""
    currency: str = ""
    days: int = 30
    leads: float = 0.0
    calls: float = 0.0
    forms: float = 0.0
    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0
    #: The same window immediately before this one, for "is this a real change".
    leads_before: float = 0.0
    cost_per_lead_before: float = 0.0
    #: This calendar month, which is what a budget is judged against.
    month_cost: float = 0.0
    month_day: int = 0
    month_days: int = 31
    monthly_budget: float = 0.0
    series: list[Day] = field(default_factory=list)
    campaigns: list[CampaignRow] = field(default_factory=list)

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
            "leads": round(self.leads, 2),
            "calls": round(self.calls, 2),
            "forms": round(self.forms, 2),
            "cost": round(self.cost, 2),
            "clicks": self.clicks,
            "impressions": self.impressions,
            "cost_per_lead": self.cost_per_lead,
            "leads_before": round(self.leads_before, 2),
            "cost_per_lead_before": self.cost_per_lead_before,
            "month_cost": round(self.month_cost, 2),
            "month_day": self.month_day,
            "month_days": self.month_days,
            "monthly_budget": round(self.monthly_budget, 2),
            "series": [{**asdict(d), "leads": d.leads} for d in self.series],
            "campaigns": [{**asdict(c), "cost_per_lead": c.cost_per_lead} for c in self.campaigns],
        }


def _micros(value: Any) -> float:
    try:
        return round(int(value) / MICRO, 2)
    except (TypeError, ValueError):
        return 0.0


def _ask(
    customer_id: str,
    query: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None,
    api_version: str,
    client: httpx.Client,
) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    body: dict[str, Any] = {"query": query}
    for _ in range(10):
        reply = client.post(
            f"{API}/{api_version}/customers/{customer_id}/googleAds:search",
            headers=_headers(access_token, developer_token, login_customer_id),
            json=body,
        )
        if reply.status_code != 200:
            log.warning("home numbers refused for %s: %s", customer_id, _why(reply))
            return [], _plain(reply)
        answer = reply.json()
        rows.extend(answer.get("results", []))
        token = answer.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
    return rows, ""


def account_summary(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    days: int = 30,
    api_version: str = "v25",
    login_customer_id: str | None = None,
    client: httpx.Client | None = None,
    today: datetime | None = None,
) -> Summary:
    """Four reads: the days, the split, the campaigns, and the month so far."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(60))
    now = today or datetime.now(UTC)
    found = Summary(customer_id=customer_id, days=days)
    window = f"LAST_{days}_DAYS" if days in (7, 14, 30) else "LAST_30_DAYS"
    ask = {
        "access_token": access_token,
        "developer_token": developer_token,
        "login_customer_id": login_customer_id,
        "api_version": api_version,
        "client": c,
    }
    try:
        # Two reads, and they cannot be one. Google refuses to segment by
        # conversion category and report clicks, cost or impressions together:
        # "unsupported metrics: clicks, cost_micros, impressions". So the money
        # comes by day on its own, and the calls-and-forms split beside it.
        by_day: dict[str, Day] = {}

        money, trouble = _ask(
            customer_id,
            f"""
            SELECT segments.date, metrics.cost_micros, metrics.clicks,
                   metrics.impressions, customer.currency_code
            FROM customer WHERE segments.date DURING {window}
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            found.trouble = trouble
            return found
        for row in money:
            day = str(row.get("segments", {}).get("date", ""))
            metrics = row.get("metrics", {})
            found.currency = str(row.get("customer", {}).get("currencyCode", "")) or found.currency
            entry = by_day.setdefault(day, Day(date=day))
            entry.cost += _micros(metrics.get("costMicros"))
            found.cost += _micros(metrics.get("costMicros"))
            found.clicks += int(metrics.get("clicks", 0) or 0)
            found.impressions += int(metrics.get("impressions", 0) or 0)
        found.cost = round(found.cost, 2)

        leads, trouble = _ask(
            customer_id,
            f"""
            SELECT segments.date, segments.conversion_action_category, metrics.conversions
            FROM customer WHERE segments.date DURING {window}
            """,
            **ask,  # type: ignore[arg-type]
        )
        for row in leads:
            day = str(row.get("segments", {}).get("date", ""))
            kind = str(row.get("segments", {}).get("conversionActionCategory", ""))
            conversions = float(row.get("metrics", {}).get("conversions", 0) or 0)
            entry = by_day.setdefault(day, Day(date=day))
            if kind in CALL_KINDS:
                entry.calls += conversions
            else:
                entry.forms += conversions

        found.series = [by_day[k] for k in sorted(by_day)]
        found.calls = round(sum(d.calls for d in found.series), 2)
        found.forms = round(sum(d.forms for d in found.series), 2)
        found.leads = round(found.calls + found.forms, 2)

        # Campaigns, with what each one brought and what it is allowed to spend.
        campaigns, trouble = _ask(
            customer_id,
            f"""
            SELECT campaign.id, campaign.name, campaign.status,
                   campaign_budget.amount_micros, metrics.conversions, metrics.cost_micros
            FROM campaign
            WHERE segments.date DURING {window} AND campaign.status != 'REMOVED'
            ORDER BY metrics.cost_micros DESC
            """,
            **ask,  # type: ignore[arg-type]
        )
        for row in campaigns:
            campaign = row.get("campaign", {})
            metrics = row.get("metrics", {})
            daily = _micros(row.get("campaignBudget", {}).get("amountMicros"))
            found.campaigns.append(
                CampaignRow(
                    campaign_id=str(campaign.get("id", "")),
                    name=str(campaign.get("name", "")),
                    status=str(campaign.get("status", "")),
                    serving=str(campaign.get("status", "")),
                    leads=round(float(metrics.get("conversions", 0) or 0), 2),
                    cost=_micros(metrics.get("costMicros")),
                    budget=daily,
                )
            )
        # A monthly budget is what the daily budgets add up to over the month.
        found.monthly_budget = round(
            sum(c.budget for c in found.campaigns if c.status == "ENABLED") * 30.4, 2
        )

        # This calendar month so far, which is what "on pace" is judged against.
        month, trouble = _ask(
            customer_id,
            "SELECT metrics.cost_micros FROM customer WHERE segments.date DURING THIS_MONTH",
            **ask,  # type: ignore[arg-type]
        )
        found.month_cost = round(sum(_micros(r["metrics"]["costMicros"]) for r in month), 2)
        found.month_day = now.day
        # The length of this month, found by stepping into the next one and back.
        next_month = now.replace(day=28) + timedelta(days=4)
        found.month_days = (next_month - timedelta(days=next_month.day)).day

        found.read = True
        return found
    finally:
        if own:
            c.close()


@dataclass
class Detail:
    """One campaign, as its page needs it: the numbers, and what is inside it."""

    read: bool = False
    trouble: str = ""
    campaign_id: str = ""
    name: str = ""
    status: str = ""
    currency: str = ""
    days: int = 30
    leads: float = 0.0
    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0
    budget: float = 0.0
    lost_to_budget: float = 0.0
    lost_to_rank: float = 0.0
    impression_share: float = 0.0
    keywords: list[dict[str, Any]] = field(default_factory=list)
    terms: list[dict[str, Any]] = field(default_factory=list)
    ads: list[dict[str, Any]] = field(default_factory=list)

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
            "leads": round(self.leads, 2),
            "cost": round(self.cost, 2),
            "clicks": self.clicks,
            "impressions": self.impressions,
            "budget": self.budget,
            "cost_per_lead": self.cost_per_lead,
            "lead_rate": self.lead_rate,
            "lost_to_budget": self.lost_to_budget,
            "lost_to_rank": self.lost_to_rank,
            "impression_share": self.impression_share,
            "keywords": self.keywords,
            "terms": self.terms,
            "ads": self.ads,
        }


def _share(value: Any) -> float:
    try:
        return round(float(value) * 100, 1)
    except (TypeError, ValueError):
        return 0.0


def campaign_detail(
    customer_id: str,
    campaign_id: str,
    *,
    access_token: str,
    developer_token: str,
    days: int = 30,
    api_version: str = "v25",
    login_customer_id: str | None = None,
    client: httpx.Client | None = None,
) -> Detail:
    """What one campaign did, and what it is made of.

    Four reads again, each filtered to the campaign. A refusal on one leaves the
    others standing, the same as everywhere else: a page that shows the keywords
    and says it could not read the search terms is more use than an error.
    """
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(60))
    window = f"LAST_{days}_DAYS" if days in (7, 14, 30) else "LAST_30_DAYS"
    found = Detail(campaign_id=campaign_id, days=days)
    where = f"campaign.id = {campaign_id}"
    ask = {
        "access_token": access_token,
        "developer_token": developer_token,
        "login_customer_id": login_customer_id,
        "api_version": api_version,
        "client": c,
    }
    try:
        rows, trouble = _ask(
            customer_id,
            f"""
            SELECT campaign.id, campaign.name, campaign.status, customer.currency_code,
                   campaign_budget.amount_micros, metrics.conversions, metrics.cost_micros,
                   metrics.clicks, metrics.impressions,
                   metrics.search_budget_lost_impression_share,
                   metrics.search_rank_lost_impression_share, metrics.search_impression_share
            FROM campaign WHERE {where} AND segments.date DURING {window}
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            found.trouble = trouble
            return found
        for row in rows:
            campaign = row.get("campaign", {})
            metrics = row.get("metrics", {})
            found.name = str(campaign.get("name", "")) or found.name
            found.status = str(campaign.get("status", "")) or found.status
            found.currency = str(row.get("customer", {}).get("currencyCode", "")) or found.currency
            found.budget = (
                _micros(row.get("campaignBudget", {}).get("amountMicros")) or found.budget
            )
            found.leads += float(metrics.get("conversions", 0) or 0)
            found.cost += _micros(metrics.get("costMicros"))
            found.clicks += int(metrics.get("clicks", 0) or 0)
            found.impressions += int(metrics.get("impressions", 0) or 0)
            found.lost_to_budget = _share(metrics.get("searchBudgetLostImpressionShare"))
            found.lost_to_rank = _share(metrics.get("searchRankLostImpressionShare"))
            found.impression_share = _share(metrics.get("searchImpressionShare"))
        found.cost = round(found.cost, 2)

        keywords, _ = _ask(
            customer_id,
            f"""
            SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
                   ad_group_criterion.quality_info.quality_score,
                   metrics.clicks, metrics.conversions, metrics.cost_micros
            FROM keyword_view WHERE {where} AND segments.date DURING {window}
            ORDER BY metrics.cost_micros DESC
            """,
            **ask,  # type: ignore[arg-type]
        )
        for row in keywords[:60]:
            criterion = row.get("adGroupCriterion", {})
            metrics = row.get("metrics", {})
            leads = round(float(metrics.get("conversions", 0) or 0), 2)
            cost = _micros(metrics.get("costMicros"))
            found.keywords.append(
                {
                    "keyword": str(criterion.get("keyword", {}).get("text", "")),
                    "match": str(criterion.get("keyword", {}).get("matchType", "")).title(),
                    "quality_score": int(
                        criterion.get("qualityInfo", {}).get("qualityScore", 0) or 0
                    ),
                    "clicks": int(metrics.get("clicks", 0) or 0),
                    "leads": leads,
                    "cost": cost,
                    "cost_per_lead": round(cost / leads, 2) if leads else 0.0,
                }
            )

        terms, _ = _ask(
            customer_id,
            f"""
            SELECT search_term_view.search_term, metrics.clicks, metrics.conversions,
                   metrics.cost_micros
            FROM search_term_view WHERE {where} AND segments.date DURING {window}
              AND metrics.cost_micros > 0
            ORDER BY metrics.cost_micros DESC
            """,
            **ask,  # type: ignore[arg-type]
        )
        for row in terms[:60]:
            metrics = row.get("metrics", {})
            leads = round(float(metrics.get("conversions", 0) or 0), 2)
            found.terms.append(
                {
                    "term": str(row.get("searchTermView", {}).get("searchTerm", "")),
                    "clicks": int(metrics.get("clicks", 0) or 0),
                    "leads": leads,
                    "cost": _micros(metrics.get("costMicros")),
                    # Google's word for it, not ours: money spent, nothing back.
                    "waste": leads == 0,
                }
            )

        ads, _ = _ask(
            customer_id,
            f"""
            SELECT ad_group.name, ad_group_ad.ad.responsive_search_ad.headlines,
                   ad_group_ad.policy_summary.approval_status, ad_group_ad.status,
                   metrics.impressions, metrics.clicks, metrics.conversions
            FROM ad_group_ad WHERE {where} AND segments.date DURING {window}
            ORDER BY metrics.impressions DESC
            """,
            **ask,  # type: ignore[arg-type]
        )
        for row in ads[:30]:
            entry = row.get("adGroupAd", {})
            metrics = row.get("metrics", {})
            heads = (entry.get("ad", {}).get("responsiveSearchAd", {}) or {}).get("headlines", [])
            impressions = int(metrics.get("impressions", 0) or 0)
            clicks = int(metrics.get("clicks", 0) or 0)
            found.ads.append(
                {
                    "ad_group": str(row.get("adGroup", {}).get("name", "")),
                    "headlines": [str(h.get("text", "")) for h in heads][:3],
                    "approval": str(entry.get("policySummary", {}).get("approvalStatus", "")),
                    "status": str(entry.get("status", "")),
                    "impressions": impressions,
                    "clicks": clicks,
                    "click_rate": round((clicks / impressions) * 100, 1) if impressions else 0.0,
                }
            )

        found.read = True
        return found
    finally:
        if own:
            c.close()
