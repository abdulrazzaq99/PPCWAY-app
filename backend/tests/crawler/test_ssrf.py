"""The SSRF boundary, attacked rather than exercised.

**READ `src/ppcway/crawler/ssrf.py`'s DOCSTRING FIRST.** The one property this
module exists to hold is that THE ADDRESS THAT WAS CHECKED IS THE ADDRESS THAT
IS CONNECTED TO, and most of what follows is either an attack on that property
or a pin on the machinery that keeps it true.

**WHY THIS FILE IS STRUCTURAL AS WELL AS BEHAVIOURAL**, which is unusual and is
the point. Two mutations of `ssrf.py` produce IDENTICAL BEHAVIOUR today and are
invisible to every test that merely calls it:

  * replacing the derived rule with a hand-written list of CIDR ranges that
    happens to be equal for the addresses any test names - the hand-maintained
    list failure, seven occurrences on this project, and the SSRF variety of it
    is how real defences ship with `100.64.0.0/10` missing;
  * replacing a judgement (`ALLOWED_PORTS`) with a derivation over another table
    (`frozenset(DEFAULT_PORTS.values())`) that is EQUAL TODAY - the mirror
    failure, where a literal that records a decision quietly becomes a
    re-derivation and stops recording anything.

Both are caught here by reading `ssrf.py`'s AST, because nothing behavioural can
see either one. `test_the_module_writes_down_no_address_ranges` and
`test_the_routability_decision_reads_exactly_three_properties` are the first;
the `_binding` assertions are the second.
"""
import ast
import dataclasses
import inspect
import ipaddress
import os
import pathlib
import socket
import subprocess
import sys

import pytest

from ppcway.crawler import ssrf
from ppcway.crawler.ssrf import (
    ALLOWED_PORTS,
    ALLOWED_SCHEMES,
    CLOUD_METADATA_ADDRESSES,
    DEFAULT_PORTS,
    MAX_REDIRECTS,
    BlockedAddress,
    SafeTarget,
    assert_safe_address,
    assert_safe_redirect,
    assert_safe_url,
)
from tests.network_ban import NETWORK_BAN

SSRF_PATH = pathlib.Path(ssrf.__file__).resolve()
SSRF_TREE = ast.parse(SSRF_PATH.read_text())

# The ban has to be in force ALREADY, here, while this module is being imported -
# import happens at COLLECTION, before any fixture of any scope runs, and this
# package's conftest arms it there through `pytest_make_collect_report`.
# Recorded rather than asserted at module scope so that a failure is a named
# test rather than a collection error nobody can read. Same shape as
# `tests/llm/test_anthropic_provider.py`, and for the same reason: measured,
# deleting this package's collection hook changed NOTHING in the suite until
# these two tests existed.
#
# **IT PROBES `socket.socket()`, NOT `getaddrinfo`, AND THAT IS DELIBERATE.**
# Constructing a socket touches no network at all, so this probe is inert when
# the ban is absent; resolving a name is a real DNS query, and a probe that
# egresses on failure is a probe that punishes the suite for the bug it is
# looking for. `_arm()` closes every door in one go, so any one door proves the
# window is armed - and that `getaddrinfo` specifically is closed is what
# `test_calling_without_a_resolver_reaches_the_socket_ban_rather_than_the_network`
# says, from inside a test.
try:
    _AT_IMPORT_TIME = socket.socket()
    _AT_IMPORT_TIME.close()
    _AT_IMPORT_TIME = "a socket was opened at import time"
except RuntimeError as refused:
    _AT_IMPORT_TIME = str(refused)

#: A host name with no meaning to anything - every test that needs a name says
#: this one, so a fake resolver's mapping is the only thing that decides what it
#: resolves to, and no test can accidentally depend on a real record.
HOST = "alphaplumbing.example"
URL = f"https://{HOST}/"


# --------------------------------------------------------------------------
# The address table. Every entry is a literal and the length is asserted.
# --------------------------------------------------------------------------
#
# Written out rather than generated, because this is the JUDGEMENT half: which
# addresses a crawler must refuse is a security decision, and a decision
# re-derived from the code under test records nothing. The length assertions
# below are what stops the table silently shrinking - a parametrisation that
# collects one case reads exactly like one that collects forty-three.

BLOCKED_ADDRESSES = (
    # Loopback, in four spellings. The last two are the same address wearing an
    # IPv6 costume; `::ffff:7f00:1` is the compressed hexadecimal form.
    "127.0.0.1",
    "127.1.2.3",
    "::1",
    "::ffff:127.0.0.1",
    # The unspecified address. `connect()` to it goes to this host.
    "0.0.0.0",
    "::",
    # RFC1918, at the edges of two of the three ranges.
    "10.0.0.5",
    "172.16.4.4",
    "172.31.255.255",
    "192.168.1.1",
    "::ffff:10.0.0.5",
    # Link-local, which is where four of the five cloud metadata services live.
    "169.254.169.254",
    "169.254.1.1",
    "fe80::1",
    "::ffff:169.254.169.254",
    # **THE TWO A DENYLIST MISSES.** Carrier-grade NAT: `is_private` is FALSE
    # for both of these and so is every other named property. The second is
    # Alibaba Cloud's metadata service. Only `is_global` refuses them.
    "100.64.0.1",
    "100.100.100.200",
    # IETF protocol assignments, documentation and benchmarking space.
    "192.0.0.192",  # Oracle Cloud's legacy metadata service
    "192.0.0.170",
    "192.0.2.1",
    "198.18.0.1",
    "198.51.100.7",
    "203.0.113.9",
    # Multicast: `is_global` is TRUE for these, so `is_multicast` is the only
    # thing refusing them.
    "224.0.0.1",
    "239.255.255.250",
    "ff02::1",
    # Reserved.
    "240.0.0.1",
    "255.255.255.255",
    "100::1",
    # `is_global` is TRUE for this one - it is the NAT64 well-known prefix with
    # 127.0.0.1 inside it, and `is_reserved` is the only thing refusing it.
    "64:ff9b::7f00:1",
    # IPv6 private space: unique-local, AWS's IPv6 metadata service,
    # documentation space, 6to4 and Teredo wrapped round a loopback address.
    "fd00::1",
    "fc00::1",
    "fd00:ec2::254",
    "2001:db8::1",
    "2002:7f00:1::",
    "2001:0:0:0:0:0:7f00:1",
    # **THE IPv6 MIRROR OF THE TWO ABOVE, AND THE ONE THIS TABLE MISSED.**
    # `fec0::/10` is site-local unicast, deprecated by RFC 3879 - so CPython
    # follows RFC 4193 and leaves it OUT of `is_private`, and `is_global` is
    # TRUE for it. Exactly the `100.64.0.0/10` shape: no named property set, an
    # address the rule admitted, and a table that named `fc00::1`, `fd00::1` and
    # `fe80::1` and stopped one prefix short. Only `is_site_local` refuses them.
    # Both ends of the range, because a rule reading `fec0::/16` would pass on
    # the first alone.
    "fec0::1",
    "feff::1",
)

ALLOWED_ADDRESSES = (
    "93.184.216.34",
    "8.8.8.8",
    "1.1.1.1",
    # 6to4 relay anycast. `ipaddress` calls it global and it is - deprecated,
    # but routable - so it is allowed, and it is in this table so that the fact
    # is written down rather than discovered.
    "192.88.99.1",
    "2606:4700:4700::1111",
    "2a00:1450:4001:80f::200e",
    "::ffff:93.184.216.34",
)


def test_the_address_table_is_the_size_it_looks() -> None:
    """A parametrisation that silently collects fewer cases than intended reads
    green. Both halves are pinned, and the two must not overlap."""
    assert len(BLOCKED_ADDRESSES) == 38
    assert len(ALLOWED_ADDRESSES) == 7
    assert len(set(BLOCKED_ADDRESSES)) == len(BLOCKED_ADDRESSES)
    assert len(set(ALLOWED_ADDRESSES)) == len(ALLOWED_ADDRESSES)
    assert not set(BLOCKED_ADDRESSES) & set(ALLOWED_ADDRESSES)
    assert all(ipaddress.ip_address(a) for a in BLOCKED_ADDRESSES + ALLOWED_ADDRESSES)


# --------------------------------------------------------------------------
# The rule is DERIVED, and that is proved structurally
# --------------------------------------------------------------------------


def _docstring_nodes(tree: ast.AST) -> set[int]:
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            found.add(id(body[0].value))
    return found


def _string_literals(tree: ast.AST) -> list[str]:
    """Every string constant in a module that is not a docstring.

    Docstrings are excluded because `ssrf.py`'s own prose names `10.0.0.0/8` and
    `169.254.169.254` while explaining why it does not use them, and a check
    that could not tell prose from code would force the explanation out of the
    file. Comments are not AST nodes at all, so they need no exclusion.
    """
    skip = _docstring_nodes(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip
    ]


def _addressish(text: str) -> bool:
    for parse in (ipaddress.ip_address, lambda t: ipaddress.ip_network(t, strict=False)):
        try:
            parse(text)
        except ValueError:
            continue
        return True
    return False


