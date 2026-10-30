"""A figure, and the five things the brief asks every one of them to carry."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from ppcway.metric.figures import (
    FRESH_HOURS,
    Figure,
    Period,
    Scope,
    Unit,
    numbers_in,
    unmatched,
)
from ppcway.metric.verdicts import Verdict

UNTIL = date(2026, 10, 30)
AT = datetime(2026, 10, 30, 6, 0, tzinfo=UTC)
MONTH = Period.last(30, until=UNTIL)


def a_figure(**over: object) -> Figure:
    fields: dict[str, object] = {
        "name": "spend",
        "value": 412.5,
        "unit": Unit.MONEY,
        "currency": "CAD",
        "period": MONTH,
        "scope": Scope(kind="campaign", id="11"),
        "as_of": AT,
    }
    fields.update(over)
    return Figure(**fields)  # type: ignore[arg-type]


def test_the_id_is_stable_and_says_what_it_identifies() -> None:
    """The action log cites figures by id months later. A position in a list cannot be."""
    assert a_figure().id == "spend:campaign-11:2026-10-01..2026-10-30"


def test_two_figures_of_the_same_thing_have_the_same_id() -> None:
    """Same measurement, same scope, same window: the same figure, so it collides."""
    assert a_figure(value=1.0).id == a_figure(value=999.0).id


def test_the_id_changes_when_any_of_the_three_does() -> None:
    first = a_figure()
    assert a_figure(name="leads").id != first.id
    assert a_figure(scope=Scope(kind="account")).id != first.id
    assert a_figure(period=Period.last(7, until=UNTIL)).id != first.id


def test_money_without_a_currency_is_refused() -> None:
    """A float carries no currency, which is how a merchant in Toronto sees euros."""
    with pytest.raises(ValueError, match="has no currency"):
        a_figure(currency="")


def test_a_count_with_a_currency_is_refused() -> None:
    """A units bug otherwise found by a reader rather than a test."""
    with pytest.raises(ValueError, match="carries a currency"):
        a_figure(name="clicks", unit=Unit.COUNT, currency="CAD")


def test_a_naive_as_of_time_is_refused() -> None:
    with pytest.raises(ValueError, match="no time zone"):
        # Naive on purpose: this is the thing being refused. A naive timestamp
        # compared against an aware one raises, and compared against a wrong
        # assumption shifts the freshness window by hours without a word.
        a_figure(as_of=datetime(2026, 10, 30, 6, 0))  # noqa: DTZ001


def test_a_reversed_period_is_refused() -> None:
    """A backwards window reads as an empty one and makes every figure zero."""
    with pytest.raises(ValueError, match="cannot end before it starts"):
        Period(start=date(2026, 10, 30), end=date(2026, 10, 1))


def test_the_period_before_is_the_same_length_and_immediately_prior() -> None:
    before = MONTH.before()
    assert before.days == MONTH.days == 30
    assert before.end == date(2026, 9, 30)
    assert before.start == date(2026, 9, 1)


def test_freshness_is_a_question_a_figure_can_answer() -> None:
    """The guardrail refuses data older than 36 hours. This is what it asks."""
    figure = a_figure()
    assert figure.fresh(AT + timedelta(hours=FRESH_HOURS - 1))
    assert not figure.fresh(AT + timedelta(hours=FRESH_HOURS + 1))
    assert figure.age(AT + timedelta(hours=5)) == timedelta(hours=5)


def test_as_of_is_when_the_data_was_read_not_when_this_was_built() -> None:
    """A figure computed now from yesterday's numbers is a yesterday figure."""
    yesterday = AT - timedelta(days=1)
    figure = a_figure(as_of=yesterday)
    assert not figure.fresh(AT + timedelta(hours=13))


def test_what_the_action_log_stores_as_evidence() -> None:
    """The brief: evidence is figure ids with as-of times."""
    cited = a_figure(before=380.0, verdict=Verdict.REAL).cite()
    assert cited == {
        "id": "spend:campaign-11:2026-10-01..2026-10-30",
        "value": 412.5,
        "unit": "money",
        "as_of": "2026-10-30T06:00:00+00:00",
        "verdict": "real",
    }


def test_the_change_against_the_period_before() -> None:
    assert a_figure(before=380.0).change == 8.6
    assert a_figure(before=None).change is None
    assert a_figure(before=0.0).change is None, "a change from nothing is not a percentage"


@pytest.mark.parametrize(
    ("said", "found"),
    [
        ("You spent 412.50", [412.5]),
        ("1,240 clicks", [1240.0]),
        ("down 8.6%", [8.6]),
        ("$412.50 over 30 days", [412.5, 30.0]),
        ("no numbers here", []),
    ],
)
def test_the_numbers_a_sentence_claims(said: str, found: list[float]) -> None:
    assert numbers_in(said) == found


def test_an_honest_sentence_matches_its_figures() -> None:
    spend = a_figure(before=380.0)
    leads = a_figure(name="leads", value=11, before=8, unit=Unit.COUNT, currency="")
    said = "You spent 412.50 over 30 days, up 8.6%, and got 11 leads against 8 before."
    assert unmatched(said, [spend, leads]) == []


def test_an_invented_number_is_caught() -> None:
    """The whole point. A model that makes a figure up is stopped before a merchant reads it."""
    spend = a_figure(before=380.0)
    assert unmatched("You spent 412.50 and got 19 leads.", [spend]) == [19.0]


def test_a_ratio_may_be_said_as_a_percentage() -> None:
    """Stored as 0.05, written as 5%. Both are the same claim."""
    rate = a_figure(name="conversion_rate", value=0.05, unit=Unit.RATIO, currency="")
    assert unmatched("Five in a hundred, or 5%, got in touch.", [rate]) == []


def test_a_rounded_figure_is_still_the_figure() -> None:
    """The check is for invented numbers, not an argument about decimal places."""
    spend = a_figure(value=412.4999)
    assert unmatched("You spent about 412.50.", [spend]) == []


def test_a_caller_may_license_numbers_that_are_not_figures() -> None:
    """Explicit, because a checker that guessed would let an invented one through."""
    spend = a_figure()
    assert unmatched("Over the last 36 hours, 412.50.", [spend]) == [36.0]
    assert unmatched("Over the last 36 hours, 412.50.", [spend], also=[36]) == []


def test_small_counting_words_are_not_treated_as_claims() -> None:
    spend = a_figure()
    assert unmatched("Both of your 2 campaigns spent 412.50.", [spend]) == []
