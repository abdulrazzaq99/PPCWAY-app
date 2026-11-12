"""The lookups Google's "New campaign" flow makes before anything is created.

Each read has to ask Google the right question at the right address, read
Google's answer the way Google writes it (camelCase, money in micros, int64 as
strings, false booleans left out), and say "nothing, because…" rather than
raise when Google refuses. No request here leaves the machine: every reply
comes from an `httpx.MockTransport`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import httpx

from ppcway.ads.clock import local_today
from ppcway.ads.setup import (
    GROUP_AFFINITY,
    GROUP_CUSTOM,
    GROUP_IN_MARKET,
    GROUP_YOUR_DATA,
    audience_segments,
    billing_ready,
    budget_recommendation,
    conversion_goals,
    image_url,
    keyword_forecast,
    merchant_accounts,
    negative_keyword_lists,
    shared_budgets,
    suggest_brands,
    time_zone_home,
)

KEYS: dict[str, Any] = {"access_token": "a", "developer_token": "d"}

REFUSED = {
    "error": {
        "code": 400,
        "message": "Request contains an invalid argument.",
        "status": "INVALID_ARGUMENT",
        "details": [
            {
                "@type": "type.googleapis.com/google.ads.googleads.v25.errors.GoogleAdsFailure",
                "errors": [
                    {
                        "errorCode": {"queryError": "UNRECOGNIZED_FIELD"},
                        "message": "Unrecognized field in the query.",
                    }
                ],
            }
        ],
    }
}


class Sent:
    """What was asked of Google, in order."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    @property
    def paths(self) -> list[str]:
        return [r.url.path for r in self.requests]

    @property
    def bodies(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests]

    @property
    def queries(self) -> list[str]:
        return [str(body.get("query", "")) for body in self.bodies]


def google(
    answer: Callable[[httpx.Request, dict[str, Any]], httpx.Response],
) -> tuple[httpx.Client, Sent]:
    sent = Sent()

    def handle(request: httpx.Request) -> httpx.Response:
        sent.requests.append(request)
        return answer(request, json.loads(request.content or b"{}"))

    return httpx.Client(transport=httpx.MockTransport(handle)), sent


def always(status: int, body: dict[str, Any]) -> Callable[..., httpx.Response]:
    return lambda request, sent: httpx.Response(status, json=body)


SEARCH = "/v25/customers/1234567890/googleAds:search"


# --- 1. conversion goals ----------------------------------------------------

GOALS = {
    "results": [
        {
            "customerConversionGoal": {
                "resourceName": "customers/1234567890/customerConversionGoals/PURCHASE~WEBSITE",
                "category": "PURCHASE",
                "origin": "WEBSITE",
                "biddable": True,
            }
        },
        {
            # Google leaves a false plain bool out of the reply altogether.
            "customerConversionGoal": {
                "resourceName": "customers/1234567890/customerConversionGoals/PAGE_VIEW~WEBSITE",
                "category": "PAGE_VIEW",
                "origin": "WEBSITE",
            }
        },
        {
            "customerConversionGoal": {
                "category": "PHONE_CALL_LEAD",
                "origin": "CALL_FROM_ADS",
                "biddable": True,
            }
        },
    ]
}

ACTIONS = {
    "results": [
        {
            "conversionAction": {
                "resourceName": "customers/1234567890/conversionActions/11",
                "name": "Checkout complete",
                "category": "PURCHASE",
                "origin": "WEBSITE",
                "status": "ENABLED",
                "primaryForGoal": True,
                "type": "WEBPAGE",
            }
        },
        {
            "conversionAction": {
                "resourceName": "customers/1234567890/conversionActions/12",
                "name": "Thank-you page",
                "category": "PURCHASE",
                "origin": "WEBSITE",
                "status": "ENABLED",
                "primaryForGoal": False,
                "type": "WEBPAGE",
            }
        },
        {
            "conversionAction": {
                "resourceName": "customers/1234567890/conversionActions/13",
                "name": "Calls from ads",
                "category": "PHONE_CALL_LEAD",
                "origin": "CALL_FROM_ADS",
                "status": "ENABLED",
                "primaryForGoal": True,
                "type": "AD_CALL",
            }
        },
    ]
}


