"""The crawler, attacked at the seam Task 26 left open for it.

**READ `src/ppcway/crawler/ssrf.py`'s DOCSTRING FIRST, AND THEN `fetch.py`'s.**
`ssrf.py` states three obligations and can hold up only the first on its own.
The other two are this module's, and they are the reason most of what follows is
an attack rather than an exercise:

  2. the caller connects to `SafeTarget.addresses`, never to `SafeTarget.host`,
     and sends `host` as the `Host:` header and the TLS server name;
  3. at the moment of connection the caller calls `assert_safe_address` on the
     address it is ACTUALLY about to use.

**AND THE FAKE THAT TESTS THAT PROPERTY CAN VIOLATE IT.** Task 26's review named
the trap precisely: a fetch test driven by a fake client that answers to any
address cannot fail, because a fake that never resolves cannot be caught being
handed a name. So `FakeSite` in this package's `conftest.py` does what a real
client does - it looks at the host in the URL it was given and RESOLVES it if it
is a name - and `site.connections` is the measurement. Under a `SequenceResolver`
answering public-then-loopback, a crawler that hands over the name connects to
loopback and this file says so.

The other half of the same idea is `_pinned_transport`: `crawl` REFUSES an
ordinary `httpx.Client`, because one would resolve the host itself and put the
window straight back, with every functional test still green.
"""
import ast
import dataclasses
import gzip
import logging
import pathlib
import socket
import ssl
import tracemalloc
import zlib

import httpx
import pytest
from httpx._utils import URLPattern

from ppcway.crawler import fetch
from ppcway.crawler.fetch import (
    ACCEPT,
    ACCEPT_ENCODING,
    FETCH_FAILURES,
    HTML_CONTENT_TYPES,
    MAX_RESPONSE_BYTES,
    MIN_TEXT_FOR_A_USABLE_PROFILE,
    REDIRECT_STATUSES,
    ROBOTS_AGENT_TOKEN,
    SAFE_TARGET_EXTENSION,
    SNI_EXTENSION,
    SOURCE_CRAWLED,
    SOURCE_INSUFFICIENT,
    USER_AGENT,
    CrawlResult,
    PinnedAddressTransport,
    authority,
    build_client,
    crawl,
    parse_robots,
)
from ppcway.crawler.ssrf import (
    DEFAULT_PORTS,
    MAX_REDIRECTS,
    BlockedAddress,
    SafeTarget,
    assert_safe_url,
)
from tests.crawler.conftest import FakeResolver, FakeSite, Reply, SequenceResolver, address_info

FETCH_PATH = pathlib.Path(fetch.__file__).resolve()
FETCH_TREE = ast.parse(FETCH_PATH.read_text())

#: Names with no meaning to anything, so a fake resolver's mapping is the only
#: thing that decides what they resolve to.
HOST = "alphaplumbing.example"
URL = f"https://{HOST}/"
FIXTURE_HOST = "fixture-site"
FIXTURE_URL = "http://fixture-site/"

#: One address on the public internet, one that is not, and the one an attacker
#: wants the second DNS answer to be.
PUBLIC = "93.184.216.34"
SECOND_PUBLIC = "93.184.216.35"
LOOPBACK = "127.0.0.1"
PRIVATE = "10.0.0.5"


def a_site(pages, *, resolver=None, timeout=60.0):
    """A fake site and a pinned client over it.

    `resolver` is what the SITE resolves with, not what the crawl checks with -
    the two are separate on purpose, so a test can make the site's answer differ
    from the checked one and see which the connection used.
    """
    site = FakeSite(pages, resolver=resolver)
    return site, build_client(timeout_seconds=timeout, inner=site)


def run(client, url=FIXTURE_URL, *, resolver, max_pages=25, timeout_seconds=60.0, **kwargs):
    return crawl(
        url,
        max_pages=max_pages,
        timeout_seconds=timeout_seconds,
        rps_per_host=kwargs.pop("rps_per_host", 1000),
        client=client,
        resolver=resolver,
        **kwargs,
    )


@pytest.fixture()
def fixture_site():
    """`fixture-site/` off the repository root, served by a fake that WOULD
    rebind: its own resolver answers loopback, so any crawl that hands it a name
    instead of an address records a connection to `127.0.0.1`."""
    from tests.crawler.conftest import fixture_site_pages

    return FakeSite(fixture_site_pages(), resolver=FakeResolver({FIXTURE_HOST: LOOPBACK}))


@pytest.fixture()
def fixture_client(fixture_site):
    return build_client(timeout_seconds=60.0, inner=fixture_site)


@pytest.fixture()
def fixture_resolver():
    return FakeResolver({FIXTURE_HOST: PUBLIC})


def _binding(name):
    """The right-hand side of a module-level assignment in `fetch.py`, as AST."""
    for node in FETCH_TREE.body:
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
    raise AssertionError(f"fetch.py binds no module-level name {name}")


# --------------------------------------------------------------------------
# The crawl, end to end, against the fixture site
# --------------------------------------------------------------------------


def test_robots_txt_disallow_is_honoured(fixture_site, fixture_client, fixture_resolver) -> None:
    """**AND THE DISALLOWED PAGE IS LINKED AND EXISTS**, which is what makes this
    test mean anything. A "no page under /private" assertion against a site with
    no such page passes for the wrong reason; both halves are asserted here."""
    result = run(fixture_client, resolver=fixture_resolver)
    assert "/private.html" in [
        httpx.URL(link).path for page in result.pages for link in page.extract.links
    ], "the disallowed page must be reachable, or honouring robots.txt proves nothing"
    assert not any("/private" in page.url for page in result.pages)
    assert "/private.html" not in fixture_site.paths, (
        "not fetched-and-discarded: never requested at all"
    )


def test_the_page_cap_is_respected(fixture_site, fixture_client, fixture_resolver) -> None:
    result = run(fixture_client, resolver=fixture_resolver, max_pages=2)
    assert len(result.pages) == 2
    assert len([path for path in fixture_site.paths if path != "/robots.txt"]) == 2


def test_the_user_agent_identifies_ppcway_with_a_contact_url(
    fixture_site, fixture_client, fixture_resolver
) -> None:
    run(fixture_client, resolver=fixture_resolver, max_pages=1)
    agent = fixture_site.last_request.headers["user-agent"]
    assert "PPCWay" in agent and "http" in agent
    assert agent == USER_AGENT


def test_a_thin_site_reports_that_manual_entry_is_needed() -> None:
    """Blueprint §6.2: a meaningful share of SMB sites are JS-rendered or thin.
    The wizard must degrade to asking the merchant rather than generating
    plausible-sounding copy from nothing."""
    _site, client = a_site({"/": "<html><body><div id='root'></div></body></html>"})
    result = run(
        client, "https://thin.example/", resolver=FakeResolver({"thin.example": PUBLIC})
    )
    assert result.source == SOURCE_INSUFFICIENT
    assert len(result.page_text) < MIN_TEXT_FOR_A_USABLE_PROFILE


def test_a_site_with_enough_to_say_is_usable(fixture_client, fixture_resolver) -> None:
    """The other side of the same threshold: a real site must NOT come back as
    INSUFFICIENT, or the fallback is not a fallback, it is the only path."""
    result = run(fixture_client, resolver=fixture_resolver)
    assert result.source == SOURCE_CRAWLED
    assert len(result.page_text) >= MIN_TEXT_FOR_A_USABLE_PROFILE


def test_the_whole_site_folds_into_one_profile(fixture_client, fixture_resolver) -> None:
    result = run(fixture_client, resolver=fixture_resolver)
    assert isinstance(result, CrawlResult)
    assert result.business_name == "Alpha Plumbing"
    assert result.phone == "+1-416-555-0134"
    assert "12 King St W" in result.address
    assert "Burst pipe repair" in result.services
    assert "Backflow testing and certification" in result.services, (
        "services from a second page must reach the profile, or the crawl is a fetch"
    )
    assert "Alpha Plumbing" in result.meta_title


def test_a_page_is_never_fetched_twice(fixture_site, fixture_client, fixture_resolver) -> None:
    """Every page of the fixture site links to every other, so a crawler with no
    `seen` set fetches the home page three times."""
    run(fixture_client, resolver=fixture_resolver)
    assert len(fixture_site.paths) == len(set(fixture_site.paths))


def test_a_link_to_another_site_is_not_followed(
    fixture_site, fixture_client, fixture_resolver
) -> None:
    """`index.html` links to `example.org`. Same host AND scheme AND port, and
    compared to the ENTRY target rather than to the page the link was found on -
    a chain of same-host redirects ending elsewhere must not widen the crawl."""
    run(fixture_client, resolver=fixture_resolver)
    assert all(host == FIXTURE_HOST for host, _ in fixture_resolver.calls)
    assert all(request.headers["host"] == FIXTURE_HOST for request in fixture_site.requests)


#: **ONE CASE PER COMPARISON, EACH DIFFERING IN THAT COMPARISON ALONE.** This
#: table is the answer to a measured failure: `_same_site` could be reduced to
#: ANY ONE of its three comparisons with the whole suite green, because the only
#: off-site link in the fixture corpus (`https://example.org/`) differs from the
#: entry (`http://fixture-site/`) in scheme AND host at once, so any one
#: surviving comparison still rejected it. A test that passes on the scheme alone
#: proves nothing about the host, and the host is the one whose absence sends the
#: crawler off to spend a merchant's page budget on somebody else's site.
ENTRY_ORIGIN = SafeTarget(
    url="http://alphaplumbing.example:443/",
    scheme="http",
    host=HOST,
    port=443,
    addresses=(PUBLIC,),
)
SAME_SITE_CASES = (
    pytest.param(f"http://{HOST}:443/services", True, id="the-same-origin"),
    pytest.param("http://elsewhere.example:443/", False, id="only-the-host-differs"),
    pytest.param(f"https://{HOST}:443/", False, id="only-the-scheme-differs"),
    pytest.param(f"http://{HOST}:80/", False, id="only-the-port-differs"),
)


@pytest.mark.parametrize("candidate,same", SAME_SITE_CASES)
def test_each_half_of_same_site_is_pinned_by_a_case_where_only_it_refuses(
    candidate: str, same: bool
) -> None:
    """The entry is deliberately `http` on port 443 - which `ALLOWED_PORTS` and
    `ALLOWED_SCHEMES` really do permit - because that is the only origin from
    which a link can differ in the scheme alone AND in the port alone."""
    assert fetch._same_site(candidate, ENTRY_ORIGIN) is same


def test_the_same_site_table_names_each_comparison_once() -> None:
    assert len(SAME_SITE_CASES) == 4
    assert sum(1 for param in SAME_SITE_CASES if param.values[1]) == 1, (
        "one positive control, and one negative per comparison - a table with no positive "
        "row is passed by a function that returns False"
    )


def test_a_link_to_another_host_on_the_same_scheme_is_not_followed() -> None:
    """The same property end to end, through the comparison the fixture corpus
    could not exercise: an off-site link that differs from the entry in the HOST
    and in nothing else. Two measurements, because a crawler that queued it and
    then failed to fetch it would look identical from the pages alone: the other
    host was never resolved, and never asked for."""
    site, client = a_site(
        {
            "/": Reply(
                body=b'<html><body><p>home page words</p>'
                b'<a href="http://elsewhere.example/deals">supplier</a>'
                b'<a href="/second">ours</a></body></html>'
            ),
            "/second": Reply(body=b"<html><body><p>the second page</p></body></html>"),
        }
    )
    resolver = FakeResolver({HOST: PUBLIC, "elsewhere.example": SECOND_PUBLIC})

    result = run(client, URL, resolver=resolver)

    assert [page.url for page in result.pages] == [URL, f"{URL}second"]
    assert all(host == HOST for host, _ in resolver.calls), (
        "the other host was resolved, which means it was queued"
    )
    assert all(request.headers["host"] == HOST for request in site.requests)


