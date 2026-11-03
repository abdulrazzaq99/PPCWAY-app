"""The Keyword Planner gate, the drafting rule, and the one-batch launch.

The gate is the one that matters. A model asked for fifty plumbing keywords
produces fifty plausible phrases, and perhaps thirty are things no human has
ever typed into Google. Those thirty cost nothing in impressions and
everything in trust.
"""

from __future__ import annotations

from typing import Any

from ppcway.ads.planner import Demand, Search
from ppcway.builder.draft import TRIES, Written, _lines, write_copy
from ppcway.builder.keywords import LEAST_MONTHLY, sift
from ppcway.builder.launch import AI_DRAFTED, Plan, declare_ai, headline_fields, launch, ready
from ppcway.builder.validate import Business
from ppcway.gateway.port import Applied, Batch, GoogleRefused, Refused
from ppcway.model.jobs import OPUS

ALPHA = Business(
    name="Alpha Plumbing",
    services=("emergency plumbing",),
    places=("Ennis",),
    open_all_hours=True,
    free_quotes=True,
    emergency_callout=True,
    years_trading=12,
    accreditations=("RGI",),
    brand_words=("Alpha Plumbing",),
)


def demand(*terms: tuple[str, int]) -> Demand:
    return Demand(
        read=True,
        town="Ennis",
        town_matched=True,
        searches=[
            Search(
                term=term,
                monthly=monthly,
                competition="MEDIUM",
                top_of_page_low=1.2,
                top_of_page_high=3.4,
            )
            for term, monthly in terms
        ],
    )


# --- the Keyword Planner gate ------------------------------------------------


def test_only_what_google_confirms_becomes_a_keyword() -> None:
    said = sift(
        ["emergency plumber ennis", "bespoke artisanal pipe solutions"],
        demand(("emergency plumber ennis", 320)),
    )
    assert [k.text for k in said.keywords] == ["emergency plumber ennis"]
    assert [d.text for d in said.dropped] == ["bespoke artisanal pipe solutions"]
    assert "no searches for this" in said.dropped[0].because


def test_a_candidate_with_no_volume_is_demoted_not_deleted() -> None:
    """ "We thought of this and Google says nobody searches for it" is useful to
    a merchant, and the sort of thing a person would want to argue with."""
    said = sift(["made up phrase"], demand())
    assert said.keywords == ()
    assert len(said.dropped) == 1
    assert said.dropped[0].text == "made up phrase"


def test_almost_nobody_searching_is_not_enough() -> None:
    said = sift(["niche thing"], demand(("niche thing", LEAST_MONTHLY - 1)))
    assert said.keywords == ()
    assert "too few to be worth bidding on" in said.dropped[0].because


def test_the_busiest_keyword_comes_first() -> None:
    """A campaign's first ad group should be what most people are looking for."""
    said = sift(
        ["quiet one", "busy one"],
        demand(("quiet one", 40), ("busy one", 900)),
    )
    assert [k.text for k in said.keywords] == ["busy one", "quiet one"]


def test_a_planner_we_could_not_reach_is_not_the_same_as_nothing_having_volume() -> None:
    """One means we do not know and must not guess; the other means we asked."""
    said = sift(["emergency plumber"], Demand(read=False, trouble="quota exhausted"))
    assert said.keywords == ()
    assert said.dropped == ()
    assert said.unavailable == "quota exhausted"
    assert not said.usable


def test_duplicates_are_collapsed_and_matching_ignores_case() -> None:
    said = sift(
        ["Emergency Plumber Ennis", "emergency  plumber ennis"],
        demand(("emergency plumber ennis", 320)),
    )
    assert len(said.keywords) == 1


# --- the drafting rule -------------------------------------------------------


