"""The campaign builder: what it writes, what it sends, and what it refuses.

Every field the launch sends was checked against Google Ads API v25's own
definitions; these hold the request to that shape, because one wrong field
fails the whole request and Google is only met in production.
"""

from __future__ import annotations

import json
from typing import Any

from ppcway.ads.planner import Demand, Search
from ppcway.builder.build import build_plan, on_theme
from ppcway.builder.campaign import (
    CampaignPlan,
    Place,
    Theme,
    campaign_of,
    in_one_sentence,
    missing,
    operations_for,
)
from ppcway.builder.draft import Written
from ppcway.builder.validate import Business
from ppcway.gateway.port import Doing

CUSTOMER = "2580586343"


def a_plan(**over: Any) -> CampaignPlan:
    fields: dict[str, Any] = {
        "name": "PDF tools",
        "daily_budget": 20.0,
        "currency": "USD",
        "final_url": "https://pdfezy.com/",
        "places": [Place("geoTargetConstants/2616", "Poland", "Country")],
        "language": Place("languageConstants/1000", "English"),
        "bidding": "clicks",
        "themes": [
            Theme(
                name="pdf to word",
                keywords=[{"text": "pdf to word", "monthly": 9000}],
                headlines=[f"Headline {n}" for n in range(12)],
                descriptions=["One description.", "Another description."],
            ),
            Theme(
                name="compress pdf",
                keywords=[{"text": "compress pdf", "monthly": 4000}],
                headlines=[f"Squeeze {n}" for n in range(10)],
                descriptions=["Smaller files.", "Same quality."],
            ),
        ],
        "negatives": ["jobs", "Jobs", " "],
        "not_political": True,
    }
    fields.update(over)
    return CampaignPlan(**fields)


def _ops(plan: CampaignPlan) -> list[Any]:
    return list(operations_for(plan, CUSTOMER, tag="abc12345").operations)


def test_the_budget_and_campaign_come_first_with_temporary_names() -> None:
    """The rest of the request points at them before they exist."""
    ops = _ops(a_plan())
    budget, campaign = ops[0], ops[1]
    assert (budget.resource_type, budget.resource_name) == (
        "campaign_budget",
        f"customers/{CUSTOMER}/campaignBudgets/-1",
    )
    assert budget.fields["amountMicros"] == "20000000"
    assert budget.fields["explicitlyShared"] is False
    assert (campaign.resource_type, campaign.resource_name) == (
        "campaign",
        f"customers/{CUSTOMER}/campaigns/-2",
    )
    assert campaign.fields["campaignBudget"] == budget.resource_name
    assert all(op.doing is Doing.CREATE for op in ops)


def test_the_campaign_is_search_only_shown_to_people_in_the_places_and_declared() -> None:
    campaign = _ops(a_plan())[1].fields
    assert campaign["advertisingChannelType"] == "SEARCH"
    assert campaign["networkSettings"] == {
        "targetGoogleSearch": True,
        "targetSearchNetwork": False,
        "targetContentNetwork": False,
        "targetPartnerSearchNetwork": False,
    }
    assert campaign["geoTargetTypeSetting"]["positiveGeoTargetType"] == "PRESENCE"
    assert campaign["containsEuPoliticalAdvertising"] == (
        "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"
    ), "Google refuses a new campaign without the declaration"
    assert campaign["targetSpend"] == {}, "maximise clicks"
    assert _ops(a_plan(bidding="leads"))[1].fields["maximizeConversions"] == {}


def test_places_and_excluded_searches_hang_off_the_campaign() -> None:
    criteria = [op.fields for op in _ops(a_plan()) if op.resource_type == "campaign_criterion"]
    campaign = f"customers/{CUSTOMER}/campaigns/-2"
    assert {"campaign": campaign, "location": {"geoTargetConstant": "geoTargetConstants/2616"}} in (
        criteria
    )
    # Google refuses a language on a Search campaign since late September
    # 2026 (ContextError.OPERATION_NOT_PERMITTED_FOR_CONTEXT), and one refused
    # operation fails the whole all-or-nothing launch.
    assert not any("language" in c for c in criteria), "no language on a Search campaign"
    negatives = [c for c in criteria if c.get("negative")]
    assert negatives == [
        {"campaign": campaign, "negative": True, "keyword": {"text": "jobs", "matchType": "PHRASE"}}
    ], "one exclusion, tidied: the duplicate and the blank are dropped"


