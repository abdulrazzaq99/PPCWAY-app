"""What a trade is worth in a town.

This is the number that makes somebody act, so it has to be Google's number and
it has to be honest about the town it describes.
"""

from __future__ import annotations

import json

import httpx

from ppcway.ads.planner import CANADA, demand_for

IDEAS = {
    "results": [
        {
            "text": "plumber oakville",
            "keywordIdeaMetrics": {
                "avgMonthlySearches": "1900",
                "competition": "HIGH",
                "lowTopOfPageBidMicros": "4100000",
                "highTopOfPageBidMicros": "7300000",
            },
        },
        {
            "text": "emergency plumber",
            "keywordIdeaMetrics": {
                "avgMonthlySearches": "480",
                "competition": "HIGH",
                "lowTopOfPageBidMicros": "9000000",
                "highTopOfPageBidMicros": "14000000",
            },
        },
        {
            "text": "plumbing apprenticeship",
            "keywordIdeaMetrics": {"avgMonthlySearches": "0", "competition": "LOW"},
        },
    ]
}

TOWN = {
    "geoTargetConstantSuggestions": [
        {"geoTargetConstant": {"resourceName": "geoTargetConstants/9001343", "status": "ENABLED"}}
    ]
}


def google(town: httpx.Response, ideas: httpx.Response) -> tuple[httpx.Client, list[dict]]:
    sent: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        return town if "locationNames" in body else ideas

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x"), sent


def test_the_month_is_counted_and_the_click_priced() -> None:
    c, _ = google(httpx.Response(200, json=TOWN), httpx.Response(200, json=IDEAS))
    with c:
        found = demand_for(
            ["plumber"],
            "Oakville",
            customer_id="123",
            access_token="a",
            developer_token="d",
            client=c,
        )

    assert found.read is True
    assert found.town_matched is True
    assert found.monthly == 2380  # the phrase nobody searches is left out
    # Weighted by how much each is searched, not a flat average of the two.
    assert found.click_range == (5.09, 8.65)
    assert [row.term for row in found.searches] == ["plumber oakville", "emergency plumber"]


def test_a_town_google_cannot_place_falls_back_and_says_so() -> None:
    """A country-wide figure is useful. A country-wide figure presented as a
    town's is a lie, so the flag travels with the number."""
    c, sent = google(
        httpx.Response(200, json={"geoTargetConstantSuggestions": []}),
        httpx.Response(200, json=IDEAS),
    )
    with c:
        found = demand_for(
            ["plumber"],
            "Nowhereville",
            customer_id="123",
            access_token="a",
            developer_token="d",
            client=c,
        )

    assert found.read is True
    assert found.town_matched is False
    assert sent[1]["geoTargetConstants"] == [CANADA]
    assert found.as_dict()["town_matched"] is False


def test_a_refusal_is_carried_in_words_not_raised() -> None:
    refused = httpx.Response(
        403,
        json={
            "error": {
                "message": "The caller does not have permission",
                "details": [
                    {
                        "errors": [
                            {
                                "errorCode": {
                                    "authorizationError": "CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION"
                                }
                            }
                        ]
                    }
                ],
            }
        },
    )
    c, _ = google(httpx.Response(200, json=TOWN), refused)
    with c:
        found = demand_for(
            ["plumber"],
            "Oakville",
            customer_id="123",
            access_token="a",
            developer_token="d",
            client=c,
        )

    assert found.read is False
    assert "approval" in found.trouble
    assert found.monthly == 0


def test_nothing_to_look_up_asks_google_nothing() -> None:
    """A business with no trade and no listing category gets no invented number."""
    c, sent = google(httpx.Response(200, json=TOWN), httpx.Response(200, json=IDEAS))
    with c:
        found = demand_for(
            ["", "   "],
            "Oakville",
            customer_id="123",
            access_token="a",
            developer_token="d",
            client=c,
        )

    assert found.read is False
    assert sent == []
