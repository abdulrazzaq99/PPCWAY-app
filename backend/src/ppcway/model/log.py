"""Every question put to a model, and what came back, with the people removed.

The client's brief asks for a redacted prompt log kept thirty days. Anthropic's
own guidance on Vertex asks for the same thing for a different reason -- so that
misuse can be found after the fact -- and the two wants are the same table.

Three properties, each of which rules something out:

- **Written whatever happened.** A row for a refusal, a timeout and a 500, not
  only for a good answer. A log of successes answers no question worth asking.
- **Carries its provenance.** Which model, which version of the prompt, which
  job. Blueprint §7.6: a live ad has to trace back to the exact prompt and
  model that wrote it, and the answer has to survive the prompt being fixed --
  which is the only way to find the merchants a bad prompt reached.
- **Forgets.** Thirty days, enforced by a job rather than by intention. A
  retention promise with no delete behind it is the kind of thing that is
  discovered during a privacy review.

The text is redacted before it is written, never on the way out: see
`ppcway.model.redact` for what that does and does not cover.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Final

from sqlalchemy import CursorResult, DateTime, Integer, String, Text, Uuid, delete, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from ppcway.db.base import Base
from ppcway.model.redact import redacted

#: How long a prompt is kept. The brief's figure, and Anthropic's own
#: recommendation for Vertex request logging.
KEEP_DAYS: Final = 30


class PromptLog(Base):
    """One call to a model.

    Not tied to an organisation by a foreign key: an internal job may have no
    organisation, and a row here must survive the account it was about being
    deleted -- the misuse question is asked of the log after the fact. The id
    is kept as a plain column for the same reason.
    """

    __tablename__ = "model_prompt_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: Which business it was about, where there was one. No foreign key: see above.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True, index=True)
    #: The Google Ads account, where there was one, as Google writes it.
    customer_id: Mapped[str] = mapped_column(String(20), default="", index=True)

    #: The job asked for, from `ppcway.model.jobs.Job`.
    job: Mapped[str] = mapped_column(String(30), index=True)
    #: The model that answered, and the version of the words we sent it.
    model: Mapped[str] = mapped_column(String(60))
    prompt_version: Mapped[str] = mapped_column(String(30))

    #: Redacted on the way in. See the module docstring.
    system_text: Mapped[str] = mapped_column(Text, default="")
    input_text: Mapped[str] = mapped_column(Text, default="")
    output_text: Mapped[str] = mapped_column(Text, default="")

    #: Why it stopped: end_turn, max_tokens, refusal, tool_use. A refusal is
    #: an ordinary outcome on these models and has to be legible here.
    stop_reason: Mapped[str] = mapped_column(String(30), default="")
    #: What Model Armor made of the input, where it was asked: "clean",
    #: "blocked", or "not_screened" when it was not asked at all.
    armor: Mapped[str] = mapped_column(String(20), default="not_screened")

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    #: How much of the input was served from cache. Zero across a run of
    #: requests that should be hitting it is the signal that something in the
    #: prefix is changing per request.
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    took_ms: Mapped[int] = mapped_column(Integer, default=0)

    #: Set when the call did not return an answer, in words a log reader can act
    #: on. The row exists either way.
    trouble: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


def record(
    session: Session,
    *,
    job: str,
    model: str,
    prompt_version: str,
    system: str = "",
    asked: str = "",
    answered: str = "",
    organization_id: uuid.UUID | None = None,
    customer_id: str = "",
    stop_reason: str = "",
    armor: str = "not_screened",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    took_ms: int = 0,
    trouble: str = "",
) -> PromptLog:
    """Write one row, redacting the three text fields on the way in."""
    row = PromptLog(
        organization_id=organization_id,
        customer_id=customer_id,
        job=job,
        model=model,
        prompt_version=prompt_version,
        system_text=redacted(system),
        input_text=redacted(asked),
        output_text=redacted(answered),
        stop_reason=stop_reason,
        armor=armor,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        took_ms=took_ms,
        trouble=trouble,
    )
    session.add(row)
    return row


def forget_old(session: Session, *, now: datetime | None = None, days: int = KEEP_DAYS) -> int:
    """Delete everything older than the retention window. Returns how many.

    Takes `now` rather than reading the clock, so the boundary is testable and
    so a backfill can be run against a stated date.
    """
    at = now or datetime.now(UTC)
    cutoff = at - timedelta(days=days)
    done = session.execute(delete(PromptLog).where(PromptLog.created_at < cutoff))
    # A DELETE always returns a CursorResult; the generic signature of
    # `Session.execute` does not say so, and `rowcount` is the only thing worth
    # knowing about the result.
    return getattr(done, "rowcount", 0) or 0 if isinstance(done, CursorResult) else 0
