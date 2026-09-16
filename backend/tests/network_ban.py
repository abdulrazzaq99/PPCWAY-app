"""**THE SOCKET BAN, AS A MECHANISM, SHARED BY EVERY DIRECTORY THAT NEEDS IT.**

Task 24 built this for `tests/llm/`, where a forgotten fake transport would
reach the real Anthropic API. Task 26 needs the identical guarantee for
`tests/crawler/`, where `ppcway.crawler.ssrf.assert_safe_url`'s DEFAULT resolver
is `socket.getaddrinfo` - so a test that omits `resolver=` makes a real DNS
query, which is egress in exactly the sense this ban exists to stop, and which
would silently pass on a developer machine and fail in CI as "a network blip".

It lives here rather than being copied because a second copy is a second thing
to keep true. What each `conftest.py` still owns is the pair of HOOKS - pytest
finds those by name in the conftest module - and the DIRECTORY they are scoped
to. Everything below is shared, so the two directories cannot end up with
different doors closed.

**WHERE THE BAN IS: at the socket, at every door DERIVED from the socket
modules rather than listed.** Three groups, one rule (see `_EGRESS_SHAPE`
below): how a connection is *made* (the socket class itself, `create_*`,
`socketpair`, and the name resolvers, since DNS is egress too); how a socket
made EARLIER is connected (`connect`, `connect_ex`); and how an
ALREADY-CONNECTED socket is used (`send`, `sendall`, `sendto`, `sendmsg`,
`sendfile`, `write`). That third group is not decoration: `httpx` pools
connections per client, so a fixture that completed one real request before the
ban was armed would leave a warm connection that a later request reuses without
touching `socket.*` at all. Closing only the constructors leaves that route open
- measured over loopback, not argued.

**WHEN THE BAN IS ARMED, which is the half the first version got wrong.** It
used to be a function-scoped autouse fixture, and a function-scoped fixture is
one of the LAST things pytest runs. Two whole classes of code ran before it:

  * **module import**, which happens during collection, so a module in a
    guarded directory could open a socket at import time - a client constructed
    *and connected* at import time being the exact scenario this ban exists for;
  * **every higher-scoped fixture**, since pytest builds session-, package-,
    module- and class-scoped fixtures before function-scoped ones.

Both are executed probes, not hypotheticals: they escaped, and
`test_the_ban_is_already_in_force_when_this_module_is_imported` and
`test_the_ban_is_already_in_force_when_a_session_scoped_fixture_runs` in
`tests/llm/test_anthropic_provider.py` now fail if either reopens.

So the ban is armed by two HOOK WRAPPERS instead, which pytest calls around the
outermost thing it does with a node:

  * `pytest_make_collect_report` wraps collection of any node in the guarded
    directory, and collection is what imports the module;
  * `pytest_runtest_protocol` wraps the WHOLE of a test - setup, call and
    teardown - and every fixture of every scope is built inside setup.

**AND BOTH HOOKS CHECK THE PATH THEMSELVES**, via `scoped_to` below, because
pytest's two dispatch rules differ: `pytest_make_collect_report` goes through
the collector's own conftest chain and so is already scoped to its directory,
but `pytest_runtest_protocol` goes through `item.config.hook`, the global one,
and fires for every test in the session. `tests/db` and `tests/gateway` need
real sockets to reach Postgres and Redis, so an unscoped ban is not a stricter
ban, it is a broken suite - which is what the first version of these hooks was,
and what `test_the_ban_does_not_leak_out_of_this_package` now runs a whole
pytest in a subprocess to catch.

**WHAT IT DOES NOT COVER, disclosed rather than implied.** Four things, and the
first is the only one that was disclosed before:

  1. **A subprocess.** The patch is in this process. `tests/llm/test_stub.py`
     spawns interpreters to check determinism under other hash seeds; those
     children run stub code, which has no client and no key, but nothing here
     would stop them if that changed.
  2. **A socket that was already open AND already connected before the ban was
     armed** can still be *closed* and *read* (`recv`) inside the window. Every
     `send`-shaped method on `socket.socket` and on `ssl.SSLSocket` is patched,
     so a request cannot be written on it - stated that way on purpose, because
     the first version of this paragraph said "the write side is patched" and
     that was FALSE: the door list was hand-written and `sendmsg` and `sendfile`
     were missing from it, and a reviewer put bytes through `sendmsg` on a warm
     connection in a real pytest run. The list is derived now, so the sentence
     is true of whatever the class actually has rather than of what somebody
     remembered.

     What is still open on such a socket, and is NOT reachable by patching in
     the `socket`/`ssl` layer at all: `os.write(sock.fileno(), ...)`, and the C
     base class underneath - `_socket.socket.send(sock, ...)`, and
     `socket.SocketType`, which IS `_socket.socket` rather than the Python
     subclass this file patches. A test doing any of those is writing code whose
     only purpose is to get round the ban.
  3. **Anything pytest does outside the two windows above**: `pytest_configure`,
     `pytest_sessionstart`/`sessionfinish`, and the TEARDOWN of a
     session-scoped fixture, which runs at the end of the session rather than
     inside any one test's protocol.
  4. **A test elsewhere in the tree**, by construction - the ban is
     per-directory. That is what
     `test_every_test_module_that_can_reach_a_guarded_module_runs_under_this_ban`
     exists to catch, and it follows the IMPORT GRAPH rather than a list of
     names. It is parametrised over every module whose default reaches the
     network - the Anthropic provider, and `ppcway.crawler.ssrf`, whose resolver
     defaults to `socket.getaddrinfo` - because a walk keyed to one of them says
     nothing about the other's directory.

**KNOWN OVER-BLOCK: `asyncio` does not work under the UNLIFTED ban.** `asyncio`'s
selector loop builds its self-pipe with `socket.socketpair()`, which calls the
module-global `socket(...)` this file replaces, and `pyproject.toml` sets
`asyncio_mode = "auto"` - so any `async def test_` added under a guarded
directory errors while the event loop is being created, before it has attempted
any I/O at all. It fails CLOSED (async HTTP really is blocked), but the message
would point at the wrong thing, so the message says so itself.

**INSIDE `loopback_only()` IT DOES WORK, AND THAT TOOK A FIX RATHER THAN BEING
FREE.** The lift opens `socketpair` explicitly, but until `ON_THIS_MACHINE` was
added it then refused every WRITE on the pair - so an event loop could be built
and never woken, and the symptom was a hang with no error. See that constant.
"""
import contextlib
import ipaddress
import pathlib
import socket
import ssl

