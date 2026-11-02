"""The optimization action log, and the limits that authorised each entry.

Blueprint §8.4 calls this the audit spine of the platform, and it is what makes
"immutable, versioned and reversible" real rather than a promise. The shape of
it follows from six properties, each of which rules something out:

- **append-only** — no update except the one move from pending to applied,
  failed or rejected. A log you can edit is not a log.
- **written before acting** — the row exists, with `before` captured, before
  the call to Google. A row written afterwards is missing exactly when the
  crash happened.
- **reversible** — `before` and `after` are kept whole, because an undo has to
  reconstruct the opposite mutation months later.
- **attributable** — which rule, which version of it, which limits were in
  force, which autonomy level, which run. "Why did this happen in March?" is
  a question a merchant is entitled to an answer to.
- **explainable** — the machine payload and a sentence a person can read, kept
  side by side, because the activity feed and the retry need different things.
- **queryable and retained** — indexed by merchant, account, kind and time.

Undo is a first-class action with its own row, linked to the one it reverses,
and it goes through the guardrails like anything else. An undo that leaves no
trace breaks the property the log exists to provide.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)


def _json() -> Mapped[dict[str, Any] | None]:
    return mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)


class Autonomy(str, Enum):
    """How far the platform may go without asking. Blueprint §8.3.

    Enforced in the guardrail layer rather than the interface, so that no code
    path can act above the level the merchant chose.
    """

    #: Detect and notify. No mutations at all except ones the merchant started.
    ALERTS_ONLY = "alerts_only"
    #: Propose and hold. Applied only on an explicit yes, and it expires.
    APPROVE_FIRST = "approve_first"
    #: Apply within the guardrails without asking per change. Phase 2, and only
    #: with a separate recorded consent naming the change classes and limits.
    FULL_AUTO = "full_auto"


class Status(str, Enum):
    """Where a proposed change has got to. The client's brief names all eight.

    Eight rather than four, and the four extra are not bookkeeping. "Awaiting
    approval" and "proposed" are different states -- one is waiting on a
    person, the other on a guardrail -- and a merchant asking why nothing
    happened is owed the difference. "Expired" is not "rejected": nobody said
    no, the offer simply went stale, and a report that counted those together
    would make the merchant look as though they had refused things they never
    saw. "Reverted" is the state the undo story depends on. "Failed" is Google
    refusing, which is nobody's decision at all.
    """

    #: Written, and the guardrails have not ruled yet.
    PROPOSED = "proposed"
    #: The guardrails allowed it, and a person has to say yes.
    AWAITING_APPROVAL = "awaiting_approval"
    #: Somebody said yes, or the account is in full auto. Not yet sent.
    APPROVED = "approved"
    #: Google accepted it.
    APPLIED = "applied"
    #: A guardrail refused it, or a person did.
    REJECTED = "rejected"
    #: Nobody answered in time. Not a refusal.
    EXPIRED = "expired"
    #: It was applied and then put back.
    REVERTED = "reverted"
    #: It was sent and Google would not have it.
    FAILED = "failed"

    @property
    def settled(self) -> bool:
        """Whether nothing more will happen to this row by itself."""
        return self in TERMINAL


#: The states nothing moves out of. `APPLIED` is not among them: an applied
#: change can still be reverted, which is the property the log exists for.
TERMINAL: frozenset[Status] = frozenset(
    {Status.REJECTED, Status.EXPIRED, Status.REVERTED, Status.FAILED}
)

#: Every move a row may make, as the trigger in the database also enforces it.
#: Kept here as data so the two can be compared by a test rather than by
#: somebody reading both and hoping.
MOVES: dict[Status, frozenset[Status]] = {
    Status.PROPOSED: frozenset(
        {Status.AWAITING_APPROVAL, Status.APPROVED, Status.REJECTED, Status.EXPIRED}
    ),
    Status.AWAITING_APPROVAL: frozenset({Status.APPROVED, Status.REJECTED, Status.EXPIRED}),
    Status.APPROVED: frozenset({Status.APPLIED, Status.FAILED, Status.REJECTED}),
    Status.APPLIED: frozenset({Status.REVERTED}),
    Status.REJECTED: frozenset(),
    Status.EXPIRED: frozenset(),
    Status.REVERTED: frozenset(),
    Status.FAILED: frozenset(),
}


#: The states that use up a merchant's ten changes a week. A proposal still
#: waiting counts: it is already a card somebody has been asked to read, and
#: offering an eleventh while ten sit unanswered is how an inbox is abandoned.
#: An applied change that was later reverted counts too -- it reached the
#: account, and the merchant spent a decision on it.
#:
#: The three that do not count never happened. A guardrail's refusal, an offer
#: nobody answered, and a change Google would not have are all things the
#: merchant did not get; counting them would spend somebody's allowance of real
#: changes on a run of failures, which is exactly backwards.
COUNTS_TOWARD_CAP: frozenset[Status] = frozenset(
    {
        Status.PROPOSED,
        Status.AWAITING_APPROVAL,
        Status.APPROVED,
        Status.APPLIED,
        Status.REVERTED,
    }
)


class ProposedBy(str, Enum):
    """Who or what put this forward. The brief's four."""

    #: A rule, in the nightly pass.
    RULE = "rule"
    #: Otto, from something a merchant asked in the chat.
    CHAT = "chat"
    #: A PPCWay expert.
    EXPERT = "expert"
    #: The merchant themselves.
    OWNER = "owner"