class Saying:
    """A model that answers with a scripted sequence."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.asked: list[dict[str, Any]] = []

    def ask(self, job: Any, **kwargs: Any) -> Any:
        from ppcway.model.service import Answer

        self.asked.append({"job": job, **kwargs})
        said = self.replies.pop(0) if self.replies else ""
        return Answer(text=said, model=OPUS, prompt_version="otto-test")


def _fifteen(prefix: str = "") -> str:
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
        "Shower Not Draining",
        "Outside Tap Fitted",
        "Toilet Repairs in Ennis",
    ]
    bodies = [
        "We answer the phone and come out the same day across Ennis and Limerick.",
        "Free quotes before any work starts, and a tidy job when we leave.",
        "RGI registered, twelve years in the trade, and no call out charge.",
        "Call any hour and speak to a plumber rather than an answering service.",
    ]
    return prefix + "\n".join(good) + "\nDESCRIPTIONS\n" + "\n".join(bodies)


def test_a_good_first_draft_is_used_once() -> None:
    models = Saying(_fifteen())
    said = write_copy(models, business=ALPHA, theme="Emergency", keywords=["plumber ennis"])
    assert said.enough
    assert len(said.headlines) == 15
    assert len(said.descriptions) == 4
    assert said.asked == 1


def test_numbering_a_model_adds_anyway_is_stripped() -> None:
    assert _lines("1. First one\n2) Second one\n- Third", most=5) == [
        "First one",
        "Second one",
        "Third",
    ]


def test_a_draft_that_mostly_fails_is_retried_once_with_the_reasons() -> None:
    """Not "try again": a model told only that it failed produces the same copy
    with different adjectives."""
    bad = (
        "\n".join(["BEST PLUMBER EVER"] * 15) + "\nDESCRIPTIONS\n" + "\n".join(["Guaranteed!"] * 4)
    )
    models = Saying(bad, _fifteen())
    said = write_copy(models, business=ALPHA, theme="Emergency", keywords=["plumber"])
    assert said.asked == 2
    assert said.enough
    second = models.asked[1]["said"]
    assert "YOUR LAST ATTEMPT WAS REJECTED" in second
    assert "policy_pre_check" in second


def test_two_bad_drafts_ask_for_the_trade_template_rather_than_a_third_try() -> None:
    """Three tries at copy refused for claiming untrue things is three tries at
    the same misunderstanding."""
    bad = (
        "\n".join(["BEST PLUMBER EVER"] * 15) + "\nDESCRIPTIONS\n" + "\n".join(["Guaranteed!"] * 4)
    )
    models = Saying(bad, bad)
    said = write_copy(models, business=ALPHA, theme="Emergency", keywords=["plumber"])
    assert said.asked == TRIES == 2
    assert not said.enough
    assert "has not supplied yet" in said.short
    assert said.refused_by.get("policy_pre_check", 0) > 0


def test_the_prompt_carries_the_business_profile() -> None:
    """The prompt is how it usually gets it right; the validator is why it does
    not matter when it does not."""
    models = Saying(_fifteen())
    write_copy(models, business=ALPHA, theme="Emergency", keywords=["plumber"])
    asked = models.asked[0]["said"]
    assert "Open 24 hours: yes" in asked
    assert "Accreditations: RGI" in asked
    assert "Years trading: 12" in asked
    system = models.asked[0]["system"]
    assert "may claim nothing beyond it" in system


def test_no_model_means_no_copy_and_says_why() -> None:
    said = write_copy(None, business=ALPHA, theme="Emergency", keywords=["plumber"])
    assert not said.enough
    assert "not switched on" in said.short
    assert said.asked == 0


# --- the launch --------------------------------------------------------------


class Door:
    def __init__(self, *answers: Applied | Exception) -> None:
        self.answers = list(answers)
        self.sent: list[Batch] = []

    def mutate(self, batch: Batch) -> Applied:
        self.sent.append(batch)
        said = self.answers.pop(0) if self.answers else Applied(landed=())
        if isinstance(said, Exception):
            raise said
        return said


def a_plan(**over: Any) -> Plan:
    fields: dict[str, Any] = {
        "name": "Emergency plumbing · Ennis",
        "daily_budget": 20.0,
        "currency": "CAD",
        "business": ALPHA,
        "theme": "Emergency",
        "keywords": sift(
            ["emergency plumber ennis", "burst pipe ennis"],
            demand(("emergency plumber ennis", 320), ("burst pipe ennis", 90)),
        ),
        "copy": Written(
            headlines=tuple(f"Headline {n}" for n in range(12)),
            descriptions=("One.", "Two."),
            asked=1,
        ),
        "final_url": "https://alphaplumbing.ie/emergency",
    }
    fields.update(over)
    return Plan(**fields)


def test_nothing_launches_while_the_write_gate_is_shut() -> None:
    door = Door(Applied(landed=("a", "b")))
    said = launch(a_plan(), door=door, customer_id="1", gate_open=False)
    assert not said.live
    assert "not creating campaigns" in said.words
    assert door.sent == []


def test_every_pre_launch_check_is_reported_together() -> None:
    """A merchant fixing one thing and being told about the next gives up on
    the third."""
    said = ready(
        a_plan(daily_budget=0.0, final_url="", copy=Written()),
        gate_open=True,
    )
    assert not said.may_launch
    assert len(said.stopping) >= 3
    assert any("daily budget" in one for one in said.stopping)
    assert any("no page to send people to" in one for one in said.stopping)


def test_a_plan_whose_keywords_google_never_confirmed_cannot_launch() -> None:
    said = ready(a_plan(keywords=sift(["made up"], demand())), gate_open=True)
    assert not said.may_launch
    assert any("Google says people search for" in one for one in said.stopping)


def test_everything_landing_is_live() -> None:
    door = Door(
        Applied(landed=("customers/1/adGroupCriteria/1~1", "customers/1/adGroupCriteria/1~2"))
    )
    said = launch(a_plan(), door=door, customer_id="1", gate_open=True)
    assert said.live
    assert "2 keywords are live" in said.words
    assert len(door.sent) == 1, "one batch, not four"


def test_a_partial_launch_is_put_back_whole() -> None:
    """Nobody asked for half a campaign, and leaving it spends money on an
    account nobody meant to change."""
    door = Door(
        Applied(
            landed=("customers/1/adGroupCriteria/1~1", None),
            refused=(Refused(at=1, code="criterion.INVALID", message="no"),),
        ),
        Applied(landed=("customers/1/adGroupCriteria/1~1",)),
    )
    said = launch(a_plan(), door=door, customer_id="1", gate_open=True)
    assert not said.live
    assert "put the 1 that landed back" in said.words
    assert "Nothing has changed in your account" in said.words
    assert len(door.sent) == 2, "the launch, then the rollback"
    assert door.sent[1].operations[0].doing.value == "remove"


def test_a_rollback_that_itself_fails_says_so_rather_than_crashing() -> None:
    """The merchant needs to know the account is in a half state far more than
    the process needs to crash."""
    door = Door(
        Applied(
            landed=("customers/1/adGroupCriteria/1~1", None),
            refused=(Refused(at=1, code="x", message="no"),),
        ),
        GoogleRefused("500"),
    )
    said = launch(a_plan(), door=door, customer_id="1", gate_open=True)
    assert not said.live
    assert said.rolled_back == ("customers/1/adGroupCriteria/1~1",)


def test_google_refusing_the_whole_request_creates_nothing() -> None:
    door = Door(GoogleRefused("403 no permission"))
    said = launch(a_plan(), door=door, customer_id="1", gate_open=True)
    assert not said.live
    assert "Nothing was created" in said.words


def test_ai_written_copy_is_declared() -> None:
    """One model-written headline makes the ad model-written, and the
    declaration costs nothing while getting it wrong is a policy matter."""
    fields = headline_fields(Written(headlines=("One",), descriptions=("Two.",), asked=1))
    assert fields["synthetic_content_info"] == AI_DRAFTED["synthetic_content_info"]


def test_copy_no_model_touched_is_not_declared() -> None:
    fields = declare_ai({"x": 1}, Written(headlines=("One",), descriptions=("Two.",), asked=0))
    assert "synthetic_content_info" not in fields


def test_the_launch_says_when_the_text_was_drafted_by_otto() -> None:
    door = Door(Applied(landed=("a", "b")))
    said = launch(a_plan(), door=door, customer_id="1", gate_open=True)
    assert "declared to Google as AI-written" in said.words


def test_the_checks_run_again_at_launch_not_only_on_the_screen() -> None:
    """Time passes between a person pressing Launch and this running, and the
    write gate is a thing that can be shut in between."""
    from ppcway.gateway import switch

    door = Door(Applied(landed=("a", "b")))
    stopped = switch.Standing(
        may_write=False, because="A rule is misbehaving.", stopped_by="global"
    )
    said = launch(a_plan(), door=door, customer_id="1", gate_open=True, writes=stopped)
    assert not said.live
    assert "misbehaving" in said.words
    assert door.sent == []
