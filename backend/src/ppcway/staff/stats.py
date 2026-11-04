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

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from ppcway.ads.mirror import SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.model.log import PromptLog
from ppcway.opt.models import OptimizationAction, Status
from ppcway.org.models import Membership, Organization

#: The windows the panel offers. Named rather than free-form: a screen that
#: lets somebody pick any window invites them to compare two figures measured
#: over different ones.
WINDOWS: Final[dict[str, int]] = {"today": 1, "7d": 7, "30d": 30, "90d": 90}

#: How each window reads inside a sentence. "In the last 7d" is a code, not
#: words, and "in the last today" was one substitution away from the screen.
SPANS: Final[dict[str, str]] = {
    "today": "in the last 24 hours",
    "7d": "in the last 7 days",
    "30d": "in the last 30 days",
    "90d": "in the last 90 days",
}


def over(window: str) -> str:
    """A window as words to end a sentence with, or nothing for no window."""
    if not window:
        return ""
    return SPANS.get(window, f"in the last {window}")


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
        """The figure as a sentence, which is how it is shown.

        Only the first letter is lowered, not the whole label. Lowering all of
        it turned "Connected to Google Ads" into "connected to google ads",
        which was on screen: a product name is a product name wherever it sits
        in a sentence.
        """
        label = self.label[:1].lower() + self.label[1:]
        if not self.known:
            return f"We cannot tell how many {label} right now."
        span = f" {over(self.window)}" if self.window else ""
        return f"{self.value:,} {label}{span}."

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
        span = f" {over(self.window)}" if self.window else ""
        return f"{self.amount:,.2f} {self.currency} {self.label.lower()}{span}."


@dataclass(frozen=True, slots=True)
class Point:
    """One period of the series: when it starts, and how many changes Otto
    proposed in it, by the state each of them is in now.

    By the state *now*, not the state on the day. A change proposed on Monday
    and applied on Wednesday counts as applied under Monday, so the chart reads
    as "what became of each day's proposals" -- which settles as the days age,
    and is the question somebody watching Otto is asking.
    """

    start: datetime
    counts: tuple[tuple[str, int], ...]

    def count(self, status: str) -> int:
        return dict(self.counts).get(status, 0)


@dataclass(frozen=True, slots=True)
class Series:
    """Proposals over the window, one point per hour ("today") or per day.

    Days are whole calendar days in UTC, the last of them today and so still
    filling. The figures above are rolling windows, which is why a screen draws
    this series' own totals beside it rather than borrowing theirs: the two are
    measured over slightly different spans, and a chart whose legend disagreed
    with its own columns would be caught.
    """

    step: str
    points: tuple[Point, ...]


