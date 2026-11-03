"""What was asked, what was answered, and what it cost to find out.

The brief: *transcripts and tool calls, 12 months, deleted with the account.*
Both halves matter and the second is the one that gets forgotten.

**Why the tool calls and not only the words.** A merchant disputing an answer
is disputing a figure, and the figure came from a lookup. Keeping the reply
without keeping which tools ran and what they returned leaves the one question
nobody can answer: was the model wrong, or was the mirror? So each turn records
the tools it used, the figures they returned, and whether the answer survived
the number check or fell back to our own words.

**Why the cost.** The brief wants an app-enforced AI budget ceiling with alerts
at half and four fifths. A ceiling needs a running total, and a running total
needs every call counted -- including the ones that failed, because a failed
call is billed. Counted here rather than in the model service, because the
service does not know which business it is answering for and should not.

**Deleted with the account, by a foreign key rather than by a job.** A
retention promise kept by a nightly sweep is a promise that breaks the first
time the sweep is paused. The twelve-month window does need a sweep, and
`forget_old` is it; the account deletion does not.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    delete,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from ppcway.chat.plans import cost_of, plan_for
from ppcway.db.base import Base
from ppcway.org.models import Organization

log = logging.getLogger(__name__)

#: The brief's figure. Twelve months of transcripts, then gone.
KEEP_MONTHS: Final = 12
KEEP_DAYS: Final = 365


def _json() -> Mapped[dict[str, Any] | None]:
    return mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)


class Conversation(Base):
    """One session with Otto. A conversation, not a question."""

    __tablename__ = "chat_conversation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), index=True
    )
    #: Who was talking. Null once the person's account is gone but the business
    #: remains, which happens when staff leave.
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"), nullable=True
    )
    #: The Google Ads account the conversation was about.
    customer_id: Mapped[str] = mapped_column(String(20), default="", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    #: The first thing they asked, shortened, so a list of conversations reads
    #: without opening each one.
    about: Mapped[str] = mapped_column(String(200), default="")


class Turn(Base):
    """One question and its answer, with everything it took to get there."""

    __tablename__ = "chat_turn"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_conversation.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), index=True
    )
    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    #: "model", "rewrite", "template" or "refused". Which of those it was is
    #: the difference between Otto's words and ours, and a dispute turns on it.
    answer_from: Mapped[str] = mapped_column(String(20), default="")

    #: Which tools ran, and the figures they returned. Without these, a dispute
    #: about a number has no answer: was the model wrong, or the mirror?
    tools_used: Mapped[dict[str, Any] | None] = _json()
    figures: Mapped[dict[str, Any] | None] = _json()
    #: Numbers the model used that no tool returned, where that happened.
    invented: Mapped[dict[str, Any] | None] = _json()

    model: Mapped[str] = mapped_column(String(60), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    #: An estimate, in US dollars. Anthropic's published rates, not Google's
    #: partner rates -- see `plans.PER_MILLION`. Stored rather than computed on
    #: read, so a price change does not rewrite history.
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    took_ms: Mapped[int] = mapped_column(Integer, default=0)


@dataclass(frozen=True, slots=True)
class Spend:
    """What a business has spent on model calls this month, and whether to say."""

    used_usd: float
    ceiling_usd: float
    questions: int
    questions_allowed: int
    #: True the first time a month crosses half, and again at four fifths.
    crossed: float | None = None

    @property
    def share_used(self) -> float:
        return round(self.used_usd / self.ceiling_usd, 4) if self.ceiling_usd else 1.0

    @property
    def spent_out(self) -> bool:
        return self.used_usd >= self.ceiling_usd

    @property
    def out_of_questions(self) -> bool:
        return self.questions >= self.questions_allowed

    @property
    def may_ask(self) -> bool:
        return not self.spent_out and not self.out_of_questions

    @property
    def because(self) -> str:
        if self.out_of_questions:
            return (
                f"This plan includes {self.questions_allowed:,} questions a month and"
                f" they have all been used. It starts again next month, or a larger"
                f" plan includes more."
            )
        if self.spent_out:
            # Deliberately not "you have spent too much": the merchant has
            # spent nothing. This is PPCWay's own ceiling.
            return (
                "Otto has reached the limit of what PPCWay spends on this account's"
                " questions this month. It starts again next month, and nothing about"
                " your ads has changed."
            )
        return ""


def this_month(
    session: Session, organization_id: uuid.UUID, *, now: datetime | None = None
) -> Spend:
    """What this business has used this month, against both ceilings."""
    at = now or datetime.now(UTC)
    since = datetime(at.year, at.month, 1, tzinfo=UTC)
    used, questions = session.execute(
        select(func.coalesce(func.sum(Turn.cost_usd), 0.0), func.count(Turn.id)).where(
            Turn.organization_id == organization_id,
            Turn.asked_at >= since,
        )
    ).one()
    place = session.get(Organization, organization_id)
    plan = plan_for(place.plan if place else "")
    return Spend(
        used_usd=round(float(used or 0.0), 6),
        ceiling_usd=plan.spend_ceiling_usd,
        questions=int(questions or 0),
        questions_allowed=plan.questions_a_month,
    )


def open_conversation(
    session: Session,
    *,
    organization_id: uuid.UUID,
    account_id: uuid.UUID | None,
    customer_id: str,
    about: str,
    now: datetime | None = None,
) -> Conversation:
    """Start a session. Committed, so a crash mid-answer still leaves the question."""
    held = Conversation(
        organization_id=organization_id,
        account_id=account_id,
        customer_id=customer_id,
        about=(about or "")[:200],
        started_at=now or datetime.now(UTC),
    )
    session.add(held)
    session.commit()
    return held


def record_turn(
    session: Session,
    *,
    conversation_id: uuid.UUID,
    organization_id: uuid.UUID,
    question: str,
    answer: str,
    answer_from: str,
    tools_used: list[str],
    figure_ids: list[str],
    invented: list[float],
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    took_ms: int = 0,
    now: datetime | None = None,
) -> Turn:
    """Write one turn down, whatever became of it.

    A refused turn is recorded too. A transcript of the answers that worked is
    not a transcript, and the turns that failed are the ones somebody asks
    about.
    """
    turn = Turn(
        conversation_id=conversation_id,
        organization_id=organization_id,
        asked_at=now or datetime.now(UTC),
        question=question,
        answer=answer,
        answer_from=answer_from,
        tools_used={"tools": list(tools_used)},
        figures={"ids": list(figure_ids)},
        invented={"numbers": list(invented)} if invented else None,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        cost_usd=cost_of(
            model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached=cached_tokens,
        ),
        took_ms=took_ms,
    )
    session.add(turn)
    session.commit()
    return turn


def crossed_a_line(before: Spend, after: Spend) -> float | None:
    """Which threshold this turn crossed, if any. For the caller to alert on.

    Compared before and after rather than read from a stored flag, so the alert
    fires once per crossing without a counter to keep in step. The brief asks
    for half and four fifths.
    """
    from ppcway.chat.plans import WARN_AT

    for line in WARN_AT:
        if before.share_used < line <= after.share_used:
            return line
    return None


def forget_old(session: Session, *, now: datetime | None = None, days: int = KEEP_DAYS) -> int:
    """Delete transcripts past the retention window. Returns how many turns went.

    Conversations whose turns have all gone are deleted too: an empty
    conversation row is a record that somebody asked something, with no way to
    know what, which is worse than no record.
    """
    at = now or datetime.now(UTC)
    cutoff = at - timedelta(days=days)
    gone = session.execute(delete(Turn).where(Turn.asked_at < cutoff))
    how_many = int(getattr(gone, "rowcount", 0) or 0)
    empty = session.scalars(
        select(Conversation.id).where(
            Conversation.started_at < cutoff,
            ~select(Turn.id).where(Turn.conversation_id == Conversation.id).exists(),
        )
    ).all()
    if empty:
        session.execute(delete(Conversation).where(Conversation.id.in_(empty)))
    if how_many or empty:
        log.info("forgot %d chat turns and %d conversations", how_many, len(empty))
    return how_many