# --------------------------------------------------------------------------
# OBLIGATION 3: the address that was checked is the address connected to
# --------------------------------------------------------------------------


def test_the_crawl_connects_to_the_judged_address_and_never_resolves_again(
    fixture_site, fixture_client, fixture_resolver
) -> None:
    """**THE PROPERTY THE WHOLE OF TASK 26 EXISTS FOR, AT THE CRAWL LEVEL.**

    The site's own resolver answers `127.0.0.1` for this host. So if `fetch.py`
    handed the transport `SafeTarget.host`, the site would resolve it, connect to
    loopback, and still serve every page - every functional test above would stay
    green. Two independent measurements say it did not: every connection went to
    the address the check approved, and the site never had to look anything up.
    """
    run(fixture_client, resolver=fixture_resolver)
    assert fixture_site.connections and set(fixture_site.connections) == {PUBLIC}
    assert fixture_site.resolutions == [], (
        "the site resolved a name, which means it was handed one - that is the "
        "rebinding window this module exists to close"
    )


def test_a_name_that_rebinds_between_the_check_and_the_connection_cannot_move_the_target(
    rebinding_resolver,
) -> None:
    """**DNS REBINDING, EXECUTED, AT THE TRANSPORT.**

    `SequenceResolver` answers the public address to the FIRST caller and
    loopback to every caller after it, which is what an attacker with a
    one-second TTL serves. The check resolves once and approves the public
    address; the transport is then handed that address rather than the name, so
    the site never gets to ask the second question. Both halves are asserted:
    where the connection went, and that only one lookup happened at all.
    """
    resolver = rebinding_resolver(HOST, [PUBLIC, LOOPBACK])
    site, client = a_site({"/": "<html><body>ok</body></html>"}, resolver=resolver)
    target = assert_safe_url(URL, resolver=resolver)
    assert target.addresses == (PUBLIC,), "the check saw the FIRST answer"

    request = client.build_request("GET", URL, extensions={SAFE_TARGET_EXTENSION: target})
    client.send(request).close()

    assert site.connections == [PUBLIC]
    assert len(resolver.calls) == 1, "a second lookup is the rebinding window, whoever made it"
    assert site.resolutions == []


def test_the_rebinding_resolver_really_does_rebind(rebinding_resolver) -> None:
    """**THE CONTROL FOR THE TEST ABOVE.** A resolver that answered the public
    address twice would make that test pass while proving nothing, so the second
    answer is measured here rather than assumed."""
    resolver = rebinding_resolver(HOST, [PUBLIC, LOOPBACK])
    assert resolver(HOST, 443)[0][4][0] == PUBLIC
    assert resolver(HOST, 443)[0][4][0] == LOOPBACK


def test_handing_the_transport_a_name_instead_of_an_address_is_refused(
    rebinding_resolver,
) -> None:
    """**THE MIS-WIRING THIS DESIGN EXISTS TO PREVENT, DONE ON PURPOSE.**

    A `SafeTarget` whose `addresses` carries the HOST NAME is what a `fetch.py`
    written to the plan's brief would produce. It does not ship green: the
    connect-time check parses its argument with `ipaddress.ip_address`, so a name
    is refused before the inner transport is reached at all. Both halves - the
    refusal, and that nothing connected - because a refusal AFTER a connection
    would be no defence.
    """
    resolver = rebinding_resolver(HOST, [PUBLIC, LOOPBACK])
    site, client = a_site({"/": "<html><body>ok</body></html>"}, resolver=resolver)
    named = SafeTarget(url=URL, scheme="https", host=HOST, port=443, addresses=(HOST,))

    with pytest.raises(BlockedAddress):
        client.send(client.build_request("GET", URL, extensions={SAFE_TARGET_EXTENSION: named}))

    assert site.connections == []
    assert site.requests == []


def test_every_address_is_checked_separately_rather_than_only_the_first() -> None:
    """A host with two addresses is tried in order, so "the first one was fine"
    must say nothing about the second. The first address here refuses to connect
    and the second is private: the fallback must be REFUSED, not taken."""
    site, client = a_site({"/": Reply(error=httpx.ConnectError("no route"))})
    mixed = SafeTarget(
        url=URL, scheme="https", host=HOST, port=443, addresses=(PUBLIC, PRIVATE)
    )
    with pytest.raises(BlockedAddress):
        client.send(client.build_request("GET", URL, extensions={SAFE_TARGET_EXTENSION: mixed}))
    assert site.connections == [PUBLIC], "the second address must never have been connected to"


def test_a_second_address_is_tried_when_the_first_will_not_connect() -> None:
    """The other side of the same loop: a host with one dead address and one
    working one is still fetched, or a site behind a stale A record is
    unreachable for no reason."""
    site = FakeSite({"/": "<html><body>ok</body></html>"})
    dead = {PUBLIC}

    class _Flaky(FakeSite):
        def handle_request(self, request):
            if request.url.host in dead:
                self.connections.append(request.url.host)
                raise httpx.ConnectError("no route")
            return super().handle_request(request)

    site = _Flaky({"/": "<html><body>ok</body></html>"})
    client = build_client(timeout_seconds=60.0, inner=site)
    target = SafeTarget(
        url=URL, scheme="https", host=HOST, port=443, addresses=(PUBLIC, SECOND_PUBLIC)
    )
    response = client.send(
        client.build_request("GET", URL, extensions={SAFE_TARGET_EXTENSION: target})
    )
    response.close()
    assert response.status_code == 200
    assert site.connections == [PUBLIC, SECOND_PUBLIC]


def test_the_checked_value_and_the_connected_value_are_the_same_variable() -> None:
    """**A STRUCTURAL PIN, BECAUSE THE ALTERNATIVE IS BEHAVIOURALLY INVISIBLE.**

    Checking `addresses[0]` and connecting to `addresses[1]` is caught above by a
    target whose second address is private - but only while a target with a bad
    address is reachable at all. This reads the loop and asserts the two
    statements name the SAME local: `assert_safe_address(address)` first, then
    `copy_with(host=address)`, adjacent, with the loop variable in both.
    """
    handle = _handle_request()
    loops = [node for node in ast.walk(handle) if isinstance(node, ast.For)]
    assert len(loops) == 1, "one loop over the addresses"
    loop = loops[0]
    variable = loop.target.id

    checked = loop.body[0].value
    assert isinstance(checked, ast.Call) and checked.func.id == "assert_safe_address"
    assert isinstance(checked.args[0], ast.Name) and checked.args[0].id == variable

    aimed = loop.body[1]
    assert isinstance(aimed, ast.Assign)
    keywords = {keyword.arg: keyword.value for keyword in aimed.value.keywords}
    assert isinstance(keywords["host"], ast.Name) and keywords["host"].id == variable, (
        "the address that is checked must be the address that is connected to, and the only "
        "way to say that in a way nothing can drift out of is to use one variable"
    )


def _handle_request():
    for node in ast.walk(FETCH_TREE):
        if isinstance(node, ast.ClassDef) and node.name == "PinnedAddressTransport":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == "handle_request":
                    return child
    raise AssertionError("PinnedAddressTransport.handle_request is not in fetch.py")


# --------------------------------------------------------------------------
# OBLIGATION 2: the name is still what the Host header and the certificate say
# --------------------------------------------------------------------------


def test_the_host_header_is_the_name_and_never_the_address(
    fixture_site, fixture_client, fixture_resolver
) -> None:
    run(fixture_client, resolver=fixture_resolver)
    for request in fixture_site.requests:
        assert request.headers["host"] == FIXTURE_HOST
        assert PUBLIC not in request.headers["host"]


def test_the_tls_server_name_is_the_name_and_never_the_address(
    fixture_site, fixture_client, fixture_resolver
) -> None:
    """Without this the certificate is verified against an IP address, which no
    merchant's certificate names - so verification either fails on every HTTPS
    site or, worse, is quietly skipped."""
    run(fixture_client, resolver=fixture_resolver)
    for request in fixture_site.requests:
        assert request.extensions[SNI_EXTENSION] == FIXTURE_HOST


def test_the_transport_overrides_a_host_header_it_was_handed() -> None:
    """**THE TRANSPORT SETS THE HEADER, NOT THE CALLER**, and that is what makes
    the line load-bearing rather than a restatement of what httpx already did.
    httpx fills `Host:` in from the request's URL at build time, so for `_send`'s
    own requests the two agree - and a caller that built the request some other
    way would otherwise put whatever it liked in front of the merchant's server,
    including a name the check never saw."""
    site, client = a_site({"/": "<html><body>ok</body></html>"})
    target = assert_safe_url(URL, resolver=FakeResolver({HOST: PUBLIC}))
    request = client.build_request(
        "GET", URL, headers={"Host": "somewhere.else.example"},
        extensions={SAFE_TARGET_EXTENSION: target},
    )
    client.send(request).close()
    assert site.last_request.headers["host"] == HOST


def test_the_redirect_cap_is_the_shared_constant_rather_than_a_copy() -> None:
    """**A JUDGEMENT OWNED BY `ssrf.py`, CONSUMED HERE, NOT RE-DECIDED HERE.**
    `MAX_REDIRECTS` is pinned to 5 as a literal in `test_ssrf.py`; a `5` written
    into this loop as well is equal today and is two judgements pretending to be
    one, which is how the two drift. Nothing behavioural can tell them apart
    while they agree, so this reads the loop instead.

    **AND THERE IS EXACTLY ONE FUNCTION THAT MENTIONS IT**, which is the half
    added when `robots.txt` learned to follow redirects. Two callers now need a
    redirect loop, and giving `_robots_for` its own `range(MAX_REDIRECTS + 1)`
    would have been the cap written down twice AGAIN - the same defect, in the
    same module, inside the fix for a different one. `_follow` is the only loop,
    and this is what says so.
    """
    mentions = {
        node.name: [n.id for n in ast.walk(node) if isinstance(n, ast.Name)].count(
            "MAX_REDIRECTS"
        )
        for node in ast.walk(FETCH_TREE)
        if isinstance(node, ast.FunctionDef)
    }
    assert {name: count for name, count in mentions.items() if count} == {"_follow": 2}, (
        "one function bounds the chain, and inside it the loop bound and the log line - a "
        "cap written down twice is two bounds enforcing each other, which the battery proved "
        "makes every single mutation of either one an equivalent mutant"
    )
    body = next(
        node
        for node in ast.walk(FETCH_TREE)
        if isinstance(node, ast.FunctionDef) and node.name == "_follow"
    )
    numbers = [
        n.value for n in ast.walk(body) if isinstance(n, ast.Constant) and isinstance(n.value, int)
    ]
    assert MAX_REDIRECTS not in numbers, "the cap is named, not spelled out a second time"


def test_the_tls_extension_is_the_one_httpcore_actually_reads() -> None:
    """**THE STRING IS A CONTRACT WITH ANOTHER LIBRARY, SO IT IS DERIVED FROM
    THAT LIBRARY RATHER THAN BELIEVED.**

    A typo here is NOT silent, which is the opposite of what this docstring used
    to say. Executed against a real TLS server on loopback: httpcore falls back
    to the connection's host, which after the rewrite is an IP literal, and
    Python's `ssl` verifies an IP literal against the certificate's `iPAddress`
    SANs - so every HTTPS fetch fails with `CERTIFICATE_VERIFY_FAILED: IP address
    mismatch` rather than skipping verification. Fail-closed, and impossible to
    miss in production.

    This grep is therefore a cheap tripwire rather than the only thing standing
    between us and an unverified connection, and it is worth keeping as one: it
    is the test that fails when httpcore RENAMES the key, before anything has to
    open a socket. `test_transport_over_loopback.py` is the stronger check that
    this docstring's old sentence would have argued against writing.
    """
    import inspect

    from httpcore import _sync

    source = pathlib.Path(inspect.getfile(_sync.connection)).read_text()
    assert f'extensions.get("{SNI_EXTENSION}"' in source
    assert "server_hostname" in source


