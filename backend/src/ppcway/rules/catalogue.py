"""The rules, as data rather than as code.

Every entry in the action log names the rule and the version of it that
produced the change. That is only answerable if a rule *is* something -- an id,
a version, a risk level, a route, and the thresholds it reads -- rather than a
function with constants scattered through it. "Which limits were in force when
this happened in March?" is a question a merchant is entitled to an answer to,
and the answer has to survive the rule being improved in April.

So the thresholds live here, in the record, and the function that implements a
rule is handed them. A rule whose numbers changed gets a new `version`, and the
old version stays in this file: an action logged against R1 version 2 must
still be explainable after version 3 ships.

**Three of the five are declared and not implemented, deliberately.** The
client's brief specifies the rules engine as "R1-R5 as versioned data" and
points at `v0.1 §1.2, 1.5` for what they are. Only §1.2's own summary reached
us: the brief names R1 (negative keywords from wasteful search terms) and R4
(pausing disapproved ads, pause only) because those are the two the client will
let run unattended. R2, R3 and R5 are named nowhere we hold.

Guessing at them would be worse than leaving them out. A rule that proposes
changes to somebody's advertising spend on thresholds we invented is not a
placeholder, it is a liability, and the version numbers would then be lies --
version 1 of R2 would be a rule the client never specified. So they sit here
with `implemented = False`, the engine skips them, and a test asserts the
engine never emits anything for a rule in that state.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class Risk(StrEnum):
    """How much a change could cost if it is wrong. The brief's three levels."""

    #: Cannot reduce traffic or raise spend. Eligible for auto-apply, if the
    #: merchant has opted in and the flag is on.
    LOW = "low"
    #: Moves money or traffic within the ordinary limits. Needs a person.
    MEDIUM = "medium"
    #: Large, or hard to put back. Needs an expert, not just the owner.
    HIGH = "high"


class Route(StrEnum):
    """Who has to say yes before this reaches the account."""

    #: One tap from the owner or an admin.
    OWNER = "owner"
    #: A PPCWay expert signs it off first. The brief's expert route, which is
    #: where a budget rise between 20% and 50% goes.
    EXPERT = "expert"


#: The brief: medium and high-risk changes always need a person, so only LOW is
#: ever a candidate for auto-apply -- and then only the types the client named.
MAY_AUTO: Final = frozenset({Risk.LOW})


@dataclass(frozen=True, slots=True)
class Rule:
    """One rule, as the action log will record it."""

    id: str
    version: int
    name: str
    #: What a person reads on the card, before any figures are put into it.
    about: str
    #: The change type this proposes, which is also what the gateway dispatches
    #: on: "add_negative_keyword", "pause_ad", "decrease_daily_budget".
    kind: str
    risk: Risk
    route: Route
    #: Whether the client has named this type as eligible for auto-apply. Not
    #: the same as it being on: the consent record and the feature flag are
    #: both separate, and both come later.
    auto_eligible: bool = False
    #: The thresholds, as data. Handed to the rule rather than read from it.
    limits: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))
    #: False where the client has not told us what the rule is. The engine
    #: skips these, and will not invent one.
    implemented: bool = False
    #: Where the specification is, so the next person knows what is missing.
    spec: str = ""

    def __post_init__(self) -> None:
        if self.auto_eligible and self.risk not in MAY_AUTO:
            raise ValueError(
                f"{self.id} is {self.risk.value} risk and marked auto-eligible. The"
                f" client's brief is explicit that medium and high-risk changes always"
                f" need a person, so this combination cannot be configured."
            )
        if self.implemented and not self.limits and self.kind != "pause_ad":
            raise ValueError(
                f"{self.id} is implemented but names no thresholds. Thresholds belong"
                f" in this record so an action logged against a version can still be"
                f" explained after the version changes."
            )


