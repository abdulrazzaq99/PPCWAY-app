"""The report: this period, the one before it, and the same period a year ago.

A small advertiser's commonest mistake, after judging a campaign in its first
week, is reading noise as news. Eleven leads last month and eight this month is
not a thirty per cent collapse; it is eleven and eight. A report that prints the
arrow without the arithmetic teaches somebody to panic on a Tuesday and spend
money fixing nothing.

So every figure here carries a verdict in plain words — a real change, within
the normal range, or too little to tell — and the test behind it is named on the
screen next to the number.

What the tests are.

  Leads are counts of rare events, so two periods are compared as two Poisson
  counts: the difference divided by the square root of their total. Beyond about
  two of those, a difference that size would turn up by chance less than one
  time in twenty.

  Lead rate is a share of clicks, so it is the ordinary two-proportion test.

  Spend and clicks get no verdict at all, and the report says why: spend is a
  decision somebody made, not a measurement with noise in it. Testing it for
  significance would be answering a question nobody asked.

Nothing here invents history. A year-on-year column appears when a year is held
and says how much we hold when it is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ppcway.ads.numbers import Day, Held, Row, account_numbers, plain_money

#: Two standard errors: a difference this big or bigger would turn up by chance
#: less than about one time in twenty.
SURE = 1.96

#: Below this many events across both periods, the test is not worth running —
#: the honest answer is that nobody can tell.
ENOUGH_EVENTS = 10

#: And below this many clicks, a rate is not worth comparing either.
ENOUGH_CLICKS = 100

#: A year, for the year-on-year column.
YEAR = 365


def _poisson_z(now: float, before: float) -> float:
    """Two counts of rare events, compared. Zero when there is nothing to compare."""
    total = now + before
    return (now - before) / math.sqrt(total) if total > 0 else 0.0


def _rate_z(hits_now: float, of_now: int, hits_before: float, of_before: int) -> float:
    """Two shares of two totals, compared the ordinary way."""
    if of_now <= 0 or of_before <= 0:
        return 0.0
    p_now, p_before = hits_now / of_now, hits_before / of_before
    pooled = (hits_now + hits_before) / (of_now + of_before)
    spread = math.sqrt(pooled * (1 - pooled) * (1 / of_now + 1 / of_before))
    return (p_now - p_before) / spread if spread > 0 else 0.0


@dataclass
class Figure:
    """One number on the report, with what it was and what that means."""

    key: str
    label: str
    #: "count", "money", "rate" — how a screen should write it.
    kind: str
    value: float
    before: float | None = None
    year_ago: float | None = None
    #: "real", "normal", "thin", or "none" where no test applies.
    verdict: str = "none"
    #: The verdict as a sentence, which is what the screen actually shows.
    words: str = ""
    #: Which test was used, named so the number can be argued with.
    test: str = ""

    @property
    def change(self) -> float | None:
        """How much it moved against the period before, as a percentage."""
        if self.before in (None, 0):
            return None
        return round(((self.value - (self.before or 0)) / (self.before or 1)) * 100, 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "value": round(self.value, 2),
            "before": None if self.before is None else round(self.before, 2),
            "year_ago": None if self.year_ago is None else round(self.year_ago, 2),
            "change": self.change,
            "verdict": self.verdict,
            "words": self.words,
            "test": self.test,
        }


#: What each word on the report means, in the words the client's handoff uses.
#: Served with the report rather than written into a screen, so the app, a
#: shared link and a printed copy cannot drift apart.
DEFINITIONS: list[dict[str, str]] = [
    {
        "term": "Lead",
        "what": (
            "Somebody who called you or sent a form, as counted by Google's conversion "
            "tracking. If that tracking is not set up, this number is zero however many "
            "times your phone rang."
        ),
    },
    {
        "term": "Cost per lead",
        "what": "What you spent in the period divided by the leads it brought.",
    },
    {
        "term": "Lead rate",
        "what": "Of the people who clicked your ad, the share who then called or sent a form.",
    },
    {
        "term": "Click rate",
        "what": "Of the people who were shown your ad, the share who clicked it.",
    },
    {
        "term": "A real change",
        "what": (
            "The difference is bigger than the ordinary wobble between two periods of this "
            "size — it would happen by chance less than about one time in twenty. It is "
            "worth looking into."
        ),
    },
    {
        "term": "Within the normal range",
        "what": (
            "The number moved, but not by more than two periods of this size normally "
            "differ. Nothing has been proved either way, and acting on it is guesswork."
        ),
    },
    {
        "term": "Too little data to tell",
        "what": (
            "There were not enough leads or clicks in the two periods for any comparison "
            "to mean anything. More time, not more analysis, is what this needs."
        ),
    },
    {
        "term": "Why spend has no verdict",
        "what": (
            "Spend is a decision you made, not a measurement with noise in it. Asking "
            "whether a budget change is statistically significant answers a question "
            "nobody asked."
        ),
    },
]


@dataclass
class Report:
    """One account over one period, against the period before and a year ago."""

    read: bool = False
    trouble: str = ""
    customer_id: str = ""
    currency: str = ""
    days: int = 30
    held_days: int = 0
    #: The window the figures cover, as dates, so a printed copy is unambiguous.
    starts_on: str = ""
    ends_on: str = ""
    figures: list[Figure] = field(default_factory=list)
    campaigns: list[Row] = field(default_factory=list)
    series: list[Day] = field(default_factory=list)
    #: True when we hold the same period a year ago. False means we are new,
    #: not that the account did nothing.
    year_held: bool = False
    #: One sentence saying what the period amounted to, which is the only part
    #: of this page some people will read.
    sentence: str = ""
    looked_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "read": self.read,
            "trouble": self.trouble,
            "customer_id": self.customer_id,
            "currency": self.currency,
            "days": self.days,
            "held_days": self.held_days,
            "starts_on": self.starts_on,
            "ends_on": self.ends_on,
            "figures": [f.as_dict() for f in self.figures],
            "campaigns": [c.as_dict() for c in self.campaigns],
            "series": [d.as_dict() for d in self.series],
            "year_held": self.year_held,
            "sentence": self.sentence,
            "definitions": DEFINITIONS,
            "looked_at": self.looked_at.isoformat() if self.looked_at else None,
            "source": "mirror",
        }


def _verdict_for_counts(now: float, before: float, *, what: str) -> tuple[str, str, str]:
    """A verdict, its sentence and the name of the test, for a count of events."""
    test = "two Poisson counts"
    if before <= 0:
        return "none", f"There is no earlier period to compare these {what} with.", ""
    if now + before < ENOUGH_EVENTS:
        return (
            "thin",
            f"Too few {what} in both periods to tell a real change from chance.",
            test,
        )
    z = _poisson_z(now, before)
    if abs(z) >= SURE:
        way = "up" if z > 0 else "down"
        return "real", f"A real change: {what} are {way} by more than the usual wobble.", test
    return "normal", f"Within the normal range for {what} at this volume.", test


def _verdict_for_rate(
    hits_now: float, of_now: int, hits_before: float, of_before: int
) -> tuple[str, str, str]:
    test = "two proportions"
    if of_before <= 0:
        return "none", "There is no earlier period to compare this rate with.", ""
    if of_now + of_before < ENOUGH_CLICKS:
        return "thin", "Too few clicks in both periods for the rate to mean anything.", test
    z = _rate_z(hits_now, of_now, hits_before, of_before)
    if abs(z) >= SURE:
        way = "better" if z > 0 else "worse"
        return "real", f"A real change: the rate is {way} by more than the usual wobble.", test
    return "normal", "Within the normal range for this many clicks.", test


def _sentence(held: Held) -> str:
    """The period in one line, for somebody who reads nothing else."""
    money = plain_money(held.cost, held.currency)
    if held.leads:
        each = plain_money(held.cost_per_lead, held.currency)
        enquiries = "enquiry" if round(held.leads) == 1 else "enquiries"
        return (
            f"You spent {money} and it brought {round(held.leads)} {enquiries}, "
            f"which is {each} each."
        )
    if held.cost:
        return (
            f"You spent {money} and Google counted no enquiries at all. Either nobody "
            "called, or the tracking that counts calls and forms is not set up — the "
            "website audit checks that, and it is the first thing to fix."
        )
    return "Nothing was spent in this period, so there is nothing to report."


def report_for(
    session: Session,
    customer_id: str,
    *,
    days: int = 30,
    currency: str = "",
    today: date | None = None,
) -> Report:
    """Build the report for one account over one period."""
    now = today or datetime.now(UTC).date()
    held = account_numbers(session, customer_id, days=days, currency=currency, today=now)
    report = Report(
        customer_id=customer_id,
        currency=currency,
        days=days,
        held_days=held.held_days,
        starts_on=(now - timedelta(days=days)).isoformat(),
        ends_on=(now - timedelta(days=1)).isoformat(),
    )
    if not held.read:
        report.trouble = held.trouble
        return report

    # The same length of time, a year earlier. The mirror answers it the same
    # way it answers today, so year on year costs one more query and no
    # round trip to Google at all.
    year = account_numbers(
        session, customer_id, days=days, currency=currency, today=now - timedelta(days=YEAR)
    )
    report.year_held = bool(year.series)

    clicks_before = 0
    # Clicks in the earlier window are not on the summary, so the rate test uses
    # the period before only when it is there to use.
    before = account_numbers(
        session, customer_id, days=days, currency=currency, today=now - timedelta(days=days)
    )
    clicks_before = before.clicks

    leads_verdict, leads_words, leads_test = _verdict_for_counts(
        held.leads, held.leads_before, what="leads"
    )
    rate_verdict, rate_words, rate_test = _verdict_for_rate(
        held.leads, held.clicks, held.leads_before, clicks_before
    )

    report.figures = [
        Figure(
            key="leads",
            label="Leads",
            kind="count",
            value=held.leads,
            before=held.leads_before or None,
            year_ago=year.leads if report.year_held else None,
            verdict=leads_verdict,
            words=leads_words,
            test=leads_test,
        ),
        Figure(
            key="cost_per_lead",
            label="Cost per lead",
            kind="money",
            value=held.cost_per_lead,
            before=held.cost_per_lead_before or None,
            year_ago=year.cost_per_lead if report.year_held else None,
            # The spend is known; the leads are the noisy part, so the verdict
            # on a cost per lead is the verdict on the leads underneath it.
            verdict=leads_verdict,
            words=(
                leads_words
                if leads_verdict != "real"
                else "A real change, because the leads underneath it really moved."
            ),
            test=leads_test,
        ),
        Figure(
            key="cost",
            label="Spend",
            kind="money",
            value=held.cost,
            before=held.cost_before or None,
            year_ago=year.cost if report.year_held else None,
            verdict="none",
            words="Spend is a decision, not a measurement, so it gets no verdict.",
        ),
        Figure(
            key="lead_rate",
            label="Lead rate",
            kind="rate",
            value=round((held.leads / held.clicks) * 100, 1) if held.clicks else 0.0,
            before=(round((held.leads_before / clicks_before) * 100, 1) if clicks_before else None),
            year_ago=(
                round((year.leads / year.clicks) * 100, 1)
                if report.year_held and year.clicks
                else None
            ),
            verdict=rate_verdict,
            words=rate_words,
            test=rate_test,
        ),
        Figure(
            key="clicks",
            label="Clicks",
            kind="count",
            value=float(held.clicks),
            before=float(clicks_before) if clicks_before else None,
            year_ago=float(year.clicks) if report.year_held else None,
            verdict="none",
            words="How many people clicked, for context rather than judgement.",
        ),
        Figure(
            key="click_rate",
            label="Click rate",
            kind="rate",
            value=(round((held.clicks / held.impressions) * 100, 1) if held.impressions else 0.0),
            before=None,
            year_ago=None,
            verdict="none",
            words="Of the people shown your ad, the share who clicked it.",
        ),
    ]

    report.campaigns = held.campaigns
    report.series = held.series
    report.sentence = _sentence(held)
    report.looked_at = held.looked_at
    report.read = True
    return report