def goals_and_actions(request: httpx.Request, body: dict[str, Any]) -> httpx.Response:
    if "FROM customer_conversion_goal" in body["query"]:
        return httpx.Response(200, json=GOALS)
    return httpx.Response(200, json=ACTIONS)


def test_goals_come_with_their_actions_underneath() -> None:
    c, sent = google(goals_and_actions)
    with c:
        found = conversion_goals("123-456-7890", login_customer_id="999-000-1111", **KEYS, client=c)

    assert sent.paths == [SEARCH, SEARCH]
    assert sent.requests[0].headers["developer-token"] == "d"
    assert sent.requests[0].headers["login-customer-id"] == "9990001111"
    assert "conversion_action.primary_for_goal" in sent.queries[1]
    assert "conversion_action.status NOT IN ('REMOVED', 'HIDDEN')" in sent.queries[1]

    assert found["tracking"] is True
    assert found["reason"] == ""
    # Account defaults first; the page view goal is not one.
    assert [(g["category"], g["biddable"]) for g in found["goals"]] == [
        ("PURCHASE", True),
        ("PHONE_CALL_LEAD", True),
        ("PAGE_VIEW", False),
    ]
    purchases = found["goals"][0]
    assert purchases["label"] == "Purchases"
    assert purchases["origin_label"] == "Website"
    assert [(a["name"], a["primary"]) for a in purchases["actions"]] == [
        ("Checkout complete", True),
        ("Thank-you page", False),
    ]
    calls = found["goals"][1]
    assert (calls["label"], calls["origin_label"]) == ("Phone call leads", "Call from ads")
    assert found["goals"][2]["label"] == "Page views"
    assert found["goals"][2]["actions"] == []


def test_an_account_with_nothing_switched_on_is_not_tracking() -> None:
    paused = {
        "results": [
            {
                "conversionAction": {
                    "name": "Old form",
                    "category": "SUBMIT_LEAD_FORM",
                    "origin": "WEBSITE",
                    "status": "UNKNOWN",
                }
            }
        ]
    }

    def answer(request: httpx.Request, body: dict[str, Any]) -> httpx.Response:
        if "FROM customer_conversion_goal" in body["query"]:
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json=paused)

    c, _ = google(answer)
    with c:
        found = conversion_goals("1234567890", **KEYS, client=c)

    assert found["tracking"] is False
    # An action whose goal Google has not made yet is still shown, under it.
    assert found["goals"][0]["label"] == "Submit lead forms"
    assert found["goals"][0]["biddable"] is False


def test_a_refused_goal_read_is_empty_and_says_why() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        found = conversion_goals("1234567890", **KEYS, client=c)

    assert found == {
        "goals": [],
        "tracking": False,
        "reason": "Unrecognized field in the query.",
    }


# --- 2. audience segments ---------------------------------------------------

LISTS = {
    "results": [
        {
            "userList": {
                "resourceName": "customers/1234567890/userLists/501",
                "name": "All visitors (Google Ads)",
                "type": "RULE_BASED",
                "sizeForSearch": "12000",
            }
        },
        {
            "userList": {
                "resourceName": "customers/1234567890/userLists/502",
                "name": "Customer list",
                "type": "CRM_BASED",
            }
        },
    ]
}

INTERESTS = {
    "results": [
        {
            "userInterest": {
                "resourceName": "customers/1234567890/userInterests/80101",
                "name": "Home Improvement Enthusiasts",
                "taxonomyType": "AFFINITY",
            }
        },
        {
            "userInterest": {
                "resourceName": "customers/1234567890/userInterests/80432",
                "name": "Home Improvement Services",
                "taxonomyType": "IN_MARKET",
            }
        },
    ]
}

CUSTOM = {
    "results": [
        {
            "customAudience": {
                "resourceName": "customers/1234567890/customAudiences/77",
                "name": "People searching for boilers",
            }
        }
    ]
}


