"""What a trade is worth in a town, in Google's own numbers.

Keyword Planner answers the question every other check only implies: how many
people search for this here, and what do those clicks cost. It turns "your
listing shuts at five" into "about 1,900 people a month look for a plumber in
Oakville, and the top of the page goes for $4 to $7".

Two calls:

  geoTargetConstants:suggest   the town, as Google knows it
  :generateKeywordIdeas        the searches, their monthly volume and bid range

Both are planning services, which Google blocks below Basic access and rate
limits above it. The answers barely move month to month, so they are asked for
once per audit and never in a loop.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from ppcway.ads.accounts import API, _headers, _plain, _why

log = logging.getLogger(__name__)

MICRO = 1_000_000

#: English. Google's language constants are stable ids; 1000 is en.
ENGLISH = "languageConstants/1000"

#: Canada, the fallback when a town cannot be matched. Better a country-wide
#: figure, said to be country-wide, than a number from the wrong continent.
CANADA = "geoTargetConstants/2124"


@dataclass
class Search:
    """One thing people type, and what it is worth."""

    term: str
    monthly: int
    competition: str
    top_of_page_low: float
    top_of_page_high: float


@dataclass
class Demand:
    """The month's searching for one trade in one town."""

    read: bool = False
    trouble: str = ""
    town: str = ""
    #: False when the town could not be matched and the figures are country-wide.
    town_matched: bool = False
    searches: list[Search] = field(default_factory=list)

    @property
    def monthly(self) -> int:
        """Everybody looking, across every phrasing we were given."""
        return sum(row.monthly for row in self.searches)

    @property
    def click_range(self) -> tuple[float, float]:
        """What the top of the page costs, weighted by how much it is searched."""
        paid = [row for row in self.searches if row.top_of_page_high > 0 and row.monthly > 0]
        if not paid:
            return (0.0, 0.0)
        weight = sum(row.monthly for row in paid)
        low = sum(row.top_of_page_low * row.monthly for row in paid) / weight
        high = sum(row.top_of_page_high * row.monthly for row in paid) / weight
        return (round(low, 2), round(high, 2))

    def as_dict(self) -> dict[str, Any]:
        low, high = self.click_range
        return {
            "read": self.read,
            "trouble": self.trouble,
            "town": self.town,
            "town_matched": self.town_matched,
            "monthly": self.monthly,
            "click_low": low,
            "click_high": high,
            "searches": [asdict(row) for row in self.searches[:12]],
        }


def _money(micros: Any) -> float:
    try:
        return round(int(micros) / MICRO, 2)
    except (TypeError, ValueError):
        return 0.0


def _town(
    name: str,
    *,
    access_token: str,
    developer_token: str,
    api_version: str,
    client: httpx.Client,
) -> str | None:
    """Google's id for a town, or None when it does not know the name."""
    reply = client.post(
        f"{API}/{api_version}/geoTargetConstants:suggest",
        headers=_headers(access_token, developer_token, None),
        json={"locale": "en", "countryCode": "CA", "locationNames": {"names": [name]}},
    )
    if reply.status_code != 200:
        log.warning("Google would not place the town %r: %s", name, _why(reply))
        return None
    for row in reply.json().get("geoTargetConstantSuggestions", []):
        constant = row.get("geoTargetConstant", {})
        if constant.get("status") == "ENABLED" and constant.get("resourceName"):
            return str(constant["resourceName"])
    return None


def demand_for(
    seeds: list[str],
    town: str,
    *,
    customer_id: str,
    access_token: str,
    developer_token: str,
    api_version: str = "v25",
    login_customer_id: str | None = None,
    client: httpx.Client | None = None,
) -> Demand:
    """How much a trade is searched for in a town, and what the clicks cost."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(45))
    found = Demand(town=town)
    try:
        wanted = [s.strip() for s in seeds if s.strip()][:10]
        if not wanted:
            found.trouble = "We had nothing to look up."
            return found

        place = (
            _town(
                town,
                access_token=access_token,
                developer_token=developer_token,
                api_version=api_version,
                client=c,
            )
            if town
            else None
        )
        found.town_matched = place is not None

        reply = c.post(
            f"{API}/{api_version}/customers/{customer_id}:generateKeywordIdeas",
            headers=_headers(access_token, developer_token, login_customer_id),
            json={
                "language": ENGLISH,
                "geoTargetConstants": [place or CANADA],
                "keywordPlanNetwork": "GOOGLE_SEARCH",
                "includeAdultKeywords": False,
                "keywordSeed": {"keywords": wanted},
            },
        )
        if reply.status_code != 200:
            log.warning("Google would not say what %r is worth: %s", wanted[:1], _why(reply))
            found.trouble = _plain(reply)
            return found

        for row in reply.json().get("results", []):
            metrics = row.get("keywordIdeaMetrics") or {}
            monthly = int(metrics.get("avgMonthlySearches", 0) or 0)
            if monthly <= 0:
                continue  # a phrase nobody searches is not news
            found.searches.append(
                Search(
                    term=str(row.get("text", "")),
                    monthly=monthly,
                    competition=str(metrics.get("competition", "")),
                    top_of_page_low=_money(metrics.get("lowTopOfPageBidMicros")),
                    top_of_page_high=_money(metrics.get("highTopOfPageBidMicros")),
                )
            )
        found.searches.sort(key=lambda row: row.monthly, reverse=True)
        found.read = True
        return found
    finally:
        if own:
            c.close()