HOST_HEADERS = (
    pytest.param("https", 443, HOST, HOST, id="https-on-its-default-port"),
    pytest.param("http", 80, HOST, HOST, id="http-on-its-default-port"),
    pytest.param("http", 443, HOST, f"{HOST}:443", id="http-on-443-which-is-allowed"),
    pytest.param("https", 80, HOST, f"{HOST}:80", id="https-on-80-which-is-allowed"),
    pytest.param("https", 443, "2606:2800::1", "[2606:2800::1]", id="an-ipv6-literal-host"),
)


@pytest.mark.parametrize("scheme,port,host,expected", HOST_HEADERS)
def test_the_host_header_is_written_the_way_http_requires(
    scheme: str, port: int, host: str, expected: str
) -> None:
    """**EVERY CONFIGURATION THAT CAN REACH THIS, NOT THE USUAL ONE.**
    `ALLOWED_PORTS` is `{80, 443}` and `ALLOWED_SCHEMES` is `{http, https}`, so
    `http://host:443/` passes the SSRF check and needs a port in the header; and
    `SafeTarget.host` comes from `urlsplit().hostname`, which STRIPS the brackets
    off an IPv6 literal, so putting them back is this function's job."""
    target = SafeTarget(
        url=URL, scheme=scheme, host=host, port=port, addresses=(PUBLIC,)
    )
    assert authority(target) == expected


def test_the_host_header_table_is_the_size_it_looks() -> None:
    assert len(HOST_HEADERS) == 5


# --------------------------------------------------------------------------
# The transport refuses anything it was not given a judgement for
# --------------------------------------------------------------------------


def test_a_request_with_no_checked_target_is_refused() -> None:
    site, client = a_site({"/": "<html><body>ok</body></html>"})
    with pytest.raises(BlockedAddress):
        client.send(client.build_request("GET", URL))
    assert site.connections == []


MISMATCHED_TARGETS = (
    pytest.param("https", "elsewhere.example", 443, id="a-different-host"),
    pytest.param("http", HOST, 443, id="a-different-scheme"),
    pytest.param("https", HOST, 80, id="a-different-port"),
)


@pytest.mark.parametrize("scheme,host,port", MISMATCHED_TARGETS)
def test_a_target_that_describes_a_different_destination_is_refused(
    scheme: str, host: str, port: int
) -> None:
    """A judgement is about an origin. Re-using one for a different origin is how
    a redirect that httpx followed by itself would reach an unchecked host."""
    site, client = a_site({"/": "<html><body>ok</body></html>"})
    target = SafeTarget(url=URL, scheme=scheme, host=host, port=port, addresses=(PUBLIC,))
    with pytest.raises(BlockedAddress):
        client.send(client.build_request("GET", URL, extensions={SAFE_TARGET_EXTENSION: target}))
    assert site.connections == []


def test_the_mismatched_target_table_is_the_size_it_looks() -> None:
    assert len(MISMATCHED_TARGETS) == 3


#: **THE ONE CLASS OF HOST THE TWO PARSERS SPELL DIFFERENTLY.** `SafeTarget.host`
#: comes from `urlsplit().hostname`, which leaves punycode alone; `httpx.URL.host`
#: DECODES it to Unicode. Everything else - case, a trailing dot, an IP literal,
#: an IDN typed in Unicode - the two agree on, which is why nothing in-tree
#: noticed that a merchant typing their own IDN the way their registrar shows it
#: had every crawl refused before it made a single request.
IDN_SPELLINGS = (
    pytest.param("xn--bcher-kva.example", "bücher.example", True, id="punycode-versus-unicode"),
    pytest.param("bücher.example", "bücher.example", True, id="unicode-both-sides"),
    pytest.param("xn--bcher-kva.example", "xn--bcher-kva.example", True, id="punycode-both-sides"),
    pytest.param("example.com", "example.com", True, id="an-ordinary-name"),
    pytest.param("example.com", "example.org", False, id="genuinely-different-hosts"),
    pytest.param("bücher.example", "bcher.example", False, id="one-character-apart"),
    pytest.param("example.com", "93.184.216.34", False, id="a-name-and-an-address"),
    pytest.param("a" * 64 + ".example", "bücher.example", False, id="a-host-idna-cannot-encode"),
)


@pytest.mark.parametrize("checked,requested,same", IDN_SPELLINGS)
def test_two_spellings_of_one_host_are_one_host_and_two_hosts_are_not(
    checked: str, requested: str, same: bool
) -> None:
    """The normalisation is IDNA in both directions, so it cannot widen anything:
    a label IDNA refuses to encode is not equal to anything, and two different
    names cannot encode to one."""
    assert fetch._the_same_host(checked, requested) is same


def test_the_idn_spelling_table_is_the_size_it_looks() -> None:
    assert len(IDN_SPELLINGS) == 8
    assert sum(1 for param in IDN_SPELLINGS if not param.values[2]) == 4


def test_a_domain_typed_in_its_punycode_form_is_crawled_rather_than_refused() -> None:
    """**A REFUSAL WHOSE MESSAGE WAS NOT TRUE, AND THE MERCHANT IT LOCKED OUT.**

    `https://XN--BCHER-KVA.example/` is a real merchant's real domain, spelled the
    way their registrar, WHOIS record and hosting panel display it. It came back
    as "the crawler will not send a request to a different destination from the
    one that was checked" - the same host, the same address, the same port - with
    zero pages, every time, and no log line either, because the first request a
    crawl makes is `robots.txt`.
    """
    punycode = "xn--bcher-kva.example"
    site, client = a_site(
        {
            "/robots.txt": Reply(body=b"", content_type="text/plain"),
            "/": Reply(
                body="<html><body><h1>Bücher</h1><p>a bookshop</p></body></html>".encode()
            ),
        }
    )
    result = run(client, f"https://{punycode}/", resolver=FakeResolver({punycode: PUBLIC}))

    assert [page.url for page in result.pages] == [f"https://{punycode}/"]
    assert site.connections == [PUBLIC, PUBLIC], "and it still connected to the judged address"
    assert all(request.headers["host"] == punycode for request in site.requests), (
        "the Host header is the name the merchant typed, not the one httpx decoded"
    )


def test_a_target_that_approved_no_addresses_is_refused() -> None:
    """`assert_safe_url` cannot produce one, which is exactly why the transport
    checks: a guard whose only in-tree producer cannot violate it is untested."""
    site, client = a_site({"/": "<html><body>ok</body></html>"})
    empty = SafeTarget(url=URL, scheme="https", host=HOST, port=443, addresses=())
    with pytest.raises(BlockedAddress):
        client.send(client.build_request("GET", URL, extensions={SAFE_TARGET_EXTENSION: empty}))
    assert site.connections == []


# --------------------------------------------------------------------------
# `crawl` refuses a client that would resolve the host itself
# --------------------------------------------------------------------------


def test_an_ordinary_httpx_client_is_refused() -> None:
    """**THE HOLE THIS TASK'S BRIEF WOULD HAVE LEFT.** An `httpx.Client` resolves
    the host itself, so accepting one puts the rebinding window back exactly
    where it was - and every functional test in this file would still pass,
    because a fake site answers to any address."""
    site = FakeSite({"/": "<html><body>ok</body></html>"})
    with pytest.raises(BlockedAddress):
        run(httpx.Client(transport=site), URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert site.requests == []


def test_a_client_with_mounted_transports_is_refused() -> None:
    """Mounts route a URL PATTERN to a different transport, which bypasses the
    pinned one for exactly the URLs an attacker would choose."""
    site = FakeSite({"/": "<html><body>ok</body></html>"})
    client = build_client(timeout_seconds=60.0, inner=site)
    client._mounts = {URLPattern("all://"): site}
    with pytest.raises(BlockedAddress):
        run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))


def test_a_client_that_follows_redirects_itself_is_refused() -> None:
    """httpx following a hop skips `assert_safe_redirect` - which is the whole
    check, not a formality."""
    site = FakeSite({"/": "<html><body>ok</body></html>"})
    client = build_client(timeout_seconds=60.0, inner=site)
    client.follow_redirects = True
    with pytest.raises(BlockedAddress):
        run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))


def test_build_client_puts_the_pinned_transport_where_the_guard_looks() -> None:
    """`_transport` and `_mounts` are httpx internals, which is a real cost. This
    is what makes the cost visible: if a future httpx renames either, this fails
    rather than the guard silently passing everything."""
    site = FakeSite({})
    client = build_client(timeout_seconds=1.0, inner=site)
    assert isinstance(client._transport, PinnedAddressTransport)
    assert client._transport.inner is site
    assert client._mounts == {}
    assert client.follow_redirects is False


def test_build_client_defaults_to_a_real_transport() -> None:
    """The production path: no inner transport means httpx's own, which is the
    thing that opens a socket. Constructed, not used - the network ban is in
    force and would refuse any actual connection."""
    client = build_client(timeout_seconds=1.0)
    assert isinstance(client._transport.inner, httpx.HTTPTransport)
    client.close()


# --------------------------------------------------------------------------
# Redirects: every hop checked, and the cap applied
# --------------------------------------------------------------------------


def redirect_chain(hops: int) -> dict[str, Reply]:
    """`/hop/0` through `/hop/{hops-1}` redirect; `/hop/{hops}` is a page."""
    pages: dict[str, Reply] = {
        f"/hop/{index}": Reply(status=302, location=f"/hop/{index + 1}")
        for index in range(hops)
    }
    pages[f"/hop/{hops}"] = Reply(
        body=b"<html><body><h1>Arrived</h1><p>the end of the chain</p></body></html>"
    )
    return pages


def test_a_redirect_to_a_private_address_is_blocked_after_the_hop() -> None:
    """Re-validate after every redirect, not only at the start."""
    _site, client = a_site({"/": Reply(status=302, location="https://internal.example/")})
    with pytest.raises(BlockedAddress):
        run(
            client,
            URL,
            resolver=FakeResolver({HOST: PUBLIC, "internal.example": PRIVATE}),
        )


def test_a_chain_that_only_turns_hostile_on_the_third_hop_is_caught_there() -> None:
    """The first URL a merchant gives is the one a human looks at; the third hop
    is not."""
    pages = {
        "/": Reply(status=302, location="/two"),
        "/two": Reply(status=302, location="/three"),
        "/three": Reply(status=302, location="https://internal.example/"),
    }
    site, client = a_site(pages)
    with pytest.raises(BlockedAddress):
        run(client, URL, resolver=FakeResolver({HOST: PUBLIC, "internal.example": PRIVATE}))
    assert site.paths == ["/robots.txt", "/", "/two", "/three"]


def test_a_chain_longer_than_the_cap_is_abandoned_rather_than_followed() -> None:
    """**SIX HOPS AGAINST A CAP OF FIVE.** Neither `ssrf.py` nor anything before
    this task enforced `MAX_REDIRECTS`; the loop here does. Three assertions,
    because the count alone would pass if the cap were off by one in the other
    direction: the requests made, the page never reached, and nothing returned.
    """
    site, client = a_site(redirect_chain(MAX_REDIRECTS + 1))
    result = run(
        client,
        f"{URL}hop/0",
        resolver=FakeResolver({HOST: PUBLIC}),
    )
    hops = [path for path in site.paths if path.startswith("/hop/")]
    assert hops == [f"/hop/{index}" for index in range(MAX_REDIRECTS + 1)]
    assert f"/hop/{MAX_REDIRECTS + 1}" not in site.paths
    assert result.pages == ()