def segments(request: httpx.Request, body: dict[str, Any]) -> httpx.Response:
    query = body["query"]
    if "FROM user_list" in query:
        return httpx.Response(200, json=LISTS)
    if "FROM user_interest" in query:
        return httpx.Response(200, json=INTERESTS)
    return httpx.Response(200, json=CUSTOM)


def test_typed_text_searches_all_three_sources() -> None:
    c, sent = google(segments)
    with c:
        found = audience_segments("1234567890", "home", **KEYS, client=c)

    assert sent.paths == [SEARCH, SEARCH, SEARCH]
    lists, interests, custom = sent.queries
    assert "user_list.membership_status = 'OPEN'" in lists
    assert "user_list.name LIKE '%home%'" in lists
    assert "user_interest.taxonomy_type IN ('AFFINITY', 'IN_MARKET')" in interests
    assert "user_interest.launched_to_all = TRUE" in interests
    assert "user_interest.name LIKE '%home%'" in interests
    assert interests.endswith("LIMIT 25")
    assert "custom_audience.status = 'ENABLED'" in custom

    assert [(s["kind"], s["group"], s["size"]) for s in found] == [
        ("user_list", GROUP_YOUR_DATA, 12000),
        ("user_list", GROUP_YOUR_DATA, None),
        ("user_interest", GROUP_AFFINITY, None),
        ("user_interest", GROUP_IN_MARKET, None),
        ("custom_audience", GROUP_CUSTOM, None),
    ]
    assert found[2]["resource"] == "customers/1234567890/userInterests/80101"
    assert found[2]["name"] == "Home Improvement Enthusiasts"


def test_quotes_and_wildcards_in_typed_text_cannot_break_the_query() -> None:
    c, sent = google(segments)
    with c:
        audience_segments("1234567890", "O'Brien's 50%_off", **KEYS, client=c)

    # A backslash before the quote, and LIKE's own wildcards in brackets.
    assert "LIKE '%O\\'Brien\\'s 50[%][_]off%'" in sent.queries[1]


def test_nothing_typed_lists_only_the_accounts_own_segments() -> None:
    c, sent = google(segments)
    with c:
        found = audience_segments("1234567890", "  ", **KEYS, client=c)

    assert len(sent.requests) == 2
    assert all("user_interest" not in q for q in sent.queries)
    assert all("LIKE" not in q for q in sent.queries)
    assert {s["kind"] for s in found} == {"user_list", "custom_audience"}


def test_a_refused_source_is_left_out_and_the_rest_still_come_back() -> None:
    def answer(request: httpx.Request, body: dict[str, Any]) -> httpx.Response:
        if "FROM user_interest" in body["query"]:
            return httpx.Response(400, json=REFUSED)
        return segments(request, body)

    c, _ = google(answer)
    with c:
        found = audience_segments("1234567890", "home", **KEYS, client=c)

    assert {s["kind"] for s in found} == {"user_list", "custom_audience"}


def test_refused_everywhere_is_an_empty_list() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        assert audience_segments("1234567890", "home", **KEYS, client=c) == []


# --- 3. brands --------------------------------------------------------------


def test_brands_are_googles_entries_with_ids() -> None:
    reply = {
        "brands": [
            {
                "id": "8263915403",
                "name": "Worcester Bosch",
                "urls": ["worcester-bosch.co.uk"],
                "state": "APPROVED",
            },
            {"id": "4410", "name": "Worx", "state": "UNVERIFIED"},
        ]
    }
    c, sent = google(always(200, reply))
    with c:
        found = suggest_brands("123-456-7890", " wor ", selected_brands=["99"], **KEYS, client=c)

    assert sent.paths == ["/v25/customers/1234567890:suggestBrands"]
    assert sent.requests[0].method == "POST"
    assert sent.bodies[0] == {"brandPrefix": "wor", "selectedBrands": ["99"]}
    assert found == [
        {
            "id": "8263915403",
            "name": "Worcester Bosch",
            "urls": ["worcester-bosch.co.uk"],
            "state": "APPROVED",
        },
        {"id": "4410", "name": "Worx", "urls": [], "state": "UNVERIFIED"},
    ]


