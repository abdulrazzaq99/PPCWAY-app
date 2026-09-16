"""Fetching a merchant's website, politely, and only ever at a judged address.

Blueprint §6.1 and §12.6. This is the caller `ssrf.py` was written for, and its
first job is not crawling - it is holding up the third obligation in that
module's docstring, the one `ssrf.py` cannot hold up on its own:

  **THE ADDRESS THAT WAS CHECKED MUST BE THE ADDRESS THAT IS CONNECTED TO.**

`assert_safe_url` resolves the host ONCE and hands back the addresses it
approved. If this module then passed the HOST NAME to an HTTP client, the client
would resolve that name a second time, and a DNS server the attacker controls
would answer the second query with `127.0.0.1`. Every property `ssrf.py` proves
about the first answer would be about an address nothing ever connected to. That
is DNS rebinding; it is the standard bypass for a check of this shape; and it is
the reason `SafeTarget.addresses` exists at all.

**SO THE CONNECTION IS AIMED, NOT NAMED.** `PinnedAddressTransport` below is the
only thing here that reaches a socket, and it:

  1. reads the `SafeTarget` that was attached to the request, and REFUSES a
     request that carries none - a request nobody checked is a request this
     module will not send;
  2. checks the target actually describes the request (same scheme, host and
     port), so a target cannot be reused for a different URL;
  3. for each address in `SafeTarget.addresses`, calls `assert_safe_address` on
     THAT address and then hands THAT address to the inner transport, in that
     order, with nothing in between. The value checked and the value connected to
     are the same local variable;
  4. sends `SafeTarget.host` as the `Host:` header and as the TLS
     `server_hostname` (httpx's `sni_hostname` extension), so the certificate is
     still verified against the name the merchant typed rather than against an
     IP address that has no certificate.

**AND A NAME CAN NEVER REACH `connect()`, BY CONSTRUCTION.** Step 3 is not a
formality: `assert_safe_address` parses its argument with `ipaddress.ip_address`
and refuses anything that is not an IP literal. So the failure mode this whole
design exists to prevent - handing the transport `target.host` instead of
`target.addresses[i]` - is not a subtle mis-wiring that ships green, it is a
`BlockedAddress` on the first request. `test_handing_the_transport_a_name_
instead_of_an_address_is_refused` is that case, executed.

**`crawl` REFUSES A CLIENT THAT IS NOT PINNED**, which is the other half. An
ordinary `httpx.Client` resolves the host itself, so accepting one would put the
rebinding window back exactly where it was - and it would do so silently, since
every functional test would still pass. `_pinned_transport` rejects a client
whose transport is not a `PinnedAddressTransport`, whose `mounts` could route a
URL somewhere else, or which follows redirects itself (see below).

**REDIRECTS ARE FOLLOWED HERE, ONE HOP AT A TIME, NOT BY httpx.** A `302
Location: http://169.254.169.254/` is the ordinary way past a check that only ran
at the start, so every hop goes through `assert_safe_redirect`, which re-runs the
WHOLE check on the joined URL. `MAX_REDIRECTS` bounds the chain; it is not a
security control - hop five is judged exactly as hop one is - it is what stops a
redirect loop becoming an unbounded crawl.

**THE OTHER OBLIGATION IS TO THE MERCHANT'S SERVER, NOT TO US.** One request at a
time per host (this crawl is sequential, so that is true by construction), at
most `rps_per_host` of them a second, a total time budget, a page cap, a response
size cap that bounds the COST rather than the result (`_read_capped`), and a user
agent that says who we are and where to complain. A crawler that a merchant
cannot identify in their access log is a crawler they are right to block.

`robots.txt` is honoured PER ORIGIN AND PER REQUEST, in `_fetch`, not once per
frontier entry - a redirect is a URL somebody else chose, and checking only what
the frontier held let a `302` reach a disallowed path on the merchant's own site
and reach a third party's site with no rules read at all. See `_RobotsRules`.
It is also FETCHED through the same redirect loop as any page, because
`http://example.com/robots.txt` answering `301 https://example.com/robots.txt`
is the commonest configuration there is, and reading that as "unreachable" meant
crawling nothing at all for the merchants who type their domain without a
scheme.

**AND WHAT A REFUSAL SAYS TO WHOM.** `BlockedAddress` carries the resolved
address on `.address` and never in its message, because the party who typed the
hostname does not know what it resolves to inside our network and must not learn
it from us - see `BlockedAddress`'s own docstring. This module LOGS `.address`
and renders `str(exception)`, and nothing here ever puts an address into a value
a merchant sees.
"""
from __future__ import annotations

import logging
import re
import time
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlsplit, urlunsplit

import httpx

from ppcway.crawler.parse import PageExtract, extract
from ppcway.crawler.ssrf import (
    DEFAULT_PORTS,
    MAX_REDIRECTS,
    BlockedAddress,
    Resolver,
    SafeTarget,
    assert_safe_address,
    assert_safe_redirect,
    assert_safe_url,
)

_LOG = logging.getLogger(__name__)

#: **WHO WE ARE, AND WHERE TO COMPLAIN.** A merchant looking at their access log
#: after we have read their site should be able to tell in one line what read it
#: and how to stop it. `PPCWay` is the product token `robots.txt` groups are
#: matched against, and the URL is what makes the token mean something.
USER_AGENT: Final = (
    "PPCWay/0.1 (+https://ppcway.example/crawler; reads a merchant's own site during onboarding)"
)

#: The `User-agent:` token `robots.txt` groups are keyed on. Lower-cased here
#: because robots matching is case-insensitive, and derived from nothing - it is
#: the product's name, and `test_the_robots_token_is_the_one_in_the_user_agent`
#: holds the two together so the agent string and the group we obey cannot drift
#: apart.
ROBOTS_AGENT_TOKEN: Final = "ppcway"

#: Sent so a server that negotiates can give us markup rather than JSON.
ACCEPT: Final = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1"

#: **WHAT WE ASK FOR IS WHAT WE CAN BOUND, AND IT IS SAID HERE RATHER THAN LEFT
#: TO httpx.** httpx sets `Accept-Encoding` from whichever decoders happen to be
#: installed - `gzip, deflate` today, and `br`/`zstd` the moment somebody adds
#: brotli or zstandard for something else - and then decodes the body itself,
#: producing one arbitrarily large object per chunk off the wire. That is how a
#: 388 KB response became 850 MB of heap in this module's first version (see
#: `_read_capped`). This module therefore names the encodings ITSELF, and names
#: only the ones `_INFLATERS` below can decompress a bounded amount of: a body in
#: any other encoding is not read at all. Adding a name here without adding a
#: bounded decoder for it re-opens that hole, which is why the two are pinned
#: against each other by
#: `test_the_encodings_asked_for_are_exactly_the_ones_that_can_be_bounded`.
ACCEPT_ENCODING: Final = "gzip, identity"

