"""Taking in what the PPCWay script reports from a merchant's website.

The script sends two kinds of event: a page was viewed, and somebody got in
touch (a form sent, a phone number or email address tapped). Both arrive at a
public endpoint, from any browser, carrying a key anybody can read in the
page source. So nothing here trusts the event, and what one can do is small:

- an unknown key, a robot, or an address that is not a web page is dropped
  without a word, so the endpoint tells a scanner nothing;
- a business takes at most `MOST_LEADS_AN_HOUR` leads an hour, one sender at
  most `MOST_FROM_ONE_SENDER`, one visit at most `MOST_PER_VISIT`, so a key
  copied out of a page cannot bury the merchant's real leads;
- what a form held is cut to `MOST_FIELDS` fields of `LONGEST_VALUE`
  characters, and anything that looks like a password or a card number is
  never kept at all, whatever the form called it.

Where a visit came from is decided here, once, from the first page's address
and referrer, and copied onto any lead it makes: an ad click (it carries
Google's click id), a search, social, email, another site, or nobody knows.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ppcway.site.models import SiteKey, SiteLead, SiteVisit

MOST_LEADS_AN_HOUR = 60
MOST_FROM_ONE_SENDER = 10
MOST_PER_VISIT = 5
MOST_FIELDS = 25
LONGEST_VALUE = 1000
#: A visit stops counting page views here; past it, something is looping.
MOST_VIEWS = 500
#: The same tap or the same form twice within this is one lead, not two.
SAME_LEAD_WITHIN = timedelta(minutes=10)

KINDS = ("form", "call", "email")

#: What each source is called on the Website screen.
SOURCE_LABEL = {
    "google_ads": "Google Ads",
    "google": "Google search",
    "microsoft_ads": "Microsoft Ads",
    "bing": "Bing search",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "email": "Email",
    "referral": "Other websites",
    "direct": "Typed in or bookmarked",
    "other": "Other",
}

_ROBOT = re.compile(
    r"bot|crawl|spider|slurp|headless|lighthouse|preview|monitor|python|curl|wget", re.IGNORECASE
)
#: Fields never kept, whatever the form called them.
_NEVER = re.compile(
    r"pass(word)?|pwd|card|cc-?num|ccnum|cvv|cvc|csc|expir|iban|routing|"
    r"account.?number|\bsin\b|\bssn\b|social.?insurance|social.?security",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_DIGITS = re.compile(r"\d")
#: Thirteen to nineteen digits in a row, spaced or not: a card number typed
#: into a field called something innocent. Dropped.
_CARD = re.compile(r"(?:\d[ -]?){13,19}")


@dataclass(frozen=True)
class Event:
    """One event, as the script sent it, cut to size."""

    key: str
    type: str
    visit: str
    visitor: str
    url: str
    referrer: str = ""
    device: str = ""
    kind: str = ""
    form: str = ""
    href: str = ""
    fields: list[tuple[str, str]] = field(default_factory=list)
    #: The browser asked not to be tracked (Global Privacy Control). The lead
    #: is still counted; what was typed is not kept.
    private: bool = False


def _text(raw: Any, most: int) -> str:
    return str(raw if raw is not None else "").strip()[:most]


def parse(raw: Any) -> Event | None:
    """The event, or None when it is not one worth reading."""
    if not isinstance(raw, dict):
        return None
    kind = _text(raw.get("t"), 10)
    if kind not in ("view", "lead"):
        return None
    url = _text(raw.get("url"), 2000)
    if not url.startswith(("http://", "https://")):
        return None
    visit = re.sub(r"[^A-Za-z0-9_-]", "", _text(raw.get("v"), 40))
    if len(visit) < 8:
        return None
    fields: list[tuple[str, str]] = []
    for pair in raw.get("f") or []:
        if len(fields) >= MOST_FIELDS:
            break
        if isinstance(pair, list | tuple) and len(pair) == 2:
            label, value = _text(pair[0], 100), _text(pair[1], LONGEST_VALUE)
            if value:
                fields.append((label, value))
    lead_kind = _text(raw.get("k"), 10)
    if kind == "lead" and lead_kind not in KINDS:
        return None
    return Event(
        key=_text(raw.get("key"), 40),
        type=kind,
        visit=visit,
        visitor=re.sub(r"[^A-Za-z0-9_-]", "", _text(raw.get("u"), 40)),
        url=url,
        referrer=_text(raw.get("r"), 2000),
        device=_text(raw.get("d"), 10) if raw.get("d") in ("mobile", "tablet", "desktop") else "",
        kind=lead_kind,
        form=_text(raw.get("n"), 100),
        href=_text(raw.get("h"), 300),
        fields=fields,
        private=bool(raw.get("p")),
    )


def new_key() -> str:
    """A key for the script tag. Public, so only long enough not to be guessed."""
    return f"pw_{secrets.token_urlsafe(15)}"


def key_for(session: Session, organization_id: uuid.UUID) -> SiteKey:
    """This business's script key, made the first time it is asked for."""
    held = session.scalar(select(SiteKey).where(SiteKey.organization_id == organization_id))
    if held is None:
        held = SiteKey(organization_id=organization_id, key=new_key())
        session.add(held)
        session.commit()
    return held


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _path(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    return (parts.path or "/")[:500]


def where_from(url: str, referrer: str) -> dict[str, str]:
    """Where a visit came from, read off its first page's address and referrer."""
    try:
        query = {k.lower(): v[0] for k, v in parse_qs(urlsplit(url).query).items() if v}
    except ValueError:
        query = {}
    out = {
        "gclid": query.get("gclid", "")[:200],
        "gbraid": query.get("gbraid", "")[:200],
        "wbraid": query.get("wbraid", "")[:200],
        "campaign": query.get("utm_campaign", "")[:100],
    }
    utm_source = query.get("utm_source", "").lower()
    medium = query.get("utm_medium", "").lower()
    came = _host(referrer)
    own = _host(url)

    if out["gclid"] or out["gbraid"] or out["wbraid"]:
        source = "google_ads"
    elif query.get("msclkid"):
        source = "microsoft_ads"
    elif medium in ("cpc", "ppc", "paid", "paidsearch", "paid_search") and "google" in utm_source:
        source = "google_ads"
    elif query.get("fbclid") or utm_source in ("facebook", "fb"):
        source = "facebook"
    elif utm_source in ("instagram", "ig"):
        source = "instagram"
    elif medium == "email" or utm_source in ("newsletter", "email"):
        source = "email"
    elif not came or came == own:
        source = "direct"
    elif re.search(r"(^|\.)google\.[a-z.]+$", came):
        source = "google"
    elif came.endswith("bing.com"):
        source = "bing"
    elif came.endswith(("facebook.com", "fb.com", "fb.me")):
        source = "facebook"
    elif came.endswith("instagram.com"):
        source = "instagram"
    elif any(mail in came for mail in ("mail.", "outlook.", "gmail")):
        source = "email"
    else:
        source = "referral"
    out["source"] = source
    out["referrer"] = "" if came == own else came[:200]
    return out


def sender_of(address: str, organization_id: uuid.UUID) -> str:
    """Who sent it, as a hash tied to this business: countable, not readable."""
    return hashlib.sha256(f"{address}|{organization_id}".encode()).hexdigest()


def is_robot(user_agent: str) -> bool:
    return not user_agent or bool(_ROBOT.search(user_agent))


def kept_fields(fields: list[tuple[str, str]]) -> list[list[str]]:
    """The fields worth keeping: never a password, never a card number."""
    out: list[list[str]] = []
    for label, value in fields:
        if _NEVER.search(label) or _CARD.fullmatch(value.strip()):
            continue
        out.append([label, value])
    return out


def picked(fields: list[list[str]]) -> dict[str, str]:
    """A name, an email address and a phone number, picked out of the fields."""
    name = first = last = email = phone = ""
    for label, value in fields:
        low = label.lower()
        if not email and _EMAIL.match(value):
            email = value
        elif not phone and (
            any(w in low for w in ("phone", "tel", "mobile", "cell"))
            or (re.fullmatch(r"[\d\s().+-]{7,20}", value) and 7 <= len(_DIGITS.findall(value)))
        ):
            phone = value
        elif "name" in low and not any(w in low for w in ("company", "business", "user", "file")):
            if "first" in low or "given" in low:
                first = value
            elif "last" in low or "sur" in low or "family" in low:
                last = value
            elif not name:
                name = value
    if not name:
        name = " ".join(part for part in (first, last) if part)
    return {"name": name[:200], "email": email[:320], "phone": phone[:40]}


def _from_link(href: str) -> dict[str, str]:
    low = href.lower()
    if low.startswith("tel:"):
        return {"phone": href[4:].split("?")[0][:40]}
    if low.startswith("mailto:"):
        return {"email": href[7:].split("?")[0][:320]}
    return {}


def take(
    session: Session,
    event: Event,
    *,
    address: str,
    user_agent: str,
    now: datetime | None = None,
) -> str:
    """Record one event. Says what happened, for the logs: never for the sender."""
    at = now or datetime.now(UTC)
    if is_robot(user_agent):
        return "robot"
    site = session.scalar(select(SiteKey).where(SiteKey.key == event.key)) if event.key else None
    if site is None:
        return "unknown key"
    org = site.organization_id

    visit = session.scalar(
        select(SiteVisit).where(SiteVisit.organization_id == org, SiteVisit.visit == event.visit)
    )
    if visit is None:
        came = where_from(event.url, event.referrer)
        visit = SiteVisit(
            organization_id=org,
            visit=event.visit,
            visitor=event.visitor,
            started_at=at,
            last_at=at,
            landing=_path(event.url),
            referrer=came["referrer"],
            source=came["source"],
            campaign=came["campaign"],
            gclid=came["gclid"],
            gbraid=came["gbraid"],
            wbraid=came["wbraid"],
            device=event.device,
            views=1 if event.type == "view" else 0,
        )
        session.add(visit)
    else:
        if event.type == "view" and visit.views < MOST_VIEWS:
            visit.views += 1
        visit.last_at = at
        if not (visit.gclid or visit.gbraid or visit.wbraid):
            # An ad click that arrives on a later page of the same visit (the
            # first page was served from a cache, say) still makes it an ad visit.
            came = where_from(event.url, "")
            if came["source"] == "google_ads":
                visit.source = "google_ads"
                visit.gclid, visit.gbraid, visit.wbraid = (
                    came["gclid"],
                    came["gbraid"],
                    came["wbraid"],
                )
                visit.campaign = visit.campaign or came["campaign"]
    site.last_seen_at = at
    site.last_seen_url = event.url[:500]
    session.flush()

    if event.type != "lead":
        session.commit()
        return "view"

    said = _limited(session, org, visit, address, at)
    if said:
        session.commit()
        return said

    kept = [] if event.private else kept_fields(event.fields)
    who = picked(kept) if event.kind == "form" else _from_link(event.href)
    if _repeat(session, org, visit, event, kept, at):
        session.commit()
        return "repeat"
    session.add(
        SiteLead(
            organization_id=org,
            visit_id=visit.id,
            created_at=at,
            kind=event.kind,
            page=_path(event.url),
            form=event.form,
            fields=kept,
            name=who.get("name", ""),
            email=who.get("email", ""),
            phone=who.get("phone", ""),
            source=visit.source,
            campaign=visit.campaign,
            gclid=visit.gclid,
            gbraid=visit.gbraid,
            wbraid=visit.wbraid,
            clicked_at=visit.started_at if (visit.gclid or visit.gbraid or visit.wbraid) else None,
            sender=sender_of(address, org),
        )
    )
    session.commit()
    return "lead"


def _limited(session: Session, org: uuid.UUID, visit: SiteVisit, address: str, at: datetime) -> str:
    hour_ago = at - timedelta(hours=1)

    def count(*where: Any) -> int:
        return session.scalar(select(func.count()).select_from(SiteLead).where(*where)) or 0

    if count(SiteLead.organization_id == org, SiteLead.created_at > hour_ago) >= MOST_LEADS_AN_HOUR:
        return "business limit"
    if (
        count(
            SiteLead.organization_id == org,
            SiteLead.sender == sender_of(address, org),
            SiteLead.created_at > hour_ago,
        )
        >= MOST_FROM_ONE_SENDER
    ):
        return "sender limit"
    if count(SiteLead.visit_id == visit.id) >= MOST_PER_VISIT:
        return "visit limit"
    return ""


def _repeat(
    session: Session,
    org: uuid.UUID,
    visit: SiteVisit,
    event: Event,
    kept: list[list[str]],
    at: datetime,
) -> bool:
    """The same tap, or the same form with the same words, moments ago."""
    recent = session.scalars(
        select(SiteLead).where(
            SiteLead.organization_id == org,
            SiteLead.visit_id == visit.id,
            SiteLead.kind == event.kind,
            SiteLead.created_at > at - SAME_LEAD_WITHIN,
        )
    ).all()
    for lead in recent:
        if event.kind == "form" and lead.fields == kept and lead.form == event.form:
            return True
        if event.kind != "form" and _from_link(event.href) == {
            k: v for k, v in (("phone", lead.phone), ("email", lead.email)) if v
        }:
            return True
    return False
