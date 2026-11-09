"""Whose ads these are, read from the page they send people to.

The builder used to hand the copywriting model the PPCWay business's name. For
anybody who never named their business that is the name PPCWay made for them on
their first page load: their own name, taken from their Google sign-in. So on 9
November the owner's ads were drafted for "Abdul Razzaq", the person, rather
than for PDFezy, the website the ads point at.

The landing page knows better. One page is read through the audit's own crawler
-- the same refusal of private addresses, the same caps on size and time -- and
its business name and title are what the ads are written for. The crawler picks
the name in a fixed order: the site's own structured data, then its OpenGraph
name, then its main heading, then the first half of its `<title>`.

A page that cannot be read gives nothing, and the caller falls back to the
Google Ads account's name. It never falls back to a person's name.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

log = logging.getLogger(__name__)

#: How long the landing page may take. The draft already waits on Keyword
#: Planner and the model, so this is a small share of a long wait, not a new one.
SITE_SECONDS: Final = 8.0

#: Long enough for any business name and any sensible title; a page whose title
#: is a paragraph does not get to put the paragraph in a prompt.
MOST_NAME: Final = 80
MOST_TITLE: Final = 120


@dataclass(frozen=True, slots=True)
class Site:
    """What the landing page says it is. Empty where it said nothing."""

    name: str = ""
    title: str = ""


def _short(text: str, most: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= most else text[: most - 1].rstrip() + "…"


def read_site(url: str, *, crawl: Callable[..., Any] | None = None) -> Site:
    """The business name and title of the page at `url`, or an empty `Site`.

    Never raises: a site that is down, slow, or refused as private must not
    stop a campaign from being drafted.
    """
    from ppcway.crawler.fetch import build_client
    from ppcway.crawler.fetch import crawl as crawl_site

    read = crawl or crawl_site
    try:
        with build_client(timeout_seconds=SITE_SECONDS) as client:
            found = read(
                url,
                max_pages=1,
                timeout_seconds=SITE_SECONDS,
                rps_per_host=1.0,
                client=client,
            )
    except Exception as exc:  # noqa: BLE001 - an unreadable site is a fallback, not a failure
        log.info("landing page %s not read for the builder: %s", url, type(exc).__name__)
        return Site()
    return Site(
        name=_short(str(getattr(found, "business_name", "") or ""), MOST_NAME),
        title=_short(str(getattr(found, "meta_title", "") or ""), MOST_TITLE),
    )


def own_name_or_not(org_name: str, people: list[tuple[str, str]]) -> str:
    """The business's PPCWay name, unless it is only somebody's own name.

    A business made on a first page load is named after that person's Google
    name, or the start of their email address. That is not a business name,
    and an ad must never carry it. `people` is every member's (name, email).
    """
    name = " ".join(org_name.split())
    if not name:
        return ""
    for person, email in people:
        local = email.split("@", 1)[0]
        if name.lower() in {person.strip().lower(), local.lower(), email.lower()}:
            return ""
    return name
