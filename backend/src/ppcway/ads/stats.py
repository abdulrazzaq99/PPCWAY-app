"""What their own Google Ads account says, for the four checks the free audit cannot see.

Everything here is a read. Five queries, each one a GAQL search against the
account the merchant chose:

  spend          what the last thirty days cost, and what it bought
  search terms   the searches that took money and returned nothing
  keywords       Google's own Quality Score, keyword by keyword
  impression share  the share of the auction lost to a small budget, and to rank
  policy         ads Google has disapproved, which spend nothing while they sit

A refusal is not an exception here. An account can be readable for one of these
and refused for another, and a report that says "we could not read your search
terms" is worth more than a report that fails. So each finding carries whether
it was read, and why not when it was not, in the same plain words the account
picker uses.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from ppcway.ads.accounts import API, _headers, _plain, _why

log = logging.getLogger(__name__)

#: Thirty days is the window the client's report speaks in, and long enough that
#: a quiet week does not read as a catastrophe.
WINDOW = "LAST_30_DAYS"

#: Micros are Google's unit: a millionth of the account's currency.
MICRO = 1_000_000


@dataclass
class Spend:
    """The month in four numbers, which is the sentence before any chart."""

    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0
    conversions: float = 0.0
    currency: str = ""

    @property
    def cost_per_click(self) -> float:
        return round(self.cost / self.clicks, 2) if self.clicks else 0.0

    @property
    def cost_per_conversion(self) -> float:
        return round(self.cost / self.conversions, 2) if self.conversions else 0.0


@dataclass
class WastedTerm:
    """A search that took money and brought no enquiry."""

    term: str
    cost: float
    clicks: int


@dataclass
class WeakKeyword:
    """A keyword Google scores poorly, which is a bill paid in every auction."""

    keyword: str
    quality_score: int
    cost: float
    clicks: int


@dataclass
class LostShare:
    """A campaign losing the auction, and whether it is the budget or the ad."""

    campaign: str
    cost: float
    lost_to_budget: float
    lost_to_rank: float
    impression_share: float


@dataclass
class RejectedAd:
    """An ad Google will not show. It costs nothing, which is the problem."""

    campaign: str
    ad_group: str
    status: str


@dataclass
class Finding[Row]:
    """One check: what it found, or why it could not look."""

    read: bool = False
    trouble: str = ""
    rows: list[Row] = field(default_factory=list)


@dataclass
class AdsReading:
    """Everything their account would tell us, on one date."""

    customer_id: str
    spend: Spend = field(default_factory=Spend)
    wasted: Finding[WastedTerm] = field(default_factory=Finding)
    keywords: Finding[WeakKeyword] = field(default_factory=Finding)
    share: Finding[LostShare] = field(default_factory=Finding)
    rejected: Finding[RejectedAd] = field(default_factory=Finding)

    @property
    def wasted_cost(self) -> float:
        return round(sum(row.cost for row in self.wasted.rows), 2)

    def as_dict(self) -> dict[str, Any]:
        """The shape the report reads, with the sums it would otherwise redo."""
        return {
            "customer_id": self.customer_id,
            "window_days": 30,
            "spend": {
                **asdict(self.spend),
                "cost_per_click": self.spend.cost_per_click,
                "cost_per_conversion": self.spend.cost_per_conversion,
            },
            "wasted": {
                "read": self.wasted.read,
                "trouble": self.wasted.trouble,
                "cost": self.wasted_cost,
                "terms": [asdict(row) for row in self.wasted.rows],
            },
            "keywords": {
                "read": self.keywords.read,
                "trouble": self.keywords.trouble,
                "rows": [asdict(row) for row in self.keywords.rows],
            },
            "share": {
                "read": self.share.read,
                "trouble": self.share.trouble,
                "rows": [asdict(row) for row in self.share.rows],
            },
            "rejected": {
                "read": self.rejected.read,
                "trouble": self.rejected.trouble,
                "rows": [asdict(row) for row in self.rejected.rows],
            },
        }


def _micros(value: Any) -> float:
    try:
        return round(int(value) / MICRO, 2)
    except (TypeError, ValueError):
        return 0.0


def _share(value: Any) -> float:
    """Google gives a share as a fraction; the screen says a percentage."""
    try:
        return round(float(value) * 100, 1)
    except (TypeError, ValueError):
        return 0.0


def _search(
    customer_id: str,
    query: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None,
    api_version: str,
    client: httpx.Client,
) -> tuple[list[dict[str, Any]], str]:
    """Every row of one query, or the plain reason there are none.

    Google pages its answers; a small account fits in one page, a busy one does
    not, and the page we never ask for is the spend we never report.
    """
    rows: list[dict[str, Any]] = []
    body: dict[str, Any] = {"query": query, "pageSize": 1000}
    for _ in range(10):  # ten pages is far past any small business
        reply = client.post(
            f"{API}/{api_version}/customers/{customer_id}/googleAds:search",
            headers=_headers(access_token, developer_token, login_customer_id),
            json=body,
        )
        if reply.status_code != 200:
            log.warning("Google would not answer for customer %s: %s", customer_id, _why(reply))
            return [], _plain(reply)
        answer = reply.json()
        rows.extend(answer.get("results", []))
        token = answer.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
    return rows, ""


SPEND_QUERY = f"""
    SELECT metrics.cost_micros, metrics.clicks, metrics.impressions,
           metrics.conversions, customer.currency_code
    FROM customer
    WHERE segments.date DURING {WINDOW}
