"""What the Website screen shows: visits, where they came from, and the leads.

Counted from PPCWay's own record of the merchant's site, not from Google, so it
includes the visits Google Ads never sees -- the searches, the social posts,
the people who typed the address -- and it answers the question a merchant
actually asks: of the people who came, how many got in touch, and from where.

Days are the Google Ads account's days when there is an account, so a visit at
11 pm in Toronto is counted on the day the merchant lived through.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.site.collect import SOURCE_LABEL
from ppcway.site.models import SiteLead, SiteVisit

STATUSES = ("new", "job", "not_job", "spam")


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name) if name else ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _aware(when: datetime) -> datetime:
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def overview(
    session: Session,
    organization_id: uuid.UUID,
    *,
    days: int = 30,
    time_zone: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Visits and leads over the last `days` days, by day, by source and by page."""
    at = now or datetime.now(UTC)
    zone = _zone(time_zone)
    today = at.astimezone(zone).date()
    first = today - timedelta(days=days - 1)
    since = datetime.combine(first, datetime.min.time(), tzinfo=zone).astimezone(UTC)

    visits = session.execute(
        select(SiteVisit.id, SiteVisit.started_at, SiteVisit.source, SiteVisit.landing).where(
            SiteVisit.organization_id == organization_id, SiteVisit.started_at >= since
        )
    ).all()
    leads = session.execute(
        select(
            SiteLead.created_at,
            SiteLead.source,
            SiteLead.page,
            SiteLead.kind,
            SiteLead.status,
            SiteLead.value,
        ).where(
            SiteLead.organization_id == organization_id,
            SiteLead.created_at >= since,
            SiteLead.status != "spam",
        )
    ).all()

    def day_of(when: datetime) -> date:
        return _aware(when).astimezone(zone).date()

    by_day: dict[date, list[int]] = {first + timedelta(days=n): [0, 0] for n in range(days)}
    by_source: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_page: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for _, started, source, landing in visits:
        d = day_of(started)
        if d in by_day:
            by_day[d][0] += 1
        by_source[source][0] += 1
        by_page[landing or "/"][0] += 1
    kinds: Counter[str] = Counter()
    jobs = 0
    worth = 0.0
    for created, source, page, kind, status, value in leads:
        d = day_of(created)
        if d in by_day:
            by_day[d][1] += 1
        by_source[source][1] += 1
        by_page[page or "/"][1] += 1
        kinds[kind] += 1
        if status == "job":
            jobs += 1
            worth += float(value or 0)

    sources: list[dict[str, Any]] = [
        {
            "source": s,
            "label": SOURCE_LABEL.get(s, s.replace("_", " ").title()),
            "visits": v,
            "leads": n,
        }
        for s, (v, n) in by_source.items()
    ]
    sources.sort(key=lambda row: (-row["visits"], -row["leads"]))
    pages: list[dict[str, Any]] = [
        {"page": p, "visits": v, "leads": n} for p, (v, n) in by_page.items()
    ]
    pages.sort(key=lambda row: (-row["visits"], -row["leads"]))

    total_visits = len(visits)
    total_leads = len(leads)
    return {
        "days": days,
        "visits": total_visits,
        "leads": total_leads,
        "rate": round(total_leads / total_visits * 100, 1) if total_visits else None,
        "kinds": {k: kinds.get(k, 0) for k in ("form", "call", "email")},
        "jobs": jobs,
        "jobs_value": round(worth, 2),
        "by_day": [
            {"day": d.isoformat(), "visits": v, "leads": n} for d, (v, n) in sorted(by_day.items())
        ],
        "sources": sources,
        "pages": pages[:10],
    }


def lead_list(
    session: Session,
    organization_id: uuid.UUID,
    *,
    status: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """The newest leads first, as the Website screen lists them."""
    query = select(SiteLead).where(SiteLead.organization_id == organization_id)
    if status in STATUSES:
        query = query.where(SiteLead.status == status)
    else:
        # Spam is out of sight unless asked for.
        query = query.where(SiteLead.status != "spam")
    rows = session.scalars(query.order_by(SiteLead.created_at.desc()).limit(min(limit, 200))).all()
    return [as_dict(lead) for lead in rows]


def as_dict(lead: SiteLead) -> dict[str, Any]:
    return {
        "id": str(lead.id),
        "created_at": _aware(lead.created_at).isoformat(),
        "kind": lead.kind,
        "page": lead.page,
        "form": lead.form,
        "fields": lead.fields or [],
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "source": lead.source,
        "source_label": SOURCE_LABEL.get(lead.source, lead.source),
        "campaign": lead.campaign,
        "from_ad": bool(lead.gclid or lead.gbraid or lead.wbraid),
        "status": lead.status,
        "value": lead.value,
        "currency": lead.currency,
        "upload": lead.upload,
        "upload_note": lead.upload_note,
    }
