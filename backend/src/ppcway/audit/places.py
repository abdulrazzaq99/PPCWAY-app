"""Find a business on Google Maps by its name, favouring the town it gave us.

Places API (New) Text Search, not the Business Profile API: that one needs the
owner's own Google sign-in and Google's approval, and its search returns ten at
most. Text Search reads public listings with a server key.

How the search is shaped, and why:
- The query is the name alone. A place written into the query overrides the bias.
- The town becomes a circle the results lean towards (``locationBias``), not a
  fence (``locationRestriction``), so a business of that name elsewhere still
  comes back. Without a bias Google leans towards the caller's IP, our server's.
- ``includePureServiceAreaBusinesses`` is on. It is off by default, and most
  trades (plumbers, electricians, cleaners) hide their address.
- Pages are followed to Google's ceiling of 60.

Rating, reviews, website and phone put every page in the Enterprise SKU: 1,000
free a month, then $35 per 1,000. Google allows keeping only the place ID; the
rest is read fresh when it is shown, with "Google Maps" credited.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

SEARCH_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
DETAILS_ENDPOINT = "https://places.googleapis.com/v1/places/"
GEOCODE_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

#: Google's ceiling for Text Search, and its page size.
MAX_RESULTS = 60
PAGE_SIZE = 20
#: The largest circle locationBias takes.
BIAS_RADIUS_M = 50_000

FIELDS = (
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.shortFormattedAddress",
    "places.location",
    "places.primaryTypeDisplayName",
    "places.businessStatus",
    "places.pureServiceAreaBusiness",
    "places.googleMapsUri",
    "places.rating",
    "places.userRatingCount",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.currentOpeningHours.openNow",
    "places.regularOpeningHours",
    "places.photos",
    "nextPageToken",
)

#: How far a "nearby" comparison looks, and how many rivals it keeps.
RIVAL_RADIUS_M = 15_000
RIVAL_LIMIT = 6


class PlacesError(RuntimeError):
    """Google refused the call. Carries Google's reason, never the key."""


@dataclass(frozen=True)
class Listing:
    place_id: str
    name: str
    address: str
    short_address: str
    category: str
    #: OPERATIONAL, CLOSED_TEMPORARILY or CLOSED_PERMANENTLY; empty when Google has none.
    status: str
    #: True when the business serves customers where they are and shows no address.
    service_area_only: bool
    maps_url: str
    rating: float | None
    reviews: int
    website: str
    phone: str
    open_now: bool | None
    lat: float | None
    lng: float | None
    #: How many photos the listing carries. Google returns at most ten.
    photos: int = 0
    #: True when Google holds opening hours at all.
    hours_set: bool = False
    #: True when a day is open with no closing time, which is how Google says 24 hours.
    open_24h: bool = False
    #: Every word of the name typed is in this listing's name.
    name_match: bool = False


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower().replace("&", " and "))


def names_match(typed: str, listed: str) -> bool:
    """Typed "Alpha Plumbing" matches "Alpha Plumbing & Drains", not "Alpine Plumbing"."""
    want = _words(typed)
    have = set(_words(listed))
    return bool(want) and all(w in have for w in want)


def parse_listing(raw: dict[str, Any], typed: str = "") -> Listing:
    loc = raw.get("location") or {}
    rating = raw.get("rating")
    name = (raw.get("displayName") or {}).get("text", "")
    hours = raw.get("regularOpeningHours") or {}
    periods = hours.get("periods") or []
    # Google says "open 24 hours" by giving a period that opens and never closes.
    always_open = any("close" not in p for p in periods if isinstance(p, dict))
    return Listing(
        place_id=str(raw.get("id", "")),
        name=name,
        address=raw.get("formattedAddress", ""),
        short_address=raw.get("shortFormattedAddress", ""),
        category=(raw.get("primaryTypeDisplayName") or {}).get("text", ""),
        status=raw.get("businessStatus", ""),
        service_area_only=bool(raw.get("pureServiceAreaBusiness", False)),
        maps_url=raw.get("googleMapsUri", ""),
        rating=float(rating) if isinstance(rating, (int, float)) else None,
        reviews=int(raw.get("userRatingCount") or 0),
        website=raw.get("websiteUri", ""),
        phone=raw.get("nationalPhoneNumber", ""),
        open_now=(raw.get("currentOpeningHours") or {}).get("openNow"),
        lat=loc.get("latitude"),
        lng=loc.get("longitude"),
        photos=len(raw.get("photos") or []),
        hours_set=bool(periods or hours.get("weekdayDescriptions")),
        open_24h=always_open,
        name_match=names_match(typed, name) if typed else False,
    )


def rank(listings: list[Listing]) -> list[Listing]:
    """Name matches first, each group in Google's order, which already leans towards the town."""
    return sorted(listings, key=lambda li: not li.name_match)


