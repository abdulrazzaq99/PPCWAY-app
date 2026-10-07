"""Which advertising accounts a connected merchant has.

One call to the Google Ads API, `listAccessibleCustomers`, then one search per
customer for its name. Both are reads. Nothing here mutates anything, and the
developer token decides what is reachable at all: a test-tier token reaches test
accounts only, which is the state the client's token is in today.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from ppcway.ads.oauth import AdsConnectionRefused

API = "https://googleads.googleapis.com"


@dataclass(frozen=True)
class AdsAccount:
    customer_id: str
    name: str
    is_manager: bool
    currency: str
    time_zone: str


def _headers(
    access_token: str, developer_token: str, login_customer_id: str | None
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
        "content-type": "application/json",
    }
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id.replace("-", "")
    return headers


def _refusal(response: httpx.Response) -> AdsConnectionRefused:
    """Google's own words, which name the real problem: an unapproved developer
    token, a customer the token cannot reach, a permission that was withdrawn."""
    try:
        body = response.json()
        detail = body.get("error", {}).get("message") or str(body)[:200]
    except ValueError:
        detail = response.reason_phrase
    return AdsConnectionRefused(f"Google Ads {response.status_code}: {detail}")


def accessible_accounts(
    *,
    access_token: str,
    developer_token: str,
    api_version: str = "v25",
    login_customer_id: str | None = None,
    client: httpx.Client | None = None,
) -> list[AdsAccount]:
    """Every account this permission can reach, with the names people recognise."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(30))
    try:
        headers = _headers(access_token, developer_token, login_customer_id)
        listed = c.get(f"{API}/{api_version}/customers:listAccessibleCustomers", headers=headers)
        if listed.status_code != 200:
            raise _refusal(listed)
        names: list[AdsAccount] = []
        for resource in listed.json().get("resourceNames", []):
            customer_id = resource.rsplit("/", 1)[-1]
            names.append(
                _describe(
                    customer_id,
                    headers=headers,
                    api_version=api_version,
                    client=c,
                )
            )
        return names
    finally:
        if own:
            c.close()


def _describe(
    customer_id: str, *, headers: dict[str, str], api_version: str, client: httpx.Client
) -> AdsAccount:
    """The account's own description, or just its number when Google will not say.

    A manager account cannot always read its own siblings, so one refusal here is
    not a reason to fail the whole list.
    """
    query = {
        "query": (
            "SELECT customer.descriptive_name, customer.currency_code, "
            "customer.time_zone, customer.manager FROM customer LIMIT 1"
        )
    }
    reply = client.post(
        f"{API}/{api_version}/customers/{customer_id}/googleAds:search",
        headers=headers,
        json=query,
    )
    if reply.status_code != 200:
        return AdsAccount(
            customer_id=customer_id, name="", is_manager=False, currency="", time_zone=""
        )
    rows = reply.json().get("results", [])
    if not rows:
        return AdsAccount(
            customer_id=customer_id, name="", is_manager=False, currency="", time_zone=""
        )
    customer = rows[0].get("customer", {})
    return AdsAccount(
        customer_id=customer_id,
        name=str(customer.get("descriptiveName", "")),
        is_manager=bool(customer.get("manager", False)),
        currency=str(customer.get("currencyCode", "")),
        time_zone=str(customer.get("timeZone", "")),
    )
