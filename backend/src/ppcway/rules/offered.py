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
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ppcway.model.service import Models
from ppcway.opt.models import UNDO_FOR, OptimizationAction, Status, may_undo
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
    #: What became of the changes already said yes to: waiting, made, refused
    #: by Google, or put back. Without it an approved card simply vanished.
    changes: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "cards": list(self.cards),
            "changes": list(self.changes),
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
    waiting_because: str = "",
) -> Offered:
    """The written proposals, plus anything found that is not written yet.

    `waiting_because` is why every approved change on this account is still
    waiting, when something holds them all -- the write gate, or a kill switch.
    The caller reads it from the gateway, which this package may not reach.
    """
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
        changes=tuple(
            recent_changes(
                session,
                organization_id=organization_id,
                now=now,
                waiting_because=waiting_because,
            )
        ),
    )


#: How far back the list of changes reaches: a week to be answered, and the
#: thirty days after a change is made in which it can be put back.
CHANGES_FOR: Final = timedelta(days=37)

#: The most changes listed. Ten a week is the cap, so this is several weeks.
MOST_CHANGES: Final = 25

#: The states a change said yes to can be in. `rejected` is listed only where
#: it happened after the yes -- see `_stopped_after_yes`.
AFTER_YES: Final = (
    Status.APPROVED.value,
    Status.APPLIED.value,
    Status.FAILED.value,
    Status.REVERTED.value,
    Status.REJECTED.value,
)


def recent_changes(
    session: Session,
    *,
    organization_id: UUID,
    now: datetime | None = None,
    waiting_because: str = "",
) -> list[dict[str, Any]]:
    """The changes this business said yes to, newest first, and where each is."""
    at = now or datetime.now(UTC)
    rows = [
        row
        for row in session.scalars(
            select(OptimizationAction)
            .where(
                OptimizationAction.organization_id == organization_id,
                OptimizationAction.undo_of.is_(None),
                OptimizationAction.status.in_(AFTER_YES),
                # Offered recently, or made recently enough to be put back. The
                # second matters once a change can wait weeks for writes to open:
                # made long after it was offered, it is still undoable.
                or_(
                    OptimizationAction.created_at >= at - CHANGES_FOR,
                    OptimizationAction.applied_at >= at - UNDO_FOR,
                ),
            )
            .order_by(OptimizationAction.created_at.desc())
        )
        if row.status != Status.REJECTED.value or _stopped_after_yes(row)
    ][:MOST_CHANGES]
    if not rows:
        return []

    # The latest attempt to put each one back, which is a row of its own.
    putting_back: dict[UUID, OptimizationAction] = {}
    for undo in session.scalars(
        select(OptimizationAction)
        .where(OptimizationAction.undo_of.in_([row.id for row in rows]))
        .order_by(OptimizationAction.created_at)
    ):
        if undo.undo_of is not None:
            putting_back[undo.undo_of] = undo

    return [_as_change(row, putting_back.get(row.id), at, waiting_because) for row in rows]


def _stopped_after_yes(row: OptimizationAction) -> bool:
    """Refused after somebody approved it, rather than declined or never offered.

    Either the guardrails' second ruling at the moment of approval, or their
    third at the door. A person's own "no" is not a change they said yes to.
    """
    if row.outcome:
        return True
    rechecked = row.rechecked or {}
    return bool(rechecked) and rechecked.get("check") != "person"


def _as_change(
    row: OptimizationAction,
    undo: OptimizationAction | None,
    at: datetime,
    waiting_because: str,
) -> dict[str, Any]:
    rule = CATALOGUE.get(row.rule_id)
    open_undo = undo is not None and undo.status == Status.APPROVED.value
    may = may_undo(row, now=at) and not open_undo and _can_be_put_back(row)
    return {
        "id": str(row.id),
        "status": row.status,
        "rule_id": row.rule_id,
        "title": rule.name if rule else row.kind.replace("_", " ").capitalize(),
        "target": {"kind": row.target_kind, "id": row.target_id, "label": row.target_label},
        "words": _what_became_of(row, undo, may, waiting_because),
        "may_undo": may,
        "undo": row.undo_plan,
        "approved_at": _iso(row.approved_at),
        "applied_at": _iso(row.applied_at),
        "reverted_at": _iso(row.reverted_at),
    }


def _what_became_of(
    row: OptimizationAction,
    undo: OptimizationAction | None,
    may: bool,
    waiting_because: str,
) -> str:
    """One sentence on where this change has got to."""
    said = row.outcome or {}
    if row.status == Status.APPROVED.value:
        if row.taken_at is not None:
            return "Sent to Google. Waiting to hear back."
        if waiting_because:
            return f"Approved{_on(row.approved_at)}. Waiting: {waiting_because}"
        return f"Approved{_on(row.approved_at)}. Otto is sending it to Google."
    if row.status == Status.APPLIED.value:
        made = f"Made{_on(row.applied_at)}."
        if undo is not None and undo.status == Status.APPROVED.value:
            return f"{made} Being put back."
        if undo is not None and undo.status in {Status.FAILED.value, Status.REJECTED.value}:
            why = (undo.outcome or {}).get("words") or "Google would not take it."
            return f"{made} We could not put it back: {why}"
        if may and row.applied_at is not None:
            return f"{made} You can undo it until {_day(row.applied_at + UNDO_FOR)}."
        return made
    if row.status == Status.REVERTED.value:
        return f"Made{_on(row.applied_at)} and put back{_on(row.reverted_at)}."
    if row.status == Status.FAILED.value:
        return str(said.get("words") or "Google would not make this change.")
    # Rejected after the yes: by the guardrails at the door, or at approval.
    why = (said.get("ruling") or {}).get("because") or (row.rechecked or {}).get("because")
    if said.get("unsendable"):
        why = said.get("words")
    return f"Approved, then stopped before it was made: {why or 'it no longer passed the checks.'}"


def _can_be_put_back(row: OptimizationAction) -> bool:
    """Whether the log holds what an undo of this would have to send."""
    sent = row.payload or {}
    if sent.get("change") == "exclude_search":
        return any((row.outcome or {}).get("landed") or [])
    if sent.get("change") == "set_ad_status":
        return bool(sent.get("ad")) and bool((row.before or {}).get("status"))
    return False


def _on(when: datetime | None) -> str:
    return f" on {_day(when)}" if when is not None else ""


def _day(when: datetime) -> str:
    return f"{when.day} {when:%B}"


def _iso(when: datetime | None) -> str | None:
    if when is None:
        return None
    return (when if when.tzinfo else when.replace(tzinfo=UTC)).isoformat()
