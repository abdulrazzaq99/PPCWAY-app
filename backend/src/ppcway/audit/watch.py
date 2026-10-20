"""Which audits are due, and how often each part is worth re-reading.

An audit that runs once is a sales document. An audit that runs every day is a
tool: it notices the week a redesign dropped the conversion tag, and it can show
an owner the day their fix landed.

Three cadences, set by what changes and what it costs.

  The website, daily. It is ours to read, it costs a crawl, and it is the thing
  that changes without anybody telling us.

  The listing and what the searching is worth, weekly. Those come from Google's
  Places and Keyword Planner, they are charged per call, and a business's
  opening hours and a town's search volume do not move daily.

  The account's own four checks, with each sync, which is the mirror's job
  rather than this one.

Nothing is audited for somebody who cannot see the result: a run is only due for
a site that belongs to a business, because that is who the history is shown to.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.audit.models import AuditRequest, AuditRun

#: The website, once a day.
EVERY_DAY = 1

#: The parts Google charges for, once a week.
LISTING_EVERY = 7

#: How many to start in one pass of the clock. A hundred accounts should not
#: become a hundred browsers at one minute past midnight.
MOST = 20


@dataclass
class Due:
    """One site that is due a re-run, and how much of it to re-read."""

    site: str
    organization_id: uuid.UUID | None
    request_id: uuid.UUID | None
    #: Re-read the parts Google charges for, because a week has passed.
    with_demand: bool = False
    #: Why it is due, for the log and for anybody asking.
    because: str = ""


def due_audits(
    session: Session,
    *,
    now: datetime | None = None,
    every: int = EVERY_DAY,
    listing_every: int = LISTING_EVERY,
    most: int = MOST,
) -> list[Due]:
    """Every site whose audit is older than the cadence says it should be."""
    at = now or datetime.now(UTC)
    stale = at - timedelta(days=every)
    old_listing = at - timedelta(days=listing_every)

    # The most recent request per site per business, which is what carries the
    # town, the trade and the listing the audit needs to run again.
    asked: dict[tuple[str, uuid.UUID | None], AuditRequest] = {}
    for request in session.scalars(
        select(AuditRequest)
        .where(AuditRequest.organization_id.is_not(None))
        .order_by(AuditRequest.created_at)
    ):
        asked[(request.site, request.organization_id)] = request

    out: list[Due] = []
    for (site, organization_id), request in asked.items():
        runs = list(
            session.scalars(
                select(AuditRun)
                .join(AuditRequest, AuditRun.request_id == AuditRequest.id)
                .where(
                    AuditRun.site == site,
                    AuditRequest.organization_id == organization_id,
                    AuditRun.status.in_(("done", "running", "queued")),
                )
                .order_by(AuditRun.created_at.desc())
                .limit(10)
            )
        )
        # Something is already in flight, so leave it alone.
        if any(run.status in ("running", "queued") for run in runs):
            continue
        done = [run for run in runs if run.status == "done"]
        latest = done[0] if done else None

        def moment(run: AuditRun) -> datetime:
            when = run.finished_at or run.created_at
            return when if when.tzinfo else when.replace(tzinfo=UTC)

        if latest is not None and moment(latest) > stale:
            continue

        # The paid half is re-read only when a week has passed since the last
        # run that actually carried it.
        with_demand = not any(
            (run.report or {}).get("demand") and moment(run) > old_listing for run in done
        )
        out.append(
            Due(
                site=site,
                organization_id=organization_id,
                request_id=request.id,
                with_demand=with_demand,
                because=(
                    "never audited" if latest is None else f"last read {moment(latest).date()}"
                ),
            )
        )
        if len(out) >= most:
            break
    return out
