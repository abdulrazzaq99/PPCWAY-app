"""Reading a merchant's page, including the pages that do not cooperate.

Two things are being held here. The first is the PRIORITY ORDER - structured
data beats OpenGraph beats a heading beats a pattern over prose - and it is
tested by taking sources AWAY one at a time, because a page that carries all
four proves only that the best one wins, never that the second one is reached.

The second is that **NOTHING ON THE PAGE IS EXECUTED, AND NOTHING FROM A
`<script>` REACHES THE TEXT.** That is a security property, not a tidiness one:
`page_text` ends up in an LLM prompt, so a page can put words in front of a
generator, and `<script>window.x = 1</script>` is the smallest witness that the
tag's contents are dropped rather than rendered.
"""
import ast
import dataclasses
import pathlib

import pytest

from ppcway.crawler import parse
from ppcway.crawler.parse import (
    ADDRESS_PATTERN,
    LINK_SCHEMES,
    MAX_LINKS,
    MAX_SELLING_POINT_LENGTH,
    MAX_SELLING_POINTS,
    MAX_SERVICE_LENGTH,
    MAX_SERVICES,
    PHONE_PATTERN,
    SELLING_POINT_MARKERS,
    STRIPPED_TAGS,
    PageExtract,
    extract,
)

PARSE_PATH = pathlib.Path(parse.__file__).resolve()
PARSE_TREE = ast.parse(PARSE_PATH.read_text())

URL = "https://alphaplumbing.example/"

HTML = """
<html><head><title>Alpha Plumbing | Emergency Plumber Toronto</title>
<meta name="description" content="Licensed emergency plumber in Toronto.">
<script type="application/ld+json">
{"@type":"Plumber","name":"Alpha Plumbing","telephone":"+1-416-555-0134",
 "address":{"streetAddress":"12 King St W","addressLocality":"Toronto"}}
</script></head>
<body><h1>Emergency Plumber in Toronto</h1>
<h2>Our Services</h2><ul><li>Burst pipe repair</li><li>Blocked drains</li></ul>
<p>Licensed and insured. Same-day service, seven days a week.</p>
<a href="tel:+14165550134">Call us</a></body></html>
"""


def _binding(name: str) -> ast.expr:
    """The right-hand side of a module-level assignment in `parse.py`, as AST."""
    for node in PARSE_TREE.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            return node.value
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.value
    raise AssertionError(f"parse.py binds no module-level name {name}")


# --------------------------------------------------------------------------
# The five the plan asked for
# --------------------------------------------------------------------------


def test_structured_data_is_preferred_over_heading_text() -> None:
    """The `<h1>` says "Emergency Plumber in Toronto" and the JSON-LD says
    "Alpha Plumbing". The heading is what the page SHOUTS; the schema is what
    the merchant TYPED into a form, and it is the one to believe."""
    page = extract(HTML, URL)
    assert page.business_name == "Alpha Plumbing"
    assert page.phone == "+1-416-555-0134"
    assert "12 King St W" in page.address


def test_services_are_extracted_from_the_list() -> None:
    page = extract(HTML, URL)
    assert "Burst pipe repair" in page.services
    assert "Blocked drains" in page.services


def test_the_meta_title_and_description_are_captured() -> None:
    page = extract(HTML, URL)
    assert "Emergency Plumber Toronto" in page.meta_title
    assert page.meta_description.startswith("Licensed")


def test_page_text_is_plain_and_carries_no_markup() -> None:
    page = extract(HTML, URL)
    assert "<" not in page.page_text
    assert "seven days a week" in page.page_text


def test_extraction_never_evaluates_page_javascript() -> None:
    """The script is DELETED, not skipped - so no reader downstream has to
    remember to skip it, and `page_text` cannot carry a payload aimed at the
    generator that reads it."""
    hostile = HTML.replace("<p>Licensed", "<script>window.x=1</script><p>Licensed")
    page = extract(hostile, URL)
    assert "window.x" not in page.page_text
    assert "Licensed and insured" in page.page_text, (
        "deleting the script must not take the paragraph after it with it"
    )