def _refusal(response: httpx.Response) -> PlacesError:
    try:
        err = response.json().get("error") or {}
        reason = err.get("message") or err.get("status") or response.reason_phrase
    except ValueError:
        reason = response.reason_phrase
    return PlacesError(f"Places {response.status_code}: {reason}")


def geocode(
    place: str, *, api_key: str, region: str = "ca", client: httpx.Client | None = None
) -> tuple[float, float] | None:
    """The centre of a town, or None when Google does not know it.

    Geocoding takes the key in the query string, so a refusal is reported by status
    alone: httpx's own error would quote the URL, key and all.
    """
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(15))
    try:
        response = c.get(
            GEOCODE_ENDPOINT, params={"address": place, "region": region, "key": api_key}
        )
        if response.status_code != 200:
            raise _refusal(response)
        body = response.json()
    finally:
        if own:
            c.close()
    status = body.get("status")
    if status == "ZERO_RESULTS":
        return None
    if status != "OK":
        raise PlacesError(f"Geocoding {status}: {body.get('error_message', '')}".rstrip(": "))
    at = body["results"][0]["geometry"]["location"]
    return float(at["lat"]), float(at["lng"])


def search_body(
    name: str, near: tuple[float, float] | None, region: str, page_token: str | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "textQuery": name,
        "pageSize": PAGE_SIZE,
        "includePureServiceAreaBusinesses": True,
        "regionCode": region,
    }
    if near is not None:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": near[0], "longitude": near[1]},
                "radius": float(BIAS_RADIUS_M),
            }
        }
    if page_token:
        body["pageToken"] = page_token
    return body


def details_mask() -> str:
    """The same fields, named as one place rather than a page of them."""
    return ",".join(f[len("places.") :] for f in FIELDS if f.startswith("places."))


def place_details(
    place_id: str, *, api_key: str, client: httpx.Client | None = None
) -> Listing | None:
    """One listing by its Google id, or None when Google no longer has it.

    The id is the only part of a listing we are allowed to keep, so the screen that
    shows a chosen business reads it again here rather than trusting a stored copy.
    """
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(15))
    try:
        response = c.get(
            DETAILS_ENDPOINT + place_id,
            headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": details_mask()},
        )
        # 404 is an id Google has dropped; 400 is an id that was never one of its
        # own. Both mean the same to a screen: there is no listing to show.
        if response.status_code in (400, 404):
            return None
        if response.status_code != 200:
            raise _refusal(response)
        return parse_listing(response.json())
    finally:
        if own:
            c.close()


def nearby_rivals(
    listing: Listing,
    *,
    api_key: str,
    city: str = "",
    limit: int = RIVAL_LIMIT,
    region: str = "ca",
    client: httpx.Client | None = None,
) -> list[Listing]:
    """The same trade within 15 km of this business, itself left out.

    The comparison the report draws is the honest part of "who you are up against":
    it says who Google shows beside them, never who is advertising, which no public
    source knows.

    A business that serves an area has no coordinates: Google publishes none for a
    trade that hides its address, which is most of them. The town they typed is the
    anchor then. Without either, this returns nothing rather than searching with no
    anchor at all, which lands on whatever the server's own address is.
    """
    if not listing.category:
        return []
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(15))
    try:
        near: tuple[float, float] | None = None
        if listing.lat is not None and listing.lng is not None:
            near = (listing.lat, listing.lng)
        elif city.strip():
            near = geocode(city, api_key=api_key, region=region, client=c)
        if near is None:
            return []
        body = search_body(listing.category, near, region)
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": near[0], "longitude": near[1]},
                "radius": float(RIVAL_RADIUS_M),
            }
        }
        response = c.post(
            SEARCH_ENDPOINT,
            json=body,
            headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": ",".join(FIELDS)},
        )
        if response.status_code != 200:
            raise _refusal(response)
        found = [parse_listing(p) for p in response.json().get("places") or []]
    finally:
        if own:
            c.close()
    return [li for li in found if li.place_id != listing.place_id][:limit]


def find_businesses(
    name: str,
    *,
    api_key: str,
    city: str = "",
    region: str = "ca",
    max_results: int = MAX_RESULTS,
    client: httpx.Client | None = None,
) -> list[Listing]:
    """Every listing Google returns for the name, up to 60, the town's first."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(15))
    try:
        near = geocode(city, api_key=api_key, region=region, client=c) if city.strip() else None
        headers = {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": ",".join(FIELDS)}
        found: list[Listing] = []
        token: str | None = None
        while len(found) < max_results:
            response = c.post(
                SEARCH_ENDPOINT, json=search_body(name, near, region, token), headers=headers
            )
            if response.status_code != 200:
                raise _refusal(response)
            body = response.json()
            found.extend(parse_listing(p, name) for p in body.get("places") or [])
            token = body.get("nextPageToken")
            if not token:
                break
        return rank(found[:max_results])
    finally:
        if own:
            c.close()
