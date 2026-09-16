"""**THE ONE LINK THE REST OF THIS PACKAGE HOLDS BY READING RATHER THAN RUNNING.**

Everything in `test_fetch.py` drives `PinnedAddressTransport` over a fake inner
transport, so the last step of obligation 2 - *an IP literal in the URL is what
httpcore actually connects to, with the `Host:` header we wrote and the
certificate verified against the `sni_hostname` extension* - was held by reading
httpcore's source and by a fake standing in for it with the same shape. Task 27's
report named that as its weakest claim and said nothing short of egress could
close it.

**THAT WAS WRONG, AND A LOOPBACK LISTENER IS NOT EGRESS.** No packet leaves the
machine, no name is resolved, nothing is billed and nothing is flaky. What
actually blocked it was the SCOPE of `tests/network_ban.py` - the ban replaces
`socket.socket` itself, so a guarded directory could not create a listener
either - and that scope is now widened, narrowly and by name, by
`network_ban.loopback_only()`. The tests at the bottom of this file are what
holds the widening honest: inside the lift, a connection to anything that is not
this machine, and a DNS lookup of any name, are still refused.

**WHY THIS IS A TRANSPORT TEST AND NOT A `crawl` TEST**, which is worth stating
because it looks like an omission: `assert_safe_url` refuses loopback addresses,
so a `crawl` can never reach a listener on 127.0.0.1 - the SSRF check forbids
exactly this. The `SafeTarget` here is therefore built by hand, below the check,
which is the only altitude at which the question "what does httpcore do with the
address it was given" can be asked at all.
"""
import ast
import pathlib
import socket
import ssl
import threading

import httpx
import pytest

from ppcway.crawler import fetch
from ppcway.crawler.fetch import (
    ACCEPT,
    ACCEPT_ENCODING,
    SAFE_TARGET_EXTENSION,
    SNI_EXTENSION,
    USER_AGENT,
    PinnedAddressTransport,
    authority,
    build_client,
)
from ppcway.crawler.ssrf import SafeTarget
from tests.network_ban import (
    CLOSED_DOORS,
    LOOPBACK_DECISIONS,
    LOOPBACK_ONLY,
    NETWORK_BAN,
    loopback_only,
)

HOST = "alphaplumbing.example"
LOOPBACK = "127.0.0.1"

#: A self-signed certificate naming `alphaplumbing.example` and NOTHING ELSE -
#: no `IP:127.0.0.1` in the SAN, which is the whole point: it is what makes
#: verification succeed when the TLS server name is the merchant's name and fail
#: when it falls back to the address. Generated once with a hundred-year life,
#: used by a listener on this machine, and trusted only by these tests through an
#: `SSLContext` built here. It secures nothing and is not a secret.
TLS = pathlib.Path(__file__).resolve().parent / "loopback_tls"

BODY = b"<html><body>hi</body></html>"
REPLY = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\n\r\n" % len(BODY) + BODY