NETWORK_BAN = "ppcway test suite: a test tried to open a socket"

#: The refusal from inside `loopback_only()`. A different sentence from
#: `NETWORK_BAN` on purpose: "the ban is closed" and "the lift is open and this
#: was still not loopback" are different facts, and a test that greps for one
#: must not pass on the other.
LOOPBACK_ONLY = "ppcway test suite: inside a loopback-only lift, a test tried to reach"

# **THE DOORS ARE DERIVED FROM THE MODULES THEMSELVES, NOT LISTED.** The first
# version of this listed fourteen by hand, with a test pinning those fourteen
# and nothing asking whether fourteen was all of them - and it was not:
# `sendmsg` and `sendfile` were missing on BOTH owners, and a reviewer drove real
# bytes through `sendmsg` in a real pytest run, in the exact scenario the send
# doors were added to close. That is the fourth time a hand-maintained list has
# failed on this project, and the first time inside the fix for the previous one.
#
# So the rule is written once and applied to all three owners:
#
#   * anything that IS the socket class - how a socket is made;
#   * anything whose name begins `send` or `connect`, or is exactly `write` -
#     how bytes leave one, whether it was made before the ban or during it;
#   * on the module only, `create_*`, `socketpair` and every name resolver
#     (`getaddrinfo`, `gethostby*`, `getnameinfo`) - DNS is egress too, and it is
#     the one route that never touches a socket object at all.
#
# `ssl.SSLSocket` is walked separately because it OVERRIDES nearly every one of
# these rather than inheriting them (`sendmsg` included - which is precisely the
# door the hand-written list forgot), so patching `socket.socket` alone would
# leave every HTTPS write open, and every request the SDK makes is HTTPS.
#
# Deriving fixes the contents. `test_the_ban_closes_every_door_it_says_it_closes`
# adds the other half - the COMPLETENESS half this table did not have - by
# asserting that every public callable on these owners which is NOT a door is one
# of a pinned set reviewed as unable to put bytes on a connection. A method
# arriving in a future Python that does not match the shape above therefore fails
# the suite instead of arriving silently.
_EGRESS_SHAPE = (
    "send",
    "connect",
    "create_",
    "getaddrinfo",
    "gethostby",
    "getnameinfo",
    "socketpair",
)