def proposals_over(session: Session, *, window: str = "7d", now: datetime | None = None) -> Series:
    """Count what Otto proposed in each period of the window.

    Bucketed here rather than with a GROUP BY on a truncated date, because the
    truncation functions differ between SQLite and Postgres and the tests run
    on one while production runs on the other. One indexed range scan of two
    columns is cheap at the volumes an internal panel looks at.
    """
    now = now or datetime.now(UTC)
    window = window if window in WINDOWS else "7d"
    if window == "today":
        step, size, n = "hour", timedelta(hours=1), 24
        first = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=n - 1)
    else:
        step, size, n = "day", timedelta(days=1), WINDOWS[window]
        first = datetime(now.year, now.month, now.day, tzinfo=UTC) - timedelta(days=n - 1)

    tally: list[dict[str, int]] = [{} for _ in range(n)]
    rows = session.execute(
        select(OptimizationAction.created_at, OptimizationAction.status).where(
            OptimizationAction.created_at >= first
        )
    )
    for created_at, status in rows:
        if created_at is None:
            continue
        at = int((_aware(created_at) - first) / size)
        if 0 <= at < n:
            tally[at][status] = tally[at].get(status, 0) + 1

    return Series(
        step=step,
        points=tuple(
            Point(start=first + size * i, counts=tuple(sorted(one.items())))
            for i, one in enumerate(tally)
        ),
    )


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
            f"{syncs_failed.value} sync{'s' if syncs_failed.value > 1 else ''} failed"
            f" {over(syncs_failed.window)}."
        )
    if model_trouble.value:
        said.append(
            f"{model_trouble.value} model call{'s' if model_trouble.value > 1 else ''} came"
            f" back with nothing {over(model_trouble.window)}."
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


#: The merchant list's tabs. "attention" is every business whose row has
#: trouble to show; "unconnected" is every business with no Google Ads account.
SHOWS: Final = ("all", "attention", "unconnected")


def _newest_connection() -> Any:
    """The id of a business's newest connection that names a Google Ads account.

    One rule for the row and for the filter. A business can hold more than one
    connection (a reconnect leaves the old row), and the list used to take
    whichever the database returned first, so the tab could count a business
    one way and its row could show it another.
    """
    pick = aliased(AdsConnection)
    return (
        select(pick.id)
        .where(pick.organization_id == Organization.id, pick.customer_id != "")
        .order_by(pick.created_at.desc(), pick.id.desc())
        .limit(1)
        .correlate(Organization)
        .scalar_subquery()
    )


def _businesses(*, look_for: str = "", show: str = "all") -> list[Any]:
    """The filters a page of the list and its counts share.

    "attention" is `MerchantRow.trouble` written as SQL, so a page of the
    "Need a person" tab can be read without building every row to find out
    which ones have trouble. The three tests, in the row's order: no
    connection; Google reports a status other than ENABLED; never synced to
    the end. A test in this module keeps the two definitions in step.
    """
    where: list[Any] = []
    if look_for.strip():
        where.append(func.lower(Organization.name).like(f"%{look_for.strip().lower()}%"))
    newest = _newest_connection()
    if show == "unconnected":
        where.append(newest.is_(None))
    elif show == "attention":
        conn, run = aliased(AdsConnection), aliased(SyncRun)
        bad_status = (
            select(conn.id)
            .where(conn.id == newest, conn.account_status.not_in(("ENABLED", "")))
            .exists()
        )
        never_synced = (
            select(conn.id)
            .where(
                conn.id == newest,
                ~select(run.id)
                .where(run.customer_id == conn.customer_id, run.finished_at.is_not(None))
                .exists(),
            )
            .exists()
        )
        where.append(or_(newest.is_(None), bad_status, never_synced))
    return where


def count_merchants(session: Session, *, look_for: str = "") -> dict[str, int]:
    """How many businesses each tab holds, under the same search."""
    return {
        show: _count(
            session,
            select(func.count())
            .select_from(Organization)
            .where(*_businesses(look_for=look_for, show=show)),
        )
        for show in SHOWS
    }


def merchants(
    session: Session,
    *,
    look_for: str = "",
    show: str = "all",
    most: int = 100,
    skip: int = 0,
) -> list[MerchantRow]:
    """Businesses, newest first, a page at a time, with enough on each row to
    decide who needs attention.

    Counted per row rather than in one grouped query, which is slower and
    deliberate: the grouped version needs outer joins across four tables and
    the first reader to change it will get a count wrong. It is only ever done
    for one page, so the cost is bounded by the page, not by the platform.

    Ordered by the id after the creation time: businesses made in one
    transaction share a timestamp, and without a second key a page boundary
    could fall differently from one request to the next.
    """
    show = show if show in SHOWS else "all"
    wanted = (
        select(Organization)
        .where(*_businesses(look_for=look_for, show=show))
        .order_by(Organization.created_at.desc(), Organization.id.desc())
        .offset(max(0, skip))
        .limit(most)
    )

    out: list[MerchantRow] = []
    for place in session.scalars(wanted):
        connection = session.scalars(
            select(AdsConnection)
            .where(AdsConnection.organization_id == place.id, AdsConnection.customer_id != "")
            .order_by(AdsConnection.created_at.desc(), AdsConnection.id.desc())
            .limit(1)
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


def _aware(when: datetime) -> datetime:
    """A time that can be subtracted from `now`, whatever the driver returned.

    SQLite hands back naive datetimes even for a `DateTime(timezone=True)`
    column, so arithmetic against an aware `now` raises. `opt.guardrails`
    already does this for the same reason; doing it here rather than at each
    call site means the next reader cannot forget.
    """
    return when if when.tzinfo else when.replace(tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class JobRun:
    """One run of one scheduled job, as the jobs screen shows it."""

    id: uuid.UUID
    customer_id: str
    kind: str
    status: str
    stage: str
    trouble: str
    started_at: datetime
    finished_at: datetime | None

    @property
    def took_seconds(self) -> int | None:
        """None while it is still running, which is not the same as instant."""
        if self.finished_at is None:
            return None
        return max(0, int((_aware(self.finished_at) - _aware(self.started_at)).total_seconds()))

    def stuck(self, now: datetime) -> bool:
        return self.finished_at is None and (_aware(now) - _aware(self.started_at)) > STUCK_AFTER

    def words(self, now: datetime) -> str:
        if self.stuck(now):
            hours = int((_aware(now) - _aware(self.started_at)).total_seconds() // 3600)
            return f"Started {hours} h ago and never finished."
        if self.trouble:
            return self.trouble
        if self.finished_at is None:
            return "Still running."
        return f"Finished in {self.took_seconds} s."


def _runs(*, kind: str = "", failed_only: bool = False) -> list[Any]:
    """The filters the jobs list and its count share, so they cannot disagree."""
    where: list[Any] = []
    if kind.strip():
        where.append(SyncRun.kind == kind.strip())
    if failed_only:
        where.append(SyncRun.status == "failed")
    return where


def jobs(
    session: Session,
    *,
    kind: str = "",
    failed_only: bool = False,
    most: int = 100,
    skip: int = 0,
    now: datetime | None = None,
) -> list[JobRun]:
    """The most recent runs, newest first, one page at a time.

    Newest first rather than oldest, because the question somebody brings to
    this screen is almost always "what just happened", not "what happened
    first". The stuck ones surface anyway: they have no finish time, so they
    read as trouble whatever their age.

    Ordered by the id after the start time. Two runs can start in the same
    second (every account's structure sync and today's figures fire on the
    quarter hour), and without a second key the database may return them in
    either order, so a row could appear on two pages or on neither.
    """
    now = now or datetime.now(UTC)
    wanted = (
        select(SyncRun)
        .where(*_runs(kind=kind, failed_only=failed_only))
        .order_by(SyncRun.started_at.desc(), SyncRun.id.desc())
        .offset(max(0, skip))
        .limit(most)
    )
    return [
        JobRun(
            id=row.id,
            customer_id=row.customer_id or "",
            kind=row.kind or "",
            status=row.status or "",
            stage=row.stage or "",
            trouble=row.trouble or "",
            started_at=row.started_at,
            finished_at=row.finished_at,
        )
        for row in session.scalars(wanted)
    ]


def count_jobs(session: Session, *, kind: str = "", failed_only: bool = False) -> int:
    """How many runs there are in all, for "26-50 of 1,284"."""
    return _count(
        session,
        select(func.count()).select_from(SyncRun).where(*_runs(kind=kind, failed_only=failed_only)),
    )


@dataclass(frozen=True, slots=True)
class Fault:
    """One thing that went wrong, from wherever it went wrong.

    Jobs and model calls fail for unrelated reasons, and a screen that showed
    them in separate tables would make somebody read both to find out whether
    anything is wrong. One list, with `where` saying which.
    """

    where: str
    what: str
    customer_id: str
    at: datetime

    @property
    def words(self) -> str:
        return self.what


def faults(
    session: Session, *, window: str = "7d", most: int = 100, now: datetime | None = None
) -> list[Fault]:
    """Everything that failed recently, newest first, from both sources."""
    now = now or datetime.now(UTC)
    since = _since(window if window in WINDOWS else "7d", now)

    out: list[Fault] = [
        Fault(
            where=f"sync ({row.kind})",
            what=row.trouble or "The job failed and said nothing.",
            customer_id=row.customer_id or "",
            at=row.started_at,
        )
        for row in session.scalars(
            select(SyncRun)
            .where(SyncRun.started_at >= since, SyncRun.status == "failed")
            .order_by(SyncRun.started_at.desc())
            .limit(most)
        )
    ]
    out += [
        Fault(
            where=f"model ({row.job})",
            what=row.trouble or "The model call failed and said nothing.",
            customer_id=row.customer_id or "",
            at=row.created_at,
        )
        for row in session.scalars(
            select(PromptLog)
            .where(PromptLog.created_at >= since, PromptLog.trouble != "")
            .order_by(PromptLog.created_at.desc())
            .limit(most)
        )
    ]
    out.sort(key=lambda one: one.at, reverse=True)
    return out[:most]