class Listener:
    """A real HTTP server on 127.0.0.1, in a thread, recording what it was sent.

    Plain or TLS, one connection at a time, and it records the bytes of the
    request line and headers exactly as they arrived - which is the measurement:
    "the `Host:` header we set is what went on the wire" cannot be asked of
    anything that is not a socket.
    """

    def __init__(self, *, tls: bool = False) -> None:
        self.requests: list[bytes] = []
        self.sni: list[str | None] = []
        self.handshake_errors: list[str] = []
        self.context: ssl.SSLContext | None = None
        if tls:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.context.load_cert_chain(TLS / "cert.pem", TLS / "key.pem")
            self.context.sni_callback = self._record_sni
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((LOOPBACK, 0))
        self.socket.listen(4)
        self.socket.settimeout(10.0)
        self.port = self.socket.getsockname()[1]
        self.thread: threading.Thread | None = None
        self.accepted = 0

    def _record_sni(self, connection, name, context):
        """`ssl`'s own callback shape: the server name the client offered, or None."""
        self.sni.append(name)

    def serve(self, connections: int = 1) -> None:
        """Accept exactly `connections` connections, then stop.

        Exactly, not "at least": the number of TCP connections a run makes IS the
        measurement for connection reuse, so a listener that would accept any
        number could not tell one pooled connection from two.
        """
        self.thread = threading.Thread(target=self._serve, args=(connections,), daemon=True)
        self.thread.start()

    def _serve(self, connections: int) -> None:
        for _ in range(connections):
            try:
                raw, _peer = self.socket.accept()
            except OSError:
                return
            self.accepted += 1
            raw.settimeout(10.0)
            connection: socket.socket = raw
            if self.context is not None:
                try:
                    connection = self.context.wrap_socket(raw, server_side=True)
                except OSError as failed:
                    self.handshake_errors.append(repr(failed))
                    raw.close()
                    continue
            with connection:
                # KEEP ALIVE: several requests on one connection, until the peer
                # closes it. A listener that closed after every response would
                # make httpcore's pooled entry dead and hide reuse entirely -
                # which it did, in the first version of this file, and the
                # measurement looked reassuring for the wrong reason.
                while True:
                    received = b""
                    try:
                        while b"\r\n\r\n" not in received:
                            block = connection.recv(4096)
                            if not block:
                                received = b""
                                break
                            received += block
                    except OSError:
                        break
                    if not received:
                        break
                    self.requests.append(received)
                    connection.sendall(REPLY)

    def close(self) -> None:
        if self.thread is not None:
            self.thread.join(10.0)
        self.socket.close()

    def headers(self, index: int = 0) -> list[str]:
        return self.requests[index].decode("ascii", "replace").split("\r\n")


#: A public address the connect-time check accepts, and the reason this file
#: cannot simply point `PinnedAddressTransport` at the listener: it calls
#: `assert_safe_address` on the address it is about to use, and 127.0.0.1 is
#: exactly what that refuses. So the request is BUILT by the shipped transport
#: against a public address and then re-aimed at the listener - see
#: `a_request_the_shipped_transport_built`.
PUBLIC = "93.184.216.34"


class _CapturesTheRequest(httpx.BaseTransport):
    """An inner transport that records what it was handed and refuses to send it.

    `httpx.ConnectError` is one of `FETCH_FAILURES`, so the pinned transport
    treats this as an address that would not connect - which is a path it already
    has - and re-raises it once the addresses run out.
    """

    def __init__(self) -> None:
        self.request: httpx.Request | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.request = request
        raise httpx.ConnectError("captured rather than sent")


def a_target(port: int, *, scheme: str = "http") -> SafeTarget:
    """The judgement `assert_safe_url` would produce for a host on that port."""
    return SafeTarget(
        url=f"{scheme}://{HOST}:{port}/some/path?q=1",
        scheme=scheme,
        host=HOST,
        port=port,
        addresses=(PUBLIC,),
    )


def a_request_the_shipped_transport_built(target: SafeTarget) -> httpx.Request:
    """The request `PinnedAddressTransport` produces, re-aimed at the listener.

    **THE SHAPE IS NOT HAND-WRITTEN HERE, AND THAT IS THE POINT.** The `Host:`
    header, the `sni_hostname` extension and the rewritten URL are all built by
    the code that ships; the only thing this changes afterwards is the ADDRESS in
    the URL, from the public one the check approved to the listener on this
    machine. Which address httpcore then connects to is the question these tests
    exist to ask, so it is the one thing they are allowed to move.
    """
    capture = _CapturesTheRequest()
    with pytest.raises(httpx.ConnectError):
        PinnedAddressTransport(inner=capture).handle_request(
            httpx.Request("GET", target.url, extensions={SAFE_TARGET_EXTENSION: target})
        )
    request = capture.request
    assert request is not None
    assert request.url.host == PUBLIC, "the transport aimed at the address it checked"
    request.url = request.url.copy_with(host=LOOPBACK)
    return request


