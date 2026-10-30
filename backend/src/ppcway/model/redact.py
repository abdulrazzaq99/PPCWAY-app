"""Taking the people out of a prompt before it is written down.

The prompt log exists so that a bad answer can be traced to the words that
produced it, and so that misuse can be found. Neither of those needs a
merchant's phone number, and keeping one turns a debugging aid into a second
copy of the customer database with a thirty-day retention nobody reviews.

So: redacted on the way in, not on the way out. A redaction applied at read
time is a redaction that was not applied to the backup, the replica, or the
log aggregator. What is written here is already safe to read.

**This removes patterns, which is not the same as removing every person.** A
business name is a person's name often enough -- "Dana Plumbing" -- and no
regular expression finds that. The claim this module supports is narrower and
worth stating plainly: an address, a telephone number, a card-shaped number or
a long opaque token will not survive into the log. A name might.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Final

#: Each pattern and what stands in for it. Ordered: the broadest token pattern
#: runs last, so an email is recognised as an email rather than as a token.
_RULES: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    # An address, before the digits in it can be read as a phone number.
    (re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), "[email]"),
    # Sixteen-ish digits in groups: a card, whatever the separator.
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[card]"),
    # A telephone number, international or local, with the separators people
    # actually type. Seven digits minimum, so a price does not become a phone
    # number. Dates are the awkward case -- 2026-10-30 is eight digits with
    # separators and looks exactly like a local number -- so `_not_a_date`
    # hands those back untouched. A prompt log with the dates stripped out of
    # it is close to useless, since when a figure was measured is most of what
    # a reason sentence is about.
    (
        re.compile(r"(?<![\w.])\+?\d(?:[\d\s().-]{5,}\d)(?![\w.])"),
        "[phone]",
    ),
    # Anything long, opaque and base64-ish: a refresh token, an API key, a
    # session cookie. Twenty-four characters of mixed case and digits is not
    # prose, and nothing of the sort belongs in a prompt in the first place --
    # this is here for the day something does. Dots are not in the character
    # class, so `ya29.AbC…` is logged as `ya29.[token]`. That is deliberate:
    # the secret is gone, and what is left says a Google credential reached a
    # prompt, which is an incident somebody should see rather than a line that
    # reads like any other redaction.
    (
        re.compile(
            r"\b(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*[a-z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{24,}\b"
        ),
        "[token]",
    ),
)

#: How much of a prompt to keep. A prompt log is for finding the shape of a bad
#: answer, not for replaying it; a crawled page in full would be most of the
#: storage and none of the value.
MOST: Final = 4_000


#: A date, in the forms these prompts carry: 2026-10-30, 30/10/2026, 30-10-2026.
_DATE = re.compile(r"^\s*(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*$")


def _not_a_date(instead: str) -> Callable[[re.Match[str]], str]:
    """Replace, unless what matched is a date, which is kept as it stands."""

    def swap(found: re.Match[str]) -> str:
        return found.group(0) if _DATE.match(found.group(0)) else instead

    return swap


def redacted(text: str, *, most: int = MOST) -> str:
    """One prompt, with the patterns above replaced and the tail dropped."""
    if not text:
        return ""
    clean = text
    for pattern, instead in _RULES:
        clean = pattern.sub(_not_a_date(instead), clean)
    if len(clean) > most:
        return f"{clean[:most]}… [{len(clean) - most} more characters]"
    return clean
