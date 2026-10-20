"""The audit over time, and what changed since last time.

One reading is a number. Two readings are an answer: did the thing we told
somebody to fix actually get fixed, and did anything break while they were not
looking?

Both questions are answered from the audit runs we already keep. Nothing new is
measured here; this is the arithmetic over what is stored, which is why it costs
a database query and can be on every screen that shows a score.

The marker on the history line is the useful part. A point is marked where a
finding went from "needs you" to "good", so an owner can see the day the work
landed and what it was worth — and where one went the other way, which is how a
redesign that quietly removed the conversion tag gets noticed in a day rather
than in a quarter.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.audit.models import AuditRequest, AuditRun

#: How many readings a history chart is worth showing.
MOST = 60


def findings_of(run: AuditRun) -> dict[str, dict[str, Any]]:
    """The run's findings, keyed by the check they belong to."""
    found = (run.report or {}).get("findings") if run.report else None
    if not found:
        return {}
    return {str(f.get("key", "")): f for f in found if f.get("key")}


def score_of(run: AuditRun) -> int | None:
    """The share of the checks this run could judge that came out good.

    `unknown` counts against nobody: a check that could not run is not a fault
    of the website, and scoring it as a failure would punish somebody for our
    own missing API key.
    """
    findings = (run.report or {}).get("findings") if run.report else None
    if not findings:
        return None
    known = [f for f in findings if f.get("status") != "unknown"]
    if not known:
        return None
    good = sum(1 for f in known if f.get("status") == "good")
    return round((good / len(known)) * 100)


@dataclass
class Point:
    """One reading on the history line."""

    run_id: str
    at: str
    score: int | None
    needs: int = 0
    good: int = 0
    #: "asked" for a run somebody started, "scheduled" for one on the clock.
    kind: str = "asked"
    #: What this reading fixed, and what it broke, against the one before it.
    fixed: list[str] = field(default_factory=list)
    broke: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "at": self.at,
            "score": self.score,
            "needs": self.needs,
            "good": self.good,
            "kind": self.kind,
            "fixed": self.fixed,
            "broke": self.broke,
        }


@dataclass
class Changed:
    """What moved between the last two readings."""

    #: True when there is only one reading, so there is nothing to compare.
    first: bool = True
    at: str = ""
    before_at: str = ""
    score: int | None = None
    score_before: int | None = None
    fixed: list[dict[str, str]] = field(default_factory=list)
    broke: list[dict[str, str]] = field(default_factory=list)
    still: list[dict[str, str]] = field(default_factory=list)

    @property
    def quiet(self) -> bool:
        """Nothing moved either way, which is itself worth saying."""
        return not self.first and not self.fixed and not self.broke

    def as_dict(self) -> dict[str, Any]:
        return {
            "first": self.first,
            "quiet": self.quiet,
            "at": self.at,
            "before_at": self.before_at,
            "score": self.score,
            "score_before": self.score_before,
            "fixed": self.fixed,
            "broke": self.broke,
            "still": self.still,
        }


def runs_for(
    session: Session,
    site: str,
    *,
    organization_id: uuid.UUID | None = None,
    most: int = MOST,
) -> list[AuditRun]:
    """Every finished run for one site, oldest first.

    Scoped to the business when we know it, because two businesses can audit the
    same address — an agency and its client often do — and neither should see
    the other's history.
    """
    query = select(AuditRun).where(AuditRun.site == site, AuditRun.status == "done")
    if organization_id is not None:
        query = query.join(AuditRequest, AuditRun.request_id == AuditRequest.id).where(
            AuditRequest.organization_id == organization_id
        )
    found = list(session.scalars(query.order_by(AuditRun.finished_at.desc()).limit(most)))
    # A run with no finish time cannot be ordered against one that has one, so
    # it sorts to the start rather than crashing the chart.
    floor = datetime.min.replace(tzinfo=UTC)
    return sorted(found, key=lambda r: r.finished_at or floor)


def _moved(
    before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """What got better, what got worse, and what is still waiting."""
    fixed: list[dict[str, str]] = []
    broke: list[dict[str, str]] = []
    still: list[dict[str, str]] = []
    for key, now in after.items():
        was = before.get(key)
        title = str(now.get("title", key))
        status = now.get("status")
        if status == "good" and was is not None and was.get("status") == "needs_you":
            fixed.append({"key": key, "title": title, "summary": str(now.get("summary", ""))})
        elif status == "needs_you" and was is not None and was.get("status") == "good":
            broke.append({"key": key, "title": title, "summary": str(now.get("summary", ""))})
        elif status == "needs_you":
            still.append({"key": key, "title": title, "summary": str(now.get("summary", ""))})
    return fixed, broke, still


def score_history(
    session: Session,
    site: str,
    *,
    organization_id: uuid.UUID | None = None,
    most: int = MOST,
) -> list[Point]:
    """Every reading for one site, with the fixes marked where they landed."""
    points: list[Point] = []
    before: dict[str, dict[str, Any]] = {}
    for run in runs_for(session, site, organization_id=organization_id, most=most):
        now = findings_of(run)
        fixed, broke, _ = _moved(before, now) if before else ([], [], [])
        points.append(
            Point(
                run_id=str(run.id),
                at=(run.finished_at or run.created_at).isoformat(),
                score=score_of(run),
                needs=sum(1 for f in now.values() if f.get("status") == "needs_you"),
                good=sum(1 for f in now.values() if f.get("status") == "good"),
                kind=run.kind,
                fixed=[f["title"] for f in fixed],
                broke=[b["title"] for b in broke],
            )
        )
        before = now
    return points


def what_changed(
    session: Session,
    site: str,
    *,
    organization_id: uuid.UUID | None = None,
) -> Changed:
    """The last two readings, compared."""
    runs = runs_for(session, site, organization_id=organization_id, most=2)
    if not runs:
        return Changed()
    latest = runs[-1]
    now = findings_of(latest)
    if len(runs) == 1:
        _, _, still = _moved(now, now)
        return Changed(
            first=True,
            at=(latest.finished_at or latest.created_at).isoformat(),
            score=score_of(latest),
            still=still,
        )
    earlier = runs[-2]
    fixed, broke, still = _moved(findings_of(earlier), now)
    return Changed(
        first=False,
        at=(latest.finished_at or latest.created_at).isoformat(),
        before_at=(earlier.finished_at or earlier.created_at).isoformat(),
        score=score_of(latest),
        score_before=score_of(earlier),
        fixed=fixed,
        broke=broke,
        still=still,
    )
