"""What Google's "New campaign" flow looks up before anything is created.

Google's own flow asks the account questions at almost every step: which
conversion goals it already has, which audiences it owns, which shared budgets
and negative keyword lists it could reuse, which Merchant Center accounts are
linked to it, what budget Google itself would suggest and what a set of
keywords might bring in. PPCWay rebuilds that flow, so its screens need the
same answers, in Google's words, before the merchant has chosen anything.

Every call here is a read. Nothing is created and nothing is changed: the one
door that may mutate an account is elsewhere, and these helpers never need it.
Two kinds of call:

  googleAds:search                     GAQL reads of the account (through
                                       `sync._ask`, which follows paging)
  :suggestBrands                       Google's brand list, from a prefix
  recommendations:generate             Google's budget suggestion for a
                                       campaign that does not exist yet
  :generateKeywordForecastMetrics      what a set of keywords might bring in

Like the other reads, a refusal is an answer rather than an exception. A
screen that cannot list the account's audiences should still open, saying in
plain words why the list is empty, so every function returns an empty result
(and a reason where its shape has room for one) instead of raising.

Every REST path below was checked against the v25 protos, whose
`google.api.http` annotations are what the REST endpoints are generated from,
and the field names against the v25 RPC and GAQL field references.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Literal

import httpx

from ppcway.ads.accounts import API, _headers, _plain, _why
from ppcway.ads.clock import local_today
from ppcway.ads.sync import _ask

log = logging.getLogger(__name__)

MICRO = 1_000_000

#: How many days the keyword forecast covers. Google wants a future window, so
#: it starts tomorrow; thirty days evens out the weekly rhythm of searching.
FORECAST_DAYS = 30

#: Google's names for each conversion category, as its "New campaign" step 1
#: shows them. Anything Google adds later falls back to its own enum, tidied.
CATEGORY_LABELS: dict[str, str] = {
    "PURCHASE": "Purchases",
    "SUBMIT_LEAD_FORM": "Submit lead forms",
    "PHONE_CALL_LEAD": "Phone call leads",
    "CONTACT": "Contacts",
    "SIGNUP": "Sign-ups",
    "PAGE_VIEW": "Page views",
    "BOOK_APPOINTMENT": "Book appointments",
    "REQUEST_QUOTE": "Request quote",
    "GET_DIRECTIONS": "Get directions",
    "OUTBOUND_CLICK": "Outbound clicks",
    "ADD_TO_CART": "Add to cart",
    "BEGIN_CHECKOUT": "Begin checkout",
    "SUBSCRIBE_PAID": "Subscriptions",
    "DOWNLOAD": "Downloads",
    "ENGAGEMENT": "Engagements",
    "STORE_VISIT": "Store visits",
    "STORE_SALE": "Store sales",
    "QUALIFIED_LEAD": "Qualified leads",
    "CONVERTED_LEAD": "Converted leads",
    "IMPORTED_LEAD": "Imported leads",
    "DEFAULT": "Other",
    # In v25's enum too, though rarer on a small business's account.
    "YOUTUBE_FOLLOW_ON_VIEWS": "YouTube follow-on views",
    "IN_APP_AD_REVENUE": "In-app ad revenue",
}

#: Where a conversion is counted, in a word or two.
ORIGIN_LABELS: dict[str, str] = {
    "WEBSITE": "Website",
    "GOOGLE_HOSTED": "Google hosted",
    "APP": "App",
    "CALL_FROM_ADS": "Call from ads",
    "STORE": "Store",
    "YOUTUBE_HOSTED": "YouTube hosted",
    "LOCAL_SERVICES_ADS": "Local Services Ads",
}

#: The audience picker's headings, Google's groups in plain words.
GROUP_YOUR_DATA = "Your data segments"
GROUP_AFFINITY = "Interests and habits (affinity)"
GROUP_IN_MARKET = "What they are actively researching (in-market)"
GROUP_CUSTOM = "Custom segments"

Strategy = Literal["maximize_clicks", "maximize_conversions", "manual_cpc"]


# --- small helpers ---------------------------------------------------------


@contextmanager
def _client(client: httpx.Client | None, seconds: float) -> Iterator[httpx.Client]:
    """The caller's client, or one of our own that is closed afterwards."""
    if client is not None:
        yield client
        return
    own = httpx.Client(timeout=httpx.Timeout(seconds))
    try:
        yield own
    finally:
        own.close()


Search = Callable[[str], tuple[list[dict[str, Any]], str]]