class Risk(str, Enum):
    """How much a change could cost if it is wrong. The brief's three levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


#: How long a proposal waits for a yes before it is too old to trust. §8.3,
#: and the brief: "Expires at | Created + 7 days".
APPROVAL_EXPIRES_DAYS = 7


class GuardrailConfig(Base):
    """The limits in force, versioned, so an old action can be explained.

    Blueprint §5.5: every action records the version that authorised it, so
    "which limits were in force when this change was made?" is answerable
    months later — which is what a merchant dispute actually requires.
    """

    __tablename__ = "guardrail_config"
    #: A version is never reused, because an action points back at one to say
    #: which limits authorised it.
    __table_args__ = (UniqueConstraint("organization_id", "version", name="one_version_once"),)

    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    #: Climbs by one each time the limits change. Never reused.
    version: Mapped[int] = mapped_column(Integer, default=1, index=True)

    autonomy: Mapped[str] = mapped_column(String(20), default=Autonomy.APPROVE_FIRST.value)

    #: Hard ceilings. Nothing may propose past these whatever the arithmetic says.
    max_daily_budget: Mapped[float] = mapped_column(Float, default=0.0)
    max_cpa: Mapped[float] = mapped_column(Float, default=0.0)
    min_bid: Mapped[float] = mapped_column(Float, default=0.0)
    max_bid: Mapped[float] = mapped_column(Float, default=0.0)

    #: How far one change may move a number, and how far a day's changes may
    #: move it in total. The per-change cap alone is not enough: twenty percent
    #: a day compounds into a thirty-eight times budget increase in a year.
    max_change_pct: Mapped[float] = mapped_column(Float, default=25.0)
    max_daily_change_pct: Mapped[float] = mapped_column(Float, default=50.0)

    #: How often one thing may be touched, and how busy a day may get.
    max_changes_per_entity_day: Mapped[int] = mapped_column(Integer, default=2)
    max_changes_per_day: Mapped[int] = mapped_column(Integer, default=20)

    #: The share of live things one job may pause. This is what turns a metrics
    #: pipeline returning zeros into a small visible anomaly rather than an
    #: account-wide outage.
    max_pause_pct: Mapped[float] = mapped_column(Float, default=10.0)

    #: How old the numbers behind a decision may be. A spend decision made on
    #: stale data is worse than no decision.
    staleness_minutes: Mapped[int] = mapped_column(Integer, default=180)

    #: Campaigns, budgets or keywords the merchant has pinned as hands-off,
    #: by resource name. Full-auto with exclusions is often the difference
    #: between a cautious merchant adopting automation and refusing it.
    hands_off: Mapped[dict[str, Any] | None] = _json()

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("account.id"), nullable=True)


class OptimizationAction(Base):
    """One proposed change, and what became of it."""

    __tablename__ = "optimization_action"
    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    #: The Google Ads account this touches. Checked against the merchant's own
    #: before anything is applied, which is the defence against spending one
    #: merchant's money on another's campaign.
    customer_id: Mapped[str] = mapped_column(String(20), index=True, default="")

    #: What sort of change: add_negative_keyword, decrease_daily_budget,
    #: pause_ad, and so on.
    kind: Mapped[str] = mapped_column(String(40), index=True)
    #: What it acts on, as Google names it, plus words for a person.
    target_kind: Mapped[str] = mapped_column(String(20), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    target_label: Mapped[str] = mapped_column(String(255), default="")

    #: Kept whole, because an undo months from now has to build the opposite
    #: of this without guessing what the world looked like.
    before: Mapped[dict[str, Any] | None] = _json()
    after: Mapped[dict[str, Any] | None] = _json()

    #: One sentence the merchant reads, and the payload the gateway sends.
    reason: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any] | None] = _json()
    #: The numbers that justified it, as they stood when it was decided:
    #: figure ids with their as-of times, which is the brief's own definition
    #: of evidence.
    evidence: Mapped[dict[str, Any] | None] = _json()
    #: What we expected it to be worth, in money a month, and in words. Kept
    #: because "was Otto right?" is a question about what was predicted, and a
    #: prediction nobody wrote down is not one.
    expected_impact: Mapped[dict[str, Any] | None] = _json()
    #: How this gets put back, in the words the merchant was shown. Not derived
    #: from the kind at undo time: what somebody was promised is what they are
    #: owed, even if we would phrase it differently now.
    undo_plan: Mapped[str] = mapped_column(Text, default="")
    #: The window the figures covered. An action explained months later needs
    #: to say which days it was looking at.
    window_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    #: Which rule, which version of it, which limits, which level, which run.
    rule_id: Mapped[str] = mapped_column(String(60), default="")
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    guardrail_config_version: Mapped[int] = mapped_column(Integer, default=0)
    autonomy: Mapped[str] = mapped_column(String(20), default="")
    job_run: Mapped[str] = mapped_column(String(64), default="", index=True)

    #: How it is meant to reach the account: applied and reported, one tap from
    #: the owner, or an expert's sign-off first.
    route: Mapped[str] = mapped_column(String(20), default="owner")
    #: How much this could cost if it is wrong: low, medium or high. Recorded
    #: rather than looked up from the rule, because a rule's risk can be
    #: changed and this row has to keep saying what was true when it was
    #: written.
    risk: Mapped[str] = mapped_column(String(10), default=Risk.MEDIUM.value, index=True)
    #: Who put this forward: a rule, the chat, an expert, or the owner. The
    #: brief's own column, and the one that answers "did a person ask for
    #: this?" without inferring it from which fields are filled in.
    proposed_by: Mapped[str] = mapped_column(String(10), default=ProposedBy.RULE.value, index=True)
    status: Mapped[str] = mapped_column(String(20), default=Status.PROPOSED.value, index=True)
    #: Which guardrail decided, and what it said, in plain words.
    decided_by: Mapped[str] = mapped_column(String(40), default="")
    decided_because: Mapped[str] = mapped_column(Text, default="")

    #: Derived from this row's id, so a retry of the same action cannot apply
    #: it twice. Blueprint §5.6.
    idempotency_key: Mapped[str] = mapped_column(String(80), default="", index=True)

    #: An undo is an action in its own right, pointing at what it reverses.
    undo_of: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("optimization_action.id"), nullable=True, index=True
    )
    #: True when this change may still be put back. Structure can be reverted;
    #: money already spent cannot, and neither can Google's learning state.
    reversible: Mapped[bool] = mapped_column(Boolean, default=True)

    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("account.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    #: When this stops being on offer. Created plus seven days, written at
    #: insert rather than worked out on read, so a row that was allowed to
    #: expire says when it was due rather than when somebody asked.
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def expired_by(self) -> bool:
        """Whether this is past its date. Does not change the status: a row
        moves between states by somebody writing the move down, never by the
        clock being read, or two readers would disagree about history."""
        return self.expires_at is not None and self.status in {
            Status.PROPOSED.value,
            Status.AWAITING_APPROVAL.value,
        }
