"""The phase-one gate: seven days of clean sync on five accounts.

The requirements put a gate in front of letting PPCway write to anybody's
account: seven consecutive days of the mirror syncing cleanly, on five internal
accounts. It is the right gate, and the only way it means anything is if the
answer is computed rather than claimed.

So this counts. It reads the sync runs we already keep and says, per account,
how many of the last seven days had a successful read and no failures, and then
says plainly how many accounts are passing against how many the gate asks for.

If we are running on two accounts rather than five, this says so. That sentence
is the point of the module: a gate that reports itself as passed because nobody
counted is worse than no gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import SyncRun
from ppcway.ads.models import AdsConnection

#: What the requirements ask for.
WANTED_DAYS = 7
WANTED_ACCOUNTS = 5


@dataclass
class AccountGate:
    """One account's standing against the gate."""

    customer_id: str
    name: str = ""
    #: Days in the window with at least one successful read and no failures.
    clean_days: int = 0
    #: Days with no read at all, which is a gap rather than a failure.
    silent_days: list[str] = field(default_factory=list)
    #: Days where something failed, with Google's reason made plain.
    failed_days: list[str] = field(default_factory=list)
    trouble: str = ""
    runs: int = 0

    @property
    def passing(self) -> bool:
        return self.clean_days >= WANTED_DAYS

    def as_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "clean_days": self.clean_days,
            "silent_days": self.silent_days,
            "failed_days": self.failed_days,
            "trouble": self.trouble,
            "runs": self.runs,
            "passing": self.passing,
        }


@dataclass
class Gate:
    """Where the gate stands, and the sentence that says it."""

    days: int = WANTED_DAYS
    wanted_accounts: int = WANTED_ACCOUNTS
    accounts: list[AccountGate] = field(default_factory=list)

    @property
    def passing(self) -> int:
        return sum(1 for account in self.accounts if account.passing)

    @property
    def passed(self) -> bool:
        return self.passing >= self.wanted_accounts

    @property
    def said(self) -> str:
        """The honest sentence, including when it is not the one we wanted."""
        if not self.accounts:
            return (
                "No account is connected, so the gate has nothing to measure. "
                f"It needs {self.wanted_accounts} accounts with {self.days} clean days."
            )
        if self.passed:
            return (
                f"{self.passing} accounts have {self.days} clean days of syncing. "
                "The gate is passed."
            )
        return (
            f"{self.passing} of the {self.wanted_accounts} accounts the gate asks for "
            f"have {self.days} clean days. It is running on {len(self.accounts)} "
            f"connected {'account' if len(self.accounts) == 1 else 'accounts'}. "
            "The gate is not passed."
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "days": self.days,
            "wanted_accounts": self.wanted_accounts,
            "passing": self.passing,
            "passed": self.passed,
            "connected": len(self.accounts),
            "said": self.said,
            "accounts": [account.as_dict() for account in self.accounts],
        }


def _days_back(now: date, days: int) -> list[date]:
    """The window, ending yesterday, because today is not over."""
    return [now - timedelta(days=n) for n in range(days, 0, -1)]


def gate_report(
    session: Session,
    *,
    now: datetime | None = None,
    days: int = WANTED_DAYS,
    wanted: int = WANTED_ACCOUNTS,
) -> Gate:
    """Count the gate, account by account, out of the sync runs we keep."""
    at = now or datetime.now(UTC)
    window = _days_back(at.date(), days)
    gate = Gate(days=days, wanted_accounts=wanted)

    connections = session.scalars(
        select(AdsConnection).where(
            AdsConnection.customer_id != "", AdsConnection.revoked_at.is_(None)
        )
    ).all()
    seen: set[str] = set()
    for connection in connections:
        if connection.customer_id in seen:
            continue
        seen.add(connection.customer_id)
        standing = AccountGate(customer_id=connection.customer_id, name=connection.customer_name)
        runs = list(
            session.scalars(
                select(SyncRun).where(
                    SyncRun.customer_id == connection.customer_id,
                    SyncRun.started_at >= at - timedelta(days=days + 1),
                )
            )
        )
        standing.runs = len(runs)
        by_day: dict[date, list[SyncRun]] = {}
        for run in runs:
            started = run.started_at
            when = (started if started.tzinfo else started.replace(tzinfo=UTC)).date()
            by_day.setdefault(when, []).append(run)
        for day in window:
            mine = by_day.get(day, [])
            if not mine:
                standing.silent_days.append(day.isoformat())
                continue
            if any(run.status == "failed" for run in mine):
                standing.failed_days.append(day.isoformat())
                if not standing.trouble:
                    standing.trouble = next(
                        (run.trouble for run in mine if run.status == "failed" and run.trouble),
                        "",
                    )
                continue
            if any(run.status == "done" for run in mine):
                standing.clean_days += 1
        gate.accounts.append(standing)

    gate.accounts.sort(key=lambda a: (-a.clean_days, a.name))
    return gate
