"""The home and campaign numbers.

Google will not segment by conversion category and report clicks, cost or
impressions in the same query. Asking anyway fails the whole read, which is how
a connected account showed an empty dashboard and Google's own complaint in the
middle of the campaigns page.
"""

from __future__ import annotations

import json

import httpx

from ppcway.ads.summary import account_summary

MONEY = {
    "results": [
        {
            "segments": {"date": "2026-10-10"},
            "metrics": {"costMicros": "12000000", "clicks": 40, "impressions": 900},
            "customer": {"currencyCode": "CAD"},
        },
        {
            "segments": {"date": "2026-10-11"},
            "metrics": {"costMicros": "8000000", "clicks": 25, "impressions": 600},
            "customer": {"currencyCode": "CAD"},
        },
    ]
}

LEADS = {
    "results": [
        {
            "segments": {"date": "2026-10-10", "conversionActionCategory": "PHONE_CALL_LEAD"},
            "metrics": {"conversions": 3.0},
        },
        {
            "segments": {"date": "2026-10-10", "conversionActionCategory": "SUBMIT_LEAD_FORM"},
            "metrics": {"conversions": 2.0},
        },
        {
            "segments": {"date": "2026-10-11", "conversionActionCategory": "PHONE_CALL_LEAD"},
            "metrics": {"conversions": 1.0},
        },
    ]
}

CAMPAIGNS = {
    "results": [
        {
            "campaign": {"id": "123", "name": "Emergency plumbing", "status": "ENABLED"},
            "campaignBudget": {"amountMicros": "30000000"},
            "metrics": {"conversions": 4.0, "costMicros": "15000000"},
        }
    ]
}


def google() -> tuple[httpx.Client, list[str]]:
    """Answers each query by what it asks for, and records every query sent."""
    sent: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        sent.append(query)
        if "conversion_action_category" in query:
            return httpx.Response(200, json=LEADS)
        if "FROM campaign" in query:
            return httpx.Response(200, json=CAMPAIGNS)
        if "THIS_MONTH" in query:
            return httpx.Response(200, json={"results": [{"metrics": {"costMicros": "20000000"}}]})
        return httpx.Response(200, json=MONEY)

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x"), sent


def test_the_category_split_never_asks_for_money_in_the_same_query() -> None:
    """Google's refusal is absolute, and it fails the whole read."""
    c, sent = google()
    with c:
        account_summary("258", access_token="a", developer_token="d", client=c)

    for query in sent:
        if "conversion_action_category" in query:
            for metric in ("cost_micros", "clicks", "impressions"):
                assert metric not in query, f"{metric} asked beside the category segment"


def test_the_day_carries_both_its_money_and_its_leads() -> None:
    c, _ = google()
    with c:
        found = account_summary("258", access_token="a", developer_token="d", client=c)

    assert found.read is True
    assert found.currency == "CAD"
    assert found.cost == 20.0
    assert found.clicks == 65
    assert (found.calls, found.forms, found.leads) == (4.0, 2.0, 6.0)
    first = found.series[0]
    assert (first.date, first.cost, first.calls, first.forms) == ("2026-10-10", 12.0, 3.0, 2.0)


def test_campaigns_carry_what_they_cost_and_brought() -> None:
    c, _ = google()
    with c:
        found = account_summary("258", access_token="a", developer_token="d", client=c)

    [campaign] = found.campaigns
    assert campaign.name == "Emergency plumbing"
    assert campaign.cost == 15.0
    assert campaign.cost_per_lead == 3.75
    assert campaign.budget == 30.0
