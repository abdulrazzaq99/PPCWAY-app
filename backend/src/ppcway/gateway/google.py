"""The real door: one HTTP call, and what Google's answer actually means.

The only module in this codebase that sends a mutation to Google. Everything
else proposes, records, judges and reports; this is the sentence at the end.

**Partial failure is read, not assumed.** Google's answer to a
`partialFailure` request carries a `results` list and, separately, a
`partialFailureError` whose details name the index of each operation it
refused. A caller that read only `results` would see a short list and have no
way to tell which of its operations was missing -- so this reassembles both
into one entry per operation sent, at the same index, which is the invariant
`Applied` is built around.

**A refusal is not an exception.** Google answering "I applied nine of your ten
keywords and here is why the tenth failed" is a successful request with a
partial result, and raising on it would throw away the nine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from ppcway.gateway.port import Applied, Batch, Doing, Refused

log = logging.getLogger(__name__)

API = "https://googleads.googleapis.com"

#: The field Google wants each operation under, by what we are doing.
_UNDER = {Doing.CREATE: "create", Doing.UPDATE: "update", Doing.REMOVE: "remove"}

#: The mutate endpoint per resource type, which is not the same as the
#: resource's own URL path: `adGroupCriteria` are mutated at
#: `adGroupCriteria:mutate`, and the operation key inside differs again.
_SERVICE = {
    "campaign": ("campaigns", "campaignOperation"),
    "campaign_budget": ("campaignBudgets", "campaignBudgetOperation"),
    "ad_group": ("adGroups", "adGroupOperation"),
    "ad_group_criterion": ("adGroupCriteria", "adGroupCriterionOperation"),
    "ad_group_ad": ("adGroupAds", "adGroupAdOperation"),
    "shared_set": ("sharedSets", "sharedSetOperation"),
    "shared_criterion": ("sharedCriteria", "sharedCriterionOperation"),
}


class GoogleRefused(RuntimeError):
    """Google would not take the request at all, as opposed to part of it."""


@dataclass(frozen=True, slots=True)
class Keys:
    """What one call to Google needs. Held by this package and nowhere else."""

    access_token: str
    developer_token: str
    login_customer_id: str | None = None
    api_version: str = "v25"


@dataclass(frozen=True, slots=True)
class GoogleDoor:
    """The one door. Constructed where the credentials are, used nowhere else."""

    keys: Keys
    client: httpx.Client | None = None

    def mutate(self, batch: Batch) -> Applied:
        own = self.client is None
        c = self.client or httpx.Client(timeout=httpx.Timeout(120))
        try:
            return self._send(c, batch)
        finally:
            if own:
                c.close()

    def _send(self, c: httpx.Client, batch: Batch) -> Applied:
        service, _key = _SERVICE[batch.operations[0].resource_type]
        url = f"{API}/{self.keys.api_version}/customers/{batch.customer_id}/{service}:mutate"
        body: dict[str, Any] = {
            "operations": [_operation(op) for op in batch.operations],
            "partialFailure": batch.partial_failure,
            "validateOnly": batch.validate_only,
        }
        headers = {
            "Authorization": f"Bearer {self.keys.access_token}",
            "developer-token": self.keys.developer_token,
            "content-type": "application/json",
        }
        if self.keys.login_customer_id:
            headers["login-customer-id"] = self.keys.login_customer_id

        try:
            reply = c.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise GoogleRefused(f"Google could not be reached: {exc}") from None

        if reply.status_code >= 400:
            # The whole request was refused. Nothing landed, and the operations
            # still counted against quota, which the caller has already
            # recorded -- see `quota.spend` on why it counts before sending.
            raise GoogleRefused(_why(reply))

        return _read(reply.json(), batch.how_many)


def _operation(op: Any) -> dict[str, Any]:
    """One operation, in the shape Google's mutate endpoint takes."""
    inner: dict[str, Any] = dict(op.fields)
    if op.resource_name:
        inner["resourceName"] = op.resource_name
    out: dict[str, Any] = {_UNDER[op.doing]: inner}
    if op.doing is Doing.REMOVE:
        # A remove is the resource name alone, not an object containing it.
        out = {"remove": op.resource_name}
    if op.doing is Doing.UPDATE:
        out["updateMask"] = ",".join(op.update_mask)
    return out


def _read(said: dict[str, Any], how_many: int) -> Applied:
    """Google's answer, reassembled into one entry per operation sent.

    `results` is positional and short when operations failed, so it cannot be
    zipped with the operations directly. The indexes of what failed are in
    `partialFailureError.details`, and this builds the aligned list from both.
    """
    refused = tuple(_refusals(said.get("partialFailureError") or {}))
    failed_at = {one.at for one in refused}

    results = said.get("results") or []
    landed: list[str | None] = []
    took = iter(results)
    for i in range(how_many):
        if i in failed_at:
            landed.append(None)
            continue
        got = next(took, None)
        name = (got or {}).get("resourceName") if isinstance(got, dict) else None
        # Google returned fewer results than we sent and said nothing about
        # the rest. Recorded as not landed rather than assumed landed: the
        # expensive mistake here is believing a change was made.
        landed.append(str(name) if name else None)

    return Applied(landed=tuple(landed), refused=refused, operations_used=how_many)


def _refusals(error: dict[str, Any]) -> list[Refused]:
    """Every operation Google named as refused, with the index it was at."""
    out: list[Refused] = []
    for detail in error.get("details") or []:
        for failure in detail.get("errors") or []:
            at = _index_of(failure.get("location") or {})
            code = _code_of(failure.get("errorCode") or {})
            out.append(
                Refused(
                    at=at if at is not None else 0,
                    code=code,
                    message=str(failure.get("message", "")),
                )
            )
    return out


def _index_of(location: dict[str, Any]) -> int | None:
    """Which operation this error was about.

    Google reports it as a list of field path elements, one of which carries
    the index. Read by name rather than by position, because the path has more
    elements for a nested field and the index is not always first.
    """
    for part in location.get("fieldPathElements") or []:
        if part.get("fieldName") == "operations" and "index" in part:
            try:
                return int(part["index"])
            except (TypeError, ValueError):
                return None
    return None


def _code_of(code: dict[str, Any]) -> str:
    """Google's error code, whichever of its many families it came from."""
    for family, value in code.items():
        if isinstance(value, str):
            return f"{family}.{value}"
    return "unknown"


def _why(reply: httpx.Response) -> str:
    """Google's refusal of a whole request, in words a log reader can act on."""
    try:
        said = reply.json()
    except ValueError:
        return f"Google refused the request: {reply.status_code}"
    error = said.get("error") or {}
    message = error.get("message") or reply.text[:200]
    return f"Google refused the request: {reply.status_code} {message}"