#: The most of one response this module will read into memory. A merchant's home
#: page is tens of kilobytes; anything past this is either a mistake or a
#: deliberate attempt to make the crawler the expensive half of the transaction.
#: It bounds TWO different quantities, and `_read_capped` applies it to each of
#: them separately: how much comes off the wire, and how much ends up in memory
#: after decompression. Those are the same number and not the same statement -
#: with `Content-Encoding: gzip` they are three orders of magnitude apart.
MAX_RESPONSE_BYTES: Final = 2_000_000

#: How much of a whole site's lists survives into one profile. Larger than one
#: page's bounds in `parse.py` because a site's services really are spread over
#: several pages, and still bounded because everything here ends up in a prompt.
MAX_SERVICES_IN_A_RESULT: Final = 40
MAX_SELLING_POINTS_IN_A_RESULT: Final = 20


#: How much text the whole crawl has to yield before the wizard may use it.
#: Blueprint §6.2: a meaningful share of small-business sites are a single
#: JavaScript-rendered shell, and a generator handed four words of scaffolding
#: writes plausible-sounding ad copy about a business it knows nothing about.
#: Below this the wizard asks the merchant instead, which is slower and true.
MIN_TEXT_FOR_A_USABLE_PROFILE: Final = 400

#: What `CrawlResult.source` says. Two literals rather than a `StrEnum`: an enum
#: here would be declared in `ppcway.crawler`, and the module that lists every
#: `StrEnum`-declaring file (`tests/narrate/test_templates.py`) imports each one
#: it finds - which would drag `ppcway.crawler.ssrf` into `tests/narrate`, a
#: directory that does not install the network ban. A two-member enum is not
#: worth putting a guarded module inside an unguarded package.
SOURCE_CRAWLED: Final = "CRAWLED"
SOURCE_INSUFFICIENT: Final = "INSUFFICIENT"

#: Status codes that carry a `Location:` this module will follow. 303 is here
#: because a GET redirected with 303 is still a GET; 307 and 308 preserve the
#: method, which for us is always GET anyway.
REDIRECT_STATUSES: Final = frozenset({301, 302, 303, 307, 308})

#: Media types worth parsing as markup. A response with NO `Content-Type` at all
#: is treated as HTML, because hand-rolled servers on small-business hosting omit
#: it and refusing them would fail the sites this module exists for; a response
#: that names a type we do not parse is skipped rather than guessed at.
HTML_CONTENT_TYPES: Final = frozenset({"text/html", "application/xhtml+xml", "text/plain"})

#: **NO CONNECTION IS REUSED ACROSS REQUESTS, AND THAT IS A CERTIFICATE
#: DECISION RATHER THAN A PERFORMANCE ONE.** This transport rewrites the URL's
#: host to the ADDRESS, and httpcore keys its connection pool on the URL's
#: origin - so after the rewrite the key is `(scheme, IP, port)` and TWO
#: DIFFERENT HOST NAMES PINNED TO ONE ADDRESS SHARE A CONNECTION. The TLS
#: handshake, and therefore the certificate check, belongs to whichever name
#: opened it. Measured against a real keep-alive TLS server on loopback, with a
#: certificate naming only the first host:
#:
#:     one pool          : 1 connection, 1 handshake, SNI=['alphaplumbing.example'],
#:                         and `https://victim.example/` answered 200 - unverified
#:     no reuse          : 2 connections, 2 handshakes, and the second name is
#:                         refused with CERTIFICATE_VERIFY_FAILED: Hostname mismatch
#:
#: It is reachable inside one `crawl` by an ordinary cross-host redirect between
#: two names on one address. The cost of closing it is a handshake per request,
#: which for a sequential crawl of at most a few dozen paced pages is not a cost
#: worth a claim that is only true of the first name.
NO_CONNECTION_REUSE: Final = httpx.Limits(max_keepalive_connections=0)

#: The key `PinnedAddressTransport` reads the checked target out of. httpx passes
#: `extensions` through to the transport untouched and httpcore ignores keys it
#: does not recognise, which is what makes this a channel rather than a global.
SAFE_TARGET_EXTENSION: Final = "ppcway_safe_target"

#: httpx's own name for the TLS server name. Named here rather than written
#: inline because it is the whole of obligation 2's certificate half: without it
#: httpcore uses the connection's host, which after the rewrite is an IP address.
#:
#: **AND WHAT THAT COSTS IS EVERY HTTPS FETCH, NOT A SILENT DOWNGRADE** - which
#: is the opposite of what this comment used to say. Executed against a real TLS
#: server on loopback: with the extension the handshake carries the name and
#: verification succeeds; with it misspelled, Python's `ssl` verifies the IP
#: literal against the certificate's `iPAddress` SANs, finds none, and raises
#: `CERTIFICATE_VERIFY_FAILED: IP address mismatch`. So a typo here fails CLOSED
#: and loudly, and `test_the_sni_extension_is_what_makes_the_certificate_be_
#: verified_against_the_name` is that measurement rather than an argument.
SNI_EXTENSION: Final = "sni_hostname"