def test_a_chain_at_the_cap_whose_last_hop_is_unsafe_is_refused() -> None:
    """**WHAT THE SINGLE BOUND COSTS, PINNED AS A DECISION RATHER THAN LEFT AS A
    SIDE EFFECT.** The cap is said once, as the number of REQUESTS, so the last
    `Location` on an over-long chain is still resolved and checked before the
    loop ends - it is simply never fetched. That makes an over-long chain ending
    at a private address a refusal rather than a quiet give-up, which is the more
    useful of the two true answers: the site really is pointing us there."""
    pages = {
        f"/hop/{index}": Reply(status=302, location=f"/hop/{index + 1}")
        for index in range(MAX_REDIRECTS)
    }
    pages[f"/hop/{MAX_REDIRECTS}"] = Reply(status=302, location="https://internal.example/")
    site, client = a_site(pages)
    with pytest.raises(BlockedAddress):
        run(
            client,
            f"{URL}hop/0",
            resolver=FakeResolver({HOST: PUBLIC, "internal.example": PRIVATE}),
        )
    assert len([path for path in site.paths if path.startswith("/hop/")]) == MAX_REDIRECTS + 1


def test_a_chain_exactly_at_the_cap_is_followed_to_its_end() -> None:
    """The other side of the boundary. Without this, a cap of zero passes the
    test above."""
    site, client = a_site(redirect_chain(MAX_REDIRECTS))
    result = run(client, f"{URL}hop/0", resolver=FakeResolver({HOST: PUBLIC}))
    assert [page.url for page in result.pages] == [f"{URL}hop/{MAX_REDIRECTS}"]
    assert len([path for path in site.paths if path.startswith("/hop/")]) == MAX_REDIRECTS + 1


def test_a_redirect_loop_is_bounded_without_being_detected() -> None:
    """A cap is not a security control - every hop is re-checked, so hop five is
    judged exactly as hop one - it is what stops a loop becoming an unbounded
    crawl, and it does that without anyone having to notice it is a loop."""
    site, client = a_site(
        {"/a": Reply(status=302, location="/b"), "/b": Reply(status=302, location="/a")}
    )
    result = run(client, f"{URL}a", resolver=FakeResolver({HOST: PUBLIC}))
    assert len([path for path in site.paths if path in ("/a", "/b")]) == MAX_REDIRECTS + 1
    assert result.pages == ()