"""

WASTED_QUERY = f"""
    SELECT search_term_view.search_term, metrics.cost_micros, metrics.clicks,
           metrics.conversions
    FROM search_term_view
    WHERE segments.date DURING {WINDOW} AND metrics.cost_micros > 0
    ORDER BY metrics.cost_micros DESC
"""

KEYWORD_QUERY = f"""
    SELECT ad_group_criterion.keyword.text,
           ad_group_criterion.quality_info.quality_score,
           metrics.cost_micros, metrics.clicks
    FROM keyword_view
    WHERE segments.date DURING {WINDOW}
      AND ad_group_criterion.quality_info.quality_score <= 5
    ORDER BY metrics.cost_micros DESC
"""

SHARE_QUERY = f"""
    SELECT campaign.name, metrics.cost_micros,
           metrics.search_budget_lost_impression_share,
           metrics.search_rank_lost_impression_share,
           metrics.search_impression_share
    FROM campaign
    WHERE segments.date DURING {WINDOW} AND metrics.impressions > 0
    ORDER BY metrics.cost_micros DESC
"""

REJECTED_QUERY = """
    SELECT campaign.name, ad_group.name,
           ad_group_ad.policy_summary.approval_status
    FROM ad_group_ad
    WHERE ad_group_ad.policy_summary.approval_status IN ('DISAPPROVED', 'AREA_OF_INTEREST_ONLY')
      AND ad_group_ad.status != 'REMOVED'
"""


def read_account(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    api_version: str = "v25",
    login_customer_id: str | None = None,
    client: httpx.Client | None = None,
) -> AdsReading:
    """The five reads, each surviving the others' refusals."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(60))
    ask = {
        "access_token": access_token,
        "developer_token": developer_token,
        "login_customer_id": login_customer_id,
        "api_version": api_version,
        "client": c,
    }
    reading = AdsReading(customer_id=customer_id)
    try:
        rows, trouble = _search(customer_id, SPEND_QUERY, **ask)  # type: ignore[arg-type]
        for row in rows:
            metrics = row.get("metrics", {})
            reading.spend.cost += _micros(metrics.get("costMicros"))
            reading.spend.clicks += int(metrics.get("clicks", 0) or 0)
            reading.spend.impressions += int(metrics.get("impressions", 0) or 0)
            reading.spend.conversions += float(metrics.get("conversions", 0) or 0)
            reading.spend.currency = str(row.get("customer", {}).get("currencyCode", "")) or (
                reading.spend.currency
            )
        reading.spend.cost = round(reading.spend.cost, 2)
        reading.spend.conversions = round(reading.spend.conversions, 2)

        rows, trouble = _search(customer_id, WASTED_QUERY, **ask)  # type: ignore[arg-type]
        reading.wasted = Finding(read=not trouble, trouble=trouble)
        for row in rows:
            metrics = row.get("metrics", {})
            if float(metrics.get("conversions", 0) or 0) > 0:
                continue  # it paid for itself; not waste
            reading.wasted.rows.append(
                WastedTerm(
                    term=str(row.get("searchTermView", {}).get("searchTerm", "")),
                    cost=_micros(metrics.get("costMicros")),
                    clicks=int(metrics.get("clicks", 0) or 0),
                )
            )

        rows, trouble = _search(customer_id, KEYWORD_QUERY, **ask)  # type: ignore[arg-type]
        reading.keywords = Finding(read=not trouble, trouble=trouble)
        for row in rows:
            criterion = row.get("adGroupCriterion", {})
            metrics = row.get("metrics", {})
            reading.keywords.rows.append(
                WeakKeyword(
                    keyword=str(criterion.get("keyword", {}).get("text", "")),
                    quality_score=int(criterion.get("qualityInfo", {}).get("qualityScore", 0) or 0),
                    cost=_micros(metrics.get("costMicros")),
                    clicks=int(metrics.get("clicks", 0) or 0),
                )
            )

        rows, trouble = _search(customer_id, SHARE_QUERY, **ask)  # type: ignore[arg-type]
        reading.share = Finding(read=not trouble, trouble=trouble)
        for row in rows:
            metrics = row.get("metrics", {})
            reading.share.rows.append(
                LostShare(
                    campaign=str(row.get("campaign", {}).get("name", "")),
                    cost=_micros(metrics.get("costMicros")),
                    lost_to_budget=_share(metrics.get("searchBudgetLostImpressionShare")),
                    lost_to_rank=_share(metrics.get("searchRankLostImpressionShare")),
                    impression_share=_share(metrics.get("searchImpressionShare")),
                )
            )

        rows, trouble = _search(customer_id, REJECTED_QUERY, **ask)  # type: ignore[arg-type]
        reading.rejected = Finding(read=not trouble, trouble=trouble)
        for row in rows:
            reading.rejected.rows.append(
                RejectedAd(
                    campaign=str(row.get("campaign", {}).get("name", "")),
                    ad_group=str(row.get("adGroup", {}).get("name", "")),
                    status=str(
                        row.get("adGroupAd", {}).get("policySummary", {}).get("approvalStatus", "")
                    ),
                )
            )
        return reading
    finally:
        if own:
            c.close()
