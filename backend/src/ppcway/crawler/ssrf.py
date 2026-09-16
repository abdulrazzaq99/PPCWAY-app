"""Server-side request forgery defence at the crawler's boundary.

Blueprint §12.6. The onboarding wizard asks a merchant for their website and
then fetches it from inside our network. That is a request whose destination an
untrusted party chooses, which is the whole of what SSRF is - and the crawler
runs beside Postgres, Redis, Temporal and, in any real deployment, a cloud
instance metadata service that hands out credentials to anything that asks.
`http://169.254.169.254/latest/meta-data/iam/security-credentials/` is one HTTP
GET away from the machine role.

**THE ONE THING THIS MODULE IS FOR: THE ADDRESS THAT WAS CHECKED MUST BE THE
ADDRESS THAT IS CONNECTED TO.** Everything else here is detail. A function that
takes a URL, resolves it, approves it and returns `None` is not a defence, it is
a delay: the HTTP client then resolves the same name AGAIN, and a DNS server the
attacker controls answers the second query with `127.0.0.1`. That is DNS
rebinding, it is the standard bypass for exactly this shape of check, and it is
why `assert_safe_url` RETURNS the addresses it approved instead of returning
nothing. `SafeTarget.addresses` is not a diagnostic; it is the connection's
instruction. The three obligations, and the third is the one that closes the
window:

  1. this module resolves the host ONCE - pinned by counting the resolver's
     calls, because a second resolution inside the check would reopen the
     window it exists to close;
  2. the caller connects to `SafeTarget.addresses`, never to `SafeTarget.host`,
     and sends `host` as the `Host:` header and TLS server name so the
     certificate is still verified against the name the merchant gave;
  3. at the moment of connection the caller calls `assert_safe_address` on the
     address it is ACTUALLY about to use. That is the same predicate, applied to
     the same kind of value, so the pre-flight check and the connection cannot
     disagree about what is safe - `tests/crawler/test_ssrf.py` sweeps both
     entry points over the same address table and asserts they agree case for
     case.

**THE BLOCKED SET IS DERIVED, NOT LISTED.** There is no table of CIDRs here and
there must never be one: a hand-maintained list is the single most reliably
recurring defect on this project (seven occurrences, the most recent inside the
fix for the one before it), and the SSRF variety of it is famous - every list of
`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` ever written has missed
something. This one is an ALLOWLIST expressed in `ipaddress`' own vocabulary:

    an address is permitted only if `is_global` and not `is_multicast`
    and not `is_reserved` and not `is_site_local`

All four conjuncts are load-bearing on CPython 3.12, and each has a witness in
the tests: `10.0.0.5` is not global; `224.0.0.1` IS global and is multicast;
`64:ff9b::7f00:1` IS global and is reserved (it is the NAT64 well-known prefix
with `127.0.0.1` inside it); `fec0::1` IS global, is neither multicast nor
reserved, and is site-local. `is_private`, `is_loopback`, `is_link_local` and
`is_unspecified` are NOT part of the decision - they are only used to say WHY a
refusal happened, because "10.0.0.5 is a private address" is a better error than
"10.0.0.5 is not globally routable".

What the allowlist form buys over the usual denylist, measured rather than
argued: `100.64.0.1` and `100.100.100.200` - carrier-grade NAT space, and
Alibaba Cloud's metadata endpoint - have NO `ipaddress` property set at all.
`is_private` is False for both. A check written as "private or loopback or
link-local or reserved or unspecified", which is what this task's own plan
specified, ALLOWS the Alibaba metadata endpoint. `is_global` refuses it.

**AND THE FOURTH CONJUNCT IS THE IPv6 MIRROR OF THAT SAME CASE, WHICH THIS
MODULE MISSED UNTIL A REVIEW SWEPT THE IANA REGISTRY AGAINST IT.** `fec0::/10`
- IPv6 site-local unicast - was deprecated by RFC 3879 in 2004, and CPython
follows RFC 4193 by DELIBERATELY excluding it from the list behind `is_private`.
It is not private, not reserved, not link-local: `is_global` is TRUE for it, and
`ipaddress` exposes it only as `is_site_local`. So `assert_safe_address("fec0::1")`
returned normally, and a merchant zone answering AAAA `fec0::1` got a `SafeTarget`
naming it. Linux forwards `fec0::/10` as ordinary global-scope unicast - the
kernel special case went away with the deprecation - so it reaches whatever
internal host still holds a legacy site-local address. The property is read
through `getattr` with a default because `IPv4Address` does not have it. The
lesson is the module's own headline argument turned on itself: an allowlist over
`ipaddress` properties is only as complete as the set of properties it reads,
and "which properties" is the thing that needs a registry sweep, not a guess.

**THE HOSTNAME IS NEVER PARSED HERE, AND THAT IS THE ANSWER TO THE ADDRESS
FORMS.** `2130706433`, `0177.0.0.1` and `0x7f.0.0.1` are all `127.0.0.1` to
`inet_aton`, which is what the C library hands `getaddrinfo`; `::ffff:127.0.0.1`
is loopback wearing an IPv6 costume. None of that is this module's problem,
because it never asks what the host string looks like - it asks the resolver
what the host IS and judges the answer. A denylist of dotted-quad strings would
have to enumerate every spelling; judging the resolved address enumerates none.
(`tests/crawler/test_ssrf.py` executes the `inet_aton` claim rather than
asserting it, so the premise is measured.)

**KNOWN OVER-BLOCKS, disclosed rather than discovered later.** Both fail closed,
which is the right direction, and both are real:

  * `64:ff9b::/96` is reserved, so on a DNS64/NAT64-only network EVERY public
    IPv4 site resolves to an address this module refuses. Decoding NAT64 would
    mean writing that prefix down as a literal - the thing this module is
    structured to avoid - and would then need the embedded address checked
    anyway. Not the deployment we have; recorded so nobody debugs it twice.
  * A merchant site behind carrier-grade NAT, or served on a port other than 80
    or 443, is refused. The alternative is a crawler that can be pointed at
    Redis on 6379 or at an SMTP server on a public address.

**WHAT IS NOT HERE.** Redirect FOLLOWING and the request itself belong to Task
27's `fetch.py`; this module gives it `MAX_REDIRECTS` and `assert_safe_redirect`,
which re-runs the whole check on each hop's resolved `Location`. A guard that
`fetch.py` calls them belongs beside `fetch.py`, where there is something to
walk - a guard written here today would walk one file and find nothing, which is
the permanently-green no-op this project has met three times.
"""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final
from urllib.parse import urljoin, urlsplit, urlunsplit