#: **A FETCH THAT FAILED, ACROSS FOUR HIERARCHIES THAT DO NOT AGREE.** One page
#: refusing to load must not end a crawl, so these are caught - and the bases are
#: listed because no two of them contain each other:
#:
#:   * `httpx.HTTPError` is NOT an `OSError`, and covers `ConnectError`,
#:     `ReadTimeout`, `RemoteProtocolError`, `UnsupportedProtocol`, `PoolTimeout`
#:     and the rest of the transport family;
#:   * `ssl.SSLError` IS an `OSError` but arrives from a different library, and a
#:     certificate that does not verify is the ordinary case here rather than an
#:     exotic one;
#:   * `OSError` itself covers a socket-level failure that reaches us unwrapped;
#:   * `zlib.error` derives from `Exception` AND NOTHING ELSE, and it is here
#:     because of a regression this module caused itself - see below.
#:
#: **THE FOURTH BASE IS THE PRICE OF DOING OUR OWN DECOMPRESSION, AND IT ARRIVED
#: THE DAY WE STOPPED USING httpx's.** `_read_capped` used to read
#: `response.iter_bytes()`, and httpx wraps a decoder failure as
#: `httpx.DecodingError` - an `httpx.HTTPError`, so a corrupt body was already
#: "that page did not load". Bounding the decompression meant driving `zlib`
#: directly, which handed that wrapper back: measured, a body labelled
#: `Content-Encoding: gzip` that is not gzip raised `zlib.error` straight out of
#: `crawl`. An ordinary misconfigured proxy - one that decompresses and forgets
#: to strip the header - produces exactly that. **When you replace a library's
#: implementation you also replace its error contract**, and this is the line
#: where that gets paid.
#:
#: Task 26's lesson, which this table exists to answer: a fake that raises only
#: the errors you thought of hides the ones you did not. `tests/crawler/test_
#: fetch.py` drives a table of real exception INSTANCES from all four families
#: through the injected client and pins that the table spans OUTSIDE EVERY BASE,
#: so no one of them can be deleted quietly.
#:
#: `BlockedAddress` is deliberately NOT here. A refusal is a decision, not a
#: failure, and swallowing it into "that page did not load" is how a security
#: control becomes a log line nobody reads.
FETCH_FAILURES: Final = (httpx.HTTPError, OSError, zlib.error)


@dataclass(frozen=True)
class Page:
    """One page that was fetched and read."""

    url: str
    extract: PageExtract


@dataclass(frozen=True)
class CrawlResult:
    """What a whole site said, and whether it was enough to work with.

    `source` is the field the wizard branches on: `SOURCE_INSUFFICIENT` means
    "ask the merchant", and it is reached whenever the crawl produced less than
    `MIN_TEXT_FOR_A_USABLE_PROFILE` characters of text, including when it
    produced no pages at all.
    """

    pages: tuple[Page, ...]
    business_name: str
    services: tuple[str, ...]
    unique_selling_points: tuple[str, ...]
    phone: str
    address: str
    meta_title: str
    meta_description: str
    page_text: str
    source: str


def authority(target: SafeTarget) -> str:
    """The `Host:` header for `target` - the NAME, never the address.

    Two details that are easy to get wrong and are both reachable here:

      * an IPv6 literal host is bracketed, because `SafeTarget.host` comes from
        `urlsplit().hostname`, which strips the brackets;
      * the port is appended when it is not the scheme's default, and that case
        IS reachable - `ALLOWED_PORTS` is `{80, 443}` and `ALLOWED_SCHEMES` is
        `{http, https}`, so `http://example/` on port 443 passes the SSRF check
        and needs `Host: example:443`. `test_the_host_header_names_the_port_when
        _it_is_not_the_scheme_default` executes exactly that combination.
    """
    host = f"[{target.host}]" if ":" in target.host else target.host
    if target.port == DEFAULT_PORTS.get(target.scheme):
        return host
    return f"{host}:{target.port}"


class PinnedAddressTransport(httpx.BaseTransport):
    """The only thing here that connects, and it connects to a judged address.

    Wraps an inner transport - `httpx.HTTPTransport` in production, a fake in
    the tests - and does four things before delegating. See this module's
    docstring for why each one is load-bearing; the short version is that this
    class is where obligations 2 and 3 of `ssrf.py`'s docstring are discharged.

    **THE CHECK AND THE CONNECTION ARE THE SAME LOCAL VARIABLE.** `address` is
    checked and then handed over, in adjacent statements, inside one loop
    iteration. There is no resolution, no lookup and no reassignment between
    them, which is the only arrangement in which a check and a connection cannot
    disagree about what they are talking about.

    Every address is tried in turn, so a host with one unreachable address and
    one working one still gets fetched - and each address goes through the check
    separately, because "the first one was fine" says nothing about the second.
    """

    def __init__(self, *, inner: httpx.BaseTransport) -> None:
        self._inner = inner

    @property
    def inner(self) -> httpx.BaseTransport:
        """The transport that actually opens the socket."""
        return self._inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        target = request.extensions.get(SAFE_TARGET_EXTENSION)
        if not isinstance(target, SafeTarget):
            raise BlockedAddress(
                "the crawler will not send a request that has not been through its safety "
                "check: no checked target was attached to it."
            )
        if not _describes(target, request.url):
            raise BlockedAddress(
                "the crawler will not send a request to a different destination from the one "
                "that was checked."
            )
        if not target.addresses:
            raise BlockedAddress(
                "the crawler will not connect to a host whose check approved no addresses."
            )

        request.headers["Host"] = authority(target)
        request.extensions[SNI_EXTENSION] = target.host

        named = request.url
        failure: Exception | None = None
        for address in target.addresses:
            assert_safe_address(address, url=str(named))
            request.url = named.copy_with(host=address)
            try:
                return self._inner.handle_request(request)
            except FETCH_FAILURES as failed:
                failure = failed
        assert failure is not None, "the loop ran at least once, so it either returned or failed"
        raise failure


def _the_same_host(checked: str, requested: str) -> bool:
    """Whether two spellings of a host name are the same host.

    **THE TWO SIDES COME FROM DIFFERENT PARSERS, AND THEY DISAGREE ABOUT EXACTLY
    ONE THING: AN INTERNATIONALISED DOMAIN.** `SafeTarget.host` is
    `urlsplit().hostname`, which lower-cases and otherwise leaves the string
    alone; `httpx.URL.host` DECODES punycode to Unicode. So a merchant who types
    their own domain the way their registrar displays it -
    `https://xn--bcher-kva.example/` - produced `'xn--bcher-kva.example'` on one
    side and `'bücher.example'` on the other, and a string comparison called that
    a different destination. Measured: the crawl refused, every time, before it
    made a single request, and told the merchant "the crawler will not send a
    request to a different destination from the one that was checked" - which is
    not true. It is the same host, the same address and the same port.

    So the comparison normalises rather than trusting either spelling: both sides
    are IDNA-encoded, which is a no-op for an ASCII name and turns both spellings
    of an IDN into the same punycode. A host that cannot be encoded at all - an
    empty label, a label over 63 characters - is NOT the same host as anything,
    so the refusal stands.

    **THIS CANNOT WIDEN WHAT IS CONNECTED TO.** IDNA is a bijection over the
    names it accepts, so two different hosts cannot normalise to one; and the
    connection is aimed at `SafeTarget.addresses` regardless of what this
    returns. What it decides is whether a checked judgement may be used for this
    request at all.
    """
    if requested == checked:
        return True
    try:
        return requested.encode("idna") == checked.encode("idna")
    except (UnicodeError, ValueError):
        return False


