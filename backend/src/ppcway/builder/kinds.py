"""What kind of business a campaign is for, and what it can honestly promise.

The builder was written around one kind of business. Its only promises were a
tradesman's -- free quotes, open 24 hours, emergency callouts -- and its
examples were "water heater repair". On 10 November the client turned it down
for exactly that: a shop, a software product, an accountant or a salon could
not say what was true about them, and a plumber's promises were the only ones
the checks knew how to police.

So the kinds and the promises live here, once. The new-campaign screen reads
them (through `/v1/campaigns/start`) to ask the right questions; the copy
checks read them to refuse any promise the merchant did not tick; and the
model is told which promises it may make. A promise the checks do not know
cannot be made by accident, because nothing licenses it -- and a promise that
is listed here can only be made when the merchant says it is true.

**Phrases are matched as substrings of the lower-cased ad text.** A phrase
belongs to exactly one promise; overlapping phrases would make one tick
license or block another's wording without anybody meaning it to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final


@dataclass(frozen=True, slots=True)
class Promise:
    """Something an ad may only say when the merchant has said it is true."""

    id: str
    #: How the merchant ticks it, in their own voice.
    label: str
    #: How it reads inside a sentence: "We can promise a free trial".
    short: str
    #: Ad wording that makes this promise. Lower case.
    phrases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Kind:
    """A kind of business, as a merchant would describe their own."""

    id: str
    label: str
    #: Who this is, for somebody deciding whether it is them.
    examples: str
    #: How it reads inside a sentence: "Advertise PDFezy, an online tool".
    noun: str
    #: What a customer would search for, as a placeholder. Never pre-filled.
    services_hint: str
    #: What counts as a win for this kind, for the bidding choice.
    win: str
    #: The promises most businesses of this kind can make, offered first.
    promises: tuple[str, ...]
    #: Searches nobody of this kind wants to pay for, offered as a start.
    negatives: tuple[str, ...]


PROMISES: Final[tuple[Promise, ...]] = (
    Promise(
        "free_quotes",
        "We give free quotes or estimates",
        "free quotes",
        ("free quote", "free estimate", "no call out charge", "no callout charge"),
    ),
    Promise(
        "free_consultation",
        "The first consultation is free",
        "a free first consultation",
        ("free consultation", "free consult", "free initial consultation", "free first meeting"),
    ),
    Promise(
        "open_all_hours",
        "We're open 24 hours, 7 days a week",
        "24/7 opening",
        ("24 hour", "24/7", "24-7", "open all hours", "round the clock", "any time of day"),
    ),
    Promise(
        "same_day",
        "We offer same-day service",
        "same-day service",
        ("same day", "same-day"),
    ),
    Promise(
        "emergency_callout",
        "We take emergency callouts",
        "emergency callouts",
        ("emergency", "callout"),
    ),
    Promise(
        "licensed_insured",
        "We're licensed and insured",
        "licensed and insured work",
        ("licensed", "licenced", "insured"),
    ),
    Promise(
        "family_owned",
        "We're family-owned",
        "a family-owned business",
        ("family owned", "family-owned", "family run", "family-run"),
    ),
    Promise(
        "book_online",
        "Customers can book online",
        "online booking",
        ("book online", "online booking", "book now online"),
    ),
    Promise(
        "free_shipping",
        "Shipping is free",
        "free shipping",
        ("free shipping", "free delivery", "ships free", "delivered free"),
    ),
    Promise(
        "next_day",
        "We deliver the next day",
        "next-day delivery",
        ("next day", "next-day", "overnight delivery"),
    ),
    Promise(
        "money_back",
        "There's a money-back guarantee",
        "a money-back guarantee",
        ("money back", "money-back", "refund guarantee", "full refund"),
    ),
    Promise(
        "free_plan",
        "There's a free version",
        "a free version",
        (
            "free forever",
            "free plan",
            "free version",
            "free to use",
            "free online",
            "for free",
            "100% free",
            "completely free",
            "totally free",
        ),
    ),
    Promise(
        "free_trial",
        "There's a free trial",
        "a free trial",
        ("free trial", "try free", "try it free", "try for free", "try it for free"),
    ),
    Promise(
        "no_card",
        "No credit card needed to start",
        "no card to start",
        ("no credit card", "no card needed", "no card required"),
    ),
)

#: Searches almost nobody wants to pay for, whatever they sell.
_ALWAYS_SKIP: Final = ("jobs", "careers", "salary")

KINDS: Final[tuple[Kind, ...]] = (
    Kind(
        id="at_their_place",
        label="We go to our customers",
        examples="Plumbers, cleaners, movers, repairs, landscaping",
        noun="a business that goes to its customers",
        services_hint="emergency plumber, end of tenancy cleaning…",
        win="calls and enquiries",
        promises=(
            "free_quotes",
            "same_day",
            "emergency_callout",
            "open_all_hours",
            "licensed_insured",
            "family_owned",
        ),
        negatives=(*_ALWAYS_SKIP, "diy", "how to"),
    ),
    Kind(
        id="they_visit",
        label="Customers come to us",
        examples="Shops, salons, restaurants, clinics, gyms",
        noun="a place customers visit",
        services_hint="haircut and colour, dental check-up…",
        win="visits and bookings",
        promises=("book_online", "free_consultation", "open_all_hours", "family_owned"),
        negatives=_ALWAYS_SKIP,
    ),
    Kind(
        id="professional",
        label="We advise or do work for clients",
        examples="Lawyers, accountants, consultants, agencies",
        noun="a professional service",
        services_hint="small business tax returns, immigration lawyer…",
        win="enquiries",
        promises=("free_consultation", "licensed_insured", "book_online", "family_owned"),
        negatives=(*_ALWAYS_SKIP, "course", "template"),
    ),
    Kind(
        id="online_shop",
        label="We sell products online",
        examples="Clothing, gifts, parts, home goods",
        noun="an online shop",
        services_hint="linen bedding, bike lights…",
        win="sales",
        promises=("free_shipping", "next_day", "money_back"),
        negatives=(*_ALWAYS_SKIP, "wholesale", "used"),
    ),
    Kind(
        id="software",
        label="We offer software or an online tool",
        examples="Apps, online tools, software for businesses",
        noun="an online tool",
        services_hint="pdf to word, invoicing software…",
        win="sign-ups",
        promises=("free_plan", "free_trial", "no_card", "money_back"),
        negatives=(*_ALWAYS_SKIP, "crack", "torrent"),
    ),
    Kind(
        id="other",
        label="Something else",
        examples="Charities, events, classes, anything not listed",
        noun="a business",
        services_hint="weekend pottery class, wedding photography…",
        win="enquiries",
        promises=("free_consultation", "book_online", "money_back"),
        negatives=_ALWAYS_SKIP,
    ),
)

BY_PROMISE: Final[dict[str, Promise]] = {one.id: one for one in PROMISES}
BY_KIND: Final[dict[str, Kind]] = {one.id: one for one in KINDS}

#: Every phrase, with the promise it makes, longest first, so the more
#: specific wording is what a refusal names.
PHRASES: Final[tuple[tuple[str, Promise], ...]] = tuple(
    sorted(
        ((phrase, one) for one in PROMISES for phrase in one.phrases),
        key=lambda pair: -len(pair[0]),
    )
)

#: The three promises the first builder knew, as booleans on the profile. A
#: draft written before 10 November still carries them, and "same day" was
#: licensed by the emergency tick then, so it still is.
LEGACY: Final[dict[str, tuple[str, ...]]] = {
    "open_all_hours": ("open_all_hours",),
    "free_quotes": ("free_quotes",),
    "emergency_callout": ("emergency_callout", "same_day"),
}


def kind_of(value: object) -> Kind:
    """The kind a merchant chose, or "something else" for anything unknown."""
    return BY_KIND.get(str(value or ""), BY_KIND["other"])


def known_promises(values: object) -> tuple[str, ...]:
    """The promises ticked, keeping only ones that exist, in catalogue order."""
    ticked = {str(v) for v in values} if isinstance(values, list | tuple) else set()
    return tuple(one.id for one in PROMISES if one.id in ticked)


def catalogue() -> dict[str, Any]:
    """Everything the new-campaign screen needs to ask the right questions."""
    return {
        "kinds": [
            {
                "id": k.id,
                "label": k.label,
                "examples": k.examples,
                "noun": k.noun,
                "services_hint": k.services_hint,
                "win": k.win,
                "promises": list(k.promises),
                "negatives": list(k.negatives),
            }
            for k in KINDS
        ],
        "promises": [{"id": p.id, "label": p.label, "short": p.short} for p in PROMISES],
    }