def test_no_prefix_asks_google_nothing() -> None:
    c, sent = google(always(200, {"brands": []}))
    with c:
        assert suggest_brands("1234567890", "", **KEYS, client=c) == []
    assert sent.requests == []


def test_refused_brands_are_an_empty_list() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        assert suggest_brands("1234567890", "wor", **KEYS, client=c) == []


# --- 4. budget recommendation -----------------------------------------------

BUDGET = {
    "recommendations": [
        {
            "type": "CAMPAIGN_BUDGET",
            "campaignBudgetRecommendation": {
                "currentBudgetAmountMicros": "20000000",
                "recommendedBudgetAmountMicros": "35000000",
                "budgetOptions": [
                    {
                        "budgetAmountMicros": "50000000",
                        "impact": {
                            "baseMetrics": {"clicks": 40, "costMicros": "140000000"},
                            "potentialMetrics": {
                                "clicks": 96.5,
                                "costMicros": "349000000",
                                "conversions": 7.2,
                            },
                        },
                    },
                    {
                        "budgetAmountMicros": "35000000",
                        "impact": {"potentialMetrics": {"clicks": 71.0, "costMicros": "245000000"}},
                    },
                ],
            },
        }
    ]
}


def test_googles_budget_options_come_back_in_money() -> None:
    c, sent = google(always(200, BUDGET))
    with c:
        found = budget_recommendation(
            "1234567890",
            channel="SEARCH",
            final_url="https://example.com",
            keywords=[("boiler repair", "PHRASE"), ("plumber", "BROAD")],
            bidding_strategy_type="TARGET_SPEND",
            country_codes=["ca"],
            language_codes=["en"],
            location_ids=["geoTargetConstants/9001343", 2124],
            current_budget=20,
            **KEYS,
            client=c,
        )

    assert sent.paths == ["/v25/customers/1234567890/recommendations:generate"]
    body = sent.bodies[0]
    assert body["recommendationTypes"] == ["CAMPAIGN_BUDGET"]
    assert body["advertisingChannelType"] == "SEARCH"
    assert body["biddingInfo"] == {"biddingStrategyType": "TARGET_SPEND"}
    assert body["adGroupInfo"] == [
        {
            "keywords": [
                {"text": "boiler repair", "matchType": "PHRASE"},
                {"text": "plumber", "matchType": "BROAD"},
            ]
        }
    ]
    assert body["assetGroupInfo"] == [{"finalUrl": "https://example.com"}]
    assert body["countryCodes"] == ["CA"]
    assert body["languageCodes"] == ["en"]
    assert body["positiveLocationsIds"] == [9001343, 2124]
    assert body["budgetInfo"] == {"currentBudget": 20_000_000}

    assert found["reason"] == ""
    assert found["recommended"] == 35.0
    # Cheapest first, with what Google expects if that amount is chosen.
    assert found["options"] == [
        {"amount": 35.0, "clicks": 71.0, "conversions": None, "cost": 245.0},
        {"amount": 50.0, "clicks": 96.5, "conversions": 7.2, "cost": 349.0},
    ]


def test_a_target_goes_in_the_bidding_info() -> None:
    c, sent = google(always(200, {"recommendations": []}))
    with c:
        found = budget_recommendation(
            "1234567890",
            channel="PERFORMANCE_MAX",
            final_url="https://example.com",
            keywords=[],
            bidding_strategy_type="TARGET_CPA",
            country_codes=[],
            language_codes=[],
            location_ids=[],
            target_cpa=42.5,
            **KEYS,
            client=c,
        )

    assert sent.bodies[0]["biddingInfo"] == {
        "biddingStrategyType": "TARGET_CPA",
        "targetCpaMicros": 42_500_000,
    }
    assert "adGroupInfo" not in sent.bodies[0]
    assert "budgetInfo" not in sent.bodies[0]
    # Google answering with nothing is not an error, but it is said.
    assert found["options"] == []
    assert found["reason"] == "Google has no budget suggestion for this campaign yet."