def test_the_module_writes_down_no_address_ranges() -> None:
    """**THE ANTI-HAND-LIST PIN, AND THE ONE MUTATION NOTHING BEHAVIOURAL SEES.**

    Replacing `_routability_problem`'s four-property rule with a list of CIDRs
    that is equal for every address any test names changes NO behaviour and
    fails no BEHAVIOURAL test at all. It is caught here - and, measured, also by
    `test_the_routability_decision_reads_exactly_four_properties`, because
    replacing the rule also removes the property reads. Two structural tests,
    nothing behavioural: an earlier report said "here, and only here", which was
    the right substance and the wrong count.

    The assertion is an equality against the metadata table rather than "no
    addresses at all", because there ARE address literals in `ssrf.py` - the
    four keys of `CLOUD_METADATA_ADDRESSES` - and they are allowed to be there
    for one reason: they only NAME what a refusal is, and
    `test_the_metadata_table_is_not_what_blocks_them` proves the refusal happens
    without them.
    """
    literals = {text for text in _string_literals(SSRF_TREE) if _addressish(text)}
    assert literals == set(CLOUD_METADATA_ADDRESSES), (
        f"ssrf.py writes down addresses that are not part of the metadata NAMING table: "
        f"{sorted(literals - set(CLOUD_METADATA_ADDRESSES))}. The blocked set is derived "
        f"from `ipaddress`; a range written down here is a hand-maintained list, which is "
        f"the defect this project has shipped seven times and the one every published SSRF "
        f"bypass turns on."
    )
    assert literals, "the detector found nothing at all, so it is proving nothing"


def test_the_address_literal_detector_would_catch_a_hand_written_range(tmp_path) -> None:
    """The guard above passes today. This is the half that proves it passes
    because there are no ranges, rather than because the walk finds nothing -
    the permanently-green no-op this project has met three times."""
    offender = tmp_path / "offender.py"
    offender.write_text(
        '"""A docstring mentioning 10.0.0.0/8, which must NOT be flagged."""\n'
        "BLOCKED = ['10.0.0.0/8', '192.168.0.0/16', '127.0.0.1']\n"
        "MESSAGE = 'not a routable address'\n"
    )
    found = {t for t in _string_literals(ast.parse(offender.read_text())) if _addressish(t)}
    assert found == {"10.0.0.0/8", "192.168.0.0/16", "127.0.0.1"}

    clean = tmp_path / "clean.py"
    clean.write_text('"""Mentions 169.254.169.254 in prose only."""\nX = 1\n')
    assert {t for t in _string_literals(ast.parse(clean.read_text())) if _addressish(t)} == set()


def _function(name: str) -> ast.FunctionDef:
    for node in ast.walk(SSRF_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"ssrf.py declares no function called {name}")


def _properties_the_decision_reads(function: ast.FunctionDef) -> set[str]:
    """Every property of the argument read INSIDE THE DECISION'S OWN `if` TEST.

    **SCOPED TO THE TEST EXPRESSION, NOT TO THE FUNCTION BODY, AND THAT IS THE
    DIFFERENCE BETWEEN A PIN AND A DECORATION.** A review evaded the previous
    version by re-implementing the rule as integer bounds in a helper and leaving
    `_judged = (ip.is_global, ip.is_multicast, ip.is_reserved)` behind as a
    decorative read: it writes down no address strings, so the literal detector
    is blind to it, and it MENTIONS the three names, so a walk over the whole
    body was satisfied - and it survived all 2768 tests. Reading only the
    expression the `if` actually decides on is what closes that, because a
    mention somewhere else in the body is not a use.

    Both spellings count, because the module uses both: a plain attribute, and
    `getattr(ip, "name", default)` - which `is_site_local` needs, since
    `IPv4Address` does not have it. The message loop's `getattr(ip, attribute)`
    reads a VARIABLE and is outside the `if` besides, so it contributes nothing
    either way.
    """
    argument = function.args.args[0].arg
    decisions = [node for node in function.body if isinstance(node, ast.If)]
    assert decisions, (
        f"{function.name} no longer reaches its verdict through an `if`, so this pin cannot "
        f"see the decision at all. Do not delete this test to make that go away - work out "
        f"what the function now decides on and pin THAT."
    )
    read = set()
    for node in ast.walk(decisions[0].test):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == argument
        ):
            read.add(node.attr)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == argument
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            read.add(node.args[1].value)
    return read


def test_the_routability_decision_reads_exactly_four_properties() -> None:
    """**WHICH `ipaddress` PROPERTIES THE CONTROL RESTS ON, PINNED MECHANICALLY.**

    The report claims the blocked set is derived from `is_global`,
    `is_multicast`, `is_reserved` and `is_site_local`. This is that claim as an
    assertion rather than as prose: every property `_routability_problem` reads
    off its argument to decide, and the set has to be exactly those four.

    It catches what the literal detector cannot - a re-implementation in integer
    arithmetic (`int(ip) >> 24 == 10`) writes down no address strings at all but
    reads no properties either - and it catches a rule quietly widened to admit
    something by dropping a conjunct. It was three properties until a review
    swept the IANA registry and found `fec0::/10` admitted; the count is here in
    the NAME so that adding a property to the rule and forgetting this test is a
    failure rather than a silent widening.

    **IT HAS A KNOWN FALSE POSITIVE AND THE FIX IS NOT TO DELETE IT.** Moving the
    conjunction into a named helper - `def _is_publicly_routable(ip): ...`, a
    behaviour-identical refactor - fails this test with a message about what
    `_routability_problem` decides on, which points at the wrong thing. That is
    inherent to a syntactic pin. If you are that person: move this pin to the
    helper, do not remove it. It is the only thing standing between this module
    and a hand-maintained list of ranges written in integer arithmetic.
    """
    read = _properties_the_decision_reads(_function("_routability_problem"))
    # Re-review N1: the equality alone is not enough. If someone replaces the
    # expected side with a re-derivation from the code under test, both sides
    # collapse to the same value and the assertion becomes `set() == set()` -
    # green, and blind to a rule rewritten as a hand-maintained list of integer
    # ranges (the literal detector above sees strings, not integers). Neither
    # mutation is dangerous alone; together they ship a hand-written CIDR list
    # inside the one pin protecting the blocked set. This line does not stop
    # anyone writing `x == x`; it stops `x == x` from disabling the guard.
    assert len(read) == 4, (
        f"the decision reads {len(read)} properties, not 4. If this fired alongside the "
        f"equality below passing, the expected side is no longer a literal - see N1."
    )
    assert read == {"is_global", "is_multicast", "is_reserved", "is_site_local"}, (
        f"_routability_problem now decides on {sorted(read)}. Those four properties are the "
        f"whole of the rule; the others appear only through getattr in the message loop, "
        f"which is why they are not here."
    )


def test_the_property_pin_reads_the_decision_and_not_a_mention_elsewhere(tmp_path) -> None:
    """The pin above passes today. This is the half that proves it passes because
    the rule reads those four properties, rather than because the four names
    happen to appear somewhere in the function - which is exactly how a review
    evaded the previous version, and is the permanently-green no-op this project
    has met three times.

    Three modules, all with the same four names present in the body: the shipped
    shape, the decorative-read evasion, and the getattr spelling.
    """

    def properties(source: str) -> set[str]:
        module = ast.parse(source)
        function = next(n for n in ast.walk(module) if isinstance(n, ast.FunctionDef))
        return _properties_the_decision_reads(function)

    assert properties(
        "def f(ip):\n"
        "    if ip.is_global and not ip.is_multicast and not ip.is_reserved"
        " and not getattr(ip, 'is_site_local', False):\n"
        "        return None\n"
        "    return 'no'\n"
    ) == {"is_global", "is_multicast", "is_reserved", "is_site_local"}

    # The evasion: a hand-written range check, with the property reads left in
    # place as decoration. The decision reads NOTHING off the argument.
    assert properties(
        "def f(ip):\n"
        "    _judged = (ip.is_global, ip.is_multicast, ip.is_reserved, ip.is_site_local)\n"
        "    if not _blocked_by_integer_bounds(int(ip)):\n"
        "        return None\n"
        "    return 'no'\n"
    ) == set()

    # And a decision reached without an `if` at all fails loudly rather than
    # reporting an empty set that looks like the evasion above.
    with pytest.raises(AssertionError, match="no longer reaches its verdict"):
        properties("def f(ip):\n    return None if ip.is_global else 'no'\n")


def test_every_conjunct_in_the_routability_rule_is_load_bearing() -> None:
    """Each of the four refuses something the other three allow - so none is
    decoration, and dropping any one of them opens a real route.

    The witnesses are the whole argument for the rule's SHAPE: a check written
    as `is_private or is_loopback or is_link_local` - which is what this task's
    plan specified - allows three of these four.
    """
    private = ipaddress.ip_address("10.0.0.5")
    assert not private.is_multicast and not private.is_reserved
    assert ssrf._routability_problem(private) is not None, "is_global is the only refuser here"

    multicast = ipaddress.ip_address("224.0.0.1")
    assert multicast.is_global and not multicast.is_reserved
    assert ssrf._routability_problem(multicast) is not None, "is_multicast is the only refuser"

    nat64 = ipaddress.ip_address("64:ff9b::7f00:1")
    assert nat64.is_global and not nat64.is_multicast
    assert ssrf._routability_problem(nat64) is not None, "is_reserved is the only refuser"

    # **THE ONE THE FIRST THREE ADMITTED.** `is_global` is TRUE for site-local
    # space and `is_private` is FALSE, because CPython follows RFC 4193 and
    # RFC 3879 deprecated `fec0::/10` - so the only property that refuses it is
    # the one `ipaddress` keeps separately.
    site_local = ipaddress.ip_address("fec0::1")
    assert site_local.is_global and not site_local.is_multicast and not site_local.is_reserved
    assert not site_local.is_private and not site_local.is_link_local
    assert site_local.is_site_local, "the stdlib property this conjunct rests on"
    assert ssrf._routability_problem(site_local) is not None, "is_site_local is the only refuser"

    # And the property is IPv6-only, which is why the rule reads it through
    # `getattr` with a default: an attribute access would be an `AttributeError`
    # on every IPv4 address, i.e. a crash on the ordinary path.
    assert not hasattr(ipaddress.ip_address("10.0.0.5"), "is_site_local")


