"""Who is signing in, according to Google.

Google's sign-in button hands the browser a signed token saying who the person is.
The browser posts it here once; this module checks the signature against Google's
published keys, that the token was issued for our own client, and that it has not
expired. Nothing is trusted because the browser said so.

`google-auth` does the checking. It normally reaches Google through `requests`,
which this project does not use, so it is given a small httpx adapter instead of a
second HTTP library.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

import httpx
from google.auth.transport import Request as GoogleRequest
from google.auth.transport import Response as GoogleResponse
from google.oauth2 import id_token

#: How long a signed-in session lasts before the person signs in again.
SESSION_DAYS = 30


class SignInRefused(RuntimeError):
    """The token was not something Google signed for us. Says why, never the token."""


@dataclass(frozen=True)
class GoogleIdentity:
    """The few claims we keep: who they are and how to greet them."""

    sub: str
    email: str
    name: str
    picture: str
    email_verified: bool


class _Reply(GoogleResponse):
    def __init__(self, reply: httpx.Response) -> None:
        self._reply = reply

    @property
    def status(self) -> int:
        return self._reply.status_code

    @property
    def headers(self) -> dict[str, str]:
        return dict(self._reply.headers)

    @property
    def data(self) -> bytes:
        return self._reply.content


class HttpxRequest(GoogleRequest):
    """What google-auth fetches Google's signing keys with, on our HTTP client."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=httpx.Timeout(15))

    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: object,
    ) -> GoogleResponse:
        reply = self._client.request(
            method, url, content=body, headers=headers, timeout=timeout or 15
        )
        return _Reply(reply)


def verify_google_token(
    credential: str, *, client_id: str, request: GoogleRequest | None = None
) -> GoogleIdentity:
    """The person Google says signed in, or a refusal naming the reason.

    An unverified email address is refused: Google issues those for accounts that
    never proved the address, and an account here is identified by its address.
    """
    try:
        # google-auth ships no type information, so this one call is untyped.
        claims: dict[str, object] = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
            credential, request or HttpxRequest(), audience=client_id
        )
    except ValueError as exc:
        raise SignInRefused(f"Google did not accept that sign-in: {exc}") from None

    if not claims.get("email"):
        raise SignInRefused("That Google account did not share an email address.")
    if not claims.get("email_verified"):
        raise SignInRefused("That Google account has not confirmed its email address.")

    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=str(claims["email"]).lower(),
        name=str(claims.get("name") or ""),
        picture=str(claims.get("picture") or ""),
        email_verified=True,
    )


def new_session_token() -> str:
    """The cookie value. Random, and never derived from anything about the person."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """What the database holds: a hash, so a stolen table is not a set of keys."""
    return hashlib.sha256(token.encode()).hexdigest()
