"""Connecting somebody's Google Ads account, read only.

The merchant goes to Google, agrees, and comes back with a code. That code is
exchanged here for a refresh token: a bearer credential with no expiry that can
read their advertising account until they revoke it. So it is never stored as it
arrives, never logged, never returned in a response and never put in an exception
message. It is encrypted with Fernet under a key the deployment holds, exactly as
the proof of concept did.

Read only is not a setting Google offers on this scope. What makes it read only is
that nothing in this repository calls a mutate method; when that changes, it will
change behind the guardrails the Blueprint sets out, not here.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

#: The one scope this asks for. It is all-or-nothing: Google has no read-only
#: variant of it, which is why the promise lives in our own code.
ADWORDS_SCOPE = "https://www.googleapis.com/auth/adwords"


class AdsConnectionRefused(RuntimeError):
    """Google would not complete the connection. Carries the reason, never a token."""


class VaultUnavailable(RuntimeError):
    """No usable encryption key, so nothing may be stored. Raised before Google is
    called, not after the merchant has already given their consent."""


@dataclass(frozen=True)
class TokenGrant:
    """What Google hands back. Prints as redacted, deliberately."""

    refresh_token: str
    access_token: str
    expires_in: int

    def __repr__(self) -> str:
        return f"TokenGrant(refresh_token=<redacted>, access_token=<redacted>, expires_in={self.expires_in})"


def new_state() -> str:
    """The value that ties a trip to Google back to the browser that started it."""
    return secrets.token_urlsafe(24)


def consent_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    """Where to send the merchant.

    `access_type=offline` with `prompt=consent` is what makes Google return a
    refresh token rather than an hour of access: without it, a merchant who has
    agreed once comes back with nothing to store.
    """
    return (
        AUTH_ENDPOINT
        + "?"
        + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": ADWORDS_SCOPE,
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
                "state": state,
            }
        )
    )


def _refusal(response: httpx.Response) -> AdsConnectionRefused:
    try:
        body = response.json()
        reason = body.get("error_description") or body.get("error") or response.reason_phrase
    except ValueError:
        reason = response.reason_phrase
    return AdsConnectionRefused(f"Google refused the connection: {reason}")


def exchange_code(
    code: str,
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    client: httpx.Client | None = None,
) -> TokenGrant:
    """The code the merchant came back with, for the tokens that read their account."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(20))
    try:
        response = c.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if response.status_code != 200:
            raise _refusal(response)
        body = response.json()
    finally:
        if own:
            c.close()
    refresh = body.get("refresh_token")
    if not refresh:
        # Google returns no refresh token when the merchant has agreed before and
        # the request did not ask to be asked again. Nothing to store, so say so.
        raise AdsConnectionRefused(
            "Google did not return a lasting permission. Disconnect PPCWay in your "
            "Google account and try again."
        )
    return TokenGrant(
        refresh_token=str(refresh),
        access_token=str(body.get("access_token", "")),
        expires_in=int(body.get("expires_in", 0)),
    )


def fresh_access_token(
    refresh_token: str,
    *,
    client_id: str,
    client_secret: str,
    client: httpx.Client | None = None,
) -> str:
    """An hour of access, from the lasting permission."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(20))
    try:
        response = c.post(
            TOKEN_ENDPOINT,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code != 200:
            raise _refusal(response)
        return str(response.json()["access_token"])
    finally:
        if own:
            c.close()


class TokenVault:
    """Encrypts a refresh token at rest, and refuses to exist without a key."""

    def __init__(self, key: str | None) -> None:
        if not key:
            raise VaultUnavailable(
                "refusing to store a Google permission: GOOGLE_OAUTH_TOKEN_KEY is not set"
            )
        try:
            self._fernet = Fernet(key.encode())
        except (ValueError, TypeError):
            raise VaultUnavailable(
                "refusing to store a Google permission: GOOGLE_OAUTH_TOKEN_KEY is not a Fernet key"
            ) from None

    def lock(self, refresh_token: str) -> str:
        return self._fernet.encrypt(refresh_token.encode()).decode()

    def unlock(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise AdsConnectionRefused(
                "That stored permission cannot be read under the current key. "
                "The account has to be connected again."
            ) from None