# --------------------------------------------------------------------------
# The priority order, tested by taking each source away
# --------------------------------------------------------------------------
#
# A page carrying every source proves only that the FIRST one wins. Each case
# below removes the sources above it, so the row that is left is the one being
# measured - which is the only way a fallback that never fires shows up.

NAME_FALLBACKS = (
    pytest.param(
        '<html><head><meta property="og:site_name" content="Beta Boilers">'
        "<title>Beta Boilers | Heating</title></head><body><h1>Boiler repair</h1></body></html>",
        "Beta Boilers",
        id="opengraph-site-name",
    ),
    pytest.param(
        "<html><head><title>Gamma Gas | Heating</title></head>"
        "<body><h1>Gamma Gas Services</h1></body></html>",
        "Gamma Gas Services",
        id="the-h1",
    ),
    pytest.param(
        "<html><head><title>Delta Drains | Toronto</title></head><body><p>Hello</p></body></html>",
        "Delta Drains",
        id="the-title-before-the-separator",
    ),
    pytest.param(
        '<html><body><span itemprop="name">Epsilon Electrics</span></body></html>',
        "Epsilon Electrics",
        id="microdata",
    ),
)


@pytest.mark.parametrize("html,expected", NAME_FALLBACKS)
def test_the_business_name_falls_back_through_its_sources(html: str, expected: str) -> None:
    assert extract(html, URL).business_name == expected


def test_the_name_fallback_table_is_the_size_it_looks() -> None:
    """A parametrisation that collects one case reads exactly like one that
    collects four."""
    assert len(NAME_FALLBACKS) == 4


PHONE_FALLBACKS = (
    pytest.param(
        '<html><body><a itemprop="telephone" href="tel:+14165550134">call</a></body></html>',
        "+14165550134",
        id="microdata-on-a-tel-link",
    ),
    pytest.param(
        '<html><body><a href="tel:+1 416 555 0134">call</a></body></html>',
        "+1 416 555 0134",
        id="a-tel-link",
    ),
    pytest.param(
        "<html><body><p>Ring us on 416 555 0134 any day.</p></body></html>",
        "416 555 0134",
        id="a-pattern-over-prose",
    ),
)


@pytest.mark.parametrize("html,expected", PHONE_FALLBACKS)
def test_the_phone_falls_back_through_its_sources(html: str, expected: str) -> None:
    assert extract(html, URL).phone == expected


def test_the_phone_fallback_table_is_the_size_it_looks() -> None:
    assert len(PHONE_FALLBACKS) == 3


def test_a_postal_address_object_is_assembled_in_the_order_a_human_writes_it() -> None:
    """`schema.org/address` is a string OR an object, and the object form is the
    one worth having - it is the only shape that says which part is the street."""
    html = (
        '<html><head><script type="application/ld+json">'
        '{"@type":"Plumber","address":{"streetAddress":"12 King St W",'
        '"addressLocality":"Toronto","addressRegion":"ON","postalCode":"M5H 1A1"}}'
        "</script></head><body></body></html>"
    )
    assert extract(html, URL).address == "12 King St W, Toronto, ON, M5H 1A1"


def test_an_address_written_only_in_prose_is_found_by_pattern() -> None:
    html = "<html><body><p>Come to 12 King St W, Toronto for a quote.</p></body></html>"
    assert "12 King St W" in extract(html, URL).address


def test_the_address_pattern_does_not_turn_a_price_into_an_address() -> None:
    """The pattern is anchored on a street-type word for this reason. A looser
    one reads "$1,200 for the work" as a street address and pre-fills a form
    field the merchant then has to clear."""
    assert ADDRESS_PATTERN.search("1200 for the work, paid on the day") is None


def test_the_phone_pattern_does_not_turn_a_postal_code_into_a_number() -> None:
    assert PHONE_PATTERN.search("M5H 1A1") is None


# --------------------------------------------------------------------------
# JSON-LD, including the pages that are wrong
# --------------------------------------------------------------------------


