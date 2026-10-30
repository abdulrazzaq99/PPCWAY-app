"""The rules as data, including the three the client has not specified."""

from __future__ import annotations

import pytest

from ppcway.rules.catalogue import (
    CATALOGUE,
    MAY_AUTO,
    Risk,
    Route,
    Rule,
    live,
    rule,
    waiting,
)


def test_only_the_two_rules_the_client_named_are_live() -> None:
    """R1 and R4. The brief names those two because they are the auto-apply types."""
    assert [r.id for r in live()] == ["R1", "R4"]


def test_the_other_three_are_declared_and_say_what_is_missing() -> None:
    """Guessing at a rule that spends somebody's money is worse than leaving it out."""
    left = waiting()
    assert [r.id for r in left] == ["R2", "R3", "R5"]
    for spec in left:
        assert not spec.implemented
        assert "v0.1" in spec.spec, "a reader has to know where the specification is"
        assert spec.kind == "unspecified"


def test_every_rule_in_the_catalogue_is_keyed_by_its_own_id() -> None:
    for key, spec in CATALOGUE.items():
        assert key == spec.id


def test_a_rule_the_log_cannot_explain_cannot_be_asked_for() -> None:
    with pytest.raises(ValueError, match="there is no rule"):
        rule("R9")


def test_only_low_risk_may_ever_auto_apply() -> None:
    """The brief: medium and high-risk changes always need a person."""
    assert MAY_AUTO == frozenset({Risk.LOW})
    for spec in CATALOGUE.values():
        if spec.auto_eligible:
            assert spec.risk is Risk.LOW


@pytest.mark.parametrize("risk", [Risk.MEDIUM, Risk.HIGH])
def test_a_risky_rule_cannot_be_configured_as_auto_eligible(risk: Risk) -> None:
    """Not merely discouraged. The combination will not construct."""
    with pytest.raises(ValueError, match="always need a person"):
        Rule(
            id="RX",
            version=1,
            name="x",
            about="x",
            kind="decrease_daily_budget",
            risk=risk,
            route=Route.OWNER,
            auto_eligible=True,
            implemented=True,
            limits={"a": 1.0},
        )


def test_an_implemented_rule_must_name_its_thresholds() -> None:
    """They live in the record so an old action stays explainable after a change."""
    with pytest.raises(ValueError, match="names no thresholds"):
        Rule(
            id="RX",
            version=1,
            name="x",
            about="x",
            kind="decrease_daily_budget",
            risk=Risk.MEDIUM,
            route=Route.OWNER,
            implemented=True,
        )


def test_the_thresholds_the_brief_states_are_the_ones_r1_uses() -> None:
    """ "1.5x target cost per lead in spend, or 100 clicks"."""
    limits = rule("R1").limits
    assert limits["wasted_multiple_of_target"] == 1.5
    assert limits["enough_clicks"] == 100.0


def test_a_rule_is_frozen() -> None:
    """A rule a caller can edit is a rule the log records wrongly."""
    with pytest.raises(Exception):  # noqa: B017 - dataclass raises FrozenInstanceError
        rule("R1").version = 2  # type: ignore[misc]
