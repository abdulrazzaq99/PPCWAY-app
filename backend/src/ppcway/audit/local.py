"""Local presence: one phone number everywhere, a local area code, an address,
a map, and the service area named. Read from the crawl and the render."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

PHONE = re.compile(r"(?:\+?1[\s.-]?)?\(?([2-9]\d{2})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})")
#: Canadian area codes to the region people know them by.
AREA_CODES = {
    "416": "Toronto", "647": "Toronto", "437": "Toronto", "905": "Toronto suburbs (Peel, York, Durham, Halton)",
    "289": "Toronto suburbs", "365": "Toronto suburbs", "742": "Toronto suburbs", "613": "Ottawa", "343": "Ottawa",
    "519": "Southwestern Ontario", "226": "Southwestern Ontario", "548": "Southwestern Ontario", "705": "Northern Ontario",
    "249": "Northern Ontario", "807": "Northwestern Ontario", "514": "Montreal", "438": "Montreal", "450": "Montreal suburbs",
    "579": "Montreal suburbs", "418": "Quebec City", "581": "Quebec City", "819": "Western Quebec", "873": "Western Quebec",
    "604": "Vancouver", "778": "British Columbia", "236": "British Columbia", "250": "British Columbia", "403": "Calgary",
    "587": "Alberta", "825": "Alberta", "780": "Edmonton", "306": "Saskatchewan", "639": "Saskatchewan", "204": "Manitoba",
    "431": "Manitoba", "902": "Nova Scotia and PEI", "782": "Nova Scotia and PEI", "506": "New Brunswick", "709": "Newfoundland",
    "867": "The territories",
}
TOLL_FREE = {"800", "833", "844", "855", "866", "877", "888"}
PREMIUM = {"900", "976"}
SERVICE_AREA = re.compile(r"\b(serving|we serve|service area|proudly serving|across|throughout)\b[^.]{0,120}", re.IGNORECASE)


@dataclass
class LocalSignals:
    numbers: list[str] = field(default_factory=list)
    #: The number that appears most, formatted.
    main_number: str = ""
    area_code: str = ""
    region: str = ""
    toll_free: bool = False
    premium: bool = False
    #: The phone number differs between pages.
    inconsistent: bool = False
    maps_embed: bool = False
    service_area: str = ""
    address: str = ""


def _format(m: re.Match[str]) -> str:
    return f"({m.group(1)}) {m.group(2)}-{m.group(3)}"


def detect_local(page_texts: list[str], *, address: str, maps_embed: bool, tel_links: list[str]) -> LocalSignals:
    counts: Counter[str] = Counter()
    for text in page_texts:
        for m in PHONE.finditer(text):
            counts[_format(m)] += 1
    for link in tel_links:
        m = PHONE.search(link)
        if m:
            counts[_format(m)] += 1
    out = LocalSignals(address=address, maps_embed=maps_embed)
    out.numbers = [n for n, _ in counts.most_common()]
    if out.numbers:
        out.main_number = out.numbers[0]
        out.area_code = out.main_number[1:4]
        out.region = AREA_CODES.get(out.area_code, "")
        out.toll_free = out.area_code in TOLL_FREE
        out.premium = out.area_code in PREMIUM
        # Two numbers that both appear often is fine (office and emergency); five is a mess.
        out.inconsistent = len([n for n, c in counts.items() if c >= 2]) > 2
    joined = " ".join(page_texts)
    m = SERVICE_AREA.search(joined)
    if m:
        out.service_area = m.group(0).strip()[:140]
    return out
