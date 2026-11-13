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

from ppcway.gateway.port import (
    Applied,
    Batch,
    Created,
    Doing,
    GoogleRefused,
    Operation,
    Refused,
    Together,
    Uploaded,
)

# Re-exported: this module raises it, and the seam defines it.
__all__ = ["API", "GoogleDoor", "GoogleRefused", "Keys"]

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
    "campaign_criterion": ("campaignCriteria", "campaignCriterionOperation"),
    "ad_group": ("adGroups", "adGroupOperation"),
    "ad_group_criterion": ("adGroupCriteria", "adGroupCriterionOperation"),
    "ad_group_ad": ("adGroupAds", "adGroupAdOperation"),
    "shared_set": ("sharedSets", "sharedSetOperation"),
    "shared_criterion": ("sharedCriteria", "sharedCriterionOperation"),
    "asset": ("assets", "assetOperation"),
    "customer_asset": ("customerAssets", "customerAssetOperation"),
    "campaign_asset": ("campaignAssets", "campaignAssetOperation"),
    "ad_group_asset": ("adGroupAssets", "adGroupAssetOperation"),
    "asset_group": ("assetGroups", "assetGroupOperation"),
    "asset_group_asset": ("assetGroupAssets", "assetGroupAssetOperation"),
    "asset_group_signal": ("assetGroupSignals", "assetGroupSignalOperation"),
    "asset_group_listing_group_filter": (
        "assetGroupListingGroupFilters",
        "assetGroupListingGroupFilterOperation",
    ),
    "asset_set": ("assetSets", "assetSetOperation"),
    "asset_set_asset": ("assetSetAssets", "assetSetAssetOperation"),
    "campaign_asset_set": ("campaignAssetSets", "campaignAssetSetOperation"),
    "campaign_conversion_goal": ("campaignConversionGoals", "campaignConversionGoalOperation"),
    "conversion_goal_campaign_config": (
        "conversionGoalCampaignConfigs",
        "conversionGoalCampaignConfigOperation",
    ),
    "campaign_shared_set": ("campaignSharedSets", "campaignSharedSetOperation"),
    "campaign_bid_modifier": ("campaignBidModifiers", "campaignBidModifierOperation"),
    "ad_group_bid_modifier": ("adGroupBidModifiers", "adGroupBidModifierOperation"),
    "audience": ("audiences", "audienceOperation"),
    "goal": ("goals", "goalOperation"),
    "campaign_goal_config": ("campaignGoalConfigs", "campaignGoalConfigOperation"),
    "conversion_action": ("conversionActions", "conversionActionOperation"),
    "customer_conversion_goal": ("customerConversionGoals", "customerConversionGoalOperation"),
}


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

    def mutate_together(self, together: Together) -> Created:
        """Several kinds of change in one request, applied whole or not at all."""
        own = self.client is None
        c = self.client or httpx.Client(timeout=httpx.Timeout(120))
        try:
            return _together(self, c, together)
        finally:
            if own:
                c.close()

    def upload_clicks(self, customer_id: str, conversions: tuple[dict[str, Any], ...]) -> Uploaded:
        """Conversions that happened away from Google, attached to their ad clicks.

        `ConversionUploadService.UploadClickConversions`, which Google only
        accepts with partial failure on: one job Google will not take (a click
        it has not seen yet, say) must not stop the rest. The answer is read
        the same way as a mutate's, one entry per conversion sent.
        """
        own = self.client is None
        c = self.client or httpx.Client(timeout=httpx.Timeout(120))
        url = f"{API}/{self.keys.api_version}/customers/{customer_id}:uploadClickConversions"
        headers = {
            "Authorization": f"Bearer {self.keys.access_token}",
            "developer-token": self.keys.developer_token,
            "content-type": "application/json",
        }
        if self.keys.login_customer_id:
            headers["login-customer-id"] = self.keys.login_customer_id
        try:
            reply = c.post(
                url,
                json={"conversions": list(conversions), "partialFailure": True},
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise GoogleRefused(f"Google could not be reached: {exc}") from None
        finally:
            if own:
                c.close()
        if reply.status_code >= 400:
            raise GoogleRefused(_why(reply))
        said = reply.json()
        refused = tuple(_refusals(said.get("partialFailureError") or {}, field="conversions"))
        failed_at = {one.at for one in refused}
        return Uploaded(
            landed=tuple(i not in failed_at for i in range(len(conversions))), refused=refused
        )

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


#: What each kind of thing is called, for a refusal a merchant reads.
_CALLED: dict[str, str] = {
    "campaign_budget": "the budget",
    "campaign": "the campaign",
    "campaign_criterion": "a campaign setting",
    "ad_group": "an ad group",
    "ad_group_criterion": "a keyword",
    "ad_group_ad": "an ad",
    "asset": "an asset",
    "campaign_asset": "an asset on the campaign",
    "customer_asset": "an account asset",
    "ad_group_asset": "an asset on an ad group",
    "asset_group": "the asset group",
    "asset_group_asset": "an asset in the asset group",
    "asset_group_signal": "a signal or search theme",
    "shared_set": "a shared list",
    "shared_criterion": "an entry in a shared list",
    "campaign_shared_set": "a shared list on the campaign",
    "campaign_conversion_goal": "a conversion goal",
    "campaign_bid_modifier": "a bid adjustment",
    "ad_group_bid_modifier": "a bid adjustment",
    "audience": "an audience",
}


def problems_in(reply: httpx.Response, together: Together) -> list[dict[str, Any]]:
    """Every error Google gave for an all-or-nothing request, not only the first.

    Google's own review screen lists every problem with a way to fix each, and
    a validate-only call returns them all at once; a merchant shown one at a
    time fixes one, presses again, and meets the next. Each comes back with
    the operation it was about, so the screen can send them to the right step.
    """
    try:
        said = reply.json()
    except ValueError:
        return []
    out: list[dict[str, Any]] = []
    for detail in (said.get("error") or {}).get("details") or []:
        for failure in (detail.get("errors") or []) if isinstance(detail, dict) else []:
            message = str(failure.get("message") or "")
            if not message:
                continue
            at: int | None = None
            path: list[str] = []
            for part in (failure.get("location") or {}).get("fieldPathElements") or []:
                name = str(part.get("fieldName") or "")
                if name in {"mutate_operations", "mutateOperations"} and at is None:
                    raw = part.get("index")
                    at = raw if isinstance(raw, int) else None
                    continue
                if name:
                    path.append(name)
            op = together.operations[at] if at is not None and at < together.how_many else None
            out.append(
                {
                    "at": at,
                    "resource_type": op.resource_type if op else "",
                    "about": _about(op) if op else "the campaign",
                    "field": ".".join(path),
                    "code": _code_of(failure.get("errorCode") or {}),
                    "message": message,
                    "trigger": str((failure.get("trigger") or {}).get("stringValue") or ""),
                }
            )
    return out


def _together(door: GoogleDoor, c: httpx.Client, together: Together) -> Created:
    """Send a `Together` to the account-wide mutate, all or nothing."""
    url = f"{API}/{door.keys.api_version}/customers/{together.customer_id}/googleAds:mutate"
    body: dict[str, Any] = {
        "mutateOperations": [
            {_SERVICE[op.resource_type][1]: _operation(op)} for op in together.operations
        ],
        "partialFailure": False,
        "validateOnly": together.validate_only,
    }
    headers = {
        "Authorization": f"Bearer {door.keys.access_token}",
        "developer-token": door.keys.developer_token,
        "content-type": "application/json",
    }
    if door.keys.login_customer_id:
        headers["login-customer-id"] = door.keys.login_customer_id
    try:
        reply = c.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise GoogleRefused(f"Google could not be reached: {exc}") from None
    if reply.status_code >= 400:
        refused = GoogleRefused(_why_together(reply, together))
        refused.problems = problems_in(reply, together)
        raise refused
    if together.validate_only:
        return Created(names=(), checked_only=True)

    names: list[str] = []
    for answer in (reply.json() or {}).get("mutateOperationResponses") or []:
        result = next(
            (v for k, v in answer.items() if k.endswith("Result") and isinstance(v, dict)), {}
        )
        names.append(str(result.get("resourceName", "")))
    if len(names) != together.how_many or not all(names):
        # All or nothing means Google applied it, so the names are owed. A
        # short answer is recorded as what it is rather than guessed at.
        log.warning("Google created %d of %d without naming them", len(names), together.how_many)
    return Created(names=tuple(names))


def _why_together(reply: httpx.Response, together: Together) -> str:
    """Google's refusal of an all-or-nothing request, naming the part it was about."""
    try:
        said = reply.json()
    except ValueError:
        return f"Google refused the request: {reply.status_code}"
    error = said.get("error") or {}
    for detail in error.get("details") or []:
        for failure in (detail.get("errors") or []) if isinstance(detail, dict) else []:
            message = str(failure.get("message") or "")
            if not message:
                continue
            code = _code_of(failure.get("errorCode") or {})
            at = None
            for part in (failure.get("location") or {}).get("fieldPathElements") or []:
                if part.get("fieldName") in {"mutate_operations", "mutateOperations"}:
                    at = part.get("index")
                    break
            about = ""
            if isinstance(at, int) and 0 <= at < together.how_many:
                about = _about(together.operations[at])
            return f"Google refused {about or 'the campaign'}: {message} ({code})"
    return f"Google refused the request: {reply.status_code} {error.get('message', '')}".strip()


def _about(op: Operation) -> str:
    """Which part of a campaign one operation is, in words."""
    called = _CALLED.get(op.resource_type, op.resource_type.replace("_", " "))
    keyword = (op.fields.get("keyword") or {}).get("text")
    if keyword:
        return f'{called} "{keyword}"'
    name = op.fields.get("name")
    if name:
        return f'{called} "{name}"'
    return called


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

    Google answers a partial-failure request with one result per operation, at
    the same index, and an *empty* result where the operation failed -- its own
    client libraries say so, and skip empty results when reading them. The
    indexes of what failed are in `partialFailureError.details`.

    Until 5 November this read `results` as short when operations failed and
    walked it past each failure, which misplaces every result after the first
    one refused: refuse the first of two, and the second -- which landed -- was
    recorded as not landed, with its id lost. Both shapes are read now, by
    position when the list is full length and by skipping when it is short.
    """
    refused = tuple(_refusals(said.get("partialFailureError") or {}))
    failed_at = {one.at for one in refused}

    results = said.get("results") or []
    if len(results) == how_many:
        by_place: list[str | None] = []
        for i, got in enumerate(results):
            name = got.get("resourceName") if isinstance(got, dict) else None
            by_place.append(None if i in failed_at or not name else str(name))
        return Applied(landed=tuple(by_place), refused=refused, operations_used=how_many)

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


def _refusals(error: dict[str, Any], *, field: str = "operations") -> list[Refused]:
    """Every operation Google named as refused, with the index it was at.

    `field` is the list the index points into: `operations` for a mutate,
    `conversions` for an upload.
    """
    out: list[Refused] = []
    for detail in error.get("details") or []:
        for failure in detail.get("errors") or []:
            at = _index_of(failure.get("location") or {}, field=field)
            code = _code_of(failure.get("errorCode") or {})
            out.append(
                Refused(
                    at=at if at is not None else 0,
                    code=code,
                    message=str(failure.get("message", "")),
                )
            )
    return out


def _index_of(location: dict[str, Any], *, field: str = "operations") -> int | None:
    """Which operation this error was about.

    Google reports it as a list of field path elements, one of which carries
    the index. Read by name rather than by position, because the path has more
    elements for a nested field and the index is not always first.
    """
    for part in location.get("fieldPathElements") or []:
        if part.get("fieldName") == field and "index" in part:
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
    # The top message is often "Request contains an invalid argument." and the
    # reason is underneath, in Google's own failure detail. The first one is
    # what a person needs: "The developer token is not approved", say.
    for detail in error.get("details") or []:
        for failure in (detail.get("errors") or []) if isinstance(detail, dict) else []:
            why = str(failure.get("message") or "")
            code = _code_of(failure.get("errorCode") or {})
            if why:
                return f"Google refused the request: {reply.status_code} {why} ({code})"
    return f"Google refused the request: {reply.status_code} {message}"
