"""What we show when Google refuses to describe an account.

A merchant who sees a row of bare numbers has no idea whether the problem is
theirs or ours. Google always says why; these tests hold us to passing that on.
"""

from __future__ import annotations

import httpx

from ppcway.ads.accounts import accessible_accounts

LIST_URL = "/v25/customers:listAccessibleCustomers"


def refusal(code: str) -> httpx.Response:
    return httpx.Response(
        403,
        json={
            "error": {
                "code": 403,
                "message": "The caller does not have permission",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.ads.googleads.v25.errors.GoogleAdsFailure",
                        "errors": [
                            {"errorCode": {"authorizationError": code}, "message": "Google's words"}
                        ],
                    }
                ],
            }
        },
    )


def ads_api(answers: dict[str, httpx.Response]) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == LIST_URL:
            return httpx.Response(
                200,
                json={"resourceNames": [f"customers/{cid}" for cid in answers]},
            )
        return answers[request.url.path.split("/")[3]]

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")


def test_an_account_awaiting_googles_approval_says_so_instead_of_appearing_blank() -> None:
    with ads_api({"2580586343": refusal("CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION")}) as c:
        [account] = accessible_accounts(access_token="a", developer_token="d", client=c)
    assert account.readable is False
    assert "approval" in account.trouble
    assert "Test accounts work today" in account.trouble


def test_an_account_not_switched_on_says_to_finish_setting_it_up() -> None:
    with ads_api({"2965552648": refusal("CUSTOMER_NOT_ENABLED")}) as c:
        [account] = accessible_accounts(access_token="a", developer_token="d", client=c)
    assert account.readable is False
    assert "not switched on" in account.trouble


def test_an_account_we_can_read_carries_its_name_and_no_trouble() -> None:
    described = httpx.Response(
        200,
        json={
            "results": [
                {
                    "customer": {
                        "descriptiveName": "Byte9",
                        "currencyCode": "CAD",
                        "timeZone": "America/Toronto",
                        "manager": False,
                    }
                }
            ]
        },
    )
    with ads_api({"2580586343": described}) as c:
        [account] = accessible_accounts(access_token="a", developer_token="d", client=c)
    assert (account.name, account.currency, account.readable, account.trouble) == (
        "Byte9",
        "CAD",
        True,
        "",
    )


def test_listing_never_carries_somebody_elses_manager_id() -> None:
    """A manager id from another Google account turns a real reason into a
    permission error, which is a day lost. The listing is asked plainly."""
    seen: list[str | None] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("login-customer-id"))
        if request.url.path == LIST_URL:
            return httpx.Response(200, json={"resourceNames": ["customers/2580586343"]})
        return refusal("CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION")

    with httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x") as c:
        accessible_accounts(
            access_token="a", developer_token="d", login_customer_id="4269106223", client=c
        )
    assert seen[0] is None, "the listing must not be asked under a manager"
    assert seen[1] is None, "an account is asked for plainly before any manager is tried"
