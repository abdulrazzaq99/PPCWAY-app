"""Where the month's spend is heading, and the two Google facts that shape it."""

from __future__ import annotations

from datetime import date

import pytest

from ppcway.metric.pacing import (
    ENOUGH_DAYS,
    GOOGLE_MONTH,
    Pace,
    project,
)

#: October has 31 days, which is the awkward case: 31 times a daily budget is
#: more than Google's own monthly cap of 30.4 times it.
OCT = date(2026, 10, 10)
#: November has 30, where the two nearly agree.
NOV = date(2026, 11, 10)


def test_spending_exactly_the_budget_is_on_pace_even_in_a_long_month() -> None:
    """31 x 10 is 310 against a cap of 304, so the naive check calls this capped.

    It is true and useless: a merchant spending precisely what they asked to
    spend must not be told every morning that they are running into a ceiling.
    """
    said = project(spent=100.0, daily_budget=10.0, today=OCT, currency="CAD")
    assert said.pace is Pace.ON
    assert said.runs_out_on is None


def test_spending_well_over_is_capped_and_says_when() -> None:
    said = project(spent=300.0, daily_budget=10.0, today=OCT, currency="CAD")
    assert said.pace is Pace.CAPPED
    assert said.projected == round(10.0 * GOOGLE_MONTH, 2)
    assert said.runs_out_on == date(2026, 10, 11)
    assert "will not charge more than" in said.words


def test_the_projection_never_exceeds_what_google_will_charge() -> None:
    """A projection above the cap is projecting something that cannot happen."""
    said = project(spent=1000.0, daily_budget=10.0, today=OCT)
    assert said.projected == said.most_google_will_charge == 304.0


def test_spending_well_under_is_reported_as_the_problem_it_is() -> None:
    said = project(spent=40.0, daily_budget=10.0, today=OCT, currency="CAD")
    assert said.pace is Pace.UNDER
    assert "not spending what they could" in said.words


@pytest.mark.parametrize("day", range(1, ENOUGH_DAYS))
def test_too_early_in_the_month_to_say(day: int) -> None:
    """Google may spend twice the daily budget on one day. Two Tuesdays prove nothing."""
    said = project(spent=40.0, daily_budget=10.0, today=date(2026, 10, day))
    assert said.pace is Pace.UNKNOWN
    assert "twice the daily budget" in said.words
    assert said.projected == 40.0, "and it does not pretend to project"


def test_no_budget_means_nothing_to_be_on_pace_with() -> None:
    said = project(spent=40.0, daily_budget=0.0, today=OCT)
    assert said.pace is Pace.UNKNOWN
    assert "No daily budget is set" in said.words


def test_a_thirty_day_month_behaves_the_same_way() -> None:
    said = project(spent=100.0, daily_budget=10.0, today=NOV, currency="CAD")
    assert said.pace is Pace.ON


def test_the_arithmetic_a_screen_shows_beside_the_verdict() -> None:
    said = project(spent=123.0, daily_budget=10.0, today=OCT, currency="CAD")
    assert said.days_gone == 10
    assert said.days_in_month == 31
    assert said.days_left == 21
    assert said.a_day_so_far == 12.30


def test_the_currency_is_said_rather_than_symbolised() -> None:
    """A bare symbol is the fastest way to show a Canadian merchant euros."""
    said = project(spent=40.0, daily_budget=10.0, today=OCT, currency="CAD")
    assert "CAD" in said.words
    assert "$" not in said.words
    assert "€" not in said.words
