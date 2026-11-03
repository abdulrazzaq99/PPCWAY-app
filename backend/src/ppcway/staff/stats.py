"""What the platform looks like from the inside, counted rather than estimated.

Every figure here is a `SELECT count(...)` or a `SELECT sum(...)` over a table
this application owns. Nothing is sampled, cached or inferred, and nothing is
rolled up into a stored summary -- a counter that drifts from the rows it
counts is worse than no counter, because somebody will believe it.

**Each figure carries the window it was measured over.** "412 changes" means
nothing; "412 changes in the last 7 days" is a fact. The merchant-facing
screens already follow the owner's rule -- a sentence before a number -- and an
internal screen has the same obligation, because the person reading it is about
to make a decision from it.

**Zero and unknown are different, and the difference is kept.** No proposals
last night because the rules found nothing worth proposing is a healthy
platform. No proposals because the nightly job did not run is an incident. A
`Count` that cannot be established says so instead of returning 0.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.model.log import PromptLog
from ppcway.opt.models import OptimizationAction, Status
from ppcway.org.models import Membership, Organization

#: The windows the panel offers. Named rather than free-form: a screen that
#: lets somebody pick any window invites them to compare two figures measured
#: over different ones.
WINDOWS: Final[dict[str, int]] = {"today": 1, "7d": 7, "30d": 30, "90d": 90}

#: A sync that has not finished after this long is stuck rather than slow. The
#: structure sync runs every 15 minutes, so an hour is four missed turns.
STUCK_AFTER: Final = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class Count:
    """One number, what it counts, and the window it was measured over.

    `known=False` is not zero. A figure that could not be established says so,
    because "no proposals last night" and "we do not know whether the job ran"
    lead to opposite actions.
    """

    label: str
    value: int = 0
    window: str = ""
    known: bool = True
    #: The same figure one window earlier, where comparing is meaningful.
    before: int | None = None

    @property
    def words(self) -> str:
        """The figure as a sentence, which is how it is shown."""
        if not self.known:
            return f"We cannot tell how many {self.label.lower()} right now."
        over = f" in the last {self.window}" if self.window else ""
        return f"{self.value:,} {self.label.lower()}{over}."

    @property
    def change(self) -> int | None:
        """How much it moved, or None where there is nothing to compare."""
        if self.before is None or not self.known:
            return None
        return self.value - self.before


@dataclass(frozen=True, slots=True)
class Money:
    """A sum of money, with its currency, because a bare number is a trap."""

    label: str
    amount: float = 0.0
    currency: str = "USD"
    window: str = ""

    @property
    def words(self) -> str:
        over = f" in the last {self.window}" if self.window else ""
        return f"{self.amount:,.2f} {self.currency} {self.label.lower()}{over}."


@dataclass(frozen=True, slots=True)
class Platform:
    """The whole internal picture, in one object a screen can render."""

    at: datetime
    window: str
    merchants: Count
    connected: Count
    people: Count
    proposed: Count
    waiting: Count
    applied: Count
    reverted: Count
    refused: Count
    model_calls: Count
    model_tokens: Count
    model_trouble: Count
    syncs_failed: Count
    syncs_stuck: Count
    #: Set where something needs attention, in words, worst first. Empty is the
    #: honest healthy state and the screen should say so rather than show
    #: nothing.
    trouble: tuple[str, ...] = field(default_factory=tuple)

    @property
    def healthy(self) -> bool:
        return not self.trouble


def _since(window: str, now: datetime) -> datetime:
    return now - timedelta(days=WINDOWS.get(window, 7))


def _count(session: Session, statement: Select[Any]) -> int:
    return int(session.scalar(statement) or 0)


def _rows(model: Any, *where: Any) -> Select[Any]:
    return select(func.count()).select_from(model).where(*where)


def platform(session: Session, *, window: str = "7d", now: datetime | None = None) -> Platform:
    """Count everything the overview screen shows, in one pass per figure.

    One function rather than a dozen endpoints, because the screen shows them
    together and a reader comparing two figures measured seconds apart at
    least knows they were measured against the same window.
    """
    now = now or datetime.now(UTC)
    window = window if window in WINDOWS else "7d"
    since = _since(window, now)
    earlier = since - (now - since)

    merchants = Count(
        label="Businesses",
        value=_count(session, select(func.count()).select_from(Organization)),
    )
    connected = Count(
        label="Connected to Google Ads",
        value=_count(
            session,
            _rows(AdsConnection, AdsConnection.customer_id != ""),
        ),
    )
    people = Count(
        label="People", value=_count(session, select(func.count()).select_from(Membership))
    )

    def actions(*where: Any, start: datetime = since, end: datetime | None = None) -> int:
        bounds = [OptimizationAction.created_at >= start]
        if end is not None:
            bounds.append(OptimizationAction.created_at < end)
        return _count(session, _rows(OptimizationAction, *where, *bounds))

    proposed = Count(
        label="Changes proposed",
        value=actions(),
        window=window,
        before=actions(start=earlier, end=since),
    )
    waiting = Count(
        label="Waiting for a merchant",
        # No window: "waiting" is a state now, not an event in a period, and
        # bounding it by date would hide the oldest ones -- which are the only
        # ones that matter.
        value=_count(
            session,
            _rows(
                OptimizationAction,
                OptimizationAction.status.in_(
                    (Status.AWAITING_APPROVAL.value, Status.PROPOSED.value)
                ),
            ),
        ),
    )
    applied = Count(
        label="Changes applied",
        value=actions(OptimizationAction.status == Status.APPLIED.value),
        window=window,
    )
    reverted = Count(
        label="Changes put back",
        value=actions(OptimizationAction.status == Status.REVERTED.value),
        window=window,
    )
    refused = Count(
        label="Refused by a guardrail",
        value=actions(OptimizationAction.status == Status.REJECTED.value),
        window=window,
    )

    model_calls = Count(
        label="Model calls",
        value=_count(session, _rows(PromptLog, PromptLog.created_at >= since)),
        window=window,
    )
    model_tokens = Count(
        label="Tokens used",
        value=int(
            session.scalar(
                select(
                    func.coalesce(func.sum(PromptLog.input_tokens + PromptLog.output_tokens), 0)
                ).where(PromptLog.created_at >= since)
            )
            or 0
        ),
        window=window,
    )
    model_trouble = Count(
        label="Model calls that failed",
        value=_count(
            session,
            _rows(PromptLog, PromptLog.created_at >= since, PromptLog.trouble != ""),
        ),
        window=window,
    )

    syncs_failed = Count(
        label="Syncs that failed",
        value=_count(
            session,
            _rows(SyncRun, SyncRun.started_at >= since, SyncRun.status == "failed"),
        ),
        window=window,
    )
    syncs_stuck = Count(
        label="Syncs still running",
        value=_count(
            session,
            _rows(
                SyncRun,
                SyncRun.status == "running",
                SyncRun.started_at < now - STUCK_AFTER,
            ),
        ),
    )

    return Platform(
        at=now,
        window=window,
        merchants=merchants,
        connected=connected,
        people=people,
        proposed=proposed,
        waiting=waiting,
        applied=applied,
        reverted=reverted,
        refused=refused,
        model_calls=model_calls,
        model_tokens=model_tokens,
        model_trouble=model_trouble,
        syncs_failed=syncs_failed,
        syncs_stuck=syncs_stuck,
        trouble=_what_needs_attention(
            syncs_stuck=syncs_stuck,
            syncs_failed=syncs_failed,
            model_trouble=model_trouble,
            waiting=waiting,
            connected=connected,
            merchants=merchants,
        ),
    )


def _what_needs_attention(
    *,
    syncs_stuck: Count,
    syncs_failed: Count,
    model_trouble: Count,
    waiting: Count,
    connected: Count,
    merchants: Count,
) -> tuple[str, ...]:
    """Everything wrong, in words, worst first.

    Worst first because a screen shows the top of a list and a person reads the
    top of a screen. Sentences rather than codes: the reader is deciding
    whether to get out of bed.
    """
    said: list[str] = []
    if syncs_stuck.value:
        said.append(
            f"{syncs_stuck.value} sync{'s' if syncs_stuck.value > 1 else ''} started over an"
            f" hour ago and never finished. Those accounts are working from old figures."
        )
    if syncs_failed.value:
        said.append(
            f"{syncs_failed.value} sync{'s' if syncs_failed.value > 1 else ''} failed in the"
            f" last {syncs_failed.window}."
        )
    if model_trouble.value:
        said.append(
            f"{model_trouble.value} model call{'s' if model_trouble.value > 1 else ''} came"
            f" back with nothing in the last {model_trouble.window}."
        )
    if waiting.value >= 50:
        said.append(
            f"{waiting.value} proposed changes are waiting for a merchant to answer. Some of"
            f" them are probably stale."
        )
    if merchants.value and not connected.value:
        said.append(
            "No business has a connected Google Ads account, so nothing can be read or"
            " proposed for anybody."
        )
    return tuple(said)


@dataclass(frozen=True, slots=True)
class MerchantRow:
    """One business, as the list shows it."""

    organization_id: uuid.UUID
    name: str
    customer_id: str
    account_status: str
    people: int
    waiting: int
    applied: int
    last_sync: datetime | None
    connected: bool

    @property
    def trouble(self) -> str:
        """One sentence where this business needs looking at, else empty."""
        if not self.connected:
            return "No Google Ads account connected."
        if self.account_status and self.account_status not in ("ENABLED", ""):
            return f"Google says this account is {self.account_status.lower()}."
        if self.last_sync is None:
            return "Never synced."
        return ""


def merchants(session: Session, *, look_for: str = "", most: int = 100) -> list[MerchantRow]:
    """Every business, newest first, with enough to decide who needs attention.

    Counted per row rather than in one grouped query, which is slower and
    deliberate: the grouped version needs outer joins across four tables and
    the first reader to change it will get a count wrong. At a hundred rows the
    difference is not worth the bug.
    """
    wanted = select(Organization).order_by(Organization.created_at.desc()).limit(most)
    if look_for.strip():
        like = f"%{look_for.strip().lower()}%"
        wanted = wanted.where(func.lower(Organization.name).like(like))

    out: list[MerchantRow] = []
    for place in session.scalars(wanted):
        connection = session.scalars(
            select(AdsConnection).where(AdsConnection.organization_id == place.id).limit(1)
        ).first()
        customer_id = (connection.customer_id if connection else "") or ""
        last = None
        if customer_id:
            last = session.scalar(
                select(func.max(SyncRun.finished_at)).where(SyncRun.customer_id == customer_id)
            )
        out.append(
            MerchantRow(
                organization_id=place.id,
                name=place.name or "(unnamed)",
                customer_id=customer_id,
                account_status=(getattr(connection, "account_status", "") or "")
                if connection
                else "",
                people=_count(session, _rows(Membership, Membership.organization_id == place.id)),
                waiting=_count(
                    session,
                    _rows(
                        OptimizationAction,
                        OptimizationAction.organization_id == place.id,
                        OptimizationAction.status.in_(
                            (Status.AWAITING_APPROVAL.value, Status.PROPOSED.value)
                        ),
                    ),
                ),
                applied=_count(
                    session,
                    _rows(
                        OptimizationAction,
                        OptimizationAction.organization_id == place.id,
                        OptimizationAction.status == Status.APPLIED.value,
                    ),
                ),
                last_sync=last,
                connected=bool(customer_id),
            )
        )
    return out
