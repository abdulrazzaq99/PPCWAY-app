"""Writing an ad's text, and what to do when most of it is refused.

The client's brief: *draft 15 headlines and 4 descriptions per ad group; keep
at least 10 headlines that pass validation; otherwise retry once, then the
category template.*

Three attempts' worth of behaviour in one sentence, and the order is the point.

1. **Draft fifteen.** Google takes fifteen headlines and runs the combinations
   it likes; a merchant with three is a merchant whose ads cannot be tested.
2. **Keep what passes.** The six validator stages filter; they do not veto the
   batch. Ten surviving is enough to launch on.
3. **One retry, told what was wrong.** Not "try again" -- the refusals, by
   stage, so the second attempt has something to work with. A model told only
   that it failed produces the same copy with different adjectives.
4. **Then the category template.** Which the client supplies per launch
   industry, and has not yet. So the honest ending is a refusal that says
   exactly that, rather than a third generated attempt: three tries at copy
   that keeps being refused for claiming things the business profile does not
   support is three tries at the same misunderstanding.

**The model is never the authority on what is true.** It is handed the business
profile and told what it may claim; stage three of the validator then checks
every draft against the same profile, so a claim that slips past the prompt
does not slip past the gate. That double handling is deliberate: the prompt is
how it usually gets it right, and the validator is why it does not matter when
it does not.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from ppcway.builder.kinds import PROMISES, kind_of
from ppcway.builder.validate import (
    DESCRIPTIONS_LEAST,
    DESCRIPTIONS_WANTED,
    HEADLINES_KEEP,
    HEADLINES_WANTED,
    Business,
    Checked,
    Kind,
    Refusal,
    Rules,
    check,
    promised,
)
from ppcway.model.jobs import Job
from ppcway.model.service import Models, ModelUnavailable

log = logging.getLogger(__name__)

#: One retry, as the brief says. Two attempts in total, never three.
TRIES: Final = 2

HOW_TO_WRITE: Final = """You write Google Search ad text for a small business. You are given what the \
business actually does, and you may claim nothing beyond it.

Rules you may not break:
- Every claim must be supported by the business profile. Make only the \
promises listed under "Promises they can make". Anything under "Promises they \
cannot make", and any number of years or any accreditation the profile does \
not give, will be refused.
- Write for the kind of business given. Software is not sold like a repair \
service, and a shop is not a consultancy.
- No superlatives and no unverifiable claims: not "best", not "cheapest", not \
"number one", not "guaranteed".
- No exclamation marks. No words in capitals.
- Headlines at most 30 characters. Descriptions at most 90.
- Each headline must say something different. Two headlines with the same \
words in a different order are one headline.
- British English. Plain words a customer would use.

