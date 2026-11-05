"""One number, and everything needed to argue with it.

The client's brief asks that every figure carry a stable id, a unit, a period,
an as-of time and a verdict. Each of those five exists because something
downstream breaks without it, and the reasons are worth keeping next to the
code:

- **a stable id**, because the action log records evidence as figure ids with
  as-of times, and because the number check matches every number in a model's
  sentence against the figures that turn was given. A figure identified only by
  its position in a list cannot be cited in March.
- **a unit**, because 0.42 is forty-two pence or forty-two per cent and a
  screen cannot tell from the number. Three of the worst bugs available here
  are a share printed as money, micros printed as currency, and a ratio
  multiplied by a hundred twice.
- **a period**, because "spend is up" is not a claim until it says over what,
  against what.
- **an as-of time**, because the guardrails refuse to act on data older than
  thirty-six hours, and a figure that cannot say when it was true cannot be
  refused on those grounds. This is the field that turns a freshness rule from
  an intention into a check.
- **a verdict**, because eleven leads and then eight is not a collapse. See
  `verdicts`, and the decision it implements.

A `Figure` is immutable. A figure a consumer can edit after it was checked is a
figure where what was validated and what was shown are different objects.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

from ppcway.metric.verdicts import Verdict

#: How old a figure may be before a decision may not rest on it. The client's
#: brief: "No decision on data older than 36 hours or while sync is failing."
FRESH_HOURS: Final = 36


class Unit(StrEnum):
    """What the number is, which is not the same as how big it is."""

    #: A whole thing that was counted: clicks, leads, impressions.
    COUNT = "count"
    #: An amount of money, in the account's own currency. Never micros: a
    #: figure that might be micros is a figure somebody will print as pounds.
    MONEY = "money"
    #: A fraction between 0 and 1. A screen multiplies by a hundred; this
    #: never does, so it cannot be done twice.
    RATIO = "ratio"
    #: A number of days, for a window or a pace.
    DAYS = "days"


@dataclass(frozen=True, slots=True)
class Period:
    """The stretch of time a figure is about, inclusive at both ends."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"a period cannot end before it starts, and got {self.start} to {self.end}."
                f" A reversed window reads as an empty one and silently makes every"
                f" figure in it zero."
            )

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def slug(self) -> str:
        return f"{self.start.isoformat()}..{self.end.isoformat()}"

    def before(self) -> Period:
        """The window of the same length immediately before this one."""
        length = self.days
        end = self.start - timedelta(days=1)
        return Period(start=end - timedelta(days=length - 1), end=end)

    @classmethod
    def last(cls, days: int, *, until: date) -> Period:
        """The `days` days ending on `until`, inclusive."""
        if days < 1:
            raise ValueError(f"a period is at least one day, not {days}")
        return cls(start=until - timedelta(days=days - 1), end=until)


@dataclass(frozen=True, slots=True)
class Scope:
    """What a figure is about: the whole account, or one thing in it."""

    #: "account", "campaign", "ad_group", "keyword", "search_term".
    kind: str
    #: Google's own id for it, empty for the account as a whole.
    id: str = ""

    @property
    def slug(self) -> str:
        return f"{self.kind}-{self.id}" if self.id else self.kind


