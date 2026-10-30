"""Why a number moved, split between the things that moved it.

The brief asks for a "why did this change" calculation. Most dashboards answer
this with a sentence a person wrote once -- "your cost per lead rose because
competition increased" -- which is a guess with a number stapled to it. This
answers it with arithmetic that adds up.

**The decomposition is exact, not apportioned.** For a figure that is the
product of two others, the change splits as

    Δ(a·b) = Δa · (b₀+b₁)/2  +  Δb · (a₀+a₁)/2

and those two terms sum to the whole change, with no residual and no choice
about which factor is "held constant" first. The asymmetric version -- change
`a` first, then `b` -- gives different answers depending on the order, and the
order is arbitrary, so whichever one you publish is arbitrary too.

**Nothing is explained unless the change was real.** A cost per lead that moved
from £41 to £47 across nine leads has not moved; it has wobbled. Handing that
to a decomposition produces a confident story about noise, and a confident
story about noise is worse than silence because somebody acts on it. So
`because` reads the figure's verdict first and declines unless it is `REAL` --
the same rule the automation itself follows, for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ppcway.metric.figures import Figure
from ppcway.metric.verdicts import Verdict


@dataclass(frozen=True, slots=True)
class Factor:
    """One thing that moved a figure, and how much of the move it accounts for."""

    name: str
    label: str
    #: In the figure's own units: how much of the total change this caused.
    amount: float
    #: The same as a share of the whole change. Can exceed 1, or be negative,
    #: when two factors pull against each other -- which is the interesting
    #: case and must not be hidden by clamping it.
    share: float
    #: What this factor itself did: "rose", "fell", or "did not move".
    moved: str
    words: str


@dataclass(frozen=True, slots=True)
class Because:
    """Why one figure moved. Or why we are not going to say."""

    figure_id: str
    #: The whole change, in the figure's units.
    change: float
    explained: bool
    factors: tuple[Factor, ...]
    words: str


@dataclass(frozen=True, slots=True)
class Part:
    """One side of a product: which figure, what to call it, and whether to invert."""

    name: str
    label: str
    #: True where the figure divides rather than multiplies. Cost per lead is
    #: cost per click over conversion rate, so the rate enters as its inverse.
    inverted: bool = False
    #: How to describe this factor going up, in a sentence about the parent.
    up: str = "rose"
    down: str = "fell"


#: What each derived figure is made of. Only products, because every figure
#: PPCway computes is one: a ratio is a product with an inverted factor.
RECIPES: Final[dict[str, tuple[Part, Part]]] = {
    "leads": (
        Part(name="clicks", label="how many people clicked"),
        Part(name="conversion_rate", label="how many of them got in touch"),
    ),
    "clicks": (
        Part(name="impressions", label="how often your ads were shown"),
        Part(name="click_rate", label="how often people clicked them"),
    ),
    "spend": (
        Part(name="clicks", label="how many people clicked"),
        Part(name="cost_per_click", label="what each click cost"),
    ),
    "cost_per_lead": (
        Part(name="cost_per_click", label="what each click cost"),
        Part(
            name="conversion_rate",
            label="how many people got in touch",
            inverted=True,
            # Inverted, so the plain-English direction flips: a conversion rate
            # going *down* is what pushes a cost per lead up.
            up="fell",
            down="rose",
        ),
    ),
}


def split(now_a: float, before_a: float, now_b: float, before_b: float) -> tuple[float, float]:
    """The exact two-factor split of the change in a product.

    Both terms together equal `now_a*now_b - before_a*before_b`, always, with
    no residual. A test asserts that rather than trusting the algebra above.
    """
    change_a = (now_a - before_a) * ((before_b + now_b) / 2)
    change_b = (now_b - before_b) * ((before_a + now_a) / 2)
    return change_a, change_b


def because(figure: Figure, parts: dict[str, Figure]) -> Because:
    """Why `figure` moved, split between the figures in `parts`.

    `parts` is keyed by factor name, and must hold both factors of the recipe
    for `figure.name`, each with a `before`. Anything missing means the honest
    answer is that we cannot say, which is returned rather than raised: a card
    with no explanation is a card, and a crash is not.
    """
    recipe = RECIPES.get(figure.name)
    change = (figure.value - figure.before) if figure.before is not None else None

    if recipe is None:
        return _cannot(
            figure,
            change,
            f"{figure.name.replace('_', ' ')} is measured directly rather than worked"
            " out from other numbers, so there is nothing to split it into.",
        )
    if change is None:
        return _cannot(figure, None, "There is no earlier period to compare this with.")
    if figure.verdict is not Verdict.REAL:
        return _cannot(
            figure,
            change,
            figure.words
            or "This has not moved by more than the usual wobble, so there is nothing to explain.",
        )

    values: list[tuple[Part, float, float]] = []
    for part in recipe:
        held = parts.get(part.name)
        if held is None or held.before is None:
            return _cannot(
                figure,
                change,
                f"We do not have {part.label} for both periods, so the change cannot be split up.",
            )
        now, before = held.value, held.before
        if part.inverted:
            if now == 0 or before == 0:
                return _cannot(
                    figure,
                    change,
                    f"{part.label.capitalize()} was zero in one of the periods, so the"
                    " arithmetic has nowhere to start.",
                )
            now, before = 1 / now, 1 / before
        values.append((part, now, before))

    (part_a, now_a, before_a), (part_b, now_b, before_b) = values
    amount_a, amount_b = split(now_a, before_a, now_b, before_b)

    factors = tuple(
        _factor(part, amount, change, now, before)
        for part, amount, now, before in (
            (part_a, amount_a, now_a, before_a),
            (part_b, amount_b, now_b, before_b),
        )
    )
    biggest = max(factors, key=lambda f: abs(f.amount))
    way = "up" if change > 0 else "down"
    return Because(
        figure_id=figure.id,
        change=round(change, 4),
        explained=True,
        factors=factors,
        words=(
            f"{figure.name.replace('_', ' ').capitalize()} went {way}, and most of that"
            f" is {biggest.label}: it {biggest.moved}."
        ),
    )


def _factor(part: Part, amount: float, change: float, now: float, before: float) -> Factor:
    moved = part.up if now > before else part.down if now < before else "did not move"
    share = round(amount / change, 3) if change else 0.0
    return Factor(
        name=part.name,
        label=part.label,
        amount=round(amount, 4),
        share=share,
        moved=moved,
        words=f"{part.label.capitalize()} {moved}, which accounts for {_percent(share)}.",
    )


def _percent(share: float) -> str:
    """A share of the change, in words that survive being negative or over one."""
    if share < 0:
        return f"{abs(share) * 100:.0f}% in the other direction"
    return f"{share * 100:.0f}% of the change"


def _cannot(figure: Figure, change: float | None, why: str) -> Because:
    return Because(
        figure_id=figure.id,
        change=0.0 if change is None else round(change, 4),
        explained=False,
        factors=(),
        words=why,
    )
