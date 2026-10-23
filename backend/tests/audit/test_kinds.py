"""What kind of business this is, and which checks that makes sensible.

The case that started this: "six businesses nearby are open twenty four hours"
is worth money to an emergency plumber and is nonsense to a law firm. The first
two tests are that, in both directions.
"""

from __future__ import annotations

import pytest

from ppcway.audit.kinds import (
    BY_TYPE,
    CHECKS,
    POLICY,
    SAID,
    Kind,
    applies,
    classify,
    keep,
    rule_for,
)


def a_finding(key: str, title: str = "Something") -> dict[str, object]:
    return {"key": key, "title": title, "status": "needs_you"}


def test_a_law_firm_is_never_told_to_open_at_three_in_the_morning() -> None:
    assert applies(Kind.PROFESSIONAL, "listing_24h") is False
    assert applies(Kind.PROFESSIONAL, "rivals_24h") is False

    kept = keep(Kind.PROFESSIONAL, [a_finding("rivals_24h"), a_finding("speed")])

    assert [one["key"] for one in kept] == ["speed"]


def test_an_emergency_plumber_is_told_exactly_that() -> None:
    """The same finding, for the one business it is true of, and weighted up."""
    assert applies(Kind.EMERGENCY, "rivals_24h") is True
    assert rule_for(Kind.EMERGENCY, "rivals_24h").weight > 1


@pytest.mark.parametrize(
    "kind",
    [k for k in Kind if k not in (Kind.EMERGENCY,)],
)
def test_no_other_kind_of_business_is_asked_about_the_night(kind: Kind) -> None:
    assert applies(kind, "listing_24h") is False
    assert applies(kind, "rivals_24h") is False


def test_an_online_store_is_asked_nothing_about_a_shopfront() -> None:
    """It cannot have a Google listing, so every question about one is wrong."""
    for check in ("listing_hours", "listing_photos", "listing_reviews", "rivals_rating"):
        assert applies(Kind.ECOMMERCE, check) is False
        assert applies(Kind.SOFTWARE, check) is False
    assert applies(Kind.ECOMMERCE, "local") is False


def test_a_plumber_open_all_night_is_an_emergency_plumber() -> None:
    guess = classify(primary_type="plumber", types=("plumber",), open_24h=True)
    assert guess.kind is Kind.EMERGENCY
    assert guess.sure is True


def test_a_plumber_with_ordinary_hours_is_a_trade() -> None:
    """Otherwise we tell a nine-to-five plumber to work nights."""
    guess = classify(primary_type="plumber", types=("plumber",), open_24h=False)
    assert guess.kind is Kind.TRADES
    assert applies(guess.kind, "rivals_24h") is False


def test_the_words_on_the_listing_can_say_it_is_urgent() -> None:
    guess = classify(
        primary_type="roofing_contractor",
        types=("roofing_contractor",),
        maps_label="Emergency roofer",
    )
    assert guess.kind is Kind.EMERGENCY


def test_the_generic_types_are_stepped_over() -> None:
    """Google puts 'establishment' on everything; it says nothing."""
    guess = classify(
        primary_type="",
        types=("point_of_interest", "establishment", "dentist"),
    )
    assert guess.kind is Kind.HEALTH
    assert guess.from_type == "dentist"


def test_a_trade_google_has_no_type_for_is_guessed_from_the_name() -> None:
    """There is no Places type for heating, pest control or cleaning."""
    guess = classify(
        primary_type="service", types=("service",), business_name="Oakville Heating Ltd"
    )
    assert guess.kind is Kind.TRADES
    # Guessed from a name, so offered rather than asserted.
    assert guess.sure is False
    assert "Change it" in guess.because


def test_a_business_we_cannot_place_gets_the_basics_and_no_guesses() -> None:
    guess = classify(primary_type="", types=("establishment",), business_name="Qxzy Ltd")
    assert guess.kind is Kind.OTHER
    assert guess.sure is False
    assert applies(Kind.OTHER, "speed") is True
    assert applies(Kind.OTHER, "listing_24h") is False


def test_an_unknown_google_type_does_not_crash_and_does_not_guess() -> None:
    """Google adds types and never removes them, so this will happen."""
    guess = classify(primary_type="quantum_blacksmith", types=("quantum_blacksmith",))
    assert guess.kind is Kind.OTHER
    assert guess.from_type == "quantum_blacksmith"


def test_every_kind_can_be_shown_to_a_person() -> None:
    for kind in Kind:
        label, about = SAID[kind]
        assert label and about
        assert label[0].isupper()


def test_the_policy_names_only_real_checks() -> None:
    """A typo here would silently switch a check off for one kind forever."""
    for kind, rules in POLICY.items():
        unknown = set(rules) - set(CHECKS)
        assert not unknown, f"{kind.value} names checks that do not exist: {unknown}"


def test_every_mapped_google_type_is_a_real_kind() -> None:
    for google_type, kind in BY_TYPE.items():
        assert isinstance(kind, Kind), google_type


def test_rewording_keeps_the_check_and_changes_the_question() -> None:
    """A restaurant is asked about its menu, not about its service pages."""
    kept = keep(Kind.FOOD, [a_finding("match", "Does each service have its own page?")])
    assert len(kept) == 1
    assert kept[0]["title"] == "Is your menu a page, not a picture of one?"
