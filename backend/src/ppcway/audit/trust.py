"""Trust signals: licence, reviews, address, hours and a privacy policy, where
people look for them. Read from structured data first, then the visible text."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from selectolax.parser import HTMLParser

# A licence NUMBER: the word, then an identifier with at least one digit in it.
# "Licensed and insured" alone is a claim, counted under INSURED, not a licence.
LICENCE = re.compile(
    r"\b(licen[cs]e[d]?|lic\.?|tssa|ecra|esa|hrai|wsib|cpso|rcdso|contractor)\s*(no\.?|number|#|:)?\s*#?\s*((?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{3,})",
    re.IGNORECASE,
)
INSURED = re.compile(r"\b(insured|bonded|licen[cs]ed)\b", re.IGNORECASE)
HOURS = re.compile(
    r"\b(mon(day)?|tue(sday)?|wed(nesday)?|thu(rsday)?|fri(day)?|sat(urday)?|sun(day)?)\b[^\n]{0,40}\b\d{1,2}(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)?\s*(-|–|to)\s*\d{1,2}",
    re.IGNORECASE,
)
OPEN_24 = re.compile(r"\b(24/7|24 hours|open 24)\b", re.IGNORECASE)
REVIEW_WORDS = re.compile(r"\b(\d+(\.\d)?)\s*(stars?|/5|out of 5)\b|\b(\d{2,5})\+?\s*reviews\b|google reviews", re.IGNORECASE)
REVIEW_WIDGETS = ("trustindex", "birdeye", "reviewsonmywebsite", "elfsight", "trustpilot", "homestars", "nicejob", "podium")
PRIVACY = re.compile(r"privacy", re.IGNORECASE)


@dataclass(frozen=True)
class TrustSignals:
    address: str
    hours: bool
    licence: str
    insured: bool
    reviews: str
    privacy_policy: bool
    #: JSON-LD LocalBusiness (or a subtype) was present.
    structured_local_business: bool


def _json_ld(tree: HTMLParser) -> list[dict]:  # type: ignore[type-arg]
    out: list[dict] = []  # type: ignore[type-arg]
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(node.text() or "")
        except ValueError:
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                out.append(item)
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
    return out


def detect_trust(pages: list[tuple[str, str]], *, address: str, page_text: str, links: list[str]) -> TrustSignals:
    hours = bool(HOURS.search(page_text) or OPEN_24.search(page_text))
    licence_match = LICENCE.search(page_text)
    licence = licence_match.group(0).strip() if licence_match else ""
    insured = bool(INSURED.search(page_text))
    reviews = ""
    structured = False
    for _url, html in pages:
        tree = HTMLParser(html)
        lowered = html.lower()
        for obj in _json_ld(tree):
            t = obj.get("@type")
            types = t if isinstance(t, list) else [t]
            if any(isinstance(x, str) and ("LocalBusiness" in x or x in ("Plumber", "Dentist", "HVACBusiness", "Electrician", "RoofingContractor", "HomeAndConstructionBusiness", "Locksmith", "MovingCompany", "AutoRepair", "LegalService", "Attorney")) for x in types):
                structured = True
            if "openingHours" in obj or "openingHoursSpecification" in obj:
                hours = True
            rating = obj.get("aggregateRating")
            if isinstance(rating, dict) and not reviews:
                reviews = f"{rating.get('ratingValue', '?')} stars from {rating.get('reviewCount') or rating.get('ratingCount') or '?'} reviews (structured data)"
        if not reviews:
            widget = next((w for w in REVIEW_WIDGETS if w in lowered), None)
            if widget:
                reviews = f"a {widget} review widget"
    if not reviews:
        m = REVIEW_WORDS.search(page_text)
        if m:
            reviews = m.group(0)
    privacy = any(PRIVACY.search(l) for l in links) or bool(re.search(r"privacy policy", page_text, re.IGNORECASE))
    return TrustSignals(
        address=address,
        hours=hours,
        licence=licence,
        insured=insured,
        reviews=reviews,
        privacy_policy=privacy,
        structured_local_business=structured,
    )
