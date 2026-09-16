"""**NO TEST IN THIS PACKAGE MAY REACH THE NETWORK, AND THAT IS MECHANICAL.**

The same ban as `tests/llm/`, from the same module - see `tests/network_ban.py`
for what it closes, when it is armed and what it does not cover. It is here for
a reason specific to this package: `ppcway.crawler.ssrf.assert_safe_url`'s
resolver defaults to `socket.getaddrinfo`, so a test that omits `resolver=` -
which is one keyword away at every call site - makes a real DNS query. That is
egress, it is slow and flaky, and on a machine with working DNS it would pass
while proving nothing about what the check does with the answer.

Task 27 adds real HTTP to this directory, at which point the ban stops being a
precaution and becomes the thing standing between the test suite and every
merchant website in the fixtures.

**AND THE BAN IS WHAT MAKES `_default_resolver` TESTABLE**, which is the other
half. `assert_safe_url` looks `socket.getaddrinfo` up when it runs rather than
capturing it as a default argument, precisely so that this ban applies to it;
`test_calling_without_a_resolver_reaches_the_socket_ban_rather_than_the_network`
is the executed proof, and it can only be written where the ban exists.

The fixtures below are ATTACKS, not conveniences. A guard tested against a
well-behaved caller is untested: every one of these fixtures exists to try
something specific at `ssrf.py` - a name that answers differently the second
time, a host with one good address and one bad one, a chain of redirects that
only turns hostile on the third hop.
"""
import dataclasses
import ipaddress
import pathlib
import socket

import httpx
import pytest

from tests.network_ban import banned, scoped_to

#: Marks this directory as one that installs the network ban, for
#: `tests/llm/test_anthropic_provider.py::test_every_test_module_that_can_reach_
#: a_guarded_module_runs_under_this_ban`, which greps conftest FILE TEXT rather
#: than importing conftests. That is why this is spelled out as a literal
#: instead of imported from `tests.llm.conftest`: an imported name would leave
#: this directory looking unguarded to that walk, silently. The two copies are
#: held equal by `test_ssrf.py::test_the_two_guarded_directories_carry_the_same_
#: ban_marker`.
BAN_INSTALLED_HERE = "ppcway-llm-network-ban"

HERE = pathlib.Path(__file__).resolve().parent
_is_ours = scoped_to(HERE)