def _describes(target: SafeTarget, url: httpx.URL) -> bool:
    """Whether `target` is a judgement about exactly this URL's destination.

    Scheme, host and port, because those three are what a connection is made of
    and what `assert_safe_url` judged. The PATH deliberately does not have to
    match: a `SafeTarget` is a judgement about an origin, and this module reuses
    one across the hops of a single request. Comparing paths would forbid that
    without making anything safer.
    """
    port = url.port if url.port is not None else DEFAULT_PORTS.get(url.scheme)
    return (
        url.scheme == target.scheme
        and _the_same_host(target.host, url.host)
        and port == target.port
    )


def build_client(
    *, timeout_seconds: float, inner: httpx.BaseTransport | None = None
) -> httpx.Client:
    """An `httpx.Client` that can only connect to addresses that were judged.

    **THE ONLY PRODUCER OF A CLIENT `crawl` WILL ACCEPT**, and the tests use it
    too - a fixture that built a bare `httpx.Client` around a fake would be
    exercising a path production never takes, and the one property that matters
    here lives in the transport it would have skipped.

    `follow_redirects=False` is not a default being restated: httpx following a
    redirect itself would skip `assert_safe_redirect`, and the request it made
    would carry the previous hop's target, which `_describes` then refuses. It
    fails closed either way; saying it here means it never gets that far.

    `NO_CONNECTION_REUSE` is the other non-default, and it is a security setting:
    see that constant for the measurement. It is on the transport rather than on
    the `Client`, because httpx ignores `limits=` entirely when it is handed a
    `transport=`.
    """
    return httpx.Client(
        transport=PinnedAddressTransport(
            inner=inner
            if inner is not None
            else httpx.HTTPTransport(retries=0, limits=NO_CONNECTION_REUSE)
        ),
        follow_redirects=False,
        timeout=httpx.Timeout(timeout_seconds),
    )


def _pinned_transport(client: httpx.Client) -> PinnedAddressTransport:
    """The client's transport, if the client is one this module may send through.

    **THIS IS THE GUARD THAT STOPS AN ORDINARY `httpx.Client` BEING INJECTED**,
    and it is the difference between a defence and a decoration. An ordinary
    client resolves the host itself, so a `crawl` that accepted one would make a
    second DNS query per request and connect to whatever the second answer said -
    with every functional test still passing, because a fake site answers to any
    address. Three ways in, all closed:

      * a transport that is not a `PinnedAddressTransport`;
      * a client with `mounts`, which route a URL pattern to a DIFFERENT
        transport and so bypass the pinned one for exactly the URLs an attacker
        would choose;
      * a client that follows redirects itself, which skips
        `assert_safe_redirect`.

    `_transport` and `_mounts` are httpx internals, which is a real cost and is
    why `test_build_client_puts_the_pinned_transport_where_the_guard_looks` reads
    them through this function on a client `build_client` made: if a future httpx
    renames either, that test fails rather than this guard silently passing
    everything.
    """
    transport = getattr(client, "_transport", None)
    if not isinstance(transport, PinnedAddressTransport):
        raise BlockedAddress(
            "the crawler was given an HTTP client that resolves host names itself. It only "
            "sends requests through a transport that connects to an address already checked."
        )
    if getattr(client, "_mounts", None):
        raise BlockedAddress(
            "the crawler was given an HTTP client with mounted transports, which would route "
            "some URLs around the checked one."
        )
    if client.follow_redirects:
        raise BlockedAddress(
            "the crawler was given an HTTP client that follows redirects itself, which would "
            "skip the check every redirect hop has to go through."
        )
    return transport


# --------------------------------------------------------------------------
# robots.txt
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Robots:
    """The rules that apply to US, from one site's `robots.txt`.

    **LONGEST MATCH WINS, AND `Allow` BREAKS A TIE**, which is RFC 9309 §2.2.2
    and is not the same as first-match: a site with `Disallow: /` and
    `Allow: /public/` means the second thing, and a first-match reader crawls
    nothing.
    """

    rules: tuple[tuple[str, re.Pattern[str], bool], ...]

    def allows(self, path: str) -> bool:
        best: tuple[int, bool] | None = None
        for value, pattern, allowed in self.rules:
            if pattern.match(path) and (best is None or (len(value), allowed) > best):
                best = (len(value), allowed)
        return True if best is None else best[1]


#: A `robots.txt` we could not read at all. Every path is allowed, which is RFC
#: 9309 §2.3.1.3's "unavailable" case: a site with no `robots.txt` has not asked
#: for anything, and refusing to crawl it would fail every small business whose
#: hosting serves a 404 for it.
ROBOTS_ALLOW_ALL: Final = Robots(rules=())

#: A `robots.txt` whose server answered but failed. RFC 9309 §2.3.1.4's
#: "unreachable" case, and the standard is explicit that this means crawl
#: NOTHING. It costs us a merchant whose site is having a bad minute, and what it
#: costs them is a wizard that asks three questions instead of reading the
#: answers - a fallback rather than a failure.
ROBOTS_ALLOW_NOTHING: Final = Robots(rules=(("/", re.compile("/"), False),))


def _robots_pattern(value: str) -> re.Pattern[str]:
    """One `Allow`/`Disallow` value as a prefix pattern.

    RFC 9309 §2.2.3's two wildcards: `*` matches any run of characters and a
    trailing `$` anchors the end. Everything else is a literal, escaped, so a
    path containing a `.` or a `+` cannot become a pattern of its own.
    """
    anchored = value.endswith("$")
    body = value[:-1] if anchored else value
    pattern = "".join(".*" if character == "*" else re.escape(character) for character in body)
    return re.compile(pattern + ("$" if anchored else ""))