def test_json_ld_inside_a_graph_wrapper_is_still_read() -> None:
    """`@graph` is what every WordPress SEO plugin emits, so a reader that only
    understands a bare object understands almost no real site."""
    html = (
        '<html><head><script type="application/ld+json">'
        '{"@context":"https://schema.org","@graph":['
        '{"@type":"WebSite","url":"https://alphaplumbing.example/"},'
        '{"@type":"Plumber","name":"Alpha Plumbing","telephone":"+1-416-555-0134"}]}'
        "</script></head><body><h1>Plumbing</h1></body></html>"
    )
    page = extract(html, URL)
    assert page.business_name == "Alpha Plumbing"
    assert page.phone == "+1-416-555-0134"


MALFORMED_JSON_LD = (
    pytest.param("{not json at all", id="not-json"),
    pytest.param("", id="empty"),
    pytest.param("[1, 2, 3]", id="a-list-of-numbers"),
    pytest.param("null", id="null"),
    pytest.param('{"name": {"nested": "object"}}', id="a-name-that-is-not-a-string"),
    pytest.param('{"name": []}', id="a-name-that-is-an-empty-list"),
)


@pytest.mark.parametrize("block", MALFORMED_JSON_LD)
def test_a_json_ld_block_that_is_wrong_is_discarded_rather_than_raising(block: str) -> None:
    """A merchant's site is not obliged to be well-formed, and a crawler that
    raises on a malformed `<script>` fails on exactly the sites this module
    exists for. Each of these must fall through to the heading."""
    html = (
        f'<html><head><title>T</title><script type="application/ld+json">{block}</script>'
        f"</head><body><h1>Zeta Roofing</h1></body></html>"
    )
    assert extract(html, URL).business_name == "Zeta Roofing"


def test_the_malformed_json_ld_table_is_the_size_it_looks() -> None:
    assert len(MALFORMED_JSON_LD) == 6


# --------------------------------------------------------------------------
# What is stripped, and what survives
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tag", STRIPPED_TAGS)
def test_every_stripped_tag_keeps_its_contents_out_of_the_page_text(tag: str) -> None:
    """Parametrised over the table itself, so a tag added there arrives with a
    test and a tag removed from it takes its test with it - which is the point:
    the list is the claim."""
    html = f"<html><body><p>kept</p><{tag}>SECRET-{tag.upper()}</{tag}></body></html>"
    page = extract(html, URL)
    assert "kept" in page.page_text
    assert "SECRET" not in page.page_text


#: The stripped tags a page can hide MARKUP inside. `svg` is the one that
#: cannot, and it is excluded by a measured fact rather than by taste - see
#: `test_svg_cannot_hide_markup_because_the_parser_takes_it_straight_back_out`,
#: which is what fails if that stops being true.
TAGS_THAT_CAN_HIDE_MARKUP = tuple(tag for tag in STRIPPED_TAGS if tag != "svg")


@pytest.mark.parametrize("tag", TAGS_THAT_CAN_HIDE_MARKUP)
def test_every_stripped_tag_stays_out_of_every_field_of_the_extract(tag: str) -> None:
    """**THE TEST ABOVE READS AS A PROPERTY OF THE EXTRACT AND WAS A PROPERTY OF
    ONE FIELD.** The deletion sat below the services, links and headline reads,
    so a `<template>` a browser never renders put "A service no visitor ever
    sees" into `services` - which `fetch.py` aggregates into `CrawlResult` and
    Stage 5 puts into a prompt - and a hidden `<a href>` into the crawl frontier,
    while `page_text` stayed clean exactly as advertised.

    So this asserts on the WHOLE extract, field by field, with hidden content of
    every shape the reader looks for: a list item, a link, a heading and a
    marker sentence. `url` is excluded because it is the argument, not a read.
    """
    html = (
        f"<html><body><h2>Our Services</h2>"
        f"<{tag}><h1>SECRET-{tag.upper()}-NAME</h1>"
        f"<ul><li>SECRET-{tag.upper()}-SERVICE</li></ul>"
        f'<a href="/SECRET-{tag.upper()}-LINK.html">hidden</a>'
        f"<p>SECRET-{tag.upper()} is licensed and insured.</p></{tag}>"
        f"<ul><li>Burst pipe repair</li></ul>"
        f"<p>Real prose a visitor can actually read, licensed and insured.</p>"
        f"</body></html>"
    )
    page = extract(html, URL)
    for field in dataclasses.fields(page):
        if field.name == "url":
            continue
        assert "SECRET" not in repr(getattr(page, field.name)), (
            f"{field.name} carries text no visitor ever saw"
        )
    assert "Burst pipe repair" in page.services, "and the visible list is still read"
    assert page.unique_selling_points, "and the visible prose is still read"


