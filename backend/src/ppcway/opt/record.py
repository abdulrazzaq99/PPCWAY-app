"""Writing a judged proposal into the log, before anything is done about it.

Blueprint §8.4's first property: the row exists, with `before` captured, before
the call to Google. A row written afterwards is missing exactly when the crash
happened, which is the only time anybody needs it.

So this is the single place a proposal enters the log, and it takes the
recommendation and the guardrails' judgement together. That pairing is
deliberate: a row that recorded what a rule wanted without recording what the
guardrails said about it would be a row that could not explain itself, and the
two arriving separately is how they would come to disagree.

Nothing here talks to Google. What the log says about a change and what was
done about it are separate steps on purpose, and the order between them is the
property the log exists to provide.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from ppcway.opt.guardrails import Judgement, Verdict
from ppcway.opt.models import (
    APPROVAL_EXPIRES_DAYS,
    Autonomy,
    OptimizationAction,
    ProposedBy,
    Status,
)
from ppcway.rules.recommend import Recommendation

log = logging.getLogger(__name__)

#: The states an offer can time out of. Nothing else has a deadline: an applied
#: change does not expire, and a refusal has nothing to wait for.
CAN_EXPIRE: frozenset[str] = frozenset({Status.PROPOSED.value, Status.AWAITING_APPROVAL.value})


def _status_for(said: Judgement, autonomy: str, auto_eligible: bool) -> str:
    """What state a judged proposal starts in.

    Three inputs, because three things have to agree before a change may go
    without being asked about: the guardrails have to allow it, the merchant
    has to have chosen full auto, and the client has to have named this change
    type as one that may run unattended. Any one of them missing means a person
    is asked -- which is approve-first, and is the default for a reason.
    """
    verdict = said.ruling.verdict
    if verdict is Verdict.REJECTED:
        return Status.REJECTED.value
    if verdict is Verdict.REQUIRES_APPROVAL:
        return Status.AWAITING_APPROVAL.value
    if autonomy == Autonomy.FULL_AUTO.value and auto_eligible:
        return Status.APPROVED.value
    return Status.AWAITING_APPROVAL.value


def write_proposal(
    session: Session,
    found: Recommendation,
    said: Judgement,
    *,
    organization_id: Any,
    guardrail_config_version: int,
    autonomy: str = Autonomy.APPROVE_FIRST.value,
    proposed_by: str = ProposedBy.RULE.value,
    job_run: str = "",
    now: datetime | None = None,
) -> OptimizationAction:
    """One row, written before anything is applied. Returns it, uncommitted.

    Uncommitted on purpose: the caller writes a pass's worth of rows and
    commits once, so a job that dies halfway leaves either all of a run's
    proposals or none, rather than a half-offered inbox.
    """
    at = now or datetime.now(UTC)
    status = _status_for(said, autonomy, found.rule.auto_eligible)
    row = OptimizationAction(
        organization_id=organization_id,
        customer_id=found.customer_id,
        kind=found.rule.kind,
        target_kind=found.target_kind,
        target_id=found.target_id,
        target_label=found.target_label,
        before=dict(found.before),
        after=dict(found.after),
        reason=found.reason,
        evidence={"figures": [dict(cite) for cite in found.evidence]},
        expected_impact={
            "money_a_month": round(found.impact.money_a_month, 2),
            "currency": found.impact.currency,
            "confidence": round(found.impact.confidence, 3),
            "words": found.impact.words,
            "blocking": found.impact.blocking,
            "priority": found.priority,
        },
        undo_plan=found.undo,
        window_start=found.figures[0].period.start if found.figures else None,
        window_end=found.figures[0].period.end if found.figures else None,
        rule_id=found.rule.id,
        rule_version=found.rule.version,
        guardrail_config_version=guardrail_config_version,
        autonomy=autonomy,
        job_run=job_run,
        route=found.route.value,
        risk=found.risk.value,
        proposed_by=proposed_by,
        status=status,
        decided_by=said.ruling.check,
        decided_because=said.ruling.because,
        reversible=found.reversible,
        # Only an offer has a deadline. Writing it at insert rather than
        # working it out on read means a row that was allowed to expire says
        # when it was due, not when somebody got round to asking.
        expires_at=(at + timedelta(days=APPROVAL_EXPIRES_DAYS) if status in CAN_EXPIRE else None),
    )
    session.add(row)
    session.flush()
    # Derived from the row's own id, so a retry of the same action cannot apply
    # it twice. Blueprint §5.6. Set after the flush because the id is the
    # thing it is derived from.
    row.idempotency_key = f"{found.rule.id}:{row.id}"
    return row


def expire_old(session: Session, *, now: datetime | None = None) -> int:
    """Mark every offer nobody answered in time. Returns how many.

    A row moves state by somebody writing the move down, never by the clock
    being read: two readers comparing a row against their own clocks would
    otherwise disagree about history, and the log is the thing that is supposed
    to settle that.
    """
    at = now or datetime.now(UTC)
    done = session.execute(
        update(OptimizationAction)
        .where(
            OptimizationAction.status.in_(tuple(CAN_EXPIRE)),
            OptimizationAction.expires_at.is_not(None),
            OptimizationAction.expires_at <= at,
        )
        .values(status=Status.EXPIRED.value)
    )
    # An UPDATE always returns a CursorResult; the generic signature of
    # `Session.execute` does not say so, and `rowcount` is the only thing worth
    # knowing about the result.
    how_many = (getattr(done, "rowcount", 0) or 0) if isinstance(done, CursorResult) else 0
    if how_many:
        log.info("%d proposals expired without an answer", how_many)
    return how_many


def waiting_for(session: Session, organization_id: Any) -> list[OptimizationAction]:
    """Everything this business has been asked about and has not answered."""
    return list(
        session.scalars(
            select(OptimizationAction)
            .where(
                OptimizationAction.organization_id == organization_id,
                OptimizationAction.status == Status.AWAITING_APPROVAL.value,
            )
            .order_by(OptimizationAction.created_at.desc())
        )
    )
