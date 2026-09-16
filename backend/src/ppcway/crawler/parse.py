"""What a merchant's website says, read out of the HTML it served.

Blueprint §6.2. The onboarding wizard would rather ask a merchant three
questions than thirty, so it reads the answers it can off their own website
first. This module is the reading half; `fetch.py` is the getting half.

**NOTHING HERE EXECUTES ANYTHING THE PAGE SUPPLIED.** `selectolax` is a parser
over a C tokeniser with no script engine at all, `<script>` and `<style>` nodes
are DELETED before anything but the JSON-LD is read rather than merely skipped
(see `STRIPPED_TAGS`, and `extract` for the one read that has to come first), and
the one
place page-supplied text is handed to a decoder - `json.loads` on a
`application/ld+json` block - is a data parser rather than an evaluator, wrapped
so that a block that is not JSON is discarded instead of raising. The distinction
matters enough to have a test on it: `test_extraction_never_evaluates_page_
javascript` puts `window.x = 1` in the page and asserts it appears nowhere in
what comes out.

**PRIORITY ORDER, AND WHY IT IS THIS WAY ROUND.** Structured data first, prose
last:

  1. **JSON-LD** (`application/ld+json`) and **microdata** (`itemprop`). This is
     the site telling us, in a schema, what it is - a merchant who filled in
     their Wix "business info" panel has a `telephone` field that is exactly
     their phone number, with no guessing;
  2. **OpenGraph** (`og:site_name`, `og:title`, `og:description`), which is the
     site telling a social network what to show, and is nearly as deliberate;
  3. **headings** - `<h1>` is what the page announces itself as;
  4. **body prose**, which is where the selling points live and where a phone
     number found by pattern is a guess rather than a fact;
  5. `tel:` links and address patterns, which is guessing with a good prior.

A guess that reaches the merchant as a pre-filled form field they can correct is
useful; a guess that reaches an ad as ad copy is not, which is why
`fetch.py` reports `INSUFFICIENT` rather than handing the generator whatever
thin scraps it found. See `CrawlResult.source` there.

**EVERY LIST THIS MODULE PRODUCES IS BOUNDED AND DE-DUPLICATED.** A page with
four hundred `<li>` elements is a navigation menu, not a service list, and an
unbounded read of it becomes an unbounded prompt in Stage 5's generator - which
is a cost and a prompt-injection surface rather than a crash. The bounds are
judgements, written as literals, and `tests/crawler/test_parse.py` pins them as
literals for the reason the whole project now writes down: a judgement
re-derived from the code it judges records nothing.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import urljoin, urlsplit

from selectolax.parser import HTMLParser

#: Nodes deleted outright before ANY field but JSON-LD is read. `script` and
#: `style` are the two that carry code; `noscript` and `template` carry markup
#: that a browser never shows, and reading them puts text on the page that no
#: visitor saw, which is worse than missing text - it is text a merchant cannot
#: find when they ask where a claim in their ad came from. Deleted rather than
#: skipped so that `Node.text()` on any ANCESTOR is also clean: skipping only
#: works if every reader remembers to skip.
#:
#: **AND THE DELETION PROTECTS EVERY FIELD, NOT JUST `page_text`.** It sat below
#: the services, links and headline reads at first, which made this a property of
#: one field while reading like a property of the extract;
#: `test_every_stripped_tag_stays_out_of_every_field_of_the_extract` is
#: parametrised over the tags AND the fields for that reason.
STRIPPED_TAGS: Final = ("script", "style", "noscript", "template", "svg", "iframe")

#: How many list items may become services, and how long one may be. A service
#: is a noun phrase ("Burst pipe repair"), not a paragraph, so anything longer
#: than this is prose that happens to be in a list.
MAX_SERVICES: Final = 24
MAX_SERVICE_LENGTH: Final = 80

#: How many selling points, and how long one may be.
MAX_SELLING_POINTS: Final = 12
MAX_SELLING_POINT_LENGTH: Final = 200

#: How many links one page may contribute to the crawl frontier.
MAX_LINKS: Final = 200

#: **A PRODUCT JUDGEMENT, WRITTEN AS A LITERAL BECAUSE THAT IS WHAT IT IS.**
#: "Which sentences on a plumber's website are the ones a merchant would want in
#: their ad" is not a fact about this codebase and no walk of the tree produces
#: it. It is a list of the claims small trade businesses actually make, and the
#: only honest way to hold it is to write it down and pin it as written down -
#: `test_the_selling_point_markers_are_a_literal_judgement` asserts both its
#: contents and its length, because a list that silently shrinks reads exactly
#: like one that was always short.
#:
#: Lower-cased, and matched against lower-cased sentences, so "Licensed" and
#: "licensed" are the same marker.
SELLING_POINT_MARKERS: Final = (
    "licensed",
    "insured",
    "bonded",
    "certified",
    "guarantee",
    "warranty",
    "same-day",
    "same day",
    "emergency",
    "24/7",
    "free estimate",
    "free quote",
    "no call-out fee",
    "family-owned",
    "family owned",
    "years of experience",
    "years in business",
)

#: The elements `_services` walks between. Headings reset the "are we under a
#: services heading" state; lists are what it collects when the answer is yes.
HEADING_TAGS: Final = ("h1", "h2", "h3", "h4")
LIST_TAGS: Final = ("ul", "ol")

#: A heading that introduces a list of services. Deliberately loose - the point
#: is to PREFER such a list, not to require one; when no heading matches, every
#: list item on the page is a candidate and the length bound does the filtering.
SERVICE_HEADING: Final = re.compile(
    r"service|what we do|our work|specialit|specialt", re.IGNORECASE
)

#: A phone number as a human writes one, used ONLY when neither structured data
#: nor a `tel:` link gave us one. Deliberately conservative: seven or more
#: digits arranged in groups, optionally with a country code, because a looser
#: pattern turns a postal code or a price into a phone number.
PHONE_PATTERN: Final = re.compile(
    r"(?:\+\d{1,3}[\s.\-]?)?(?:\(\d{2,4}\)|\d{2,4})(?:[\s.\-]\d{2,4}){2,4}"
)

#: A street address as a human writes one, used only as a last resort: a number,
#: then words, then a street-type word. Anchored on the street type rather than
#: on the number, because "12 King St W" and "1600 Pennsylvania Avenue" share the
#: type word and nothing else.
ADDRESS_PATTERN: Final = re.compile(
    r"\d{1,5}[\w.\-]*\s+(?:[\w.'\-]+\s+){0,4}"
    r"(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|way|boulevard|blvd|court|ct|"
    r"place|pl|crescent|cres|terrace|parade|highway|hwy)\b[\w\s.,'\-]{0,40}",
    re.IGNORECASE,
)

#: The keys this module reads out of a schema.org object, whatever the vocabulary
#: spells them as. JSON-LD writes `telephone`; microdata writes
#: `itemprop="telephone"`; both are the same field, which is why one table serves
#: both readers.
_SCHEMA_NAME: Final = "name"
_SCHEMA_TELEPHONE: Final = "telephone"
_SCHEMA_ADDRESS: Final = "address"

#: The parts of a `PostalAddress`, in the order a human writes them.
_ADDRESS_PARTS: Final = (
    "streetAddress",
    "addressLocality",
    "addressRegion",
    "postalCode",
    "addressCountry",
)

#: Schemes a discovered link may use. A crawler that follows `javascript:` or
#: `data:` has no idea what it is fetching, and `ssrf.assert_safe_url` refuses
#: both anyway - filtering here means the refusal is never reached rather than
#: reached and logged for every menu entry on the page.
LINK_SCHEMES: Final = frozenset({"http", "https"})


@dataclass(frozen=True)
class PageExtract:
    """One page, read.

    Frozen because an extract is evidence: `fetch.py` aggregates several of
    these into a `CrawlResult` and nothing downstream may edit what a page said.

    Empty string and empty tuple mean "this page did not say", never "unknown
    and possibly something" - a caller deciding whether it has enough to work
    with counts characters, and `None` would make that count a special case at
    every site.
    """

    url: str
    business_name: str
    services: tuple[str, ...]
    unique_selling_points: tuple[str, ...]
    phone: str
    address: str
    meta_title: str
    meta_description: str
    page_text: str
    links: tuple[str, ...]


def _clean(text: str) -> str:
    """One line of whitespace-collapsed text.

    Every string this module returns goes through here, so a caller never has to
    wonder whether a value carries the page's indentation - and `page_text`
    reaching an LLM prompt as one collapsed run is the difference between a
    prompt and a prompt with four thousand newlines in it.
    """
    return " ".join(text.split())


def _json_ld_objects(tree: HTMLParser) -> list[dict[str, Any]]:
    """Every JSON-LD object on the page, flattened out of its wrappers.

    A block can be one object, a list of them, or a `@graph` holding either, and
    an object's values can hold more objects - so this walks rather than
    indexing. A block that is not JSON at all is DISCARDED: a merchant's site is
    not obliged to be well-formed, and a crawler that raises on a malformed
    `<script>` fails on exactly the sites this whole module exists to cope with.
    """
    found: list[dict[str, Any]] = []
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            parsed = json.loads(node.text())
        except (ValueError, TypeError):
            continue
        _collect_objects(parsed, found)
    return found


def _collect_objects(value: Any, found: list[dict[str, Any]]) -> None:
    """Depth-first walk of a decoded JSON-LD value, collecting the dicts."""
    if isinstance(value, dict):
        found.append(value)
        for nested in value.values():
            _collect_objects(nested, found)
    elif isinstance(value, list):
        for nested in value:
            _collect_objects(nested, found)


def _from_json_ld(objects: list[dict[str, Any]], key: str) -> str:
    """The first usable string value for `key` across the page's JSON-LD."""
    for obj in objects:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return _clean(value)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return _clean(item)
    return ""


