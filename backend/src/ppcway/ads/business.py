"""What we already know about the business behind a connected account.

Asking somebody to type their business name and website, moments after they
handed us the Google Ads account that advertises that business, is asking them
to tell us what we were just told. It also lets the two disagree: we once
printed one website's audit beside another business's spending, under the first
one's name, and it read as nonsense because it was.

So this works it out instead:

- **the name** is the account's own, which Google keeps as its descriptive name;
- **the website** is where the live ads actually send people, which beats
  anything typed, because it is where the money lands;
- **the Google listing** is looked up on Maps and only taken as certain when its
  website matches the one the ads use. A listing we are unsure of is offered for
  the person to pick, never assumed.

Nothing here guesses silently. Every field says where it came from, so the
screen can show its working and the person can correct any of it.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import MirrorAd
from ppcway.audit.places import Listing, PlacesError, find_businesses

log = logging.getLogger(__name__)

#: How many listings to offer when we cannot be sure which one it is.
OFFER = 5


@dataclass
class Known:
    """What the connected account tells us, and how certain each part is."""

    customer_id: str = ""
    name: str = ""
    site: str = ""
    place_id: str = ""
    listing_name: str = ""
    city: str = ""
    trade: str = ""
    #: True when the listing's own website is the one the ads send people to.
    #: False means the listing is a suggestion and the person should confirm it.
    sure: bool = False
    #: Offered when we could not be sure, so the screen can ask rather than guess.
    choices: list[dict[str, str]] = field(default_factory=list)
    #: Where each part came from, in words a screen can print.
    whence: dict[str, str] = field(default_factory=dict)

    @property
    def enough(self) -> bool:
        """Enough to offer, which is not the same as enough to run.

        The ads usually give us the website. When they do not — a brand new
        account, or one whose ads are all paused — a listing on Maps carries
        one, so the question becomes "which of these is you?" rather than
        "type your website address".
        """
        if not self.name:
            return False
        return bool(self.site) or any(one.get("website") for one in self.choices)

    def as_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "site": self.site,
            "place_id": self.place_id,
            "listing_name": self.listing_name,
            "city": self.city,
            "trade": self.trade,
            "sure": self.sure,
            "enough": self.enough,
            "choices": self.choices,
            "whence": self.whence,
        }


def host_of(url: str) -> str:
    """The bare host of an address, without www and without a scheme."""
    raw = url.strip()
    if not raw:
        return ""
    if "//" not in raw:
        raw = f"https://{raw}"
    host = (urlparse(raw).hostname or "").lower()
    return host.removeprefix("www.")


def site_from_ads(session: Session, customer_id: str) -> str:
    """The host the live ads send people to, when they agree on one.

    An account can advertise more than one site; the one most of its ads point
    at is the business being advertised, and the rest are worth nobody's guess.
    """
    hosts: Counter[str] = Counter()
    ads = session.scalars(
        select(MirrorAd).where(MirrorAd.customer_id == customer_id, MirrorAd.gone_at.is_(None))
    )
    for ad in ads:
        for raw in ad.final_urls or []:
            host = host_of(str(raw))
            if host:
                hosts[host] += 1
    if not hosts:
        return ""
    return hosts.most_common(1)[0][0]


def _town(listing: Listing) -> str:
    """The town a listing is in, as Google writes it on the short address."""
    short = (listing.short_address or "").strip()
    if short and "," in short:
        return short.rsplit(",", 1)[1].strip()
    if short:
        return short
    parts = [p.strip() for p in (listing.address or "").split(",") if p.strip()]
    # "123 Main St, Mississauga, ON L5B 1M2, Canada": the town is third from last.
    return parts[-3] if len(parts) >= 3 else ""


def _as_choice(listing: Listing) -> dict[str, str]:
    return {
        "place_id": listing.place_id,
        "name": listing.name,
        "address": listing.short_address or listing.address,
        "website": listing.website,
        "category": listing.category,
    }


def known_business(
    session: Session,
    *,
    customer_id: str,
    account_name: str = "",
    maps_key: str = "",
    client: httpx.Client | None = None,
) -> Known:
    """Everything the connected account can tell us about its own business."""
    known = Known(customer_id=customer_id, name=account_name.strip())
    if known.name:
        known.whence["name"] = "the name on your Google Ads account"

    known.site = site_from_ads(session, customer_id)
    if known.site:
        known.whence["site"] = "the pages your ads send people to"

    if not known.name and known.site:
        # An account with no name of its own: the domain is a better label than
        # nothing, and the person can correct it.
        known.name = known.site.split(".")[0]
        known.whence["name"] = "your website address"

    if not maps_key or not (known.name or known.site):
        return known

    try:
        found = find_businesses(known.name or known.site, api_key=maps_key, client=client)
    except PlacesError as exc:
        log.warning("could not look up %r on Maps: %s", known.name, exc)
        return known

    matched = next(
        (one for one in found if known.site and host_of(one.website) == known.site), None
    )
    if matched is not None:
        known.place_id = matched.place_id
        known.listing_name = matched.name
        known.city = _town(matched)
        known.trade = matched.category
        known.sure = True
        known.whence["listing"] = "Google Maps, matched on your website address"
        return known

    known.choices = [_as_choice(one) for one in found[:OFFER]]
    if known.choices:
        known.whence["listing"] = (
            "Google Maps, by name — tell us which one is yours"
            if known.site
            else "Google Maps, by name — your ads do not say which website yet"
        )
    return known
