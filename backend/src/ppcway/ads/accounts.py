"""Which advertising accounts a connected merchant has.

One call to the Google Ads API, `listAccessibleCustomers`, then one search per
customer for its name. Both are reads. Nothing here mutates anything, and the
developer token decides what is reachable at all: a test-tier token reaches test
accounts only, which is the state the client's token is in today.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from ppcway.ads.oauth import AdsConnectionRefused

log = logging.getLogger(__name__)

API = "https://googleads.googleapis.com"


@dataclass(frozen=True)
class AdsAccount:
    customer_id: str
    name: str
    is_manager: bool
    currency: str
    time_zone: str
    #: False when Google refused to read it, with `trouble` saying why in plain words.
    readable: bool = True
    trouble: str = ""


#: Google's error codes, in words a plumber can act on. Anything unlisted is passed
#: through as Google wrote it, which is better than a shrug.
TROUBLE = {
    "CUSTOMER_NOT_ENABLED": "Google says this account is not switched on yet. Finish setting it up in Google Ads.",
    "CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION": "We are waiting on Google's approval to read live accounts. Test accounts work today.",
    "DEVELOPER_TOKEN_NOT_APPROVED": "We are waiting on Google's approval to read live accounts. Test accounts work today.",
    "USER_PERMISSION_DENIED": "This account is managed by somebody else. Its manager has to allow the connection.",
    "CUSTOMER_NOT_FOUND": "Google no longer has this account.",
}


def _plain(reply: httpx.Response) -> str:
    """What went wrong, said once, in the words the screen will show."""
    try:
        errors = (reply.json().get("error", {}).get("details") or [{}])[0].get("errors", [])
        for error in errors:
            for code in (error.get("errorCode") or {}).values():
                if code in TROUBLE:
                    return TROUBLE[code]
            if error.get("message"):
                return str(error["message"])
    except (ValueError, AttributeError, IndexError):
        pass
    return "Google would not let us read this account."


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


def _why(response: httpx.Response) -> str:
    """Google's own words for a refusal, which name the real problem."""
    try:
        body = response.json()
        error = body.get("error", {})
        detail = error.get("message", "")
        inner = error.get("details", [])
        if inner:
            detail += " | " + str(inner)[:300]
        return f"{response.status_code}: {detail or str(body)[:200]}"
    except ValueError:
        return f"{response.status_code}: {response.reason_phrase}"


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
        # Listing is about the person, not about any manager, so it is asked plainly.
        listed = c.get(
            f"{API}/{api_version}/customers:listAccessibleCustomers",
            headers=_headers(access_token, developer_token, None),
        )
        if listed.status_code != 200:
            raise _refusal(listed)
        names: list[AdsAccount] = []
        for resource in listed.json().get("resourceNames", []):
            customer_id = resource.rsplit("/", 1)[-1]
            names.append(
                _describe(
                    customer_id,
                    access_token=access_token,
                    developer_token=developer_token,
                    login_customer_id=login_customer_id,
                    api_version=api_version,
                    client=c,
                )
            )
        return names
    finally:
        if own:
            c.close()


def _describe(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None,
    api_version: str,
    client: httpx.Client,
) -> AdsAccount:
    """The account's own description, or just its number when Google will not say.

    A manager account cannot always read its own siblings, and a developer token
    at test tier cannot read a production account at all, so one refusal here is
    not a reason to fail the whole list. It is written to the log, though: a row
    of bare numbers with no explanation is the kind of silence that wastes a day.
    """
    query = {
        "query": (
            "SELECT customer.descriptive_name, customer.currency_code, "
            "customer.time_zone, customer.manager FROM customer LIMIT 1"
        )
    }

    def ask(manager: str | None) -> httpx.Response:
        return client.post(
            f"{API}/{api_version}/customers/{customer_id}/googleAds:search",
            headers=_headers(access_token, developer_token, manager),
            json=query,
        )

    # An account somebody owns outright is asked for plainly. Only if Google says
    # the permission is missing is it asked again under the manager, which is what
    # a client account under a manager needs and what an owned one must not have.
    reply = ask(None)
    if reply.status_code != 200 and login_customer_id and "USER_PERMISSION_DENIED" in reply.text:
        reply = ask(login_customer_id)
    if reply.status_code != 200:
        log.warning("Google would not describe customer %s: %s", customer_id, _why(reply))
        return AdsAccount(
            customer_id=customer_id,
            name="",
            is_manager=False,
            currency="",
            time_zone="",
            readable=False,
            trouble=_plain(reply),
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