def parse_robots(text: str, agent_token: str = ROBOTS_AGENT_TOKEN) -> Robots:
    """The rules for `agent_token`, or for `*` if the file names no group for us.

    A group is a run of `User-agent:` lines followed by rules; a `User-agent:`
    line after a rule starts a NEW group, which is the one piece of this format
    that a naive line-by-line reader gets wrong.

    An EMPTY value contributes no rule. `Disallow:` with nothing after it means
    "nothing is disallowed" rather than "everything is", and a reader that turned
    it into a rule matching the empty prefix would refuse to crawl the sites
    trying hardest to be crawled.
    """
    groups: list[tuple[set[str], list[tuple[str, re.Pattern[str], bool]]]] = []
    agents: set[str] = set()
    rules: list[tuple[str, re.Pattern[str], bool]] = []
    naming_agents = True

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if not naming_agents:
                groups.append((agents, rules))
                agents, rules = set(), []
            naming_agents = True
            agents.add(value.lower())
        elif field in ("allow", "disallow"):
            naming_agents = False
            if value:
                rules.append((value, _robots_pattern(value), field == "allow"))
    groups.append((agents, rules))

    token = agent_token.lower()
    for wanted in (token, "*"):
        for named, group_rules in groups:
            if wanted in named:
                return Robots(rules=tuple(group_rules))
    return ROBOTS_ALLOW_ALL


# --------------------------------------------------------------------------
# Politeness
# --------------------------------------------------------------------------


class _Pace:
    """At most `rps` requests a second to any one host.

    Per host rather than overall, because the limit is a courtesy to a server
    and two servers are two servers. The clock and the sleep are injected for the
    same reason the resolver is: a test that measures rate limiting by actually
    waiting is a test that makes the suite slower every time someone tightens the
    limit.
    """

    def __init__(
        self, rps: float, *, now: Callable[[], float], pause: Callable[[float], None]
    ) -> None:
        if rps <= 0:
            raise ValueError(f"rps_per_host must be positive, not {rps!r}")
        self._interval = 1.0 / rps
        self._now = now
        self._pause = pause
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        previous = self._last.get(host)
        if previous is not None:
            outstanding = self._interval - (self._now() - previous)
            if outstanding > 0:
                self._pause(outstanding)
        self._last[host] = self._now()


# --------------------------------------------------------------------------
# The crawl
# --------------------------------------------------------------------------


def _same_site(candidate: str, target: SafeTarget) -> bool:
    """Whether a discovered link is on the site we were asked to read.

    Host AND scheme AND port, compared to the crawl's SCOPE - which is where the
    ENTRY page landed - rather than to the page the link was found on: a chain of
    same-host redirects that ends somewhere else must not widen the crawl, and
    comparing to the current page would let it. `crawl` sets the scope once, from
    the entry page's own redirect, and never again.

    **EACH OF THE THREE IS PINNED BY A CASE WHERE ONLY THAT ONE REFUSES**, in
    `SAME_SITE_CASES`. Any one of them held the whole function up while the only
    off-site link in the fixture corpus differed in scheme AND host at once - so
    all three could be deleted one at a time with the suite green, and deleting
    the host comparison sends the crawler off to spend a merchant's page budget
    reading a third party's site.
    """
    parts = urlsplit(candidate)
    port = parts.port if parts.port is not None else DEFAULT_PORTS.get(parts.scheme.lower())
    return (
        parts.scheme.lower() == target.scheme
        and _the_same_host(target.host, (parts.hostname or "").lower())
        and port == target.port
    )


def _path_of(url: str) -> str:
    """The path a `robots.txt` rule is matched against, query included."""
    parts = urlsplit(url)
    return urlunsplit(("", "", parts.path or "/", parts.query, ""))


def _identity_inflater() -> Callable[[bytes, int], bytes]:
    """A body that is not encoded at all: at most `room` of it, per chunk."""
    return lambda chunk, room: chunk[:room]


def _gzip_inflater() -> Callable[[bytes, int], bytes]:
    """**A GZIP BODY, DECOMPRESSED A BOUNDED AMOUNT AT A TIME.**

    `zlib.decompressobj().decompress(data, max_length)` is the whole reason this
    module can accept compression at all: it produces AT MOST `max_length` bytes
    and keeps the rest as `unconsumed_tail` instead of materialising it. Nothing
    in httpx or httpcore takes such a bound - their decoders hand back whatever
    one chunk expands to, which is the defect this replaced.

    The tail is dropped rather than fed back, and that is safe for exactly one
    reason: a non-empty tail can only happen when the output hit `max_length`,
    and `_read_capped` stops reading in the same statement. If it ever continued,
    the tail would have to go back in first or the output would be corrupt.
    """
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    return lambda chunk, room: decompressor.decompress(chunk, room)


#: The `Content-Encoding` values this module can read, and the ONLY ones it will.
#: Held equal to `ACCEPT_ENCODING` by a test, because an encoding we ask for and
#: cannot bound is the hole, and an encoding we can bound and do not ask for is
#: dead code. The empty string is "the header was absent", which is the ordinary
#: case rather than an encoding.
_INFLATERS: Final = {
    "": _identity_inflater,
    "identity": _identity_inflater,
    "gzip": _gzip_inflater,
}


def _read_capped(response: httpx.Response) -> bytes:
    """At most `MAX_RESPONSE_BYTES` OFF THE WIRE and at most that much IN MEMORY.

    **THE CAP HAS TO BOUND THE COST, NOT THE RESULT, AND THOSE COME APART THE
    MOMENT THE SERVER COMPRESSES.** The first version of this read
    `response.iter_bytes()` - httpx's DECODED stream - and extended the buffer by
    a whole chunk before consulting the cap. With `Content-Encoding: gzip` one
    64 KB chunk on the wire is one arbitrarily large chunk in memory, so the
    result came back neatly capped at 2 MB while the process had allocated 850 MB
    getting there: 388 KB on the wire, 425x the cap in heap, measured end to end
    through `crawl`. A `chunk_size=` on `iter_bytes` makes it WORSE (the decoder
    still expands the whole chunk first, and the chunker then buffers a second
    copy of it), so this is not a tuning question - the decompression itself has
    to be bounded.

    So the body is read RAW - `iter_raw` is the stream before httpx decodes
    anything - and the two bounds are applied separately, because they are two
    different quantities that happen to share one number:

      * `allowance` bounds the TRANSFER, and is what stops a stream that decodes
        to nothing - deflate can encode an endless run of empty blocks - from
        being read for as long as the time budget allows;
      * `room` bounds the MEMORY, and is what stops a compression bomb.

    Each is applied BEFORE the buffer is extended, not after, so neither can be
    exceeded by one chunk - and the `break` says "a budget ran out" in terms of
    those two rather than naming the constant a third and fourth time, so the cap
    appears exactly once per quantity it bounds. **THOSE TWO ARE NOT THE SAME
    STATEMENT WRITTEN TWICE**, which is the thing this module has already been
    bitten by: each is caught by a test the other cannot fail - the bomb for
    `room`, the stream that decodes to nothing for `allowance` - and that was
    measured rather than argued.

    An encoding `_INFLATERS` has no bounded decoder for is not read at all: the
    page contributes nothing, which is the same answer this module already gives
    for a PDF.
    """
    encoding = response.headers.get("content-encoding", "").strip().lower()
    build = _INFLATERS.get(encoding)
    if build is None:
        _LOG.info("the crawler does not read a body encoded as %r", encoding)
        return b""
    inflate = build()

    body = bytearray()
    transferred = 0
    for chunk in response.iter_raw():
        room = MAX_RESPONSE_BYTES - len(body)
        allowance = MAX_RESPONSE_BYTES - transferred
        taken = chunk[:allowance]
        transferred += len(taken)
        inflated = inflate(taken, room)
        body += inflated
        if len(taken) == allowance or len(inflated) == room:
            break
    return bytes(body)


