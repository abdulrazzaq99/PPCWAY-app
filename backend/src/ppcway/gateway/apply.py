"""Making an approved change, and recording exactly what happened.

The last step, and the one with the most ways to be wrong. The order below is
the order, and every line of it is load-bearing:

1. **The three switches**, read now. The write gate, the global kill switch,
   the account's own. A change refused here is not failed -- it stays approved,
   because nothing was attempted and it should go out when writes resume.
2. **The guardrails, once more.** They ran when the proposal was written and
   again when somebody approved it; this is the third time, and the first two
   do not cover it. A job can sit in a queue, and the thing that makes a
   change unsafe is the passage of time.
3. **Quota, then taken, before the call.** Room is read first, so a full day
   leaves the change approved for tomorrow. Then the change is *taken* --
   `taken_at`, set by an update only one sender can win -- and the day's
   count raised, in one commit. Taken is what makes a change go to Google at
   most once: the request that approved it, the scheduled pass and a retry of
   either can all reach it, and only one gets past here. An operation Google
   refuses still spends quota, and a crash between sending and counting would
   hide what was spent, so the honest error is to believe we have used
   slightly more than we have, never less.
4. **The call**, through the one door.
5. **The outcome**, written whatever it was, with what Google said -- the ids
   of what it created, or its words for what it refused -- and `applied` only
   when Google says every operation landed. This is the line Blueprint §5.6 is about: a
   batch where nine of ten keywords landed is not `applied`, and calling it so
   is how a platform comes to believe it created four hundred things when it
   created three hundred and eighty-six.

**Nothing here decides whether a change is a good idea.** By the time an action
reaches this module that has been decided three times by other code. This
decides only whether it is safe to send now, sends it, and says what Google
said.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CursorResult, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from ppcway.gateway import quota, switch
from ppcway.gateway.google import GoogleRefused
from ppcway.gateway.port import Applied, Batch, Door
from ppcway.opt.context import limits_for, standing_for
from ppcway.opt.guardrails import Verdict, judge
from ppcway.opt.models import UNDO_FOR, OptimizationAction, Status, may_undo

__all__ = ["UNDO_FOR", "CannotApply", "Outcome", "apply_now", "may_undo"]

log = logging.getLogger(__name__)

#: `UNDO_FOR` and `may_undo` live in `opt.models` now, beside the other limits
#: on a change's life, because asking for an undo is decided outside this
#: package. They are re-exported here for the callers that read them here.


class CannotApply(RuntimeError):
    """This change must not be sent now. The action is left as it was."""


@dataclass(frozen=True, slots=True)
class Outcome:
    """What became of one attempt to make a change."""

    action: OptimizationAction
    status: Status
    words: str
    #: Google's answer, where it was asked. None when nothing was sent.
    said: Applied | None = None
    #: Set when the account has crossed the brief's 80% quota threshold today
    #: for the first time, so a caller sends one alert rather than one a batch.
    quota_alert: bool = False


def apply_now(
    session: Session,
    action: OptimizationAction,
    operations: Batch,
    *,
    door: Door,
    connection: Any,
    organization_id: UUID,
    gate_open: bool,
    now: datetime | None = None,
) -> Outcome:
    """Send one approved change, in the order described at the top of this file."""
    at = now or datetime.now(UTC)

    if action.status != Status.APPROVED.value:
        raise CannotApply(
            f"only an approved change is sent, and that one is {action.status.replace('_', ' ')}."
        )

    # 1. The three switches, read now rather than when the job started.
    standing = switch.may_write(session, customer_id=action.customer_id, gate_open=gate_open)
    if not standing.may_write:
        # Left approved, not failed. Nothing was attempted, and it should go
        # out when writes resume rather than needing to be proposed again.
        log.info("not applying %s: %s", action.id, standing.stopped_by)
        raise CannotApply(standing.because)

    # 2. The guardrails, a third time. A job can sit in a queue.
    said = judge(
        _proposal_for(action, operations),
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
    if said.ruling.verdict is Verdict.REJECTED:
        words = f"We checked once more before sending and stopped: {said.ruling.because}"
        action.status = Status.REJECTED.value
        action.outcome = _said(at, words, ruling=said.as_dict())
        session.commit()
        log.info("refused %s at the last moment: %s", action.id, said.ruling.check)
        return Outcome(action=action, status=Status.REJECTED, words=words)

    # 3. Room for it today, read before the change is taken: a full day leaves
    # it approved, to go out tomorrow, rather than taken and stuck.
    if quota.room_today(session, action.customer_id, today=at.date()).left < operations.how_many:
        raise CannotApply(
            "This account has used its Google Ads allowance for today."
            " The change will go out tomorrow."
        )
    # Then taken, by one sender only, and counted: one commit, before the call.
    if not _take(session, action, at):
        raise CannotApply("That change is already being sent.")
    room = quota.spend(session, action.customer_id, operations.how_many, today=at.date())
    session.commit()

    # 4. The call.
    try:
        answered = door.mutate(operations)
    except GoogleRefused as exc:
        words = f"Google would not make that change: {exc}"
        action.status = Status.FAILED.value
        action.outcome = _said(at, words, refused_whole=str(exc))
        session.commit()
        log.warning("Google refused %s: %s", action.id, exc)
        return Outcome(
            action=action,
            status=Status.FAILED,
            words=words,
            quota_alert=room.say_something,
        )

    # 5. The outcome. `applied` only if everything landed.
    if answered.all_landed:
        action.status = Status.APPLIED.value
        action.applied_at = at
        action.outcome = _said(at, "Done.", answered=answered)
        if action.undo_of is not None:
            # This was an undo, and it worked, so the thing it reverses is now
            # reverted. Written here rather than when the undo was asked for:
            # until this moment nothing had been put back.
            original = session.get(OptimizationAction, action.undo_of)
            if original is not None and original.status == Status.APPLIED.value:
                original.status = Status.REVERTED.value
                original.reverted_at = at
        session.commit()
        return Outcome(
            action=action,
            status=Status.APPLIED,
            words="Done.",
            said=answered,
            quota_alert=room.say_something,
        )

    # Something landed and something did not. Not `applied`: see the note at
    # the top. The partial result is recorded so the next attempt knows what
    # is already there, and a person is told rather than the number being
    # rounded up.
    landed, sent = answered.how_many_landed, len(answered.landed)
    words = f"Google accepted {landed} of {sent} changes and refused the rest: " + "; ".join(
        f"{one.code}: {one.message}" for one in answered.refused[:3]
    )
    action.status = Status.FAILED.value
    action.outcome = _said(at, words, answered=answered)
    session.commit()
    log.warning("%s landed %d of %d operations", action.id, landed, sent)
    return Outcome(
        action=action,
        status=Status.FAILED,
        words=words,
        said=answered,
        quota_alert=room.say_something,
    )


def _take(session: Session, action: OptimizationAction, at: datetime) -> bool:
    """Take this change to send it, or find that another sender already has.

    One conditional update, so two senders arriving together cannot both win:
    the database lets one of them set `taken_at` and the other finds it set.
    """
    done = session.execute(
        update(OptimizationAction)
        .where(
            OptimizationAction.id == action.id,
            OptimizationAction.status == Status.APPROVED.value,
            OptimizationAction.taken_at.is_(None),
        )
        .values(taken_at=at)
        .execution_options(synchronize_session=False)
    )
    won = isinstance(done, CursorResult) and done.rowcount == 1
    if won:
        # Told to the row in memory as already saved, so the next commit does
        # not write it a second time.
        set_committed_value(action, "taken_at", at)
    return won


def _said(
    at: datetime,
    words: str,
    *,
    answered: Applied | None = None,
    refused_whole: str = "",
    ruling: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """What happened at the door, as the row keeps it."""
    out: dict[str, Any] = {"at": at.isoformat(), "words": words}
    if answered is not None:
        out["landed"] = list(answered.landed)
        out["refused"] = [
            {"at": one.at, "code": one.code, "message": one.message} for one in answered.refused
        ]
        out["operations_used"] = answered.operations_used
    if refused_whole:
        out["refused_whole"] = refused_whole
    if ruling is not None:
        out["ruling"] = ruling
    return out


def _proposal_for(action: OptimizationAction, operations: Batch) -> Any:
    """The action, in the shape the guardrails judge, with the real batch size.

    `pauses` comes from the batch rather than the action, because the
    blast-radius check is about how much this request would stop and the batch
    is the request. An action that said "pause one ad" and a batch carrying
    four hundred removals is exactly the disagreement that check exists for.
    """
    from dataclasses import replace as _replace

    from ppcway.opt.answer import _as_proposal

    base = _as_proposal(action)
    # Removing a negative keyword stops nothing: it lets a search back in.
    # Counted as a pause, the undo of an exclusion was measured against the
    # account's live ads and keywords, and on a small account refused.
    lets_back_in = (action.payload or {}).get("change") == "remove_exclusions"
    pauses = sum(
        1
        for op in operations.operations
        if (op.doing.value == "remove" and not lets_back_in)
        or str(op.fields.get("status", "")).upper() == "PAUSED"
    )
    return _replace(base, pauses=pauses)
