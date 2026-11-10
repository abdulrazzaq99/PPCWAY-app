"""Promises for any kind of business, not only a tradesman's.

On 10 November the client turned the builder down for knowing one kind of
business: free quotes, open 24 hours and emergency callouts were the only
promises it could police. These hold the catalogue together and hold the copy
checks to it.
"""

from __future__ import annotations

from ppcway.builder.kinds import BY_PROMISE, KINDS, PHRASES, catalogue, kind_of, known_promises
from ppcway.builder.validate import Business, Kind, Stage, check


def _one(text: str, **business: object) -> object:
    return check([text], kind=Kind.HEADLINE, business=Business(**business))  # type: ignore[arg-type]


def test_every_kind_offers_only_promises_that_exist() -> None:
    for kind in KINDS:
        assert kind.promises, kind.id
        assert all(p in BY_PROMISE for p in kind.promises), kind.id
        assert "jobs" in kind.negatives, "nobody pays for job seekers"


def test_no_phrase_belongs_to_two_promises() -> None:
    seen: dict[str, str] = {}
    for phrase, promise in PHRASES:
        assert seen.setdefault(phrase, promise.id) == promise.id, phrase


def test_an_unknown_kind_is_something_else_and_unknown_promises_are_dropped() -> None:
    assert kind_of("spaceship").id == "other"
    assert known_promises(["free_trial", "made_up", "free_plan"]) == ("free_plan", "free_trial")
    assert known_promises("free_trial") == ()


def test_a_shop_cannot_promise_free_shipping_unless_it_ticks_it() -> None:
    refused = _one("Free Shipping on Bedding", kind="online_shop")
    assert refused.refused[0].stage is Stage.FACTUAL  # type: ignore[attr-defined]
    assert "free shipping" in refused.refused[0].because  # type: ignore[attr-defined]
    allowed = _one("Free Shipping on Bedding", kind="online_shop", promises=("free_shipping",))
    assert allowed.kept == ("Free Shipping on Bedding",)  # type: ignore[attr-defined]


def test_a_free_trial_ticked_is_not_refused_as_a_free_version() -> None:
    """ "Try for free" contains "for free". The longer wording is the free
    trial's, and once it is allowed it is not looked at again."""
    said = _one("Try It for Free Today", kind="software", promises=("free_trial",))
    assert said.kept == ("Try It for Free Today",)  # type: ignore[attr-defined]
    refused = _one("Convert PDFs for Free", kind="software", promises=("free_trial",))
    assert refused.refused  # type: ignore[attr-defined]


def test_a_draft_from_before_promises_were_a_list_still_checks_the_same() -> None:
    """The emergency tick licensed "same day" before 10 November, so it still does."""
    said = _one("Same Day Emergency Plumber", emergency_callout=True)
    assert said.kept == ("Same Day Emergency Plumber",)  # type: ignore[attr-defined]


def test_the_screen_gets_every_kind_and_promise_in_words() -> None:
    shape = catalogue()
    assert [k["id"] for k in shape["kinds"]][-1] == "other"
    assert all(p["label"] and p["short"] for p in shape["promises"])
    software = next(k for k in shape["kinds"] if k["id"] == "software")
    assert software["win"] == "sign-ups"