def _address_from_json_ld(objects: list[dict[str, Any]]) -> str:
    """A postal address assembled from its parts, or a plain string if that is
    all the page gave.

    `schema.org/address` is either a string or a `PostalAddress` object, and the
    object form is the one worth having - it is the only shape that says which
    part is the street and which is the city.
    """
    for obj in objects:
        value = obj.get(_SCHEMA_ADDRESS)
        if isinstance(value, str) and value.strip():
            return _clean(value)
        if isinstance(value, dict):
            parts = [
                _clean(str(value[part]))
                for part in _ADDRESS_PARTS
                if isinstance(value.get(part), str) and str(value[part]).strip()
            ]
            if parts:
                return ", ".join(parts)
    return ""


def _microdata(tree: HTMLParser, prop: str) -> str:
    """The first `itemprop=<prop>` value on the page.

    Microdata puts the value in `content` on a `<meta>`, in `href` on a link and
    in the element's text everywhere else, which is why this reads three places
    rather than one.
    """
    for node in tree.css(f'[itemprop="{prop}"]'):
        content = node.attributes.get("content")
        if content and content.strip():
            return _clean(content)
        href = node.attributes.get("href")
        if href and href.strip().startswith("tel:"):
            return _clean(href.strip()[len("tel:"):])
        text = node.text(strip=True)
        if text:
            return _clean(text)
    return ""


