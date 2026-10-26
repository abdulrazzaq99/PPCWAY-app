"""The layer between an automated decision and a merchant's money.

Blueprint §5.5. Every test here is a thing that must not happen, and the order
of the checks is itself part of the specification, so it is asserted rather
than assumed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ppcway.opt.guardrails import (
    ORDER,
    Limits,
    Proposal,
    Standing,
    Verdict,
    judge,
)
from ppcway.opt.models import Autonomy

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def a_proposal(**over: object) -> Proposal:
    fields: dict[str, object] = {
        "kind": "decrease_daily_budget",
        "customer_id": "2580586343",
        "target_id": "11",
        "target_label": "Emergency plumbing",
        "new_daily_budget": 32.0,
        "change_pct": -20.0,
        "metrics_as_of": NOW - timedelta(minutes=30),
    }
    fields.update(over)
    return Proposal(**fields)  # type: ignore[arg-type]


def a_standing(**over: object) -> Standing:
    fields: dict[str, object] = {
        "link_active": True,
        "token_refreshable": True,
        "account_status": "ENABLED",
        "billing_on_hold": False,
        "own_customer_id": "2580586343",
        "changes_to_entity_today": 0,
        "changes_today": 0,
        "moved_pct_today": 0.0,
        "active_entities": 100,
        "quota_left": 500,
    }
    fields.update(over)
    return Standing(**fields)  # type: ignore[arg-type]


def limits(**over: object) -> Limits:
    fields: dict[str, object] = {
        "version": 3,
        "autonomy": Autonomy.FULL_AUTO.value,
        "max_daily_budget": 40.0,
        "max_cpa": 60.0,
        "min_bid": 0.1,
        "max_bid": 8.0,
    }
    fields.update(over)
    return Limits(**fields)  # type: ignore[arg-type]


def ruling(**over: object):
    """One judgement, with everything clean unless a test says otherwise."""
    return judge(
        a_proposal(**over.pop("proposal", {})),  # type: ignore[arg-type]
        a_standing(**over.pop("standing", {})),  # type: ignore[arg-type]
        limits(**over.pop("limits", {})),  # type: ignore[arg-type]
        now=NOW,
    )


def test_the_order_is_the_one_the_blueprint_sets() -> None:
    """The order is the specification. Reordering it is a change of behaviour."""
    assert [name for name, _ in ORDER] == [
        "link_valid",
        "account_serviceable",
        "autonomy_level",
        "scope",
        "hard_spend_limits",
        "delta_limits",
        "velocity_limits",
        "blast_radius",
        "data_freshness",
        "quota",
    ]


def test_a_sound_change_on_a_sound_account_is_allowed() -> None:
    said = ruling()
    assert said.ruling.verdict is Verdict.APPROVED
    assert len(said.ran) == 10


def test_the_first_failure_stops_the_run() -> None:
    said = ruling(standing={"link_active": False})
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "link_valid"
    assert said.ran == ["link_valid"]


@pytest.mark.parametrize(
    ("standing", "check"),
    [
        ({"link_active": False}, "link_valid"),
        ({"token_refreshable": False}, "link_valid"),
        ({"account_status": "SUSPENDED"}, "account_serviceable"),
        ({"account_status": "CANCELED"}, "account_serviceable"),
        ({"billing_on_hold": True}, "account_serviceable"),
        ({"own_customer_id": "9999999999"}, "scope"),
        ({"changes_to_entity_today": 2}, "velocity_limits"),
        ({"changes_today": 20}, "velocity_limits"),
        ({"quota_left": 0}, "quota"),
    ],
)
def test_each_check_refuses_what_it_is_for(standing: dict, check: str) -> None:
    said = ruling(standing=standing)
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == check
    assert said.ruling.because


# --- fail-closed ------------------------------------------------------------


@pytest.mark.parametrize(
    ("over", "check"),
    [
        ({"standing": {"account_status": ""}}, "account_serviceable"),
        ({"standing": {"own_customer_id": ""}}, "scope"),
        ({"limits": {"max_daily_budget": 0.0}}, "hard_spend_limits"),
        ({"proposal": {"metrics_as_of": None}}, "data_freshness"),
        ({"proposal": {"pauses": 5}, "standing": {"active_entities": 0}}, "blast_radius"),
        ({"limits": {"autonomy": ""}}, "autonomy_level"),
    ],
)
def test_what_cannot_be_checked_is_refused(over: dict, check: str) -> None:
    """Not knowing whether a change is safe is not a reason to make it."""
    said = ruling(**over)
    assert said.ruling.verdict is Verdict.REJECTED, said.ruling
    assert said.ruling.check == check


def test_a_check_that_throws_has_not_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    import ppcway.opt.guardrails as module

    def explode(*a: object, **k: object) -> None:
        raise RuntimeError("the metrics store is down")

    monkeypatch.setattr(module, "ORDER", (("data_freshness", explode),), raising=True)
    said = judge(a_proposal(), a_standing(), limits(), now=NOW)
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "data_freshness"


# --- autonomy ---------------------------------------------------------------


def test_alerts_only_changes_nothing() -> None:
    said = ruling(limits={"autonomy": Autonomy.ALERTS_ONLY.value})
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "autonomy_level"


def test_approve_first_asks_rather_than_acts() -> None:
    said = ruling(limits={"autonomy": Autonomy.APPROVE_FIRST.value})
    assert said.ruling.verdict is Verdict.REQUIRES_APPROVAL
    # Every later check still ran before anybody was offered the choice.
    assert len(said.ran) == 10


def test_a_tap_cannot_authorise_what_the_limits_forbid() -> None:
    """The reason approval does not short-circuit the checks after it.

    Otherwise a proposal past the hard ceiling would be queued for the
    merchant, and their yes would apply it.
    """
    said = ruling(
        limits={"autonomy": Autonomy.APPROVE_FIRST.value, "max_daily_budget": 20.0},
        proposal={"new_daily_budget": 500.0},
    )
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "hard_spend_limits"


# --- the money checks -------------------------------------------------------


def test_a_budget_past_the_ceiling_is_refused() -> None:
    said = ruling(proposal={"new_daily_budget": 90.0})
    assert said.ruling.verdict is Verdict.REJECTED
    assert "ceiling" in said.ruling.because


def test_a_bid_outside_the_range_is_refused() -> None:
    said = ruling(proposal={"new_daily_budget": None, "new_bid": 25.0, "change_pct": None})
    assert said.ruling.check == "hard_spend_limits"


def test_one_change_may_only_move_a_number_so_far() -> None:
    said = ruling(proposal={"change_pct": -60.0})
    assert said.ruling.check == "delta_limits"
    assert "one change may move it" in said.ruling.because


def test_the_day_has_a_limit_even_when_each_change_is_small() -> None:
    """Twenty percent a day is a thirty-eight times increase over a year."""
    said = ruling(proposal={"change_pct": 20.0}, standing={"moved_pct_today": 40.0})
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "delta_limits"
    assert "already moved it" in said.ruling.because


def test_the_same_change_passes_when_the_day_has_room() -> None:
    said = ruling(proposal={"change_pct": 20.0}, standing={"moved_pct_today": 20.0})
    assert said.ruling.verdict is Verdict.APPROVED


def test_nothing_may_pause_most_of_an_account() -> None:
    """A metrics pipeline returning zeros must not become an outage."""
    said = ruling(proposal={"pauses": 40}, standing={"active_entities": 100})
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "blast_radius"
    assert "40%" in said.ruling.because


def test_a_small_pause_is_allowed() -> None:
    assert ruling(proposal={"pauses": 5}).ruling.verdict is Verdict.APPROVED


def test_old_figures_do_not_get_to_move_money() -> None:
    said = ruling(proposal={"metrics_as_of": NOW - timedelta(hours=9)})
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "data_freshness"
    assert "9 hours old" in said.ruling.because


def test_a_naive_timestamp_is_read_as_utc_rather_than_refused() -> None:
    """SQLite hands datetimes back without a timezone; that is not staleness."""
    said = ruling(proposal={"metrics_as_of": NOW.replace(tzinfo=None)})
    assert said.ruling.verdict is Verdict.APPROVED


def test_what_the_merchant_pinned_is_left_alone() -> None:
    said = ruling(
        proposal={"resources": ("customers/258/campaigns/11",)},
        limits={"hands_off": ("customers/258/campaigns/11",)},
    )
    assert said.ruling.verdict is Verdict.REJECTED
    assert said.ruling.check == "scope"
    assert "leave that one alone" in said.ruling.because


def test_every_refusal_says_why_in_words_a_person_can_read() -> None:
    for standing in ({"link_active": False}, {"billing_on_hold": True}, {"quota_left": 0}):
        said = ruling(standing=standing)
        because = said.ruling.because
        assert because.endswith("."), because
        assert because[0].isupper(), because
