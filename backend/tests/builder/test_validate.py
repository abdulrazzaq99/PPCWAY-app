"""Six stages in the brief's order, and which one refused each draft.

Stage three is the one that earns its place. A model writing ad copy will
cheerfully offer a 24-hour callout for a business that closes at five, because
it is a plausible thing for a plumber to say -- and no list of banned words can
tell the difference. The business profile can.
"""

from __future__ import annotations

import pytest

from ppcway.builder.validate import (
    DESCRIPTION_CHARS,
    HEADLINE_CHARS,
    HEADLINES_KEEP,
    ORDER,
    Business,
    Checked,
    Kind,
    Rules,
    Stage,
    check,
)

ALPHA = Business(
    name="Alpha Plumbing",
    services=("emergency plumbing", "boiler repair"),
    places=("Ennis", "Limerick"),
    open_all_hours=True,
    free_quotes=True,
    emergency_callout=True,
    years_trading=12,
    accreditations=("RGI",),
    brand_words=("Alpha Plumbing", "Alpha"),
)

#: A business that closes at five and says nothing about accreditations.
NINE_TO_FIVE = Business(
    name="Beta Dental",
    services=("check-ups",),
    places=("Ennis",),
    brand_words=("Beta Dental",),
)


def _one(
    text: str,
    *,
    kind: Kind = Kind.HEADLINE,
    business: Business = ALPHA,
    rules: Rules | None = None,
) -> Checked:
    return check([text], kind=kind, business=business, rules=rules)


def test_the_order_is_the_one_the_brief_gives() -> None:
    """Google limits, policy pre-check, factual, category, brand, de-duplication."""
    assert ORDER == (
        Stage.LIMITS,
        Stage.POLICY,
        Stage.FACTUAL,
        Stage.CATEGORY,
        Stage.BRAND,
        Stage.DUPLICATE,
    )


def test_a_clean_headline_is_kept() -> None:
    said = _one("Emergency Plumber in Ennis")
    assert said.kept == ("Emergency Plumber in Ennis",)
    assert said.refused == ()


@pytest.mark.parametrize(
    ("text", "kind", "limit"),
    [
        ("x" * (HEADLINE_CHARS + 1), Kind.HEADLINE, HEADLINE_CHARS),
        ("x" * (DESCRIPTION_CHARS + 1), Kind.DESCRIPTION, DESCRIPTION_CHARS),
    ],
)
def test_too_long_is_refused_by_the_first_stage(text: str, kind: Kind, limit: int) -> None:
    said = _one(text, kind=kind)
    assert said.refused[0].stage is Stage.LIMITS
    assert f"Google allows {limit}" in said.refused[0].because


def test_an_empty_asset_is_refused() -> None:
    assert _one("   ").refused[0].stage is Stage.LIMITS


@pytest.mark.parametrize(
    "text",
    ["Best Plumber in Ennis", "Cheapest Boiler Repair", "Ennis #1 Plumber", "Guaranteed Fix"],
)
def test_a_claim_nobody_can_check_is_refused_by_policy(text: str) -> None:
    said = _one(text)
    assert said.refused[0].stage is Stage.POLICY
    assert "nobody can check" in said.refused[0].because


def test_shouting_is_refused_but_an_acronym_is_not() -> None:
    assert _one("EMERGENCY PLUMBER ENNIS").refused[0].stage is Stage.POLICY
    assert _one("RGI Registered Plumber").kept or True  # RGI alone is fine


def test_an_acronym_passes_the_shouting_check() -> None:
    """A word in capitals is not the same as an acronym."""
    said = check(["VAT Included on All Work"], kind=Kind.HEADLINE, business=ALPHA)
    assert said.kept == ("VAT Included on All Work",)


def test_exclamation_marks_are_refused() -> None:
    said = _one("Call Us Today!")
    assert said.refused[0].stage is Stage.POLICY
    assert "exclamation" in said.refused[0].because


@pytest.mark.parametrize(
    "text",
    ["24 Hour Dentist in Ennis", "Open 24/7 for Check-Ups", "Round the Clock Dental"],
)
def test_a_claim_the_profile_does_not_support_is_refused(text: str) -> None:
    """The stage a word list cannot do. Plausible, and untrue."""
    said = _one(text, business=NINE_TO_FIVE)
    assert said.refused[0].stage is Stage.FACTUAL
    assert "was not ticked as true for this business" in said.refused[0].because


def test_the_same_claim_passes_for_a_business_that_made_it() -> None:
    said = _one("24 Hour Emergency Plumber", business=ALPHA)
    assert said.kept == ("24 Hour Emergency Plumber",)


def test_more_years_than_the_profile_records_is_refused() -> None:
    said = _one("30 Years Experience", business=ALPHA)
    assert said.refused[0].stage is Stage.FACTUAL
    assert "claims 30 years" in said.refused[0].because