#: How many `Location:` hops `fetch.py` may follow before giving up. A cap is
#: not itself a security control - `assert_safe_redirect` re-checks every hop,
#: so hop five is judged exactly as hop one - it is what stops a redirect loop
#: from becoming an unbounded crawl.
MAX_REDIRECTS: Final = 5

#: The only two schemes a crawler has any business speaking. `file:`, `gopher:`,
#: `ftp:` and `data:` are refused by NOT BEING HERE rather than by being listed
#: somewhere as forbidden, which is the same allowlist discipline as the address
#: rule: a denylist only forbids what somebody thought of, and URL schemes are a
#: registry that grows.
ALLOWED_SCHEMES: Final = frozenset({"http", "https"})

#: The ports a merchant's website is served on. Restricting these is what stops
#: the crawler being used as a port-scanner-with-an-HTTP-parser against internal
#: services that happen to sit on globally routable addresses - Redis on 6379,
#: SMTP on 25 - which the address rule alone does not cover.
ALLOWED_PORTS: Final = frozenset({80, 443})

#: What each scheme means when the URL names no port.
DEFAULT_PORTS: Final = {"http": 80, "https": 443}

#: **NAMING ONLY. THESE ARE NOT WHAT BLOCKS THEM.** Every address here is
#: already refused by the rule in `_routability_problem` - 169.254.169.254 and
#: fd00:ec2::254 and 192.0.0.192 because they are not global, 100.100.100.200
#: because it is not global either (it has no other property set at all, which
#: is the case a denylist misses). This table exists so the refusal SAYS what
#: was being reached, because "your website redirects to the cloud metadata
#: service" is a materially different thing to read than "not globally
#: routable". `test_the_metadata_table_is_not_what_blocks_them` deletes this
#: table and checks each address is still refused, so the naming can never
#: quietly become the mechanism.
CLOUD_METADATA_ADDRESSES: Final = {
    "169.254.169.254": "the cloud instance metadata service (AWS, Azure, GCP, Oracle, "
                       "DigitalOcean and Hetzner all serve credentials here)",
    "fd00:ec2::254": "the AWS instance metadata service over IPv6",
    "100.100.100.200": "the Alibaba Cloud instance metadata service",
    "192.0.0.192": "the Oracle Cloud legacy instance metadata service",
}