def test_httpcore_connects_to_the_ip_literal_in_the_url_and_writes_the_host_we_set() -> None:
    """**THE STEP THAT WAS HELD BY READING httpcore's SOURCE, EXECUTED.**

    The real `httpx.HTTPTransport`, handed the request the shipped transport
    built, aimed at a listener on this machine. Three measurements, each a
    different claim: the server accepted a connection at all (so the ADDRESS in
    the URL is what was connected to - the name resolves to nothing, and DNS is
    refused inside the lift anyway); the `Host:` line is the name and port
    `authority()` built rather than the address httpcore connected to; and there
    is exactly ONE of it, because a client that added its own alongside ours
    would be sending a request with two Hosts.
    """
    with loopback_only():
        listener = Listener()
        listener.serve()
        transport = httpx.HTTPTransport(retries=0)
        try:
            target = a_target(listener.port)
            request = a_request_the_shipped_transport_built(target)
            response = transport.handle_request(request)
            response.read()
            response.close()
        finally:
            transport.close()
            listener.close()

    assert response.status_code == 200
    assert request.url.host == LOOPBACK, "the URL handed to httpcore is an ADDRESS"
    lines = listener.headers()
    assert lines[0] == "GET /some/path?q=1 HTTP/1.1"
    hosts = [line for line in lines if line.lower().startswith("host:")]
    assert hosts == [f"Host: {authority(target)}"]
    assert hosts == [f"Host: {HOST}:{listener.port}"]


SNI_CASES = (
    pytest.param(True, id="with-the-sni-extension"),
    pytest.param(False, id="without-it"),
)


@pytest.mark.parametrize("with_extension", SNI_CASES)
def test_the_sni_extension_is_what_makes_the_certificate_be_verified_against_the_name(
    with_extension: bool,
) -> None:
    """**AND A TYPO IN THAT KEY FAILS CLOSED AND LOUDLY, WHICH IS NOT WHAT THIS
    MODULE USED TO CLAIM.**

    Both docstrings said a typo made certificate verification "a check against
    nothing". Executed against real TLS, it does the opposite: httpcore falls
    back to the connection's host, which after the rewrite is an IP literal, and
    Python's `ssl` verifies an IP literal against the certificate's `iPAddress`
    SANs - of which this certificate has none. So every HTTPS fetch fails with
    `CERTIFICATE_VERIFY_FAILED: IP address mismatch`, which is impossible to miss
    in production. It was silent only IN-TREE, because no test drove real TLS.
    This one does, in both directions:

      * with the extension, the handshake carries the merchant's NAME and the
        certificate verifies against it;
      * without it, the connection fails - so the extension is load-bearing, and
        that is now a measurement rather than an argument about httpcore.
    """
    verify = ssl.create_default_context(cafile=str(TLS / "cert.pem"))
    with loopback_only():
        listener = Listener(tls=True)
        listener.serve()
        transport = httpx.HTTPTransport(retries=0, verify=verify)
        try:
            target = a_target(listener.port, scheme="https")
            request = a_request_the_shipped_transport_built(target)
            assert request.extensions[SNI_EXTENSION] == HOST
            if not with_extension:
                del request.extensions[SNI_EXTENSION]

            if with_extension:
                response = transport.handle_request(request)
                response.read()
                response.close()
                assert response.status_code == 200
                assert listener.sni == [HOST], "the NAME reached the TLS handshake"
            else:
                with pytest.raises(httpx.ConnectError) as refused:
                    transport.handle_request(request)
                assert "CERTIFICATE_VERIFY_FAILED" in str(refused.value)
                assert "IP address mismatch" in str(refused.value), (
                    "the fallback verifies the ADDRESS against the certificate and fails - "
                    "loudly, on every HTTPS fetch, rather than skipping verification"
                )
                assert listener.sni == [None]
        finally:
            transport.close()
            listener.close()


