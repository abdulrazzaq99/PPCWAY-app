"""Leads that became jobs, sent back to Google Ads as conversions.

Google's bidding learns from whatever it is told counts. Told "a form was
sent", it finds more people who send forms, including the ones who were only
asking. Told "this form became a $450 job", it finds more people like the ones
who paid. That second signal is the most useful thing a small service business
can give it, and only the merchant knows it: so the merchant marks a lead as a
job on the Website screen, and PPCWay uploads it against the ad click that
brought the visitor (Google's `ConversionUploadService`, "offline conversions").

This module decides and reads; it does not send. Sending goes through the
gateway, from the API, behind the same switches as every other write.

What Google needs, and what this checks before asking:

- **the click.** A lead that did not come from a Google ad has nothing to
  attach the job to, and says so (`no_click`) rather than failing later;
- **within 90 days of it**, the longest window the action is created with;
- **one id per conversion**: gclid, or else gbraid, or else wbraid;
- **an order id**, the lead's own id, so a job sent twice is counted once.

Google is sometimes not ready yet -- a click from minutes ago, or an action
created in the last few hours -- and says so with a code that means "later".
Those stay `waiting` for the hourly pass. Anything else is `failed`, with
Google's reason, which the screen shows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ppcway.site.models import SiteLead, SiteVisit

#: The conversion action PPCWay creates for jobs, by name.
JOB_ACTION_NAME: Final = "Jobs from PPCWay leads"

#: Google accepts a click's conversion for as long as the action's window,
#: which PPCWay creates at Google's longest, 90 days.
CLICK_WINDOW: Final = timedelta(days=90)

#: Google's codes that mean "not yet": try again on the next pass.
LATER: Final = frozenset(
    {
        "TOO_RECENT_CONVERSION_ACTION",
        "TOO_RECENT_EVENT",
        "TOO_RECENT_CLICK",
        "EVENT_NOT_FOUND",
        "CLICK_NOT_FOUND",
        "CONCURRENT_MODIFICATION",
        "INTERNAL_ERROR",
        "TRANSIENT_ERROR",
    }
)
#: How long "Google has not seen that click yet" is believed. Past this, the
#: click is not going to appear, and the job is reported as failed.
NOT_FOUND_FOR: Final = timedelta(days=3)
#: Codes that mean Google has this one already.
ALREADY: Final = frozenset(
    {"ORDER_ID_ALREADY_IN_USE", "DUPLICATE_ORDER_ID", "CLICK_CONVERSION_ALREADY_EXISTS"}
)

#: How long leads and visits are kept. Thirteen months: a year's comparison
#: with the month either side, and no longer.
KEEP: Final = timedelta(days=395)


def _aware(when: datetime) -> datetime:
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def mark(
    lead: SiteLead,
    *,
    status: str,
    value: float | None,
    currency: str,
    by: Any,
    sending: bool,
    now: datetime | None = None,
) -> None:
    """Record what the lead turned out to be, and whether it goes to Google.

    A job already sent stays sent whatever it is changed to afterwards: Google
    has it, and saying otherwise would be untrue. The screen says so.
    """
    at = now or datetime.now(UTC)
    lead.status = status
    lead.value = value if status == "job" else None
    lead.currency = currency if status == "job" else ""
    lead.marked_at = at
    lead.marked_by = by
    if lead.upload == "sent":
        return
    if status != "job" or not sending:
        lead.upload = ""
        lead.upload_note = ""
        return
    if not (lead.gclid or lead.gbraid or lead.wbraid):
        lead.upload = "no_click"
        lead.upload_note = "This lead did not come from a Google ad, so there is no click to send."
        return
    if lead.clicked_at and at - _aware(lead.clicked_at) > CLICK_WINDOW:
        lead.upload = "no_click"
        lead.upload_note = (
            "The ad click was more than 90 days ago, which is longer than Google allows."
        )
        return
    lead.upload = "waiting"
    lead.upload_note = ""


def waiting(session: Session, organization_id: Any, *, limit: int = 200) -> list[SiteLead]:
    """Jobs waiting to go to Google Ads, oldest first."""
    return list(
        session.scalars(
            select(SiteLead)
            .where(SiteLead.organization_id == organization_id, SiteLead.upload == "waiting")
            .order_by(SiteLead.marked_at.asc())
            .limit(limit)
        ).all()
    )


def businesses_waiting(session: Session) -> list[Any]:
    """Every business with a job waiting, for the hourly pass."""
    return list(
        session.scalars(
            select(SiteLead.organization_id).where(SiteLead.upload == "waiting").distinct()
        ).all()
    )


def click_conversion(lead: SiteLead, action: str) -> dict[str, Any]:
    """One job in the shape Google's `uploadClickConversions` takes."""
    when = _aware(lead.marked_at or datetime.now(UTC)).astimezone(UTC)
    clicked = _aware(lead.clicked_at) if lead.clicked_at else None
    if clicked and when <= clicked:
        # Marked within a second of the click, in a test or by a fast hand:
        # Google refuses a conversion that does not come after its click.
        when = clicked + timedelta(seconds=1)
    out: dict[str, Any] = {
        "conversionAction": action,
        "conversionDateTime": when.strftime("%Y-%m-%d %H:%M:%S+00:00"),
        "orderId": str(lead.id),
    }
    if lead.value is not None and lead.value > 0:
        out["conversionValue"] = float(lead.value)
        out["currencyCode"] = lead.currency or "CAD"
    if lead.gclid:
        out["gclid"] = lead.gclid
    elif lead.gbraid:
        out["gbraid"] = lead.gbraid
    else:
        out["wbraid"] = lead.wbraid
    return out