def _doors(owner: object) -> tuple[tuple[object, str], ...]:
    found = []
    for name in dir(owner):
        if name.startswith("_"):
            continue
        try:
            value = getattr(owner, name)
        except AttributeError:  # pragma: no cover - a descriptor that refuses
            continue
        if value is socket.socket or (
            callable(value) and (name.startswith(_EGRESS_SHAPE) or name == "write")
        ):
            found.append((owner, name))
    return tuple(found)


#: Captured here, at first import of this module, because arming REBINDS
#: `socket.socket` - so by the time any test runs, `socket.socket` is the refuser
#: and is no longer a handle on the class the doors belong to. Nothing that needs
#: the real owners may look them up through the module.
DOOR_OWNERS: tuple[object, ...] = (socket, socket.socket, ssl.SSLSocket)

CLOSED_DOORS: tuple[tuple[object, str], ...] = tuple(
    door for owner in DOOR_OWNERS for door in _doors(owner)
)


def _refuse(*args: object, **kwargs: object) -> None:
    raise RuntimeError(
        f"{NETWORK_BAN}. Every test in this package runs with the network closed - see "
        f"tests/network_ban.py. If this fired somewhere that is not making a request, "
        f"the likely cause is an `async def` test: asyncio builds its event loop's "
        f"self-pipe with socket.socketpair(), which goes through the same patched "
        f"socket(), so the loop cannot be created here at all."
    )


_depth = 0
_restore: list[tuple[object, str, object, bool]] = []


def _arm() -> None:
    """Close every door, remembering whether each was defined on its owner.

    `socket.socket.send` and friends are INHERITED from the C base class, so
    setting them defines a new attribute that has to be deleted rather than
    restored; `ssl.SSLSocket`'s are its own and have to be put back.
    """
    for owner, name in CLOSED_DOORS:
        owned = name in vars(owner)
        _restore.append((owner, name, getattr(owner, name), owned))
        setattr(owner, name, _refuse)


def _disarm() -> None:
    while _restore:
        owner, name, original, owned = _restore.pop()
        if owned:
            setattr(owner, name, original)
        else:
            delattr(owner, name)


@contextlib.contextmanager
def banned():
    """The ban, for the duration of a block. Reentrant, so a window that nests
    inside another (a module collected inside a package collection, or a
    guarded directory's test running inside another's collection) does not lift
    the ban when the inner one ends.

    The depth counter is shared across every directory that installs the ban,
    which is the point of sharing this module: two independent counters could
    each think they were outermost and one could disarm while the other was
    still open."""
    global _depth
    if _depth == 0:
        _arm()
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1
        if _depth == 0:
            _disarm()