@pytest.mark.parametrize("status", sorted(REDIRECT_STATUSES))
def test_every_redirect_status_is_followed(status: int) -> None:
    _site, client = a_site(
        {
            "/": Reply(status=status, location="/moved"),
            "/moved": Reply(body=b"<html><body><p>moved here</p></body></html>"),
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert [page.url for page in result.pages] == [f"{URL}moved"]


def test_the_redirect_status_table_is_the_size_it_looks() -> None:
    assert REDIRECT_STATUSES == frozenset({301, 302, 303, 307, 308})
    assert isinstance(_binding("REDIRECT_STATUSES"), ast.Call)


# --------------------------------------------------------------------------
# Failures, across hierarchies that do not agree
# --------------------------------------------------------------------------
#
# **A FAKE THAT RAISES ONLY THE ERRORS YOU THOUGHT OF HIDES THE ONES YOU DID
# NOT.** That is Task 26's own finding, from a real defect that shipped because
# the only resolver in the tree raised `gaierror` and nothing else. The seam here
# is an injected HTTP client, and httpx raises several types that are not
# `OSError` while `ssl` raises one that is - so the table below deliberately
# spans both, and the test after it asserts that it does.

FETCH_FAILURE_TABLE = (
    pytest.param(httpx.ConnectError("connection refused"), id="connect-error"),
    pytest.param(httpx.ConnectTimeout("timed out connecting"), id="connect-timeout"),
    pytest.param(httpx.ReadTimeout("timed out reading"), id="read-timeout"),
    pytest.param(httpx.RemoteProtocolError("server disconnected"), id="remote-protocol"),
    pytest.param(httpx.UnsupportedProtocol("no such scheme"), id="unsupported-protocol"),
    pytest.param(httpx.PoolTimeout("no connection free"), id="pool-timeout"),
    pytest.param(ssl.SSLCertVerificationError("certificate has expired"), id="ssl-verification"),
    pytest.param(ssl.SSLError("record layer failure"), id="ssl-error"),
    pytest.param(ConnectionResetError("connection reset by peer"), id="a-bare-oserror"),
    pytest.param(socket.gaierror(socket.EAI_NONAME, "nodename"), id="gaierror"),
    pytest.param(
        zlib.error("Error -3 while decompressing data: incorrect header check"),
        id="a-body-that-is-not-the-gzip-it-claims-to-be",
    ),
)


@pytest.mark.parametrize("failure", FETCH_FAILURE_TABLE)
def test_a_page_that_will_not_load_is_skipped_rather_than_ending_the_crawl(
    failure: BaseException,
) -> None:
    """One page refusing to load must not end a crawl. The ENTRY page failing
    leaves a result with no pages, which is `INSUFFICIENT` and is a fallback
    rather than a crash."""
    _site, client = a_site({"/": Reply(error=failure)})
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert result.pages == ()
    assert result.source == SOURCE_INSUFFICIENT


@pytest.mark.parametrize("failure", FETCH_FAILURE_TABLE)
def test_one_bad_page_does_not_stop_the_rest_of_the_site(failure: BaseException) -> None:
    _site, client = a_site(
        {
            "/": Reply(
                body=b'<html><body><p>home</p><a href="/broken">b</a>'
                b'<a href="/good">g</a></body></html>'
            ),
            "/broken": Reply(error=failure),
            "/good": Reply(body=b"<html><body><p>the good page</p></body></html>"),
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert [page.url for page in result.pages] == [URL, f"{URL}good"]


def test_the_fetch_failure_table_spans_outside_every_base_it_names() -> None:
    """**THE COMPLETENESS HALF, AND IT IS WRITTEN AS A LOOP FOR A REASON.** A
    table of eleven `httpx.ConnectError`s would pass every test above and would
    prove that one base class is caught. Every row is checked to be caught, and
    for EVERY base at least one row is asserted to live outside it, so no base
    can be deleted quietly - which two hand-written assertions could not promise
    when a fourth base arrived. `zlib.error` is that fourth: it derives from
    `Exception` alone, and it reaches this module because the response reader
    stopped using httpx's decoder and so stopped inheriting httpx's wrapper."""
    failures = [param.values[0] for param in FETCH_FAILURE_TABLE]
    assert len(FETCH_FAILURE_TABLE) == 11
    assert all(isinstance(failure, FETCH_FAILURES) for failure in failures)
    for base in FETCH_FAILURES:
        assert any(not isinstance(failure, base) for failure in failures), (
            f"every row is a {base.__name__}, so that base could be the only one and this "
            f"table would not notice the others being deleted"
        )
    assert FETCH_FAILURES == (httpx.HTTPError, OSError, zlib.error)
    assert not issubclass(zlib.error, (httpx.HTTPError, OSError)), (
        "the fourth base is a fourth base because nothing else contains it"
    )
    assert isinstance(_binding("FETCH_FAILURES"), ast.Tuple)


def test_a_refusal_is_not_a_failure() -> None:
    """`BlockedAddress` must not be swallowed by the failure catch. A refusal is
    a decision; folding it into "that page did not load" is how a security
    control becomes a log line nobody reads."""
    assert not issubclass(BlockedAddress, FETCH_FAILURES)


def test_the_fake_site_cannot_hide_a_lookup_failure_as_a_key_error() -> None:
    """The other half of the same lesson, aimed at this file's own fakes: a fake
    whose own failure is a `KeyError` would make `assert_safe_url` raise
    something no caller catches, and the test would still be green because the
    test expected an exception."""
    site = FakeSite({}, resolver=FakeResolver({HOST: PUBLIC}))
    with pytest.raises(socket.gaierror):
        site._connect("unknown.example", 443)
    with pytest.raises(socket.gaierror):
        FakeResolver({HOST: PUBLIC})("unknown.example", 443)
    with pytest.raises(socket.gaierror):
        SequenceResolver(HOST, [PUBLIC])("unknown.example", 443)


# --------------------------------------------------------------------------
# What a refusal says, and to whom
# --------------------------------------------------------------------------


def test_a_refusal_is_logged_with_the_address_and_rendered_without_it(caplog) -> None:
    """**THE CALLER'S HALF OF TASK 26's I3.** The message a merchant sees says
    WHY and never WHICH, or the onboarding form is an internal address
    enumeration oracle: submit `jenkins.corp.internal`, read `10.4.2.17` back out
    of the refusal, repeat. The operator reading the log needs exactly that, so
    it rides on the exception and is logged from there.

    The first `except BlockedAddress as e: return str(e)` written without this in
    mind undoes the whole of that fix, which is why both halves are asserted in
    one test - they are one property, not two.
    """
    _site, client = a_site({"/": "<html><body>ok</body></html>"})
    with (
        caplog.at_level(logging.WARNING, logger="ppcway.crawler.fetch"),
        pytest.raises(BlockedAddress) as refused,
    ):
        run(client, URL, resolver=FakeResolver({HOST: PRIVATE}))

    assert PRIVATE not in str(refused.value), "the merchant must not learn the address"
    assert refused.value.address == PRIVATE
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert PRIVATE in logged, "the operator must be told the address, and only here"


def _refused_at_the_entry_check():
    """The merchant's own hostname resolves somewhere private."""
    _site, client = a_site({"/": "<html><body>ok</body></html>"})
    return client, URL, FakeResolver({HOST: PRIVATE})


def _refused_at_a_redirect_hop():
    """The site answers 302 towards a private host. **THIS IS THE ROUTE THAT
    MATTERS MOST AND WAS THE ONE NOT PINNED**: on the entry path the merchant
    supplied the hostname and learns the address of a host they already named; on
    this path the address is the one their site was pointed AT - `10.4.2.17`
    behind `jenkins.corp.internal` - which is exactly the oracle
    `BlockedAddress.address` exists to close."""
    _site, client = a_site({"/": Reply(status=302, location="https://internal.example/")})
    return client, URL, FakeResolver({HOST: PUBLIC, "internal.example": PRIVATE})


def _refused_while_reading_robots_txt():
    """A host that rebinds between the entry check and the `robots.txt` request:
    answer one is the entry check, answer two is `robots.txt`. This refusal is
    raised inside `_robots_for`, which used to sit outside every handler `crawl`
    had - so it reached the caller with no log line at all."""
    _site, client = a_site({"/": "<html><body>ok</body></html>"})
    return client, URL, SequenceResolver(HOST, [PUBLIC, PRIVATE])


def _refused_because_the_client_is_not_pinned():
    """A refusal that never reached an address at all, through the third route
    out of `crawl` - the client guard, which also ran before any handler."""
    return httpx.Client(transport=FakeSite({"/": "<html><body>ok</body></html>"})), URL, (
        FakeResolver({HOST: PUBLIC})
    )


#: **EVERY WAY A REFUSAL CAN REACH THE CALLER OF `crawl`.** The property is one
#: property - the address is for the log and never for the merchant - and it was
#: pinned on ONE of these routes. Measured on the others: putting `refused.address`
#: into the message raised from the redirect path survived the whole suite, twice
#: over, including worded as a sentence a merchant would read.
REFUSAL_ROUTES = (
    pytest.param(_refused_at_the_entry_check, PRIVATE, id="the-entry-check"),
    pytest.param(_refused_at_a_redirect_hop, PRIVATE, id="a-redirect-hop"),
    pytest.param(_refused_while_reading_robots_txt, PRIVATE, id="reading-robots-txt"),
    pytest.param(_refused_because_the_client_is_not_pinned, None, id="an-unpinned-client"),
)


@pytest.mark.parametrize("route,address", REFUSAL_ROUTES)
def test_every_refusal_that_reaches_the_caller_says_why_and_never_which(
    route, address, caplog
) -> None:
    """**THE SAME TWO ASSERTIONS ON EVERY ROUTE OUT, BECAUSE IT IS ONE PROPERTY
    AND THE ROUTES ARE WHERE IT GETS FORGOTTEN.** `crawl` says "EVERY REFUSAL IS
    LOGGED WITH `BlockedAddress.address` AND RENDERED WITHOUT IT"; that sentence
    was false in both halves, each on a different route, and both were invisible
    because the only test of it drove the entry check.

    `PRIVATE not in str(...)` is asserted on every row including the ones that
    never resolved anything, so the table has no branch in it: the row's expected
    `.address` is what distinguishes them, and the log line is asserted to carry
    it either way - `None` included, since it is written unconditionally.
    """
    client, url, resolver = route()
    with (
        caplog.at_level(logging.WARNING, logger="ppcway.crawler.fetch"),
        pytest.raises(BlockedAddress) as refused,
    ):
        run(client, url, resolver=resolver)

    assert PRIVATE not in str(refused.value), "the merchant must not learn the address"
    assert refused.value.address == address
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert str(address) in logged, "the operator must be told the address, and only here"


def test_the_refusal_route_table_covers_every_way_out_of_the_crawl() -> None:
    """The completeness half. Four routes, and at least one that never reached an
    address, since that is the row the unconditional log line exists for."""
    assert len(REFUSAL_ROUTES) == 4
    assert sum(1 for param in REFUSAL_ROUTES if param.values[1] is None) == 1


def _rebinding_mid_crawl():
    """A site of two pages whose host turns private on the THIRD lookup.

    **THIS IS THE ONLY WAY A DISCOVERED LINK CAN BE REFUSED, AND FINDING THAT
    OUT IS WORTH RECORDING.** A link is only followed when it is on the same
    scheme, host and port as the entry, so it resolves the same way the entry
    did - a link to a private host is never queued at all, it is dropped by
    `_same_site` before any check runs. What CAN be refused is a host that
    rebinds mid-crawl: lookup one is the entry, two is `robots.txt`, three is the
    link, and three answers `10.0.0.5`.
    """
    resolver = SequenceResolver(HOST, [PUBLIC, PUBLIC, PRIVATE])
    site, client = a_site(
        {
            "/": Reply(
                body=b'<html><body><p>home page words</p>'
                b'<a href="/second">x</a></body></html>'
            ),
            "/second": Reply(body=b"<html><body><p>the second page</p></body></html>"),
        }
    )
    return site, client, resolver


def test_a_link_that_resolves_somewhere_private_is_logged_and_skipped(caplog) -> None:
    """The entry URL's refusal propagates - the merchant typed it and has to be
    told. A link found ON their site is a fact about their site, not about their
    request, so the crawl logs it and carries on with what it already had."""
    site, client, resolver = _rebinding_mid_crawl()
    with caplog.at_level(logging.WARNING, logger="ppcway.crawler.fetch"):
        result = run(client, URL, resolver=resolver)
    assert [page.url for page in result.pages] == [URL]
    assert "/second" not in site.paths
    assert PRIVATE in "\n".join(record.getMessage() for record in caplog.records)


def test_nothing_a_crawl_returns_carries_a_resolved_address() -> None:
    """The whole result, not just the message: a refusal that reached a field of
    `CrawlResult` would be the same disclosure by another route."""
    _site, client, resolver = _rebinding_mid_crawl()
    result = run(client, URL, resolver=resolver)
    assert PRIVATE not in repr(result)


def test_a_refusal_that_never_reached_an_address_is_still_logged(caplog) -> None:
    """`BlockedAddress.address` is `None` for a refusal that never resolved
    anything - an unusable scheme, a port. The log line is written
    unconditionally rather than branching, so `None` is what it says."""
    _site, client = a_site({"/": "<html><body>ok</body></html>"})
    with (
        caplog.at_level(logging.WARNING, logger="ppcway.crawler.fetch"),
        pytest.raises(BlockedAddress) as refused,
    ):
        run(client, "https://alphaplumbing.example:8080/", resolver=FakeResolver({}))
    assert refused.value.address is None
    assert "None" in "\n".join(record.getMessage() for record in caplog.records)


# --------------------------------------------------------------------------
# robots.txt
# --------------------------------------------------------------------------


ROBOTS_CASES = (
    pytest.param("User-agent: *\nDisallow: /private", "/private/x", False, id="a-prefix"),
    pytest.param("User-agent: *\nDisallow: /private", "/public", True, id="not-the-prefix"),
    pytest.param("User-agent: *\nDisallow: /", "/anything", False, id="everything"),
    pytest.param("User-agent: *\nDisallow:", "/anything", True, id="an-empty-disallow"),
    pytest.param("", "/anything", True, id="an-empty-file"),
    pytest.param(
        "User-agent: *\nDisallow: /\nAllow: /public/", "/public/x", True, id="longest-match-wins"
    ),
    pytest.param(
        "User-agent: *\nDisallow: /a\nAllow: /a", "/a", True, id="allow-breaks-a-tie"
    ),
    pytest.param(
        "User-agent: EvilBot\nDisallow: /\n\nUser-agent: *\nDisallow: /private",
        "/public",
        True,
        id="a-second-group-after-the-first",
    ),
    pytest.param(
        "User-agent: *\nDisallow: /\n\nUser-agent: PPCWay\nDisallow: /private",
        "/public",
        True,
        id="our-own-group-wins-over-the-star",
    ),
    pytest.param(
        "User-agent: *\nDisallow: /*.pdf$", "/manual.pdf", False, id="a-wildcard-and-an-anchor"
    ),
    pytest.param(
        "User-agent: *\nDisallow: /*.pdf$", "/manual.pdf.html", True, id="the-anchor-anchors"
    ),
    pytest.param(
        "User-agent: *  # trailing comment\nDisallow: /private # here too",
        "/private",
        False,
        id="comments",
    ),
    pytest.param("Disallow: /private", "/private", True, id="a-rule-with-no-group"),
    pytest.param("nonsense\nUser-agent: *\nDisallow: /x", "/x", False, id="a-line-with-no-colon"),
)


@pytest.mark.parametrize("text,path,allowed", ROBOTS_CASES)
def test_the_robots_reader_agrees_with_the_standard(
    text: str, path: str, allowed: bool
) -> None:
    assert parse_robots(text).allows(path) is allowed


def test_the_robots_case_table_is_the_size_it_looks() -> None:
    assert len(ROBOTS_CASES) == 14


def test_the_robots_token_is_the_one_in_the_user_agent() -> None:
    """The group we obey and the name we send have to be the same word, or a
    merchant who writes a rule for `PPCWay` is writing it for nobody."""
    assert ROBOTS_AGENT_TOKEN == "ppcway"
    assert ROBOTS_AGENT_TOKEN in USER_AGENT.lower()
    assert USER_AGENT.startswith("PPCWay/")
    assert "http" in USER_AGENT


ROBOTS_RESPONSES = (
    pytest.param(Reply(status=404, body=b"nope", content_type="text/plain"), True, id="404"),
    pytest.param(Reply(status=410, body=b"gone", content_type="text/plain"), True, id="410"),
    pytest.param(Reply(status=500, body=b"oops", content_type="text/plain"), False, id="500"),
    pytest.param(Reply(status=503, body=b"busy", content_type="text/plain"), False, id="503"),
    pytest.param(Reply(error=httpx.ConnectError("refused")), False, id="unreachable"),
)


@pytest.mark.parametrize("reply,crawls", ROBOTS_RESPONSES)
def test_an_unreadable_robots_file_decides_whether_the_crawl_happens(
    reply: Reply, crawls: bool
) -> None:
    """RFC 9309 §2.3.1: "unavailable" (4xx) means nothing is disallowed;
    "unreachable" (5xx, or no answer at all) means crawl NOTHING. The second
    costs us a merchant whose site is having a bad minute, and what it costs
    THEM is a wizard that asks three questions instead of reading the answers."""
    _site, client = a_site(
        {
            "/robots.txt": reply,
            "/": Reply(body=b"<html><body><p>home page words</p></body></html>"),
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert bool(result.pages) is crawls


def test_the_robots_response_table_is_the_size_it_looks() -> None:
    assert len(ROBOTS_RESPONSES) == 5


class Origins(FakeSite):
    """A fake serving SEVERAL origins, keyed by `scheme://host`.

    `FakeSite` is keyed by path because the host is not its to decide - by the
    time a request reaches it the URL's host is an ADDRESS, which is the whole
    point. So what says which site a request is for is the SCHEME of the URL,
    which the transport does not touch, plus the `Host:` header it wrote, which
    is the name that was checked. Together those are the origin, and the origin
    is what `robots.txt` belongs to and what the crawl is scoped to.
    """

    def __init__(self, sites, *, resolver=None):
        super().__init__({}, resolver=resolver)
        self.sites = {origin: FakeSite(pages).pages for origin, pages in sites.items()}
        self.asked: list[tuple[str, str]] = []

    def handle_request(self, request):
        origin = f"{request.url.scheme}://{request.headers['host']}"
        self.asked.append((origin, str(request.url.path)))
        self.pages = self.sites.get(origin, {})
        return super().handle_request(request)


ALPHA, BETA = "alpha.example", "beta.example"
BOTH_HOSTS = {ALPHA: PUBLIC, BETA: SECOND_PUBLIC}


def test_a_redirect_onto_a_disallowed_path_of_the_same_site_is_not_followed() -> None:
    """**A `302` WAS A WAY ROUND `robots.txt` ENTIRELY, ON THE MERCHANT'S OWN
    SITE.** The rules were consulted for the FRONTIER url and `_fetch` then
    followed up to five hops, so a linked page that redirects into a disallowed
    directory was fetched and kept. Executed against the reader that ships, and
    the disallowed page is genuinely linked and genuinely exists - both halves,
    or this passes for the wrong reason."""
    site, client = a_site(
        {
            "/robots.txt": Reply(
                body=b"User-agent: *\nDisallow: /private", content_type="text/plain"
            ),
            "/": Reply(body=b'<html><body><p>home</p><a href="/door.html">d</a></body></html>'),
            "/door.html": Reply(status=302, location="/private/trade-portal.html"),
            "/private/trade-portal.html": Reply(body=b"<html><body><p>secrets</p></body></html>"),
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert "/door.html" in site.paths, "the redirecting page must really be reachable"
    assert "/private/trade-portal.html" not in site.paths, (
        "not fetched-and-discarded: never requested at all"
    )
    assert all("/private" not in page.url for page in result.pages)


def test_a_redirect_onto_another_origin_reads_that_origins_robots_first() -> None:
    """**AND THE CROSS-ORIGIN CASE WAS WORSE: the target host's `robots.txt` was
    never fetched AT ALL.** A merchant's site could walk us onto a third party's
    disallowed path with our own `User-Agent` in that third party's access log,
    which is precisely what `USER_AGENT`'s comment says a crawler must not do."""
    site = Origins(
        {
            f"https://{ALPHA}": {
                "/robots.txt": Reply(body=b"", content_type="text/plain"),
                "/": Reply(status=302, location=f"https://{BETA}/secret/page.html"),
            },
            f"https://{BETA}": {
                "/robots.txt": Reply(
                    body=b"User-agent: *\nDisallow: /secret", content_type="text/plain"
                ),
                "/secret/page.html": Reply(body=b"<html><body><p>not for you</p></body></html>"),
            },
        },
        resolver=FakeResolver(BOTH_HOSTS),
    )
    client = build_client(timeout_seconds=60.0, inner=site)

    result = run(client, f"https://{ALPHA}/", resolver=FakeResolver(BOTH_HOSTS))

    assert (f"https://{BETA}", "/robots.txt") in site.asked, "the other origin has its own rules to read"
    assert (f"https://{BETA}", "/secret/page.html") not in site.asked
    assert result.pages == ()


def test_a_redirect_onto_another_origin_that_allows_it_is_still_followed() -> None:
    """The other side of the boundary, and it is the ordinary case rather than an
    edge: `http://example.com/` redirecting to `https://www.example.com/` is what
    most merchants' sites do. Reading the second origin's rules must not mean
    refusing to follow it."""
    site = Origins(
        {
            f"https://{ALPHA}": {
                "/robots.txt": Reply(body=b"", content_type="text/plain"),
                "/": Reply(status=302, location=f"https://{BETA}/welcome.html"),
            },
            f"https://{BETA}": {
                "/robots.txt": Reply(
                    body=b"User-agent: *\nDisallow: /admin", content_type="text/plain"
                ),
                "/welcome.html": Reply(body=b"<html><body><p>the moved site</p></body></html>"),
            },
        },
        resolver=FakeResolver(BOTH_HOSTS),
    )
    client = build_client(timeout_seconds=60.0, inner=site)

    result = run(client, f"https://{ALPHA}/", resolver=FakeResolver(BOTH_HOSTS))

    assert [page.url for page in result.pages] == [f"https://{BETA}/welcome.html"]
    assert (f"https://{BETA}", "/robots.txt") in site.asked


#: The site every merchant actually has: `http://` answers `301` to `https://`
#: for everything, `robots.txt` included. Typing a domain without a scheme is
#: what nearly everyone does, and this is where it lands.
def a_site_that_redirects_http_to_https(disallow: bytes = b"") -> Origins:
    return Origins(
        {
            f"http://{HOST}": {
                "/robots.txt": Reply(
                    status=301, location=f"https://{HOST}/robots.txt", content_type="text/plain"
                ),
                "/": Reply(status=301, location=f"https://{HOST}/"),
                "/services": Reply(status=301, location=f"https://{HOST}/services"),
            },
            f"https://{HOST}": {
                "/robots.txt": Reply(
                    body=b"User-agent: *\nDisallow: /private" + disallow,
                    content_type="text/plain",
                ),
                "/": Reply(
                    body=b'<html><body><h1>Alpha Plumbing</h1>'
                    b"<p>Emergency call-outs across the city, licensed and insured, with a "
                    b"same-day guarantee on every burst pipe and blocked drain we are called "
                    b"to. Family-owned since 1998, and every engineer on the van is fully "
                    b"certified. We cover the whole metropolitan area seven days a week, and "
                    b"there is no call-out fee for an emergency visit booked before noon.</p>"
                    b'<a href="/">home</a><a href="/services">what we do</a>'
                    b'<a href="/private">staff</a></body></html>'
                ),
                "/services": Reply(
                    body=b"<html><body><h2>Our Services</h2><ul><li>Burst pipe repair</li>"
                    b"</ul></body></html>"
                ),
                "/private": Reply(body=b"<html><body><p>not for you</p></body></html>"),
            },
        },
        resolver=FakeResolver({HOST: PUBLIC}),
    )


def test_a_site_that_redirects_http_to_https_is_crawled_rather_than_giving_up() -> None:
    """**THE COMMONEST CONFIGURATION ON THE WEB, AND IT USED TO END THE CRAWL AT
    THE FIRST REQUEST.**

    `_robots_for` had no redirect loop, so `301` was neither `200` nor `4xx` and
    fell through to "unreachable", which RFC 9309 says means crawl NOTHING.
    Measured at the commit before this fix, against this exact site: **one
    request, zero pages, INSUFFICIENT.** Every merchant who types their domain
    without a scheme, at any site that redirects to https - which is nearly all
    of them - got that.

    Two assertions, because reading the file is not the same as obeying it: the
    whole site comes back, AND the disallowed page named in the redirected
    `robots.txt` is still not fetched. A crawl that ignored robots entirely would
    also pass the first one.
    """
    site = a_site_that_redirects_http_to_https()
    client = build_client(timeout_seconds=60.0, inner=site)

    result = run(client, f"http://{HOST}/", resolver=FakeResolver({HOST: PUBLIC}))

    assert [page.url for page in result.pages] == [
        f"https://{HOST}/",
        f"https://{HOST}/services",
    ]
    assert (f"https://{HOST}", "/private") not in site.asked, (
        "the rules came back through a redirect, and they still apply"
    )
    assert "Burst pipe repair" in result.services
    assert result.source == SOURCE_CRAWLED


def test_typing_http_reads_exactly_what_typing_https_reads() -> None:
    """**THE SAME SITE, THE SAME PROFILE, WHICHEVER THE MERCHANT TYPED.** This is
    the property the onboarding form actually needs, and it takes both halves of
    the fix: following the redirect on `robots.txt`, and scoping the crawl to
    where the ENTRY page landed. Without the second, the home page is read and
    every link on it is off-site - measured, three pages became one and the
    profile lost more than half its text."""
    over_http = run(
        build_client(timeout_seconds=60.0, inner=a_site_that_redirects_http_to_https()),
        f"http://{HOST}/",
        resolver=FakeResolver({HOST: PUBLIC}),
    )
    over_https = run(
        build_client(timeout_seconds=60.0, inner=a_site_that_redirects_http_to_https()),
        f"https://{HOST}/",
        resolver=FakeResolver({HOST: PUBLIC}),
    )
    assert [page.url for page in over_http.pages] == [page.url for page in over_https.pages]
    assert over_http.page_text == over_https.page_text
    assert over_http.services == over_https.services


def test_the_entry_pages_redirect_sets_the_scope_and_nothing_else_widens_it() -> None:
    """**WHAT `_same_site` GUARDS IS UNTOUCHED**, and that is worth a test rather
    than a sentence. The scope is taken from where the ENTRY page landed, once.
    A redirect on any OTHER page cannot move it: here the second page redirects
    off to another host entirely, and the page it lands on is read (every hop was
    checked) but the links ON it are not followed, because they are not on the
    site the entry named."""
    site = Origins(
        {
            f"https://{ALPHA}": {
                "/robots.txt": Reply(body=b"", content_type="text/plain"),
                "/": Reply(
                    body=b'<html><body><p>home page words</p>'
                    b'<a href="/away">away</a></body></html>'
                ),
                "/away": Reply(status=302, location=f"https://{BETA}/landing"),
            },
            f"https://{BETA}": {
                "/robots.txt": Reply(body=b"", content_type="text/plain"),
                "/landing": Reply(
                    body=b'<html><body><p>another site entirely</p>'
                    b'<a href="/deeper">deeper</a></body></html>'
                ),
                "/deeper": Reply(body=b"<html><body><p>should never be read</p></body></html>"),
            },
        },
        resolver=FakeResolver(BOTH_HOSTS),
    )
    client = build_client(timeout_seconds=60.0, inner=site)

    result = run(client, f"https://{ALPHA}/", resolver=FakeResolver(BOTH_HOSTS))

    assert [page.url for page in result.pages] == [
        f"https://{ALPHA}/",
        f"https://{BETA}/landing",
    ]
    assert (f"https://{BETA}", "/deeper") not in site.asked, (
        "a redirect on a page that is not the entry must not widen the crawl"
    )


def test_a_page_reached_twice_by_different_routes_is_read_once() -> None:
    """**A `Location:` IS NOT A URL ANY LINK NAMED, SO THE `seen` SET CANNOT SEE
    IT.** Two frontier entries that redirect onto one page, plus a link straight
    to it: without a record of where pages LANDED this reads the same page three
    times, doubles its text in the profile, and asks the merchant's server for it
    twice more than it needed to. Found by measuring an `http` -> `https` crawl,
    where the entry's redirect target is also the home page's own navigation
    link."""
    site, client = a_site(
        {
            "/robots.txt": Reply(body=b"", content_type="text/plain"),
            "/": Reply(
                body=b'<html><body><p>home page words</p><a href="/one">1</a>'
                b'<a href="/two">2</a><a href="/real">3</a></body></html>'
            ),
            "/one": Reply(status=302, location="/real"),
            "/two": Reply(status=302, location="/real"),
            "/real": Reply(body=b"<html><body><p>the page itself</p></body></html>"),
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))

    assert [page.url for page in result.pages] == [URL, f"{URL}real"]
    assert site.paths.count("/real") == 1, "asked for once, however many routes reach it"


def served_origin(url: str) -> str:
    """The key `Origins` serves by, derived through the production `authority()`
    so the fake and the transport cannot disagree about what an origin is."""
    parsed = httpx.URL(url)
    port = parsed.port if parsed.port is not None else DEFAULT_PORTS[parsed.scheme]
    target = SafeTarget(
        url=url, scheme=parsed.scheme, host=parsed.host, port=port, addresses=(PUBLIC,)
    )
    return f"{parsed.scheme}://{authority(target)}"


#: **ONE CASE PER PART OF THE ORIGIN KEY, EACH DIFFERING IN THAT PART ALONE.**
#: `_RobotsRules` keys on `(scheme, host, port)`, and dropping any one of the
#: three survived the suite: the only tests that reached two origins differed in
#: the host AND the scheme AND the port at once, which is the same shape as the
#: `_same_site` defect one layer out. `http` on 443 and `https` on 443 are both
#: reachable - `ALLOWED_PORTS` is `{80, 443}` - which is what makes a
#: scheme-only and a port-only pair constructible at all.
ORIGIN_KEY_CASES = (
    pytest.param(f"http://{HOST}:443/", f"https://{HOST}/", None, id="only-the-scheme-differs"),
    pytest.param(f"http://{HOST}/", f"http://{HOST}:443/", None, id="only-the-port-differs"),
    pytest.param(f"https://{ALPHA}/", f"https://{BETA}/", BOTH_HOSTS, id="only-the-host-differs"),
)


@pytest.mark.parametrize("entry,elsewhere,hosts", ORIGIN_KEY_CASES)
def test_two_origins_differing_in_one_thing_do_not_share_one_robots_file(
    entry: str, elsewhere: str, hosts: dict[str, str] | None
) -> None:
    """**THE RULES BELONG TO AN ORIGIN, AND AN ORIGIN IS THREE THINGS.** The
    entry origin's file forbids `/kept`; the origin its redirect lands on allows
    everything. If the two shared a key, the first file's rules would be applied
    to the second origin, the second origin would never be asked for its own, and
    a page its own site permits would be dropped - fail-open in the other
    direction whenever the entry origin is the permissive one.

    Both halves are asserted, because either alone passes for the wrong reason:
    the second origin WAS asked for its rules, and the page only its own rules
    allow was fetched.
    """
    resolver = FakeResolver(hosts if hosts is not None else {HOST: PUBLIC})
    site = Origins(
        {
            served_origin(entry): {
                "/robots.txt": Reply(
                    body=b"User-agent: *\nDisallow: /kept", content_type="text/plain"
                ),
                "/": Reply(status=301, location=elsewhere),
            },
            served_origin(elsewhere): {
                "/robots.txt": Reply(body=b"", content_type="text/plain"),
                "/": Reply(
                    body=b'<html><body><p>the site it moved to</p>'
                    b'<a href="/kept">more</a></body></html>'
                ),
                "/kept": Reply(body=b"<html><body><p>the page that is allowed</p></body></html>"),
            },
        },
        resolver=resolver,
    )
    client = build_client(timeout_seconds=60.0, inner=site)

    result = run(client, entry, resolver=resolver)

    assert (served_origin(elsewhere), "/robots.txt") in site.asked, (
        "the second origin has its own rules and must be asked for them"
    )
    assert [page.url for page in result.pages] == [elsewhere, f"{elsewhere}kept"]


def test_the_origin_key_table_names_each_part_once() -> None:
    assert len(ORIGIN_KEY_CASES) == 3


def test_a_robots_file_behind_an_endless_redirect_chain_stops_the_crawl() -> None:
    """**FOLLOWING REDIRECTS DOES NOT MEAN FOLLOWING THEM FOREVER, AND WHERE THE
    CHAIN RUNS OUT IT FAILS CLOSED.** RFC 9309 §2.3.1.4: a `robots.txt` we could
    not read means crawl NOTHING, and a chain longer than the cap is one we could
    not read. The cap is the same `MAX_REDIRECTS` a page gets, from the same
    loop."""
    pages: dict[str, Reply] = {
        f"/robots-{index}.txt": Reply(
            status=301, location=f"/robots-{index + 1}.txt", content_type="text/plain"
        )
        for index in range(MAX_REDIRECTS + 2)
    }
    pages["/robots.txt"] = Reply(
        status=301, location="/robots-0.txt", content_type="text/plain"
    )
    pages["/"] = Reply(body=b"<html><body><p>home page words</p></body></html>")
    site, client = a_site(pages)

    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))

    assert result.pages == ()
    assert "/" not in site.paths, "not fetched-and-discarded: never requested at all"
    assert len([path for path in site.paths if "robots" in path]) == MAX_REDIRECTS + 1


def test_one_robots_file_is_read_per_origin_rather_than_per_request(
    fixture_site, fixture_client, fixture_resolver
) -> None:
    """Checking the rules for every hop must not mean fetching the file for every
    hop: a three-page crawl of one site is one `robots.txt` request, the same as
    before the check moved."""
    run(fixture_client, resolver=fixture_resolver)
    assert fixture_site.paths.count("/robots.txt") == 1
    assert len(fixture_site.paths) > 3, "and the crawl really did make several requests"


def test_the_fixture_site_robots_file_is_the_one_being_obeyed() -> None:
    """The file a human can open, read by the reader that ships - and the second
    group is the one that applies, which a first-match reader gets wrong."""
    robots = pathlib.Path(__file__).resolve().parents[2] / "fixture-site" / "robots.txt"
    rules = parse_robots(robots.read_text())
    assert rules.allows("/services.html") is True
    assert rules.allows("/private.html") is False


# --------------------------------------------------------------------------
# Politeness: pace, budget, size
# --------------------------------------------------------------------------


class Clock:
    """A clock that only moves when something waits, or when a page is served."""

    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def test_requests_to_one_host_are_paced(fixture_site, fixture_client, fixture_resolver) -> None:
    """One request at a time per host is true by construction here - the crawl is
    sequential - so what needs a test is the RATE. Two requests a second means
    half a second between every pair, including the `robots.txt` request and
    every hop of a redirect, which is why the pause lives at the request rather
    than at the page loop."""
    clock = Clock()
    run(
        fixture_client,
        resolver=fixture_resolver,
        rps_per_host=2,
        clock=clock,
        sleep=clock.sleep,
    )
    assert len(clock.slept) == len(fixture_site.requests) - 1
    assert clock.slept == [0.5] * len(clock.slept)


def test_a_rate_of_zero_or_less_is_refused() -> None:
    with pytest.raises(ValueError):
        fetch._Pace(0, now=lambda: 0.0, pause=lambda _: None)
    with pytest.raises(ValueError):
        fetch._Pace(-1, now=lambda: 0.0, pause=lambda _: None)


def test_the_time_budget_stops_the_crawl_partway(fixture_resolver) -> None:
    """A merchant waiting on an onboarding form is the reason there is a budget
    at all. Two assertions: the pages kept, and the requests not made."""
    clock = Clock()

    class SlowSite(FakeSite):
        def handle_request(self, request):
            clock.t += 6.0
            return super().handle_request(request)

    from tests.crawler.conftest import fixture_site_pages

    site = SlowSite(fixture_site_pages(), resolver=FakeResolver({FIXTURE_HOST: LOOPBACK}))
    client = build_client(timeout_seconds=10.0, inner=site)
    result = run(
        client,
        resolver=fixture_resolver,
        timeout_seconds=10.0,
        clock=clock,
        sleep=clock.sleep,
    )
    assert len(result.pages) == 1
    assert site.paths == ["/robots.txt", "/"]


def test_the_response_size_cap_stops_reading_rather_than_truncating_afterwards() -> None:
    """**THE DIFFERENCE IS THE WHOLE POINT.** Reading everything and slicing
    bounds the RESULT; stopping bounds the COST, which is what a body that never
    ends actually costs us. The stream counts how much of it was taken."""
    chunk = b"a" * 100_000
    chunks = tuple([b"<html><body><p>"] + [chunk] * 40 + [b"</p></body></html>"])
    site, client = a_site({"/": Reply(chunks=chunks)})
    run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    stream = site.streams[0]
    assert stream.taken < len(chunks), "the whole body was read, so nothing was capped"
    assert stream.taken == MAX_RESPONSE_BYTES // len(chunk) + 1


# --------------------------------------------------------------------------
# The size cap bounds the COST, and a compressed body is where those come apart
# --------------------------------------------------------------------------
#
# **THE FIRST VERSION OF THIS SECTION MEASURED THE RESULT AND CALLED IT THE
# COST.** `_read_capped` read httpx's DECODED stream and extended the buffer by
# a whole chunk before consulting the cap, and the crawler asked for gzip - so
# one 64 KB chunk on the wire was one arbitrarily large chunk in memory.
# Executed end to end through `crawl`: 388 KB on the wire, a page_text of exactly
# 1,999,985 characters, and 850,255,702 bytes of peak Python heap - 425x the cap,
# from a URL an untrusted party types into an onboarding form.
#
# The test that was supposed to hold this counted CHUNKS from an uncompressed
# stream, so it measured the transfer bound and could not see the memory one at
# all. Both are measured now, each by the thing it bounds: peak heap for memory,
# chunks taken for transfer - and they are separate tests because with
# `Content-Engineering: gzip` they are three orders of magnitude apart.


def a_gzip_stream_that_decodes_to_nothing(length: int) -> bytes:
    """A gzip body that consumes `length` bytes on the wire and yields NO output.

    Deflate's sync-flush marker is five bytes and carries no data, so a stream of
    them is an endless body that a decompressed-size bound alone never notices:
    the buffer stays empty and the reader keeps asking for more. That is the case
    the TRANSFER bound exists for, and the only case that tells the two bounds
    apart.
    """
    compressor = zlib.compressobj(9, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
    opening = compressor.compress(b"") + compressor.flush(zlib.Z_SYNC_FLUSH)
    empty = opening[-5:]
    stream = (opening + empty * length)[:length]
    assert not zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(stream), (
        "this generator has to yield nothing, or it is testing the other bound"
    )
    return stream


def test_a_compressed_body_costs_one_cap_of_MEMORY_rather_than_what_it_expands_to(
) -> None:
    """**THE CAP BOUNDS THE COST, AND PEAK HEAP IS WHERE THAT IS TRUE OR NOT.**

    A body that comes off the wire smaller than the cap and expands past it is
    the whole attack, so the assertion is on what the process ALLOCATED, not on
    what came back: the returned text was already correctly capped while the
    heap was 425x the cap. `tracemalloc` counts only what is allocated inside the
    window, and the payload is built and compressed before it opens.

    **AND THE BOMB ARRIVES IN CHUNKS, WHICH IS THE HALF THIS TEST WAS MISSING.**
    The first version handed the whole compressed body over as ONE chunk, and the
    memory budget is an ACCUMULATION - `MAX_RESPONSE_BYTES - len(body)`, and a
    `break` that stops the accumulating. A budget that accumulates cannot be
    pinned by a fixture that never accumulates: with one chunk both halves could
    be deleted and this test still passed. Measured on the chunked version:
    dropping the subtraction lets the buffer grow by a whole cap PER CHUNK -
    120 MB of body, 240x the cap - and dropping the memory half of the `break`
    walks `room` to zero, where `zlib` reads `max_length=0` as UNLIMITED, and
    then past it, where it raises.

    The chunk size is asserted rather than chosen: no single chunk may decode to
    a whole budget, or the loop refills in one step and accumulation is invisible
    again. That is exactly what hid it - at 2,000 bytes a chunk the shipped code
    and the mutant are indistinguishable, and at 500 they are 60x apart.
    """
    expanded = 60 * MAX_RESPONSE_BYTES
    payload = b"<html><body><p>" + b"a" * expanded + b"</p></body></html>"
    compressed = gzip.compress(payload, 9)
    del payload
    assert len(compressed) < MAX_RESPONSE_BYTES // 10, (
        "the point is a body that is TINY on the wire and enormous once decoded"
    )
    wire = 500
    chunks = tuple(compressed[index:index + wire] for index in range(0, len(compressed), wire))
    first = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(chunks[0], MAX_RESPONSE_BYTES)
    assert 0 < len(first) < MAX_RESPONSE_BYTES, (
        "one chunk must decode to SOME of the budget and not all of it, or a budget that "
        "fails to accumulate across chunks is indistinguishable from one that does"
    )
    _site, client = a_site({"/": Reply(chunks=chunks, content_encoding="gzip")})

    tracemalloc.start()
    try:
        result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak < 6 * MAX_RESPONSE_BYTES, (
        f"reading this page allocated {peak:,} bytes for a {MAX_RESPONSE_BYTES:,} byte cap - "
        f"the cap is bounding the result and not the cost"
    )
    assert len(result.page_text) <= MAX_RESPONSE_BYTES


def test_a_compressed_body_that_decodes_to_nothing_still_stops_being_read() -> None:
    """**THE OTHER BOUND, AND IT IS A DIFFERENT STATEMENT.** A memory bound alone
    never fires on a stream that decodes to nothing, so the reader would go on
    taking chunks until the time budget ran out. One cap's worth of transfer and
    then it stops, whatever the body decodes to."""
    chunk = 300_000
    wire = a_gzip_stream_that_decodes_to_nothing(MAX_RESPONSE_BYTES * 3)
    chunks = tuple(wire[index:index + chunk] for index in range(0, len(wire), chunk))
    assert len(chunks) == 20
    site, client = a_site({"/": Reply(chunks=chunks, content_encoding="gzip")})

    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))

    assert site.streams[0].taken == -(-MAX_RESPONSE_BYTES // chunk), (
        "one cap's worth of bytes off the wire and then the stream is abandoned - and the "
        "chunk size deliberately does NOT divide the cap, so the last chunk has to be "
        "TRUNCATED to the remaining allowance rather than taken whole and noticed afterwards"
    )
    assert result.pages == (), "nothing decoded, so there was no page"


def test_a_gzipped_page_IS_read(fixture_resolver) -> None:
    """**THE POSITIVE CONTROL, AND WITHOUT IT THE TWO BOUNDS ABOVE PASS ON A
    DECODER THAT NEVER WORKS.** Compression is accepted rather than refused, so
    a merchant on hosting that gzips everything is still readable - which is the
    trade this module chose over `Accept-Encoding: identity`, and the reason the
    decompression has to be bounded rather than avoided."""
    page = (
        b"<html><body><h1>Alpha Plumbing</h1>"
        b"<p>Emergency call-outs across the city, licensed and insured.</p></body></html>"
    )
    site, client = a_site({"/": Reply(body=gzip.compress(page), content_encoding="gzip")})
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert [page_.url for page_ in result.pages] == [URL]
    assert "Emergency call-outs" in result.page_text
    assert site.last_request.headers["accept-encoding"] == ACCEPT_ENCODING


def test_a_body_in_an_encoding_the_crawler_cannot_bound_is_not_read() -> None:
    """A server answering with an encoding we did not ask for and cannot
    decompress a bounded amount of contributes nothing, rather than being handed
    to a decoder that has no size argument."""
    _site, client = a_site(
        {"/": Reply(body=b"<html><body><p>brotli, unasked for</p></body></html>",
                    content_encoding="br")}
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert result.pages == ()


#: Bodies that arrive labelled `Content-Encoding: gzip` and are not gzip. The
#: third is not hostile at all: a proxy that decompresses a response and forgets
#: to strip the header produces it, which is why this is an ordinary failure
#: rather than an attack.
NOT_ACTUALLY_GZIP = (
    pytest.param(b"<html><body><p>plain markup</p></body></html>", id="never-compressed"),
    pytest.param(zlib.compress(b"<html><body><p>deflate</p></body></html>"), id="deflate-not-gzip"),
    pytest.param(b"\x1f\x8b\x08\x00" + b"\x00" * 40, id="a-gzip-header-over-nonsense"),
)


@pytest.mark.parametrize("body", NOT_ACTUALLY_GZIP)
def test_a_body_that_is_not_the_gzip_it_claims_to_be_does_not_end_the_crawl(
    body: bytes,
) -> None:
    """**THE ERROR CONTRACT THIS MODULE GAVE BACK WHEN IT TOOK OVER THE
    DECODING, EXECUTED.**

    `_read_capped` used to read `response.iter_bytes()`, and httpx wraps a
    decoder failure as `httpx.DecodingError` - an `httpx.HTTPError`, already in
    `FETCH_FAILURES`. Driving `zlib` directly to get a size bound handed that
    wrapper back, and `zlib.error` derives from `Exception` alone: measured, this
    body raised `zlib.error` straight out of `crawl`, past every caller catching
    `BlockedAddress` or `FETCH_FAILURES`, for a merchant whose proxy is
    misconfigured.

    Two assertions, because "it does not raise" is not the property: the crawl
    finishes AND the rest of the site is still read.
    """
    _site, client = a_site(
        {
            "/": Reply(
                body=b'<html><body><p>home page words here</p>'
                b'<a href="/broken">b</a><a href="/good">g</a></body></html>'
            ),
            "/broken": Reply(body=body, content_encoding="gzip"),
            "/good": Reply(body=b"<html><body><p>the good page</p></body></html>"),
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert [page.url for page in result.pages] == [URL, f"{URL}good"]


def test_the_not_gzip_table_is_the_size_it_looks() -> None:
    assert len(NOT_ACTUALLY_GZIP) == 3


def test_a_corrupt_robots_file_is_unreadable_rather_than_fatal() -> None:
    """The same escape through the other reader. A `robots.txt` we cannot decode
    is one we could not read, which RFC 9309 §2.3.1.4 says means crawl NOTHING -
    fail-closed, and not a `zlib.error` out of the wizard."""
    _site, client = a_site(
        {
            "/robots.txt": Reply(
                body=b"User-agent: *", content_type="text/plain", content_encoding="gzip"
            ),
            "/": Reply(body=b"<html><body><p>home page words</p></body></html>"),
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert result.pages == ()


def test_the_encodings_asked_for_are_exactly_the_ones_that_can_be_bounded() -> None:
    """**THE TWO HALVES OF THE SAME DECISION, HELD TOGETHER.** An encoding asked
    for with no bounded decoder behind it is the hole this section exists for;
    one with a decoder and no request for it is dead code. `""` is the absent
    header rather than an encoding, which is why it is taken out."""
    asked = {token.strip() for token in ACCEPT_ENCODING.split(",")}
    assert asked == set(fetch._INFLATERS) - {""}
    assert asked == {"gzip", "identity"}
    assert isinstance(_binding("ACCEPT_ENCODING"), ast.Constant)


def test_the_size_cap_is_named_once_per_quantity_it_bounds() -> None:
    """**THE LESSON FROM THE REDIRECT CAP, APPLIED TO THE ONE OTHER VALUE IN THIS
    MODULE THAT WAS WRITTEN DOWN TWICE.**

    `MAX_RESPONSE_BYTES` used to appear twice inside `_read_capped` - the read
    bound and a slice of the result - and those two ARE the same statement, so
    the slice was an equivalent mutant and nothing asserted the returned length
    at all: `return bytes(body)` and `bytes(body[:cap * 2])` both survived the
    whole suite. The slice is gone; the result is bounded by construction.

    It still appears twice, and this asserts that it is twice and not three
    times, because the two are different QUANTITIES - what comes off the wire and
    what ends up in memory - and each is caught by a test the other cannot fail.
    A third mention would be a bound restating one of those, which is exactly the
    shape that hid the redirect cap's defect.
    """
    body = None
    for node in ast.walk(FETCH_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == "_read_capped":
            body = node
    assert body is not None
    names = [n.id for n in ast.walk(body) if isinstance(n, ast.Name)]
    assert names.count("MAX_RESPONSE_BYTES") == 2, (
        "one for the transfer budget and one for the memory budget - the `break` says which "
        "budget ran out in terms of those two rather than naming the cap again"
    )
    numbers = [
        n.value for n in ast.walk(body) if isinstance(n, ast.Constant) and isinstance(n.value, int)
    ]
    assert MAX_RESPONSE_BYTES not in numbers, "the cap is named, not spelled out a second time"


def test_the_accept_encoding_header_is_this_modules_choice_not_httpxs(
    fixture_site, fixture_client, fixture_resolver
) -> None:
    """httpx fills this header in from whichever decoders happen to be installed
    - `gzip, deflate` today, `br` and `zstd` the moment somebody adds brotli for
    something unrelated - and then decodes the body with no size bound at all. So
    the header is said here, and it says only what `_INFLATERS` can bound."""
    run(fixture_client, resolver=fixture_resolver)
    assert fixture_site.requests
    for request in fixture_site.requests:
        assert request.headers["accept-encoding"] == ACCEPT_ENCODING


UNREADABLE_RESPONSES = (
    pytest.param(Reply(status=404, body=b"nope"), id="not-found"),
    pytest.param(Reply(status=500, body=b"oops"), id="server-error"),
    pytest.param(Reply(status=204, body=b""), id="no-content"),
    pytest.param(Reply(body=b"%PDF-1.7", content_type="application/pdf"), id="a-pdf"),
    pytest.param(Reply(body=b"{}", content_type="application/json"), id="json"),
    pytest.param(Reply(body=b"", content_type="text/html"), id="an-empty-body"),
)


@pytest.mark.parametrize("reply", UNREADABLE_RESPONSES)
def test_a_response_that_is_not_a_page_contributes_nothing(reply: Reply) -> None:
    _site, client = a_site({"/": reply})
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert result.pages == ()
    assert result.source == SOURCE_INSUFFICIENT


def test_the_unreadable_response_table_is_the_size_it_looks() -> None:
    assert len(UNREADABLE_RESPONSES) == 6


def test_a_response_with_no_content_type_is_read_as_html() -> None:
    """Hand-rolled servers on small-business hosting omit it, and refusing them
    would fail exactly the sites this module exists for."""
    _site, client = a_site(
        {"/": Reply(body=b"<html><body><p>plain and unlabelled</p></body></html>",
                    content_type=None)}
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert [page.url for page in result.pages] == [URL]


def test_the_media_types_are_the_ones_worth_parsing() -> None:
    assert HTML_CONTENT_TYPES == frozenset(
        {"text/html", "application/xhtml+xml", "text/plain"}
    )
    assert "text/plain" in HTML_CONTENT_TYPES, (
        "robots.txt is served as text/plain, so dropping it here makes every site "
        "look as though it has no robots file at all"
    )


def test_a_page_that_lies_about_its_encoding_is_read_rather_than_raising() -> None:
    _site, client = a_site(
        {
            "/": Reply(
                body="<html><body><p>café plumbing</p></body></html>".encode("latin-1"),
                content_type="text/html; charset=nonsense-9",
            )
        }
    )
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    assert len(result.pages) == 1


# --------------------------------------------------------------------------
# The judgements are literals
# --------------------------------------------------------------------------


LITERAL_JUDGEMENTS = (
    ("MAX_RESPONSE_BYTES", MAX_RESPONSE_BYTES, 2_000_000),
    ("MIN_TEXT_FOR_A_USABLE_PROFILE", MIN_TEXT_FOR_A_USABLE_PROFILE, 400),
    ("MAX_SERVICES_IN_A_RESULT", fetch.MAX_SERVICES_IN_A_RESULT, 40),
    ("MAX_SELLING_POINTS_IN_A_RESULT", fetch.MAX_SELLING_POINTS_IN_A_RESULT, 20),
)


@pytest.mark.parametrize("name,value,expected", LITERAL_JUDGEMENTS)
def test_every_bound_is_a_literal_with_the_value_it_has(name, value, expected) -> None:
    assert value == expected
    assert isinstance(_binding(name), ast.Constant)


def test_the_literal_judgement_table_is_the_size_it_looks() -> None:
    assert len(LITERAL_JUDGEMENTS) == 4


def test_the_source_values_are_literals() -> None:
    """The wizard branches on these strings, so they are an interface."""
    assert SOURCE_CRAWLED == "CRAWLED"
    assert SOURCE_INSUFFICIENT == "INSUFFICIENT"
    assert isinstance(_binding("SOURCE_CRAWLED"), ast.Constant)
    assert isinstance(_binding("SOURCE_INSUFFICIENT"), ast.Constant)


def test_the_extension_keys_are_literals() -> None:
    assert SAFE_TARGET_EXTENSION == "ppcway_safe_target"
    assert SNI_EXTENSION == "sni_hostname"
    assert isinstance(_binding("SAFE_TARGET_EXTENSION"), ast.Constant)
    assert isinstance(_binding("SNI_EXTENSION"), ast.Constant)


def test_the_accept_header_asks_for_markup() -> None:
    assert "text/html" in ACCEPT


def test_a_crawl_result_is_frozen() -> None:
    _site, client = a_site({"/": "<html><body><p>words</p></body></html>"})
    result = run(client, URL, resolver=FakeResolver({HOST: PUBLIC}))
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.source = SOURCE_CRAWLED  # type: ignore[misc]


def test_the_default_resolver_is_the_ssrf_one_and_reaches_the_ban() -> None:
    """`crawl` passes `resolver=None` straight through, so a forgotten keyword
    makes a real DNS query. This package's ban is what stops that, and this is
    the executed proof that the default really does reach it."""
    _site, client = a_site({"/": "<html><body>ok</body></html>"})
    with pytest.raises(RuntimeError, match="tried to open a socket"):
        crawl(URL, max_pages=1, timeout_seconds=5, rps_per_host=1000, client=client)


def test_address_info_is_the_shape_the_module_indexes() -> None:
    """The conftest fake builds four-wide sockaddrs for IPv6 and two-wide for
    IPv4 because that is what `getaddrinfo` really returns; a uniform shape would
    let a real indexing bug through."""
    assert len(address_info("1.1.1.1", 443)[4]) == 2
    assert len(address_info("2606:2800::1", 443)[4]) == 4