@dataclass(frozen=True)
class Outcome:
    sent: int = 0
    later: int = 0
    failed: int = 0


def read_outcome(
    leads: list[SiteLead],
    landed: tuple[bool, ...],
    refusals: dict[int, tuple[str, str]],
    *,
    now: datetime | None = None,
) -> Outcome:
    """What Google said about each job, written onto its lead.

    `refusals` is by index: Google's code ("conversionUploadError.TOO_RECENT_EVENT")
    and message.
    """
    at = now or datetime.now(UTC)
    sent = later = failed = 0
    for i, lead in enumerate(leads):
        if i < len(landed) and landed[i] and i not in refusals:
            lead.upload, lead.upload_note, lead.uploaded_at = "sent", "", at
            sent += 1
            continue
        code, message = refusals.get(i, ("unknown", "Google did not say what happened to it."))
        bare = code.rsplit(".", 1)[-1]
        if bare in ALREADY:
            lead.upload, lead.upload_note, lead.uploaded_at = "sent", "", at
            sent += 1
        elif bare in LATER and not (
            bare in ("EVENT_NOT_FOUND", "CLICK_NOT_FOUND")
            and lead.marked_at
            and at - _aware(lead.marked_at) > NOT_FOUND_FOR
        ):
            lead.upload_note = "Google is not ready for it yet. PPCWay tries again every hour."
            later += 1
        else:
            lead.upload = "failed"
            lead.upload_note = (message or "Google refused it.")[:300]
            failed += 1
    return Outcome(sent=sent, later=later, failed=failed)


def hold_all(leads: list[SiteLead], why: str) -> None:
    """Nothing could be sent (writes are stopped, or the connection needs
    renewing). They stay waiting, with the reason."""
    for lead in leads:
        lead.upload_note = why[:300]


def purge(session: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Delete leads and visits older than `KEEP`. Leads first: they point at visits."""
    before = (now or datetime.now(UTC)) - KEEP
    leads = session.execute(delete(SiteLead).where(SiteLead.created_at < before))
    visits = session.execute(delete(SiteVisit).where(SiteVisit.started_at < before))
    session.commit()
    return {
        "leads": int(getattr(leads, "rowcount", 0) or 0),
        "visits": int(getattr(visits, "rowcount", 0) or 0),
    }
