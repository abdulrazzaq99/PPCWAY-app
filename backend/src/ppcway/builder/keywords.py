"""Which keywords may go into a campaign, and which may only be suggested.

The client's brief, twice over: *keywords only from Keyword Planner; model
suggestions shown only if Keyword Planner returns volume*, and *the model may
suggest candidates only; each must have Keyword Planner volume. The model never
adds a keyword directly.*

So there are two kinds of word here and the difference is the whole module. A
**candidate** is something a model thought of, or a merchant typed, or we
lifted off their website. A **keyword** is a candidate that Google's own
Keyword Planner has confirmed people actually search for, with a volume
attached. Only the second kind reaches a campaign.

**Why that matters more than it sounds.** A model asked for fifty plumbing
keywords will produce fifty plausible phrases, and perhaps thirty of them are
things no human has ever typed into Google. Those thirty cost nothing in
impressions and everything in trust: a merchant reading their new campaign sees
half of it is invented, and stops believing the half that is not. Keyword
Planner is the only thing that can tell them apart, and it is free.

**A candidate with no volume is not deleted, it is demoted.** It comes back
marked, with its reason, because "we thought of this and Google says nobody
searches for it" is useful to a merchant and is the sort of thing a person
would want to argue with. Silently dropping it would make the builder look like
it had simply thought of less.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from ppcway.ads.planner import Demand

#: Below this many monthly searches a keyword is not worth a campaign's time.
#: Google reports very low volumes as a range starting at 10, so anything under
#: that is "effectively nobody" rather than a number.
LEAST_MONTHLY: Final = 10


@dataclass(frozen=True, slots=True)
class Keyword:
    """A candidate Keyword Planner has confirmed, with what it is worth."""

    text: str
    monthly: int
    competition: str
    top_of_page_low: float
    top_of_page_high: float


@dataclass(frozen=True, slots=True)
class Dropped:
    """A candidate that may be shown and may not be used."""

    text: str
    because: str


@dataclass(frozen=True, slots=True)
class Sifted:
    """What may go into the campaign, and what may only be talked about."""

    keywords: tuple[Keyword, ...] = ()
    dropped: tuple[Dropped, ...] = ()
    #: Set when Keyword Planner could not be reached at all. Not the same as
    #: "nothing had volume": one means we do not know and must not guess, the
    #: other means we know and the answer was no.
    unavailable: str = ""

    @property
    def usable(self) -> bool:
        """Whether a campaign may be built from this at all."""
        return not self.unavailable and bool(self.keywords)


def _tidy(text: str) -> str:
    return " ".join(text.lower().split())


def sift(candidates: Sequence[str], demand: Demand, *, least: int = LEAST_MONTHLY) -> Sifted:
    """Keep the candidates Keyword Planner confirmed; demote the rest.

    `demand` is what the planner answered for these seeds. A planner that could
    not be reached produces `unavailable` rather than an empty keyword list,
    because a builder that treated "we could not ask" as "the answer is no"
    would quietly build nothing and report success.
    """
    if not demand.read:
        return Sifted(
            unavailable=(
                demand.trouble
                or "We could not reach Google's Keyword Planner, so we cannot tell which"
                " of these people actually search for."
            )
        )

    confirmed = {_tidy(found.term): found for found in demand.searches}
    keywords: list[Keyword] = []
    dropped: list[Dropped] = []
    seen: set[str] = set()

    for candidate in candidates:
        key = _tidy(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        found = confirmed.get(key)
        if found is None:
            dropped.append(
                Dropped(
                    text=candidate,
                    because=(
                        "Google's Keyword Planner has no searches for this, so we have"
                        " not added it. It can go in later if that changes."
                    ),
                )
            )
            continue
        if found.monthly < least:
            dropped.append(
                Dropped(
                    text=candidate,
                    because=(
                        f"Only about {found.monthly} searches a month, which is too few"
                        f" to be worth bidding on."
                    ),
                )
            )
            continue
        keywords.append(
            Keyword(
                text=candidate,
                monthly=found.monthly,
                competition=found.competition,
                top_of_page_low=found.top_of_page_low,
                top_of_page_high=found.top_of_page_high,
            )
        )

    # Busiest first: a campaign's first ad group should be the thing most
    # people are actually looking for.
    keywords.sort(key=lambda one: one.monthly, reverse=True)
    return Sifted(keywords=tuple(keywords), dropped=tuple(dropped))
