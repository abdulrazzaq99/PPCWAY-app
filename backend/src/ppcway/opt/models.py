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
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
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
    """The one transition this log allows: pending, then an outcome."""

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    REJECTED = "rejected"


#: How long a proposal waits for a yes before it is too old to trust. §8.3.
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
    #: The numbers that justified it, as they stood when it was decided.
    evidence: Mapped[dict[str, Any] | None] = _json()

    #: Which rule, which version of it, which limits, which level, which run.
    rule_id: Mapped[str] = mapped_column(String(60), default="")
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    guardrail_config_version: Mapped[int] = mapped_column(Integer, default=0)
    autonomy: Mapped[str] = mapped_column(String(20), default="")
    job_run: Mapped[str] = mapped_column(String(64), default="", index=True)

    #: How it is meant to reach the account: applied and reported, one tap from
    #: the owner, or an expert's sign-off first.
    route: Mapped[str] = mapped_column(String(20), default="owner")
    status: Mapped[str] = mapped_column(String(20), default=Status.PENDING.value, index=True)
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
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
