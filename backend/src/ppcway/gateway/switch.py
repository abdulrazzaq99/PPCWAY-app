"""Whether anything may be written to Google at all, and who can stop it.

Three separate answers, and all three have to be yes. They are separate on
purpose: each one is held by a different person for a different reason, and
collapsing them into one flag would mean the engineer's deploy switch and the
merchant's own choice were the same lever.

1. **The write gate.** Off unless somebody turns it on. PPCWay does not yet
   have Google Standard access, the client's brief puts a gate on the write
   path closing on 6 December, and the Terms and Google filings have to be
   updated before anything is applied unattended. So nothing writes until
   somebody sets it, and the default in code is the safe one rather than the
   convenient one.

   Since 5 November it is a switch in the internal panel as well as a
   setting, at the owner's request: a redeploy for every on and off was the
   wrong cost for the one control that gets flipped while testing. The
   latest time somebody switched it in the panel wins; until anybody has, the
   deployment's `ADS_WRITES_ENABLED` stands. Principal access only, a reason
   to switch it on, and every flip kept as a row -- see `WriteGate`.

2. **The global kill switch.** PPCWay staff can stop every write for every
   account, now, without a deploy. The brief asks for it, and the reason to
   have it is the morning a rule turns out to be wrong across three hundred
   accounts: a deploy takes minutes and a row takes seconds.

3. **The per-account kill switch.** An expert or the owner can stop writes for
   one business without stopping anybody else's.

**All three are read at the moment of writing, never cached.** A kill switch
that was read when the job started is a kill switch that does not work during
the job, which is the only time anybody reaches for one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from ppcway.db.base import Base


class WritesStopped(RuntimeError):
    """Nothing may be written. Carries which of the three said so, in words."""


class KillSwitch(Base):
    """A standing instruction to write nothing, for one account or for all.

    A row rather than a setting, so stopping writes needs no deploy, and
    append-shaped rather than a boolean somebody flips: who stopped it, when,
    and why are all part of the answer to "why did nothing happen last
    Tuesday", and a flag that was turned on and off again answers none of it.
    """

    __tablename__ = "ads_kill_switch"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: The Google Ads account this stops, or empty for every account there is.
    customer_id: Mapped[str] = mapped_column(String(20), default="", index=True)
    #: Why, in words somebody will read in a hurry.
    because: Mapped[str] = mapped_column(Text, default="")
    #: Who pulled it. Null for a switch set by a job rather than a person.
    pulled_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    pulled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    #: Set when somebody lets writes resume. The row stays, because the fact
    #: that writes were once stopped is part of the account's history.
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    #: True for a switch PPCWay staff set, which an owner may not release.
    ours: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def global_(self) -> bool:
        return not self.customer_id


class WriteGate(Base):
    """One time somebody switched writes to Google Ads on or off in the panel.

    Rows, never changed: the latest one is the gate. "Who turned writes on
    last Tuesday, and why?" is the first question after anything goes wrong,
    and a setting somebody flipped and flipped back answers none of it. The
    database refuses an update or a delete, so the history cannot be tidied.
    """

    __tablename__ = "ads_write_gate"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    is_open: Mapped[bool] = mapped_column(Boolean)
    #: Why, in words. Required to open it; whoever reads the log later is told.
    because: Mapped[str] = mapped_column(Text, default="")
    set_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    #: Written by the code rather than the database clock, to the microsecond,
    #: so two flips in one second still have an order.
    set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


@dataclass(frozen=True, slots=True)
class Gate:
    """Whether the gate is open, and where that answer came from."""

    is_open: bool
    #: "panel" when somebody switched it there, "deployment" when nobody has
    #: and `ADS_WRITES_ENABLED` stands.
    source: str
    because: str = ""
    set_by: uuid.UUID | None = None
    set_at: datetime | None = None


def gate(session: Session, *, default: bool) -> Gate:
    """The write gate, read now. `default` is the deployment's own setting."""
    latest = session.scalars(
        select(WriteGate).order_by(WriteGate.set_at.desc(), WriteGate.id.desc()).limit(1)
    ).first()
    if latest is None:
        return Gate(is_open=default, source="deployment")
    return Gate(
        is_open=bool(latest.is_open),
        source="panel",
        because=latest.because or "",
        set_by=latest.set_by,
        set_at=latest.set_at,
    )


