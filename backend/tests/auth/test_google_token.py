"""What Google's token must say before anybody is signed in."""

from __future__ import annotations

import pytest

from ppcway.auth import google
from ppcway.auth.google import SignInRefused, verify_google_token


def claims(**extra: object) -> dict[str, object]:
    base = {"sub": "g-1", "email": "owner@alphaplumbing.ca", "email_verified": True, "name": "Dana"}
    base.update(extra)
    return base


def test_a_good_token_becomes_the_person(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(google.id_token, "verify_oauth2_token", lambda *a, **k: claims())
    who = verify_google_token("tok", client_id="our-client", request=object())  # type: ignore[arg-type]
    assert who.sub == "g-1" and who.email == "owner@alphaplumbing.ca" and who.name == "Dana"


def test_the_address_is_lower_cased_because_it_identifies_the_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        google.id_token, "verify_oauth2_token", lambda *a, **k: claims(email="Owner@Alpha.CA")
    )
    assert verify_google_token("tok", client_id="c", request=object()).email == "owner@alpha.ca"  # type: ignore[arg-type]


def test_an_unconfirmed_address_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        google.id_token, "verify_oauth2_token", lambda *a, **k: claims(email_verified=False)
    )
    with pytest.raises(SignInRefused, match="confirmed"):
        verify_google_token("tok", client_id="c", request=object())  # type: ignore[arg-type]


def test_a_token_google_will_not_vouch_for_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*a: object, **k: object) -> dict[str, object]:
        raise ValueError("Token has wrong audience")

    monkeypatch.setattr(google.id_token, "verify_oauth2_token", refuse)
    with pytest.raises(SignInRefused, match="wrong audience"):
        verify_google_token("tok", client_id="c", request=object())  # type: ignore[arg-type]
