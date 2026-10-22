"""Who may come in, while PPCWay is open to some people and not to everybody.

The free audit is for anybody. It is the whole reason the site exists before
anybody signs up, it asks for nothing, and none of it is gated here.

What sits behind signing in is not ready for strangers yet, so that door is on
the latch rather than open. `open_to` is the latch:

- **empty** — open to everybody. That is how it runs locally, how every test
  runs, and how it will ship on the day PPCWay opens properly. This module then
  does nothing at all.
- **a list** — only those addresses may sign in or make an account, plus
  anybody already invited by somebody who is inside. The people in a business
  should not each have to be named here by hand.

A whole domain can be named as `@example.com`, which is how an agency or a
client's staff are let in without listing every person.
"""

from __future__ import annotations

#: What a refused person is told. No hint that the list exists, because the
#: list is nobody's business, and no apology, because nothing has gone wrong.
NOT_YET = (
    "PPCWay is not open to everybody yet. The free website audit is open now "
    "and needs no account, and we will let you in as soon as we can."
)


def guests(open_to: str) -> tuple[set[str], set[str]]:
    """The addresses and the whole domains named in the setting."""
    addresses: set[str] = set()
    domains: set[str] = set()
    for raw in open_to.replace(";", ",").split(","):
        one = raw.strip().lower()
        if not one:
            continue
        if one.startswith("@"):
            domains.add(one[1:])
        elif "@" in one:
            addresses.add(one)
        else:
            # A bare domain reads as a domain; nobody writes an address
            # without an @, so this is what they meant.
            domains.add(one)
    return addresses, domains


def open_to_everybody(open_to: str) -> bool:
    """True when nothing is named, which is the open state."""
    addresses, domains = guests(open_to)
    return not addresses and not domains


def may_come_in(email: str, *, open_to: str, invited: bool = False) -> bool:
    """Whether this address may sign in or make an account."""
    if open_to_everybody(open_to):
        return True
    if invited:
        return True
    address = email.strip().lower()
    if not address:
        return False
    addresses, domains = guests(open_to)
    if address in addresses:
        return True
    _, _, domain = address.partition("@")
    return bool(domain) and domain in domains