def set_gate(
    session: Session,
    *,
    is_open: bool,
    because: str,
    set_by: uuid.UUID | None,
    now: datetime | None = None,
) -> WriteGate:
    """Open or shut the gate. Takes effect for the next change sent.

    Who may do this, and what they must say, is `staff.controls`' to check:
    this records the decision, it does not make it.
    """
    row = WriteGate(
        is_open=is_open, because=because, set_by=set_by, set_at=now or datetime.now(UTC)
    )
    session.add(row)
    session.commit()
    return row


@dataclass(frozen=True, slots=True)
class Standing:
    """Whether writes may happen, and what to say when they may not."""

    may_write: bool
    because: str = ""
    #: "gate", "global" or "account", so a screen can say which and a log can
    #: be grepped for the one that matters.
    stopped_by: str = ""


def may_write(session: Session, *, customer_id: str, gate_open: bool) -> Standing:
    """All three answers, read now. Never cached.

    `gate_open` is the write gate, passed in rather than read here so this
    function has no opinion about settings and can be tested without them.
    Callers read it with `gate`, at the moment of writing.
    """
    if not gate_open:
        return Standing(
            may_write=False,
            because=(
                "PPCWay is not writing to Google Ads yet. Changes are proposed and"
                " recorded; nothing is applied."
            ),
            stopped_by="gate",
        )

    live = session.scalars(
        select(KillSwitch).where(
            KillSwitch.released_at.is_(None),
            KillSwitch.customer_id.in_(("", customer_id)),
        )
    ).all()
    # The global one first, where both are set: it is the more serious answer,
    # and a screen saying "writes are stopped on your account" when they are
    # stopped everywhere would send a merchant to the wrong conversation.
    whole = next((s for s in live if s.global_), None)
    if whole is not None:
        return Standing(
            may_write=False,
            because=whole.because or "Writing to Google Ads is stopped for everybody.",
            stopped_by="global",
        )
    just_them = next((s for s in live if not s.global_), None)
    if just_them is not None:
        return Standing(
            may_write=False,
            because=just_them.because or "Writing to this account is stopped.",
            stopped_by="account",
        )
    return Standing(may_write=True)


def stop(
    session: Session,
    *,
    customer_id: str = "",
    because: str,
    pulled_by: uuid.UUID | None = None,
    ours: bool = False,
) -> KillSwitch:
    """Stop writes, for one account or for all of them. Takes effect at once.

    Idempotent: pulling a switch that is already pulled returns the one that
    is already there rather than stacking another, so releasing it once is
    enough and "it is still stopped" cannot be caused by a forgotten duplicate.
    """
    already = session.scalars(
        select(KillSwitch).where(
            KillSwitch.customer_id == customer_id,
            KillSwitch.released_at.is_(None),
        )
    ).first()
    if already is not None:
        return already
    switch = KillSwitch(customer_id=customer_id, because=because, pulled_by=pulled_by, ours=ours)
    session.add(switch)
    session.commit()
    return switch


def release(
    session: Session,
    *,
    customer_id: str = "",
    released_by: uuid.UUID | None = None,
    staff: bool = False,
    now: datetime | None = None,
) -> KillSwitch | None:
    """Let writes resume. Returns the switch released, or None if none was set.

    A switch PPCWay staff set cannot be released by a merchant. If it could,
    the one case it exists for -- we have found a problem and are stopping
    writes while we look -- would be a case the merchant could overrule.
    """
    at = now or datetime.now(UTC)
    switch = session.scalars(
        select(KillSwitch).where(
            KillSwitch.customer_id == customer_id,
            KillSwitch.released_at.is_(None),
        )
    ).first()
    if switch is None:
        return None
    if switch.ours and not staff:
        raise WritesStopped(
            "PPCWay has stopped writes on this account while we look into something."
            " Please talk to us rather than turning it back on."
        )
    switch.released_at = at
    switch.released_by = released_by
    session.commit()
    return switch
