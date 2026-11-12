"""Whether one piece of ad text may be used, and which stage said no.

The client's brief gives the order and the order is the specification:
*Google limits → policy pre-check → factual check against the business
profile → category prohibited claims → brand check → de-duplication.*

**The order is about blame, not about speed.** Every asset is checked by every
stage that can reach it, because the builder keeps the assets that pass rather
than stopping at the first problem -- the brief asks for fifteen headlines
drafted and at least ten kept. What the order decides is which refusal a
person is shown when an asset fails more than one stage, and that matters:
"too long" is a thing the model can fix on the next attempt, while "claims
something the business profile does not support" is a thing it must not try to
fix by rewording.

**Stage three is the one that cannot be done with a word list.** "Factual check
against the business profile" means a claim in the ad has to be supported by
what the merchant actually told us they do. A list of banned words cannot
decide whether "24 hour emergency callout" is true; the business profile can,
and where it cannot the honest answer is to refuse the asset rather than to
pass it because no rule matched. So an unsupported specific claim fails, and
that is the stage that will reject the most drafts.

**What is not here.** The per-industry prohibited-claim lists and the category
templates are the client's to supply -- their brief lists them under "What
PPCway will supply", per launch industry. Stage four reads whatever list it is
given and passes everything when given none, which is the only honest
behaviour: a stage that invented its own list for a trade nobody has described
would be a stage refusing ads for reasons nobody agreed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from ppcway.builder.kinds import BY_PROMISE, LEGACY, PHRASES

#: Google's own limits for a responsive search ad. Restated here rather than
#: read from the API, because an asset has to be refused before it is sent and
#: the API only answers about assets it has been sent.
HEADLINE_CHARS: Final = 30
DESCRIPTION_CHARS: Final = 90
#: How many Google will take, and how few it will run with.
HEADLINES_WANTED: Final = 15
HEADLINES_LEAST: Final = 3
DESCRIPTIONS_WANTED: Final = 4
DESCRIPTIONS_LEAST: Final = 2

#: The brief: draft 15, keep at least 10 that pass, otherwise retry once and
#: then fall back to the category template.
HEADLINES_KEEP: Final = 10


class Stage(StrEnum):
    """The six, in the brief's order. The value is what a person is shown."""

    LIMITS = "google_limits"
    POLICY = "policy_pre_check"
    FACTUAL = "factual_check"
    CATEGORY = "category_claims"
    BRAND = "brand_check"
    DUPLICATE = "de_duplication"


#: The order they run in. As data, because the order is the specification and
#: a test asserts this tuple against the brief's sentence.
ORDER: Final[tuple[Stage, ...]] = (
    Stage.LIMITS,
    Stage.POLICY,
    Stage.FACTUAL,
    Stage.CATEGORY,
    Stage.BRAND,
    Stage.DUPLICATE,
)


class Kind(StrEnum):
    HEADLINE = "headline"
    DESCRIPTION = "description"


@dataclass(frozen=True, slots=True)
class Business:
    """What the merchant told us they do, which is what a claim is checked against.

    Everything here came from the merchant or from their own website. Nothing
    is inferred: a trade we guessed at cannot be the thing that licenses a
    claim about opening hours.
    """

    name: str = ""
    #: The landing page's own title, for the model to write in the site's
    #: voice. Context only: no claim is licensed by it (`builder.site`).
    site_title: str = ""
    #: What they sell, in their own words.
    services: tuple[str, ...] = ()
    #: The towns they work in.
    places: tuple[str, ...] = ()
    #: True only where the merchant said so. The audit learned this one the
    #: hard way: "open 24 hours" is a criterion for a plumber and nonsense for
    #: a dentist, and an ad claiming it for a business that is not is a
    #: complaint waiting to happen.
    open_all_hours: bool = False
    free_quotes: bool = False
    emergency_callout: bool = False
    #: Which kind of business it is (`builder.kinds`), so the copy is written
    #: for a software product as one and for a salon as the other.
    kind: str = ""
    #: The promises the merchant ticked as true (`builder.kinds.PROMISES`).
    #: The three booleans above are the first builder's version of the same
    #: thing, kept so a draft written before 10 November still checks.
    promises: tuple[str, ...] = ()
    years_trading: int | None = None
    #: Accreditations they have evidence for.
    accreditations: tuple[str, ...] = ()
    #: Their own brand terms, which an ad may of course use.
    brand_words: tuple[str, ...] = ()
    #: The business summary from Google's "Keyword and asset generation" step,
    #: in the merchant's words. Context for the writer only: like the site's
    #: title, it licenses no claim; the promises ticked above still decide.
    summary: str = ""


