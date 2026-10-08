"""Reading a merchant's own Google Ads account.

These are the four checks the free audit cannot see, so the numbers have to be
right and a refusal on one must not take the others down with it.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

from ppcway.ads.stats import read_account

REFUSED = {
    "error": {
        "code": 403,
        "message": "The caller does not have permission",
        "details": [
            {
                "errors": [
                    {
                        "errorCode": {
                            "authorizationError": "CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION"
                        },
                        "message": "only approved for test accounts",
                    }
                ]
            }
        ],
    }
}


def account(answer: Callable[[str, int], httpx.Response]) -> httpx.Client:
    """An account where every query is answered by `answer(query, page)`."""

    pages: dict[str, int] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        query = body["query"]
        which = next(
            w
            for w in (
                "FROM customer",
                "search_term_view",
                "keyword_view",
                "FROM campaign",
                "ad_group_ad",
            )
            if w in query
        )
        pages[which] = pages.get(which, 0) + 1
        return answer(which, pages[which])

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")


def ok(results: list[dict[str, object]], next_page: str = "") -> httpx.Response:
    body: dict[str, object] = {"results": results}
    if next_page:
        body["nextPageToken"] = next_page
    return httpx.Response(200, json=body)


def test_no_page_size_is_sent() -> None:
    """v25 refuses the whole query if a page size is set, which cost a live run."""
    bodies: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return ok([])

    with httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x") as c:
        read_account("2580586343", access_token="a", developer_token="d", client=c)

    assert bodies, "no query was sent"
    assert all("pageSize" not in body for body in bodies)


def test_a_refused_spend_read_is_not_shown_as_a_month_of_nothing() -> None:
    """Zero spend and an unread account look identical in a total, and only one
    of them is good news."""

    def answer(which: str, page: int) -> httpx.Response:
        return httpx.Response(403, json=REFUSED)

    with account(answer) as c:
        reading = read_account("2580586343", access_token="a", developer_token="d", client=c)

    assert reading.spend.read is False
    assert reading.spend.trouble
    assert reading.as_dict()["spend"]["read"] is False


def test_a_month_of_spend_becomes_the_sentence_before_the_numbers() -> None:
    def answer(which: str, page: int) -> httpx.Response:
        if which == "FROM customer":
            return ok(
                [
                    {
                        "metrics": {
                            "costMicros": "47180000",
                            "clicks": 603,
                            "impressions": 13400,
                            "conversions": 12.0,
                        },
                        "customer": {"currencyCode": "CAD"},
                    }
                ]
            )
        return ok([])

    with account(answer) as c:
        reading = read_account("2580586343", access_token="a", developer_token="d", client=c)

    assert reading.spend.read is True
    assert reading.spend.cost == 47.18
    assert reading.spend.currency == "CAD"
    assert reading.spend.cost_per_click == 0.08
    assert reading.spend.cost_per_conversion == 3.93


def test_a_search_that_converted_is_not_called_waste() -> None:
    """The whole claim rests on this: money spent that brought nothing back."""

    def answer(which: str, page: int) -> httpx.Response:
        if which == "search_term_view":
            return ok(
                [
                    {
                        "searchTermView": {"searchTerm": "plumber oakville"},
                        "metrics": {"costMicros": "9000000", "clicks": 30, "conversions": 2.0},
                    },
                    {
                        "searchTermView": {"searchTerm": "plumber salary"},
                        "metrics": {"costMicros": "4500000", "clicks": 15, "conversions": 0.0},
                    },
                    {
                        "searchTermView": {"searchTerm": "free plumbing course"},
                        "metrics": {"costMicros": "2500000", "clicks": 9, "conversions": 0.0},
                    },
                ]
            )
        return ok([])

    with account(answer) as c:
        reading = read_account("2580586343", access_token="a", developer_token="d", client=c)

    assert [row.term for row in reading.wasted.rows] == ["plumber salary", "free plumbing course"]
    assert reading.wasted_cost == 7.0
    assert reading.wasted.read is True


def test_every_page_of_search_terms_is_read() -> None:
    """A page we never ask for is spend we never report."""

    def answer(which: str, page: int) -> httpx.Response:
        if which != "search_term_view":
            return ok([])
        term = {
            "searchTermView": {"searchTerm": f"term {page}"},
            "metrics": {"costMicros": "1000000", "clicks": 1, "conversions": 0.0},
        }
        return ok([term], next_page="more" if page < 3 else "")

    with account(answer) as c:
        reading = read_account("2580586343", access_token="a", developer_token="d", client=c)

    assert [row.term for row in reading.wasted.rows] == ["term 1", "term 2", "term 3"]
    assert reading.wasted_cost == 3.0


def test_impression_share_is_shown_as_a_percentage() -> None:
    def answer(which: str, page: int) -> httpx.Response:
        if which == "FROM campaign":
            return ok(
                [
                    {
                        "campaign": {"name": "Emergency plumbing"},
                        "metrics": {
                            "costMicros": "30000000",
                            "searchBudgetLostImpressionShare": 0.3421,
                            "searchRankLostImpressionShare": 0.1,
                            "searchImpressionShare": 0.5579,
                        },
                    }
                ]
            )
        return ok([])

    with account(answer) as c:
        reading = read_account("2580586343", access_token="a", developer_token="d", client=c)

    [row] = reading.share.rows
    assert (row.lost_to_budget, row.lost_to_rank, row.impression_share) == (34.2, 10.0, 55.8)


def test_one_refusal_does_not_take_the_other_checks_down() -> None:
    """An account can be readable for spend and refused for search terms. The
    report still goes out, saying which part is missing and why."""

    def answer(which: str, page: int) -> httpx.Response:
        if which == "search_term_view":
            return httpx.Response(403, json=REFUSED)
        if which == "FROM customer":
            return ok([{"metrics": {"costMicros": "10000000", "clicks": 100}}])
        return ok([])

    with account(answer) as c:
        reading = read_account("2580586343", access_token="a", developer_token="d", client=c)

    assert reading.spend.cost == 10.0
    assert reading.wasted.read is False
    assert "approval" in reading.wasted.trouble
    assert reading.wasted.rows == []
    assert reading.share.read is True


def test_the_report_shape_carries_both_the_numbers_and_the_reasons() -> None:
    def answer(which: str, page: int) -> httpx.Response:
        if which == "ad_group_ad":
            return ok(
                [
                    {
                        "campaign": {"name": "Emergency plumbing"},
                        "adGroup": {"name": "Burst pipe"},
                        "adGroupAd": {"policySummary": {"approvalStatus": "DISAPPROVED"}},
                    }
                ]
            )
        if which == "keyword_view":
            return httpx.Response(403, json=REFUSED)
        return ok([])

    with account(answer) as c:
        shape = read_account(
            "2580586343", access_token="a", developer_token="d", client=c
        ).as_dict()

    assert shape["customer_id"] == "2580586343"
    assert shape["window_days"] == 30
    assert shape["rejected"]["rows"][0]["status"] == "DISAPPROVED"
    assert shape["keywords"]["read"] is False
    assert shape["keywords"]["trouble"]