def _meta(tree: HTMLParser, attribute: str, value: str) -> str:
    """A `<meta>` element's `content`, selected by `name` or `property`."""
    node = tree.css_first(f'meta[{attribute}="{value}"]')
    if node is None:
        return ""
    return _clean(node.attributes.get("content") or "")


def _tel_link(tree: HTMLParser) -> str:
    """The first `tel:` href, which is a phone number a human deliberately made
    clickable rather than one a pattern found in prose."""
    for node in tree.css("a[href]"):
        href = (node.attributes.get("href") or "").strip()
        if href.lower().startswith("tel:"):
            number = _clean(href[len("tel:"):])
            if number:
                return number
    return ""


def _headline(tree: HTMLParser) -> str:
    """The page's `<h1>`, or the first `<h2>` if it has none."""
    for selector in ("h1", "h2"):
        node = tree.css_first(selector)
        if node is not None:
            text = _clean(node.text())
            if text:
                return text
    return ""


def _name_from_title(title: str) -> str:
    """The business half of a `Name | Tagline` title.

    Small-business titles are overwhelmingly `<business> <separator> <what they
    do>`, and the business is the first half. Only used when nothing more
    deliberate said the name, and a title with no separator is returned whole.
    """
    for separator in ("|", " - ", " – ", " — ", "::"):
        if separator in title:
            return _clean(title.split(separator)[0])
    return title


def _services(tree: HTMLParser) -> tuple[str, ...]:
    """List items that read like services.

    **THE HEADING IS A PREFERENCE, NOT A REQUIREMENT.** A list under a heading
    matching `SERVICE_HEADING` is a service list beyond reasonable doubt, so if
    any such list exists it is the answer. When none does, every list item on the
    page is a candidate and `MAX_SERVICE_LENGTH` does the filtering - which lets
    a site with no headings at all contribute something, at the cost of
    occasionally reading a navigation menu. That trade is the right way round
    here: a wrong service reaches the merchant as a pre-filled field they delete,
    and a missing one reaches them as a field they have to type.
    """
    root = tree.body if tree.body is not None else tree.root
    if root is None:
        return ()
    preferred: list[str] = []
    heading_matched = False
    # **`traverse` RATHER THAN A COMMA SELECTOR, AND THAT IS NOT A STYLE
    # CHOICE.** `css("h2, ul")` returns every `h2` and THEN every `ul`, grouped
    # by selector rather than in document order - so "the list that follows a
    # services heading" cannot be expressed with one. Measured: with a comma
    # selector this function returned the navigation menu as the services of a
    # page whose heading was in the right place.
    for node in root.traverse(include_text=False):
        if node.tag in HEADING_TAGS:
            heading_matched = bool(SERVICE_HEADING.search(node.text()))
        elif node.tag in LIST_TAGS and heading_matched:
            preferred.extend(item.text() for item in node.css("li"))
    candidates = preferred or [node.text() for node in tree.css("li")]
    return _bounded(candidates, MAX_SERVICES, MAX_SERVICE_LENGTH)