# --------------------------------------------------------------------------
# The one narrow lift: a listener on this machine, and nothing else
# --------------------------------------------------------------------------
#
# **WHY THIS EXISTS, AND WHY IT IS NOT A HOLE IN THE BAN.** Task 27's crawler
# rests on one step nothing in-tree executed: "an IP literal in the URL is what
# httpcore connects to, with the `Host:` header we wrote and the certificate
# verified against the `sni_hostname` extension". The task disclosed that as the
# weakest link and said only egress could close it. That was wrong: a listener on
# 127.0.0.1 closes it, and A LOOPBACK LISTENER IS NOT EGRESS - no packet leaves
# the machine, no name is resolved, nothing is billed and nothing is flaky.
#
# What blocked it was this file's SCOPE rather than its purpose: the ban replaces
# `socket.socket` itself, so a guarded directory cannot create a listener either.
# So the scope is widened here, deliberately and by name:
#
#   * the doors that MAKE a socket (`socket`, `socketpair`) open, because a
#     socket that is not connected to anything has sent nothing;
#   * every door that TAKES an address (`connect`, `connect_ex`,
#     `create_connection`, `create_server`, `sendto`) checks that address, and
#     every door that writes on an ALREADY-CONNECTED socket (`send`, `sendall`,
#     `sendmsg`, `sendfile`, `write`, `send_fds`) checks the socket's PEER - so a
#     connection opened before the ban was armed cannot be written to inside the
#     lift either, which is the one thing a naive "restore the originals" version
#     would have quietly reopened;
#   * the NAME RESOLVERS stay closed for everything but a loopback literal and
#     `localhost`. DNS is egress; `create_connection` is allowed to look up
#     `127.0.0.1` because it does that internally and a numeric lookup asks
#     nobody.
#
# A door that is not in the table below is REFUSED inside the lift, so a new one
# arriving in a future Python is closed rather than open;
# `test_the_loopback_lift_has_a_decision_for_every_door_the_ban_closes` is the
# other half of that, and fails by name.


def _host_of(value: object) -> str | None:
    """The host out of whatever shape a socket API was handed one in."""
    if isinstance(value, (tuple, list)) and value:
        value = value[0]
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("ascii")
        except UnicodeDecodeError:
            return None
    return value if isinstance(value, str) else None


#: What a decision returns for a socket that CANNOT leave this machine, because
#: it is not a network socket at all.
#:
#: **THE LIFT ALLOWED MAKING A SOCKETPAIR AND REFUSED WRITING ON THE PAIR IT HAD
#: JUST MADE, AND THOSE TWO DECISIONS CONTRADICTED EACH OTHER.** `socketpair` is
#: `_ALLOWED` above on the argument that a socket connected to nothing has sent
#: nothing - but a socketpair IS connected, to its own twin, over AF_UNIX, and
#: `_the_peer` asked `getpeername()`, which for an unnamed AF_UNIX socket is the
#: empty string. Empty string is not a loopback address, so every write was
#: refused.
#:
#: MEASURED, and the symptom was a HANG rather than a failure: `anyio`'s blocking
#: portal - which `fastapi.testclient.TestClient` uses for every request - wakes
#: its event loop by writing on exactly such a pair, from inside the loop thread.
#: The refusal was raised there, the main thread went on waiting for a future
#: that could never complete, and the suite stopped with no error at all. Found
#: by `tests/api`, the first guarded directory to drive an ASGI app.
#:
#: A named value rather than "127.0.0.1", because a refusal message that quoted a
#: loopback address for a socket that has no address would be untrue about the
#: thing it is describing.
ON_THIS_MACHINE = "<a unix-domain socket, which has no network peer>"

#: `AF_UNIX` does not exist on every platform, so it is looked up rather than
#: named. `None` is compared against nothing, which is the safe direction.
_AF_UNIX = getattr(socket, "AF_UNIX", None)


def _is_loopback(host: str | None) -> bool:
    """Only an address on this machine, or the one name that always means one."""
    if host is None:
        return False
    if host == ON_THIS_MACHINE:
        return True
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _argument(index: int):
    def pick(args: tuple[object, ...], _kwargs: dict[str, object]) -> str | None:
        return _host_of(args[index]) if len(args) > index else None

    return pick


def _the_last_argument(args: tuple[object, ...], _kwargs: dict[str, object]) -> str | None:
    return _host_of(args[-1]) if args else None


def _the_peer(args: tuple[object, ...], _kwargs: dict[str, object]) -> str | None:
    """Where an already-connected socket would put these bytes.

    An AF_UNIX socket is answered BEFORE `getpeername()` is asked, because for an
    unnamed one - which is what `socket.socketpair()` returns - the answer is the
    empty string and there is nothing to judge. See `ON_THIS_MACHINE` for the
    measurement that put this here.
    """
    sock = args[0] if args else None
    if _AF_UNIX is not None and getattr(sock, "family", None) == _AF_UNIX:
        return ON_THIS_MACHINE
    try:
        return _host_of(sock.getpeername())  # type: ignore[union-attr]
    except (AttributeError, IndexError, OSError):
        return None