def _reader(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None,
    api_version: str,
    client: httpx.Client,
) -> Search:
    """One account's GAQL search, with the credentials said once."""

    def search(query: str) -> tuple[list[dict[str, Any]], str]:
        return _ask(
            customer_id,
            query,
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=client,
        )

    return search


def _cid(customer_id: str) -> str:
    """Google wants the ten digits, never the dashed form people copy."""
    return customer_id.replace("-", "").strip()


def _units(micros: Any) -> float | None:
    """Micros as money, or None where Google gave nothing."""
    if micros is None or micros == "":
        return None
    try:
        return round(int(micros) / MICRO, 2)
    except (TypeError, ValueError):
        return None


def _micros_as_units(micros: Any) -> float | None:
    """Micros as money, unrounded, for figures that are divided afterwards."""
    value = _number(micros)
    return None if value is None else value / MICRO


def _micros(amount: float) -> int:
    return round(amount * MICRO)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _whole(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _quoted(text: str) -> str:
    """Text as a GAQL string literal.

    GAQL's grammar allows no raw line breaks in a string and wants a backslash
    before any backslash or quote, so somebody typing O'Brien's into a search
    box gets O'Brien's searched for rather than a broken query.
    """
    clean = " ".join(text.split())
    return "'" + clean.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _like(text: str) -> str:
    """A LIKE pattern matching `text` anywhere, its own wildcards taken literally.

    GAQL's LIKE treats %, _, [ and ] as pattern characters; wrapping each one
    in square brackets is Google's documented way to match it as itself. LIKE
    is case insensitive, so "plumb" finds "Plumbing".
    """
    literal = "".join(f"[{ch}]" if ch in "[]%_" else ch for ch in text)
    return _quoted(f"%{literal}%")


def _tidy(enum: str) -> str:
    return enum.replace("_", " ").capitalize() if enum else ""


def _geo(value: str | int) -> str:
    text = str(value).strip()
    return text if text.startswith("geoTargetConstants/") else f"geoTargetConstants/{text}"


def _language(value: str | int) -> str:
    text = str(value).strip()
    return text if text.startswith("languageConstants/") else f"languageConstants/{text}"


def _location_id(value: str | int) -> int | None:
    """The bare id Google's recommendation request wants, from either form."""
    return _whole(str(value).strip().removeprefix("geoTargetConstants/"))


# --- 1. conversion goals ----------------------------------------------------


# GAQL resources, v25:
#   https://developers.google.com/google-ads/api/fields/v25/customer_conversion_goal
#   https://developers.google.com/google-ads/api/fields/v25/conversion_action
# Searched through POST {API}/v25/customers/{customer_id}/googleAds:search.
def conversion_goals(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """The account's conversion goals, the way Google's step 1 lists them.

    A goal is a category and an origin together ("Purchases, Website"); the
    conversion actions are the tags and imports that count towards it. Google
    shows each goal with its actions underneath, marks the account defaults
    (`biddable`), and warns when nothing is being tracked at all, which is what
    `tracking` answers: is there at least one switched-on conversion action.
    """
    cid = _cid(customer_id)
    found: dict[str, Any] = {"goals": [], "tracking": False, "reason": ""}
    with _client(client, 30) as c:
        search = _reader(
            cid,
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
        goal_rows, trouble = search(
            """SELECT customer_conversion_goal.category, customer_conversion_goal.origin,
                customer_conversion_goal.biddable
            FROM customer_conversion_goal"""
        )
        if trouble:
            log.warning("Google would not list the conversion goals of %s: %s", cid, trouble)
            found["reason"] = trouble
            return found

        # Removed actions are gone for good and hidden ones are Google's own
        # (old Smart campaign tags, for instance); Google's screen shows neither.
        action_rows, trouble = search(
            """SELECT conversion_action.resource_name, conversion_action.name,
                conversion_action.category, conversion_action.origin,
                conversion_action.status, conversion_action.primary_for_goal,
                conversion_action.type
            FROM conversion_action
            WHERE conversion_action.status NOT IN ('REMOVED', 'HIDDEN')"""
        )

    goals: dict[tuple[str, str], dict[str, Any]] = {}

    def goal(category: str, origin: str, biddable: bool) -> dict[str, Any]:
        return {
            "category": category,
            "origin": origin,
            # A plain proto bool: Google leaves it out of the reply when false.
            "biddable": biddable,
            "label": CATEGORY_LABELS.get(category) or _tidy(category),
            "origin_label": ORIGIN_LABELS.get(origin) or _tidy(origin),
            "actions": [],
        }

    for row in goal_rows:
        g = row.get("customerConversionGoal") or {}
        key = (str(g.get("category", "")), str(g.get("origin", "")))
        goals[key] = goal(*key, bool(g.get("biddable", False)))

    if trouble:
        log.warning("Google would not list the conversion actions of %s: %s", cid, trouble)
        found["reason"] = trouble
    for row in action_rows:
        a = row.get("conversionAction") or {}
        key = (str(a.get("category", "")), str(a.get("origin", "")))
        if key not in goals:
            # Google makes the goal when the first action of its kind appears;
            # one read between the two would otherwise lose the action.
            goals[key] = goal(*key, False)
        status = str(a.get("status", ""))
        goals[key]["actions"].append(
            {
                "resource": str(a.get("resourceName", "")),
                "name": str(a.get("name", "")),
                "status": status,
                "primary": bool(a.get("primaryForGoal", False)),
                "type": str(a.get("type", "")),
            }
        )
        if status == "ENABLED":
            found["tracking"] = True

    # Account defaults first, as Google lists them; otherwise Google's order.
    found["goals"] = sorted(goals.values(), key=lambda g: not g["biddable"])
    return found


# --- 2. audience segments ---------------------------------------------------


# GAQL resources, v25:
#   https://developers.google.com/google-ads/api/fields/v25/user_list
#   https://developers.google.com/google-ads/api/fields/v25/user_interest
#   https://developers.google.com/google-ads/api/fields/v25/custom_audience
# LIKE is case insensitive and brackets escape its wildcards:
#   https://developers.google.com/google-ads/api/docs/query/case-sensitivity
#   https://developers.google.com/google-ads/api/docs/query/grammar
def audience_segments(
    customer_id: str,
    query: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Audience segments matching what somebody typed, for the audience picker.

    Three sources, as Google's picker has them: the account's own lists
    (website visitors, customer lists), Google's affinity and in-market
    segments, and the account's custom segments. With nothing typed, only the
    account's own lists and custom segments come back: Google's catalogue runs
    to thousands and is only worth showing once somebody has said what they
    are looking for. A source Google refuses is left out; the others still
    come back.
    """
    cid = _cid(customer_id)
    text = query.strip()[:80]
    named = f"AND user_list.name LIKE {_like(text)}" if text else ""
    custom_named = f"AND custom_audience.name LIKE {_like(text)}" if text else ""
    out: list[dict[str, Any]] = []
    with _client(client, 30) as c:
        search = _reader(
            cid,
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )

        # A closed list stops collecting people, so it cannot be targeted.
        rows, trouble = search(
            f"""SELECT user_list.resource_name, user_list.name, user_list.type,
                user_list.size_for_search
            FROM user_list
            WHERE user_list.membership_status = 'OPEN' {named}"""
        )
        if trouble:
            log.warning("Google would not list the audience lists of %s: %s", cid, trouble)
        for row in rows:
            u = row.get("userList") or {}
            out.append(
                {
                    "kind": "user_list",
                    "resource": str(u.get("resourceName", "")),
                    "name": str(u.get("name", "")),
                    "group": GROUP_YOUR_DATA,
                    "size": _whole(u.get("sizeForSearch")),
                }
            )

        if text:
            # Only segments Google has launched everywhere; the rest are
            # channel or country experiments a Search campaign cannot use.
            rows, trouble = search(
                f"""SELECT user_interest.resource_name, user_interest.name,
                    user_interest.taxonomy_type
                FROM user_interest
                WHERE user_interest.taxonomy_type IN ('AFFINITY', 'IN_MARKET')
                    AND user_interest.launched_to_all = TRUE
                    AND user_interest.name LIKE {_like(text)}
                LIMIT 25"""
            )
            if trouble:
                log.warning("Google would not search its segments for %s: %s", cid, trouble)
            for row in rows:
                i = row.get("userInterest") or {}
                taxonomy = str(i.get("taxonomyType", ""))
                out.append(
                    {
                        "kind": "user_interest",
                        "resource": str(i.get("resourceName", "")),
                        "name": str(i.get("name", "")),
                        "group": GROUP_AFFINITY if taxonomy == "AFFINITY" else GROUP_IN_MARKET,
                        "size": None,
                    }
                )

        rows, trouble = search(
            f"""SELECT custom_audience.resource_name, custom_audience.name
            FROM custom_audience
            WHERE custom_audience.status = 'ENABLED' {custom_named}"""
        )
        if trouble:
            log.warning("Google would not list the custom segments of %s: %s", cid, trouble)
        for row in rows:
            a = row.get("customAudience") or {}
            out.append(
                {
                    "kind": "custom_audience",
                    "resource": str(a.get("resourceName", "")),
                    "name": str(a.get("name", "")),
                    "group": GROUP_CUSTOM,
                    "size": None,
                }
            )
    return out


# --- 3. brands --------------------------------------------------------------


# POST {API}/v25/customers/{customer_id}:suggestBrands
#   https://developers.google.com/google-ads/api/reference/rpc/v25/BrandSuggestionService
#   https://developers.google.com/google-ads/api/reference/rpc/v25/SuggestBrandsRequest
#   path from googleapis/google/ads/googleads/v25/services/brand_suggestion_service.proto
def suggest_brands(
    customer_id: str,
    prefix: str,
    *,
    selected_brands: list[str] | None = None,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Brands Google knows that start with what somebody typed.

    For brand inclusions and exclusions (AI Max and Performance Max brand
    lists): Google matches brands by its own id, not by the name typed, so the
    picker has to offer Google's entries. `selected_brands` are ids already
    chosen, which Google then leaves out of the suggestions.
    """
    text = prefix.strip()
    if not text:
        return []
    with _client(client, 20) as c:
        reply = c.post(
            f"{API}/{api_version}/customers/{_cid(customer_id)}:suggestBrands",
            headers=_headers(access_token, developer_token, login_customer_id),
            json={"brandPrefix": text, "selectedBrands": list(selected_brands or [])},
        )
    if reply.status_code != 200:
        log.warning("Google would not suggest brands for %r: %s", text, _why(reply))
        return []
    return [
        {
            "id": str(brand.get("id", "")),
            "name": str(brand.get("name", "")),
            "urls": [str(url) for url in brand.get("urls") or []],
            "state": str(brand.get("state", "")),
        }
        for brand in reply.json().get("brands") or []
    ]


# --- 4. budget recommendation -----------------------------------------------


# POST {API}/v25/customers/{customer_id}/recommendations:generate
#   https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateRecommendationsRequest
#   https://developers.google.com/google-ads/api/reference/rpc/v25/Recommendation.CampaignBudgetRecommendation
#   https://developers.google.com/google-ads/api/docs/recommendations (campaign construction)
#   path from googleapis/google/ads/googleads/v25/services/recommendation_service.proto
def budget_recommendation(
    customer_id: str,
    *,
    channel: str,
    final_url: str,
    keywords: list[tuple[str, str]],
    bidding_strategy_type: str,
    country_codes: list[str],
    language_codes: list[str],
    location_ids: list[str | int],
    current_budget: float | None = None,
    target_cpa: float | None = None,
    target_roas: float | None = None,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Google's suggested daily budget for a campaign that does not exist yet.

    Google's budget step offers a few amounts, each with what it expects that
    amount to bring in. The same suggestion is available before the campaign
    is created, from a description of it: `channel` is SEARCH or
    PERFORMANCE_MAX (the only two Google accepts here), `bidding_strategy_type`
    is Google's enum (Maximize clicks is TARGET_SPEND there), `keywords` are
    (text, match type) pairs, and `location_ids` are geo target ids, bare or
    as `geoTargetConstants/…`.

    For Search, Google needs the keywords, countries, languages and places, or
    it quietly returns nothing. The amounts are daily, in the account's
    currency. Google does not say what period its click and conversion
    estimates cover, so they are passed on as given, not scaled.
    """
    found: dict[str, Any] = {"options": [], "recommended": None, "reason": ""}

    bidding: dict[str, Any] = {"biddingStrategyType": bidding_strategy_type}
    # One target at most: the three are a oneof in Google's request.
    if target_cpa is not None:
        bidding["targetCpaMicros"] = _micros(target_cpa)
    elif target_roas is not None:
        bidding["targetRoas"] = float(target_roas)

    body: dict[str, Any] = {
        "recommendationTypes": ["CAMPAIGN_BUDGET"],
        "advertisingChannelType": channel,
        "biddingInfo": bidding,
        "assetGroupInfo": [{"finalUrl": final_url}],
        "countryCodes": [code.upper() for code in country_codes],
        "languageCodes": list(language_codes),
        "positiveLocationsIds": [
            place for place in (_location_id(v) for v in location_ids) if place is not None
        ],
    }
    if keywords:
        body["adGroupInfo"] = [
            {"keywords": [{"text": text, "matchType": match} for text, match in keywords]}
        ]
    if current_budget is not None:
        body["budgetInfo"] = {"currentBudget": _micros(current_budget)}

    with _client(client, 30) as c:
        reply = c.post(
            f"{API}/{api_version}/customers/{_cid(customer_id)}/recommendations:generate",
            headers=_headers(access_token, developer_token, login_customer_id),
            json=body,
        )
    if reply.status_code != 200:
        log.warning("Google would not suggest a budget for %s: %s", customer_id, _why(reply))
        found["reason"] = _plain(reply)
        return found

    for item in reply.json().get("recommendations") or []:
        budget = item.get("campaignBudgetRecommendation")
        if not budget:
            continue
        found["recommended"] = _units(budget.get("recommendedBudgetAmountMicros"))
        for option in budget.get("budgetOptions") or []:
            amount = _units(option.get("budgetAmountMicros"))
            if amount is None:
                continue
            # What Google expects if this amount is chosen, not what the
            # account does today (that is `baseMetrics`).
            expect = (option.get("impact") or {}).get("potentialMetrics") or {}
            found["options"].append(
                {
                    "amount": amount,
                    "clicks": _number(expect.get("clicks")),
                    "conversions": _number(expect.get("conversions")),
                    "cost": _units(expect.get("costMicros")),
                }
            )
        break
    found["options"].sort(key=lambda option: option["amount"])
    if not found["options"] and found["recommended"] is None:
        found["reason"] = "Google has no budget suggestion for this campaign yet."
    return found


# --- 5. keyword forecast ----------------------------------------------------


# POST {API}/v25/customers/{customer_id}:generateKeywordForecastMetrics
#   https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateKeywordForecastMetricsRequest
#   https://developers.google.com/google-ads/api/docs/keyword-planning/generate-forecast-metrics
#   path from googleapis/google/ads/googleads/v25/services/keyword_plan_idea_service.proto
def keyword_forecast(
    customer_id: str,
    *,
    keywords: list[tuple[str, str]],
    geo_ids: list[str | int],
    language_id: str | int,
    currency: str = "",
    daily_budget: float,
    max_cpc: float | None = None,
    strategy: Strategy = "maximize_clicks",
    time_zone: str = "",
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """What a set of keywords might bring in a day, in Google's forecast.

    Google forecasts a whole campaign over a window, not a day, so this asks
    for the thirty days from tomorrow and divides the totals by thirty. The
    averages (cost per click, cost per conversion) are averages already and
    are passed on as they are.

    v24 cut the forecast down: clicks and cost per click come back only for
    Maximize clicks and manual CPC, conversions and cost per conversion only
    for Maximize conversions, and impressions never. Whatever Google leaves
    out is None, never zero, because zero would be a forecast.

    Google dates the window in the account's own time zone and refuses one
    that starts today there, so pass the account's `time_zone` where it is
    known; without it, tomorrow is reckoned in UTC.
    """
    empty: dict[str, Any] = {
        "clicks": None,
        "cost": None,
        "average_cpc": None,
        "conversions": None,
        "average_cpa": None,
        "reason": "",
    }
    wanted = [(text.strip(), match) for text, match in keywords if text.strip()]
    if not wanted:
        return {**empty, "reason": "We had no keywords to forecast."}

    spend = _micros(daily_budget)
    bidding: dict[str, Any]
    if strategy == "manual_cpc":
        if max_cpc is None:
            return {**empty, "reason": "A manual bidding forecast needs a highest bid per click."}
        bidding = {
            "manualCpcBiddingStrategy": {
                "maxCpcBidMicros": _micros(max_cpc),
                "dailyBudgetMicros": spend,
            }
        }
    elif strategy == "maximize_conversions":
        bidding = {"maximizeConversionsBiddingStrategy": {"dailyTargetSpendMicros": spend}}
    else:
        clicks: dict[str, Any] = {"dailyTargetSpendMicros": spend}
        if max_cpc is not None:
            clicks["maxCpcBidCeilingMicros"] = _micros(max_cpc)
        bidding = {"maximizeClicksBiddingStrategy": clicks}

    start = local_today(time_zone) + timedelta(days=1)
    end = start + timedelta(days=FORECAST_DAYS - 1)
    # v24 renamed geo_modifiers to geo_target_constants and biddable_keywords
    # to keywords, and dropped the network choice; this is the v25 shape.
    body: dict[str, Any] = {
        "forecastPeriod": {"startDate": start.isoformat(), "endDate": end.isoformat()},
        "campaign": {
            "languageConstants": [_language(language_id)],
            "geoTargetConstants": [_geo(place) for place in geo_ids],
            "biddingStrategy": bidding,
            "adGroups": [
                {"keywords": [{"text": text, "matchType": match} for text, match in wanted]}
            ],
        },
    }
    if currency:
        body["currencyCode"] = currency.upper()

    with _client(client, 45) as c:
        reply = c.post(
            f"{API}/{api_version}/customers/{_cid(customer_id)}:generateKeywordForecastMetrics",
            headers=_headers(access_token, developer_token, login_customer_id),
            json=body,
        )
    if reply.status_code != 200:
        log.warning("Google would not forecast %r: %s", wanted[:1], _why(reply))
        return {**empty, "reason": _plain(reply)}

    metrics = reply.json().get("campaignForecastMetrics") or {}

    def per_day(value: float | None) -> float | None:
        return None if value is None else round(value / FORECAST_DAYS, 2)

    return {
        "clicks": per_day(_number(metrics.get("clicks"))),
        "cost": per_day(_micros_as_units(metrics.get("costMicros"))),
        "average_cpc": _units(metrics.get("averageCpcMicros")),
        "conversions": per_day(_number(metrics.get("conversions"))),
        "average_cpa": _units(metrics.get("averageCpaMicros")),
        "reason": "" if metrics else "Google had no forecast for these keywords.",
    }


# --- 6. shared budgets ------------------------------------------------------


# GAQL resource, v25:
#   https://developers.google.com/google-ads/api/fields/v25/campaign_budget
def shared_budgets(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """The account's shared budgets, which Google's budget step offers to reuse.

    Every campaign has a budget, but only an explicitly shared one can be
    picked for a new campaign; the rest belong to their own campaign.
    """
    cid = _cid(customer_id)
    with _client(client, 30) as c:
        rows, trouble = _ask(
            cid,
            """SELECT campaign_budget.resource_name, campaign_budget.name,
                campaign_budget.amount_micros, campaign_budget.period
            FROM campaign_budget
            WHERE campaign_budget.explicitly_shared = TRUE
                AND campaign_budget.status = 'ENABLED'""",
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
    if trouble:
        log.warning("Google would not list the shared budgets of %s: %s", cid, trouble)
    out: list[dict[str, Any]] = []
    for row in rows:
        b = row.get("campaignBudget") or {}
        out.append(
            {
                "resource": str(b.get("resourceName", "")),
                "name": str(b.get("name", "")),
                "amount": _units(b.get("amountMicros")),
                "period": str(b.get("period", "")),
            }
        )
    return out


# --- 7. negative keyword lists ----------------------------------------------


# GAQL resource, v25:
#   https://developers.google.com/google-ads/api/fields/v25/shared_set
def negative_keyword_lists(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """The account's negative keyword lists, which a new campaign may take on.

    Only NEGATIVE_KEYWORDS sets: the account-level list
    (ACCOUNT_LEVEL_NEGATIVE_KEYWORDS) applies to every campaign already and is
    not something a campaign chooses.
    """
    cid = _cid(customer_id)
    with _client(client, 30) as c:
        rows, trouble = _ask(
            cid,
            """SELECT shared_set.resource_name, shared_set.name, shared_set.member_count
            FROM shared_set
            WHERE shared_set.type = 'NEGATIVE_KEYWORDS' AND shared_set.status = 'ENABLED'""",
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
    if trouble:
        log.warning("Google would not list the negative keyword lists of %s: %s", cid, trouble)
    out: list[dict[str, Any]] = []
    for row in rows:
        s = row.get("sharedSet") or {}
        out.append(
            {
                "resource": str(s.get("resourceName", "")),
                "name": str(s.get("name", "")),
                "count": _whole(s.get("memberCount")) or 0,
            }
        )
    return out


# --- 8. Merchant Center accounts --------------------------------------------


# GAQL resource, v25:
#   https://developers.google.com/google-ads/api/fields/v25/product_link
def merchant_accounts(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Merchant Center accounts linked to this Google Ads account.

    Shopping and retail Performance Max campaigns sell from one of these.
    Google Ads knows a linked Merchant Center account only by its number;
    its name lives in Merchant Center, which this service does not read, so
    `name` is empty and the screen shows the number.
    """
    cid = _cid(customer_id)
    with _client(client, 30) as c:
        rows, trouble = _ask(
            cid,
            """SELECT product_link.resource_name, product_link.merchant_center.merchant_center_id
            FROM product_link
            WHERE product_link.type = 'MERCHANT_CENTER'""",
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
    if trouble:
        log.warning("Google would not list the Merchant Center links of %s: %s", cid, trouble)
    out: list[dict[str, Any]] = []
    for row in rows:
        link = row.get("productLink") or {}
        merchant = _whole((link.get("merchantCenter") or {}).get("merchantCenterId"))
        if merchant is not None:
            out.append({"id": merchant, "name": ""})
    return out


# --- 9. image asset ---------------------------------------------------------


# GAQL resource, v25:
#   https://developers.google.com/google-ads/api/fields/v25/asset
#   (ImageAsset.full_size is an ImageDimension: url, width_pixels, height_pixels)
def image_url(
    customer_id: str,
    asset_resource: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Where an image asset can be seen, and its size, for a preview.

    Google hosts every uploaded image and gives a link to its full size; the
    screens show that link rather than keeping a copy of the image.
    """
    cid = _cid(customer_id)
    found: dict[str, Any] = {"url": "", "width": None, "height": None, "reason": ""}
    with _client(client, 20) as c:
        rows, trouble = _ask(
            cid,
            f"""SELECT asset.resource_name, asset.image_asset.full_size.url,
                asset.image_asset.full_size.width_pixels,
                asset.image_asset.full_size.height_pixels
            FROM asset
            WHERE asset.resource_name = {_quoted(asset_resource)}""",
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
    if trouble:
        log.warning("Google would not show the image %s: %s", asset_resource, trouble)
        found["reason"] = trouble
        return found
    if not rows:
        found["reason"] = "Google has no image by that name in this account."
        return found
    size = ((rows[0].get("asset") or {}).get("imageAsset") or {}).get("fullSize") or {}
    found["url"] = str(size.get("url", ""))
    found["width"] = _whole(size.get("widthPixels"))
    found["height"] = _whole(size.get("heightPixels"))
    if not found["url"]:
        found["reason"] = "That asset is not an image Google can show."
    return found


# --- 10. the account's home country -----------------------------------------

#: Countries as Google's geo target constants. A country's id is 2000 plus
#: its ISO 3166 numeric code (Canada is 124, so 2124).
_COUNTRIES: dict[str, tuple[int, str]] = {
    "US": (2840, "United States"),
    "CA": (2124, "Canada"),
    "GB": (2826, "United Kingdom"),
    "AU": (2036, "Australia"),
    "PK": (2586, "Pakistan"),
    "IN": (2356, "India"),
    "IE": (2372, "Ireland"),
    "NZ": (2554, "New Zealand"),
    "DE": (2276, "Germany"),
    "FR": (2250, "France"),
    "ES": (2724, "Spain"),
    "IT": (2380, "Italy"),
    "NL": (2528, "Netherlands"),
    "AE": (2784, "United Arab Emirates"),
    "SA": (2682, "Saudi Arabia"),
    "SG": (2702, "Singapore"),
    "ZA": (2710, "South Africa"),
    "MX": (2484, "Mexico"),
    "BR": (2076, "Brazil"),
    "PL": (2616, "Poland"),
}

#: The zones each country's accounts are commonly set to, including the old
#: aliases ("US/Eastern", "Asia/Calcutta") that older accounts still carry.
_ZONES: dict[str, tuple[str, ...]] = {
    "US": (
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Phoenix",
        "America/Anchorage",
        "Pacific/Honolulu",
        "America/Detroit",
        "America/Boise",
        "America/Juneau",
        "America/Sitka",
        "America/Nome",
        "America/Yakutat",
        "America/Metlakatla",
        "America/Adak",
        "America/Menominee",
        "America/Indiana/Indianapolis",
        "America/Indiana/Knox",
        "America/Indiana/Marengo",
        "America/Indiana/Petersburg",
        "America/Indiana/Tell_City",
        "America/Indiana/Vevay",
        "America/Indiana/Vincennes",
        "America/Indiana/Winamac",
        "America/Kentucky/Louisville",
        "America/Kentucky/Monticello",
        "America/North_Dakota/Center",
        "America/North_Dakota/New_Salem",
        "America/North_Dakota/Beulah",
        "US/Eastern",
        "US/Central",
        "US/Mountain",
        "US/Pacific",
        "US/Arizona",
        "US/Alaska",
        "US/Hawaii",
    ),
    "CA": (
        "America/Toronto",
        "America/Vancouver",
        "America/Edmonton",
        "America/Winnipeg",
        "America/Halifax",
        "America/St_Johns",
        "America/Regina",
        "America/Montreal",
        "America/Moncton",
        "America/Glace_Bay",
        "America/Goose_Bay",
        "America/Swift_Current",
        "America/Whitehorse",
        "America/Dawson",
        "America/Dawson_Creek",
        "America/Fort_Nelson",
        "America/Creston",
        "America/Yellowknife",
        "America/Iqaluit",
        "America/Rankin_Inlet",
        "America/Resolute",
        "America/Cambridge_Bay",
        "America/Inuvik",
        "America/Atikokan",
        "America/Thunder_Bay",
        "America/Nipigon",
        "America/Rainy_River",
        "America/Blanc-Sablon",
        "Canada/Eastern",
        "Canada/Central",
        "Canada/Mountain",
        "Canada/Pacific",
        "Canada/Atlantic",
        "Canada/Newfoundland",
        "Canada/Saskatchewan",
    ),
    "GB": ("Europe/London", "Europe/Belfast", "GB"),
    "AU": (
        "Australia/Sydney",
        "Australia/Melbourne",
        "Australia/Brisbane",
        "Australia/Perth",
        "Australia/Adelaide",
        "Australia/Hobart",
        "Australia/Darwin",
        "Australia/Canberra",
        "Australia/Lord_Howe",
        "Australia/Broken_Hill",
        "Australia/Lindeman",
        "Australia/Eucla",
        "Australia/ACT",
        "Australia/NSW",
        "Australia/Queensland",
        "Australia/Victoria",
        "Australia/West",
        "Australia/South",
        "Australia/Tasmania",
        "Australia/North",
    ),
    "PK": ("Asia/Karachi",),
    "IN": ("Asia/Kolkata", "Asia/Calcutta"),
    "IE": ("Europe/Dublin", "Eire"),
    "NZ": ("Pacific/Auckland", "Pacific/Chatham", "NZ"),
    "DE": ("Europe/Berlin", "Europe/Busingen"),
    "FR": ("Europe/Paris",),
    "ES": ("Europe/Madrid", "Atlantic/Canary", "Africa/Ceuta"),
    "IT": ("Europe/Rome",),
    "NL": ("Europe/Amsterdam",),
    "AE": ("Asia/Dubai",),
    "SA": ("Asia/Riyadh",),
    "SG": ("Asia/Singapore", "Singapore"),
    "ZA": ("Africa/Johannesburg",),
    "MX": (
        "America/Mexico_City",
        "America/Cancun",
        "America/Merida",
        "America/Monterrey",
        "America/Matamoros",
        "America/Chihuahua",
        "America/Ciudad_Juarez",
        "America/Ojinaga",
        "America/Mazatlan",
        "America/Bahia_Banderas",
        "America/Hermosillo",
        "America/Tijuana",
    ),
    "BR": (
        "America/Sao_Paulo",
        "America/Bahia",
        "America/Fortaleza",
        "America/Recife",
        "America/Belem",
        "America/Maceio",
        "America/Araguaina",
        "America/Manaus",
        "America/Cuiaba",
        "America/Campo_Grande",
        "America/Porto_Velho",
        "America/Boa_Vista",
        "America/Rio_Branco",
        "America/Eirunepe",
        "America/Santarem",
        "America/Noronha",
    ),
    "PL": ("Europe/Warsaw",),
}

_ZONE_COUNTRY: dict[str, str] = {
    name: country for country, names in _ZONES.items() for name in names
}


def billing_ready(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Whether the account can pay for ads, as Google's review page checks.

    Google flags billing problems before a campaign is published; a campaign
    published into an account with no approved billing setup is created and
    never serves. `billing_setup` is readable through the API
    (developers.google.com/google-ads/api/fields/v25/billing_setup). A read
    Google refuses says nothing either way, and `known` is False.
    """
    cid = _cid(customer_id)
    with _client(client, 30) as c:
        rows, trouble = _ask(
            cid,
            "SELECT billing_setup.status FROM billing_setup",
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
    if trouble:
        log.warning("Google would not say how %s pays: %s", cid, trouble)
        return {"known": False, "ready": False, "reason": trouble}
    statuses = {str((r.get("billingSetup") or {}).get("status", "")) for r in rows}
    return {"known": True, "ready": "APPROVED" in statuses, "reason": ""}


def time_zone_home(time_zone: str) -> dict[str, str] | None:
    """The country an account most likely serves, from its time zone.

    Google's location step offers "<your country>" first, worked out from the
    account. Google Ads does not report a country for an account, but its time
    zone is set when the account is opened and almost always names the
    business's own country, so it is a fair first guess. A zone we cannot tie
    to one country gives None, and the screen offers no guess rather than a
    wrong one.
    """
    country = _ZONE_COUNTRY.get(time_zone.strip())
    if country is None:
        return None
    number, name = _COUNTRIES[country]
    return {"resource": f"geoTargetConstants/{number}", "name": name, "kind": "Country"}