def _selling_points(page_text: str) -> tuple[str, ...]:
    """Sentences carrying one of `SELLING_POINT_MARKERS`."""
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", page_text)]
    carrying = [
        sentence
        for sentence in sentences
        if any(marker in sentence.lower() for marker in SELLING_POINT_MARKERS)
    ]
    return _bounded(carrying, MAX_SELLING_POINTS, MAX_SELLING_POINT_LENGTH)


def _bounded(candidates: list[str], limit: int, length: int) -> tuple[str, ...]:
    """Clean, drop the empty and the over-long, de-duplicate, and cap.

    `dict.fromkeys` rather than a set because the page's order is the site's own
    idea of what matters most, and a set would replace it with the hash order -
    which changes between runs under `PYTHONHASHSEED`, and this project already
    pins determinism elsewhere.
    """
    cleaned = [_clean(candidate) for candidate in candidates]
    kept = [text for text in cleaned if text and len(text) <= length]
    return tuple(dict.fromkeys(kept))[:limit]


def _links(tree: HTMLParser, url: str) -> tuple[str, ...]:
    """Every `http(s)` link on the page, made absolute against `url`.

    Fragments are dropped, because `/services#pricing` and `/services` are one
    page and fetching both is a doubling of every crawl for nothing.
    """
    found: list[str] = []
    for node in tree.css("a[href]"):
        href = (node.attributes.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        try:
            absolute = urljoin(url, href)
            parts = urlsplit(absolute)
        except ValueError:
            continue
        if parts.scheme.lower() not in LINK_SCHEMES:
            continue
        found.append(parts._replace(fragment="").geturl())
    return tuple(dict.fromkeys(found))[:MAX_LINKS]


def extract(html: str, url: str) -> PageExtract:
    """Read one page.

    `url` is what relative links are resolved against and what the extract
    records itself as; it is never fetched from here.

    **THE ORDER OF THE STATEMENTS BELOW IS LOAD-BEARING, AND THE LINE IS DRAWN
    IN ONE PLACE RATHER THAN NINE.** JSON-LD is read BEFORE `STRIPPED_TAGS` are
    deleted, because it lives inside a `<script>` element - deleting first would
    throw away the best source on the page and leave the guessing. **Everything
    else is read after**, and that ordering is the fix to a real hole: the first
    version read the services, the links and the headline before the deletion
    too, so `STRIPPED_TAGS` protected `page_text` and nothing else. Executed, a
    `<template>` a browser never renders put "A service no visitor ever sees"
    into `CrawlResult.services` - which `fetch.py` aggregates and Stage 5 puts in
    a prompt - and `/hidden-by-template.html` into the crawl frontier. That is
    the "text a merchant cannot find when they ask where a claim in their ad came
    from" that `STRIPPED_TAGS`' own comment is about, and a hidden link is a
    fetch the merchant cannot account for either.
    """
    tree = HTMLParser(html)

    json_ld = _json_ld_objects(tree)

    for node in tree.css(", ".join(STRIPPED_TAGS)):
        node.decompose()

    title = tree.css_first("title")
    meta_title = _clean(title.text()) if title is not None else ""
    meta_description = _meta(tree, "name", "description") or _meta(
        tree, "property", "og:description"
    )
    og_site_name = _meta(tree, "property", "og:site_name")
    og_title = _meta(tree, "property", "og:title")
    tel = _tel_link(tree)
    microdata_name = _microdata(tree, _SCHEMA_NAME)
    microdata_phone = _microdata(tree, _SCHEMA_TELEPHONE)
    microdata_address = _microdata(tree, _SCHEMA_ADDRESS)
    services = _services(tree)
    links = _links(tree, url)
    headline = _headline(tree)

    body = tree.body if tree.body is not None else tree.root
    page_text = _clean(body.text(separator=" ")) if body is not None else ""

    business_name = (
        _from_json_ld(json_ld, _SCHEMA_NAME)
        or microdata_name
        or og_site_name
        or og_title
        or headline
        or _name_from_title(meta_title)
    )
    phone = (
        _from_json_ld(json_ld, _SCHEMA_TELEPHONE)
        or microdata_phone
        or tel
        or _first_match(PHONE_PATTERN, page_text)
    )
    address = (
        _address_from_json_ld(json_ld)
        or microdata_address
        or _first_match(ADDRESS_PATTERN, page_text)
    )

    return PageExtract(
        url=url,
        business_name=business_name,
        services=services,
        unique_selling_points=_selling_points(page_text),
        phone=phone,
        address=address,
        meta_title=meta_title or og_title,
        meta_description=meta_description,
        page_text=page_text,
        links=links,
    )


def _first_match(pattern: re.Pattern[str], text: str) -> str:
    """The first match of `pattern` in `text`, cleaned, or the empty string."""
    found = pattern.search(text)
    return _clean(found.group(0)) if found else ""