@dataclass(frozen=True, slots=True)
class Figure:
    """One computed number, with its provenance and its verdict."""

    #: What was measured: "spend", "leads", "cost_per_lead", "lost_to_budget".
    name: str
    value: float
    unit: Unit
    period: Period
    scope: Scope
    #: When the data behind it was last read from Google. Not when this object
    #: was built: a figure computed now from numbers read yesterday is a
    #: yesterday figure, and the guardrails have to be told the truth about it.
    as_of: datetime
    #: The account's currency, required when the unit is money and forbidden
    #: otherwise -- a money figure with no currency is the bug where a Canadian
    #: merchant is shown euros.
    currency: str = ""
    #: The same figure over the period immediately before, where there is one.
    before: float | None = None
    verdict: Verdict = Verdict.NONE
    #: The verdict as a sentence, which is what a person actually reads.
    words: str = ""
    #: Which test was used, named so the number can be argued with.
    test: str = ""
    #: Anything else worth carrying, such as whether Google capped the figure.
    notes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.unit is Unit.MONEY and not self.currency:
            raise ValueError(
                f"the money figure {self.name!r} has no currency. Micros carry no"
                f" currency of their own and neither does a float, so a figure"
                f" without one is how a merchant in Toronto is shown euros."
            )
        if self.unit is not Unit.MONEY and self.currency:
            raise ValueError(
                f"the figure {self.name!r} is {self.unit.value} and carries a currency"
                f" {self.currency!r}. A count of clicks in Canadian dollars is a"
                f" units bug that would otherwise be found by a reader, not a test."
            )
        if self.as_of.tzinfo is None:
            raise ValueError(
                f"the as-of time of {self.name!r} has no time zone. A naive"
                f" timestamp compared against an aware one raises, and compared"
                f" against a wrong assumption silently shifts the freshness"
                f" window by hours."
            )

    @property
    def id(self) -> str:
        """The stable identifier. Deterministic, readable, and citable in March.

        Derived rather than stored, so it cannot drift from the three things it
        names. Two figures with the same name, scope and period *are* the same
        figure, and should collide.
        """
        return f"{self.name}:{self.scope.slug}:{self.period.slug}"

    @property
    def change(self) -> float | None:
        """How far it moved against the period before, as a percentage."""
        if self.before in (None, 0):
            return None
        return round(((self.value - (self.before or 0)) / (self.before or 1)) * 100, 1)

    def age(self, now: datetime | None = None) -> timedelta:
        return (now or datetime.now(UTC)) - self.as_of

    def fresh(self, now: datetime | None = None, *, hours: int = FRESH_HOURS) -> bool:
        """Whether a decision may rest on this. The guardrails' own question."""
        return self.age(now) <= timedelta(hours=hours)

    def cite(self) -> dict[str, Any]:
        """The form the action log stores as evidence: an id, a value, a time."""
        return {
            "id": self.id,
            "value": round(self.value, 4),
            "unit": self.unit.value,
            "as_of": self.as_of.isoformat(),
            "verdict": self.verdict.value,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "value": round(self.value, 4),
            "unit": self.unit.value,
            "currency": self.currency,
            "period": {
                "start": self.period.start.isoformat(),
                "end": self.period.end.isoformat(),
                "days": self.period.days,
            },
            "scope": {"kind": self.scope.kind, "id": self.scope.id},
            "as_of": self.as_of.isoformat(),
            "before": None if self.before is None else round(self.before, 4),
            "change": self.change,
            "verdict": self.verdict.value,
            "words": self.words,
            "test": self.test,
            "notes": dict(self.notes),
        }


#: Numbers a sentence may contain without citing a figure: the small integers
#: that are almost always counting words rather than measurements ("the top
#: three", "both of your campaigns"). Deliberately short. Anything else a
#: caller wants to allow it has to name.
PLAIN_WORDS: Final = frozenset({0.0, 1.0, 2.0, 3.0})

#: A number in a sentence, with or without a currency symbol, thousands
#: separators or a trailing per cent. A hyphen is a minus sign only where it
#: does not follow a letter or a digit: in "2025-11-05" and "5-11 November" it
#: joins numbers, and reading it as a minus once turned a date the lookup had
#: given into three negative numbers nothing had, and the answer into the
#: fallback.
_NUMBER = re.compile(r"(?:(?<!\w)-)?\d[\d,]*(?:\.\d+)?")

#: Numbers written as words, the way our own help text and a merchant's
#: question often put them: "for thirty days", "the last twelve months". These
#: only ever license a number. The check reads digits, so a number the model
#: spells out is not checked at all, but one it writes as digits after reading
#: it as a word has to be allowed.
_UNITS: Final = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS: Final = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_SPELLED = re.compile(
    r"\b(?:(?P<tens>"
    + "|".join(_TENS)
    + r")(?:[- ](?P<and>"
    + "|".join(word for word, n in _UNITS.items() if 0 < n < 10)
    + r"))?|(?P<units>"
    + "|".join(_UNITS)
    + r")|(?P<hundred>hundred))\b",
    re.IGNORECASE,
)


