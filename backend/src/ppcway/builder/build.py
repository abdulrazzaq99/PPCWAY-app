"""Writing a new campaign: real searches first, then ad text, then checks.

What the "Start a new campaign" screen promises, in its order:

1. **Ask Google what people type.** For each theme, Keyword Planner's ideas in
   the places and language the campaign will run in. Only a phrase Google says
   people search for may become a keyword -- the brief's keywords gate, in
   `keywords.sift` -- and only one about the theme: every word of the theme has
   to be in it, which keeps "pdf to word" from filling up with other people's
   brand names and other tools.
2. **Write and check the ads.** Fifteen headlines and four descriptions per
   theme, drafted by the model from what the merchant said the business does,
   then put through the six checks; at least ten headlines kept, one retry
   told what was wrong. `draft.write_copy`.
3. **You review it.** Nothing here talks to Google's write side. The plan is
   returned for the merchant to read and edit, and only a launch creates it.

Themes are written side by side: each is a planner call and a model call,
and one after the other they add up to a minute of a merchant watching a
spinner.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Final

from ppcway.ads.planner import Demand
from ppcway.builder.campaign import MOST_KEYWORDS, MOST_THEMES, CampaignPlan, Place, Theme
from ppcway.builder.draft import write_copy
from ppcway.builder.keywords import sift
from ppcway.builder.validate import Business, Rules
from ppcway.model.service import Models

#: Words a theme may have that a search need not repeat.
_LINKING: Final = frozenset(
    {"a", "an", "and", "the", "to", "for", "of", "in", "on", "near", "me", "my", "with", "&"}
)
_TOKENS = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    """The words of a phrase, with a plain plural read as its singular."""
    out = set()
    for word in _TOKENS.findall(text.lower()):
        if word in _LINKING:
            continue
        out.add(word[:-1] if len(word) > 3 and word.endswith("s") else word)
    return out


def on_theme(search: str, theme: str) -> bool:
    """Whether a search is about the theme: it contains every word of it."""
    wanted = _words(theme)
    return bool(wanted) and wanted <= _words(search)


def write_theme(
    theme: str,
    *,
    ask_planner: Callable[[str], Demand],
    models: Models | None,
    business: Business,
    rules: Rules | None = None,
) -> Theme:
    """One ad group: its keywords from Keyword Planner, then its ad text."""
    demand = ask_planner(theme)
    ideas = [found.term for found in demand.searches if on_theme(found.term, theme)]
    sifted = sift([theme, *ideas], demand)
    if not sifted.usable:
        return Theme(
            name=theme,
            dropped=[asdict(d) for d in sifted.dropped],
            short=sifted.unavailable
            or f'Google says too few people search for "{theme}" where these ads will show.',
        )
    keywords = list(sifted.keywords[:MOST_KEYWORDS])
    written = write_copy(
        models,
        business=business,
        theme=theme,
        keywords=[k.text for k in keywords],
        rules=rules,
    )
    return Theme(
        name=theme,
        keywords=[asdict(k) for k in keywords],
        headlines=list(written.headlines),
        descriptions=list(written.descriptions),
        dropped=[asdict(d) for d in sifted.dropped],
        short=written.short,
    )


def build_plan(
    *,
    themes: Sequence[str],
    name: str,
    daily_budget: float,
    currency: str,
    final_url: str,
    places: list[Place],
    language: Place,
    bidding: str,
    negatives: Sequence[str],
    business: Business,
    ask_planner: Callable[[str], Demand],
    models: Models | None,
) -> CampaignPlan:
    """The whole campaign, written, for the merchant to read before anything exists."""
    wanted = list(dict.fromkeys(t.strip() for t in themes if t.strip()))[:MOST_THEMES]
    with ThreadPoolExecutor(max_workers=max(1, len(wanted))) as pool:
        written = list(
            pool.map(
                lambda theme: write_theme(
                    theme, ask_planner=ask_planner, models=models, business=business
                ),
                wanted,
            )
        )
    return CampaignPlan(
        name=name.strip() or (wanted[0] if wanted else "New campaign"),
        daily_budget=daily_budget,
        currency=currency,
        final_url=final_url.strip(),
        places=places,
        language=language,
        bidding=bidding,
        themes=written,
        negatives=[n.strip() for n in negatives if n.strip()],
        business=business,
        ai_written=models is not None and any(t.headlines or t.descriptions for t in written),
    )
