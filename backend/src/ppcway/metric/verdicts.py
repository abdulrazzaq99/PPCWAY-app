"""Whether a difference between two numbers means anything.

Moved here from `ads.reports`, where it was written for the dashboard, because
phases 1 to 4 need the same answer and a second copy of a statistical test is
a second copy that disagrees. The decision it implements is recorded in
`docs/decisions/2026-10-20-the-report-gives-a-verdict-not-an-arrow.md`.

Eleven leads last month and eight this month is not a thirty per cent collapse;
it is eleven and eight. Most accounts PPCway serves have single-figure monthly
lead counts, where period-on-period noise is larger than almost any real
effect, and a screen that prints the arrow without the arithmetic teaches a
small business owner to panic on a Tuesday and spend money fixing nothing.

The same reasoning is what makes this module load-bearing for the automation
rather than only for the screens. A rule that acts on a difference it cannot
show to be real is a rule that spends somebody's money on noise.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Final

#: Two standard errors: a difference this big or bigger would turn up by
#: chance less than about one time in twenty.
SURE: Final = 1.96

#: Below this many events across both periods the test is not worth running.
#: The honest answer is that nobody can tell.
ENOUGH_EVENTS: Final = 10

#: And below this many clicks, a rate is not worth comparing either.
ENOUGH_CLICKS: Final = 100


class Verdict(StrEnum):
    """What a comparison between two periods is worth.

    `NONE` and `THIN` are different answers and the difference matters: there
    was nothing to compare against, versus there was and it is too small to
    read. A screen can say the first and should say the second.
    """

    #: The difference is larger than the usual wobble.
    REAL = "real"
    #: There is a difference and it is the size of ordinary noise.
    NORMAL = "normal"
    #: Too little data for the question to have an answer.
    THIN = "thin"
    #: No test applies, or there is no earlier period.
    NONE = "none"

    @property
    def actionable(self) -> bool:
        """Whether an automated change may be based on this.

        Only `REAL`. This is the property the rules engine reads, and it is
        the whole reason this module is not just presentation: a proposal
        resting on `NORMAL` is a proposal resting on noise, and one resting on
        `THIN` is a guess wearing a number.
        """
        return self is Verdict.REAL


def poisson_z(now: float, before: float) -> float:
    """Two counts of rare events, compared. Zero when there is nothing to compare."""
    total = now + before
    return (now - before) / math.sqrt(total) if total > 0 else 0.0


def rate_z(hits_now: float, of_now: int, hits_before: float, of_before: int) -> float:
    """Two shares of two totals, compared the ordinary way."""
    if of_now <= 0 or of_before <= 0:
        return 0.0
    p_now, p_before = hits_now / of_now, hits_before / of_before
    pooled = (hits_now + hits_before) / (of_now + of_before)
    spread = math.sqrt(pooled * (1 - pooled) * (1 / of_now + 1 / of_before))
    return (p_now - p_before) / spread if spread > 0 else 0.0


def for_counts(now: float, before: float, *, what: str) -> tuple[str, str, str]:
    """A verdict, its sentence and the name of the test, for a count of events."""
    test = "two Poisson counts"
    if before <= 0:
        return Verdict.NONE, f"There is no earlier period to compare these {what} with.", ""
    if now + before < ENOUGH_EVENTS:
        return (
            Verdict.THIN,
            f"Too few {what} in both periods to tell a real change from chance.",
            test,
        )
    z = poisson_z(now, before)
    if abs(z) >= SURE:
        way = "up" if z > 0 else "down"
        return (
            Verdict.REAL,
            f"A real change: {what} are {way} by more than the usual wobble.",
            test,
        )
    return Verdict.NORMAL, f"Within the normal range for {what} at this volume.", test


def for_rate(
    hits_now: float, of_now: int, hits_before: float, of_before: int
) -> tuple[str, str, str]:
    """The same, for a share of a total rather than a count."""
    test = "two proportions"
    if of_before <= 0:
        return Verdict.NONE, "There is no earlier period to compare this rate with.", ""
    if of_now + of_before < ENOUGH_CLICKS:
        return Verdict.THIN, "Too few clicks in both periods for the rate to mean anything.", test
    z = rate_z(hits_now, of_now, hits_before, of_before)
    if abs(z) >= SURE:
        way = "better" if z > 0 else "worse"
        return (
            Verdict.REAL,
            f"A real change: the rate is {way} by more than the usual wobble.",
            test,
        )
    return Verdict.NORMAL, "Within the normal range for this many clicks.", test
