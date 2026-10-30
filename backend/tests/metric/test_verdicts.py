"""Whether a difference means anything, which the automation also depends on."""

from __future__ import annotations

import pytest

from ppcway.metric.verdicts import (
    ENOUGH_CLICKS,
    ENOUGH_EVENTS,
    SURE,
    Verdict,
    for_counts,
    for_rate,
    poisson_z,
    rate_z,
)


def test_eleven_leads_then_eight_is_not_a_collapse() -> None:
    """The decision this module exists for, in the one example that motivated it."""
    verdict, words, test = for_counts(8, 11, what="leads")
    assert verdict is Verdict.NORMAL
    assert "normal range" in words
    assert test == "two Poisson counts"


def test_too_few_events_is_said_rather_than_guessed_at() -> None:
    verdict, words, _ = for_counts(2, 3, what="leads")
    assert verdict is Verdict.THIN
    assert "Too few leads" in words


def test_no_earlier_period_is_a_different_answer_from_too_little_data() -> None:
    """A screen can say the first. It should say the second."""
    none_verdict, _, test = for_counts(8, 0, what="leads")
    thin_verdict, _, _ = for_counts(2, 3, what="leads")
    assert none_verdict is Verdict.NONE
    assert thin_verdict is Verdict.THIN
    assert test == "", "no test was run, so none is named"


def test_a_large_move_on_enough_events_is_real() -> None:
    verdict, words, _ = for_counts(40, 11, what="leads")
    assert verdict is Verdict.REAL
    assert "up by more than the usual wobble" in words


def test_a_rate_needs_clicks_behind_it() -> None:
    verdict, words, _ = for_rate(2, 40, 3, 50)
    assert verdict is Verdict.THIN
    assert "Too few clicks" in words


def test_a_rate_that_really_moved() -> None:
    verdict, words, test = for_rate(60, 600, 20, 600)
    assert verdict is Verdict.REAL
    assert "better" in words
    assert test == "two proportions"


@pytest.mark.parametrize(
    ("verdict", "may_act"),
    [
        (Verdict.REAL, True),
        (Verdict.NORMAL, False),
        (Verdict.THIN, False),
        (Verdict.NONE, False),
    ],
)
def test_only_a_real_change_may_be_acted_on(verdict: Verdict, may_act: bool) -> None:
    """A proposal resting on NORMAL rests on noise; on THIN, on a guess."""
    assert verdict.actionable is may_act


def test_the_tests_are_symmetric_and_zero_safe() -> None:
    assert poisson_z(0, 0) == 0.0
    assert poisson_z(20, 10) == pytest.approx(-poisson_z(10, 20))
    assert rate_z(1, 0, 1, 10) == 0.0
    assert rate_z(1, 10, 1, 0) == 0.0


def test_the_thresholds_are_the_ones_the_decision_names() -> None:
    assert SURE == 1.96
    assert ENOUGH_EVENTS == 10
    assert ENOUGH_CLICKS == 100
