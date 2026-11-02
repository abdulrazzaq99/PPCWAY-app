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
3. **Quota, counted before the call.** An operation Google refuses still
   spends it, and a crash between sending and counting would hide what was
   spent. The honest error is to believe we have used slightly more than we
   have, never less.
4. **The call**, through the one door.
5. **The outcome**, written whatever it was -- and `applied` only when Google
   says every operation landed. This is the line Blueprint §5.6 is about: a
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
from datetime import UTC, datetime, timedelta
from typing import Any, Final
from uuid import UUID

from sqlalchemy.orm import Session

from ppcway.gateway import quota, switch
from ppcway.gateway.google import GoogleRefused
from ppcway.gateway.port import Applied, Batch, Door
from ppcway.opt.context import limits_for, standing_for
from ppcway.opt.guardrails import Verdict, judge
from ppcway.opt.models import OptimizationAction, Status

log = logging.getLogger(__name__)

#: How long an applied change may be put back. The client's brief: 30-day undo.
#: Past it the structure can still be changed by hand, but PPCWay stops
#: offering to do it: an undo built from a month-old `before` is a change to an
#: account that has moved on.
UNDO_FOR: Final = timedelta(days=30)


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


def may_undo(action: OptimizationAction, *, now: datetime | None = None) -> bool:
    """Whether this is still inside the thirty-day window.

    Read from `applied_at` rather than `created_at`: the window the brief means
    is thirty days since the change was made, not since it was suggested, and a
    proposal that waited six days for a yes would otherwise lose six days of
    its undo.
    """
    if action.status != Status.APPLIED.value or not action.reversible:
        return False
    if action.applied_at is None:
        return False
    at = now or datetime.now(UTC)
    made = action.applied_at
    made = made if made.tzinfo else made.replace(tzinfo=UTC)
    return (at - made) <= UNDO_FOR


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
        action.status = Status.REJECTED.value
        session.commit()
        log.info("refused %s at the last moment: %s", action.id, said.ruling.check)
        return Outcome(
            action=action,
            status=Status.REJECTED,
            words=f"We checked once more before sending and stopped: {said.ruling.because}",
        )

    # 3. Quota, counted before the call.
    room = quota.spend(session, action.customer_id, operations.how_many, today=at.date())
    if room.left <= 0:
        session.commit()
        raise CannotApply(
            "This account has used its Google Ads allowance for today."
            " The change will go out tomorrow."
        )
    session.commit()

    # 4. The call.
    try:
        answered = door.mutate(operations)
    except GoogleRefused as exc:
        action.status = Status.FAILED.value
        session.commit()
        log.warning("Google refused %s: %s", action.id, exc)
        return Outcome(
            action=action,
            status=Status.FAILED,
            words=f"Google would not make that change: {exc}",
            quota_alert=room.say_something,
        )

    # 5. The outcome. `applied` only if everything landed.
    if answered.all_landed:
        action.status = Status.APPLIED.value
        action.applied_at = at
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
    action.status = Status.FAILED.value
    session.commit()
    landed, sent = answered.how_many_landed, len(answered.landed)
    log.warning("%s landed %d of %d operations", action.id, landed, sent)
    return Outcome(
        action=action,
        status=Status.FAILED,
        words=(
            f"Google accepted {landed} of {sent} changes and refused the rest: "
            + "; ".join(f"{one.code}: {one.message}" for one in answered.refused[:3])
        ),
        said=answered,
        quota_alert=room.say_something,
    )


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
    pauses = sum(
        1
        for op in operations.operations
        if op.doing.value == "remove" or str(op.fields.get("status", "")).upper() == "PAUSED"
    )
    return _replace(base, pauses=pauses)