def test_the_whole_request_the_crawler_sends_is_what_arrives_on_a_real_wire() -> None:
    """**WHAT A MERCHANT ACTUALLY SEES IN THEIR ACCESS LOG**, read off a socket
    rather than off a fake's recorded `httpx.Request`.

    This one goes through `_send` - the function a crawl uses - so the headers
    are the ones the crawler really sends: the `User-Agent` that says who we are
    and where to complain, the `Accept`, and the `Accept-Encoding` this module
    now chooses for itself. A fake transport can only show what httpx was ASKED
    for; a listener shows what h11 wrote.
    """
    verify = ssl.create_default_context(cafile=str(TLS / "cert.pem"))
    with loopback_only():
        listener = Listener(tls=True)
        listener.serve()
        capture = _CapturesTheRequest()
        client = build_client(timeout_seconds=10.0, inner=capture)
        transport = httpx.HTTPTransport(retries=0, verify=verify)
        try:
            target = a_target(listener.port, scheme="https")
            with pytest.raises(httpx.ConnectError):
                fetch._send(
                    client,
                    target,
                    timeout=10.0,
                    pace=fetch._Pace(1000, now=lambda: 0.0, pause=lambda _seconds: None),
                )
            request = capture.request
            assert request is not None
            request.url = request.url.copy_with(host=LOOPBACK)
            response = transport.handle_request(request)
            response.read()
            response.close()
        finally:
            transport.close()
            client.close()
            listener.close()

    assert response.status_code == 200
    assert listener.sni == [HOST], "the handshake carried the merchant's name"
    lines = listener.headers()
    assert f"Host: {HOST}:{listener.port}" in lines
    assert f"User-Agent: {USER_AGENT}" in lines
    assert f"Accept-Encoding: {ACCEPT_ENCODING}" in lines
    assert f"Accept: {ACCEPT}" in lines


# --------------------------------------------------------------------------
# Two names on one address, and which of them the certificate was checked against
# --------------------------------------------------------------------------
#
# **THE POOL IS KEYED ON THE URL'S ORIGIN, AND THIS TRANSPORT REWRITES THAT TO AN
# ADDRESS.** So `https://a.example/` and `https://b.example/` on one address are
# one pool entry, and the TLS handshake - the certificate check included -
# belongs to whichever of them opened it. `crawl` reaches this with an ordinary
# cross-host redirect. `NO_CONNECTION_REUSE` is the answer; the two tests below
# are the boundary from both sides, because a test that only showed the second
# name being refused would pass just as well if the listener were closing the
# connection itself.

OTHER_NAME = "victim.example"


def two_names_through(transport: httpx.HTTPTransport, listener: Listener) -> list[object]:
    """Fetch as `alphaplumbing.example`, then as `victim.example`, same address."""
    outcomes: list[object] = []
    for name in (HOST, OTHER_NAME):
        target = SafeTarget(
            url=f"https://{name}:{listener.port}/",
            scheme="https",
            host=name,
            port=listener.port,
            addresses=(PUBLIC,),
        )
        try:
            response = transport.handle_request(a_request_the_shipped_transport_built(target))
            response.read()
            response.close()
            outcomes.append(response.status_code)
        except httpx.ConnectError as refused:
            outcomes.append(type(refused).__name__ + ": " + str(refused))
    return outcomes


def test_a_pooled_connection_really_does_carry_only_the_first_names_certificate_check(
) -> None:
    """**THE CONTROL, AND IT IS THE FINDING.** With httpx's default pooling, the
    second name rides the first one's connection: one TCP connection, one
    handshake carrying only the first name, and a `200` for a host this
    certificate does not name. This test asserts the WEAKNESS, on purpose - it is
    what makes `NO_CONNECTION_REUSE` load-bearing rather than decorative, and it
    fails the day httpx changes its pool key."""
    verify = ssl.create_default_context(cafile=str(TLS / "cert.pem"))
    with loopback_only():
        listener = Listener(tls=True)
        listener.serve(1)
        transport = httpx.HTTPTransport(retries=0, verify=verify)
        try:
            outcomes = two_names_through(transport, listener)
        finally:
            transport.close()
            listener.close()

    assert outcomes == [200, 200], "both names were served"
    assert listener.accepted == 1, "on ONE connection"
    assert listener.sni == [HOST], "and only the first name reached a handshake"
    assert [line for line in listener.headers(1) if line.lower().startswith("host:")] == [
        f"Host: {OTHER_NAME}:{listener.port}"
    ], "the second request really was for the other name"