def test_svg_cannot_hide_markup_because_the_parser_takes_it_straight_back_out() -> None:
    """**THE EXCLUSION ABOVE, EXECUTED RATHER THAN ASSERTED.**

    In FOREIGN CONTENT the HTML tokeniser treats `h1`, `ul`, `li` and `a` as
    BREAKOUT elements: meeting one inside `<svg>` closes the svg and puts the
    element back in the document. So a `<ul>` inside an `<svg>` is a list a
    visitor really does see, there is nothing for `STRIPPED_TAGS` to protect, and
    the table above would be asserting something false rather than something
    strong. If a future parser stops breaking out, this fails and the exclusion
    gets looked at again.
    """
    page = extract(
        "<html><body><svg><h1>BROKE-OUT</h1><ul><li>BROKE-OUT-TOO</li></ul></svg>"
        "<p>and the page goes on.</p></body></html>",
        URL,
    )
    assert page.business_name == "BROKE-OUT", "the h1 is no longer inside the svg"
    assert "BROKE-OUT-TOO" in page.services
    assert "svg" in STRIPPED_TAGS and "svg" not in TAGS_THAT_CAN_HIDE_MARKUP


def test_svg_text_that_does_stay_inside_it_is_still_stripped() -> None:
    """The other half: what an `<svg>` really can hold - its own `<title>` and
    `<desc>` - is foreign content, stays inside, and is deleted with it."""
    page = extract(
        "<html><body><svg><title>SECRET-SVG-TITLE</title>"
        "<desc>SECRET-SVG-DESC</desc></svg><p>visible words</p></body></html>",
        URL,
    )
    assert "SECRET" not in repr(page)
    assert "visible words" in page.page_text


def test_the_stripped_tag_table_is_a_literal_and_names_the_six() -> None:
    """CONTENTS and SHAPE. Which tags carry text a visitor never saw is a
    judgement; a comprehension over some other table would be equal today and
    would stop recording it."""
    assert STRIPPED_TAGS == ("script", "style", "noscript", "template", "svg", "iframe")
    binding = _binding("STRIPPED_TAGS")
    assert isinstance(binding, ast.Tuple), "a literal tuple, not a comprehension"
    assert all(isinstance(element, ast.Constant) for element in binding.elts)


def test_json_ld_is_read_before_the_script_tags_are_deleted() -> None:
    """**THE ORDER OF TWO STATEMENTS IN `extract`, AND IT IS LOAD-BEARING.**
    JSON-LD lives inside a `<script>`, which `STRIPPED_TAGS` deletes. Deleting
    first would throw away the best source on the page and leave the guessing -
    and the page would still parse, still return a name, and still pass every
    test that did not put a DIFFERENT name in the heading. This one does."""
    html = (
        '<html><head><title>T</title><script type="application/ld+json">'
        '{"name":"From The Schema"}</script></head>'
        "<body><h1>From The Heading</h1></body></html>"
    )
    assert extract(html, URL).business_name == "From The Schema"


# --------------------------------------------------------------------------
# Services, selling points and their bounds
# --------------------------------------------------------------------------


def test_a_list_under_a_services_heading_is_preferred_to_the_navigation() -> None:
    """The navigation menu is a list of list items too, and on a real site it is
    the FIRST one. Preferring the list under a services heading is what stops
    "Home, About, Contact" being offered to a merchant as their services."""
    html = (
        "<html><body><ul><li>Home</li><li>About</li><li>Contact</li></ul>"
        "<h2>Our Services</h2><ul><li>Burst pipe repair</li></ul></body></html>"
    )
    assert extract(html, URL).services == ("Burst pipe repair",)