def _decoded(response: httpx.Response, body: bytes) -> str:
    """The body as text, never raising on a page that lies about its encoding."""
    encoding = response.charset_encoding or "utf-8"
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _is_html(response: httpx.Response) -> bool:
    header = response.headers.get("content-type", "")
    if not header.strip():
        return True
    return header.split(";", 1)[0].strip().lower() in HTML_CONTENT_TYPES


def _send(
    client: httpx.Client, target: SafeTarget, *, timeout: float, pace: _Pace
) -> tuple[int, httpx.Headers, bytes, str]:
    """One request to one checked target: status, headers, body, decoded text.

    **THE RATE LIMIT IS APPLIED HERE, WHICH IS THE ONLY PLACE IT IS TRUE.** A
    crawl makes requests the page loop never sees - `robots.txt` before it starts,
    and every hop of a redirect chain - and pacing the loop rather than the
    request would leave a six-hop chain going out as six requests back to back,
    which is exactly the burst a small server notices.
    """
    pace.wait(target.host)
    request = client.build_request(
        "GET",
        target.url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT,
            "Accept-Encoding": ACCEPT_ENCODING,
        },
        extensions={SAFE_TARGET_EXTENSION: target},
        timeout=httpx.Timeout(timeout),
    )
    response = client.send(request, stream=True)
    try:
        body = _read_capped(response) if _is_html(response) else b""
        return response.status_code, response.headers, body, _decoded(response, body)
    finally:
        response.close()


def _follow(
    client: httpx.Client,
    target: SafeTarget,
    *,
    resolver: Resolver | None,
    timeout: float,
    pace: _Pace,
    permitted: Callable[[SafeTarget], bool] | None = None,
) -> tuple[SafeTarget, int, httpx.Headers, bytes, str] | None:
    """Request `target`, following at most `MAX_REDIRECTS` hops, and report where
    the chain ENDED: `(final_target, status, headers, body, text)`.

    **THE ONE REDIRECT LOOP IN THIS MODULE, BECAUSE A SECOND ONE WOULD BE THE CAP
    WRITTEN DOWN TWICE.** Both callers need the same thing - pages need it because
    a merchant's site redirects, and `robots.txt` needs it because
    `http://example.com/robots.txt` answering `301 https://example.com/robots.txt`
    is the commonest configuration on the web. `_robots_for` originally had no
    loop at all and read a `301` as "unreachable", which meant crawl NOTHING: a
    merchant who typed their site without the scheme got zero pages, every time.
    Writing a second `range(MAX_REDIRECTS + 1)` to fix that would have re-created
    exactly the defect §5 of this task's report exists to record, so there is one
    loop and both callers use it.

    `permitted` is called with each target BEFORE it is requested, and `None`
    comes back if it refuses. Pages pass `robots.allows` here; the `robots.txt`
    request itself passes nothing, because a file that says what may be fetched
    cannot be gated on itself.

    Each hop is resolved again, by `assert_safe_redirect`, because each hop is a
    new URL somebody else chose. `None` also means the chain outran the cap.

    **THE CAP IS SAID ONCE.** `range(MAX_REDIRECTS + 1)` bounds the REQUESTS, and
    `MAX_REDIRECTS` hops followed and `MAX_REDIRECTS + 1` requests made are the
    same statement, so writing both down is one bound in two places. It was
    written both ways at first - a `range` AND an `if hops_followed ==
    MAX_REDIRECTS` inside it - and the mutation battery is what found that out:
    changing EITHER of them alone left the other enforcing the same limit, so
    three separate mutations of the cap were equivalent mutants and no
    behavioural test could see any of them. A redirect LOOP is bounded by the
    same one line, without needing to detect that it is a loop.

    **THE ONE THING THE SINGLE BOUND COSTS, AND IT FAILS CLOSED.** On a chain
    longer than the cap, the last `Location` is still resolved and CHECKED by
    `assert_safe_redirect` before the loop ends - it is simply never fetched. So
    an over-long chain whose last hop points somewhere private comes back as a
    refusal rather than as a quiet give-up, which is the more useful of the two
    true answers: the merchant's site really is redirecting towards a private
    address. `test_a_chain_at_the_cap_whose_last_hop_is_unsafe_is_refused` pins
    it so it is a decision rather than a side effect.
    """
    for _ in range(MAX_REDIRECTS + 1):
        if permitted is not None and not permitted(target):
            return None
        status, headers, body, text = _send(client, target, timeout=timeout, pace=pace)
        if status not in REDIRECT_STATUSES:
            return target, status, headers, body, text
        target = assert_safe_redirect(
            target.url, headers.get("location", ""), resolver=resolver
        )
    _LOG.info("the crawler stopped following redirects after %d hops", MAX_REDIRECTS)
    return None


def _fetch(
    client: httpx.Client,
    target: SafeTarget,
    *,
    resolver: Resolver | None,
    timeout: float,
    pace: _Pace,
    robots: _RobotsRules,
    landed: set[str],
) -> tuple[SafeTarget, str] | None:
    """Fetch one page. `(final_target, html)`, or `None` if there was nothing.

    Takes a target rather than a URL, so the caller's resolution is the one used
    and this host is looked up ONCE per page rather than once here and once
    wherever the caller needed to know the origin. Returns the final TARGET
    rather than the final URL because the caller needs the origin the chain ended
    on, and re-parsing the URL to get it would be a second answer to a question
    already answered.

    `None` when the page is not readable: a non-2xx status, a media type we do
    not parse, a redirect chain longer than the cap, or a URL this origin's
    `robots.txt` disallows. A refusal is NOT `None` - `BlockedAddress`
    propagates, because "we would not go there" is a different fact from "there
    was nothing to read".

    **`robots.txt` IS CHECKED FOR EVERY HOP, WHICH IS THE ONLY PLACE IT IS TRUE.**
    Every hop is a URL somebody else chose, on an origin they chose, so the rules
    are consulted for the target about to be SENT to rather than for the one the
    frontier held - see `_RobotsRules` for the two ways a redirect got round the
    first version.
    """
    followed = _follow(
        client, target, resolver=resolver, timeout=timeout, pace=pace,
        permitted=lambda hop: hop.url not in landed and robots.allows(hop, timeout=timeout),
    )
    if followed is None:
        return None
    final, status, _headers, body, text = followed
    if not 200 <= status < 300 or not body:
        return None
    return final, text