def test_the_second_name_on_one_address_is_verified_rather_than_riding_the_first(
) -> None:
    """The same two requests through the limits `build_client` gives production:
    two connections, two handshakes, and the certificate that does not name
    `victim.example` refuses it."""
    verify = ssl.create_default_context(cafile=str(TLS / "cert.pem"))
    with loopback_only():
        listener = Listener(tls=True)
        listener.serve(2)
        transport = httpx.HTTPTransport(
            retries=0, verify=verify, limits=fetch.NO_CONNECTION_REUSE
        )
        try:
            outcomes = two_names_through(transport, listener)
        finally:
            transport.close()
            listener.close()

    assert outcomes[0] == 200
    assert "CERTIFICATE_VERIFY_FAILED" in str(outcomes[1])
    assert "Hostname mismatch" in str(outcomes[1])
    assert listener.accepted == 2
    assert listener.sni == [HOST, OTHER_NAME], "each name got its own handshake"


def test_build_client_asks_for_no_connection_reuse() -> None:
    """**THE STRUCTURAL HALF, BECAUSE THE BEHAVIOURAL ONE CANNOT USE THE REAL
    TRANSPORT.** The transport `build_client` builds verifies against certifi, so
    a test that drove IT at a self-signed listener would fail on both names and
    prove nothing. This reads the source instead and asserts the constant the
    test above measured is the one production passes - the pair is the pin, not
    either half."""
    tree = ast.parse(pathlib.Path(fetch.__file__).read_text())
    built = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "HTTPTransport"
    ]
    assert len(built) == 1, "one place builds the transport that opens a socket"
    limits = [
        keyword.value.id
        for keyword in built[0].keywords
        if keyword.arg == "limits" and isinstance(keyword.value, ast.Name)
    ]
    assert limits == ["NO_CONNECTION_REUSE"]
    assert fetch.NO_CONNECTION_REUSE.max_keepalive_connections == 0


# --------------------------------------------------------------------------
# The lift itself, which is a widening of a security control and is pinned as one
# --------------------------------------------------------------------------


def test_inside_the_lift_a_connection_to_anything_but_this_machine_is_still_refused() -> None:
    """**THE WIDENING IS "LOOPBACK", NOT "SOCKETS".** A test that reaches for a
    public address inside the lift gets a different refusal, with its own
    sentence, so neither message can pass for the other."""
    with loopback_only():
        with pytest.raises(RuntimeError, match=LOOPBACK_ONLY):
            socket.create_connection(("93.184.216.34", 80), 1.0)
        opened = socket.socket()
        try:
            with pytest.raises(RuntimeError, match=LOOPBACK_ONLY):
                opened.connect(("93.184.216.34", 80))
        finally:
            opened.close()


def test_inside_the_lift_dns_is_still_egress_and_still_closed() -> None:
    """The route that never touches a socket at all. A numeric loopback lookup is
    allowed because `socket.create_connection` makes one internally and it asks
    nobody; a NAME is refused, `localhost` excepted."""
    with loopback_only():
        with pytest.raises(RuntimeError, match=LOOPBACK_ONLY):
            socket.getaddrinfo("alphaplumbing.example", 443)
        with pytest.raises(RuntimeError, match=LOOPBACK_ONLY):
            socket.gethostbyname("alphaplumbing.example")
        assert socket.getaddrinfo(LOOPBACK, 80)


class _AlreadyConnectedElsewhere:
    """A stand-in for a socket that was connected BEFORE the ban was armed.

    **THE INSTRUMENT CHANGED; THE PROPERTY DID NOT.** This case used to be built
    with a `socket.socketpair()`, whose peer name is the empty string - and the
    lift refused the write, which looked like the peer check working. It was
    ALSO refusing every write a unix-domain pair makes, and `anyio`'s blocking
    portal (which `fastapi.testclient.TestClient` uses for every request) wakes
    its event loop with exactly such a write. So the first guarded directory to
    drive an ASGI app - `tests/api` - HUNG: the refusal was raised inside the
    portal thread and the main thread waited for a future that could never
    complete. `network_ban.ON_THIS_MACHINE` carries the measurement.

    A unix pair therefore no longer proves anything about the peer check, and
    the case the check exists for cannot be built from a real socket without
    egress: `connect` is guarded, so the only socket with a non-loopback peer is
    one connected before the ban, and reaching for one of those means leaving the
    machine. What the door actually reads is `getpeername()`, so this object
    provides one. It is not a substitute for a socket in the test - the DOOR is
    the real, patched `socket.socket.send`, called unbound - it is a substitute
    for a peer.
    """

    def getpeername(self) -> tuple[str, int]:
        return ("93.184.216.34", 443)


