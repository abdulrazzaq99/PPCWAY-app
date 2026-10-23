"""What the free audit page shows, before and after the email is proved.

Two shapes come out of here, and the difference between them is the whole
point of the page:

- **the summary**, for anybody who ran an audit: the score, the verdict in
  words, and how many things are to fix, to improve and already working. It
  says how much there is without saying what it is.
- **the report**, once the address is proved: every finding, what it means and
  what to do about it, and what the spending is likely losing.

The findings are the audit's own. Nothing here invents one, re-words one, or
orders them by anything but how much they cost the person reading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ppcway.audit.models import AuditRequest, AuditRun

#: Who looks after the advertising. It changes nothing we check; it tells
#: whoever speaks to them next what conversation to have.
RUNNERS: dict[str, str] = {
    "me": "I run them",
    "agency": "An agency runs them",
    "none": "Not running ads yet",
    "self_agency": "I'm an agency",
}

#: What the ads are for, in the client's words.
GOALS: dict[str, str] = {
    "sales": "Online sales",
    "leads": "Leads and demos",
    "calls": "Calls and bookings",
    "signups": "Sign-ups and installs",
}

#: What they spend a month, and what the client's own figures say that much
#: spending typically loses where these problems are present. Theirs, from the
#: handoff, not ours: a range offered as a range, never as a measurement.
SPEND_BANDS: dict[str, str] = {
    "none": "Not yet",
    "under_1k": "Under $1k",
    "1k_5k": "$1k–$5k",
    "5k_25k": "$5k–$25k",
    "25k_plus": "$25k+",
}

WASTE: dict[str, tuple[int, int | None] | None] = {
    "none": None,
    "under_1k": (90, 180),
    "1k_5k": (400, 1100),
    "5k_25k": (1800, 5200),
    "25k_plus": (6000, None),
}

#: A score at or above this reads as a working account with leaks in it.
GOOD_FROM = 60

#: The six stages the waiting screen names, and the part of the run that does
#: each one. The run has four phases; these are what those phases are for, in
#: the words somebody waiting would use.
STAGES: list[tuple[str, str]] = [
    ("Reading your website", "crawling"),
    ("Checking conversion tracking", "crawling"),
    ("Checking speed and security on a phone", "speed"),
    ("Checking your search presence", "checks"),
    ("Checking ad readiness", "checks"),
    ("Comparing with similar businesses", "checks"),
]

#: The order the run moves through, so a stage can be told from a later one.
PHASES = ["", "crawling", "rendering", "speed", "checks", "done"]

#: What the audit's own statuses mean on this page.
SEVERITY = {"needs_you": "fix", "ours": "improve", "good": "good"}

#: Findings first by what they cost, then in the order the audit found them.
WEIGHT = {"fix": 0, "improve": 1, "good": 2}


@dataclass
class Summary:
    """What anybody who runs an audit may see."""

    score: int = 0
    verdict: str = ""
    business: str = ""
    goal: str = ""
    to_fix: int = 0
    to_improve: int = 0
    working: int = 0

    @property
    def band(self) -> str:
        return "good" if self.score >= GOOD_FROM else "warn"

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band,
            "verdict": self.verdict,
            "business": self.business,
            "goal": self.goal,
            "to_fix": self.to_fix,
            "to_improve": self.to_improve,
            "working": self.working,
        }


@dataclass
class Report:
    """The summary, plus what anybody who proved their address may see."""

    summary: Summary = field(default_factory=Summary)
    findings: list[dict[str, str]] = field(default_factory=list)
    waste: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {**self.summary.as_dict(), "findings": self.findings, "waste": self.waste}


def verdict_for(score: int) -> str:
    """The score in words, which is what a person actually reads."""
    return (
        "Good base, with clear leaks to fix"
        if score >= GOOD_FROM
        else "Room to grow, and it's fixable"
    )


def stages_at(stage: str, *, done: bool = False) -> list[dict[str, str]]:
    """The six stages, each marked done, running or still to come."""
    if done:
        return [{"label": label, "state": "done"} for label, _ in STAGES]
    at = PHASES.index(stage) if stage in PHASES else 0
    out: list[dict[str, str]] = []
    running_taken = False
    for label, owner in STAGES:
        owner_at = PHASES.index(owner)
        if owner_at < at:
            state = "done"
        elif owner_at == at and not running_taken:
            state = "running"
            running_taken = True
        elif owner_at == at:
            state = "todo"
        else:
            state = "todo"
        out.append({"label": label, "state": state})
    return out


def percent_at(stage: str, *, done: bool = False) -> int:
    """How far along, for the bar above the stages."""
    if done:
        return 100
    marks = stages_at(stage)
    finished = sum(1 for one in marks if one["state"] == "done")
    running = any(one["state"] == "running" for one in marks)
    return min(96, round((finished + (0.5 if running else 0)) / len(STAGES) * 100))


def _findings(run: AuditRun) -> list[dict[str, Any]]:
    report = run.report or {}
    found = report.get("findings")
    return [one for one in found if isinstance(one, dict)] if isinstance(found, list) else []


def summary_of(run: AuditRun, request: AuditRequest | None, *, score: int) -> Summary:
    """The locked half: how much there is, without saying what."""
    counted = {"fix": 0, "improve": 0, "good": 0}
    for one in _findings(run):
        severity = SEVERITY.get(str(one.get("status", "")))
        if severity:
            counted[severity] += 1
    return Summary(
        score=score,
        verdict=verdict_for(score),
        business=(request.business_name if request else "") or run.site,
        goal=GOALS.get(request.goal if request else "", ""),
        to_fix=counted["fix"],
        to_improve=counted["improve"],
        working=counted["good"],
    )


def waste_for(spend_band: str) -> dict[str, Any] | None:
    """What that much spending is likely losing, as a range or not at all."""
    band = WASTE.get(spend_band)
    if band is None:
        return None
    low, high = band
    return {
        "low": low,
        "high": high,
        "said": f"${low:,}–${high:,} a month" if high else f"${low:,}+ a month",
    }


def report_of(run: AuditRun, request: AuditRequest | None, *, score: int) -> Report:
    """Everything, for somebody who has proved the address is theirs."""
    summary = summary_of(run, request, score=score)
    findings: list[dict[str, str]] = []
    for one in _findings(run):
        severity = SEVERITY.get(str(one.get("status", "")))
        if not severity:
            continue
        detail = one.get("detail")
        findings.append(
            {
                "id": str(one.get("key", "")),
                "severity": severity,
                "title": str(one.get("title", "")),
                "detail": str(one.get("summary", ""))
                or (" ".join(str(d) for d in detail) if isinstance(detail, list) else ""),
                "fix": str(one.get("fix") or ""),
            }
        )
    findings.sort(key=lambda f: WEIGHT.get(f["severity"], 3))
    return Report(
        summary=summary,
        findings=findings,
        waste=waste_for(request.spend_band if request else ""),
    )