Reply with one headline or description per line and nothing else: no numbering, \
no quotes, no commentary."""


@dataclass(frozen=True, slots=True)
class Written:
    """What survived, what did not, and how it was arrived at."""

    headlines: tuple[str, ...] = ()
    descriptions: tuple[str, ...] = ()
    refused: tuple[Refusal, ...] = ()
    #: How many times the model was asked. Zero means it was never reachable.
    asked: int = 0
    #: Set when there is not enough usable copy. Says what is needed next,
    #: which today is the client's own category template.
    short: str = ""
    #: Every stage that refused something, with how many. The thing a person
    #: tuning a prompt actually needs.
    refused_by: dict[str, int] = field(default_factory=dict)

    @property
    def enough(self) -> bool:
        return (
            len(self.headlines) >= HEADLINES_KEEP and len(self.descriptions) >= DESCRIPTIONS_LEAST
        )

    @property
    def declared_as_ai(self) -> bool:
        """Whether this copy is AI-drafted, for the merchant to be told so.

        True whenever a model wrote any of it: one model-written headline makes
        the ad model-written. The brief asked for `synthetic_content_info` on
        such ads, and Google accepts that only on image and HTML5 ads -- a
        search ad carrying it is refused -- so the disclosure is PPCWay's own,
        on the review screen and in the record of the launch.
        """
        return self.asked > 0 and bool(self.headlines or self.descriptions)


def _lines(text: str, *, most: int) -> list[str]:
    """One per line, stripped of the numbering a model adds anyway."""
    out: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip().lstrip("-*•").strip()
        # "1." and "1)" prefixes, which the prompt forbids and models add.
        while line[:1].isdigit():
            cut = line.lstrip("0123456789").lstrip(".)").lstrip()
            if cut == line:
                break
            line = cut
        line = line.strip().strip('"').strip("'").strip()
        if line:
            out.append(line)
        if len(out) >= most:
            break
    return out


def _profile(business: Business) -> str:
    """The business, in the words the model is allowed to work from."""
    says = [f"Name: {business.name or 'not given'}"]
    if business.kind:
        says.append(f"Kind of business: {kind_of(business.kind).label}")
    if business.site_title:
        says.append(f"Their website's title: {business.site_title}")
    if business.services:
        says.append(f"What they sell: {', '.join(business.services)}")
    if business.places:
        says.append(f"Where their customers are: {', '.join(business.places)}")
    allowed = promised(business)
    can = [one.short for one in PROMISES if one.id in allowed]
    cannot = [one.short for one in PROMISES if one.id not in allowed]
    says.append("Promises they can make: " + (", ".join(can) or "none"))
    says.append("Promises they cannot make: " + (", ".join(cannot) or "none"))
    says.append(
        "Years trading: "
        + (str(business.years_trading) if business.years_trading is not None else "not given")
    )
    says.append("Accreditations: " + (", ".join(business.accreditations) or "none recorded"))
    return "\n".join(says)


def _complaints(refused: Sequence[Refusal]) -> str:
    """What was wrong with the last attempt, so the next one can differ.

    By stage and with the text, because "too long" and "claims something the
    profile does not support" need opposite corrections and a model told only
    that it failed produces the same copy with different adjectives.
    """
    lines = [
        f'- "{one.text}" was refused ({one.stage.value}): {one.because}' for one in refused[:12]
    ]
    return "\n".join(lines)


def write_copy(
    models: Models | None,
    *,
    business: Business,
    theme: str,
    keywords: Sequence[str],
    rules: Rules | None = None,
) -> Written:
    """Draft, validate, retry once, then say what is needed.

    Returns what passed. Never raises: a builder step that crashed on a bad
    generation would leave a half-built campaign, and the whole point of
    drafting fifteen is that some of them are expected to fail.
    """
    if models is None:
        return Written(
            short=(
                "Otto is not switched on in this deployment, so there is nothing to"
                " draft ad text with yet."
            )
        )

    asked = 0
    headlines: Checked = Checked(kept=())
    descriptions: Checked = Checked(kept=())
    complaints = ""

    for _ in range(TRIES):
        asked += 1
        said = _ask(
            models,
            business=business,
            theme=theme,
            keywords=keywords,
            complaints=complaints,
        )
        if said is None:
            break
        headlines = check(
            _lines(said[0], most=HEADLINES_WANTED),
            kind=Kind.HEADLINE,
            business=business,
            rules=rules,
        )
        descriptions = check(
            _lines(said[1], most=DESCRIPTIONS_WANTED),
            kind=Kind.DESCRIPTION,
            business=business,
            rules=rules,
        )
        if len(headlines.kept) >= HEADLINES_KEEP and len(descriptions.kept) >= DESCRIPTIONS_LEAST:
            break
        complaints = _complaints([*headlines.refused, *descriptions.refused])

    refused = (*headlines.refused, *descriptions.refused)
    by_stage: dict[str, int] = {}
    for one in refused:
        by_stage[one.stage.value] = by_stage.get(one.stage.value, 0) + 1

    short = ""
    if len(headlines.kept) < HEADLINES_KEEP or len(descriptions.kept) < DESCRIPTIONS_LEAST:
        short = (
            f"Only {len(headlines.kept)} of {HEADLINES_WANTED} headlines and"
            f" {len(descriptions.kept)} descriptions survived checking, and"
            f" {HEADLINES_KEEP} headlines are needed. The next step is this trade's"
            f" own ad template, which PPCWay has not supplied yet."
        )
        log.info("copy for %r came up short: %s", theme, by_stage)

    return Written(
        headlines=headlines.kept,
        descriptions=descriptions.kept,
        refused=refused,
        asked=asked,
        short=short,
        refused_by=by_stage,
    )


def _ask(
    models: Models,
    *,
    business: Business,
    theme: str,
    keywords: Sequence[str],
    complaints: str,
) -> tuple[str, str] | None:
    """One attempt at both. None where the model could not be reached."""
    wanted = (
        f"THE BUSINESS\n{_profile(business)}\n\n"
        f"THIS AD GROUP\nTheme: {theme}\n"
        f"What people search for: {', '.join(keywords[:10])}\n\n"
        f"WRITE\n{HEADLINES_WANTED} headlines, then the word DESCRIPTIONS on its own"
        f" line, then {DESCRIPTIONS_WANTED} descriptions."
    )
    if complaints:
        wanted += (
            f"\n\nYOUR LAST ATTEMPT WAS REJECTED\n{complaints}\n\nWrite it again,"
            f" fixing each of those. Do not reword a claim the profile does not"
            f" support -- leave the claim out."
        )
    try:
        said = models.ask(Job.AD_DRAFT, system=HOW_TO_WRITE, said=wanted)
    except ModelUnavailable as exc:
        log.info("could not draft copy for %r: %s", theme, exc)
        return None
    if said.refused or not said.text.strip():
        return None

    # The model is asked for one block with a marker, so a short reply still
    # yields headlines rather than nothing.
    head, _, rest = said.text.partition("DESCRIPTIONS")
    return head, rest or ""
