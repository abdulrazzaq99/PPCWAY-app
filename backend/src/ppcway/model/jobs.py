"""Which model does which job, and how hard it is allowed to think.

The client's brief names three models for three kinds of work, and the split is
about money rather than taste: Haiku is roughly a twentieth of Opus per token,
and the jobs that run on a schedule for every account are the ones that would
otherwise dominate the bill. So the tier is a property of the job, decided here
once, and no caller picks a model.

A job, not a model, is what the rest of the application asks for. That is the
difference between "the weekly letter is written by Sonnet" -- a fact recorded
in one place and changeable in one place -- and a model name spelled out at
fifteen call sites, where the fifteenth is the one still on last year's model
when the bill arrives.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

#: Vertex AI takes the bare first-party model id for current-generation models,
#: with no publisher prefix and no date suffix. Only dated snapshots use the
#: `@version` form, and none of these are snapshots.
SONNET: Final = "claude-sonnet-5-5"
HAIKU: Final = "claude-haiku-5-5"
OPUS: Final = "claude-opus-5-5"


class Job(StrEnum):
    """Every kind of model work this platform does.

    An enum rather than a string, for the reason the audit's business kinds are
    one: `job="weekly"` is a spelling nothing has a tier for, and the failure
    would be a letter that silently cost twenty times what it should.
    """

    #: Answering a merchant's question about their account. Ask Otto, phase 3.
    CHAT = "chat"
    #: The sentence on an inbox card that says why we are proposing this.
    CARD_REASON = "card_reason"
    #: Monday's summary letter.
    WEEKLY_LETTER = "weekly_letter"
    #: Work no merchant is waiting for: classifying, tidying, summarising.
    INTERNAL = "internal"
    #: Headlines and descriptions for the campaign builder.
    AD_DRAFT = "ad_draft"


@dataclass(frozen=True, slots=True)
class Tier:
    """One job's model, effort and ceiling."""

    model: str
    #: Vertex and the Claude API both read this inside `output_config`. The
    #: default differs by model -- medium on Opus 5.5 and Haiku 5.5, high on
    #: Sonnet 5.5 -- so every tier states it rather than inheriting a default
    #: that would change the bill if Anthropic changed the default.
    effort: str
    max_tokens: int

    def __post_init__(self) -> None:
        if self.effort not in EFFORTS:
            raise ValueError(
                f"effort must be one of {', '.join(EFFORTS)}, not {self.effort!r}:"
                f" an unrecognised level is rejected by the API at request time,"
                f" which is a worse place to find out than here."
            )


#: What `output_config.effort` accepts. Restated rather than imported, because
#: it is a string on the wire and this is where a typo should be caught.
EFFORTS: Final = ("low", "medium", "high", "xhigh", "max")

#: The brief's own allocation. Sonnet for anything a person reads, Haiku for
#: the jobs behind it, Opus for the one job where the words are the product.
TIERS: Final[dict[Job, Tier]] = {
    # Low effort for chat: the brief asks for first words in two seconds and a
    # full answer in eight at p95, and the levels were recalibrated on Sonnet
    # 5.5 such that low is where everyday conversation belongs.
    Job.CHAT: Tier(model=SONNET, effort="low", max_tokens=4_000),
    # A card's reason is one sentence over figures that are already computed.
    # The model is writing, not working anything out, and must not: every
    # number in it is checked against the figures it was given.
    Job.CARD_REASON: Tier(model=SONNET, effort="low", max_tokens=1_000),
    Job.WEEKLY_LETTER: Tier(model=SONNET, effort="medium", max_tokens=4_000),
    Job.INTERNAL: Tier(model=HAIKU, effort="low", max_tokens=2_000),
    # Fifteen headlines and four descriptions that have to survive the
    # validator, and a retry costs more than the effort does.
    Job.AD_DRAFT: Tier(model=OPUS, effort="high", max_tokens=8_000),
}


def tier_for(job: Job) -> Tier:
    """The tier for one job, refusing rather than guessing at an unknown one."""
    try:
        return TIERS[Job(job)]
    except (KeyError, ValueError):
        raise ValueError(
            f"no model tier is defined for job {job!r}. Every job names its own"
            f" model, effort and ceiling in TIERS; a job without one would"
            f" otherwise pick up whatever default the API has that week."
        ) from None