def _nothing(_args: tuple[object, ...], _kwargs: dict[str, object]) -> str | None:
    """No decision was recorded for this door, so it stays shut."""
    return None


_ALLOWED = "a socket that is connected to nothing has sent nothing"

#: One decision per door, by name. The three owners share no door name, so one
#: table serves all of them.
LOOPBACK_DECISIONS: dict[str, object] = {
    "socket": _ALLOWED,
    "socketpair": _ALLOWED,
    "create_connection": _argument(0),
    "create_server": _argument(0),
    "connect": _argument(1),
    "connect_ex": _argument(1),
    "sendto": _the_last_argument,
    "send": _the_peer,
    "sendall": _the_peer,
    "sendmsg": _the_peer,
    "sendfile": _the_peer,
    "send_fds": _the_peer,
    "write": _the_peer,
    "getaddrinfo": _argument(0),
    "gethostbyname": _argument(0),
    "gethostbyname_ex": _argument(0),
    "gethostbyaddr": _argument(0),
    "getnameinfo": _argument(0),
}

#: Captured at import for the same reason `CLOSED_DOORS` is: arming REBINDS these
#: names, so by the time a lift runs the module no longer holds the real ones.
ORIGINAL_DOORS: tuple[object, ...] = tuple(
    getattr(owner, name) for owner, name in CLOSED_DOORS
)


def _only_loopback(door, pick, name):  # type: ignore[no-untyped-def]
    def guarded(*args: object, **kwargs: object) -> object:
        host = pick(args, kwargs)
        if not _is_loopback(host):
            raise RuntimeError(
                f"{LOOPBACK_ONLY} {host!r} through {name}(). The lift is for a listener on "
                f"this machine; anything else is egress and stays closed."
            )
        return door(*args, **kwargs)

    return guarded


@contextlib.contextmanager
def loopback_only():
    """The network ban, lifted for 127.0.0.1 and nothing else, for one block.

    Nests inside `banned()` rather than replacing it: it saves whatever is on
    each door (the refuser, normally), installs the guarded original, and puts
    the refuser back afterwards - so the ban is exactly as it was on the way out,
    including for a test that raises inside the block.
    """
    saved = [(owner, name, getattr(owner, name)) for owner, name in CLOSED_DOORS]
    try:
        for (owner, name), door in zip(CLOSED_DOORS, ORIGINAL_DOORS, strict=True):
            decision = LOOPBACK_DECISIONS.get(name, _nothing)
            setattr(
                owner,
                name,
                door if decision is _ALLOWED else _only_loopback(door, decision, name),
            )
        yield
    finally:
        for owner, name, original in saved:
            setattr(owner, name, original)


def scoped_to(directory: pathlib.Path):
    """A predicate for "is this node inside `directory`", for the hooks below.

    **THE HOOKS NEED THIS AND IT IS NOT OPTIONAL.** Two of pytest's own dispatch
    rules differ, and the difference is a leak rather than a nuisance:
    `pytest_make_collect_report` is called through the COLLECTOR's conftest
    chain (so a conftest sees only nodes under it), but
    `pytest_runtest_protocol` is called through `item.config.hook` - the global
    one - so a wrapper declared in one directory fires for EVERY test in the
    session, `tests/db` and `tests/gateway` included, and those need real
    sockets to reach Postgres and Redis. Without this guard the first version of
    these hooks banned the network for the whole suite; it was caught by running
    the probes rather than by reading the code.
    """
    root = directory.resolve()

    def is_ours(path: object) -> bool:
        if path is None:
            # `pytest_runtest_protocol` is dispatched globally, so this runs for
            # EVERY item in the session and has to be total. A node with no path
            # is not in this directory, so it is not ours - and a `TypeError`
            # raised here would be a TypeError in a global hook.
            return False
        resolved = pathlib.Path(str(path)).resolve()
        return resolved == root or root in resolved.parents

    return is_ours