def test_inside_the_lift_a_write_on_a_socket_whose_peer_is_not_loopback_is_refused() -> None:
    """**THE DOOR THE FIRST VERSION OF THIS FILE LEFT UNPINNED, AND THE BATTERY
    FOUND IT.** Making `sendall` a straight pass-through inside the lift survived
    the whole suite: `connect` is guarded, so no test could reach a socket whose
    peer is NOT loopback - the only way in is a connection opened before the ban
    was armed, and reaching for one of those needs egress.

    See `_AlreadyConnectedElsewhere` for why the instrument is what it is.

    **EVERY PEER-CHECKED DOOR IS DRIVEN, AND THE SET IS DERIVED.** They are
    separate entries in `LOOPBACK_DECISIONS`, so a pass-through can be introduced
    on any single one; and they are spread across two owners (`write` is
    `ssl.SSLSocket`'s and does not exist on `socket.socket` at all), so a
    hand-written list would either miss one or name one that is not there. The
    set comes off the decision table, keyed on the decision `send` uses.
    """
    peer_check = LOOPBACK_DECISIONS["send"]
    doors = [(owner, name) for owner, name in CLOSED_DOORS
             if LOOPBACK_DECISIONS.get(name) is peer_check]
    assert len(doors) >= 6, (
        f"only {len(doors)} peer-checked doors found; the walk is not seeing the table"
    )

    remote = _AlreadyConnectedElsewhere()
    with loopback_only():
        for owner, name in doors:
            with pytest.raises(RuntimeError, match=LOOPBACK_ONLY):
                getattr(owner, name)(remote, b"ping")


def test_inside_the_lift_a_unix_pair_may_be_written_to() -> None:
    """The other side of the decision above, and the reason it changed.

    A `socketpair` cannot leave this machine by construction - it is AF_UNIX and
    has no address at all - so refusing its writes bought nothing and cost every
    event loop in a guarded directory. `tests/api/test_ban.py` asserts the same
    thing through a real ASGI request, which is the case that found it.
    """
    with loopback_only():
        # Made INSIDE the lift: this directory runs under the full ban, where
        # `socketpair` is closed like every other way of making a socket.
        here, there = socket.socketpair()
        try:
            assert here.getpeername() == "", (
                "an unnamed pair: no address, in either direction")
            here.sendall(b"ping")
            assert there.recv(4) == b"ping"
        finally:
            here.close()
            there.close()


def test_the_ban_is_exactly_as_it_was_after_the_lift_closes() -> None:
    """Including after a test raises inside one, which is why the restore is in a
    `finally` and why this asserts the ORIGINAL sentence comes back."""
    with pytest.raises(ValueError, match="deliberate"), loopback_only():
        raise ValueError("a deliberate failure inside the lift")
    with pytest.raises(RuntimeError, match=NETWORK_BAN):
        socket.socket()
    with pytest.raises(RuntimeError, match=NETWORK_BAN):
        socket.getaddrinfo(LOOPBACK, 80)


def test_the_loopback_lift_has_a_decision_for_every_door_the_ban_closes() -> None:
    """**COMPLETENESS, THE SAME WAY THE DOOR TABLE ITSELF HAS IT.** A door with no
    decision recorded is REFUSED inside the lift rather than opened, so a new one
    arriving in a future Python fails closed - and this fails BY NAME, so whoever
    meets it decides what it should be instead of finding out later."""
    closed = {name for _owner, name in CLOSED_DOORS}
    assert closed - set(LOOPBACK_DECISIONS) == set()
    assert set(LOOPBACK_DECISIONS) - closed == set(), (
        "a decision about a door the ban does not close is a decision about nothing"
    )
    assert len(closed) == 18, "the 25 doors, deduplicated by name across the three owners"
