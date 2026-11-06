"""What counts as a lead, out of everything Google calls a conversion.

Google Ads counts whatever an advertiser tells it to, and some accounts are set
up to count a page loading. On those, every click is a "conversion": PDFezy's
new campaign showed 38 clicks and 38 leads. PPCWay used to pass that straight
through, so its cost per lead was a cost per visit, and R1 -- which only offers
to exclude a search that brought no leads -- could never fire, because no
search with a click ever had none.

So a conversion is a lead unless its category is something a visitor does on
the way: seeing a page, engaging with it, adding to a basket, starting a
checkout. Everything else counts -- forms, calls, sign-ups, quote requests,
bookings, and sales too, because a search that sells is never wasted.

**Why a short list of what does not count, rather than a list of what does.**
`DEFAULT` ("Other") is what an advertiser gets when they do not choose a
category, and a real enquiry form is often filed there. Treating the unknown as
not a lead would make searches that bring enquiries look wasted, and the worst
thing Otto can do is offer to stop a search that brings customers. So the
doubtful cases count, which errs the safe way: fewer suggestions, not wrong
ones. See `docs/decisions/2026-11-06-what-counts-as-a-lead.md`.

Google refuses to report the conversion category beside clicks, cost or
impressions, so every read that needs leads asks a second question for the
split and lays it over the first.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Final

#: The categories Google gives to calls. A call is a lead and is shown apart
#: from forms, because a merchant answers the two differently.
CALLS: Final = frozenset({"PHONE_CALL_LEAD", "CALL"})

#: What a visitor does on the way, which is not somebody getting in touch or
#: buying. Named in Google's own words, from `ConversionActionCategory` (v25).
NOT_LEADS: Final = frozenset(
    {
        "PAGE_VIEW",
        "ENGAGEMENT",
        "ADD_TO_CART",
        "BEGIN_CHECKOUT",
        "STORE_VISIT",
        "YOUTUBE_FOLLOW_ON_VIEWS",
        "IN_APP_AD_REVENUE",
    }
)


def is_lead(category: str) -> bool:
    """Whether a conversion in this category is somebody getting in touch or buying."""
    return category not in NOT_LEADS


def is_call(category: str) -> bool:
    return category in CALLS


def category_of(row: Mapping[str, Any]) -> str:
    """The conversion category of one row of a split read, as Google spells it."""
    return str(row.get("segments", {}).get("conversionActionCategory", "") or "")


def conversions_in(row: Mapping[str, Any]) -> float:
    return float(row.get("metrics", {}).get("conversions", 0) or 0)


def leads_by[Key](
    rows: Iterable[dict[str, Any]], key: Callable[[dict[str, Any]], Key]
) -> dict[Key, float]:
    """Leads per key, from a read split by conversion category.

    A key with conversions but no leads is present with 0.0, so a caller can
    tell "counted, and none were leads" from "Google said nothing about it".
    """
    found: dict[Key, float] = {}
    for row in rows:
        at = key(row)
        found.setdefault(at, 0.0)
        if is_lead(category_of(row)):
            found[at] += conversions_in(row)
    return found