def test_a_refused_budget_suggestion_is_empty_and_says_why() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        found = budget_recommendation(
            "1234567890",
            channel="SEARCH",
            final_url="https://example.com",
            keywords=[("plumber", "BROAD")],
            bidding_strategy_type="TARGET_SPEND",
            country_codes=["CA"],
            language_codes=["en"],
            location_ids=[2124],
            **KEYS,
            client=c,
        )

    assert found == {
        "options": [],
        "recommended": None,
        "reason": "Unrecognized field in the query.",
    }


# --- 5. keyword forecast ----------------------------------------------------


def test_the_thirty_day_forecast_is_given_per_day() -> None:
    reply = {
        "campaignForecastMetrics": {
            "averageCpcMicros": "2450000",
            "clicks": 912.0,
            "costMicros": "2234400000",
        }
    }
    c, sent = google(always(200, reply))
    with c:
        found = keyword_forecast(
            "123-456-7890",
            keywords=[("boiler repair", "PHRASE"), ("  ", "BROAD")],
            geo_ids=[9001343, "geoTargetConstants/2124"],
            language_id=1000,
            currency="cad",
            daily_budget=75,
            max_cpc=4,
            strategy="maximize_clicks",
            time_zone="America/Toronto",
            **KEYS,
            client=c,
        )

    assert sent.paths == ["/v25/customers/1234567890:generateKeywordForecastMetrics"]
    body = sent.bodies[0]
    start = local_today("America/Toronto") + timedelta(days=1)
    assert body["forecastPeriod"] == {
        "startDate": start.isoformat(),
        "endDate": (start + timedelta(days=29)).isoformat(),
    }
    assert body["currencyCode"] == "CAD"
    campaign = body["campaign"]
    assert campaign["languageConstants"] == ["languageConstants/1000"]
    assert campaign["geoTargetConstants"] == [
        "geoTargetConstants/9001343",
        "geoTargetConstants/2124",
    ]
    assert campaign["adGroups"] == [
        {"keywords": [{"text": "boiler repair", "matchType": "PHRASE"}]}
    ]
    assert campaign["biddingStrategy"] == {
        "maximizeClicksBiddingStrategy": {
            "dailyTargetSpendMicros": 75_000_000,
            "maxCpcBidCeilingMicros": 4_000_000,
        }
    }

    # Totals over thirty days, divided; averages left as they are; and what
    # Google does not forecast for Maximize clicks stays None, not zero.
    assert found == {
        "clicks": 30.4,
        "cost": 74.48,
        "average_cpc": 2.45,
        "conversions": None,
        "average_cpa": None,
        "reason": "",
    }


def test_maximize_conversions_forecasts_conversions() -> None:
    reply = {
        "campaignForecastMetrics": {
            "costMicros": "1500000000",
            "conversions": 45.0,
            "averageCpaMicros": "33333333",
        }
    }
    c, sent = google(always(200, reply))
    with c:
        found = keyword_forecast(
            "1234567890",
            keywords=[("plumber", "BROAD")],
            geo_ids=[2124],
            language_id="languageConstants/1000",
            daily_budget=50,
            strategy="maximize_conversions",
            **KEYS,
            client=c,
        )

    body = sent.bodies[0]
    assert "currencyCode" not in body
    assert body["campaign"]["biddingStrategy"] == {
        "maximizeConversionsBiddingStrategy": {"dailyTargetSpendMicros": 50_000_000}
    }
    assert found["clicks"] is None
    assert found["conversions"] == 1.5
    assert found["cost"] == 50.0
    assert found["average_cpa"] == 33.33


def test_manual_bidding_sends_the_bid_and_budget() -> None:
    c, sent = google(always(200, {"campaignForecastMetrics": {"clicks": 30}}))
    with c:
        keyword_forecast(
            "1234567890",
            keywords=[("plumber", "EXACT")],
            geo_ids=[2124],
            language_id=1000,
            daily_budget=20,
            max_cpc=3.5,
            strategy="manual_cpc",
            **KEYS,
            client=c,
        )

    assert sent.bodies[0]["campaign"]["biddingStrategy"] == {
        "manualCpcBiddingStrategy": {"maxCpcBidMicros": 3_500_000, "dailyBudgetMicros": 20_000_000}
    }


