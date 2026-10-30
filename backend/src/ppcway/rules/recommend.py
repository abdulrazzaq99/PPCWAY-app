"""What a rule found, why, and how it ranks against everything else it found.

A recommendation is not a guardrail `Proposal`. The guardrails need the
mechanical facts -- which number moves, by how much, how many things get paused
-- and nothing else; that is what makes them checkable. A recommendation is the
richer thing a merchant reads and the action log stores: a reason, the figures
behind it, what we expect to happen, and how to put it back. `to_proposal`
is the seam between the two, and it only ever narrows.

**The priority score is money a month, and that is deliberately almost all of
it.** A finding worth two hundred pounds a month outranks one worth five,
whatever either is about, because the merchant's question is which of these to
do first and the answer is usually the expensive one. Confidence multiplies it,
so a shaky two hundred ranks below a certain one-fifty. Risk is a small
tiebreak, no more: a safe change is slightly preferred at equal money, because
being wrong about it costs less.

**Blocking findings sort first regardless, and that is a second key rather than
a bigger number.** An ad group with nothing live in it is not a saving of any
size; it is a thing that has stopped working. Expressing that as "worth £900 a
month" would be inventing a figure to make the sort come out right, and the
figure would then appear on the card. So it is a boolean, it sorts ahead, and
the reason says what it is.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from ppcway.opt import guardrails
from ppcway.rules.catalogue import Risk, Route, Rule

#: How much a safe change is preferred over a risky one at equal money. Small
#: on purpose: this breaks ties, it does not reorder the list.
RISK_WEIGHT: Final[dict[Risk, float]] = {
    Risk.LOW: 1.0,
    Risk.MEDIUM: 0.95,
    Risk.HIGH: 0.9,
}


@dataclass(frozen=True, slots=True)
class Impact:
    """What we expect this change to be worth, and how sure we are.

    `money_a_month` is signed from the merchant's point of view: positive is
    money they keep or gain. Zero is a real answer -- some findings are worth
    doing and worth nothing.
    """

    money_a_month: float
    currency: str
    #: Between 0 and 1. How much data is behind the finding, not how much we
    #: like it.
    confidence: float
    words: str
    #: True when something has stopped working rather than merely costing too
    #: much. Sorts ahead of money. See the module docstring.
    blocking: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence is a share between 0 and 1, and got {self.confidence}."
                f" A confidence above one would quietly reorder the whole inbox."
            )
        if self.money_a_month and not self.currency:
            raise ValueError(
                "an impact with money in it needs a currency: a figure without one is"
                " how a merchant in Toronto is shown euros."
            )


@dataclass(frozen=True, slots=True)
class Recommendation:
    """One change a rule is proposing, with everything a card and the log need."""

    rule: Rule
    customer_id: str
    #: What it acts on: "search_term", "ad", "campaign", "keyword".
    target_kind: str
    target_id: str
    target_label: str
    #: One sentence the merchant reads. Written from computed figures; a model
    #: may rewrite it for tone, and then every number in it is checked.
    reason: str
    impact: Impact
    #: Figure ids with as-of times, which is what the brief calls evidence.
    evidence: tuple[Mapping[str, Any], ...]
    #: How this gets put back, in words. "Not reversible" is also an answer.
    undo: str
    #: The state before and after, kept whole so an undo months later can build
    #: the opposite of this without guessing.
    before: Mapping[str, Any] = field(default_factory=dict)
    after: Mapping[str, Any] = field(default_factory=dict)
    reversible: bool = True
    #: When the figures behind it were last read from Google.
    as_of: datetime | None = None
    #: What the proposal would set, where it touches a number at all.
    new_daily_budget: float | None = None
    new_bid: float | None = None
    new_target_cpa: float | None = None
    change_pct: float | None = None
    pauses: int = 0
    resources: tuple[str, ...] = ()

    @property
    def risk(self) -> Risk:
        return self.rule.risk

    @property
    def route(self) -> Route:
        return self.rule.route

    @property
    def priority(self) -> float:
        """Money a month, weighted by how sure we are and slightly by risk."""
        return round(
            abs(self.impact.money_a_month) * self.impact.confidence * RISK_WEIGHT[self.rule.risk],
            2,
        )

    @property
    def rank(self) -> tuple[int, float]:
        """The sort key. Blocking first, then money. Descending on both."""
        return (1 if self.impact.blocking else 0, self.priority)

    def to_proposal(self) -> guardrails.Proposal:
        """The narrow, mechanical view the guardrails judge."""
        return guardrails.Proposal(
            kind=self.rule.kind,
            customer_id=self.customer_id,
            target_id=self.target_id,
            target_label=self.target_label,
            new_daily_budget=self.new_daily_budget,
            new_target_cpa=self.new_target_cpa,
            new_bid=self.new_bid,
            change_pct=self.change_pct,
            pauses=self.pauses,
            metrics_as_of=self.as_of,
            resources=self.resources,
        )

    def as_dict(self) -> dict[str, Any]:
        """What an inbox card is drawn from."""
        return {
            "rule_id": self.rule.id,
            "rule_version": self.rule.version,
            "kind": self.rule.kind,
            "title": self.rule.name,
            "about": self.rule.about,
            "target": {
                "kind": self.target_kind,
                "id": self.target_id,
                "label": self.target_label,
            },
            "reason": self.reason,
            "impact": {
                "money_a_month": round(self.impact.money_a_month, 2),
                "currency": self.impact.currency,
                "confidence": round(self.impact.confidence, 3),
                "words": self.impact.words,
                "blocking": self.impact.blocking,
            },
            "evidence": [dict(cite) for cite in self.evidence],
            "undo": self.undo,
            "reversible": self.reversible,
            "risk": self.risk.value,
            "route": self.route.value,
            "priority": self.priority,
            "as_of": self.as_of.isoformat() if self.as_of else None,
        }


def in_order(found: Sequence[Recommendation]) -> list[Recommendation]:
    """Highest first: blocking ahead of money, money ahead of everything."""
    return sorted(found, key=lambda r: r.rank, reverse=True)
