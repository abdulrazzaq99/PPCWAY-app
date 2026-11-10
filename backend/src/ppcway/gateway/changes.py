"""What an approved change sends to Google, built from what the log says it is.

A rule writes its change into the log as plain data -- `payload` -- when it is
proposed, because a rule may not reach this package and because what reaches
Google has to be what the merchant was shown, not whatever a rule would find on
the day the change is sent. This turns that data into a `Batch`, and it is the
only place that knows the shape Google's mutate endpoints take for each kind of
change.

Three changes exist, which is everything R1 and R4 propose and everything an
undo of either needs:

- `exclude_search` -- the search, as an exact-match negative keyword, in every
  ad group it was answered from. Exact is the narrowest exclusion there is: it
  stops that search and nothing else.
- `set_ad_status` -- one ad paused, or put back to what it was.
- `remove_exclusions` -- the negative keywords an earlier change created,
  removed by the ids Google gave them.

**Nothing outside the account is sent.** Every resource a change names has to
belong to the account the row is for. The guardrails' scope check compares
account ids; this compares the resource names themselves, which is the thing
Google will actually act on, so a payload that named another merchant's ad
group would be refused here even if every id beside it matched.
"""

from __future__ import annotations

from typing import Any, Final

from ppcway.gateway.port import Batch, Doing, Operation
from ppcway.opt.models import OptimizationAction

#: The match types a negative keyword can have, as Google spells them.
MATCH_TYPES: Final = frozenset({"EXACT", "PHRASE", "BROAD"})

#: The statuses an ad can be set to. REMOVED is not one: removing an ad cannot
#: be put back, and nothing here offers a change that cannot.
AD_STATUSES: Final = frozenset({"ENABLED", "PAUSED"})


class Unsendable(ValueError):
    """The log does not describe a change this gateway can send. Nothing is."""


def batch_for(action: OptimizationAction) -> Batch:
    """The request that makes this change, for this account and nothing else."""
    sent: dict[str, Any] = dict(action.payload or {})
    change = sent.get("change")
    if not change:
        raise Unsendable(
            "This change was written down before PPCWay recorded what to send for it,"
            " so nothing was sent."
        )
    if change == "exclude_search":
        operations = _exclusions(sent)
    elif change == "set_ad_status":
        operations = (_ad_status(sent),)
    elif change == "set_budget":
        operations = (_budget(sent),)
    elif change == "remove_exclusions":
        operations = _removals(sent)
    else:
        raise Unsendable(f"PPCWay does not know how to send a {change!r} change.")

    _all_in(action.customer_id, operations)
    return Batch(
        customer_id=action.customer_id,
        operations=operations,
        idempotency_key=action.idempotency_key,
    )


def done_words(action: OptimizationAction) -> str:
    """What was done, in a sentence, for the merchant who asked for it."""
    sent = action.payload or {}
    change = sent.get("change")
    if change == "exclude_search":
        groups = len(sent.get("ad_groups") or [])
        where = "" if groups <= 1 else f" in all {groups} ad groups it showed up in"
        return f'Searches for "{sent.get("text", "")}" no longer show your ads{where}.'
    if change == "remove_exclusions":
        return f'Searches for "{action.target_label}" can show your ads again.'
    if change == "set_ad_status":
        if str(sent.get("status")) == "PAUSED":
            return "The ad is paused."
        return "The ad is back on."
    if change == "set_budget":
        amount = int(sent.get("amount_micros") or 0) / 1_000_000
        return f"The daily budget of {action.target_label} is now {amount:,.2f}."
    return "The change is made."


def _exclusions(sent: dict[str, Any]) -> tuple[Operation, ...]:
    text = str(sent.get("text") or "").strip()
    match = str(sent.get("match_type") or "")
    groups = [str(g) for g in (sent.get("ad_groups") or []) if g]
    if not text:
        raise Unsendable("The change names no search to exclude.")
    if match not in MATCH_TYPES:
        raise Unsendable(f"{match!r} is not a match type Google has.")
    if not groups:
        raise Unsendable("The change names no ad group to exclude the search from.")
    return tuple(
        Operation(
            resource_type="ad_group_criterion",
            doing=Doing.CREATE,
            fields={
                "adGroup": group,
                "negative": True,
                "keyword": {"text": text, "matchType": match},
            },
        )
        for group in dict.fromkeys(groups)
    )


def _ad_status(sent: dict[str, Any]) -> Operation:
    ad = str(sent.get("ad") or "")
    status = str(sent.get("status") or "")
    if not ad:
        raise Unsendable("The change names no ad.")
    if status not in AD_STATUSES:
        raise Unsendable(f"An ad cannot be set to {status!r} from here.")
    return Operation(
        resource_type="ad_group_ad",
        doing=Doing.UPDATE,
        resource_name=ad,
        fields={"status": status},
        update_mask=("status",),
    )


def _budget(sent: dict[str, Any]) -> Operation:
    """A campaign budget's daily amount, and nothing else about it."""
    budget = str(sent.get("budget") or "")
    amount = sent.get("amount_micros")
    if "/campaignBudgets/" not in budget:
        raise Unsendable("The change names no campaign budget.")
    if not isinstance(amount, int) or amount <= 0:
        raise Unsendable("The change names no daily amount above zero.")
    return Operation(
        resource_type="campaign_budget",
        doing=Doing.UPDATE,
        resource_name=budget,
        fields={"amountMicros": amount},
        # Google's JSON name for the field, as the request body spells it.
        update_mask=("amountMicros",),
    )


def _removals(sent: dict[str, Any]) -> tuple[Operation, ...]:
    names = [str(n) for n in (sent.get("criteria") or []) if n]
    if not names:
        raise Unsendable("The change names nothing to remove.")
    for name in names:
        if "/adGroupCriteria/" not in name:
            # Only what an exclusion created is removed this way. A remove is
            # final in Google, so it is never pointed at anything else.
            raise Unsendable(f"{name} is not an exclusion PPCWay made.")
    return tuple(
        Operation(resource_type="ad_group_criterion", doing=Doing.REMOVE, resource_name=name)
        for name in dict.fromkeys(names)
    )


def _all_in(customer_id: str, operations: tuple[Operation, ...]) -> None:
    """Every resource each operation names belongs to this one account."""
    if not customer_id:
        raise Unsendable("The change does not say which account it is for.")
    mine = f"customers/{customer_id}/"
    for op in operations:
        named = [op.resource_name] if op.resource_name else []
        named += [str(v) for k, v in op.fields.items() if k in {"adGroup", "campaign"}]
        for name in named:
            if not str(name).startswith(mine):
                raise Unsendable(
                    f"The change names {name}, which is not in account {customer_id}."
                    " Nothing was sent."
                )
