"""Saying yes, saying no, and putting something back.

The client's brief asks for three endpoints, ported from the proof of concept's
contract, with the guardrails re-run at approval and risk routing including the
expert route. This is the part of that which has nothing to do with HTTP, so it
can be tested without one.

**Why the guardrails run again when somebody says yes.** The first ruling was
made when the proposal was written, which may have been six days ago. Since
then the figures behind it have aged -- possibly past the thirty-six hours the
freshness rule allows -- the day's budget may have moved, other changes may
have used up the account's allowance, and the account itself may have been
suspended. A yes is permission to make the change, not a finding that the
change is still safe. So the checks run again at the moment of acting, and a
proposal that no longer passes is refused *after* being approved, with the
reason recorded against the second ruling rather than the first.

**Why a role is checked against the route and not against a permission.** The
brief routes a change by risk: a budget rise between 20% and 50% goes to a
PPCWay expert, not to the owner. That is not "the owner lacks a permission" --
the owner has every permission in their own account. It is that this
particular change needs a particular kind of person, and an owner tapping
approve on an expert-routed change has to be told why nothing happened in
those terms rather than in the language of access control.

**An undo is a new action, not a status change.** The brief is explicit. So
`undo` writes a fresh row whose `before` and `after` are the original's
swapped, pointing back at what it reverses, and the original stays `applied`
until that reversing change has actually been made. A row that said `reverted`
the moment somebody asked would be a log claiming something had happened
because it had been requested.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.models import AdsConnection
from ppcway.opt.context import limits_for, standing_for
from ppcway.opt.guardrails import Proposal, Verdict, judge
from ppcway.opt.models import OptimizationAction, ProposedBy, Status, may_undo
from ppcway.org.models import Role

log = logging.getLogger(__name__)

#: Who may answer a change on each route. An expert-routed change needs an
#: expert; an owner-routed one needs somebody who runs the business. A member
#: may propose and read but not answer, which is the role table's own rule.
MAY_ANSWER: dict[str, frozenset[Role]] = {
    "owner": frozenset({Role.OWNER, Role.ADMIN, Role.EXPERT}),
    # Only an expert. Not the owner as well: the point of the band is that
    # somebody who does this for a living looks at it first, and an owner who
    # could also approve it would make the route decorative.
    "expert": frozenset({Role.EXPERT}),
}


class NotAllowed(PermissionError):
    """This person may not answer this change. Carries words to show them."""


class NotAnswerable(RuntimeError):
    """This change is not in a state where it can be answered."""


@dataclass(frozen=True, slots=True)
class Answered:
    """What became of the answer, and what to tell the person who gave it."""

    action: OptimizationAction
    #: The status the row ended in.
    status: Status
    words: str
    #: Set when a yes was overturned by the second run of the guardrails.
    refused_by: str = ""


def _theirs(session: Session, action_id: UUID, organization_id: UUID) -> OptimizationAction:
    """The action, if it belongs to this business.

    One query for both questions, because they are the same question. The
    proof of concept learned this the hard way: a caller-supplied id that was
    never checked against the row it named produced an audit entry that
    misdescribed its own mutation. Here the organisation comes from the
    session rather than the caller, and the row has to match it or it does not
    exist as far as this caller is concerned -- whether a change exists is
    itself something to know.
    """
    found = session.scalars(
        select(OptimizationAction).where(
            OptimizationAction.id == action_id,
            OptimizationAction.organization_id == organization_id,
        )
    ).first()
    if found is None:
        raise LookupError("no such change")
    return found


def _may(role: Role | None, route: str) -> None:
    allowed = MAY_ANSWER.get(route, frozenset())
    if role is None or role not in allowed:
        if route == "expert":
            raise NotAllowed(
                "This change is large enough that a PPCWay expert has to sign it off."
                " We have been asked to look at it."
            )
        raise NotAllowed("Your role does not allow you to approve or reject changes.")


def _as_proposal(action: OptimizationAction) -> Proposal:
    """The row, back in the shape the guardrails judge.

    Rebuilt from what was stored rather than kept in memory between the two
    rulings, because the two rulings are days apart and the thing being judged
    the second time must be the thing that was written down.
    """
    after = action.after or {}
    return Proposal(
        kind=action.kind,
        customer_id=action.customer_id,
        target_id=action.target_id,
        target_label=action.target_label,
        new_daily_budget=_number(after.get("daily_budget")),
        new_target_cpa=_number(after.get("target_cpa")),
        new_bid=_number(after.get("bid")),
        change_pct=_number((action.expected_impact or {}).get("change_pct")),
        pauses=1 if action.kind == "pause_ad" else 0,
        # The age of the figures, as the row recorded it. This is the field the
        # freshness check reads, and it is why a six-day-old proposal is
        # refused at approval rather than applied on stale numbers.
        metrics_as_of=_oldest_figure(action),
        # Read from the payload, where the proposal put them. `after` is the
        # older home and nothing writes it there any more; both are read so a
        # row written either way is checked against what the merchant pinned.
        resources=tuple(
            str(r)
            for r in ((action.payload or {}).get("resources") or after.get("resources") or ())
        ),
        is_undo=action.undo_of is not None,
    )


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _oldest_figure(action: OptimizationAction) -> datetime | None:
    """When the oldest figure behind this was read.

    The oldest, not the newest: a proposal is only as fresh as its stalest
    number, and taking the newest would let one recently-read figure vouch for
    a fortnight-old one beside it.
    """
    cites = (action.evidence or {}).get("figures") or []
    times: list[datetime] = []
    for cite in cites:
        stamp = cite.get("as_of") if isinstance(cite, dict) else None
        if not stamp:
            continue
        try:
            when = datetime.fromisoformat(str(stamp))
        except ValueError:
            continue
        times.append(when if when.tzinfo else when.replace(tzinfo=UTC))
    return min(times) if times else None


def approve(
    session: Session,
    action_id: UUID,
    *,
    organization_id: UUID,
    account_id: UUID,
    role: Role | None,
    connection: AdsConnection,
    now: datetime | None = None,
) -> Answered:
    """Say yes, then check again whether yes is still allowed."""
    at = now or datetime.now(UTC)
    action = _theirs(session, action_id, organization_id)
    _may(role, action.route)

    if action.status != Status.AWAITING_APPROVAL.value:
        raise NotAnswerable(_already(action))
    if action.expires_at is not None and _aware(action.expires_at) <= at:
        action.status = Status.EXPIRED.value
        session.commit()
        raise NotAnswerable(
            "That change was offered more than a week ago and has expired."
            " Otto will propose it again if it is still worth doing."
        )

    said = judge(
        _as_proposal(action),
        standing_for(
            session,
            connection,
            organization_id=organization_id,
            target_id=action.target_id,
            now=at,
        ),
        limits_for(session, organization_id),
        now=at,
    )
    action.rechecked = said.as_dict()
    action.rechecked_at = at

    if said.ruling.verdict is Verdict.REJECTED:
        action.status = Status.REJECTED.value
        session.commit()
        log.info("approval of %s overturned by %s", action.id, said.ruling.check)
        return Answered(
            action=action,
            status=Status.REJECTED,
            words=(f"We checked again before making the change and stopped: {said.ruling.because}"),
            refused_by=said.ruling.check,
        )

    action.status = Status.APPROVED.value
    action.approved_by = account_id
    action.approved_at = at
    session.commit()
    # Only "approved". Whether the change is made now, later, or not at all is
    # the gateway's to say, and the caller says it: until 5 November this
    # promised "Otto will make the change and tell you when it is done" with
    # nothing behind it that could.
    return Answered(action=action, status=Status.APPROVED, words="Approved.")


def reject(
    session: Session,
    action_id: UUID,
    *,
    organization_id: UUID,
    account_id: UUID,
    role: Role | None,
    because: str = "",
    now: datetime | None = None,
) -> Answered:
    """Say no. No guardrails: nobody needs permission to decline a change."""
    at = now or datetime.now(UTC)
    action = _theirs(session, action_id, organization_id)
    _may(role, action.route)

    if action.status not in {Status.AWAITING_APPROVAL.value, Status.PROPOSED.value}:
        raise NotAnswerable(_already(action))

    action.status = Status.REJECTED.value
    action.approved_by = account_id
    action.approved_at = at
    # The first ruling's words are kept; this records that a person declined,
    # on the second-ruling columns, because a refusal by a person at a later
    # moment is a second decision about the same row.
    action.rechecked = {
        "verdict": "rejected",
        "check": "person",
        "because": because.strip() or "The owner declined this change.",
    }
    action.rechecked_at = at
    session.commit()
    return Answered(
        action=action,
        status=Status.REJECTED,
        words="Declined. Otto will not propose that one again this week.",
    )


def undo(
    session: Session,
    action_id: UUID,
    *,
    organization_id: UUID,
    account_id: UUID,
    role: Role | None,
    now: datetime | None = None,
) -> Answered:
    """Put a change back, by proposing the opposite of it.

    A new row, as the brief requires, and it goes through the guardrails like
    anything else when it is applied. The original stays `applied` until the
    reversing change has actually been made.
    """
    at = now or datetime.now(UTC)
    action = _theirs(session, action_id, organization_id)
    _may(role, action.route)

    if action.status != Status.APPLIED.value:
        raise NotAnswerable(
            "Only a change that was actually made can be put back, and that one "
            f"is {action.status.replace('_', ' ')}."
        )
    if not action.reversible:
        raise NotAnswerable(
            "That change cannot be put back. Money already spent and Google's own "
            "learning about your ads do not come back, whatever we do next."
        )
    if not may_undo(action, now=at):
        raise NotAnswerable(
            "That change was made more than 30 days ago, so PPCWay no longer offers to"
            " put it back. It can still be changed in Google Ads itself."
        )
    reverse = _reverse(action)
    already = session.scalars(
        select(OptimizationAction).where(
            OptimizationAction.undo_of == action.id,
            OptimizationAction.status.notin_(
                (Status.REJECTED.value, Status.FAILED.value, Status.EXPIRED.value)
            ),
        )
    ).first()
    if already is not None:
        raise NotAnswerable("That change is already being put back.")

    putting_back = OptimizationAction(
        organization_id=organization_id,
        customer_id=action.customer_id,
        kind=action.kind,
        target_kind=action.target_kind,
        target_id=action.target_id,
        target_label=action.target_label,
        # Swapped: the undo's job is to get back to where the original started.
        before=dict(action.after or {}),
        after=dict(action.before or {}),
        # And exactly what to send to get there, worked out now from what was
        # sent and what Google said it created, rather than at the door.
        payload=reverse,
        reason=f"Putting back: {action.reason}",
        undo_plan="An undo of an undo is just the original change again.",
        rule_id=action.rule_id,
        rule_version=action.rule_version,
        guardrail_config_version=action.guardrail_config_version,
        autonomy=action.autonomy,
        route=action.route,
        risk=action.risk,
        # A person asked for this one, whatever proposed the original.
        proposed_by=ProposedBy.OWNER.value if role is not Role.EXPERT else ProposedBy.EXPERT.value,
        status=Status.APPROVED.value,
        undo_of=action.id,
        # An undo of an undo is the original change, which is a thing somebody
        # can ask for again from the inbox rather than from here.
        reversible=False,
        approved_by=account_id,
        approved_at=at,
    )
    session.add(putting_back)
    session.flush()
    putting_back.idempotency_key = f"undo:{putting_back.id}"
    session.commit()
    return Answered(action=putting_back, status=Status.APPROVED, words="Putting that back.")


def _reverse(action: OptimizationAction) -> dict[str, Any]:
    """What to send to put this change back, from what was sent to make it.

    An exclusion is put back by removing the very negative keywords Google
    created, by the ids it gave them, which only its answer has. A status is put
    back to the status the row recorded before. Anything else was written before
    the log kept what it sent, and saying so beats sending a guess.
    """
    sent = action.payload or {}
    change = sent.get("change")
    if change == "exclude_search":
        made = [str(name) for name in ((action.outcome or {}).get("landed") or []) if name]
        if not made:
            raise NotAnswerable(
                "We have no record of what Google created for that change, so it cannot"
                " be put back from here. It can be removed in Google Ads itself."
            )
        return {"change": "remove_exclusions", "criteria": made}
    if change == "set_ad_status" and sent.get("ad"):
        was = str((action.before or {}).get("status") or "")
        if not was:
            raise NotAnswerable("We have no record of what that ad was set to before.")
        return {"change": "set_ad_status", "ad": str(sent["ad"]), "status": was}
    raise NotAnswerable(
        "That change was recorded before PPCWay kept what it sent to Google, so it"
        " has to be put back in Google Ads itself."
    )


def _already(action: OptimizationAction) -> str:
    """Why this cannot be answered, in words that say what happened instead."""
    said = {
        Status.APPROVED.value: "That change has already been approved.",
        Status.APPLIED.value: "That change has already been made.",
        Status.REJECTED.value: "That change was already declined.",
        Status.EXPIRED.value: "That change expired before anybody answered it.",
        Status.REVERTED.value: "That change was made and then put back.",
        Status.FAILED.value: "Google would not accept that change.",
        Status.PROPOSED.value: "Otto has not finished checking that one yet.",
    }
    return said.get(action.status, f"That change is {action.status.replace('_', ' ')}.")


def _aware(when: datetime) -> datetime:
    return when if when.tzinfo else when.replace(tzinfo=UTC)