#: Why an address was refused, for the message only - the DECISION is the
#: three-property conjunction in `_routability_problem` and nothing here. First
#: match wins, so the order is most-specific-first: 169.254.169.254 is both
#: link-local and private and "a link-local address" is the more useful half.
#:
#: Every description has to be true of EVERY address the property matches, not
#: of the usual one. "a link-local address, where the metadata service lives" is
#: false of `fe80::1`; "a private address" is a stretch for `192.0.2.1`, which
#: IANA calls documentation space and `ipaddress` calls private. Hence the
#: deliberately flat wording. The fallback is reached by real addresses -
#: `100.64.0.1` and `fec0::1` set none of these - so it is a sentence a merchant
#: can see and it has to be true on its own.
#:
#: **`is_site_local` IS IN THE DECISION AND DELIBERATELY NOT HERE.** Every
#: property in this table is read with a BARE `getattr` below, for an address of
#: either version, and `is_site_local` exists only on `IPv6Address` - so a row
#: for it would be an `AttributeError` on every IPv4 refusal, i.e. a crash on the
#: ordinary path in the code that words the refusal. Site-local addresses reach
#: the fallback instead, which is true of them.
_WHY_NOT_ROUTABLE: Final = (
    ("is_unspecified", "the unspecified address"),
    ("is_loopback", "a loopback address"),
    ("is_link_local", "a link-local address"),
    ("is_multicast", "a multicast address"),
    ("is_reserved", "in reserved address space"),
    ("is_private", "in private or special-purpose address space"),
)

#: How much of a URL an error message may quote. A `data:` URL can be megabytes
#: and every message here ends up in a log line and, through Task 27, in front
#: of a merchant.
_ECHO_LIMIT: Final = 120

#: One `socket.getaddrinfo` answer: `(family, type, proto, canonname, sockaddr)`,
#: where `sockaddr` is `(address, port)` for IPv4, `(address, port, flowinfo,
#: scope_id)` for IPv6 and - for the link-layer families typeshed also allows -
#: `(interface_index, packed_address)`. Only `sockaddr[0]` is read, and the third
#: shape puts an integer there, which `assert_safe_address` refuses as "not an IP
#: address". That is the right direction: an answer this module does not
#: understand is not an answer it connects to.
_SockAddr = tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes]
AddressInfo = tuple[int, int, int, str, _SockAddr]

#: **THE SEAM MUST BE `getaddrinfo`-SHAPED, NOT URL-SHAPED.** A test double that
#: takes a URL cannot be substituted for the real default, so the production
#: call shape would never be exercised by any test that used it - the plan's own
#: sketch had exactly that shape. Taking `(host, port)` means the fake and
#: `socket.getaddrinfo` are interchangeable, which is the only way the tests are
#: testing the thing that ships.
Resolver = Callable[[str, int], Sequence[AddressInfo]]


def _default_resolver() -> Resolver:
    """`socket.getaddrinfo`, looked up NOW rather than captured at import.

    **A DEFAULT ARGUMENT WRITTEN `resolver=socket.getaddrinfo` - which is what
    this task's plan specified - IS A DIRECT REFERENCE TO THE FUNCTION OBJECT,
    TAKEN WHEN THIS MODULE IS IMPORTED.** Rebinding `socket.getaddrinfo`
    afterwards does not touch it. That matters here for a reason beyond taste:
    `tests/network_ban.py` closes the network by replacing `socket.getaddrinfo`
    on the module, and a captured default would sail straight past it and make a
    real DNS query from a test suite that believes it cannot. Looking the name
    up at call time is what makes the ban - and any later monkeypatch, and any
    future resolver policy - actually apply. Pinned by
    `test_the_default_resolver_is_looked_up_at_call_time_not_captured_at_import`.
    """
    return socket.getaddrinfo


