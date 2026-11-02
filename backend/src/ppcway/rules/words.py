"""The sentence on a card: computed first, then rewritten, then checked.

The brief: *the model writes the reason from computed figures with the number
check*, and *every number matched to that turn's tool results; one rewrite,
then a fixed template*. This is that, and the order of those three words
matters more than it looks.

**Computed first.** The rule already produces a correct sentence from the
figures. The model is not asked what to say, only to say the same thing better,
and if it cannot, the computed sentence is what ships. That makes the model an
improvement on the words rather than the source of them, which is the only
arrangement where a bad generation costs tone instead of truth.

**Then checked.** Every number in what comes back has to be one the figures
licence. One rewrite naming the offending number, and then the computed
sentence, exactly as the brief specifies -- no third attempt, because a model
that has invented a figure twice is not going to be talked out of it and a
merchant is waiting.

**What this does not catch, said plainly.** The number check finds invented
*numbers*. It does not find an invented *claim*: "your competitors have raised
their bids" contains no digits and would pass. Three things hold that down and
none of them is this function -- the prompt gives the model the computed
sentence and asks for a rewrite rather than an explanation, the card shows the
figures next to the words so a claim with nothing behind it has nothing beside
it either, and the rule's own sentence is always available as the fallback. A
reviewer should not read a passing number check as "the sentence is true".
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from ppcway.metric.figures import Figure, unmatched
from ppcway.model.jobs import Job
from ppcway.model.service import Models, ModelUnavailable
from ppcway.rules.recommend import Recommendation

log = logging.getLogger(__name__)

#: How the words may be arrived at.
FROM_MODEL: Final = "model"
FROM_REWRITE: Final = "rewrite"
FROM_TEMPLATE: Final = "template"

HOW_TO_WRITE: Final = """You rewrite one sentence for a small business owner who runs Google Ads and \
has about thirty seconds. You are not explaining, analysing or advising: a \
correct sentence has already been written from the figures, and your only job \
is to say the same thing in warmer, plainer words.

Rules you may not break:
- Use only the numbers listed under FIGURES. Do not add a number, round one \
differently, work one out, or mention a number that is not there.
- Do not add a cause, a comparison or a prediction. If the sentence does not \
say why, neither do you.
- Two sentences at most. No greeting, no sign-off, no bullet points, no \
markdown.
- British English. Plain words. A number before a judgement.

Reply with the rewritten sentence and nothing else."""


@dataclass(frozen=True, slots=True)
class Written:
    """The words that will go on the card, and where they came from."""

    text: str
    #: "model", "rewrite" or "template".
    source: str
    #: How many times the model was asked. Zero when it was never reachable.
    asked: int = 0
    #: What was refused and why, kept for the prompt log and for a screen that
    #: wants to say the words are ours rather than the model's.
    refused: tuple[str, ...] = ()

    @property
    def is_ours(self) -> bool:
        """True when a person is reading the computed sentence, not a model's."""
        return self.source == FROM_TEMPLATE


def reason_for(
    models: Models,
    found: Recommendation,
    *,
    also: Iterable[float] = (),
) -> Written:
    """The sentence for one card. Falls back to the rule's own words, always.

    Never raises. A card whose words could not be improved is a card; a card
    that crashed is an empty inbox.
    """
    licensed = (*also, found.impact.money_a_month, found.priority)
    asked = _prompt(found)

    said = _ask(models, found, asked)
    if said is None:
        return Written(text=found.reason, source=FROM_TEMPLATE)

    wrong = unmatched(said, found.figures, also=licensed)
    if not wrong:
        return Written(text=said, source=FROM_MODEL, asked=1)

    # One rewrite, naming what was wrong with the last one. Specific, because
    # "try again" produces another invented number about as often.
    again = _ask(
        models,
        found,
        f"{asked}\n\nYour last attempt was:\n{said}\n\nIt is rejected: it used"
        f" {', '.join(_plain(n) for n in wrong)}, which is not in FIGURES. Write it"
        f" again using only the numbers listed there.",
    )
    if again is not None and not unmatched(again, found.figures, also=licensed):
        return Written(text=again, source=FROM_REWRITE, asked=2, refused=(said,))

    log.info(
        "the card for %s kept its computed words: the model used numbers that were not there",
        found.rule.id,
    )
    return Written(
        text=found.reason,
        source=FROM_TEMPLATE,
        asked=2,
        refused=(said,) if again is None else (said, again),
    )


def _ask(models: Models, found: Recommendation, asked: str) -> str | None:
    """One attempt. None where the model could not be reached or declined."""
    try:
        answer = models.ask(
            Job.CARD_REASON,
            system=HOW_TO_WRITE,
            said=asked,
            customer_id=found.customer_id,
        )
    except ModelUnavailable as exc:
        log.info("the card for %s kept its computed words: %s", found.rule.id, exc)
        return None
    if answer.refused or not answer.text.strip():
        return None
    return answer.text.strip()


def _prompt(found: Recommendation) -> str:
    """The figures, then the sentence to rewrite. In that order on purpose.

    The figures come first because they are the stable part of the prompt and
    the cache is a prefix match; the sentence changes per card and goes last.
    """
    return "\n".join(
        (
            "FIGURES",
            *(f"- {_describe(figure)}" for figure in found.figures),
            (
                f"- expected effect: {found.impact.money_a_month:,.2f}"
                f" {found.impact.currency} a month"
            ),
            "",
            "SENTENCE TO REWRITE",
            found.reason,
        )
    )


def _describe(figure: Figure) -> str:
    """One figure, in words the model can only copy from."""
    value = f"{figure.value:,.2f}" if figure.unit.value == "money" else f"{figure.value:,.10g}"
    unit = f" {figure.currency}" if figure.currency else ""
    return (
        f"{figure.name.replace('_', ' ')}: {value}{unit}"
        f" over {figure.period.days} days to {figure.period.end.isoformat()}"
    )


def _plain(number: float) -> str:
    return f"{number:,.10g}"
