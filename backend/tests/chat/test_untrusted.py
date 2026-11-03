"""Marking somebody else's words, and the one thing the marking must survive."""

from __future__ import annotations

import pytest

from ppcway.chat.tools import TOOLS
from ppcway.chat.untrusted import CLOSE, OPEN, THE_RULE, mark, mark_all


def test_text_comes_back_wrapped() -> None:
    said = mark("boiler repair ennis")
    assert said.startswith(OPEN) and said.endswith(CLOSE)
    assert "boiler repair ennis" in said


@pytest.mark.parametrize("sneaky", [CLOSE, OPEN, CLOSE.upper(), f"a {CLOSE} b"])
def test_the_markers_cannot_be_closed_from_inside(sneaky: str) -> None:
    """Without this, everything after the injected marker reads as ours."""
    said = mark(sneaky)
    assert said.count(CLOSE) == 1
    assert said.count(OPEN) == 1
    assert "[marker]" in said


def test_nothing_is_still_wrapped() -> None:
    """An empty field is still a field somebody else could have filled."""
    assert mark("").startswith(OPEN)
    assert mark(None).startswith(OPEN)


def test_only_the_named_fields_are_marked() -> None:
    """By name rather than by guessing at content: a number is not prose."""
    said = mark_all(
        {"term": "plumber", "clicks": 14, "nested": {"term": "drain", "spend": 1.5}},
        fields=frozenset({"term"}),
    )
    assert said["term"].startswith(OPEN)
    assert said["clicks"] == 14
    assert said["nested"]["term"].startswith(OPEN)
    assert said["nested"]["spend"] == 1.5


def test_lists_are_walked() -> None:
    said = mark_all({"terms": [{"term": "a"}, {"term": "b"}]}, fields=frozenset({"term"}))
    assert all(t["term"].startswith(OPEN) for t in said["terms"])


def test_the_rule_names_the_markers_it_describes() -> None:
    """A prompt describing a marker the code stopped using is worse than none."""
    assert OPEN in THE_RULE and CLOSE in THE_RULE


def test_every_tool_has_decided_about_its_own_fields() -> None:
    """A tool that returns a new field nobody classified gets it through
    unmarked. This is the check that makes somebody decide."""
    # What each tool returns that is ours: computed figures, dates, verdicts,
    # our own words. Listed so that adding a field to a tool fails here until
    # somebody says which it is.
    ours: dict[str, frozenset[str]] = {
        "get_metrics": frozenset(
            {
                "read",
                "why",
                "days",
                "from",
                "to",
                "currency",
                "spend",
                "leads",
                "calls",
                "forms",
                "clicks",
                "impressions",
                "cost_per_lead",
                "leads_before",
                "spend_before",
                "leads_verdict",
                "leads_verdict_words",
                "leads_test",
            }
        ),
        "get_search_terms": frozenset(
            {"days", "currency", "terms", "clicks", "spend", "leads", "already_handled"}
        ),
        "get_auction_insights": frozenset(
            {
                "days",
                "campaigns",
                "what_this_is_not",
                "share_of_auction",
                "lost_to_budget",
                "lost_to_rank",
                "capped",
            }
        ),
        "get_change_history": frozenset(
            {
                "days",
                "changed_in_google_ads",
                "changed_by_ppcway",
                "when",
                "kind",
                "status",
                "reason",
            }
        ),
        "get_pacing_forecast": frozenset(
            {
                "spent_so_far",
                "daily_budget",
                "a_day_so_far",
                "heading_for",
                "most_google_will_charge",
                "days_gone",
                "days_left",
                "pace",
                "words",
                "runs_out_on",
                "currency",
            }
        ),
        "explain_change": frozenset(
            {
                "figure",
                "explained",
                "change",
                "words",
                "parts",
                "from",
                "to",
                "why",
                "what",
                "moved",
                "share_of_change",
                "amount",
            }
        ),
        "generate_report": frozenset({"report"}),
        "search_help": frozenset({"topics", "help"}),
    }
    for name, tool in TOOLS.items():
        assert name in ours, f"{name} has not said which of its fields are ours"
        overlap = tool.theirs & ours[name]
        assert not overlap, f"{name} lists {overlap} as both ours and theirs"