@dataclass(frozen=True, slots=True)
class Rules:
    """What this trade may not say, and whose names may not appear.

    Both supplied by the client per launch industry. Empty means "nobody has
    told us", and an empty list passes everything -- see the module note.
    """

    #: Phrases this trade may not claim. The client's per-industry list.
    prohibited: tuple[str, ...] = ()
    #: Competitor and third-party names an ad may not use.
    protected_brands: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Refusal:
    """Why one asset may not be used."""

    stage: Stage
    text: str
    kind: Kind
    because: str


@dataclass(frozen=True, slots=True)
class Checked:
    """What survived, and why the rest did not."""

    kept: tuple[str, ...] = ()
    refused: tuple[Refusal, ...] = ()
    #: Which stages actually ran, for the action log and for a screen that
    #: wants to say the category list was empty rather than that it passed.
    ran: tuple[Stage, ...] = field(default_factory=lambda: ORDER)

    @property
    def enough_headlines(self) -> bool:
        return len(self.kept) >= HEADLINES_KEEP


#: Superlatives Google's own policy treats as unverifiable. Not an exhaustive
#: list and not meant to be: the per-industry list is the client's, and this
#: catches the handful that appear in almost every first draft.
_SUPERLATIVES: Final = frozenset(
    {
        "best",
        "cheapest",
        "number one",
        "#1",
        "no.1",
        "no 1",
        "top rated",
        "guaranteed",
        "fastest",
        "greatest",
        "unbeatable",
        "lowest price",
        "world class",
    }
)


def promised(business: Business) -> frozenset[str]:
    """Every promise this business may make: ticked, or carried from a draft
    written before promises were a list."""
    allowed = set(business.promises)
    for flag, ids in LEGACY.items():
        if getattr(business, flag, False):
            allowed.update(ids)
    return frozenset(allowed)


#: Shouting. Google refuses an asset in capitals, and a word in capitals is
#: not the same as an acronym.
_ACRONYMS: Final = frozenset({"UK", "IE", "VAT", "LED", "CCTV", "NICEIC", "RGI", "HVAC", "DIY"})

_PUNCTUATION = re.compile(r"[!]{1,}")
_REPEATED = re.compile(r"(.)\1{2,}")
_WORDS = re.compile(r"[A-Za-z][A-Za-z'’-]*")
#: For the duplicate key: words *and* numbers. Numbers have to count, or
#: "Boiler Repair from £50" and "from £80" would be one headline -- which is
#: the opposite of true, since the number is the only thing a reader sees.
_TOKENS = re.compile(r"[A-Za-z][A-Za-z'’-]*|\d+")


def _limit_for(kind: Kind) -> int:
    return HEADLINE_CHARS if kind is Kind.HEADLINE else DESCRIPTION_CHARS


def _google_limits(text: str, kind: Kind) -> str:
    """Stage one. What Google will simply not accept."""
    if not text.strip():
        return "it is empty"
    limit = _limit_for(kind)
    if len(text) > limit:
        return f"it is {len(text)} characters and Google allows {limit} for a {kind.value}"
    if _REPEATED.search(text):
        return "it repeats a character three or more times, which Google refuses"
    return ""


def _policy(text: str, kind: Kind) -> str:
    """Stage two. What Google's policy refuses before anybody reviews it."""
    if _PUNCTUATION.search(text):
        return "Google does not allow exclamation marks in this position"
    shouting = [
        word
        for word in _WORDS.findall(text)
        if len(word) > 1 and word.isupper() and word not in _ACRONYMS
    ]
    if shouting:
        return f"{shouting[0]} is in capitals, which Google treats as shouting"
    lowered = text.lower()
    for word in sorted(_SUPERLATIVES):
        if word in lowered:
            return (
                f'"{word}" is a claim nobody can check, and Google refuses'
                f" unverifiable superlatives"
            )
    del kind
    return ""