class BlockedAddress(Exception):
    """A URL the crawler refused to fetch.

    Raised for every refusal, whatever the reason - an unusable scheme,
    credentials in the URL, a port we do not speak, a host that does not
    resolve, or an address that is not on the public internet. One exception
    type because the caller's response to all of them is identical: do not
    fetch, and tell the merchant we could not read their site. The MESSAGE
    distinguishes them and is written to be true of the specific case rather
    than of the category.

    **`address` IS THE HALF THE MESSAGE MUST NOT CARRY, AND THAT IS THE WHOLE
    REASON THIS TYPE HAS AN ATTRIBUTE AT ALL.** The two readers of a refusal are
    not the same party. An operator reading a log needs the address that was
    refused; the person who typed the hostname chose the NAME and does not know
    what it resolves to inside our network - and if the message tells them, the
    onboarding form is an internal DNS and address enumeration oracle that needs
    no fetch at all. Submit `jenkins.corp.internal`, read `10.4.2.17` back out of
    the refusal, repeat. So the message says WHY (a loopback address, the cloud
    metadata service) and never WHICH, and the address rides here instead, for
    `fetch.py` to LOG and never to render. The module already redacted passwords
    from these messages and bounded their length; the resolved address had simply
    never been weighed on the same terms.

    `None` for the refusals that never reached an address - an unusable scheme,
    credentials, a port, an unparseable URL, a host that does not resolve - so a
    caller can log it unconditionally.
    """

    def __init__(self, message: str, *, address: str | None = None) -> None:
        super().__init__(message)
        self.address = address


@dataclass(frozen=True)
class SafeTarget:
    """A URL that has been checked, AND the addresses the connection must use.

    **`addresses` IS THE POINT OF THIS TYPE.** Returning it is what makes the
    check and the connection agree: a caller that connects to `host` re-runs
    DNS and gets whatever the attacker's second answer is, and a caller that
    connects to `addresses` gets what was actually judged. Task 27's `fetch.py`
    is required to connect to these, send `host` as the `Host:` header and the
    TLS server name so certificate verification still happens against the name
    the merchant gave, and call `assert_safe_address` on the address it ends up
    using.

    `host` is `urlsplit`'s `hostname`: lower-cased, and with the brackets
    stripped from an IPv6 literal, so re-assembling a URL from it means putting
    the brackets back.
    """

    url: str
    scheme: str
    host: str
    port: int
    addresses: tuple[str, ...]


def _safe_to_echo(url: str) -> str:
    """A URL fit to appear in an error message: no credentials, bounded length.

    `http://token@internal/` puts a secret in the URL, and an error message is
    the one place a secret is guaranteed to be written down - logs, an audit
    row, a merchant-facing string. The userinfo is replaced rather than the
    whole URL suppressed, because the rest of it is what makes the message
    useful.

    **AND IT MUST BE A STRING THAT CAN ACTUALLY BE WRITTEN DOWN.** A host
    carrying a lone surrogate - `alpha\\ud800.example` - produces a message that
    a UTF-8 log handler cannot encode, so the handler raises WHILE LOGGING the
    refusal; control characters (`\\x07`, `\\x08`) reach a terminal intact. Both
    are hard to reach through an HTTP form and neither is a way past the check,
    which is why this is the last thing this function does rather than the first:
    a URL that is not printable is shown escaped, and a printable one - an IDN
    among them - is left exactly as the merchant typed it.
    """
    try:
        parts = urlsplit(url)
        if parts.username is not None or parts.password is not None:
            host = parts.hostname or ""
            if ":" in host:
                host = f"[{host}]"
            try:
                port = parts.port
            except ValueError:
                port = None
            authority = f"***@{host}:{port}" if port is not None else f"***@{host}"
            url = urlunsplit((parts.scheme, authority, parts.path, parts.query, parts.fragment))
    except ValueError:
        pass
    if not url.isprintable():
        url = url.encode("unicode_escape").decode("ascii")
    return url if len(url) <= _ECHO_LIMIT else url[:_ECHO_LIMIT] + "..."