def _robots_for(
    client: httpx.Client,
    origin: SafeTarget,
    *,
    resolver: Resolver | None,
    timeout: float,
    pace: _Pace,
) -> Robots:
    """One origin's `robots.txt`, read through the same checked path as any page.

    Takes any target on the origin and asks that origin - `robots.txt` is a
    property of a scheme, host and port, not of a site, so a redirect onto
    another origin lands somewhere with its own file and its own rules.
    """
    robots_url = urlunsplit((origin.scheme, authority(origin), "/robots.txt", "", ""))
    try:
        target = assert_safe_url(robots_url, resolver=resolver)
        followed = _follow(client, target, resolver=resolver, timeout=timeout, pace=pace)
    except FETCH_FAILURES:
        return ROBOTS_ALLOW_NOTHING
    if followed is None:
        return ROBOTS_ALLOW_NOTHING
    _final, status, _headers, _body, text = followed
    if status == 200:
        return parse_robots(text)
    if 400 <= status < 500:
        return ROBOTS_ALLOW_ALL
    return ROBOTS_ALLOW_NOTHING


class _RobotsRules:
    """Every origin the crawl touches, and what that origin allows us to fetch.

    **THE RULES ARE CHECKED AGAINST THE URL THAT IS ACTUALLY FETCHED, WHICH IS
    NOT THE URL THAT WAS QUEUED.** The first version of this module read one
    `robots.txt` - the entry origin's - and consulted it once per FRONTIER entry,
    before `_fetch` followed up to five redirects. So a `302` was a way round the
    file entirely: executed, a site with `Disallow: /private` served `/door.html`
    as `302 Location: /private/trade-portal.html` and the disallowed page was
    fetched AND kept. Cross-origin it was worse - the redirect was followed to
    another host whose `robots.txt` was never fetched at all, which puts our own
    `User-Agent` in a third party's access log on a path they asked us to stay
    off. That is the outcome `USER_AGENT`'s comment exists to avoid.

    So the check lives in `_fetch`, applied to every target it is about to send
    to, and the rules are keyed on the ORIGIN of that target. One fetch per
    origin per crawl: a site is nearly always one origin, so the ordinary case
    still costs exactly one `robots.txt` request, and a redirect to a second
    origin costs one more rather than none.
    """

    def __init__(
        self, client: httpx.Client, *, resolver: Resolver | None, pace: _Pace
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._pace = pace
        self._known: dict[tuple[str, str, int], Robots] = {}

    def allows(self, target: SafeTarget, *, timeout: float) -> bool:
        origin = (target.scheme, target.host, target.port)
        if origin not in self._known:
            self._known[origin] = _robots_for(
                self._client, target, resolver=self._resolver, timeout=timeout,
                pace=self._pace,
            )
        allowed = self._known[origin].allows(_path_of(target.url))
        if not allowed:
            _LOG.info("robots.txt does not allow %s", target.url)
        return allowed


def _first(values: Iterable[str]) -> str:
    """The first non-empty string, or the empty string."""
    for value in values:
        if value:
            return value
    return ""


def _merged(values: Iterable[Iterable[str]], limit: int) -> tuple[str, ...]:
    """De-duplicated in page order, capped."""
    seen: dict[str, None] = {}
    for group in values:
        for value in group:
            seen.setdefault(value, None)
    return tuple(seen)[:limit]


def _result(pages: list[Page]) -> CrawlResult:
    """Everything the crawl read, folded into one profile.

    The first page is the one the merchant named, so its `<title>` and
    description are the site's rather than a sub-page's; every other field takes
    the first page that had one, in the order the crawl reached them.
    """
    extracts = [page.extract for page in pages]
    page_text = " ".join(item.page_text for item in extracts if item.page_text)
    return CrawlResult(
        pages=tuple(pages),
        business_name=_first(item.business_name for item in extracts),
        services=_merged((item.services for item in extracts), MAX_SERVICES_IN_A_RESULT),
        unique_selling_points=_merged(
            (item.unique_selling_points for item in extracts), MAX_SELLING_POINTS_IN_A_RESULT
        ),
        phone=_first(item.phone for item in extracts),
        address=_first(item.address for item in extracts),
        meta_title=_first(item.meta_title for item in extracts),
        meta_description=_first(item.meta_description for item in extracts),
        page_text=page_text,
        source=(
            SOURCE_CRAWLED
            if len(page_text) >= MIN_TEXT_FOR_A_USABLE_PROFILE
            else SOURCE_INSUFFICIENT
        ),
    )


def crawl(
    url: str,
    *,
    max_pages: int,
    timeout_seconds: float,
    rps_per_host: float,
    client: httpx.Client | None = None,
    resolver: Resolver | None = None,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> CrawlResult:
    """Read a merchant's website, breadth-first, and report what it said.

    `client` must be a client `build_client` made; anything else is refused, for
    the reason `_pinned_transport` sets out. `None` means one is built and closed
    here.

    `resolver` is `ssrf`'s seam, `None` meaning `socket.getaddrinfo` looked up at
    call time. `clock` and `sleep` are the pacing seams; both default to
    `time`'s and both exist so the time budget and the rate limit can be
    exercised without a test that waits.

    **THE ENTRY URL'S REFUSAL PROPAGATES; A DISCOVERED LINK'S DOES NOT.** The
    merchant typed the entry URL and has to be told we would not fetch it. A link
    found ON their site that resolves somewhere private is a fact about their
    site, not about their request, so it is logged and skipped - and the crawl
    still produces whatever the rest of the site said.

    **WHICH SITE THIS IS, IS DECIDED ONCE, BY THE ENTRY PAGE'S OWN REDIRECT.** A
    merchant who types `http://theirsite.example` at a site that redirects to
    `https://` has named their site; the `301` is the site saying where it lives.
    Scoping the crawl to what they TYPED reads the home page and then calls every
    link on it off-site - measured against the fixture site, three pages became
    one and the profile lost more than half its text. So `scope` is taken from
    where the entry page landed and is read-only afterwards: a link on a page
    still cannot widen the crawl, and neither can a redirect on any page but the
    entry.

    **EVERY REFUSAL IS LOGGED WITH `BlockedAddress.address` AND RENDERED WITHOUT
    IT.** The address is for the operator reading the log; the message is for the
    merchant, and a message naming the address would turn the onboarding form
    into an internal address enumeration oracle. See `BlockedAddress`.

    That sentence was FALSE when it was first written, in both halves, and both
    are now held by the shape of this function rather than by discipline:

      * **logged.** The whole body is inside ONE `except BlockedAddress` handler
        that logs and re-raises, because a refusal used to be logged at the two
        `raise` sites somebody thought of - and a host that rebinds between the
        entry check and the `robots.txt` request was refused at a third, outside
        both of them, reaching the caller with no log line at all;
      * **rendered without it.** Both routes out of here - the entry check and a
        refusal from inside the page loop - are driven by
        `REFUSAL_ROUTES` in `tests/crawler/test_fetch.py`, which asserts the
        message and the log line for each. Pinning only the entry route left the
        REDIRECT route - the one where the address is the one the merchant does
        not know - open to two mutations that put it in front of them, both of
        which survived a green suite.
    """
    now = time.monotonic if clock is None else clock
    pause = time.sleep if sleep is None else sleep
    owned = client is None
    http = build_client(timeout_seconds=timeout_seconds) if client is None else client
    pace = _Pace(rps_per_host, now=now, pause=pause)
    deadline = now() + timeout_seconds

    try:
        try:
            _pinned_transport(http)
            entry = assert_safe_url(url, resolver=resolver)
            robots = _RobotsRules(http, resolver=resolver, pace=pace)

            pages: list[Page] = []
            frontier: list[str] = [entry.url]
            seen: set[str] = {entry.url}
            # **WHERE PAGES WERE QUEUED FROM AND WHERE THEY LANDED ARE TWO
            # DIFFERENT SETS, BECAUSE A REDIRECT MAKES THEM DIFFERENT.** `seen`
            # stops a URL being queued twice; `landed` stops a page being READ
            # twice when two frontier URLs redirect onto one, which `seen` cannot
            # see - it holds the URLs a link named, and a `Location:` is not one
            # of those. Found by measuring an `http` -> `https` crawl of the
            # fixture site: the home page came back twice, once as the entry's
            # redirect target and once as its own navigation link.
            #
            # `landed` is read in exactly one place - the hook that already asks
            # "may this target be requested" - and adding the landing URL to
            # `seen` as well was tried and REMOVED: the battery showed it changed
            # nothing any test could see, because the hook had already refused,
            # and a second copy of a rule that saves one DNS lookup is how this
            # module has twice ended up with two bounds and no pin on either.
            landed: set[str] = set()
            scope = entry
            while frontier and len(pages) < max_pages:
                remaining = deadline - now()
                if remaining <= 0:
                    _LOG.info("the crawler ran out of time after %d pages", len(pages))
                    break
                page_url = frontier.pop(0)
                try:
                    # The entry was resolved above, to learn the origin the
                    # same-site test is keyed on; re-resolving it here would be a
                    # second lookup of one host for one page.
                    target = (
                        entry
                        if page_url == entry.url
                        else assert_safe_url(page_url, resolver=resolver)
                    )
                    fetched = _fetch(
                        http, target, resolver=resolver, timeout=remaining, pace=pace,
                        robots=robots, landed=landed,
                    )
                except BlockedAddress as refused:
                    if page_url == entry.url:
                        raise
                    _log_refusal(refused)
                    continue
                except FETCH_FAILURES as failed:
                    _LOG.info("the crawler could not read a page: %s", failed)
                    continue
                if fetched is None:
                    continue
                final, html = fetched
                if page_url == entry.url:
                    # **THE ENTRY PAGE'S OWN REDIRECT DECIDES WHICH SITE THIS IS,
                    # AND NOTHING ELSE EVER WIDENS IT.** A merchant who types
                    # `http://theirsite.example` at a site that redirects to
                    # `https://` has named the site; the `301` is the site saying
                    # where it lives. Scoping the crawl to what they TYPED reads
                    # the home page and then calls every link on it off-site -
                    # measured, three pages became one. So the scope is taken from
                    # where the ENTRY page landed, once, and every hop of that
                    # redirect was checked by `assert_safe_redirect` on the way.
                    #
                    # This is not the thing `_same_site` guards. A link found on a
                    # page still cannot widen the crawl, and a redirect on any
                    # OTHER page still cannot: the scope is set here, from the one
                    # URL the merchant supplied, and is read-only afterwards.
                    scope = final
                landed.add(final.url)
                found = extract(html, final.url)
                pages.append(Page(url=final.url, extract=found))
                for link in found.links:
                    if link not in seen and _same_site(link, scope):
                        seen.add(link)
                        frontier.append(link)
            return _result(pages)
        except BlockedAddress as refused:
            # **THE ONE PLACE A REFUSAL LEAVES THIS FUNCTION, SO IT IS THE ONE
            # PLACE THE LOG LINE HAS TO BE.** The first version logged at the two
            # `raise` sites it could think of, and a third existed: a host that
            # rebinds between the entry check and the `robots.txt` request is
            # refused inside `_robots_for`, which sat outside both handlers, so
            # that refusal reached the caller with no log line at all - and so did
            # every refusal from `_pinned_transport`. Wrapping the whole body
            # instead means "every refusal is logged" is a property of the
            # function's shape rather than of somebody having remembered.
            _log_refusal(refused)
            raise
    finally:
        if owned:
            http.close()


def _log_refusal(refused: BlockedAddress) -> None:
    """**THE ADDRESS GOES IN THE LOG AND NOWHERE ELSE.**

    `str(refused)` is written to be safe to show a merchant - Task 26 took the
    resolved address out of it deliberately, because the party who chose the
    hostname must not learn what it resolves to inside our network. The operator
    reading this line needs exactly that, so it is passed separately, from the
    attribute that exists for this purpose. `None` for a refusal that never
    reached an address, which is why this logs it unconditionally rather than
    branching.
    """
    _LOG.warning("the crawler refused a URL: %s (it resolved to %s)", refused, refused.address)