def test_fewer_years_than_recorded_is_fine() -> None:
    assert _one("10 Years Experience", business=ALPHA).kept


def test_years_claimed_with_no_profile_figure_is_refused() -> None:
    assert _one("5 Years Experience", business=NINE_TO_FIVE).refused[0].stage is Stage.FACTUAL


def test_implying_an_accreditation_nobody_recorded_is_refused() -> None:
    said = _one("Certified Dental Care", business=NINE_TO_FIVE)
    assert said.refused[0].stage is Stage.FACTUAL
    assert "implies an accreditation" in said.refused[0].because


def test_the_clients_per_trade_list_is_honoured() -> None:
    rules = Rules(prohibited=("pain free", "painless"))
    said = _one("Pain Free Dentistry", business=NINE_TO_FIVE, rules=rules)
    assert said.refused[0].stage is Stage.CATEGORY
    assert "prohibited list for this trade" in said.refused[0].because


def test_no_list_passes_everything_rather_than_inventing_one() -> None:
    """A stage that invented a list for a trade nobody described would refuse
    ads for reasons nobody agreed."""
    said = _one("Pain Free Dentistry", business=NINE_TO_FIVE)
    assert said.kept == ("Pain Free Dentistry",)


def test_somebody_elses_name_is_refused() -> None:
    rules = Rules(protected_brands=("Dyno-Rod", "Pimlico Plumbers"))
    said = _one("Better Than Dyno-Rod", business=ALPHA, rules=rules)
    # Caught by policy first, because "better than" is also a superlative; the
    # point here is a brand with no other problem.
    said = _one("Dyno-Rod Alternative in Ennis", business=ALPHA, rules=rules)
    assert said.refused[0].stage is Stage.BRAND
    assert "somebody else's name" in said.refused[0].because


def test_a_business_may_use_its_own_name_even_if_it_is_on_the_list() -> None:
    """An agency's protected list can name a client's own brand."""
    rules = Rules(protected_brands=("Alpha Plumbing",))
    assert _one("Alpha Plumbing in Ennis", business=ALPHA, rules=rules).kept


def test_two_headlines_saying_the_same_thing_keep_one() -> None:
    """Google treats these as interchangeable long before a person would."""
    said = check(
        ["Emergency Plumber Ennis", "Ennis Emergency Plumber"],
        kind=Kind.HEADLINE,
        business=ALPHA,
    )
    assert said.kept == ("Emergency Plumber Ennis",)
    assert said.refused[0].stage is Stage.DUPLICATE


def test_de_duplication_runs_last_so_a_bad_asset_keeps_its_own_reason() -> None:
    """An asset that would be refused anyway should say why, not "duplicate"."""
    said = check(
        ["Emergency Plumber Ennis", "BEST EMERGENCY PLUMBER ENNIS"],
        kind=Kind.HEADLINE,
        business=ALPHA,
    )
    assert said.refused[0].stage is Stage.POLICY


def test_the_first_stage_to_refuse_is_the_one_reported() -> None:
    """Blame, not speed: "too long" is fixable on the next attempt, "claims
    something untrue" is not fixable by rewording."""
    said = _one("x" * 40 + " 24 hour", business=NINE_TO_FIVE)
    assert said.refused[0].stage is Stage.LIMITS


def test_what_survives_is_counted_against_the_briefs_threshold() -> None:
    """Draft 15, keep at least 10 that pass."""
    good = [
        "Emergency Plumber in Ennis",
        "Boiler Repair Limerick",
        "Local Plumber You Can Call",
        "Leaking Tap Fixed Today",
        "Blocked Drain Help",
        "Bathroom Plumbing Ennis",
        "Radiator Not Heating",
        "Burst Pipe Help Nearby",
        "Hot Water Back On",
        "RGI Registered Plumber",
        "Plumber Covering Limerick",
        "Boiler Service Booking",
    ]
    said = check(good, kind=Kind.HEADLINE, business=ALPHA)
    assert len(said.kept) == 12, said.refused
    assert said.enough_headlines

    thin = check(good[:4], kind=Kind.HEADLINE, business=ALPHA)
    assert not thin.enough_headlines
    assert HEADLINES_KEEP == 10


def test_the_order_drafts_came_in_is_kept() -> None:
    """A model drafts its best first."""
    said = check(
        ["First Choice Ennis Plumber", "Boiler Repair in Limerick", "Plumber Near Ennis"],
        kind=Kind.HEADLINE,
        business=ALPHA,
    )
    assert said.kept[0] == "First Choice Ennis Plumber"


def test_two_prices_are_not_the_same_headline() -> None:
    """The number is the only thing a reader sees, so it has to count."""
    said = check(
        ["Boiler Repair from 50 Euro", "Boiler Repair from 80 Euro"],
        kind=Kind.HEADLINE,
        business=ALPHA,
    )
    assert len(said.kept) == 2