def _factual(text: str, kind: Kind, business: Business) -> str:
    """Stage three. A specific claim has to be supported by the profile.

    The stage that will reject the most drafts, and the one that should: a
    model writing ad copy will cheerfully offer a 24-hour callout for a
    business that closes at five, because it is a plausible thing for a plumber
    to say.
    """
    lowered = text.lower()
    allowed = promised(business)
    # Longest phrase first, and a phrase that is allowed is blanked out before
    # the shorter ones are looked for: "try for free" is the free trial's
    # wording, and must not then be refused as the free version's "for free".
    for phrase, promise in PHRASES:
        if phrase not in lowered:
            continue
        if promise.id in allowed:
            lowered = lowered.replace(phrase, " ")
            continue
        return (
            f'"{phrase}" promises {BY_PROMISE[promise.id].short}, which was not ticked as'
            f" true for this business. It can only be used if the merchant says it is."
        )
    years = re.search(r"\b(\d{1,3})\s*(?:\+\s*)?years?\b", lowered)
    if years:
        claimed = int(years.group(1))
        if business.years_trading is None or claimed > business.years_trading:
            return f"it claims {claimed} years, which the business profile does not support"
    for word in ("certified", "accredited", "approved", "registered"):
        if word in lowered and not business.accreditations:
            return f'"{word}" implies an accreditation, and none is recorded for this business'
    del kind
    return ""


def _category(text: str, kind: Kind, rules: Rules) -> str:
    """Stage four. What this trade may not say, from the client's own list."""
    lowered = text.lower()
    for phrase in rules.prohibited:
        if phrase and phrase.lower() in lowered:
            return f'"{phrase}" is on the prohibited list for this trade'
    del kind
    return ""


def _brand(text: str, kind: Kind, business: Business, rules: Rules) -> str:
    """Stage five. Somebody else's name."""
    lowered = text.lower()
    mine = {word.lower() for word in business.brand_words if word}
    for brand in rules.protected_brands:
        if not brand or brand.lower() in mine:
            continue
        if brand.lower() in lowered:
            return f'"{brand}" is somebody else\'s name and may not be used in an ad'
    del kind
    return ""


def _tidy(text: str) -> str:
    """One asset reduced to what makes it the same as another.

    Case and punctuation go, and so does word order: Google treats two
    headlines as interchangeable long before a person would, and "Emergency
    Plumber Ennis" beside "Ennis Emergency Plumber" is one idea written twice.
    """
    return " ".join(sorted(token.lower() for token in _TOKENS.findall(text)))


def check(
    drafts: Sequence[str],
    *,
    kind: Kind,
    business: Business,
    rules: Rules | None = None,
) -> Checked:
    """Every draft through all six stages, in the brief's order.

    Each asset is checked by every stage until one refuses it; the refusal
    names that stage, which is the first one it failed. Assets that pass are
    kept in the order they were drafted, because a model drafts its best
    first.
    """
    the_rules = rules or Rules()
    kept: list[str] = []
    refused: list[Refusal] = []
    seen: set[str] = set()

    for text in drafts:
        said = _google_limits(text, kind)
        stage = Stage.LIMITS
        if not said:
            said, stage = _policy(text, kind), Stage.POLICY
        if not said:
            said, stage = _factual(text, kind, business), Stage.FACTUAL
        if not said:
            said, stage = _category(text, kind, the_rules), Stage.CATEGORY
        if not said:
            said, stage = _brand(text, kind, business, the_rules), Stage.BRAND
        if not said:
            # Last, because an asset that would be refused anyway should be
            # refused for its own reason rather than for resembling one.
            tidied = _tidy(text)
            if tidied in seen:
                said, stage = "it says the same as another headline", Stage.DUPLICATE
            else:
                seen.add(tidied)

        if said:
            refused.append(Refusal(stage=stage, text=text, kind=kind, because=said))
        else:
            kept.append(text)

    return Checked(kept=tuple(kept), refused=tuple(refused))