def test_manual_bidding_without_a_bid_asks_google_nothing() -> None:
    c, sent = google(always(200, {}))
    with c:
        found = keyword_forecast(
            "1234567890",
            keywords=[("plumber", "EXACT")],
            geo_ids=[2124],
            language_id=1000,
            daily_budget=20,
            strategy="manual_cpc",
            **KEYS,
            client=c,
        )

    assert sent.requests == []
    assert found["clicks"] is None
    assert found["reason"]


def test_a_refused_forecast_is_empty_and_says_why() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        found = keyword_forecast(
            "1234567890",
            keywords=[("plumber", "BROAD")],
            geo_ids=[2124],
            language_id=1000,
            daily_budget=20,
            **KEYS,
            client=c,
        )

    assert found == {
        "clicks": None,
        "cost": None,
        "average_cpc": None,
        "conversions": None,
        "average_cpa": None,
        "reason": "Unrecognized field in the query.",
    }


# --- 6. shared budgets ------------------------------------------------------


def test_shared_budgets_are_read_across_every_page() -> None:
    first = {
        "results": [
            {
                "campaignBudget": {
                    "resourceName": "customers/1234567890/campaignBudgets/31",
                    "name": "Shared: all search",
                    "amountMicros": "45500000",
                    "period": "DAILY",
                }
            }
        ],
        "nextPageToken": "page-2",
    }
    second = {
        "results": [
            {
                "campaignBudget": {
                    "resourceName": "customers/1234567890/campaignBudgets/32",
                    "name": "Shared: brand",
                    "amountMicros": "10000000",
                    "period": "DAILY",
                }
            }
        ]
    }

    def answer(request: httpx.Request, body: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json=second if body.get("pageToken") else first)

    c, sent = google(answer)
    with c:
        found = shared_budgets("1234567890", **KEYS, client=c)

    assert sent.paths == [SEARCH, SEARCH]
    assert "campaign_budget.explicitly_shared = TRUE" in sent.queries[0]
    assert "campaign_budget.status = 'ENABLED'" in sent.queries[0]
    assert found == [
        {
            "resource": "customers/1234567890/campaignBudgets/31",
            "name": "Shared: all search",
            "amount": 45.5,
            "period": "DAILY",
        },
        {
            "resource": "customers/1234567890/campaignBudgets/32",
            "name": "Shared: brand",
            "amount": 10.0,
            "period": "DAILY",
        },
    ]


def test_refused_shared_budgets_are_an_empty_list() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        assert shared_budgets("1234567890", **KEYS, client=c) == []


# --- 7. negative keyword lists ----------------------------------------------


def test_negative_keyword_lists_with_their_size() -> None:
    reply = {
        "results": [
            {
                "sharedSet": {
                    "resourceName": "customers/1234567890/sharedSets/61",
                    "name": "Jobs and training",
                    "memberCount": "48",
                }
            },
            {"sharedSet": {"resourceName": "customers/1234567890/sharedSets/62", "name": "Empty"}},
        ]
    }
    c, sent = google(always(200, reply))
    with c:
        found = negative_keyword_lists("1234567890", **KEYS, client=c)

    assert sent.paths == [SEARCH]
    assert "shared_set.type = 'NEGATIVE_KEYWORDS'" in sent.queries[0]
    assert "shared_set.status = 'ENABLED'" in sent.queries[0]
    assert found == [
        {
            "resource": "customers/1234567890/sharedSets/61",
            "name": "Jobs and training",
            "count": 48,
        },
        {"resource": "customers/1234567890/sharedSets/62", "name": "Empty", "count": 0},
    ]


def test_refused_negative_lists_are_an_empty_list() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        assert negative_keyword_lists("1234567890", **KEYS, client=c) == []


# --- 8. Merchant Center accounts --------------------------------------------


def test_linked_merchant_accounts_by_number() -> None:
    reply = {
        "results": [
            {
                "productLink": {
                    "resourceName": "customers/1234567890/productLinks/5",
                    "merchantCenter": {"merchantCenterId": "123456789"},
                }
            }
        ]
    }
    c, sent = google(always(200, reply))
    with c:
        found = merchant_accounts("1234567890", **KEYS, client=c)

    assert sent.paths == [SEARCH]
    assert "product_link.merchant_center.merchant_center_id" in sent.queries[0]
    assert "product_link.type = 'MERCHANT_CENTER'" in sent.queries[0]
    assert found == [{"id": 123456789, "name": ""}]


