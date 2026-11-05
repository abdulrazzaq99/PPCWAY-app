"""The real door, against Google's own answer shapes, over a fake transport.

Nothing here reaches Google. The transport records the request and returns
what Google's REST interface returns, so these hold the two things that only
show up in production otherwise: the request is the one Google takes, and the
answer is read the way Google means it.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from ppcway.gateway.google import GoogleDoor, GoogleRefused, Keys
from ppcway.gateway.port import Batch, Doing, Operation

CUSTOMER = "2580586343"


def _exclusions(*groups: str) -> Batch:
    return Batch(
        customer_id=CUSTOMER,
        operations=tuple(
            Operation(
                resource_type="ad_group_criterion",
                doing=Doing.CREATE,
                fields={
                    "adGroup": f"customers/{CUSTOMER}/adGroups/{g}",
                    "negative": True,
                    "keyword": {"text": "pdf to word", "matchType": "EXACT"},
                },
            )
            for g in groups
        ),
    )


def _door(answer: dict[str, Any], status: int = 200) -> tuple[GoogleDoor, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=answer)

    keys = Keys(access_token="access", developer_token="developer", login_customer_id="1112223333")
    return GoogleDoor(keys, client=httpx.Client(transport=httpx.MockTransport(reply))), seen


def _refusal(at: int, message: str) -> dict[str, Any]:
    return {
        "errors": [
            {
                "errorCode": {"criterionError": "KEYWORD_HAS_INVALID_CHARS"},
                "message": message,
                "location": {"fieldPathElements": [{"fieldName": "operations", "index": at}]},
            }
        ]
    }


def test_an_exclusion_is_sent_where_and_how_google_takes_it() -> None:
    door, seen = _door(
        {"results": [{"resourceName": f"customers/{CUSTOMER}/adGroupCriteria/21~9"}]}
    )
    said = door.mutate(_exclusions("21"))
    (request,) = seen
    assert str(request.url) == (
        f"https://googleads.googleapis.com/v25/customers/{CUSTOMER}/adGroupCriteria:mutate"
    )
    assert request.headers["developer-token"] == "developer"
    assert request.headers["login-customer-id"] == "1112223333"
    body = json.loads(request.content)
    assert body["partialFailure"] is True
    assert body["validateOnly"] is False
    assert body["operations"] == [
        {
            "create": {
                "adGroup": f"customers/{CUSTOMER}/adGroups/21",
                "negative": True,
                "keyword": {"text": "pdf to word", "matchType": "EXACT"},
            }
        }
    ]
    assert said.all_landed
    assert said.landed == (f"customers/{CUSTOMER}/adGroupCriteria/21~9",)


def test_a_refused_first_operation_does_not_lose_the_second() -> None:
    """Google answers one result per operation, empty where it failed. Read as
    a short list, the second -- which landed -- was recorded as not landing,
    and the id an undo needs was lost."""
    made = f"customers/{CUSTOMER}/adGroupCriteria/22~9"
    door, _seen = _door(
        {
            "results": [{}, {"resourceName": made}],
            "partialFailureError": {
                "code": 3,
                "message": "bad keyword",
                "details": [_refusal(0, "The keyword has invalid characters.")],
            },
        }
    )
    said = door.mutate(_exclusions("21", "22"))
    assert said.landed == (None, made)
    assert [(r.at, r.code) for r in said.refused] == [
        (0, "criterionError.KEYWORD_HAS_INVALID_CHARS")
    ]
    assert said.how_many_landed == 1
    assert not said.all_landed


def test_a_short_list_of_results_is_still_read() -> None:
    """The shape this was first written for, kept in case it is ever sent."""
    made = f"customers/{CUSTOMER}/adGroupCriteria/22~9"
    door, _seen = _door(
        {
            "results": [{"resourceName": made}],
            "partialFailureError": {"details": [_refusal(0, "no")]},
        }
    )
    assert door.mutate(_exclusions("21", "22")).landed == (None, made)


def test_a_whole_refusal_says_google_s_own_reason() -> None:
    """The top message is "Request contains an invalid argument."; the reason
    a person can act on is underneath it."""
    door, _seen = _door(
        {
            "error": {
                "code": 403,
                "message": "The caller does not have permission",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.ads.googleads.v25.errors.GoogleAdsFailure",
                        "errors": [
                            {
                                "errorCode": {"authorizationError": "DEVELOPER_TOKEN_NOT_APPROVED"},
                                "message": "The developer token is not approved.",
                            }
                        ],
                    }
                ],
            }
        },
        status=403,
    )
    with pytest.raises(GoogleRefused) as refused:
        door.mutate(_exclusions("21"))
    assert "The developer token is not approved." in str(refused.value)
    assert "authorizationError.DEVELOPER_TOKEN_NOT_APPROVED" in str(refused.value)
