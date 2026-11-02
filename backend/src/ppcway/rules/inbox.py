"""The inbox: the cards a merchant reads, in the order they should read them.

The brief calls the inbox the product and the chat the thing that follows it,
so this is the shape everything else in phase 1 serves.

**Why polishing the words is optional here.** `words.reason_for` calls a model,
and a model call for each of ten cards is ten seconds a merchant spends looking
at a spinner. So `cards_for` takes the model service or `None`: given `None` it
returns the computed sentences, which are correct, immediate and free. The
nightly job hands it the service and stores what comes back, so by the time
anybody opens the inbox the better words are already there and nothing is
waiting on a model.

That is also why the computed sentence is never a placeholder. It is what
ships when the model is unreachable, when it invents a figure twice, and on
every card until the job has been round -- so it has to read well on its own,
and `words` treats it as the authority rather than as a fallback of last
resort.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from ppcway.model.service import Models
from ppcway.rules.engine import Pass, run
from ppcway.rules.recommend import Recommendation
from ppcway.rules.words import FROM_TEMPLATE, Written, reason_for


@dataclass(frozen=True, slots=True)
class Card:
    """One recommendation as a merchant reads it."""

    found: Recommendation
    words: Written

    def as_dict(self) -> dict[str, Any]:
        said = self.found.as_dict()
        # The computed sentence is replaced by the written one, and the card
        # says which it is: a screen that wants to mark a sentence as ours
        # rather than a model's can, and the brief's AI disclosure needs it.
        said["reason"] = self.words.text
        said["reason_from"] = self.words.source
        said["reason_is_ours"] = self.words.is_ours
        return said


@dataclass(frozen=True, slots=True)
class Inbox:
    """What to show, and what to say when there is nothing."""

    customer_id: str
    cards: tuple[Card, ...]
    #: Found but below this week's cap. Counted, not shown.
    held_back: int
    used_this_week: int
    room_left: int
    #: Why there is nothing, when there is nothing. Empty when there are cards.
    nothing_because: str
    ran: tuple[str, ...]
    not_specified: tuple[str, ...]
    ran_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "cards": [card.as_dict() for card in self.cards],
            "held_back": self.held_back,
            "used_this_week": self.used_this_week,
            "room_left": self.room_left,
            "nothing_because": self.nothing_because,
            "ran": list(self.ran),
            "not_specified": list(self.not_specified),
            "ran_at": self.ran_at.isoformat(),
        }


def cards_for(
    session: Session,
    customer_id: str,
    *,
    currency: str,
    target_cost_per_lead: float,
    models: Models | None = None,
    today: date | None = None,
    now: datetime | None = None,
    protected: Sequence[str] = (),
    blocked: Sequence[str] = (),
) -> Inbox:
    """Run the rules and turn what they found into cards.

    `models` is optional: without it every card carries the computed sentence.
    See the note at the top of this module for why that is a choice rather
    than a shortcut.
    """
    said = run(
        session,
        customer_id,
        currency=currency,
        target_cost_per_lead=target_cost_per_lead,
        today=today,
        now=now,
        protected=protected,
        blocked=blocked,
    )
    return _inbox(said, models)


def _inbox(said: Pass, models: Models | None) -> Inbox:
    cards = tuple(
        Card(
            found=found,
            words=(
                reason_for(models, found)
                if models is not None
                else Written(text=found.reason, source=FROM_TEMPLATE)
            ),
        )
        for found in said.offered
    )
    return Inbox(
        customer_id=said.customer_id,
        cards=cards,
        held_back=len(said.held_back),
        used_this_week=said.used_this_week,
        room_left=said.room_left,
        nothing_because=said.stopped if said.stopped else _quiet(said),
        ran=said.ran,
        not_specified=said.not_specified,
        ran_at=said.ran_at,
    )


def _quiet(said: Pass) -> str:
    """Why an empty inbox is empty, which is not always good news.

    Three different silences, and a merchant deserves to know which: we looked
    and there is nothing, we found things but this week is full, or we have
    only two of five rules because the rest have not been specified. Saying
    "nothing to do" for all three would be wrong twice.
    """
    if said.offered:
        return ""
    if said.held_back:
        return (
            f"There are {len(said.held_back)} more things worth doing, held back because"
            f" this week's ten changes are already used."
        )
    if said.room_left == 0:
        return "This week's ten changes are already used, so nothing new is being offered."
    return "We looked and found nothing worth changing."