def _routability_problem(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str | None:
    """Why `ip` is not an address on the public internet, or `None` if it is.

    **THE DECISION IS THE FIRST STATEMENT AND NOTHING ELSE.** Four properties
    of `ipaddress`, all four load-bearing, no ranges written down anywhere:

      * `is_global` - the allowlist. False for loopback, RFC1918, link-local,
        unique-local, the unspecified address, documentation space, benchmarking
        space, carrier-grade NAT, 6to4, Teredo and IPv4-mapped forms of any of
        them (CPython delegates the mapped case to the embedded IPv4 address,
        which `test_an_ipv4_address_hidden_inside_an_ipv6_one_is_judged_by_the_
        ipv4_address` pins, because that delegation arrived during the 3.x
        series and this control depends on it);
      * `is_multicast` - `224.0.0.1` and `ff02::1` are `is_global` TRUE, so
        without this conjunct they would be allowed;
      * `is_reserved` - `64:ff9b::7f00:1` is `is_global` TRUE and is
        `127.0.0.1` behind the NAT64 well-known prefix;
      * `is_site_local` - `fec0::/10`, which `is_global` calls TRUE and
        `is_private` calls FALSE, because CPython follows RFC 4193 and site-local
        was deprecated by RFC 3879. Read through `getattr` with a default because
        only `IPv6Address` has it; see the module docstring for how it was found
        and why the same shape can recur.

    Everything after the first statement is wording. `test_every_conjunct_in_
    the_routability_rule_is_load_bearing` proves each of the four by finding an
    address that only it refuses.
    """
    if (
        ip.is_global
        and not ip.is_multicast
        and not ip.is_reserved
        and not getattr(ip, "is_site_local", False)
    ):
        return None
    for attribute, description in _WHY_NOT_ROUTABLE:
        if getattr(ip, attribute):
            return description
    return "not a globally routable address"


def assert_safe_address(address: str, *, url: str = "") -> None:
    """Refuse an address that is not on the public internet.

    **THIS IS THE GATE THE CONNECTION ITSELF GOES THROUGH**, and it is the same
    function `assert_safe_url` applies to every address it resolves. Task 27's
    transport calls it with the address it is about to hand to `connect()`, so
    the last thing checked is the thing actually used - the only arrangement in
    which a check and a connection cannot disagree.

    `url` is optional and only makes the message say which URL led here.

    **NEITHER MESSAGE NAMES THE ADDRESS.** It goes on `BlockedAddress.address`
    instead; see that class for why the log and the merchant are different
    audiences. The metadata SERVICE is still named, because "your site redirects
    to the cloud metadata service" is actionable and discloses nothing the party
    who chose the hostname did not already choose.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError as unparseable:
        raise BlockedAddress(
            f"{_safe_to_echo(url) + ' resolved to ' if url else ''}something that is not an "
            f"IP address, so the crawler cannot judge whether it is safe to connect to it, "
            f"so it will not connect to it.",
            address=address,
        ) from unparseable

    problem = _routability_problem(ip)
    if problem is None:
        return

    named = CLOUD_METADATA_ADDRESSES.get(str(ip))
    leads_to = f"{_safe_to_echo(url)} leads to " if url else "the crawler was asked to connect to "
    because = f" - {named}" if named else ""
    raise BlockedAddress(
        f"{leads_to}an address that is {problem}{because}. The crawler only fetches "
        f"addresses on the public internet.",
        address=address,
    )


def assert_safe_url(url: str, *, resolver: Resolver | None = None) -> SafeTarget:
    """Check a URL and return the addresses a connection to it may use.

    Refuses, in this order: anything `urlsplit` cannot parse; any scheme outside
    `ALLOWED_SCHEMES`; a URL carrying credentials; a port outside
    `ALLOWED_PORTS`; a URL naming no host; a host that does not resolve, that the
    resolver cannot even look up, or that resolves to nothing; and any resolved
    address `assert_safe_address` refuses. **Every one of those comes back as
    `BlockedAddress` and nothing else** - see the `except ValueError` branch
    below for the one that did not, and why no fake resolver could find it.

    **EVERY address is checked, and one bad one refuses the URL.** A host that
    resolves to a public address and a private one is a host under someone's
    control who is trying something, and picking the good address out of the
    answer would leave the caller free to try the other one.

    The resolver is called exactly ONCE, and the addresses it returned are what
    comes back in `SafeTarget.addresses`. Resolving again - here or in the HTTP
    client - is the rebinding window; see the module docstring.

    `resolver=None` means `socket.getaddrinfo`, looked up when this runs; see
    `_default_resolver` for why it is not a captured default argument.
    """
    resolve = _default_resolver() if resolver is None else resolver
    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        host = parts.hostname
        port_in_url = parts.port
        has_credentials = parts.username is not None or parts.password is not None
    except ValueError as unparseable:
        raise BlockedAddress(
            f"{_safe_to_echo(url)} is not a URL the crawler can parse: {unparseable}"
        ) from unparseable

    if scheme not in ALLOWED_SCHEMES:
        named = repr(scheme) if scheme else "missing"
        raise BlockedAddress(
            f"{_safe_to_echo(url)} has the scheme {named}; the crawler fetches "
            f"{' and '.join(sorted(ALLOWED_SCHEMES))} URLs and nothing else."
        )

    if has_credentials:
        raise BlockedAddress(
            f"{_safe_to_echo(url)} carries credentials in the URL. The crawler never "
            f"authenticates, and a name before the @ is a common way to make a URL look "
            f"like it points somewhere it does not."
        )

    if not host:
        raise BlockedAddress(f"{_safe_to_echo(url)} names no host to fetch from.")

    port = DEFAULT_PORTS[scheme] if port_in_url is None else port_in_url
    if port not in ALLOWED_PORTS:
        raise BlockedAddress(
            f"{_safe_to_echo(url)} is on port {port}. The crawler connects on "
            f"{' and '.join(str(allowed) for allowed in sorted(ALLOWED_PORTS))} only."
        )

    try:
        answers = resolve(host, port)
    except OSError as unresolved:
        raise BlockedAddress(
            f"{_safe_to_echo(url)} could not be resolved: {unresolved}"
        ) from unresolved
    except ValueError as unusable:
        # **THE RESOLVER SEAM DOES NOT RAISE `OSError` ALONE.**
        # `socket.getaddrinfo` IDNA-encodes a `str` host BEFORE it does any I/O,
        # and the `idna` codec raises `UnicodeError` - which is a `ValueError`
        # and is NOT an `OSError` - for a DNS label longer than 63 characters.
        # `http://<64 a's>.example/` is a string a merchant can type into the
        # onboarding form, and with `except OSError` alone it came out of here
        # as a bare `UnicodeError`, straight past a caller catching
        # `BlockedAddress`. Fail-closed, but as a crash rather than a refusal.
        # Found by running this function against the REAL resolver, because the
        # only resolver the tests have raises `socket.gaierror` and nothing else.
        raise BlockedAddress(
            f"{_safe_to_echo(url)} names a host the resolver cannot look up: {unusable}"
        ) from unusable

    try:
        addresses = tuple(dict.fromkeys(str(answer[4][0]) for answer in answers))
    except (LookupError, TypeError) as unreadable:
        # **AN ANSWER THIS MODULE CANNOT READ IS NOT AN ANSWER IT CONNECTS TO.**
        # `_SockAddr` above says an unrecognised sockaddr is refused as "not an
        # IP address", and that was true only of the shapes that are still
        # SUBSCRIPTABLE: `answers[4][0]` also assumes a 5-tuple whose fifth
        # element can be indexed, and an empty sockaddr `()` or a 4-wide answer
        # was an `IndexError` straight past a caller catching `BlockedAddress`,
        # while `None` in place of an answer or of the sockaddr, and an integer
        # sockaddr, were `TypeError`. `socket.getaddrinfo` produces none of them,
        # which is why this stayed open - but Task 27 injects a resolver of its
        # own, at which point this seam has a producer that is not the stdlib.
        #
        # Re-review N2: this caught `IndexError` and was therefore itself a
        # denylist of the failures somebody thought of - a dict-shaped ANSWER
        # escapes as `KeyError: 4` and a dict-shaped SOCKADDR as `KeyError: 0`
        # (index 4 succeeds; `sockaddr[0]` is what fails), which is the same
        # class of defect this guard exists to close. Both are `LookupError`,
        # which is the base of all three, so the guard now
        # names the category rather than two of its members.
        raise BlockedAddress(
            f"{_safe_to_echo(url)} resolved to an answer the crawler cannot read "
            f"({type(unreadable).__name__}: {unreadable})."
        ) from unreadable
    if not addresses:
        raise BlockedAddress(f"{_safe_to_echo(url)} resolved to no addresses at all.")

    for address in addresses:
        assert_safe_address(address, url=url)

    return SafeTarget(url=url, scheme=scheme, host=host, port=port, addresses=addresses)


def assert_safe_redirect(
    current_url: str, location: str, *, resolver: Resolver | None = None
) -> SafeTarget:
    """Check one `Location:` hop, resolved against the URL that produced it.

    **A REDIRECT IS A URL AN ATTACKER CHOSE, AND SO IS THE ONE AFTER IT.** The
    first URL a merchant gives is the one that gets scrutinised by a human; the
    third hop is not. A public site answering `302 Location: http://127.0.0.1/`
    - or `Location: //169.254.169.254/` , which inherits the scheme and looks
    like a path - is the ordinary way past a check that only ran once, so this
    runs the WHOLE of `assert_safe_url` again on the joined URL rather than
    comparing it to the previous host.

    Joining is `urljoin`, so a relative `Location` resolves against
    `current_url` and an absolute one replaces it entirely - including a scheme
    change to `file:` or `gopher:`, which then meets the scheme check like any
    other URL.
    """
    if not location.strip():
        raise BlockedAddress(
            f"{_safe_to_echo(current_url)} redirected with an empty Location header."
        )
    return assert_safe_url(urljoin(current_url, location), resolver=resolver)