def test_the_denylist_of_properties_the_plan_specified_admits_seven_of_these() -> None:
    """**THE MEASURED CASE FOR THE ALLOWLIST FORM**, rather than the argued one.

    The plan asked for "private, loopback, link-local, reserved or unspecified",
    which is the shape almost every hand-written SSRF check has. Run it over the
    table and it admits seven addresses, in three classes:

      * carrier-grade NAT space, `100.64.0.0/10`, where NO named property is
        set - and `100.100.100.200` inside it is Alibaba Cloud's instance
        metadata service, an endpoint that hands credentials to anything that
        asks it;
      * multicast, which nobody thinks to list because it is not "private";
      * IPv6 site-local, `fec0::/10`, which is not private EITHER - CPython
        excludes it from `is_private` because RFC 3879 deprecated it - and which
        this module itself admitted until a review swept the IANA registry.

    All seven are refused by this module, and this test is the executed proof
    that the difference between the two rules is real rather than stylistic.
    """

    def the_plans_rule(ip):
        return not (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
            or ip.is_unspecified
        )

    admitted = sorted(
        address
        for address in BLOCKED_ADDRESSES
        if the_plans_rule(ipaddress.ip_address(address))
    )
    assert admitted == [
        "100.100.100.200", "100.64.0.1", "224.0.0.1", "239.255.255.250",
        "fec0::1", "feff::1", "ff02::1",
    ]
    for address in admitted:
        assert ssrf._routability_problem(ipaddress.ip_address(address)) is not None


def test_an_ipv4_address_hidden_inside_an_ipv6_one_is_judged_by_the_ipv4_address() -> None:
    """**A STDLIB BEHAVIOUR THIS CONTROL DEPENDS ON, EXECUTED RATHER THAN
    ASSUMED.** CPython delegates `is_private`/`is_global` on an IPv4-mapped IPv6
    address to the embedded IPv4 address, and that delegation arrived DURING the
    3.x series. On a Python without it, `::ffff:127.0.0.1` would be judged as an
    ordinary IPv6 address and allowed. This fails loudly if that ever regresses,
    which is the only way a dependency on someone else's version-dependent
    behaviour can be safe.

    6to4 and Teredo are covered differently - `2002::/16` and `2001::/32` are
    non-global as whole prefixes - so both spellings of "an IPv4 address inside
    an IPv6 one" are pinned here.
    """
    for hidden in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "100.100.100.200"):
        mapped = ipaddress.ip_address(f"::ffff:{hidden}")
        assert mapped.ipv4_mapped == ipaddress.ip_address(hidden)
        assert ssrf._routability_problem(mapped) is not None, hidden

    public = ipaddress.ip_address("::ffff:93.184.216.34")
    assert public.ipv4_mapped == ipaddress.ip_address("93.184.216.34")
    assert ssrf._routability_problem(public) is None, "the mapped form of a public address"

    assert ipaddress.ip_address("2002:7f00:1::").sixtofour == ipaddress.ip_address("127.0.0.1")
    assert ssrf._routability_problem(ipaddress.ip_address("2002:7f00:1::")) is not None


# Where each blocked range stops. Written as (last blocked, first allowed) pairs
# of LITERALS, because the geometry of the blocked set is the thing a reader
# most wants to be able to check by eye and the thing a rewritten rule is most
# likely to get subtly wrong. A rule that blocked `10.0.0.0/7` instead of
# `10.0.0.0/8` passes every other test in this file.
BLOCKED_RANGE_EDGES = (
    ("10.255.255.255", "11.0.0.0"),
    ("100.127.255.255", "100.128.0.0"),
    ("127.255.255.255", "128.0.0.0"),
    ("169.254.255.255", "169.255.0.0"),
    ("172.31.255.255", "172.32.0.0"),
    ("192.168.255.255", "192.169.0.0"),
)


@pytest.mark.parametrize("last_blocked,first_allowed", BLOCKED_RANGE_EDGES)
def test_each_blocked_range_ends_where_it_should(last_blocked, first_allowed) -> None:
    assert ssrf._routability_problem(ipaddress.ip_address(last_blocked)) is not None
    assert ssrf._routability_problem(ipaddress.ip_address(first_allowed)) is None


def test_the_range_edge_table_is_the_size_it_looks() -> None:
    assert len(BLOCKED_RANGE_EDGES) == 6


# --------------------------------------------------------------------------
# The judgements are LITERALS, and that is proved structurally too
# --------------------------------------------------------------------------


def _binding(name: str) -> ast.expr:
    """The right-hand side of a module-level assignment, as AST."""
    for node in SSRF_TREE.body:
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
    raise AssertionError(f"ssrf.py binds no module-level name {name}")


def test_the_allowed_schemes_are_a_literal_and_are_http_and_https() -> None:
    """CONTENTS and SHAPE. The value is pinned because adding `ftp` must come
    through a diff; the SHAPE is pinned because a set replaced by a
    comprehension over something else is invisible to every value comparison -
    the mirror of the hand-list failure, and this project has now shipped it."""
    assert ALLOWED_SCHEMES == frozenset({"http", "https"})
    binding = _binding("ALLOWED_SCHEMES")
    assert isinstance(binding, ast.Call) and binding.func.id == "frozenset"
    assert isinstance(binding.args[0], ast.Set), "a literal set, not a comprehension"
    assert all(isinstance(element, ast.Constant) for element in binding.args[0].elts)


def test_the_allowed_ports_are_a_literal_and_are_eighty_and_four_four_three() -> None:
    """**THE EQUAL-TODAY MUTATION THIS EXISTS FOR:** `frozenset(DEFAULT_PORTS.
    values())` is `{80, 443}`, so swapping the judgement for a derivation over
    the neighbouring table passes every value assertion in this file. Which
    ports a crawler will connect on is a security decision, not a restatement of
    what a scheme's default port is; only the AST can tell the two apart."""
    assert ALLOWED_PORTS == frozenset({80, 443})
    assert ALLOWED_PORTS == frozenset(DEFAULT_PORTS.values()), (
        "they coincide today, which is exactly why the shape assertion below is needed"
    )
    binding = _binding("ALLOWED_PORTS")
    assert isinstance(binding, ast.Call) and binding.func.id == "frozenset"
    assert isinstance(binding.args[0], ast.Set), "a literal set, not a comprehension"
    assert all(isinstance(element, ast.Constant) for element in binding.args[0].elts)


def test_the_default_ports_are_a_literal_and_cover_every_allowed_scheme() -> None:
    assert DEFAULT_PORTS == {"http": 80, "https": 443}
    assert set(DEFAULT_PORTS) == ALLOWED_SCHEMES, (
        "assert_safe_url indexes DEFAULT_PORTS by scheme after the scheme check, so a "
        "scheme allowed without a default port here is a KeyError on an ordinary URL"
    )
    assert isinstance(_binding("DEFAULT_PORTS"), ast.Dict)


def test_the_metadata_table_is_a_literal_and_names_the_four_endpoints() -> None:
    assert set(CLOUD_METADATA_ADDRESSES) == {
        "169.254.169.254", "fd00:ec2::254", "100.100.100.200", "192.0.0.192",
    }
    assert isinstance(_binding("CLOUD_METADATA_ADDRESSES"), ast.Dict)


def test_the_reason_table_is_a_literal_and_names_real_ipaddress_properties() -> None:
    """A typo in a property name here is an `AttributeError` in production, on
    the refusal path, where it would turn a clean block into a crash."""
    assert isinstance(_binding("_WHY_NOT_ROUTABLE"), ast.Tuple)
    assert len(ssrf._WHY_NOT_ROUTABLE) == 6
    assert [attribute for attribute, _ in ssrf._WHY_NOT_ROUTABLE] == [
        "is_unspecified",
        "is_loopback",
        "is_link_local",
        "is_multicast",
        "is_reserved",
        "is_private",
    ], (
        "FIRST MATCH WINS, so this ORDER is the message's specificity and is a judgement, "
        "not an accident. `is_private` is true of loopback, link-local and reserved space "
        "as well, so moving it up quietly turns every one of those messages into the "
        "vaguest true thing that can be said - measured, moving it above is_link_local "
        "degrades all four link-local refusals, the metadata endpoints included, and "
        "survived the whole suite before this assertion existed."
    )
    for version in ("1.1.1.1", "::1"):
        sample = ipaddress.ip_address(version)
        for attribute, description in ssrf._WHY_NOT_ROUTABLE:
            assert hasattr(sample, attribute), (
                f"{attribute} does not exist on {version}. Every property here is read with a "
                f"BARE getattr on the refusal path, for an address of either version, so an "
                f"IPv6-only property in this table is an AttributeError on every IPv4 "
                f"refusal. `is_site_local` is exactly that, which is why the fourth conjunct "
                f"of the DECISION words its refusals through the fallback instead of adding a "
                f"row here."
            )
            assert isinstance(getattr(sample, attribute), bool), attribute
            assert description == description.strip() and description


def test_the_redirect_cap_is_five() -> None:
    assert MAX_REDIRECTS == 5
    assert isinstance(_binding("MAX_REDIRECTS"), ast.Constant)


# --------------------------------------------------------------------------
# Blocking, through both entry points
# --------------------------------------------------------------------------


@pytest.mark.parametrize("address", BLOCKED_ADDRESSES)
def test_a_blocked_address_is_refused_at_the_connection(address) -> None:
    with pytest.raises(BlockedAddress):
        assert_safe_address(address)


