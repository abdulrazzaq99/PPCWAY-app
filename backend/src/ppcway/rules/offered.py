"""The inbox as it actually is: the proposals that were written down.

Phase 1.2 computed cards on read, because nothing wrote them yet and "shown
not applied" was the whole of that phase. Phase 2.1 gave them a table and
phase 2.2 gave them an id to answer by -- and the two never met. The inbox was
serving cards computed afresh on every request, with no id, so **nothing in it
could be approved**. A card a merchant cannot answer is not an inbox.

So the inbox reads the log. A card has an id because a row has an id, a status
because a row has a status, and the approve and reject endpoints address the
same thing the screen is showing.

**And it still shows what has not been written yet, marked as such.** A
business that connected an hour ago has nothing in the log until the nightly
pass runs, and an empty inbox saying "nothing worth changing" would be a lie
about an account nobody has looked at. So anything the rules find that has no
row yet is included as a preview: visible, explained, and with no buttons,
because there is nothing to answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.model.service import Models
from ppcway.opt.models import OptimizationAction, Status
from ppcway.rules.catalogue import CATALOGUE
from ppcway.rules.engine import MOST_A_WEEK
from ppcway.rules.inbox import Card, Inbox, cards_for


@dataclass(frozen=True, slots=True)
class Offered:
    """What the inbox shows: written proposals first, then anything not yet written."""

    connected: bool
    cards: tuple[dict[str, Any], ...]
    held_back: int
    used_this_week: int
    room_left: int
    nothing_because: str
    ran: tuple[str, ...]
    not_specified: tuple[str, ...]
    ran_at: str
    target_cost_per_lead: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "cards": list(self.cards),
            "held_back": self.held_back,
            "used_this_week": self.used_this_week,
            "room_left": self.room_left,
            "nothing_because": self.nothing_because,
            "ran": list(self.ran),
            "not_specified": list(self.not_specified),
            "ran_at": self.ran_at,
            "target_cost_per_lead": self.target_cost_per_lead,
        }


def _from_row(row: OptimizationAction) -> dict[str, Any]:
    """One written proposal, in the shape the screen draws.

    Built from the row rather than from the rule, because the row is what was
    decided: a rule whose thresholds changed last week must not make a card
    written before that look different now.
    """
    rule = CATALOGUE.get(row.rule_id)
    impact = row.expected_impact or {}
    return {
        # The id is the point of this module.
        "id": str(row.id),
        "status": row.status,
        "rule_id": row.rule_id,
        "rule_version": row.rule_version,
        "kind": row.kind,
        "title": rule.name if rule else row.kind.replace("_", " ").capitalize(),
        "about": rule.about if rule else "",
        "target": {
            "kind": row.target_kind,
            "id": row.target_id,
            "label": row.target_label,
        },
        "reason": row.reason,
        # Whether a model wrote the words. The brief's AI disclosure needs it,
        # and a screen should be able to say so.
        "reason_is_ours": not bool((row.rechecked or {}).get("worded_by_model")),
        "impact": {
            "money_a_month": impact.get("money_a_month", 0.0),
            "currency": impact.get("currency", ""),
            "confidence": impact.get("confidence", 0.0),
            "words": impact.get("words", ""),
            "blocking": bool(impact.get("blocking")),
        },
        "evidence": list((row.evidence or {}).get("figures", [])),
        "undo": row.undo_plan,
        "reversible": row.reversible,
        "risk": row.risk,
        "route": row.route,
        "priority": impact.get("priority", 0.0),
        "as_of": row.window_end.isoformat() if row.window_end else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "answerable": True,
    }


def _as_preview(card: Card) -> dict[str, Any]:
    """Something the rules found that has no row yet. No id, no buttons."""
    said: dict[str, Any] = dict(card.as_dict())
    said["id"] = ""
    said["status"] = "found"
    said["answerable"] = False
    return said


def inbox_for(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: str,
    currency: str,
    target_cost_per_lead: float,
    models: Models | None = None,
    protected: tuple[str, ...] = (),
    today: date | None = None,
    now: datetime | None = None,
) -> Offered:
    """The written proposals, plus anything found that is not written yet."""
    waiting = list(
        session.scalars(
            select(OptimizationAction)
            .where(
                OptimizationAction.organization_id == organization_id,
                OptimizationAction.status.in_(
                    (Status.AWAITING_APPROVAL.value, Status.PROPOSED.value)
                ),
            )
            .order_by(OptimizationAction.created_at.desc())
        )
    )
    answerable = [_from_row(row) for row in waiting]
    already = {row.target_id for row in waiting}

    # What the rules would find now. Used for the preview and for the counts,
    # and it is the same call the nightly pass makes, so the two cannot
    # disagree about what is worth doing.
    found: Inbox = cards_for(
        session,
        customer_id,
        currency=currency,
        target_cost_per_lead=target_cost_per_lead,
        models=models,
        today=today,
        now=now,
        protected=protected,
    )
    previews = [_as_preview(card) for card in found.cards if card.found.target_id not in already]

    return Offered(
        connected=True,
        cards=(*answerable, *previews),
        held_back=found.held_back,
        used_this_week=found.used_this_week,
        room_left=max(0, MOST_A_WEEK - found.used_this_week),
        nothing_because=(
            ""
            if (answerable or previews)
            else found.nothing_because or "We looked and found nothing worth changing."
        ),
        ran=found.ran,
        not_specified=found.not_specified,
        ran_at=found.ran_at.isoformat(),
        target_cost_per_lead=target_cost_per_lead,
    )