def spelled_in(text: str) -> list[float]:
    """Every number a sentence writes as a word, "twenty-one" as one number."""
    out: list[float] = []
    for found in _SPELLED.finditer(text):
        if found["tens"]:
            tens = _TENS[found["tens"].lower()]
            out.append(float(tens + (_UNITS[found["and"].lower()] if found["and"] else 0)))
        elif found["units"]:
            out.append(float(_UNITS[found["units"].lower()]))
        else:
            out.append(100.0)
    return out


def numbers_in(text: str) -> list[float]:
    """Every number a sentence claims, in the order it claims them."""
    out: list[float] = []
    for found in _NUMBER.finditer(text):
        try:
            out.append(float(found.group(0).replace(",", "")))
        except ValueError:  # pragma: no cover - the pattern cannot produce this
            continue
    return out


def _allowed(figures: Iterable[Figure]) -> set[float]:
    """Every number the given figures license a sentence to say.

    A figure licenses more than its own value: the rounded forms a sentence
    would naturally use, the percentage it moved, the value it moved from, and
    a ratio written as a percentage. Being generous here is deliberate -- the
    check exists to catch an invented number, not to argue about rounding.
    """
    ok: set[float] = set()
    for figure in figures:
        for value in (figure.value, figure.before):
            if value is None:
                continue
            ok.update({float(value), round(value, 2), round(value, 1), float(round(value))})
            if figure.unit is Unit.RATIO:
                percent = value * 100
                ok.update({percent, round(percent, 2), round(percent, 1), float(round(percent))})
        if figure.change is not None:
            ok.update({figure.change, abs(figure.change), float(round(figure.change))})
        ok.add(float(figure.period.days))
    return ok


def numbers_given(data: Any) -> set[float]:
    """Every number put in front of the model, as a sentence would say it.

    The rule the tools were written to: a number the model was given is a
    number it may say. A lookup returns its figures and also the rest of what
    it read -- the period before, calls and forms, the window's dates -- and
    the model rightly quotes those too. Checked against the figures alone,
    "compared with CAD 150.45 before" was rejected as invented while the
    lookup had supplied exactly 150.45, and the rewrite could not fix what was
    not wrong.

    Each value counts with the forms a sentence would use: rounded, a share as
    a percentage, and either sign. Numbers inside text count too, in digits or
    in words (a campaign called "Boiler 24/7", "put back for thirty days"), and
    a date gives its day, month and year. What is still not licensed is
    anything the model works out for itself.
    """
    out: set[float] = set()

    def plain(value: float) -> None:
        size = abs(float(value))
        forms = {size, round(size, 2), round(size, 1), float(round(size))}
        if 0 < size < 1:
            percent = size * 100
            forms |= {percent, round(percent, 2), round(percent, 1), float(round(percent))}
        # "Fell by 27.87" and "a change of -27.87" are the same number.
        out.update(forms | {-form for form in forms})

    def walk(value: Any) -> None:
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            plain(value)
        elif isinstance(value, str):
            for number in (*numbers_in(value), *spelled_in(value)):
                plain(number)
        elif isinstance(value, dict):
            for one in value.values():
                walk(one)
        elif isinstance(value, (list, tuple, set)):
            for one in value:
                walk(one)

    walk(data)
    return out


def unmatched(
    text: str,
    figures: Sequence[Figure],
    *,
    also: Iterable[float] = (),
) -> list[float]:
    """The numbers in `text` that no given figure accounts for.

    The number check, in its primitive form. The brief: *every number matched
    to that turn's tool results; one rewrite, then a fixed template*. This
    returns what did not match, so a caller can decide between those two.

    `also` is how a caller licenses numbers that are real but are not figures
    -- a threshold it is quoting, a count of days it chose. It is explicit on
    purpose: a checker that guessed which extra numbers were acceptable would
    be a checker that let an invented one through on a Tuesday.
    """
    ok = _allowed(figures) | {float(n) for n in also} | PLAIN_WORDS
    return [n for n in numbers_in(text) if n not in ok]