@pytest.mark.parametrize("address", BLOCKED_ADDRESSES)
def test_a_host_resolving_to_a_blocked_address_is_refused(address, fake_resolver) -> None:
    """DNS rebinding in its simplest form: the NAME is unremarkable and the
    ADDRESS is not, which is the only thing this module ever looks at.

    The address comes back on the EXCEPTION and not in the message; see
    `test_no_refusal_hands_the_resolved_address_back_to_the_caller` for why that
    distinction is a security property rather than a formatting one.
    """
    with pytest.raises(BlockedAddress) as refused:
        assert_safe_url(URL, resolver=fake_resolver({HOST: address}))
    assert refused.value.address == address


@pytest.mark.parametrize("address", ALLOWED_ADDRESSES)
def test_a_public_address_is_allowed(address, fake_resolver) -> None:
    """The non-vacuity half. A check that refuses everything passes every test
    above and is useless."""
    assert_safe_address(address)
    target = assert_safe_url(URL, resolver=fake_resolver({HOST: address}))
    assert target.addresses == (address,)


def test_the_two_entry_points_agree_on_every_address(fake_resolver) -> None:
    """**THE CHECK AND THE CONNECTION USE THE SAME PREDICATE, SWEPT.**

    `assert_safe_url` runs before the request; `assert_safe_address` runs at the
    moment of connection, on the address actually being used. They are only a
    defence together if they cannot disagree, so this crosses the whole table
    through both and compares the verdicts case for case.

    The structural half of the same claim is that `assert_safe_url` reaches its
    verdict BY CALLING `assert_safe_address` - see the test below - so this
    sweep is checking the composition rather than two parallel implementations.
    """
    sweep = BLOCKED_ADDRESSES + ALLOWED_ADDRESSES
    assert len(sweep) == 45, "the sweep must cover the whole table"

    disagreed, refused_at_connection = [], 0
    for address in sweep:
        at_connection = _refuses_the_address(address)
        before_request = _refuses_the_url(address, fake_resolver)
        refused_at_connection += at_connection
        if at_connection != before_request:
            disagreed.append((address, before_request, at_connection))
    assert disagreed == [], (
        f"the pre-flight check and the connect-time check disagree: {disagreed}. One of them "
        f"is the one that runs on the address the socket actually gets."
    )
    assert refused_at_connection == 38, "and the sweep is not vacuously refusing everything"


def _refuses_the_address(address: str) -> bool:
    try:
        assert_safe_address(address)
    except BlockedAddress:
        return True
    return False


def _refuses_the_url(address: str, fake_resolver) -> bool:
    try:
        assert_safe_url(URL, resolver=fake_resolver({HOST: address}))
    except BlockedAddress:
        return True
    return False


