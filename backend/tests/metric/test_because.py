"""Why a figure moved: arithmetic that adds up, and silence when it should not."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from ppcway.metric.because import because, split
from ppcway.metric.figures import Figure, Period, Scope, Unit
from ppcway.metric.verdicts import Verdict

MONTH = Period.last(30, until=date(2026, 10, 30))
AT = datetime(2026, 10, 30, 6, 0, tzinfo=UTC)


def f(
    name: str,
    value: float,
    before: float | None,
    *,
    unit: Unit = Unit.COUNT,
    currency: str = "",
    verdict: Verdict = Verdict.REAL,
    words: str = "",
) -> Figure:
    return Figure(
        name=name,
        value=value,
        before=before,
        unit=unit,
        currency=currency,
        period=MONTH,
        scope=Scope(kind="account"),
        as_of=AT,
        verdict=verdict,
        words=words,
    )


@pytest.mark.parametrize(
    ("a0", "a1", "b0", "b1"),
    [
        (10.0, 12.0, 2.0, 3.0),
        (10.0, 5.0, 2.0, 8.0),
        (0.5, 0.25, 100.0, 400.0),
        (7.0, 7.0, 3.0, 9.0),
        (-4.0, 6.0, 2.0, -1.0),
    ],
)
def test_the_split_is_exact_with_no_residual(a0: float, a1: float, b0: float, b1: float) -> None:
    """Both terms sum to the whole change, always. The algebra, asserted."""
    one, two = split(a1, a0, b1, b0)
    assert one + two == pytest.approx(a1 * b1 - a0 * b0)


def test_the_split_does_not_depend_on_which_factor_goes_first() -> None:
    """The asymmetric version gives a different answer per order, and order is arbitrary."""
    one, two = split(12.0, 10.0, 3.0, 2.0)
    two_again, one_again = split(3.0, 2.0, 12.0, 10.0)
    assert (one, two) == pytest.approx((one_again, two_again))


def test_a_rising_cost_per_lead_is_blamed_on_the_right_thing() -> None:
    """Clicks got slightly dearer; far fewer of them got in touch. The second one did it."""
    said = because(
        f("cost_per_lead", 47.0, 32.0, unit=Unit.MONEY, currency="CAD"),
        {
            "cost_per_click": f("cost_per_click", 2.35, 2.24, unit=Unit.MONEY, currency="CAD"),
            "conversion_rate": f("conversion_rate", 0.05, 0.07, unit=Unit.RATIO),
        },
    )
    assert said.explained
    assert said.change == 15.0
    assert sum(part.amount for part in said.factors) == pytest.approx(15.0)

    blamed = max(said.factors, key=lambda p: abs(p.amount))
    assert blamed.name == "conversion_rate"
    assert blamed.share > 0.8
    assert blamed.moved == "fell", "a conversion rate that fell is what pushes a cost per lead up"
    assert "got in touch" in said.words


def test_leads_split_between_clicks_and_the_rate() -> None:
    said = because(
        f("leads", 22.0, 11.0),
        {
            "clicks": f("clicks", 400.0, 320.0),
            "conversion_rate": f("conversion_rate", 0.055, 0.034375, unit=Unit.RATIO),
        },
    )
    assert said.explained
    assert sum(part.amount for part in said.factors) == pytest.approx(11.0)
    assert {part.name for part in said.factors} == {"clicks", "conversion_rate"}


def test_two_factors_pulling_against_each_other_are_not_hidden() -> None:
    """More clicks, a worse rate. A share over 1 or below 0 is the interesting case."""
    said = because(
        f("leads", 12.0, 11.0),
        {
            "clicks": f("clicks", 800.0, 320.0),
            "conversion_rate": f("conversion_rate", 0.015, 0.034375, unit=Unit.RATIO),
        },
    )
    assert said.explained
    shares = sorted(part.share for part in said.factors)
    assert shares[0] < 0 < shares[-1], "one factor pushed up, the other pulled down"
    assert sum(part.amount for part in said.factors) == pytest.approx(1.0)


def test_a_change_that_is_not_real_is_not_explained() -> None:
    """A confident story about noise is worse than silence: somebody acts on it."""
    said = because(
        f(
            "cost_per_lead",
            47.0,
            41.0,
            unit=Unit.MONEY,
            currency="CAD",
            verdict=Verdict.THIN,
            words="Too few leads in both periods to tell a real change from chance.",
        ),
        {},
    )
    assert not said.explained
    assert "Too few leads" in said.words
    assert said.factors == ()


def test_a_change_within_the_normal_range_is_not_explained_either() -> None:
    said = because(
        f("leads", 12.0, 11.0, verdict=Verdict.NORMAL, words="Within the normal range."),
        {
            "clicks": f("clicks", 400.0, 320.0),
            "conversion_rate": f("conversion_rate", 0.03, 0.034, unit=Unit.RATIO),
        },
    )
    assert not said.explained


def test_a_figure_measured_directly_has_nothing_to_split() -> None:
    said = because(f("impressions", 9000.0, 8000.0), {})
    assert not said.explained
    assert "measured directly" in said.words


def test_a_missing_factor_says_so_rather_than_raising() -> None:
    """A card with no explanation is a card. A crash is not."""
    said = because(
        f("leads", 22.0, 11.0),
        {"clicks": f("clicks", 400.0, 320.0)},
    )
    assert not said.explained
    assert "cannot be split up" in said.words


def test_a_factor_with_no_earlier_value_says_so() -> None:
    said = because(
        f("leads", 22.0, 11.0),
        {
            "clicks": f("clicks", 400.0, None),
            "conversion_rate": f("conversion_rate", 0.055, 0.034, unit=Unit.RATIO),
        },
    )
    assert not said.explained


def test_a_zero_rate_has_nowhere_for_the_arithmetic_to_start() -> None:
    said = because(
        f("cost_per_lead", 47.0, 32.0, unit=Unit.MONEY, currency="CAD"),
        {
            "cost_per_click": f("cost_per_click", 2.35, 2.24, unit=Unit.MONEY, currency="CAD"),
            "conversion_rate": f("conversion_rate", 0.05, 0.0, unit=Unit.RATIO),
        },
    )
    assert not said.explained
    assert "was zero" in said.words


def test_nothing_to_compare_against_is_its_own_answer() -> None:
    said = because(f("leads", 22.0, None), {})
    assert not said.explained
    assert "no earlier period" in said.words