def test_with_no_services_heading_every_list_item_is_a_candidate() -> None:
    """The other half of the same judgement: a site with no headings must still
    contribute something, because a missing field is one the merchant types and
    a wrong one is one they delete."""
    html = "<html><body><ul><li>Drain clearing</li><li>Leak detection</li></ul></body></html>"
    assert extract(html, URL).services == ("Drain clearing", "Leak detection")


def test_a_list_item_longer_than_a_service_is_dropped() -> None:
    long_item = "x" * (MAX_SERVICE_LENGTH + 1)
    html = f"<html><body><ul><li>Leak detection</li><li>{long_item}</li></ul></body></html>"
    assert extract(html, URL).services == ("Leak detection",)


def test_services_are_capped_and_de_duplicated_in_page_order() -> None:
    """De-duplicated with `dict.fromkeys` rather than a set, because the page's
    own order is the site's idea of what matters most - and a set would replace
    it with an order that changes between runs under `PYTHONHASHSEED`."""
    items = "".join(f"<li>Service {index}</li>" for index in range(MAX_SERVICES + 10))
    html = f"<html><body><ul><li>Service 0</li>{items}</ul></body></html>"
    services = extract(html, URL).services
    assert len(services) == MAX_SERVICES
    assert services[0] == "Service 0"
    assert len(set(services)) == len(services)


def test_a_selling_point_is_a_sentence_carrying_one_of_the_markers() -> None:
    html = (
        "<html><body><p>We are licensed and insured. The van is blue. "
        "Same-day service, seven days a week.</p></body></html>"
    )
    points = extract(html, URL).unique_selling_points
    assert "We are licensed and insured." in points
    assert "The van is blue." not in points


def test_the_selling_point_markers_are_a_literal_judgement() -> None:
    """**A JUDGEMENT, PINNED AS ONE.** Which claims a trade business makes is not
    a fact about this codebase and no walk of the tree produces it, so it is
    written down - and a written-down judgement quietly replaced by a
    comprehension over some other table stops recording anything while every
    value assertion still passes. Contents AND length AND shape, because a table
    that silently shrinks reads exactly like one that was always short."""
    assert len(SELLING_POINT_MARKERS) == 17
    assert SELLING_POINT_MARKERS[0] == "licensed"
    assert "24/7" in SELLING_POINT_MARKERS
    assert all(marker == marker.lower() for marker in SELLING_POINT_MARKERS), (
        "matched against a lower-cased sentence, so an upper-cased marker never fires"
    )
    binding = _binding("SELLING_POINT_MARKERS")
    assert isinstance(binding, ast.Tuple), "a literal tuple, not a comprehension"
    assert all(isinstance(element, ast.Constant) for element in binding.elts)


BOUNDS = (
    ("MAX_SERVICES", MAX_SERVICES, 24),
    ("MAX_SERVICE_LENGTH", MAX_SERVICE_LENGTH, 80),
    ("MAX_SELLING_POINTS", MAX_SELLING_POINTS, 12),
    ("MAX_SELLING_POINT_LENGTH", MAX_SELLING_POINT_LENGTH, 200),
    ("MAX_LINKS", MAX_LINKS, 200),
)


@pytest.mark.parametrize("name,value,expected", BOUNDS)
def test_every_bound_is_a_literal_with_the_value_it_has(
    name: str, value: int, expected: int
) -> None:
    """Everything this module produces ends up in a prompt, so every bound here
    is a cost decision. Value and shape."""
    assert value == expected
    assert isinstance(_binding(name), ast.Constant)


def test_the_bounds_table_is_the_size_it_looks() -> None:
    assert len(BOUNDS) == 5


# --------------------------------------------------------------------------
# Links, which is what the crawl walks
# --------------------------------------------------------------------------


