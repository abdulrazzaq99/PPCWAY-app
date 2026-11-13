"""Uploading jobs as conversions: the request Google gets, and its answer read right.

Google answers an upload the way it answers a mutate with partial failure: one
result per conversion, and the refusals separately, each naming the index of
the conversion it was about -- under `conversions` this time, not `operations`.
Read under the wrong name, every refusal would land on the first job.
"""

from __future__ import annotations

import json

import httpx

from ppcway.gateway.google import GoogleDoor, Keys


def test_an_upload_is_sent_with_partial_failure_and_refusals_land_on_their_job() -> None:
    seen: list[httpx.Request] = []

    def google(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "results": [{"gclid": "a"}, {}, {"gclid": "c"}],
                "partialFailureError": {
                    "message": "one refused",
                    "details": [
                        {
                            "errors": [
                                {
                                    "errorCode": {"conversionUploadError": "TOO_RECENT_EVENT"},
                                    "message": "The click is too recent.",
                                    "location": {
                                        "fieldPathElements": [
                                            {"fieldName": "conversions", "index": 1}
                                        ]
                                    },
                                }
                            ]
                        }
                    ],
                },
            },
        )

    door = GoogleDoor(
        Keys(access_token="t", developer_token="d", login_customer_id="999"),
        client=httpx.Client(transport=httpx.MockTransport(google)),
    )
    jobs = tuple({"gclid": g, "conversionAction": "customers/1/conversionActions/2"} for g in "abc")
    said = door.upload_clicks("1234567890", jobs)

    (request,) = seen
    assert request.url.path == "/v25/customers/1234567890:uploadClickConversions"
    assert request.headers["login-customer-id"] == "999"
    body = json.loads(request.content)
    assert body["partialFailure"] is True and len(body["conversions"]) == 3
    assert said.landed == (True, False, True)
    (refused,) = said.refused
    assert refused.at == 1
    assert refused.code == "conversionUploadError.TOO_RECENT_EVENT"