#: Every rule, by id. The versions here are what the action log records.
CATALOGUE: Final[dict[str, Rule]] = {
    "R1": Rule(
        id="R1",
        version=2,
        name="Money going on the wrong searches",
        about=(
            "Somebody searched for something your ads should not have answered, "
            "clicked, and cost you money without getting in touch."
        ),
        kind="add_negative_keyword",
        # Excluding a search nobody converted on cannot raise spend and cannot
        # cost traffic worth having, which is why the client will let it run.
        risk=Risk.LOW,
        route=Route.OWNER,
        auto_eligible=True,
        limits=MappingProxyType(
            {
                # The brief's own figures: "Minimum data to call a loser: 1.5x
                # target cost per lead in spend, or 100 clicks."
                "wasted_multiple_of_target": 1.5,
                "enough_clicks": 100.0,
                # And a floor in money, so a cheap account with a low target
                # does not start excluding terms that cost pennies. It was 20
                # until 6 November 2026 (version 1), which on a small account
                # was the whole test: at five dollars a day no single search
                # reached it, and the brief's own bar never got a say.
                "least_wasted": 5.0,
                "window_days": 30.0,
            }
        ),
        implemented=True,
        spec="client brief, auto-apply opt-in (R1)",
    ),
    "R2": Rule(
        id="R2",
        version=1,
        name="Not specified",
        about="The client has not told us what this rule is.",
        kind="unspecified",
        risk=Risk.MEDIUM,
        route=Route.OWNER,
        implemented=False,
        spec="v0.1 §1.2 -- not supplied",
    ),
    "R3": Rule(
        id="R3",
        version=1,
        name="Not specified",
        about="The client has not told us what this rule is.",
        kind="unspecified",
        risk=Risk.MEDIUM,
        route=Route.OWNER,
        implemented=False,
        spec="v0.1 §1.2 -- not supplied",
    ),
    "R4": Rule(
        id="R4",
        version=1,
        name="Ads Google has refused",
        about=(
            "Google has disapproved this ad, so it is not being shown to anybody. "
            "Pausing it does not cost you traffic you were getting."
        ),
        kind="pause_ad",
        # A disapproved ad is already not serving. Pausing it cannot reduce
        # traffic, which is the whole reason this is low risk and pause-only.
        risk=Risk.LOW,
        route=Route.OWNER,
        auto_eligible=True,
        implemented=True,
        spec="client brief, auto-apply opt-in (R4, pause only)",
    ),
    "R5": Rule(
        id="R5",
        version=1,
        name="Not specified",
        about="The client has not told us what this rule is.",
        kind="unspecified",
        risk=Risk.MEDIUM,
        route=Route.OWNER,
        implemented=False,
        spec="v0.1 §1.2 -- not supplied",
    ),
    # Two rules of PPCWay's own, written on 10 November 2026 when the owner
    # found Otto had nothing to say on an account whose conversion tracking
    # counts nearly every click: R1 can never find a search with no leads
    # there, and R4 had no refused ad to find. Both compare campaigns with
    # each other rather than judging one search, so they work on any account
    # that counts leads at all. Their thresholds are judgements, recorded in
    # docs/decisions/2026-11-10-otto-moves-money-between-campaigns.md, and
    # they stand until the client's own R2, R3 and R5 arrive.
    "R6": Rule(
        id="R6",
        version=1,
        name="A campaign held back by its budget",
        about=(
            "This campaign brings leads far more cheaply than the rest of your account, "
            "and it runs out of budget before the day is over."
        ),
        kind="increase_daily_budget",
        # More spend is never low risk, however good the campaign: a person
        # always decides it, and it is never applied unattended.
        risk=Risk.MEDIUM,
        route=Route.OWNER,
        limits=MappingProxyType(
            {
                "window_days": 30.0,
                # Leads cost at most this share of the account's average...
                "cheaper_than": 0.6,
                # ...and Google says it lost at least this share of its searches
                # to the budget, on average over the last fourteen days.
                "lost_to_budget": 0.2,
                # Enough leads that the comparison is not luck.
                "least_leads": 10.0,
                # A campaign this new is still learning; Google advises leaving
                # its budget alone until it has settled.
                "settled_days": 7.0,
                # Within the client's band for a change a merchant may approve
                # alone (opt.guardrails: up to 20%).
                "step_pct": 20.0,
            }
        ),
        implemented=True,
        spec="PPCWay, 10 November 2026, pending the client's R2/R3/R5",
    ),
    "R7": Rule(
        id="R7",
        version=1,
        name="A campaign whose leads cost far more",
        about=(
            "This campaign's leads cost a lot more than the rest of your account's. "
            "Less of the budget there means less money on your dearest leads."
        ),
        kind="decrease_daily_budget",
        # Spending less cannot cost more, which is what makes it low risk. It
        # can cost leads, which is why it is a suggestion and says so.
        risk=Risk.LOW,
        route=Route.OWNER,
        limits=MappingProxyType(
            {
                "window_days": 30.0,
                # Leads cost at least this many times the account's average.
                "dearer_than": 2.0,
                "least_leads": 10.0,
                "settled_days": 7.0,
                "step_pct": 20.0,
                # Never suggest a budget below this, in the account's currency.
                "least_budget": 1.0,
            }
        ),
        implemented=True,
        spec="PPCWay, 10 November 2026, pending the client's R2/R3/R5",
    ),
}


def rule(rule_id: str) -> Rule:
    """One rule by id, refusing rather than inventing an unknown one."""
    try:
        return CATALOGUE[rule_id]
    except KeyError:
        raise ValueError(
            f"there is no rule {rule_id!r}. Every action in the log names a rule, so a"
            f" rule id that is not in the catalogue would be an entry nobody can explain."
        ) from None


def live() -> tuple[Rule, ...]:
    """The rules the engine may run: the ones we have actually been told."""
    return tuple(r for r in CATALOGUE.values() if r.implemented)


def waiting() -> tuple[Rule, ...]:
    """The rules the client still owes us, for a status screen to be honest on."""
    return tuple(r for r in CATALOGUE.values() if not r.implemented)
