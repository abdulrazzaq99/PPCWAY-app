"""What day it is for an advertising account, which is not what day it is in UTC.

Google keeps an account's figures in the account's own time zone: its days run
midnight to midnight in that zone, and its own "last 30 days" ends at the
account's yesterday. Until 6 November every window here ended at the UTC
yesterday instead, so the screens turned the day over at an hour that meant
nothing to the merchant -- seven in the evening in Toronto, five in the
morning in Karachi -- and the hourly read asked Google for a day that had not
started in the account yet.

So "today" for an account's figures is the date in the account's time zone,
read from Google when the account is chosen and on every structure read. An
account whose zone we have not read yet, or a zone Python does not know, is
dated in UTC as before: a wrong guess at a zone would be worse than the old
behaviour.

Timestamps -- when a figure was read, when a change was made -- stay in UTC.
Only the calendar date an account's figures are filed under follows its zone.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, tzinfo
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.models import AdsConnection


@lru_cache(maxsize=64)
def zone(name: str) -> tzinfo:
    """The time zone Google named, such as "America/Toronto", or UTC."""
    if not name:
        return UTC
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def local_today(time_zone: str, now: datetime | None = None) -> date:
    """The date it is now in that time zone."""
    at = now or datetime.now(UTC)
    at = at if at.tzinfo else at.replace(tzinfo=UTC)
    return at.astimezone(zone(time_zone)).date()


def zone_of(session: Session, customer_id: str) -> str:
    """The time zone held for an account, or empty where none has been read.

    Any connection to the account will do: one Google Ads account has one time
    zone however many businesses are connected to it.
    """
    if not customer_id:
        return ""
    found = session.scalar(
        select(AdsConnection.time_zone)
        .where(AdsConnection.customer_id == customer_id, AdsConnection.time_zone != "")
        .limit(1)
    )
    return str(found or "")


def account_today(session: Session, customer_id: str, now: datetime | None = None) -> date:
    """The date it is now for this account's figures."""
    return local_today(zone_of(session, customer_id), now)