def test_each_theme_is_an_ad_group_with_its_keywords_and_one_ad() -> None:
    ops = _ops(a_plan())
    groups = [op for op in ops if op.resource_type == "ad_group"]
    assert [g.resource_name for g in groups] == [
        f"customers/{CUSTOMER}/adGroups/-3",
        f"customers/{CUSTOMER}/adGroups/-4",
    ]
    keyword = next(op for op in ops if op.resource_type == "ad_group_criterion")
    assert keyword.fields == {
        "adGroup": groups[0].resource_name,
        "status": "ENABLED",
        "keyword": {"text": "pdf to word", "matchType": "PHRASE"},
    }
    ads = [op.fields for op in ops if op.resource_type == "ad_group_ad"]
    assert len(ads) == 2
    first = ads[0]["ad"]
    assert first["finalUrls"] == ["https://pdfezy.com/"]
    assert len(first["responsiveSearchAd"]["headlines"]) == 12
    assert first["responsiveSearchAd"]["descriptions"][0] == {"text": "One description."}


def test_no_ai_declaration_rides_on_a_search_ad() -> None:
    """The brief asks for `synthetic_content_info`; Google accepts it only on
    image and HTML5 ads, and refuses a responsive search ad that carries it."""
    sent = json.dumps([op.fields for op in _ops(a_plan(ai_written=True))])
    assert "synthetic" not in sent.lower()
    assert "ai_generated" not in sent.lower()


def test_everything_stopping_a_launch_is_said_together() -> None:
    plan = a_plan(
        daily_budget=0,
        final_url="pdfezy.com",
        places=[],
        not_political=False,
        themes=[Theme(name="pdf to word")],
    )
    said = missing(plan)
    assert "Set a daily budget." in said
    assert any("https://" in one for one in said)
    assert any("place" in one for one in said)
    assert any("no keywords" in one for one in said)
    assert any("political advertising" in one for one in said)
    assert missing(a_plan()) == []


def test_the_plan_survives_being_stored_and_read_back() -> None:
    plan = a_plan(business=Business(name="PDFezy", services=("pdf to word",)))
    again = CampaignPlan.from_dict(json.loads(json.dumps(plan.as_dict())))
    assert again == plan


def test_the_summary_is_built_from_the_plan_not_written_by_a_model() -> None:
    said = in_one_sentence(a_plan())
    assert said.startswith("We'll show your ads to people in Poland who search for")
    assert "20.00 USD a day" in said
    assert "https://pdfezy.com/" in said


def test_the_new_campaign_is_found_among_what_google_created() -> None:
    names = (
        "customers/1/campaignBudgets/9",
        "customers/1/campaigns/77",
        "customers/1/adGroups/5",
    )
    assert campaign_of(names) == "customers/1/campaigns/77"


def test_a_search_is_on_theme_only_if_it_has_every_word_of_it() -> None:
    assert on_theme("pdf to word converter", "pdf to word")
    assert on_theme("convert pdfs to word", "pdf to word"), "a plural is the same word"
    assert not on_theme("ilovepdf", "pdf to word"), "another company's name is not the theme"
    assert not on_theme("pdf editor", "pdf to word")
    assert not on_theme("anything", "to the")


def _demand(*terms: tuple[str, int]) -> Demand:
    return Demand(
        read=True,
        searches=[
            Search(term=t, monthly=m, competition="LOW", top_of_page_low=0.5, top_of_page_high=1.5)
            for t, m in terms
        ],
    )


def test_a_plan_is_built_from_real_searches_and_checked_copy(monkeypatch: Any) -> None:
    from ppcway.builder import build

    planner = {
        "pdf to word": _demand(
            ("pdf to word", 90000), ("pdf to word converter", 30000), ("ilovepdf", 500000)
        ),
        "unicorn repair": _demand(("unicorn repair", 2)),
    }
    monkeypatch.setattr(
        build,
        "write_copy",
        lambda models, **k: Written(
            headlines=tuple(f"H{n}" for n in range(11)), descriptions=("D1.", "D2."), asked=1
        ),
    )
    plan = build_plan(
        themes=["pdf to word", "unicorn repair", "pdf to word"],
        name="",
        daily_budget=15.0,
        currency="USD",
        final_url="https://pdfezy.com/",
        places=[Place("geoTargetConstants/2616", "Poland")],
        language=Place("languageConstants/1000", "English"),
        bidding="clicks",
        negatives=["jobs"],
        business=Business(name="PDFezy"),
        ask_planner=lambda theme: planner[theme],
        models=object(),  # type: ignore[arg-type]
    )
    assert [t.name for t in plan.themes] == ["pdf to word", "unicorn repair"], "deduplicated"
    pdf, unicorn = plan.themes
    assert [k["text"] for k in pdf.keywords] == ["pdf to word", "pdf to word converter"], (
        "only searches about the theme, busiest first; the other company's name never gets in"
    )
    assert len(pdf.headlines) == 11
    assert unicorn.keywords == [] and "too few people search" in unicorn.short
    assert plan.name == "pdf to word"
    assert plan.ai_written is True
