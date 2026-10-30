"""The daily pass: run the rules, rank what they found, and stop at ten a week.

Phase 1 of the client's brief is "recommendations, shown not applied", so this
emits recommendations and writes nothing to Google. It does not even write the
action log: that is the caller's job, after the guardrails have judged each one,
because the log records what was decided and the decision has not been made
here.

**The ten-a-week cap is here as well as in the guardrails, and they are
different jobs.** The guardrail refuses an eleventh change: it is a limit on
what may reach the account. This caps what is *offered*, which is a limit on
what a merchant is asked to read. Without it a first pass over a neglected
account would produce forty cards, the merchant would approve the first three
and never open the inbox again, and the guardrail would have refused numbers
eleven to forty after they had already done the damage -- to attention rather
than to money, but the inbox is the product.

**Nothing is proposed while the sync is failing.** The brief: "No decision on
data older than 36 hours or while sync is failing." The per-proposal freshness
check in the guardrails catches a stale figure; this catches the case where
every figure is stale for the same reason, and refuses the whole pass rather
than producing forty cards that will each be rejected one at a time.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import SyncRun
from ppcway.metric.figures import FRESH_HOURS
from ppcway.opt.models import OptimizationAction, Status
from ppcway.rules import library
from ppcway.rules.catalogue import Rule, live, waiting
from ppcway.rules.recommend import Recommendation, in_order

#: The client's brief: at most ten changes per account per week.
MOST_A_WEEK: Final = 10

#: The window that cap is measured over.
A_WEEK: Final = 7


@dataclass(frozen=True, slots=True)
class Pass:
    """What one run of the rules found, and what it chose to show."""

    customer_id: str
    ran_at: datetime
    #: The recommendations to put in front of the merchant, best first.
    offered: tuple[Recommendation, ...] = ()
    #: Found, ranked below the cap, and kept for next week rather than shown.
    held_back: tuple[Recommendation, ...] = ()
    #: How many of this week's ten are already used.
    used_this_week: int = 0
    #: Set when the pass refused to run at all, in words a log reader can act on.
    stopped: str = ""
    #: The rules that ran, and the ones the client has not specified yet.
    ran: tuple[str, ...] = ()
    not_specified: tuple[str, ...] = field(default_factory=tuple)

    @property
    def room_left(self) -> int:
        return max(0, MOST_A_WEEK - self.used_this_week)

    @property
    def ok(self) -> bool:
        return not self.stopped


def run(
    session: Session,
    customer_id: str,
    *,
    currency: str,
    target_cost_per_lead: float,
    today: date | None = None,
    now: datetime | None = None,
    protected: Sequence[str] = (),
    blocked: Sequence[str] = (),
) -> Pass:
    """One pass over one account. Reads the mirror, writes nothing."""
    at = now or datetime.now(UTC)
    day = today or at.date()
    unspecified = tuple(r.id for r in waiting())

    trouble = _sync_trouble(session, customer_id, at)
    if trouble:
        return Pass(
            customer_id=customer_id,
            ran_at=at,
            stopped=trouble,
            not_specified=unspecified,
        )

    found: list[Recommendation] = []
    ran: list[str] = []
    for spec in live():
        ran.append(spec.id)
        found.extend(
            _for(
                spec, session, customer_id, currency, target_cost_per_lead, day, protected, blocked
            )
        )

    used = _used_this_week(session, customer_id, at)
    room = max(0, MOST_A_WEEK - used)
    ranked = in_order(found)
    return Pass(
        customer_id=customer_id,
        ran_at=at,
        offered=tuple(ranked[:room]),
        held_back=tuple(ranked[room:]),
        used_this_week=used,
        ran=tuple(ran),
        not_specified=unspecified,
    )


def _for(
    spec: Rule,
    session: Session,
    customer_id: str,
    currency: str,
    target_cost_per_lead: float,
    day: date,
    protected: Sequence[str],
    blocked: Sequence[str],
) -> list[Recommendation]:
    """Dispatch to the one function that implements a rule.

    A mapping rather than a method on `Rule`, so the catalogue stays data and
    can be read without importing anything that touches a database.
    """
    if spec.id == "R1":
        return library.wasteful_terms(
            session,
            customer_id,
            currency=currency,
            target_cost_per_lead=target_cost_per_lead,
            today=day,
            protected=protected,
            blocked=blocked,
        )
    if spec.id == "R4":
        return library.disapproved_ads(session, customer_id, currency=currency, today=day)
    # Unreachable while `live()` only returns implemented rules, and a test
    # says so. Here rather than an assert because a rule marked implemented
    # with nothing behind it should produce nothing, not a crash in a job.
    return []


def _used_this_week(session: Session, customer_id: str, at: datetime) -> int:
    """How many changes this account has had, or is waiting on, in seven days.

    Rejected ones are not counted: they never happened, and counting them would
    let a run of refusals use up a merchant's allowance of real changes.
    """
    since = at - timedelta(days=A_WEEK)
    rows = session.scalars(
        select(OptimizationAction.id).where(
            OptimizationAction.customer_id == customer_id,
            OptimizationAction.created_at >= since,
            OptimizationAction.status.in_((Status.PENDING.value, Status.APPLIED.value)),
        )
    ).all()
    return len(rows)


def _sync_trouble(session: Session, customer_id: str, at: datetime) -> str:
    """Why this pass must not run, or empty if it may."""
    last = session.scalars(
        select(SyncRun)
        .where(SyncRun.customer_id == customer_id)
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    ).first()
    if last is None:
        return (
            "this account has never been read, so there are no figures to recommend anything from"
        )
    if last.status == "failed":
        return f"the last read of this account failed, so nothing is proposed: {last.trouble}"
    if last.status == "running":
        return "a read of this account is still going, so the figures are half a picture"
    finished = last.finished_at or last.started_at
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=UTC)
    age = at - finished
    if age > timedelta(hours=FRESH_HOURS):
        hours = int(age.total_seconds() // 3600)
        return (
            f"the figures for this account were last read {hours} hours ago, past the"
            f" {FRESH_HOURS}-hour limit, so no decision may rest on them"
        )
    return ""
