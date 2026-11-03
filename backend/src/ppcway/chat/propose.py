"""The one thing Otto may write, and why it cannot be aimed by the model.

The client's brief, exactly: *create_proposal only; target resolved
server-side from a tool-returned id; never a model-supplied budget, bid or
target.* Those three clauses are a design, not a wish list, and this is it.

**The model never names a target.** A read tool that returns something
proposable attaches an opaque handle to it, generated server-side and kept in
a dictionary that lives for one turn. `create_proposal` takes a handle and a
change type and nothing else. So the model cannot say "exclude the term
'competitor brand'", only "propose on the thing you showed me third" -- and a
handle it invents, or one from somebody else's turn, resolves to nothing.

**The model never supplies a number.** The proposal's figures are recomputed
here, from the mirror, at the moment of proposing. Not taken from the handle,
not taken from the model, not even taken from the read tool's own output: a
figure that travelled through a prompt is a figure that could have been
rewritten on the way.

**The model never approves anything.** What this writes is a proposal in the
state everything else arrives in -- awaiting a person -- recorded as proposed
by the chat so the inbox can say where it came from. The brief puts this phase
after phase 2 is live for exactly that reason: a chat that could create
proposals before approvals existed would be a chat that created things nobody
could act on.

**Why handles rather than letting the model pass the term back.** A search
term is text somebody else wrote. If `create_proposal` took a term string, the
value flowing into it would be attacker-controlled text that had passed
through a model's attention -- and the model would be the thing deciding which
account it belonged to. The handle breaks that: it is ours, it is opaque, and
it carries the scope with it.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from typing import Any, Final

from ppcway.opt.context import limits_for, standing_for
from ppcway.opt.guardrails import judge
from ppcway.opt.models import ProposedBy, Status
from ppcway.opt.record import write_proposal
from ppcway.rules.library import wasteful_terms

log = logging.getLogger(__name__)

#: How long a handle is. Short enough to sit in a prompt without costing
#: anything, long enough that guessing one is not a strategy.
LENGTH: Final = 10

#: What a handle may be used to propose, by the kind of thing it points at.
#: A handle for a search term cannot be used to pause an ad, which is the
#: second half of "target resolved server-side": the server decides what a
#: given target is even eligible for.
WHAT_FOR: Final[dict[str, frozenset[str]]] = {
    "search_term": frozenset({"add_negative_keyword"}),
}


@dataclass(frozen=True, slots=True)
class Handle:
    """One proposable thing a read tool showed, kept server-side."""

    #: "search_term", and later "ad".
    points_at: str
    #: Everything needed to find it again. Never sent to the model.
    what: dict[str, Any]
    #: A label for the transcript, so a person reading it later can tell what
    #: was proposed on without resolving a handle that no longer exists.
    label: str = ""


@dataclass(slots=True)
class Handles:
    """Everything this turn's read tools offered, by opaque id.

    One turn. A handle from the previous question is gone, which is deliberate:
    a proposal should rest on figures the model has just been shown, not on
    something it remembers from four questions ago about an account that has
    moved since.
    """

    held: dict[str, Handle] = field(default_factory=dict)

    def offer(self, points_at: str, *, label: str = "", **what: Any) -> str:
        """Register something proposable and return the handle for it."""
        handle = f"h_{secrets.token_urlsafe(LENGTH)}"
        self.held[handle] = Handle(points_at=points_at, what=what, label=label)
        return handle

    def resolve(self, handle: object) -> Handle | None:
        """The thing a handle points at, or None for one we never issued."""
        return self.held.get(str(handle)) if handle else None


class CannotPropose(RuntimeError):
    """Nothing was written, and this says why in words a merchant can read."""


#: The tool definition the model is given. No target, no amount, no account --
#: there is nothing in this schema to aim.
SCHEMA: Final[dict[str, Any]] = {
    "name": "create_proposal",
    "description": (
        "Put a change in the merchant's inbox for them to approve or decline."
        " You cannot make a change yourself and this does not make one: it"
        " writes a proposal a person then decides on."
        "\n\nYou may only propose on something a read tool showed you this turn."
        " Pass the `handle` that came back with it. You cannot name a target or"
        " an amount; the figures are worked out here from the account's own"
        " data, not from anything you say."
        "\n\nUse it when the merchant has asked for a change, or clearly agreed"
        " to one you suggested. Do not use it to be helpful unprompted."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "handle": {
                "type": "string",
                "description": "The handle that came back with the thing to act on.",
            },
            "change": {
                "type": "string",
                "enum": ["add_negative_keyword"],
                "description": "What to propose doing to it.",
            },
        },
        "required": ["handle", "change"],
        "additionalProperties": False,
    },
}


def create_proposal(asked: Any) -> dict[str, Any]:
    """Write one proposal, from a handle and nothing the model chose.

    Returns what to tell the model. Never raises into the turn loop: a refusal
    is something Otto should explain, not something that ends the conversation.
    """
    handles: Handles | None = getattr(asked, "handles", None)
    found = handles.resolve(asked.args.get("handle")) if handles else None
    if found is None:
        return {
            "proposed": False,
            "why": (
                "That handle is not something I showed you this turn. Look the thing"
                " up again and use the handle that comes back with it."
            ),
        }

    change = str(asked.args.get("change", ""))
    if change not in WHAT_FOR.get(found.points_at, frozenset()):
        return {
            "proposed": False,
            "why": (
                f"A {found.points_at.replace('_', ' ')} cannot be used to propose"
                f" {change or 'that'}."
            ),
        }

    try:
        return _negative_keyword(asked, found)
    except CannotPropose as exc:
        return {"proposed": False, "why": str(exc)}
    except Exception:
        log.exception("create_proposal failed")
        return {
            "proposed": False,
            "why": "I could not write that proposal. Say so rather than claiming it worked.",
        }


def _negative_keyword(asked: Any, found: Handle) -> dict[str, Any]:
    """Propose excluding one search term, with the figures recomputed here.

    The rule that would have found this anyway is the one that builds it, so a
    proposal made from the chat and one made by the nightly pass are the same
    shape, cite the same figures and carry the same undo plan. A second code
    path for "the same change, but asked for in conversation" is a second set
    of thresholds to drift.
    """
    term_hash = str(found.what.get("term_hash", ""))
    everything = wasteful_terms(
        asked.session,
        asked.customer_id,
        currency=asked.currency,
        # Nothing to measure waste against here, so the rule's spend threshold
        # is disabled and its hundred-click one carries the finding. That is
        # the safe direction: more waste is needed to qualify, not less.
        target_cost_per_lead=0.0,
        today=asked.today,
    )
    mine = next((one for one in everything if one.target_id == term_hash), None)
    if mine is None:
        raise CannotPropose(
            "That search has not cost enough to be worth excluding yet, or it has"
            " already brought somebody in. I would rather not propose it."
        )

    said = judge(
        mine.to_proposal(),
        standing_for(
            asked.session,
            asked.connection,
            organization_id=asked.organization_id,
            target_id=mine.target_id,
        ),
        limits_for(asked.session, asked.organization_id),
    )
    row = write_proposal(
        asked.session,
        mine,
        said,
        organization_id=asked.organization_id,
        guardrail_config_version=limits_for(asked.session, asked.organization_id).version,
        # Recorded as the chat's, so the inbox can say where it came from and
        # so "did a person ask for this?" is answerable without inference.
        proposed_by=ProposedBy.CHAT.value,
        job_run="chat",
    )
    asked.session.commit()

    settled = row.status == Status.REJECTED.value
    return {
        "proposed": not settled,
        "status": row.status,
        "in_their_inbox": row.status == Status.AWAITING_APPROVAL.value,
        "about": found.label or mine.target_label,
        "reason": mine.reason,
        "why_not": row.decided_because if settled else "",
        "expected_saving_a_month": mine.impact.money_a_month,
        "currency": mine.impact.currency,
        "undo": mine.undo,
    }
