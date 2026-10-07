"""Connecting a Google Ads account: the trip out, the exchange back, and the vault."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet

from ppcway.ads.oauth import (
    ADWORDS_SCOPE,
    AdsConnectionRefused,
    TokenGrant,
    TokenVault,
    VaultUnavailable,
    consent_url,
    exchange_code,
    fresh_access_token,
    new_state,
)


def test_the_consent_url_asks_for_a_lasting_permission() -> None:
    url = consent_url(client_id="cid", redirect_uri="https://ppcway.test/back", state="s1")
    asked = parse_qs(urlsplit(url).query)
    assert asked["scope"] == [ADWORDS_SCOPE]
    # Without these two Google returns an hour of access and nothing to store.
    assert asked["access_type"] == ["offline"]
    assert asked["prompt"] == ["consent"]
    assert asked["state"] == ["s1"] and asked["redirect_uri"] == ["https://ppcway.test/back"]


def test_every_trip_gets_its_own_state() -> None:
    assert new_state() != new_state()
    assert len(new_state()) >= 24


def test_the_code_becomes_a_refresh_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        sent = dict(pair.split("=", 1) for pair in request.content.decode().split("&"))
        assert sent["grant_type"] == "authorization_code" and sent["code"] == "abc123"
        return httpx.Response(
            200, json={"refresh_token": "r-1", "access_token": "a-1", "expires_in": 3599}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        grant = exchange_code(
            "abc123",
            client_id="cid",
            client_secret="sec",
            redirect_uri="https://x/back",
            client=client,
        )
    assert grant.refresh_token == "r-1" and grant.expires_in == 3599


def test_a_grant_never_prints_its_tokens() -> None:
    shown = repr(TokenGrant(refresh_token="r-secret", access_token="a-secret", expires_in=60))
    assert "r-secret" not in shown and "a-secret" not in shown and "redacted" in shown


def test_an_agreement_with_nothing_to_store_is_refused() -> None:
    """Google sends no refresh token to somebody who already agreed once."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "a-1", "expires_in": 3599})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(AdsConnectionRefused, match="lasting permission"),
    ):
        exchange_code(
            "abc", client_id="c", client_secret="s", redirect_uri="https://x", client=client
        )


def test_googles_refusal_is_passed_on_in_its_own_words() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error_description": "redirect_uri_mismatch"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(AdsConnectionRefused, match="redirect_uri_mismatch"),
    ):
        exchange_code(
            "abc", client_id="c", client_secret="s", redirect_uri="https://x", client=client
        )


def test_a_lasting_permission_buys_an_hour_of_access() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        sent = dict(pair.split("=", 1) for pair in request.content.decode().split("&"))
        assert sent["grant_type"] == "refresh_token"
        return httpx.Response(200, json={"access_token": "a-2"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert fresh_access_token("r-1", client_id="c", client_secret="s", client=client) == "a-2"


def test_the_vault_locks_and_unlocks_the_same_token() -> None:
    vault = TokenVault(Fernet.generate_key().decode())
    locked = vault.lock("r-secret")
    assert "r-secret" not in locked
    assert vault.unlock(locked) == "r-secret"


def test_a_token_locked_under_another_key_cannot_be_read() -> None:
    locked = TokenVault(Fernet.generate_key().decode()).lock("r-secret")
    with pytest.raises(AdsConnectionRefused, match="connected again"):
        TokenVault(Fernet.generate_key().decode()).unlock(locked)


@pytest.mark.parametrize("key", [None, "", "not-a-fernet-key"])
def test_without_a_usable_key_nothing_is_stored_at_all(key: str | None) -> None:
    """Refused here, before the merchant is sent to Google, not after they agree."""
    with pytest.raises(VaultUnavailable, match="GOOGLE_OAUTH_TOKEN_KEY"):
        TokenVault(key)
