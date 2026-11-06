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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ppcway.ads.clock import account_today
from ppcway.ads.mirror import MICRO, CampaignDay, SyncRun
from ppcway.metric.figures import FRESH_HOURS
from ppcway.opt.models import COUNTS_TOWARD_CAP, UNDO_FOR, OptimizationAction, Status
from ppcway.rules import library
from ppcway.rules.catalogue import Rule, live, waiting
from ppcway.rules.recommend import Recommendation, in_order

#: The client's brief: at most ten changes per account per week.
MOST_A_WEEK: Final = 10

#: The window that cap is measured over.
A_WEEK: Final = 7

#: Rows that mean a target is still being dealt with, at any age: offered and
#: waiting for an answer, or approved and waiting to be sent. Offering the same
#: change again beside one of these is two cards for one decision -- and, once
#: changes are sent, two attempts at one change.
STILL_OPEN: Final = frozenset(
    {Status.PROPOSED.value, Status.AWAITING_APPROVAL.value, Status.APPROVED.value}
)


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
    #: Why the rules that rest on leads did not run, in the merchant's words:
    #: the account counts no enquiries, so nothing can be called wasted.
    cannot_check: str = ""

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
    day = today or account_today(session, customer_id, at)
    unspecified = tuple(r.id for r in waiting())

    trouble = _sync_trouble(session, customer_id, at)
    if trouble:
        return Pass(
            customer_id=customer_id,
            ran_at=at,
            stopped=trouble,
            not_specified=unspecified,
        )

    blind = _cannot_tell_leads(session, customer_id, day)
    found: list[Recommendation] = []
    ran: list[str] = []
    for spec in live():
        if blind and spec.id in RESTS_ON_LEADS:
            continue
        ran.append(spec.id)
        found.extend(
            _for(
                spec, session, customer_id, currency, target_cost_per_lead, day, protected, blocked
            )
        )

    # What the log already has an answer for is not found again. Without this
    # every night re-offered the same search until Google's own report caught
    # up, and "Otto will not propose that one again this week" was not true.
    taken = spoken_for(session, customer_id, at)
    found = [one for one in found if (one.rule.kind, one.target_id) not in taken]

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
        cannot_check=blind,
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


def spoken_for(session: Session, customer_id: str, at: datetime) -> dict[tuple[str, str], str]:
    """The changes, by kind and target, that are not to be offered again yet,
    each with the status that holds it -- so a caller can say why, as the chat
    does when somebody asks it to propose one of these.

    - still open, at any age: waiting for an answer, or approved and not sent;
    - made in the last thirty days, which is how long Google's own reports can
      take to show it and how long it can be undone;
    - put back in the last thirty days: the merchant undid it, and offering it
      again the next morning would be arguing with them;
    - declined by a person, or refused by Google, in the last week. What the
      inbox tells a merchant who says no is "Otto will not propose that one
      again this week", and this is what makes it true.

    Not an offer that expired -- nobody said no to it, and the inbox says "Otto
    will propose it again if it is still worth doing" -- and not one a
    guardrail refused, which may pass tomorrow on fresher figures.
    """
    rows = session.execute(
        select(
            OptimizationAction.kind,
            OptimizationAction.target_id,
            OptimizationAction.status,
            OptimizationAction.rechecked,
            OptimizationAction.created_at,
            OptimizationAction.applied_at,
            OptimizationAction.reverted_at,
        ).where(
            OptimizationAction.customer_id == customer_id,
            # An undo carries its original's kind and target, and the original's
            # own status already says where that change stands.
            OptimizationAction.undo_of.is_(None),
        )
    ).all()
    week = timedelta(days=A_WEEK)
    taken: dict[tuple[str, str], str] = {}
    for kind, target, status, rechecked, created, applied, reverted in rows:
        recent = _since(at, created)
        if status in STILL_OPEN:
            keep = True
        elif status == Status.APPLIED.value:
            keep = _since(at, applied or created) <= UNDO_FOR
        elif status == Status.REVERTED.value:
            keep = _since(at, reverted or created) <= UNDO_FOR
        elif status == Status.FAILED.value:
            keep = recent <= week
        elif status == Status.REJECTED.value:
            by_a_person = isinstance(rechecked, dict) and rechecked.get("check") == "person"
            keep = by_a_person and recent <= week
        else:
            keep = False
        # A row still open says more than an older answer beside it.
        if keep and taken.get((kind, target)) not in STILL_OPEN:
            taken[(kind, target)] = status
    return taken


def _since(at: datetime, when: datetime) -> timedelta:
    """How long ago, with SQLite's naive timestamps read as the UTC they are."""
    return at - (when if when.tzinfo else when.replace(tzinfo=UTC))


def _used_this_week(session: Session, customer_id: str, at: datetime) -> int:
    """How many changes this account has had, or is waiting on, in seven days.

    Which states count is `COUNTS_TOWARD_CAP`, and the reasoning is there: a
    refusal, an offer nobody answered and a change Google would not have are
    all things the merchant did not get, so counting them would spend their
    allowance of real changes on a run of failures.
    """
    since = at - timedelta(days=A_WEEK)
    rows = session.scalars(
        select(OptimizationAction.id).where(
            OptimizationAction.customer_id == customer_id,
            OptimizationAction.created_at >= since,
            OptimizationAction.status.in_([s.value for s in COUNTS_TOWARD_CAP]),
        )
    ).all()
    return len(rows)


#: The rules that call something wasted because it brought no leads. On an
#: account that counts no leads at all, every search looks wasted -- including
#: the ones the business lives on -- so these do not run there.
RESTS_ON_LEADS: Final = frozenset({"R1"})

#: The window that question is asked over, which is R1's own.
LEADS_WINDOW_DAYS: Final = 30


def _cannot_tell_leads(session: Session, customer_id: str, day: date) -> str:
    """Why nothing here can be called wasted, or empty if it can.

    An account that spent money and counted not one call, form, sign-up or
    sale has no conversion tracking that means anything. Excluding searches
    there would be guessing, and the first guess would be its busiest search.
    """
    since = day - timedelta(days=LEADS_WINDOW_DAYS)
    spent, leads, not_leads = session.execute(
        select(
            func.coalesce(func.sum(CampaignDay.cost_micros), 0),
            func.coalesce(func.sum(CampaignDay.calls + CampaignDay.forms), 0.0),
            func.coalesce(func.sum(CampaignDay.not_leads), 0.0),
        ).where(
            CampaignDay.customer_id == customer_id,
            CampaignDay.day >= since,
            CampaignDay.day <= day,
        )
    ).one()
    if spent <= 0 or leads > 0:
        return ""
    counted = round(float(not_leads or 0.0))
    seen = (
        f" It counted {counted} page {'view' if counted == 1 else 'views'} and the like,"
        " which are not enquiries."
        if counted > 0
        else ""
    )
    return (
        f"Google Ads counted no enquiries on this account in the last {LEADS_WINDOW_DAYS}"
        f" days, after spending {spent / MICRO:,.2f}: no calls, forms, sign-ups or sales.{seen}"
        " Otto cannot tell a wasted search from a working one until enquiries are tracked,"
        " so it is not suggesting any exclusions."
    )


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
