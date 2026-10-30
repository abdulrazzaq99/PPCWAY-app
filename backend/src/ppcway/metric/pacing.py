"""Where this month's spend is heading, and when the money runs out.

The brief asks for a budget projection. The naive one -- spend so far divided
by days so far, times the length of the month -- is wrong twice over, and both
corrections matter to a merchant deciding whether to panic.

**Google may spend up to twice the daily budget on a single day.** So a Tuesday
that cost double is not an overspend and must not be reported as one. Two days
into a month, the honest answer to "are we on pace" is that it is too early to
say, and this says so rather than extrapolating from noise.

**Google will not charge more than 30.4 times the daily budget in a month.**
That is a contractual cap, not a tendency, so a projection that exceeds it is
projecting something that cannot happen. The projection is capped, and says
when it has been.

The figure 30.4 is Google's own average month length; `ads.numbers.MONTH` holds
the same number for the dashboard's arithmetic, and the two should be
consolidated the next time either is touched.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Final

#: Google's own average month, used for the monthly charging cap.
GOOGLE_MONTH: Final = 30.4

#: Google's own daily ceiling: it may spend up to twice the daily budget on any
#: given day, and routinely does on a day that converts well.
DAILY_CEILING: Final = 2.0

#: Fewer days than this into the month and a projection is extrapolating from
#: noise. Two good Tuesdays would read as a fifty per cent overspend.
ENOUGH_DAYS: Final = 3

#: How far either side of the budget counts as on pace. Google's own pacing is
#: not smooth, and a merchant told they are 4% over every other morning stops
#: reading the emails.
TOLERANCE: Final = 0.10


class Pace(StrEnum):
    """What the month is doing."""

    #: Heading for roughly the budget, within the tolerance.
    ON = "on_pace"
    #: Heading to underspend. Often the more expensive problem of the two.
    UNDER = "under"
    #: Heading to overspend, as far as Google's cap allows.
    OVER = "over"
    #: The projection hit Google's monthly cap, so spend stops there.
    CAPPED = "capped"
    #: Too early in the month, or no budget set, to say anything.
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Projection:
    """Where the month ends up, and what that is worth saying."""

    spent: float
    daily_budget: float
    days_gone: int
    days_in_month: int
    #: What the month ends at if the rest of it looks like the part so far,
    #: capped at what Google will actually charge.
    projected: float
    #: The most Google will charge this month whatever happens.
    most_google_will_charge: float
    pace: Pace
    words: str
    #: The day the month's allowance is used up, where that happens before the
    #: month ends. None when it does not.
    runs_out_on: date | None = None
    currency: str = ""

    @property
    def days_left(self) -> int:
        return max(0, self.days_in_month - self.days_gone)

    @property
    def a_day_so_far(self) -> float:
        return round(self.spent / self.days_gone, 2) if self.days_gone else 0.0


def project(
    *,
    spent: float,
    daily_budget: float,
    today: date,
    currency: str = "",
) -> Projection:
    """Where this month's spend is heading, from the month so far.

    `spent` is month-to-date, `daily_budget` is what the account is set to
    spend a day. Both in the account's own currency, never micros.
    """
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_gone = today.day
    ceiling = round(daily_budget * GOOGLE_MONTH, 2)

    if daily_budget <= 0:
        return Projection(
            spent=spent,
            daily_budget=daily_budget,
            days_gone=days_gone,
            days_in_month=days_in_month,
            projected=spent,
            most_google_will_charge=0.0,
            pace=Pace.UNKNOWN,
            words="No daily budget is set, so there is nothing to be on pace with.",
            currency=currency,
        )

    if days_gone < ENOUGH_DAYS:
        return Projection(
            spent=spent,
            daily_budget=daily_budget,
            days_gone=days_gone,
            days_in_month=days_in_month,
            projected=spent,
            most_google_will_charge=ceiling,
            pace=Pace.UNKNOWN,
            words=(
                f"Only {days_gone} {'day' if days_gone == 1 else 'days'} into the month."
                " Google can spend up to twice the daily budget on any one day, so"
                " this early a projection would be guesswork."
            ),
            currency=currency,
        )

    a_day = spent / days_gone
    straight = a_day * days_in_month
    projected = round(min(straight, ceiling), 2)
    # What the merchant planned to spend, which in a 31-day month is *more*
    # than Google will charge: 31 times the daily budget is 310 against a cap
    # of 304. So the plan is capped too, or spending exactly the daily budget
    # every day would be reported as running into the cap -- which is true,
    # and useless, and alarming.
    expected = round(min(daily_budget * days_in_month, ceiling), 2)

    # And the cap is only worth mentioning when it will actually bite, rather
    # than whenever the arithmetic grazes it.
    will_be_capped = straight > ceiling * (1 + TOLERANCE)

    runs_out: date | None = None
    if a_day > 0 and will_be_capped:
        # The day the monthly cap is reached, at the rate so far.
        day = min(days_in_month, max(1, int(ceiling // a_day) + 1))
        runs_out = date(today.year, today.month, day)

    if will_be_capped:
        pace = Pace.CAPPED
        words = (
            f"At {_money(a_day, currency)} a day this month would reach"
            f" {_money(straight, currency)}, but Google will not charge more than"
            f" {_money(ceiling, currency)} in a month, so spend stops there."
        )
    elif projected > expected * (1 + TOLERANCE):
        pace = Pace.OVER
        words = (
            f"Heading for {_money(projected, currency)} this month against a budget of"
            f" {_money(expected, currency)}. Running faster than planned."
        )
    elif projected < expected * (1 - TOLERANCE):
        pace = Pace.UNDER
        words = (
            f"Heading for {_money(projected, currency)} this month against a budget of"
            f" {_money(expected, currency)}. The ads are not spending what they could,"
            f" which usually means they are not showing as often as they could."
        )
    else:
        pace = Pace.ON
        words = (
            f"Heading for {_money(projected, currency)} this month, which is about the"
            f" {_money(expected, currency)} planned."
        )

    return Projection(
        spent=spent,
        daily_budget=daily_budget,
        days_gone=days_gone,
        days_in_month=days_in_month,
        projected=projected,
        most_google_will_charge=ceiling,
        pace=pace,
        words=words,
        runs_out_on=runs_out,
        currency=currency,
    )


def _money(amount: float, currency: str) -> str:
    """An amount in words, with the currency said rather than symbolised.

    A bare symbol is the fastest way to show a Canadian merchant euros; the
    code beside the number cannot be mistaken.
    """
    whole = f"{amount:,.2f}"
    return f"{whole} {currency}".strip() if currency else whole