def test_the_url_check_reaches_its_verdict_by_calling_the_address_check() -> None:
    """The composition, structurally. Two independent implementations of "is
    this address safe" would pass the sweep above on the day they were written
    and drift the day after."""
    called = {
        node.func.id
        for node in ast.walk(_function("assert_safe_url"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "assert_safe_address" in called


# --------------------------------------------------------------------------
# DNS rebinding: the check and the connection must agree on the ADDRESS
# --------------------------------------------------------------------------


def test_the_resolver_is_called_exactly_once(fake_resolver) -> None:
    """A second resolution INSIDE the check would reopen the window the check
    exists to close: the addresses judged would not be the addresses returned."""
    resolver = fake_resolver({HOST: "93.184.216.34"})
    assert_safe_url(URL, resolver=resolver)
    assert resolver.calls == [(HOST, 443)]


def test_the_addresses_returned_are_the_ones_that_were_checked(fake_resolver) -> None:
    resolver = fake_resolver({HOST: ["93.184.216.34", "2606:4700:4700::1111"]})
    target = assert_safe_url(URL, resolver=resolver)
    assert target.addresses == ("93.184.216.34", "2606:4700:4700::1111")
    assert isinstance(target, SafeTarget)
    assert (target.host, target.port, target.scheme) == (HOST, 443, "https")


def test_a_name_that_answers_differently_the_second_time_cannot_move_the_target(
    rebinding_resolver,
) -> None:
    """**DNS REBINDING, EXECUTED.**

    The attack: the record is served with a one-second TTL, so the CHECK sees a
    public address and the CONNECTION - if it resolves again - is handed
    loopback. Everything about the defence is in what `assert_safe_url` gives
    back.

    Three things are asserted, and the second is the one that matters:

      1. the check passes, because the first answer really is public - a
         defence that refused here would be refusing the wrong thing;
      2. the addresses it returns are the ones it SAW, so a caller that connects
         to `target.addresses` reaches the address that was judged, not the one
         the attacker moved to;
      3. the second answer, which is what a caller that re-resolved would get,
         is refused by `assert_safe_address` - so the connect-time check catches
         even a caller that ignored point 2.
    """
    resolver = rebinding_resolver(HOST, ["93.184.216.34", "127.0.0.1"])

    target = assert_safe_url(URL, resolver=resolver)
    assert target.addresses == ("93.184.216.34",)
    assert len(resolver.calls) == 1

    second_answer = resolver(HOST, 443)[0][4][0]
    assert second_answer == "127.0.0.1", "the fixture must actually rebind, or this proves nothing"
    assert second_answer not in target.addresses
    with pytest.raises(BlockedAddress):
        assert_safe_address(second_answer, url=URL)


def test_a_name_that_is_private_first_and_public_afterwards_is_still_refused(
    rebinding_resolver,
) -> None:
    """The attack run the other way round, in case the check ever started
    retrying or taking the last answer rather than the first."""
    resolver = rebinding_resolver(HOST, ["10.0.0.5", "93.184.216.34"])
    with pytest.raises(BlockedAddress) as refused:
        assert_safe_url(URL, resolver=resolver)
    assert refused.value.address == "10.0.0.5", "the FIRST answer is the one that was judged"
    assert len(resolver.calls) == 1


#: Answers where one host resolves to more than one address. A module constant
#: rather than an inline list, because the length assertion below has to be
#: about THE LIST THE PARAMETRISATION USES. It used to be written inline and
#: re-listed inside the size test, and a second copy asserts nothing: collapsing
#: the parametrisation to a single case survived the whole suite, measured.
MULTI_ADDRESS_ANSWERS = (
    ["93.184.216.34", "10.0.0.5"],
    ["10.0.0.5", "93.184.216.34"],
    ["93.184.216.34", "2606:4700:4700::1111", "::1"],
)


@pytest.mark.parametrize("answers", MULTI_ADDRESS_ANSWERS)
def test_one_bad_address_in_the_answer_refuses_the_whole_url(answers, fake_resolver) -> None:
    """A host that resolves to a public address AND a private one is a host
    somebody is steering. Picking the good address out of the answer would leave
    the caller free to try the other one - and a client with happy-eyeballs
    behaviour makes that choice itself."""
    with pytest.raises(BlockedAddress):
        assert_safe_url(URL, resolver=fake_resolver({HOST: answers}))


def test_the_multi_address_table_is_the_size_it_looks() -> None:
    """About the constant the parametrisation reads, which is the only version
    of this assertion that says anything."""
    assert len(MULTI_ADDRESS_ANSWERS) == 3
    assert all(len(answer) >= 2 for answer in MULTI_ADDRESS_ANSWERS), (
        "every row has to name more than one address, or it is not testing the "
        "one-bad-address-refuses-the-whole-URL rule at all"
    )


# --------------------------------------------------------------------------
# The address FORMS the module deliberately never parses
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spelling",
    ["2130706433", "0177.0.0.1", "0x7f.0.0.1", "127.1", "017700000001"],
)
def test_the_c_library_turns_these_spellings_into_loopback(spelling) -> None:
    """**THE PREMISE, MEASURED RATHER THAN ASSERTED.**

    `ssrf.py` never asks what a host string looks like; it asks the resolver
    what the host IS. That is only a defence if the resolver really does turn
    these spellings into `127.0.0.1` - so this runs the conversion the C library
    performs, through `socket.inet_aton`, which is the same parser
    `getaddrinfo` reaches for a numeric host and is a pure string conversion
    with no I/O (it is on the socket ban's "cannot egress" list for that
    reason).

    A denylist of dotted-quad strings would have to enumerate all five of these
    spellings and the ones nobody has thought of. Judging the resolved address
    enumerates none.
    """
    assert socket.inet_ntoa(socket.inet_aton(spelling)) == "127.0.0.1"


@pytest.mark.parametrize(
    "spelling",
    ["2130706433", "0177.0.0.1", "0x7f.0.0.1", "127.1", "017700000001", "①②⑦.0.0.1"],
)
def test_a_host_in_any_spelling_is_refused_once_the_resolver_has_spoken(
    spelling, fake_resolver
) -> None:
    """The other half of the pair above: given a resolver that behaves the way
    the C library does, every spelling is refused - and so is a Unicode one that
    IDNA would fold, because the module judges the answer rather than the
    question."""
    with pytest.raises(BlockedAddress, match="loopback"):
        assert_safe_url(f"http://{spelling}/", resolver=fake_resolver({spelling: "127.0.0.1"}))


@pytest.mark.parametrize("url", ["http://[::1]/", "http://[::ffff:127.0.0.1]/", "http://[fd00::1]/"])
def test_a_bracketed_ipv6_literal_is_unwrapped_and_refused(url, fake_resolver) -> None:
    host = url.removeprefix("http://[").removesuffix("]/")
    with pytest.raises(BlockedAddress):
        assert_safe_url(url, resolver=fake_resolver({host: host}))


# --------------------------------------------------------------------------
# Schemes, credentials, ports, hosts
# --------------------------------------------------------------------------


NON_HTTP_URLS = (
    "file:///etc/passwd",
    "gopher://evil.example/_GET%20/",
    "ftp://evil.example/",
    "data:text/html,<script>alert(1)</script>",
    "dict://127.0.0.1:6379/",
    "jar:http://evil.example/!/",
    "javascript:alert(1)",
    "HTTPS+SOMETHING://evil.example/",
    "//evil.example/",
    "alphaplumbing.example/no-scheme",
)


@pytest.mark.parametrize("url", NON_HTTP_URLS)
def test_a_non_http_scheme_is_refused(url, fake_resolver) -> None:
    """`file:` reads the crawler's own filesystem; `gopher:` and `dict:` are the
    classic ways to speak an arbitrary protocol - Redis, SMTP - through a URL
    fetcher; `data:` needs no network at all. The last two have NO scheme, which
    is the same refusal for a different reason and a shape a "scheme not in
    denylist" check gets wrong."""
    resolver = fake_resolver({})
    with pytest.raises(BlockedAddress, match="scheme"):
        assert_safe_url(url, resolver=resolver)
    assert resolver.calls == [], "a refused scheme must never reach the resolver"


def test_the_scheme_table_is_the_size_it_looks() -> None:
    assert len(NON_HTTP_URLS) == 10


def test_an_uppercase_scheme_is_still_http(fake_resolver) -> None:
    target = assert_safe_url("HTTP://Alphaplumbing.Example/x", resolver=fake_resolver(
        {HOST: "93.184.216.34"}
    ))
    assert (target.scheme, target.host, target.port) == ("http", HOST, 80)


CREDENTIALLED_URLS = (
    "http://user:secret@alphaplumbing.example/",
    "https://alphaplumbing.example@127.0.0.1/",
    "http://alphaplumbing.example\\@127.0.0.1/",
    "https://token@alphaplumbing.example/",
)


@pytest.mark.parametrize("url", CREDENTIALLED_URLS)
def test_credentials_in_the_url_are_refused(url, fake_resolver) -> None:
    """Two separate reasons, and the second is the SSRF one. A crawler never
    authenticates, so a password in the URL is a secret about to be written into
    a log; and `https://alphaplumbing.example@127.0.0.1/` is the oldest trick
    there is for making a URL look like it points at a merchant's site when the
    host is the part after the @."""
    resolver = fake_resolver({})
    with pytest.raises(BlockedAddress, match="credentials") as refused:
        assert_safe_url(url, resolver=resolver)
    assert "secret" not in str(refused.value), "a message must not repeat the password back"
    assert "token" not in str(refused.value)
    assert resolver.calls == []


def test_the_credentials_table_is_the_size_it_looks() -> None:
    assert len(CREDENTIALLED_URLS) == 4


@pytest.mark.parametrize("port", [22, 25, 6379, 5432, 8080, 8443, 3128, 11211])
def test_a_port_outside_eighty_and_four_four_three_is_refused(port, fake_resolver) -> None:
    """The address rule does not cover this: a globally routable address can be
    somebody's Redis or SMTP server, and an HTTP fetcher pointed at either is a
    protocol-smuggling primitive."""
    resolver = fake_resolver({HOST: "93.184.216.34"})
    with pytest.raises(BlockedAddress, match=f"port {port}"):
        assert_safe_url(f"http://{HOST}:{port}/", resolver=resolver)
    assert resolver.calls == []


@pytest.mark.parametrize("url,port", [(f"http://{HOST}:80/", 80), (f"https://{HOST}:443/", 443)])
def test_an_explicit_default_port_is_allowed(url, port, fake_resolver) -> None:
    target = assert_safe_url(url, resolver=fake_resolver({HOST: "93.184.216.34"}))
    assert target.port == port


def test_an_explicit_port_zero_is_refused_rather_than_read_as_the_default(
    fake_resolver,
) -> None:
    """`urlsplit` returns `0` for `:0`, and `0` is FALSEY - so writing the
    default as `port_in_url or DEFAULT_PORTS[scheme]` silently turns "port 0"
    into "port 80" and lets the `SafeTarget` disagree with the URL about where
    the connection is going. The shipped spelling tests `is None` instead, and
    this is what holds it: measured, the `or` spelling survives every other test
    in this file."""
    resolver = fake_resolver({HOST: "93.184.216.34"})
    with pytest.raises(BlockedAddress, match="port 0"):
        assert_safe_url(f"http://{HOST}:0/", resolver=resolver)
    assert resolver.calls == [], "a refused port must never reach the resolver"


@pytest.mark.parametrize("url", ["http:///path", "http://", "https://:443/"])
def test_a_url_naming_no_host_is_refused(url, fake_resolver) -> None:
    with pytest.raises(BlockedAddress, match="no host"):
        assert_safe_url(url, resolver=fake_resolver({}))


@pytest.mark.parametrize("url", [f"http://{HOST}:99999/", f"http://{HOST}:notaport/"])
def test_an_unparseable_url_is_refused_rather_than_raising(url, fake_resolver) -> None:
    """A `ValueError` escaping this function would be an unhandled crash on the
    onboarding path, and worse, it would be a refusal that does not look like
    one to a caller catching `BlockedAddress`."""
    with pytest.raises(BlockedAddress):
        assert_safe_url(url, resolver=fake_resolver({}))


def test_a_host_that_does_not_resolve_is_refused_and_says_so(fake_resolver) -> None:
    """Fail closed, and say something TRUE while doing it: a merchant who
    mistyped their domain must not be told their website points somewhere
    dangerous."""
    with pytest.raises(BlockedAddress, match="could not be resolved") as refused:
        assert_safe_url("https://typo.exmaple/", resolver=fake_resolver({}))
    message = str(refused.value)
    assert "metadata" not in message and "private" not in message


def test_a_host_that_resolves_to_nothing_at_all_is_refused(fake_resolver) -> None:
    with pytest.raises(BlockedAddress, match="no addresses"):
        assert_safe_url(URL, resolver=fake_resolver({HOST: []}))


#: What a resolver can raise - and it is NOT `OSError` alone. Written out as
#: literals because "every failure of the seam comes back as one exception type"
#: is a judgement about the caller's contract, not a restatement of what the
#: fakes in this file happen to do; the length is pinned below.
RESOLVER_FAILURES = (
    socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided"),
    UnicodeError("label empty or too long"),
    ValueError("embedded null character"),
    OSError(51, "Network is unreachable"),
)


def test_the_resolver_failure_table_is_the_size_it_looks() -> None:
    assert len(RESOLVER_FAILURES) == 4
    assert any(not isinstance(failure, OSError) for failure in RESOLVER_FAILURES), (
        "the whole point of this table is the failures that are NOT OSError; a table "
        "of nothing but OSErrors would pass against `except OSError` alone"
    )


@pytest.mark.parametrize("failure", RESOLVER_FAILURES)
def test_any_failure_the_resolver_raises_comes_back_as_a_refusal(failure) -> None:
    """**THE RESOLVER SEAM DOES NOT RAISE `OSError` ALONE, AND NO FAKE IN THIS
    FILE COULD HAVE TOLD YOU THAT.**

    `socket.getaddrinfo` IDNA-encodes a `str` host before it does any I/O, and
    the `idna` codec raises `UnicodeError` - a `ValueError`, NOT an `OSError` -
    for a DNS label longer than 63 characters. `http://<64 a's>.example/` is a
    string a merchant can type into the onboarding form, and with `except
    OSError` alone `assert_safe_url` raised a bare `UnicodeError`: fail-closed,
    but as a crash straight past every caller catching `BlockedAddress`.

    It was invisible here because the only resolver these tests have is
    `FakeResolver`, which raises `socket.gaierror` and nothing else - a guard
    whose only in-tree producer cannot violate it. It was found by driving
    `assert_safe_url` against the REAL resolver outside the suite, and this
    table is the generalisation of the fix: whatever the seam raises, one
    exception type comes out.
    """

    def angry_resolver(host: str, port: int):
        raise failure

    with pytest.raises(BlockedAddress):
        assert_safe_url(URL, resolver=angry_resolver)


def test_the_idna_codec_refuses_an_over_long_dns_label_with_a_unicode_error() -> None:
    """**THE PREMISE, MEASURED**, and measurable here only because it is a pure
    string conversion with no I/O: the socket ban has replaced
    `socket.getaddrinfo` in this package, so the end-to-end reproduction cannot
    be run from inside the suite at all. The two subclass assertions are the
    load-bearing half - they are exactly why `except OSError` did not hold."""
    with pytest.raises(UnicodeError):
        ("a" * 64 + ".example").encode("idna")
    assert issubclass(UnicodeError, ValueError)
    assert not issubclass(UnicodeError, OSError)
    assert issubclass(socket.gaierror, OSError), "and the ordinary case still is one"


#: Answers that are not `getaddrinfo`-shaped at all. `socket.getaddrinfo`
#: produces none of these, which is exactly why they stayed open: the seam's only
#: producer today is the stdlib, and Task 27 injects a resolver of its own. Two
#: classes deliberately, because the first fix here would have caught one:
#: `answers[4][0]` was an `IndexError` on a short answer and a `TypeError` on an
#: unsubscriptable one, and a table of nothing but empty tuples would pass
#: against a guard that only caught `IndexError`.
MALFORMED_ANSWERS = (
    [(2, 1, 6, "", ())],           # a 5-tuple whose sockaddr is empty - IndexError
    [(2, 1, 6, "")],               # a 4-wide answer - IndexError
    [None],                        # not an answer at all - TypeError
    [(2, 1, 6, "", None)],         # no sockaddr - TypeError
    [(2, 1, 6, "", 7)],            # a sockaddr that is not a sequence - TypeError
    # Re-review N2: the guard caught `IndexError`, so it was itself a denylist of
    # the failures somebody thought of. A mapping is subscriptable and is NOT a
    # sequence, so `sockaddr[0]` is a `KeyError` - which escaped the guard
    # entirely, the same class of defect the guard exists to close. The guard now
    # catches `LookupError`, the base of both.
    [(2, 1, 6, "", {"addr": "10.0.0.1"})],  # a mapping sockaddr - KeyError
)


def test_the_malformed_answer_table_is_the_size_it_looks() -> None:
    assert len(MALFORMED_ANSWERS) == 6
    kinds = set()
    for answers in MALFORMED_ANSWERS:
        try:
            tuple(str(answer[4][0]) for answer in answers)
        except Exception as raised:  # noqa: BLE001 - the type IS the measurement
            kinds.add(type(raised).__name__)
    assert kinds == {"IndexError", "KeyError", "TypeError"}, (
        f"this table exists to cover both ways an unreadable answer fails, and it now covers "
        f"{sorted(kinds)}. A table of one kind would pass against a guard catching only that "
        f"kind - the same shape as RESOLVER_FAILURES above."
    )


@pytest.mark.parametrize("answers", MALFORMED_ANSWERS)
def test_an_answer_the_module_cannot_read_is_a_refusal_rather_than_a_crash(answers) -> None:
    """**AN ANSWER THIS MODULE DOES NOT UNDERSTAND IS NOT AN ANSWER IT CONNECTS
    TO**, which `_SockAddr`'s comment already claimed - truthfully for a sockaddr
    whose first element is an integer or bytes (both come back as "not an IP
    address"), and falsely for one that cannot be indexed at all. Those escaped
    as `IndexError` and `TypeError`, straight past a caller catching
    `BlockedAddress`, in the same shape as the `UnicodeError` defect: a guard
    written for the failures somebody thought of.
    """
    with pytest.raises(BlockedAddress, match="cannot read"):
        assert_safe_url(URL, resolver=lambda host, port: answers)


def test_the_fake_resolver_refuses_a_url_shaped_key(fake_resolver) -> None:
    """The FIXTURE's own guard, exercised. The plan's sketch keyed the double by
    URL, which would make it a different SHAPE from `socket.getaddrinfo` - so no
    test using it would exercise the call this module really makes. Every other
    test here passes a bare host, so without this the guard is a branch nothing
    runs, and a guard whose only in-tree producer cannot violate it is untested.
    Measured: deleting the check survives the whole suite."""
    with pytest.raises(ValueError, match="keyed by HOST"):
        fake_resolver({URL: "93.184.216.34"})


# --------------------------------------------------------------------------
# The cloud metadata services
# --------------------------------------------------------------------------


@pytest.mark.parametrize("address,description", sorted(CLOUD_METADATA_ADDRESSES.items()))
def test_a_metadata_endpoint_is_named_in_the_refusal(address, description, fake_resolver) -> None:
    """Blueprint §12.6: a merchant URL redirecting there, on a crawler with an
    over-privileged service account, is a direct route to cloud credentials. The
    refusal says which service, because "your site redirects to the AWS metadata
    service" is a materially different thing for an operator to read than "not
    globally routable"."""
    with pytest.raises(BlockedAddress, match="metadata") as refused:
        assert_safe_url(
            "http://metadata.internal/latest/meta-data/",
            resolver=fake_resolver({"metadata.internal": address}),
        )
    assert description in str(refused.value)


def test_the_metadata_table_is_not_what_blocks_them() -> None:
    """**THE NAMING MUST NEVER BECOME THE MECHANISM.**

    Every address in that table is refused by the derived rule alone. If it were
    not - if the table were doing the blocking - then the defence against
    metadata services would be a list of four addresses, which is the
    hand-maintained list failure in the one place it costs the most: a fifth
    cloud provider, or one that moves its endpoint, would be reachable.

    Executed by asking `_routability_problem`, which cannot see the table.
    """
    for address in CLOUD_METADATA_ADDRESSES:
        assert ssrf._routability_problem(ipaddress.ip_address(address)) is not None, address
    assert set(CLOUD_METADATA_ADDRESSES) <= set(BLOCKED_ADDRESSES)


def test_every_metadata_key_is_written_the_way_ipaddress_writes_it() -> None:
    """The lookup is `CLOUD_METADATA_ADDRESSES.get(str(ip))`, so a key written
    in any other form - `fd00:ec2:0:0:0:0:0:254`, or with a capital letter -
    would match nothing and the naming would silently stop happening. Nothing
    behavioural would fail, because the address would still be blocked."""
    for address in CLOUD_METADATA_ADDRESSES:
        assert str(ipaddress.ip_address(address)) == address


# --------------------------------------------------------------------------
# Redirects: every hop, not just the first
# --------------------------------------------------------------------------


REDIRECT_ATTACKS = (
    ("http://127.0.0.1/admin", "127.0.0.1"),
    ("http://169.254.169.254/latest/meta-data/", "169.254.169.254"),
    ("//169.254.169.254/latest/meta-data/", "169.254.169.254"),
    ("/../../", None),
    ("file:///etc/passwd", None),
    ("gopher://127.0.0.1:6379/_FLUSHALL", None),
    ("http://sneaky.example/", "10.1.2.3"),
)

#: The three groups the table splits into, DERIVED so that every row drives a
#: test and the split is asserted to be a partition. The two parametrisations
#: below used to be written as a SLICE (`[:3] + [6:]`) and as a duplicated pair
#: of literals, which left row 3 - the `/../../` Location - driving nothing at
#: all: `len(REDIRECT_ATTACKS) == 7` read like seven attacks and was four.
REDIRECTS_TO_A_BAD_ADDRESS = tuple(
    (location, resolves_to)
    for location, resolves_to in REDIRECT_ATTACKS
    if resolves_to is not None
)
REDIRECTS_THAT_CHANGE_SCHEME = tuple(
    location
    for location, resolves_to in REDIRECT_ATTACKS
    if resolves_to is None and "://" in location
)
REDIRECTS_THAT_STAY_PUT = tuple(
    location
    for location, resolves_to in REDIRECT_ATTACKS
    if resolves_to is None and "://" not in location
)


@pytest.mark.parametrize("location,resolves_to", REDIRECTS_TO_A_BAD_ADDRESS)
def test_a_redirect_to_a_private_address_is_refused(location, resolves_to, fake_resolver) -> None:
    """A public URL that answers `302` is the ordinary way past a check that
    only ran on the URL the merchant typed. The protocol-relative form is the
    one worth naming: `Location: //169.254.169.254/` inherits `https` and looks
    like a path."""
    answers = {HOST: "93.184.216.34", "169.254.169.254": "169.254.169.254",
               "127.0.0.1": "127.0.0.1", "sneaky.example": "10.1.2.3"}
    with pytest.raises(BlockedAddress) as refused:
        assert_safe_redirect(URL, location, resolver=fake_resolver(answers))
    assert refused.value.address == resolves_to, (
        "the hop is judged on the address it resolved to, and that address reaches the "
        "operator on the exception rather than the merchant in the message"
    )


@pytest.mark.parametrize("location", REDIRECTS_THAT_CHANGE_SCHEME)
def test_a_redirect_that_changes_scheme_is_refused(location, fake_resolver) -> None:
    """`urljoin` lets an absolute `Location` replace the scheme outright, so a
    hop can leave http entirely. It meets the scheme check like any other URL,
    which is the whole reason the hop re-runs the WHOLE check rather than
    comparing hosts."""
    with pytest.raises(BlockedAddress, match="scheme"):
        assert_safe_redirect(URL, location, resolver=fake_resolver({}))


def test_a_relative_redirect_stays_on_the_host_it_came_from(fake_resolver) -> None:
    target = assert_safe_redirect(URL, "/services", resolver=fake_resolver({HOST: "93.184.216.34"}))
    assert target.url == f"https://{HOST}/services"
    assert target.addresses == ("93.184.216.34",)


def test_an_empty_location_header_is_refused(fake_resolver) -> None:
    with pytest.raises(BlockedAddress, match="empty Location"):
        assert_safe_redirect(URL, "   ", resolver=fake_resolver({}))


def test_a_chain_that_only_turns_hostile_on_the_third_hop_is_caught_there(fake_resolver) -> None:
    """**EVERY HOP, NOT THE FIRST HOP.** Two innocent redirects and then the
    metadata service: a check that ran once, or that trusted a hop because the
    previous one was fine, follows this all the way down. Each hop is judged on
    its own resolved address, so the chain is refused where it turns and not
    before.
    """
    resolver = fake_resolver({
        HOST: "93.184.216.34",
        "cdn.example": "8.8.8.8",
        "metadata.internal": "169.254.169.254",
    })
    chain = ["/promo", "https://cdn.example/asset", "http://metadata.internal/latest/meta-data/"]

    here = URL
    for hop in chain[:-1]:
        here = assert_safe_redirect(here, hop, resolver=resolver).url
    assert here == "https://cdn.example/asset"

    with pytest.raises(BlockedAddress, match="metadata"):
        assert_safe_redirect(here, chain[-1], resolver=resolver)
    assert len(resolver.calls) == 3, "every hop was resolved and judged, including the last"


@pytest.mark.parametrize("location", REDIRECTS_THAT_STAY_PUT)
def test_a_location_that_walks_up_the_path_stays_on_the_host_it_came_from(
    location, fake_resolver
) -> None:
    """`/../../` is not an attack on the ADDRESS - `urljoin` resolves it back to
    the origin - and it belongs in the table because a check that refused it
    would be refusing an ordinary redirect. It is exercised here so that EVERY
    row of `REDIRECT_ATTACKS` drives something; before this it drove nothing and
    the table's size assertion read like coverage it did not have."""
    target = assert_safe_redirect(URL, location, resolver=fake_resolver({HOST: "93.184.216.34"}))
    assert target.host == HOST
    assert target.addresses == ("93.184.216.34",)


def test_the_redirect_attack_table_is_the_size_it_looks() -> None:
    """The table AND the partition of it. A derived parametrisation that quietly
    collects nothing reads exactly like one that collects four, and the sum
    assertion is what says every row still has a home."""
    assert len(REDIRECT_ATTACKS) == 7
    assert len(REDIRECTS_TO_A_BAD_ADDRESS) == 4
    assert len(REDIRECTS_THAT_CHANGE_SCHEME) == 2
    assert len(REDIRECTS_THAT_STAY_PUT) == 1
    assert (
        len(REDIRECTS_TO_A_BAD_ADDRESS)
        + len(REDIRECTS_THAT_CHANGE_SCHEME)
        + len(REDIRECTS_THAT_STAY_PUT)
    ) == len(REDIRECT_ATTACKS), "every row of the table has to drive a test"


# --------------------------------------------------------------------------
# The resolver seam itself
# --------------------------------------------------------------------------


def test_the_default_resolver_is_looked_up_at_call_time_not_captured_at_import(
    monkeypatch,
) -> None:
    """**A CAPTURED DEFAULT ARGUMENT IS IMMUNE TO EVERY LATER PATCH**, including
    this suite's socket ban. `def f(resolver=socket.getaddrinfo)` - which is
    what this task's plan specified - binds the function OBJECT when `ssrf.py`
    is imported, so rebinding `socket.getaddrinfo` afterwards does not touch it
    and a test believing it cannot reach the network would make a real DNS
    query.

    Both halves are asserted: the signature carries no captured callable, and a
    resolver installed on the `socket` module AFTER import is the one that runs.
    """
    assert inspect.signature(assert_safe_url).parameters["resolver"].default is None
    assert inspect.signature(assert_safe_redirect).parameters["resolver"].default is None

    seen = []

    def probe(host, port, *args, **kwargs):
        seen.append((host, port))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", probe)
    target = assert_safe_url(URL)
    assert seen == [(HOST, 443)]
    assert target.addresses == ("93.184.216.34",)


def test_no_function_here_captures_a_socket_function_as_a_default() -> None:
    """The general form of the finding above, so it cannot come back on the next
    function somebody adds to this module."""
    captured = []
    for node in ast.walk(SSRF_TREE):
        if not isinstance(node, ast.FunctionDef):
            continue
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if (
                isinstance(default, ast.Attribute)
                and isinstance(default.value, ast.Name)
                and default.value.id == "socket"
            ):
                captured.append(f"{node.name}() defaults to socket.{default.attr}")
    assert captured == [], (
        f"{captured}: a default argument is evaluated at import, so it holds the ORIGINAL "
        f"function and no later patch - the socket ban included - can reach it. Look the "
        f"name up inside the function instead."
    )


def test_calling_without_a_resolver_reaches_the_socket_ban_rather_than_the_network() -> None:
    """**THE BAN IS MEASURED IN THIS PACKAGE, NOT ASSUMED.** The default really
    is the real resolver, and in this directory the real resolver is closed. A
    test in this package that forgets `resolver=` therefore fails loudly instead
    of quietly making a DNS query - which is the only reason a default of
    `socket.getaddrinfo` is safe to ship at all.
    """
    with pytest.raises(RuntimeError, match=NETWORK_BAN):
        assert_safe_url("https://example.invalid/")


def test_the_ban_is_already_in_force_when_this_module_is_imported() -> None:
    """**THE COLLECTION HOOK, PINNED IN THE DIRECTORY IT GUARDS.**

    Module import happens during COLLECTION, before any fixture of any scope
    runs, so `pytest_runtest_protocol` alone would leave import time open - and
    the test above, which reaches the ban through an ordinary test, cannot tell
    the two hooks apart. Measured: deleting
    `tests/crawler/conftest.py::pytest_make_collect_report` survived all 2766
    tests before this existed. The equivalent pair lives in
    `tests/llm/test_anthropic_provider.py`; this package had neither.
    """
    assert NETWORK_BAN in _AT_IMPORT_TIME, _AT_IMPORT_TIME


@pytest.fixture(scope="session")
def a_session_scoped_fixture_that_tries_the_network():
    """Session scope, so pytest builds it before every function-scoped fixture.
    `socket.socket()` for the same reason as the import-time probe above: it is
    inert when the ban is absent, where resolving a name would egress."""
    try:
        opened = socket.socket()
        opened.close()
        return "a socket was opened in a session-scoped fixture"
    except RuntimeError as refused:
        return str(refused)


def test_the_ban_is_already_in_force_when_a_session_scoped_fixture_runs(
    a_session_scoped_fixture_that_tries_the_network,
) -> None:
    """pytest builds session-, package-, module- and class-scoped fixtures
    before function-scoped ones, so a fixture is the second way past a guard
    installed too late. `pytest_runtest_protocol` wraps the whole protocol
    INCLUDING setup, which is what makes this hold."""
    assert NETWORK_BAN in a_session_scoped_fixture_that_tries_the_network, (
        a_session_scoped_fixture_that_tries_the_network
    )


def test_the_ban_does_not_leak_out_of_this_package() -> None:
    """**THE THIRD PROBE, COMMITTED THIS TIME - AND IT IS THE DEFECT THIS FILE
    IS ABOUT.**

    `pytest_runtest_protocol` is dispatched through `item.config.hook`, THE
    GLOBAL ONE, so this package's wrapper fires for every test in the session and
    `_is_ours` is the only thing keeping the ban inside `tests/crawler/`.
    `tests/db` and `tests/gateway` need real sockets to reach Postgres and Redis,
    so an unscoped ban is not a stricter ban, it is a broken suite - and that is
    what the first version of these hooks was.

    Nothing held it. Measured, twice, a round apart: replacing `_is_ours` with
    `if False:` in `tests/crawler/conftest.py` bans the network for the WHOLE
    session, and the DB-free selection - the only selection that runs while the
    Docker daemon is down - still reports every test passing. `tests/llm`'s own
    leak test cannot see it, because its subprocess collects one `tests/llm` test
    and a probe, so `tests/crawler/conftest.py` is never loaded there and its
    hooks are never registered.

    That is D7 again in the report that closed D7: the previous round ran this as
    a scratch probe, read the output, and deleted it - the third of three probes,
    and the only one that did not become a test. `tests/llm` has the identical
    test for its own directory; a shared mechanism needs the guard in BOTH
    directories that install it, because each installs its own hooks.

    It fails in the safe direction (an over-block, never egress), which is why
    the subprocess asserts `2 passed` rather than merely a zero return code: an
    over-blocked outside test FAILS, and a collection that quietly found one test
    instead of two would return zero.

    **BOTH PROBES ARE WRITTEN HERE RATHER THAN NAMING AN EXISTING TEST**, which
    `tests/llm`'s version does. Measured, in this fix round's own battery: with a
    named test inside the guarded directory, any mutation that broke THAT test
    also failed this one, so a CAUGHT verdict here could be right for the wrong
    reason. Writing both ends means this test depends on no other test - and the
    inside probe now asserts the other direction too, that the ban really IS
    armed in the subprocess, so `2 passed` cannot be reached by a run where the
    hooks never fired at all.
    """
    tests_root = pathlib.Path(__file__).resolve().parents[1]
    repo_root = tests_root.parent
    # One probe in this guarded directory and one outside BOTH of them, named so
    # neither can collide with `tests/llm`'s probe of the same shape.
    stamp = os.getpid()
    inside = tests_root / "crawler" / f"test_zz_crawler_ban_armed_probe_{stamp}.py"
    outside = tests_root / f"test_zz_crawler_ban_leak_probe_{stamp}.py"
    inside.write_text(
        "import socket\n\n"
        "import pytest\n\n"
        "from tests.network_ban import NETWORK_BAN\n\n\n"
        "def test_a_test_inside_tests_crawler_cannot_open_a_socket():\n"
        "    with pytest.raises(RuntimeError, match=NETWORK_BAN):\n"
        "        socket.socket()\n"
    )
    outside.write_text(
        "import socket\n\n\n"
        "def test_a_test_outside_tests_crawler_can_still_open_a_socket():\n"
        "    made = socket.socket()\n"
        "    made.close()\n"
    )
    try:
        finished = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(inside.relative_to(repo_root)),
                str(outside.relative_to(repo_root)),
                "-q",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,  # the return code is the measurement, so it is read below
        )
    finally:
        inside.unlink()
        outside.unlink()
    assert finished.returncode == 0, finished.stdout + finished.stderr
    assert "2 passed" in finished.stdout, finished.stdout


def test_the_guarded_directories_carry_the_same_ban_marker() -> None:
    """The marker is spelled out as a literal in every guarded conftest because
    the walk that consumes it reads FILE TEXT. Separate literals drift; this is
    what stops them.

    **THE DIRECTORIES ARE DERIVED, NOT NAMED.** This test used to import
    `tests.crawler.conftest` and `tests.llm.conftest` by hand and was called
    `..._the_two_guarded_directories...`; Task 28 added a third
    (`tests/workflows`, which wraps both guarded packages) and the hand-written
    version went on passing while covering two thirds of what it claims to. A
    list of the things a guard applies to, inside the guard, is the shape this
    project has now paid for eight times - so the set comes off the filesystem.
    """
    from tests.crawler.conftest import BAN_INSTALLED_HERE

    tests_root = pathlib.Path(__file__).resolve().parents[1]
    conftests = sorted(
        path for path in tests_root.rglob("conftest.py")
        if BAN_INSTALLED_HERE in path.read_text()
    )
    # The proof of concept had three guarded directories (crawler, llm, workflows).
    # This repository starts with the crawler alone; the count grows as the LLM and
    # worker packages are ported, and this floor rises with them.
    assert len(conftests) >= 1, f"only {len(conftests)} conftest(s) install the ban"
    for path in conftests:
        text = path.read_text()
        assert f'"{BAN_INSTALLED_HERE}"' in text, (
            f"{path}: the marker must appear as a literal, not as an imported name - the "
            f"walk in tests/llm/test_anthropic_provider.py greps conftest text without "
            f"importing it"
        )


# --------------------------------------------------------------------------
# The messages, which reach a merchant
# --------------------------------------------------------------------------


def test_every_refusal_reason_is_true_of_the_address_it_is_given_for() -> None:
    """**ANY MESSAGE A MERCHANT SEES MUST BE TRUE IN EVERY CONFIGURATION THAT
    CAN REACH IT** - nine instances of the opposite on this project so far. The
    reason is picked by first match over `_WHY_NOT_ROUTABLE`, so this walks the
    whole blocked table and checks the property the wording names is actually
    set on that address.
    """
    property_for = {description: attribute for attribute, description in ssrf._WHY_NOT_ROUTABLE}
    fallback_used = []
    for address in BLOCKED_ADDRESSES:
        ip = ipaddress.ip_address(address)
        reason = ssrf._routability_problem(ip)
        if reason == "not a globally routable address":
            assert not any(getattr(ip, name) for name, _ in ssrf._WHY_NOT_ROUTABLE), address
            fallback_used.append(address)
        else:
            assert getattr(ip, property_for[reason]), f"{address} is called {reason!r}"
    assert fallback_used == ["100.64.0.1", "100.100.100.200", "fec0::1", "feff::1"], (
        "the fallback wording is a sentence a merchant can reach, so the table has to keep "
        "reaching it"
    )


def test_a_refusal_never_repeats_a_password_back(fake_resolver) -> None:
    """An exception message is the one place a secret is certain to be written
    down: a log line, and through Task 27 a merchant-facing string."""
    with pytest.raises(BlockedAddress) as refused:
        assert_safe_url("http://alice:hunter2@alphaplumbing.example:22/", resolver=fake_resolver({}))
    assert "hunter2" not in str(refused.value)
    assert "***@" in str(refused.value), "the shape is kept so the message is still useful"


def test_a_refusal_does_not_quote_an_unbounded_url(fake_resolver) -> None:
    """A `data:` URL can be megabytes long and it goes straight into a message."""
    enormous = "data:text/html," + "A" * 10_000
    with pytest.raises(BlockedAddress) as refused:
        assert_safe_url(enormous, resolver=fake_resolver({}))
    assert len(str(refused.value)) < 400
    assert str(refused.value).count("A") <= ssrf._ECHO_LIMIT


#: Hosts that make a message impossible to write down. Neither is reachable
#: through a browser form - `urlsplit` already strips `\t\r\n`, and a lone
#: surrogate cannot arrive over UTF-8 - but the message is documented as
#: merchant-facing and log-bound, and `_safe_to_echo` is the one place with the
#: responsibility.
UNWRITEABLE_HOSTS = (
    "a\x07b.example",           # BEL, which a terminal reading a log would ring
    "x\x08\x08\x08y.example",   # backspaces, which rewrite what was already printed
    "alpha\ud800.example",      # a lone surrogate: str.encode("utf-8") RAISES on it
)


def test_a_refusal_can_always_be_written_to_a_utf_eight_log(fake_resolver) -> None:
    """**A LOG HANDLER THAT RAISES WHILE LOGGING THE REFUSAL IS WORSE THAN THE
    REFUSAL.** A host carrying a lone surrogate produced a `BlockedAddress` whose
    message could not be UTF-8 encoded, so printing it raised
    `UnicodeEncodeError` - the crawler would refuse correctly and then die
    writing the refusal down. Control characters reached a terminal intact.

    The rule `_safe_to_echo` now applies is one line and covers both: a URL that
    is not printable is shown escaped. A printable one is untouched, which is
    what keeps an internationalised domain readable to the merchant who owns it -
    the assertion below is the half that stops the fix being "escape everything".
    """
    for host in UNWRITEABLE_HOSTS:
        with pytest.raises(BlockedAddress) as refused:
            assert_safe_url(f"http://{host}/", resolver=fake_resolver({}))
        message = str(refused.value)
        message.encode("utf-8")  # the failure this exists for: it used to raise here
        assert message.isprintable(), message.encode("unicode_escape")

    idn = "https://café.example/"
    with pytest.raises(BlockedAddress) as refused:
        assert_safe_url(idn, resolver=fake_resolver({}))
    assert idn in str(refused.value), "a printable URL is quoted as the merchant typed it"


def test_the_echo_limit_is_a_literal() -> None:
    assert ssrf._ECHO_LIMIT == 120
    assert isinstance(_binding("_ECHO_LIMIT"), ast.Constant)


def test_a_refusal_names_the_url_and_why_but_not_the_address_it_leads_to(
    fake_resolver,
) -> None:
    """The URL is the merchant's own; the reason is what they can act on; the
    address is neither, and it is the one piece they did not supply."""
    with pytest.raises(BlockedAddress) as refused:
        assert_safe_url(URL, resolver=fake_resolver({HOST: "10.0.0.5"}))
    message = str(refused.value)
    assert URL in message
    assert "private" in message
    assert "10.0.0.5" not in message
    assert refused.value.address == "10.0.0.5"


def test_no_refusal_hands_the_resolved_address_back_to_the_caller(fake_resolver) -> None:
    """**THE ONBOARDING FORM MUST NOT BE AN INTERNAL DNS AND ADDRESS
    ENUMERATION ORACLE**, which is what it was: the refusal for a hostname the
    merchant supplied read "... leads to 10.4.2.17, which is in private ...", so
    an untrusted party could submit `jenkins.corp.internal` and read our internal
    address out of the answer, with no fetch and no redirect. The module already
    redacted passwords from these messages and bounded their length; the resolved
    address had never been weighed on the same terms.

    Swept over the whole blocked table through BOTH entry points, because the
    connect-time gate produces messages too, and a caller logs whichever it got.
    The address is carried on `BlockedAddress.address` for the operator - the
    other assertion here, since a redaction that also lost the address for the
    log would have to be undone by the next person to debug a refusal.

    Note what this does NOT close, honestly: the three outcomes are still
    distinguishable ("could not be resolved" / "leads to ... not on the public
    internet" / accepted), so a merchant-facing check still says whether a name
    resolves and whether it is fetchable. That is inherent to telling a merchant
    why we could not read their site. Removing the VALUE is what stops the oracle
    yielding addresses.
    """
    leaked = []
    for address in BLOCKED_ADDRESSES:
        for name, refuse in (
            ("assert_safe_url", lambda a: assert_safe_url(URL, resolver=fake_resolver({HOST: a}))),
            ("assert_safe_address", lambda a: assert_safe_address(a, url=URL)),
            ("assert_safe_address (no url)", lambda a: assert_safe_address(a)),
        ):
            with pytest.raises(BlockedAddress) as refused:
                refuse(address)
            if address in str(refused.value):
                leaked.append((name, address, str(refused.value)))
            assert refused.value.address == address, (
                f"{name} refused {address} without carrying it on the exception - Task 27 "
                f"logs this, and a refusal an operator cannot resolve to an address is a "
                f"refusal nobody can debug"
            )
    assert leaked == [], (
        f"these refusals name the resolved address in a message a merchant reads: {leaked}. "
        f"The address goes on BlockedAddress.address, which fetch.py LOGS and never renders."
    )


def test_the_address_check_refuses_something_that_is_not_an_address() -> None:
    """`assert_safe_address` is called by Task 27 with whatever the socket layer
    reports, which is a string. Anything unparseable must refuse rather than
    raise `ValueError` past a caller catching `BlockedAddress`.

    The same audience split as above: the value is on the exception, not in the
    message. A resolver's answer is chosen by whoever controls the zone.
    """
    with pytest.raises(BlockedAddress, match="not an IP address") as refused:
        assert_safe_address("not-an-address")
    assert "not-an-address" not in str(refused.value)
    assert refused.value.address == "not-an-address"


def test_a_refusal_that_never_reached_an_address_carries_none(fake_resolver) -> None:
    """`BlockedAddress.address` is `None` rather than absent for the refusals
    that stop before DNS, so `fetch.py` can log it unconditionally instead of
    guarding every call site with `getattr`."""
    for url in ("file:///etc/passwd", "http://user:pw@alphaplumbing.example/",
                "http://alphaplumbing.example:6379/", "https://alphaplumbing.example/"):
        with pytest.raises(BlockedAddress) as refused:
            assert_safe_url(url, resolver=fake_resolver({}))
        assert refused.value.address is None, url


# --------------------------------------------------------------------------
# The shape of the module
# --------------------------------------------------------------------------


def test_the_safe_target_is_frozen() -> None:
    """It is the connection's instruction. A caller that could edit `addresses`
    after the check could edit the check's answer."""
    target = SafeTarget(url=URL, scheme="https", host=HOST, port=443, addresses=("1.1.1.1",))
    with pytest.raises(dataclasses.FrozenInstanceError):
        target.addresses = ("127.0.0.1",)  # type: ignore[misc]


def test_blocked_address_is_the_only_refusal_type() -> None:
    """One exception type, because the caller's response to every refusal is the
    same: do not fetch. The message is what distinguishes them."""
    assert issubclass(BlockedAddress, Exception)
    raised = {
        node.exc.func.id
        for node in ast.walk(SSRF_TREE)
        if isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, ast.Name)
    }
    assert raised == {"BlockedAddress"}
