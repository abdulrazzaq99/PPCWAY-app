"""Words Google may object to, found on the site before they reach an ad.

The same lists the ad validator uses, pointed at the merchant's page text. A hit
here is "ours": we keep the phrase out of the ads. A destination problem (the site
itself would be refused) is "needs you".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Kept in step with the validator's lexicons; the validator is the owner.
SUPERLATIVES = frozenset(
    {"best", "#1", "number one", "cheapest", "lowest price", "top rated", "unbeatable",
     "guaranteed", "fastest", "most trusted"}
)
RESTRICTED_CLAIMS = {
    "promises a medical result": frozenset({"cure", "cures", "clinically proven", "pain free", "miracle"}),
    "promises a lending outcome": frozenset({"loan approval", "no credit check", "instant approval", "debt free"}),
    "promises a legal outcome": frozenset({"win your case", "no win no fee", "settlement guaranteed"}),
}


@dataclass(frozen=True)
class PolicyHit:
    phrase: str
    family: str
    context: str


def _context(text: str, start: int, end: int, width: int = 60) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    snippet = text[left:right].replace("\n", " ").strip()
    return ("…" if left > 0 else "") + snippet + ("…" if right < len(text) else "")


def scan_policy(page_text: str) -> list[PolicyHit]:
    hits: list[PolicyHit] = []
    seen: set[str] = set()
    lowered = page_text.lower()
    families = [("superlative or guarantee", SUPERLATIVES)] + list(RESTRICTED_CLAIMS.items())
    for family, phrases in families:
        for phrase in sorted(phrases):
            pattern = r"(?<![\w#])" + re.escape(phrase) + r"(?![\w])"
            m = re.search(pattern, lowered)
            if m and phrase not in seen:
                seen.add(phrase)
                hits.append(PolicyHit(phrase=phrase, family=family, context=_context(page_text, m.start(), m.end())))
    return hits
