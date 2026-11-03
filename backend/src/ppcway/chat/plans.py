"""What each plan may ask Otto, and what PPCWay will spend answering.

Two different ceilings, and conflating them is the mistake this module exists
to avoid.

**A message cap is about fairness.** How many questions a plan includes, so
one merchant on the cheapest plan cannot use a hundred times what another on
the same plan does. It is a product decision and the numbers are the client's.

**A spend ceiling is about solvency.** What PPCWay is prepared to pay Anthropic
for one account in one month, whatever the message count. It exists because the
two are not proportional: one question about a year of search terms can cost
more than two hundred short ones, so a message cap alone does not bound the
bill. The brief asks for this one explicitly, with alerts at half and at four
fifths.

**The numbers below are assumptions, and are marked as such.** The client's
brief lists "which plans, monthly cap per plan, and the AI budget ceiling,
once pricing is final" as an open item for their call, and notes that our own
report still uses the $149 / $349 / $949 tiers. So these are those tiers, with
caps derived from them, and `ASSUMED` is checked by a test so that nobody can
quietly come to believe they were agreed. Changing them is changing a constant;
what matters is that the mechanism is right and the figures are visibly
provisional.

**Model prices are first-party rates, and Vertex is not first-party.** Claude
on Vertex AI is partner-operated and priced separately by Google. The rates
here are Anthropic's own published per-token prices, which is the closest
honest estimate available without the client's Google Cloud billing in front
of us, and the estimate is labelled everywhere it surfaces. It will be wrong;
the question is whether it is wrong by ten per cent or by a factor, and that is
answerable the first month there is a bill.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ppcway.model.jobs import HAIKU, OPUS, SONNET

#: True while the figures in this file are ours rather than the client's. A
#: test asserts it, so that it has to be changed deliberately along with them.
ASSUMED: Final = True


@dataclass(frozen=True, slots=True)
class Plan:
    """One plan's name, price, and what it may ask for."""

    name: str
    #: What the merchant pays a month, in the currency they are billed in.
    costs: float
    #: Questions a month. None means no cap, which no plan has today.
    questions_a_month: int
    #: What PPCWay will spend on model calls for this account in a month,
    #: before it stops answering. In US dollars, because that is what the bill
    #: arrives in whatever the merchant pays in.
    spend_ceiling_usd: float
    #: Whether this plan includes Otto at all.
    has_otto: bool = True


#: The tiers from PPCWay's own earlier report. Not agreed. See ASSUMED.
PLANS: Final[dict[str, Plan]] = {
    "starter": Plan(
        name="Starter",
        costs=149.0,
        questions_a_month=100,
        # About 8% of the plan price, which is the share the LLM report found
        # a typical account's model cost to be. Kept low because the cheapest
        # plan is the one somebody will point a script at.
        spend_ceiling_usd=12.0,
    ),
    "growth": Plan(
        name="Growth",
        costs=349.0,
        questions_a_month=400,
        spend_ceiling_usd=28.0,
    ),
    "agency": Plan(
        name="Agency",
        costs=949.0,
        questions_a_month=2000,
        spend_ceiling_usd=76.0,
    ),
}

#: What a plan nobody recognises gets: the most cautious one. A business whose
#: plan string was mistyped should be limited, not unlimited.
FALLBACK: Final = "starter"

#: Where the brief asks us to start saying something, and where to stop.
WARN_AT: Final = (0.50, 0.80)

#: Anthropic's own published per-million-token prices, for the three models
#: this platform uses. **Not Vertex prices**: Claude on Vertex AI is
#: partner-operated and priced by Google separately. These are the closest
#: honest estimate available until there is a Google Cloud bill to read, and
#: everything that surfaces a figure derived from them says it is an estimate.
PER_MILLION: Final[dict[str, tuple[float, float, float]]] = {
    # model: (input, output, cached input)
    SONNET: (2.00, 10.00, 0.20),
    HAIKU: (0.10, 0.50, 0.01),
    OPUS: (4.00, 20.00, 0.20),
}


def plan_for(name: str) -> Plan:
    """One plan by name, falling back to the most cautious rather than to none."""
    return PLANS.get((name or "").strip().lower(), PLANS[FALLBACK])


def cost_of(model: str, *, input_tokens: int, output_tokens: int, cached: int = 0) -> float:
    """An estimate of what one model call cost, in US dollars.

    Cached input is billed at a fraction of fresh input, so it is subtracted
    from the input count rather than added on top -- Anthropic's `usage`
    reports `input_tokens` and `cache_read_input_tokens` as separate figures
    where the cached ones are not also in the first, and getting that backwards
    would overstate every cached call.
    """
    prices = PER_MILLION.get(model)
    if prices is None:
        return 0.0
    rate_in, rate_out, rate_cached = prices
    fresh = max(0, input_tokens)
    return round(
        (fresh * rate_in + output_tokens * rate_out + max(0, cached) * rate_cached) / 1_000_000,
        6,
    )
