"""The card's sentence: one rewrite, then the computed words, and never a crash.

No model is called. The service is injected, which is the only way to assert
what happens when a model invents a figure -- the case this whole module exists
for, and the one a live model obligingly refuses to produce on demand.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from ppcway.metric.figures import Figure, Period, Scope, Unit
from ppcway.model.jobs import SONNET, Job
from ppcway.model.service import Models, ModelUnavailable
from ppcway.rules.catalogue import rule
from ppcway.rules.recommend import Impact, Recommendation
from ppcway.rules.words import (
    FROM_MODEL,
    FROM_REWRITE,
    FROM_TEMPLATE,
    reason_for,
)

WINDOW = Period.last(30, until=date(2026, 10, 30))
AT = datetime(2026, 10, 30, 6, 0, tzinfo=UTC)
SCOPE = Scope(kind="search_term", id="abc123")

TEMPLATE = (
    'People searching for "boiler repair jobs" clicked 140 times in the last 30 days'
    " and cost you 96.00 CAD. None of them got in touch."
)


def a_card() -> Recommendation:
    return Recommendation(
        rule=rule("R1"),
        customer_id="1",
        target_kind="search_term",
        target_id="abc123",
        target_label="boiler repair jobs",
        reason=TEMPLATE,
        impact=Impact(
            money_a_month=97.28,
            currency="CAD",
            confidence=0.8,
            words="Excluding it stops about 97.28 CAD a month.",
        ),
        figures=(
            Figure(
                name="search_term_spend",
                value=96.0,
                unit=Unit.MONEY,
                currency="CAD",
                period=WINDOW,
                scope=SCOPE,
                as_of=AT,
            ),
            Figure(
                name="search_term_clicks",
                value=140.0,
                unit=Unit.COUNT,
                period=WINDOW,
                scope=SCOPE,
                as_of=AT,
            ),
        ),
        undo="Remove the negative keyword.",
        as_of=AT,
    )


class Saying:
    """A model service that returns a scripted answer per attempt."""

    def __init__(self, *answers: str | Exception) -> None:
        self._answers = list(answers)
        self.asked: list[dict[str, Any]] = []

    def ask(self, job: Job, **kwargs: Any) -> Any:
        self.asked.append({"job": job, **kwargs})
        said = self._answers.pop(0) if self._answers else ""
        if isinstance(said, Exception):
            raise said
        from ppcway.model.service import Answer

        return Answer(text=said, model=SONNET, prompt_version="otto-test")


def _models(*answers: str | Exception) -> Any:
    return Saying(*answers)


def test_a_good_rewrite_is_used() -> None:
    said = reason_for(
        _models("140 clicks on “boiler repair jobs” cost you 96.00 CAD and nobody rang."),
        a_card(),
    )
    assert said.source == FROM_MODEL
    assert said.asked == 1
    assert "96.00" in said.text
    assert not said.is_ours


def test_an_invented_number_is_rejected_and_rewritten_once() -> None:
    """The case the module exists for. 19 is in no figure."""
    models = _models(
        "You wasted 96.00 CAD on 19 wasted leads.",
        "140 clicks cost you 96.00 CAD and none of them got in touch.",
    )
    said = reason_for(models, a_card())
    assert said.source == FROM_REWRITE
    assert said.asked == 2
    assert said.refused and "19" in said.refused[0]
    assert "19" not in said.text


def test_the_rewrite_prompt_says_which_number_was_wrong() -> None:
    """ "Try again" produces another invented number about as often."""
    models = _models("96.00 CAD and 19 leads.", "96.00 CAD, nobody rang.")
    reason_for(models, a_card())
    second = models.asked[1]["said"]
    assert "rejected" in second
    assert "19" in second


def test_two_invented_attempts_fall_back_to_our_own_words() -> None:
    """One rewrite, then the fixed template. No third try."""
    models = _models("96.00 and 19 leads", "96.00 and 23 leads")
    said = reason_for(models, a_card())
    assert said.source == FROM_TEMPLATE
    assert said.text == TEMPLATE
    assert said.asked == 2
    assert len(said.refused) == 2
    assert len(models.asked) == 2, "the brief says one rewrite, so exactly two attempts"


def test_an_unreachable_model_leaves_a_perfectly_good_card() -> None:
    said = reason_for(_models(ModelUnavailable("502")), a_card())
    assert said.source == FROM_TEMPLATE
    assert said.text == TEMPLATE
    assert said.is_ours


def test_a_refusal_leaves_a_perfectly_good_card() -> None:
    said = reason_for(_models(""), a_card())
    assert said.source == FROM_TEMPLATE
    assert said.text == TEMPLATE


def test_the_expected_effect_may_be_quoted_though_it_is_not_a_figure() -> None:
    """It is derived from one, so the caller licenses it rather than the checker guessing."""
    said = reason_for(_models("Excluding this saves about 97.28 CAD a month."), a_card())
    assert said.source == FROM_MODEL


def test_the_card_asks_the_right_job_so_the_right_model_answers() -> None:
    models = _models("96.00 CAD, nobody rang.")
    reason_for(models, a_card())
    assert models.asked[0]["job"] is Job.CARD_REASON


def test_the_figures_go_before_the_sentence_in_the_prompt() -> None:
    """The figures are the stable part and the cache is a prefix match."""
    models = _models("96.00 CAD, nobody rang.")
    reason_for(models, a_card())
    asked = models.asked[0]["said"]
    assert asked.index("FIGURES") < asked.index("SENTENCE TO REWRITE")
    assert "search term spend: 96.00 CAD" in asked
    assert "140" in asked


def test_the_instruction_forbids_adding_a_cause() -> None:
    """The number check cannot catch an invented claim, so the prompt has to."""
    models = _models("96.00 CAD, nobody rang.")
    reason_for(models, a_card())
    system = models.asked[0]["system"]
    assert "Do not add a cause" in system
    assert "Use only the numbers listed under FIGURES" in system


def test_a_real_model_service_is_what_this_is_shaped_for() -> None:
    """The fake above stands in for `Models`, so it has to match its one method."""
    assert hasattr(Models, "ask")
    assert callable(Models.ask)


@pytest.mark.parametrize(
    "said",
    [
        "140 clicks cost 96 CAD.",
        "140 clicks cost 96.0 CAD.",
        "About 96.00 CAD over 30 days.",
    ],
)
def test_rounding_is_not_treated_as_invention(said: str) -> None:
    """The check is for made-up figures, not an argument about decimal places."""
    assert reason_for(_models(said), a_card()).source == FROM_MODEL