@pytest.hookimpl(wrapper=True)
def pytest_make_collect_report(collector):
    """Collection is what imports a test module, so this is the window that
    covers import time."""
    if not _is_ours(getattr(collector, "path", None)):
        return (yield)
    with banned():
        return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Setup, call and teardown of one test. Fixtures of EVERY scope are built
    inside setup, so a session-scoped fixture requested by a test in this
    package is created with the ban already in force.

    **`_is_ours` IS NOT A TIDINESS CHECK, IT IS THE ONLY THING KEEPING THE BAN
    INSIDE THIS DIRECTORY.** THIS hook is dispatched through `item.config.hook`,
    the global one, so it fires for every test in the session - `tests/db` and
    `tests/gateway` included, and those need real sockets to reach Postgres and
    Redis. Removing it does not make the suite stricter, it breaks it, and the
    DB-free selection stays entirely green while it does. Held by
    `test_ssrf.py::test_the_ban_does_not_leak_out_of_this_package`, which is the
    crawler's own copy of the `tests/llm` test of the same name: each directory
    registers its own hooks, so the other package's copy cannot see this one.
    """
    if not _is_ours(getattr(item, "path", None)):
        return (yield)
    with banned():
        return (yield)


def address_info(address: str, port: int):
    """One `socket.getaddrinfo` answer tuple for `address`.

    The family is derived from the address rather than passed in, and the
    sockaddr is four-wide for IPv6 and two-wide for IPv4, because that is the
    shape `getaddrinfo` really returns and `ssrf.py` indexes into it. A fake
    that returned a uniform shape would let a real-world indexing bug through.
    """
    ip = ipaddress.ip_address(address)
    if ip.version == 4:
        return (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port))
    return (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port, 0, 0))


class FakeResolver:
    """A `socket.getaddrinfo` stand-in over a host -> addresses mapping.

    **KEYED BY HOST, NOT BY URL.** The plan's sketch keyed it by URL, which
    would make the double a different SHAPE from the thing it replaces - the
    production default takes `(host, port)` - so no test using it would exercise
    the call this module actually makes. A fake that cannot be substituted for
    the real one tests the fake.

    An unknown host raises `socket.gaierror`, which is what the real resolver
    does and is a case `assert_safe_url` has to have an answer for. `calls`
    records every lookup, because "how many times was this resolved" is a
    security property here rather than a performance one.
    """

    def __init__(self, answers):
        self.answers = {}
        for host, addresses in answers.items():
            if "://" in host or "/" in host:
                raise ValueError(
                    f"{host!r} looks like a URL. FakeResolver is keyed by HOST, the way "
                    f"socket.getaddrinfo is - otherwise it is not a stand-in for it."
                )
            self.answers[host] = (addresses,) if isinstance(addresses, str) else tuple(addresses)
        self.calls: list[tuple[str, int]] = []

    def __call__(self, host, port):
        self.calls.append((host, port))
        if host not in self.answers:
            raise socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided")
        return [address_info(address, port) for address in self.answers[host]]


class SequenceResolver:
    """A resolver that answers DIFFERENTLY EACH TIME IT IS ASKED.

    This is DNS rebinding as a test double. A real attacker serves the record
    with a one-second TTL: the check resolves it and sees a public address, the
    HTTP client resolves it again a moment later and is handed `127.0.0.1`.
    Anything that resolves twice loses to this; anything that resolves once and
    connects to what it resolved does not.
    """

    def __init__(self, host, answers_per_call):
        self.host = host
        self.answers_per_call = [
            (addresses,) if isinstance(addresses, str) else tuple(addresses)
            for addresses in answers_per_call
        ]
        self.calls: list[tuple[str, int]] = []

    def __call__(self, host, port):
        self.calls.append((host, port))
        if host != self.host:
            raise socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided")
        index = min(len(self.calls) - 1, len(self.answers_per_call) - 1)
        return [address_info(address, port) for address in self.answers_per_call[index]]


@pytest.fixture()
def fake_resolver():
    """Build a `FakeResolver` from `{host: address}` or `{host: [addresses]}`."""
    return FakeResolver


@pytest.fixture()
def rebinding_resolver():
    """Build a `SequenceResolver`: `(host, [first_answer, second_answer, ...])`."""
    return SequenceResolver


# --------------------------------------------------------------------------
# The site fakes, for `fetch.py`
# --------------------------------------------------------------------------
#
# **THE FAKE SITE RESOLVES WHATEVER HOST IT IS HANDED, AND THAT IS THE WHOLE
# POINT OF IT.** Task 26's review named the trap this exists to avoid: a fetch
# test driven by a fake client that answers to any address CANNOT FAIL the one
# property the crawler is for, because a fake that never resolves cannot be
# handed a name and caught doing it. So `FakeSite` does what a real HTTP client
# does - it looks at the host in the URL it was given, and if that host is a
# NAME rather than an address it resolves it, through the same resolver seam the
# check used. Hand it `SafeTarget.addresses[0]` and it records a connection to
# that address and never resolves anything; hand it `SafeTarget.host` and it
# resolves, and under `SequenceResolver` the second answer is loopback.
#
# `connections` is therefore the measurement that matters, and `resolutions` is
# the independent second one: a crawl that connected to the right address for
# the wrong reason still shows a lookup here.


@dataclasses.dataclass
class Reply:
    """One canned response.

    `error` is raised instead of replying, and it is an exception INSTANCE rather
    than a type so a test can name `httpx.ReadTimeout("...")` and
    `ssl.SSLCertVerificationError(...)` in the same table - see
    `tests/crawler/test_fetch.py::FETCH_FAILURE_TABLE`, which exists because a
    fake that raises only the errors somebody thought of hides the ones they did
    not.

    `chunks` replaces `body` with a stream that COUNTS how much of it was
    consumed, which is the only way to tell a reader that stops at a size cap
    from one that reads everything and slices.
    """

    status: int = 200
    body: bytes = b""
    content_type: str | None = "text/html; charset=utf-8"
    content_encoding: str | None = None
    location: str | None = None
    chunks: tuple[bytes, ...] | None = None
    error: BaseException | None = None


class CountingStream(httpx.SyncByteStream):
    """A response body that records how many chunks were actually taken."""

    def __init__(self, chunks):
        self.chunks = tuple(chunks)
        self.taken = 0

    def __iter__(self):
        for chunk in self.chunks:
            self.taken += 1
            yield chunk


class FakeSite(httpx.BaseTransport):
    """An INNER transport for `PinnedAddressTransport`: a website, and a network.

    Keyed by PATH, because the host is not this fake's to decide - the host is
    what the crawler chose to connect to, and recording it is the measurement.
    An unknown path is a 404, which is what a real site does and is what makes
    "the crawler asked for /private" visible as a fetch rather than as a
    KeyError.
    """

    def __init__(self, pages, *, resolver=None):
        self.pages = {path: _as_reply(reply) for path, reply in pages.items()}
        self.resolver = resolver
        self.requests: list[httpx.Request] = []
        self.connections: list[str] = []
        self.resolutions: list[tuple[str, int]] = []
        self.streams: list[CountingStream] = []

    @property
    def last_request(self):
        return self.requests[-1]

    @property
    def paths(self):
        """Every path asked for, in order, so a cap or a robots rule is visible."""
        return [str(request.url.path) for request in self.requests]

    def _connect(self, host, port):
        """What a client does with the host it was given: connect, or resolve first."""
        try:
            ipaddress.ip_address(host)
        except ValueError:
            self.resolutions.append((host, port))
            if self.resolver is None:
                raise socket.gaierror(
                    socket.EAI_NONAME, f"this fake site was given the name {host!r} and has "
                    f"no resolver, so it cannot connect to it"
                )
            answers = self.resolver(host, port)
            return str(answers[0][4][0])
        return host

    def handle_request(self, request):
        self.requests.append(request)
        port = request.url.port
        if port is None:
            port = 443 if request.url.scheme == "https" else 80
        self.connections.append(self._connect(request.url.host, port))

        reply = self.pages.get(str(request.url.path), Reply(status=404, body=b"not found"))
        if reply.error is not None:
            raise reply.error
        headers = {}
        if reply.content_type is not None:
            headers["content-type"] = reply.content_type
        if reply.content_encoding is not None:
            # A server that compresses. The bytes in `body`/`chunks` are what
            # goes on the WIRE, so a test writes them compressed itself - the
            # fake does not compress for it, because the point of these tests is
            # the ratio between the two.
            headers["content-encoding"] = reply.content_encoding
        if reply.location is not None:
            headers["location"] = reply.location
        if reply.chunks is not None:
            stream = CountingStream(reply.chunks)
            self.streams.append(stream)
            return httpx.Response(reply.status, headers=headers, stream=stream)
        # **`stream=` RATHER THAN `content=`, BECAUSE A REAL TRANSPORT HAS NOT
        # READ THE BODY YET.** `httpx.Response(..., content=b"...")` arrives
        # already consumed, with `_content` set - so `iter_bytes()` hands back
        # that attribute and never touches the stream at all, while
        # `iter_raw()` (the only way to see the bytes BEFORE httpx decompresses
        # them, which is what `_read_capped` needs) raises `StreamConsumed`.
        # `httpx.HTTPTransport` returns a stream every time, so a fake that
        # returns content is a fake the production reader cannot be pointed at.
        return httpx.Response(reply.status, headers=headers, stream=httpx.ByteStream(reply.body))


def _as_reply(reply):
    """`str` and `bytes` are the ordinary case; a `Reply` says more."""
    if isinstance(reply, Reply):
        return reply
    if isinstance(reply, str):
        return Reply(body=reply.encode())
    if isinstance(reply, bytes):
        return Reply(body=reply)
    raise TypeError(f"a page is a str, bytes or Reply, not {type(reply).__name__}")


FIXTURE_SITE = pathlib.Path(__file__).resolve().parents[2] / "fixture-site"


def fixture_site_pages():
    """`fixture-site/` off the repository root, as paths a `FakeSite` serves.

    Read from disk rather than inlined so the files a human can open in a browser
    are the same bytes the tests read - a fixture site nobody serves is a fixture
    site that drifts.
    """
    pages = {}
    for path in sorted(FIXTURE_SITE.iterdir()):
        if path.suffix == ".txt":
            pages["/" + path.name] = Reply(body=path.read_bytes(), content_type="text/plain")
        elif path.suffix == ".html":
            pages["/" + path.name] = Reply(body=path.read_bytes())
    pages["/"] = pages["/index.html"]
    return pages
