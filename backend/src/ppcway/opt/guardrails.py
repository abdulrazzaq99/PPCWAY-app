"""The layer that stands between an automated decision and a merchant's money.

Blueprint §5.5. Ten checks, in this order, first failure short-circuits, and
**fail-closed**: a check that cannot be evaluated returns REJECTED. Not knowing
whether a change is safe is not a reason to make it.

This is the only code path permitted to authorise a mutate. Any service that
could get past it is a defect, not a shortcut.

Everything here is a pure function of (proposal, standing, limits). That is
what makes automated spend changes testable, and the tests are what make them
defensible.

One judgement call, written down because it is a departure. The blueprint lists
APPROVE_FIRST under check 3 and says first failure short-circuits. Stopping
there would queue a change for the merchant's tap **without** running checks 5
to 10 — so a tap could authorise a budget past the hard ceiling. So an
approval-level finding is remembered rather than returned: the remaining checks
all run, and a proposal that survives them comes back as REQUIRES_APPROVAL
instead of APPROVED. A merchant saying yes must not be able to say yes to
something the limits forbid.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from ppcway.metric.figures import FRESH_HOURS
from ppcway.opt.models import Autonomy

log = logging.getLogger(__name__)


class Verdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass(frozen=True)
class Ruling:
    """What the layer decided, which check decided it, and why in plain words."""

    verdict: Verdict
    check: str = ""
    because: str = ""

    @property
    def may_apply(self) -> bool:
        return self.verdict is Verdict.APPROVED

    def as_dict(self) -> dict[str, Any]:
        return {"verdict": self.verdict.value, "check": self.check, "because": self.because}


@dataclass(frozen=True)
class Proposal:
    """One change somebody wants to make, with everything the checks need."""

    kind: str
    customer_id: str
    target_id: str = ""
    target_label: str = ""
    #: The numbers it would set. None means this change does not touch that one.
    new_daily_budget: float | None = None
    new_target_cpa: float | None = None
    new_bid: float | None = None
    #: How far this moves the number it touches, as a percentage of today's.
    change_pct: float | None = None
    #: How many live things it would pause. Zero for anything that pauses none.
    pauses: int = 0
    #: When the numbers behind this decision were last refreshed. None means we
    #: do not know, which is not the same as fresh.
    metrics_as_of: datetime | None = None
    #: Google resource names this touches, checked against what is pinned.
    resources: tuple[str, ...] = ()
    #: True when this change exists to reverse one already made. Four of the
    #: ten checks do not apply to one, and `SKIP_FOR_UNDO` says which and why.
    is_undo: bool = False


@dataclass(frozen=True)
class Standing:
    """What is true of the account and the day so far."""

    link_active: bool = False
    token_refreshable: bool = False
    account_status: str = ""
    billing_on_hold: bool = True
    #: The Google account this merchant is actually allowed to touch.
    own_customer_id: str = ""
    changes_to_entity_today: int = 0
    changes_today: int = 0
    #: How far the day's changes have already moved this number, as a percent.
    moved_pct_today: float = 0.0
    active_entities: int = 0
    quota_left: int = 0


@dataclass(frozen=True)
class Limits:
    """The versioned guardrail configuration, as a plain value."""

    version: int = 0
    autonomy: str = Autonomy.APPROVE_FIRST.value
    max_daily_budget: float = 0.0
    max_cpa: float = 0.0
    min_bid: float = 0.0
    max_bid: float = 0.0
    #: The client's three bands, settled in their brief of 30 October: up to
    #: 20% is the normal route, 20% to 50% goes to an expert, and over 50% in
    #: one change is refused outright. The middle band is the whole reason
    #: `expert_max_change_pct` exists -- without it, a 30% rise is simply
    #: rejected and never reaches the person whose job is to judge it.
    max_change_pct: float = 20.0
    expert_max_change_pct: float = 50.0
    #: And no more than this in a day, however many changes it takes.
    max_daily_change_pct: float = 100.0
    max_changes_per_entity_day: int = 2
    max_changes_per_day: int = 20
    max_pause_pct: float = 10.0
    #: The brief's own figure: "No decision on data older than 36 hours". Three
    #: hours until 5 November, which refused every search-term change approved
    #: after breakfast -- those figures are settled a day behind and read once a
    #: night -- so the merchant's yes could never get past its own recheck.
    staleness_minutes: int = FRESH_HOURS * 60
    hands_off: tuple[str, ...] = ()


#: The checks an undo does not have to pass, and the reason for each. Found
#: while building the write path: the velocity limit counted a change and its
#: own reversal as two changes to the same thing, so undoing something was
#: refused as thrashing. A limit that stops a merchant reversing a mistake
#: traps them in it, which is the opposite of what a guardrail is for.
#:
#: * `velocity_limits` -- an undo is not thrashing, it is a return to a state
#:   that was in force before. The changes it reverses were themselves rate
#:   limited, so nothing can loop: after two changes to a thing the next one
#:   is refused, and only the undos remain free.
#: * `delta_limits` -- the number goes back to a value this account already
#:   had. Asking an expert to re-approve the reversal of a change they
#:   approved an hour ago is a worse outcome than the original mistake.
#: * `data_freshness` -- an undo rests on the `before` that was stored when
#:   the change was made, not on current metrics. Requiring fresh figures to
#:   undo would mean a merchant cannot undo while the sync is broken, which is
#:   exactly when they most want to.
#: * `autonomy_level` -- a person asked for this one explicitly. Holding it for
#:   approval would be asking them to approve their own request.
#:
#: Everything else still applies, and deliberately: an undo still has to be
#: for an account this business owns, still may not push past a hard spend
#: ceiling, still may not pause most of an account, and still needs a working
#: connection and some quota.
SKIP_FOR_UNDO: frozenset[str] = frozenset(
    {"velocity_limits", "delta_limits", "data_freshness", "autonomy_level"}
)

#: Returned by a check that is happy. Anything else stops the run.
Passed = None
Check = Callable[[Proposal, Standing, Limits, datetime], "Ruling | None"]


def _no(check: str, because: str) -> Ruling:
    return Ruling(Verdict.REJECTED, check, because)


# --- the ten, in order ------------------------------------------------------


def link_valid(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    if not s.link_active:
        return _no("link_valid", "The Google Ads connection is not active.")
    if not s.token_refreshable:
        return _no("link_valid", "The permission to reach this account has stopped working.")
    return Passed


def account_serviceable(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    status = (s.account_status or "").upper()
    if not status:
        return _no("account_serviceable", "We cannot tell what state this account is in.")
    if status in {"SUSPENDED", "CANCELED", "CANCELLED", "CLOSED"}:
        return _no("account_serviceable", f"The account is {status.lower()}.")
    if s.billing_on_hold:
        return _no("account_serviceable", "Billing on this account is on hold.")
    return Passed


def autonomy_level(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    """Enforced here, never in the interface, so nothing can act above it."""
    level = limits.autonomy
    if level == Autonomy.FULL_AUTO.value:
        return Passed
    if level == Autonomy.APPROVE_FIRST.value:
        return Ruling(
            Verdict.REQUIRES_APPROVAL,
            "autonomy_level",
            "This account applies nothing without being asked first.",
        )
    if level == Autonomy.ALERTS_ONLY.value:
        return _no("autonomy_level", "This account is set to tell you and change nothing.")
    return _no("autonomy_level", "This account has no autonomy level set.")


def scope(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    """The entity belongs to this merchant, and is not one they pinned.

    Redundant with row-level security and the application logic, and it stays:
    the cost of the redundancy is one comparison, and the cost of the failure
    it prevents is spending one merchant's money on another's campaign.
    """
    if not s.own_customer_id or not p.customer_id:
        return _no("scope", "We cannot tell which account this change belongs to.")
    if p.customer_id != s.own_customer_id:
        return _no("scope", "That change is for an account this business does not own.")
    pinned = [r for r in p.resources if r in limits.hands_off]
    if pinned:
        return _no("scope", "You have asked us to leave that one alone.")
    return Passed


def hard_spend_limits(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    """The ceilings a change may not cross.

    The daily budget ceiling governs a rise. A cut cannot breach a spending
    ceiling, and putting back the merchant's own earlier budget is not a new
    rise: refusing either for want of a ceiling would leave a merchant unable
    to spend less, or unable to undo a cut they regret (found 10 November,
    building the budget rules). A change whose direction is not recorded is
    treated as a rise, the safe way round.
    """
    raising = p.change_pct is None or p.change_pct > 0
    if p.new_daily_budget is not None and raising and not p.is_undo:
        if limits.max_daily_budget <= 0:
            return _no(
                "hard_spend_limits", "No daily budget ceiling has been set for this account."
            )
        if p.new_daily_budget > limits.max_daily_budget:
            return _no(
                "hard_spend_limits",
                f"That would set a daily budget of {p.new_daily_budget:,.2f}, "
                f"above your ceiling of {limits.max_daily_budget:,.2f}.",
            )
    if p.new_target_cpa is not None:
        if limits.max_cpa <= 0:
            return _no("hard_spend_limits", "No cost-per-action ceiling has been set.")
        if p.new_target_cpa > limits.max_cpa:
            return _no(
                "hard_spend_limits",
                f"That target of {p.new_target_cpa:,.2f} is above your ceiling "
                f"of {limits.max_cpa:,.2f}.",
            )
    if p.new_bid is not None:
        if limits.max_bid <= 0:
            return _no("hard_spend_limits", "No bid range has been set for this account.")
        if not (limits.min_bid <= p.new_bid <= limits.max_bid):
            return _no(
                "hard_spend_limits",
                f"That bid of {p.new_bid:,.2f} is outside your range of "
                f"{limits.min_bid:,.2f} to {limits.max_bid:,.2f}.",
            )
    return Passed


def delta_limits(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    """How far one change may move a number, and how far today's may in total.

    The per-change cap alone is not enough. Twenty percent a day is a
    thirty-eight times budget increase over a year, each step of it inside the
    rules. The daily cumulative cap is what actually bounds the exposure.

    Three bands rather than two, which is the client's decision of 30 October
    and not a softening. Over the hard ceiling is refused as before. Between
    the ordinary cap and that ceiling, the answer is not "no" but "not by
    you": the change goes to an expert. Returning a flat rejection there would
    mean a merchant who genuinely needs to double a budget has no route at
    all, which is how a guardrail gets switched off rather than respected.
    """
    if p.change_pct is None:
        return Passed
    size = abs(p.change_pct)
    if size > limits.expert_max_change_pct:
        return _no(
            "delta_limits",
            f"That moves it by {size:.0f}%, which is past the {limits.expert_max_change_pct:.0f}%"
            f" ceiling for a single change. Nobody here can approve that; it has to be"
            f" done in smaller steps.",
        )
    if size > limits.max_change_pct:
        return Ruling(
            Verdict.REQUIRES_APPROVAL,
            "delta_limits",
            f"That moves it by {size:.0f}%, more than the {limits.max_change_pct:.0f}% a"
            f" change is normally allowed, so a PPCWay expert has to sign it off.",
        )
    if abs(s.moved_pct_today) + size > limits.max_daily_change_pct:
        return _no(
            "delta_limits",
            f"Today's changes have already moved it {abs(s.moved_pct_today):.0f}%, "
            f"and the day's limit is {limits.max_daily_change_pct:.0f}%.",
        )
    return Passed


def velocity_limits(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    if s.changes_to_entity_today >= limits.max_changes_per_entity_day:
        return _no(
            "velocity_limits",
            f"That has been changed {s.changes_to_entity_today} times today already.",
        )
    if s.changes_today >= limits.max_changes_per_day:
        return _no(
            "velocity_limits",
            f"{s.changes_today} changes have been made to this account today already.",
        )
    return Passed


def blast_radius(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    """What stops a bad metrics read from pausing an entire account.

    The realistic catastrophe is not a slightly wrong bid. It is a metrics
    pipeline returning zeros and the rules concluding that every keyword is
    non-converting. Capping the share anything may pause turns an account-wide
    outage into a small, visible anomaly.
    """
    if p.pauses <= 0:
        return Passed
    if s.active_entities <= 0:
        return _no("blast_radius", "We cannot tell how much of this account that would pause.")
    share = p.pauses / s.active_entities * 100
    if share > limits.max_pause_pct:
        return _no(
            "blast_radius",
            f"That would pause {share:.0f}% of what is running, and the limit "
            f"is {limits.max_pause_pct:.0f}%.",
        )
    return Passed


def data_freshness(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    """A spend decision made on stale data is worse than no decision."""
    if p.metrics_as_of is None:
        return _no("data_freshness", "We do not know how old the figures behind this are.")
    seen = p.metrics_as_of if p.metrics_as_of.tzinfo else p.metrics_as_of.replace(tzinfo=UTC)
    old = now - seen
    if old > timedelta(minutes=limits.staleness_minutes):
        return _no(
            "data_freshness",
            f"The figures behind this are {int(old.total_seconds() // 3600)} hours old.",
        )
    return Passed


def quota(p: Proposal, s: Standing, limits: Limits, now: datetime) -> Ruling | None:
    if s.quota_left <= 0:
        return _no("quota", "We have used today's allowance of changes to Google.")
    return Passed


#: The order is the specification, so it is written once, as data, and the
#: tests assert it rather than trusting the reading order of a function.
ORDER: tuple[tuple[str, Check], ...] = (
    ("link_valid", link_valid),
    ("account_serviceable", account_serviceable),
    ("autonomy_level", autonomy_level),
    ("scope", scope),
    ("hard_spend_limits", hard_spend_limits),
    ("delta_limits", delta_limits),
    ("velocity_limits", velocity_limits),
    ("blast_radius", blast_radius),
    ("data_freshness", data_freshness),
    ("quota", quota),
)


@dataclass
class Judgement:
    """The ruling, and every check that was run to reach it."""

    ruling: Ruling
    ran: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {**self.ruling.as_dict(), "checks_run": self.ran}


def judge(
    proposal: Proposal,
    standing: Standing,
    limits: Limits,
    *,
    now: datetime | None = None,
) -> Judgement:
    """Run the ten, in order, and say what may happen to this proposal."""
    at = now or datetime.now(UTC)
    ran: list[str] = []
    held_for_approval: Ruling | None = None

    for name, check in ORDER:
        if proposal.is_undo and name in SKIP_FOR_UNDO:
            # Recorded as skipped rather than silently omitted: the log keeps
            # `checks_run`, and a reader comparing two actions needs to see
            # that a check was passed over rather than wonder if it ran.
            ran.append(f"{name}:skipped_for_undo")
            continue
        ran.append(name)
        try:
            said = check(proposal, standing, limits, at)
        except Exception:
            log.exception("guardrail %s could not be evaluated", name)
            return Judgement(_no(name, "We could not check that this change was safe."), ran)
        if said is None:
            continue
        if said.verdict is Verdict.REQUIRES_APPROVAL:
            # Remembered, not returned: the rest of the checks still have to
            # pass before anybody is offered the chance to say yes.
            held_for_approval = said
            continue
        return Judgement(said, ran)

    if held_for_approval is not None:
        return Judgement(held_for_approval, ran)
    return Judgement(Ruling(Verdict.APPROVED, "", "Within every limit set for this account."), ran)