def test_refused_merchant_accounts_are_an_empty_list() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        assert merchant_accounts("1234567890", **KEYS, client=c) == []


# --- 9. image asset ---------------------------------------------------------


def test_an_image_asset_gives_its_link_and_size() -> None:
    reply = {
        "results": [
            {
                "asset": {
                    "resourceName": "customers/1234567890/assets/888",
                    "imageAsset": {
                        "fullSize": {
                            "url": "https://tpc.googlesyndication.com/simgad/123",
                            "widthPixels": "1200",
                            "heightPixels": "628",
                        }
                    },
                }
            }
        ]
    }
    c, sent = google(always(200, reply))
    with c:
        found = image_url("1234567890", "customers/1234567890/assets/888", **KEYS, client=c)

    assert sent.paths == [SEARCH]
    assert "asset.image_asset.full_size.url" in sent.queries[0]
    assert "asset.resource_name = 'customers/1234567890/assets/888'" in sent.queries[0]
    assert found == {
        "url": "https://tpc.googlesyndication.com/simgad/123",
        "width": 1200,
        "height": 628,
        "reason": "",
    }


def test_an_unknown_image_is_empty_and_says_so() -> None:
    c, _ = google(always(200, {"results": []}))
    with c:
        found = image_url("1234567890", "customers/1234567890/assets/1", **KEYS, client=c)

    assert found["url"] == ""
    assert found["reason"] == "Google has no image by that name in this account."


def test_a_refused_image_read_is_empty_and_says_why() -> None:
    c, _ = google(always(400, REFUSED))
    with c:
        found = image_url("1234567890", "customers/1234567890/assets/888", **KEYS, client=c)

    assert found == {
        "url": "",
        "width": None,
        "height": None,
        "reason": "Unrecognized field in the query.",
    }


# --- 10. the account's home country -----------------------------------------


def test_a_time_zone_names_its_country() -> None:
    assert time_zone_home("America/Toronto") == {
        "resource": "geoTargetConstants/2124",
        "name": "Canada",
        "kind": "Country",
    }
    assert time_zone_home("America/St_Johns") == time_zone_home("America/Regina")
    assert time_zone_home("America/Phoenix") == {
        "resource": "geoTargetConstants/2840",
        "name": "United States",
        "kind": "Country",
    }
    assert time_zone_home("Pacific/Honolulu")["name"] == "United States"
    assert time_zone_home("Asia/Karachi")["resource"] == "geoTargetConstants/2586"
    assert time_zone_home("Europe/London")["name"] == "United Kingdom"
    assert time_zone_home("Asia/Calcutta")["name"] == "India"
    assert time_zone_home("Asia/Dubai")["name"] == "United Arab Emirates"


def test_an_unknown_zone_gives_no_guess() -> None:
    assert time_zone_home("Antarctica/Troll") is None
    assert time_zone_home("") is None
    assert time_zone_home("UTC") is None


# --- billing ----------------------------------------------------------------


def test_billing_is_ready_only_with_an_approved_setup() -> None:
    client, sent = google(
        always(
            200,
            {
                "results": [
                    {"billingSetup": {"status": "PENDING"}},
                    {"billingSetup": {"status": "APPROVED"}},
                ]
            },
        )
    )
    assert billing_ready("1234567890", client=client, **KEYS) == {
        "known": True,
        "ready": True,
        "reason": "",
    }
    assert sent.paths == [SEARCH] and "FROM billing_setup" in sent.queries[0]
    client, _ = google(always(200, {"results": [{"billingSetup": {"status": "PENDING"}}]}))
    assert billing_ready("1234567890", client=client, **KEYS)["ready"] is False


def test_billing_refused_says_nothing_either_way() -> None:
    client, _ = google(always(400, REFUSED))
    said = billing_ready("1234567890", client=client, **KEYS)
    assert said["known"] is False and said["ready"] is False
