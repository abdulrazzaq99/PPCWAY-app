"""What an audit says. Plain words first, evidence second.

A finding has one of four statuses, the same three the report screen draws plus
one for "could not tell":

* ``good``      green, nothing to do
* ``needs_you`` amber, a small change only the merchant can make
* ``ours``      grey, PPCWay handles it in the campaign
* ``unknown``   the check could not run; the summary says why
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

Status = Literal["good", "needs_you", "ours", "unknown"]

#: The eight checks, in the order the report shows them. Keys are stable: the web
#: app and the database rely on them.
CHECK_KEYS: tuple[str, ...] = (
    "counting",
    "speed",
    "mobile",
    "match",
    "form",
    "tags",
    "trust",
    "policy",
)
#: The look under the hood: what people see first, site health, local presence.
MORE_KEYS: tuple[str, ...] = ("firstscreen", "health", "local")


@dataclass(frozen=True)
class Finding:
    key: str
    title: str
    status: Status
    #: One sentence a plumber can read.
    summary: str
    #: What we saw, in plain words, one line each.
    detail: tuple[str, ...] = ()
    #: What to do, when the status is needs_you.
    fix: str | None = None
    #: Raw numbers and identifiers, for the drilled-in screen and for us.
    evidence: dict[str, Any] = field(default_factory=dict)
    #: "checks" for the eight, "more" for the look under the hood.
    group: Literal["checks", "more"] = "checks"


@dataclass
class AuditReport:
    site: str
    started_at: datetime
    finished_at: datetime | None = None
    business_name: str = ""
    phone: str = ""
    pages_read: int = 0
    findings: list[Finding] = field(default_factory=list)
    #: Stage failures that did not stop the audit, one line each.
    notes: list[str] = field(default_factory=list)
    #: What the home page looks like on a phone and a laptop; served by the API, not stored in the report.
    screenshots: dict[str, bytes] = field(default_factory=dict, repr=False)
    #: Filled by the API once the screenshots are saved: kind -> URL path.
    screenshot_urls: dict[str, str] = field(default_factory=dict)
    headline: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("screenshots", None)
        d["started_at"] = self.started_at.isoformat()
        d["finished_at"] = self.finished_at.isoformat() if self.finished_at else None
        return d

    @property
    def counts(self) -> dict[str, int]:
        out = {"good": 0, "needs_you": 0, "ours": 0, "unknown": 0}
        for f in self.findings:
            out[f.status] += 1
        return out