def test_relative_links_are_made_absolute_against_the_page() -> None:
    html = '<html><body><a href="/services.html">s</a><a href="about">a</a></body></html>'
    links = extract(html, "https://alphaplumbing.example/pages/index.html").links
    assert "https://alphaplumbing.example/services.html" in links
    assert "https://alphaplumbing.example/pages/about" in links


def test_a_fragment_is_dropped_so_one_page_is_not_crawled_twice() -> None:
    html = '<html><body><a href="/s#pricing">a</a><a href="/s">b</a></body></html>'
    assert extract(html, URL).links == ("https://alphaplumbing.example/s",)


NON_LINK_HREFS = (
    pytest.param("javascript:alert(1)", id="javascript"),
    pytest.param("data:text/html,<h1>x</h1>", id="data"),
    pytest.param("mailto:someone@example.com", id="mailto"),
    pytest.param("tel:+14165550134", id="tel"),
    pytest.param("file:///etc/passwd", id="file"),
    pytest.param("#top", id="a-bare-fragment"),
)


@pytest.mark.parametrize("href", NON_LINK_HREFS)
def test_a_link_the_crawler_cannot_fetch_is_not_offered_to_it(href: str) -> None:
    """`assert_safe_url` refuses every one of these anyway. Filtering here means
    the refusal is never REACHED, rather than reached and logged once per menu
    entry on every page of the site."""
    html = f'<html><body><a href="{href}">x</a></body></html>'
    assert extract(html, URL).links == ()


def test_the_non_link_table_is_the_size_it_looks() -> None:
    assert len(NON_LINK_HREFS) == 6


def test_the_link_schemes_are_the_two_the_crawler_speaks() -> None:
    assert LINK_SCHEMES == frozenset({"http", "https"})


def test_links_are_capped() -> None:
    html = "<html><body>" + "".join(
        f'<a href="/p{index}">x</a>' for index in range(MAX_LINKS + 5)
    ) + "</body></html>"
    assert len(extract(html, URL).links) == MAX_LINKS


# --------------------------------------------------------------------------
# The shapes a real site actually has
# --------------------------------------------------------------------------


EMPTY_PAGES = (
    pytest.param("", id="nothing-at-all"),
    pytest.param("<html></html>", id="no-body"),
    pytest.param("<html><head></head><body></body></html>", id="an-empty-body"),
    pytest.param("not markup, just words", id="not-markup"),
    pytest.param("<html><body><p>&lt;unclosed", id="unclosed-and-entity-encoded"),
)


@pytest.mark.parametrize("html", EMPTY_PAGES)
def test_a_page_with_nothing_on_it_is_an_empty_extract_rather_than_a_crash(html: str) -> None:
    """Empty string and empty tuple mean "this page did not say" - never `None`,
    because a caller counting characters would need a special case at every
    field."""
    page = extract(html, URL)
    assert isinstance(page, PageExtract)
    assert page.url == URL
    assert page.services == () and page.unique_selling_points == () and page.links == ()
    assert isinstance(page.business_name, str) and isinstance(page.page_text, str)


def test_the_empty_page_table_is_the_size_it_looks() -> None:
    assert len(EMPTY_PAGES) == 5


def test_an_extract_is_frozen() -> None:
    """An extract is evidence: `fetch.py` folds several into one result and
    nothing downstream may edit what a page said."""
    page = extract(HTML, URL)
    with pytest.raises(dataclasses.FrozenInstanceError):
        page.business_name = "something else"  # type: ignore[misc]


def test_the_fixture_site_index_reads_as_the_business_it_describes() -> None:
    """The end-to-end shape of this module against the file a human can open in
    a browser - the same bytes `tests/crawler/test_fetch.py` serves."""
    index = pathlib.Path(__file__).resolve().parents[2] / "fixture-site" / "index.html"
    page = extract(index.read_text(), "http://fixture-site/")
    assert page.business_name == "Alpha Plumbing"
    assert page.phone == "+1-416-555-0134"
    assert "12 King St W" in page.address
    assert "Burst pipe repair" in page.services
    assert any("licensed and insured" in point.lower() for point in page.unique_selling_points)
    assert "<" not in page.page_text
