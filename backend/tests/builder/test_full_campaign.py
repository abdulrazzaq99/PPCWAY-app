"""A campaign built on Google's own steps becomes the request Google's guides describe.

Every assertion here is a rule Google states: the creation order, what may
not be sent any more, and what each setting is called in v25.
"""

from __future__ import annotations

import base64
import struct
from datetime import UTC, datetime, timedelta

import pytest

from ppcway.builder import images
from ppcway.builder.checks import blocking, problems, step_of
from ppcway.builder.ops import build
from ppcway.builder.spec import (
    CampaignSpec,
    is_v2,
    new_spec,
)

CUSTOMER = "2580586343"
TODAY = datetime.now(UTC).date()


def a_search(**overrides: object) -> CampaignSpec:
    data: dict[str, object] = {
        "objective": "leads",
        "type": "SEARCH",
        "name": "PDF tools",
        "currency": "CAD",
        "eu_political": False,
        "ways": {"website": True, "website_url": "https://pdfezy.com"},
        "locations": {
            "mode": "custom",
            "targets": [{"resource": "geoTargetConstants/2124", "name": "Canada"}],
            "excluded": [{"resource": "geoTargetConstants/9000093", "name": "Quebec"}],
            "radius": [{"label": "Toronto", "latitude": 43.65, "longitude": -79.38, "radius": 25}],
        },
        "budget": {"type": "daily", "amount": 20},
        "ad_groups": [
            {
                "name": "PDF to Word",
                "keywords": [
                    {"text": "pdf to word", "match": "BROAD"},
                    {"text": "convert pdf to word", "match": "EXACT"},
                ],
                "negatives": [{"text": "free download", "match": "PHRASE"}],
                "ads": [
                    {
                        "path1": "pdf",
                        "path2": "word",
                        "headlines": [
                            {"text": "Convert PDF to Word", "pin": "HEADLINE_1"},
                            {"text": "Fast and accurate"},
                            {"text": "Try PDFezy today"},
                            {"text": "try pdfezy today"},
                        ],
                        "descriptions": [
                            {"text": "Turn any PDF into an editable Word file in seconds."},
                            {"text": "No sign-up needed for your first file."},
                        ],
                    }
                ],
            }
        ],
    }
    data.update(overrides)
    return CampaignSpec.model_validate(data)


def _ops(spec: CampaignSpec) -> list:
    return list(build(spec, CUSTOMER, tag="abc12345", today=TODAY).together.operations)


def _of(spec: CampaignSpec, kind: str) -> list:
    return [op for op in _ops(spec) if op.resource_type == kind]


def test_search_follows_googles_creation_order() -> None:
    kinds = [op.resource_type for op in _ops(a_search())]
    first = {kind: kinds.index(kind) for kind in dict.fromkeys(kinds)}
    assert first["campaign_budget"] < first["campaign"] < first["campaign_criterion"]
    assert first["campaign_criterion"] < first["ad_group"] < first["ad_group_criterion"]
    assert first["ad_group_criterion"] < first["ad_group_ad"]
    # Same kinds sit together, which Google asks for so it can batch them.
    seen: list[str] = []
    for kind in kinds:
        if not seen or seen[-1] != kind:
            assert kind not in seen, f"{kind} is split into two runs"
            seen.append(kind)


def test_temporary_ids_are_unique_across_the_request() -> None:
    names = [op.resource_name for op in _ops(a_search()) if op.resource_name]
    ids = [n.rsplit("/", 1)[1] for n in names]
    assert len(ids) == len(set(ids))


def test_no_language_and_no_broad_match_setting_on_search() -> None:
    spec = a_search(languages=[{"resource": "languageConstants/1000", "name": "English"}])
    criteria = [op.fields for op in _of(spec, "campaign_criterion")]
    assert not any("language" in c for c in criteria)
    campaign = _of(spec, "campaign")[0].fields
    assert "keywordMatchType" not in campaign
    assert "manualCpc" not in campaign or "enhancedCpcEnabled" not in campaign["manualCpc"]


def test_google_defaults_are_sent_as_google_sets_them() -> None:
    campaign = _of(a_search(), "campaign")[0].fields
    assert campaign["networkSettings"]["targetSearchNetwork"] is True, "search partners ticked"
    assert campaign["networkSettings"]["targetContentNetwork"] is True, "Display Network ticked"
    assert campaign["geoTargetTypeSetting"] == {
        "positiveGeoTargetType": "PRESENCE_OR_INTEREST",
        "negativeGeoTargetType": "PRESENCE",
    }
    assert campaign["aiMaxSetting"] == {"enableAiMax": True}, "AI Max on for a new Search campaign"
    automation = {
        s["assetAutomationType"]: s["assetAutomationStatus"]
        for s in campaign["assetAutomationSettings"]
    }
    assert automation == {
        "TEXT_ASSET_AUTOMATION": "OPTED_IN",
        "FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION": "OPTED_IN",
    }
    assert campaign["maximizeConversions"] == {}
    assert campaign["containsEuPoliticalAdvertising"] == "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"


def test_ai_max_off_sends_none_of_its_settings() -> None:
    spec = a_search(ai_max={"enabled": False})
    campaign = _of(spec, "campaign")[0].fields
    assert "aiMaxSetting" not in campaign and "assetAutomationSettings" not in campaign


def test_search_term_matching_off_is_set_on_every_ad_group() -> None:
    spec = a_search(ai_max={"enabled": True, "search_term_matching": False})
    group = _of(spec, "ad_group")[0].fields
    assert group["aiMaxAdGroupSetting"] == {"disableSearchTermMatching": True}


@pytest.mark.parametrize(
    ("bidding", "expected"),
    [
        (
            {"focus": "conversions", "set_target": True, "target_cpa": 12.5},
            {"maximizeConversions": {"targetCpaMicros": "12500000"}},
        ),
        (
            {"focus": "conversion_value", "set_target": True, "target_roas": 350},
            {"maximizeConversionValue": {"targetRoas": 3.5}},
        ),
        (
            {
                "focus": "conversion_value",
                "set_target": True,
                "target_roas": 400,
                "explore": True,
                "explore_tolerance": 20,
            },
            {
                "maximizeConversionValue": {
                    "targetRoas": 4.0,
                    "targetRoasTolerancePercentMillis": "20000",
                }
            },
        ),
        ({"focus": "clicks"}, {"targetSpend": {}}),
        ({"focus": "clicks", "max_cpc": 2}, {"targetSpend": {"cpcBidCeilingMicros": "2000000"}}),
        (
            {
                "focus": "impression_share",
                "impression_location": "TOP_OF_PAGE",
                "impression_percent": 65,
                "impression_max_cpc": 3,
            },
            {
                "targetImpressionShare": {
                    "location": "TOP_OF_PAGE",
                    "locationFractionMicros": "650000",
                    "cpcBidCeilingMicros": "3000000",
                }
            },
        ),
        ({"strategy": "manual_cpc", "default_bid": 1.5}, {"manualCpc": {}}),
    ],
)
def test_bidding_is_googles_strategy_for_the_focus(bidding: dict, expected: dict) -> None:
    campaign = _of(a_search(bidding=bidding), "campaign")[0].fields
    sent = {
        k: v
        for k, v in campaign.items()
        if k
        in {
            "maximizeConversions",
            "maximizeConversionValue",
            "targetSpend",
            "targetImpressionShare",
            "manualCpc",
        }
    }
    assert sent == expected


def test_manual_cpc_puts_the_default_bid_on_ad_groups() -> None:
    spec = a_search(
        bidding={"strategy": "manual_cpc", "default_bid": 1.5}, ai_max={"enabled": False}
    )
    assert _of(spec, "ad_group")[0].fields["cpcBidMicros"] == "1500000"


def test_locations_radius_and_exclusions() -> None:
    criteria = [op.fields for op in _of(a_search(), "campaign_criterion")]
    assert any(
        c.get("location") == {"geoTargetConstant": "geoTargetConstants/2124"}
        and "negative" not in c
        for c in criteria
    )
    assert any(
        c.get("location") == {"geoTargetConstant": "geoTargetConstants/9000093"}
        and c.get("negative")
        for c in criteria
    )
    radius = next(c["proximity"] for c in criteria if "proximity" in c)
    assert radius == {
        "geoPoint": {"latitudeInMicroDegrees": 43650000, "longitudeInMicroDegrees": -79380000},
        "radius": 25.0,
        "radiusUnits": "KILOMETERS",
    }


def test_all_countries_sends_no_location() -> None:
    spec = a_search(locations={"mode": "all"})
    assert not any(
        "location" in op.fields or "proximity" in op.fields
        for op in _of(spec, "campaign_criterion")
    )


def test_schedule_devices_ip_and_audiences() -> None:
    spec = a_search(
        bidding={"focus": "clicks"},
        schedule=[
            {
                "day": "MONDAY",
                "start_hour": 9,
                "start_minute": 30,
                "end_hour": 17,
                "bid_adjustment": 20,
            }
        ],
        devices={"MOBILE": 30, "TABLET": -100, "DESKTOP": 0},
        ip_exclusions=["203.0.113.7", "203.0.113.7"],
        audiences={
            "mode": "observation",
            "segments": [{"kind": "user_list", "resource": "customers/1/userLists/9"}],
        },
    )
    criteria = [op.fields for op in _of(spec, "campaign_criterion")]
    schedule = next(c for c in criteria if "adSchedule" in c)
    assert schedule["adSchedule"] == {
        "dayOfWeek": "MONDAY",
        "startHour": 9,
        "startMinute": "THIRTY",
        "endHour": 17,
        "endMinute": "ZERO",
    }
    assert schedule["bidModifier"] == 1.2
    devices = {c["device"]["type"]: c["bidModifier"] for c in criteria if "device" in c}
    assert devices == {"MOBILE": 1.3, "TABLET": 0.0}, "no criterion for an unchanged device"
    assert [c["ipBlock"] for c in criteria if "ipBlock" in c] == [{"ipAddress": "203.0.113.7"}]
    assert any(c.get("userList") == {"userList": "customers/1/userLists/9"} for c in criteria)
    campaign = _of(spec, "campaign")[0].fields
    assert campaign["targetingSetting"] == {
        "targetRestrictions": [{"targetingDimension": "AUDIENCE", "bidOnly": True}]
    }


def test_keywords_keep_their_match_types_and_ads_drop_repeats() -> None:
    spec = a_search()
    keywords = [op.fields for op in _of(spec, "ad_group_criterion")]
    assert {"text": "convert pdf to word", "matchType": "EXACT"} in [k["keyword"] for k in keywords]
    assert any(k.get("negative") and k["keyword"]["matchType"] == "PHRASE" for k in keywords)
    ad = _of(spec, "ad_group_ad")[0].fields["ad"]
    rsa = ad["responsiveSearchAd"]
    assert [h["text"] for h in rsa["headlines"]] == [
        "Convert PDF to Word",
        "Fast and accurate",
        "Try PDFezy today",
    ]
    assert rsa["headlines"][0]["pinnedField"] == "HEADLINE_1"
    assert rsa["path1"] == "pdf" and rsa["path2"] == "word"
    assert ad["finalUrls"] == ["https://pdfezy.com"], "the website stands in for an empty final URL"


def test_assets_are_created_before_the_campaign_and_linked_after() -> None:
    spec = a_search(
        assets={
            "sitelinks": [
                {
                    "text": "Pricing",
                    "description1": "Plans from $5",
                    "description2": "Cancel anytime",
                    "final_url": "https://pdfezy.com/pricing",
                },
                {"text": "Merge PDF"},
            ],
            "callouts": ["No sign-up", "No sign-up", "Secure"],
            "snippets": [{"header": "Types", "values": ["Word", "Excel", "JPG"]}],
            "call": True,
            "call_country": "ca",
            "call_number": "+14165550100",
            "business_name": "PDFezy",
            "logo": {"asset": "customers/1/assets/77", "width": 1200, "height": 1200},
            "images": [{"asset": "customers/1/assets/78", "width": 1200, "height": 1200}],
        }
    )
    kinds = [op.resource_type for op in _ops(spec)]
    assert kinds.index("asset") < kinds.index("campaign") < kinds.index("campaign_asset")
    assets = [op.fields for op in _of(spec, "asset")]
    assert assets[0] == {
        "sitelinkAsset": {
            "linkText": "Pricing",
            "description1": "Plans from $5",
            "description2": "Cancel anytime",
        },
        "finalUrls": ["https://pdfezy.com/pricing"],
    }
    assert assets[1]["finalUrls"] == ["https://pdfezy.com"]
    assert [a["calloutAsset"]["calloutText"] for a in assets if "calloutAsset" in a] == [
        "No sign-up",
        "Secure",
    ]
    assert next(a for a in assets if "callAsset" in a)["callAsset"] == {
        "countryCode": "CA",
        "phoneNumber": "+14165550100",
    }
    kinds_linked = sorted(op.fields["fieldType"] for op in _of(spec, "campaign_asset"))
    assert kinds_linked == sorted(
        [
            "SITELINK",
            "SITELINK",
            "CALLOUT",
            "CALLOUT",
            "STRUCTURED_SNIPPET",
            "CALL",
            "BUSINESS_NAME",
            "BUSINESS_LOGO",
            "AD_IMAGE",
        ]
    )


def test_campaign_goals_are_set_with_the_temporary_campaign_id() -> None:
    spec = a_search(
        goals={
            "account_default": False,
            "chosen": [{"category": "SUBMIT_LEAD_FORM", "origin": "WEBSITE"}],
            "available": [
                {"category": "SUBMIT_LEAD_FORM", "origin": "WEBSITE"},
                {"category": "PURCHASE", "origin": "WEBSITE"},
            ],
        }
    )
    campaign = _of(spec, "campaign")[0].resource_name
    goals = _of(spec, "campaign_conversion_goal")
    temp = campaign.rsplit("/", 1)[1]
    assert [(g.resource_name.rsplit("/", 1)[1], g.fields["biddable"]) for g in goals] == [
        (f"{temp}~SUBMIT_LEAD_FORM~WEBSITE", True),
        (f"{temp}~PURCHASE~WEBSITE", False),
    ]
    assert all(g.update_mask == ("biddable",) for g in goals)


def test_account_goals_need_no_operation() -> None:
    assert _of(a_search(), "campaign_conversion_goal") == []


def test_brand_lists_and_url_exclusions_under_ai_max() -> None:
    spec = a_search(
        ai_max={
            "brand_exclusions": [{"id": "123", "name": "Adobe"}],
            "url_exclusions": ["https://pdfezy.com/careers", "/blog/"],
            "text_guidelines": {
                "term_exclusions": ["cheap"],
                "messaging_restrictions": ["Never mention discounts"],
            },
        }
    )
    sets = _of(spec, "shared_set")
    assert sets[0].fields["type"] == "BRANDS"
    assert _of(spec, "shared_criterion")[0].fields == {
        "sharedSet": sets[0].resource_name,
        "brand": {"entityId": "123"},
    }
    criteria = [op.fields for op in _of(spec, "campaign_criterion")]
    assert any(
        c.get("brandList") == {"sharedSet": sets[0].resource_name} and c.get("negative")
        for c in criteria
    )
    pages = [c["webpage"]["conditions"][0] for c in criteria if "webpage" in c]
    assert pages == [
        {"operand": "URL", "operator": "EQUALS", "argument": "https://pdfezy.com/careers"},
        {"operand": "URL", "operator": "CONTAINS", "argument": "/blog/"},
    ]
    campaign = _of(spec, "campaign")[0].fields
    assert campaign["textGuidelines"] == {
        "termExclusions": ["cheap"],
        "messagingRestrictions": [
            {
                "restrictionText": "Never mention discounts",
                "restrictionType": "RESTRICTION_BASED_EXCLUSION",
            }
        ],
    }


def test_dates_total_budget_and_url_options() -> None:
    start = TODAY + timedelta(days=3)
    end = TODAY + timedelta(days=30)
    spec = a_search(
        dates={"start": start.isoformat(), "end": end.isoformat()},
        budget={"type": "total", "amount": 600},
        url_options={
            "tracking_template": "{lpurl}?src=ads",
            "final_url_suffix": "?utm_source=google",
            "custom_parameters": [{"key": "_promo", "value": "fall"}],
        },
    )
    campaign = _of(spec, "campaign")[0].fields
    assert campaign["startDateTime"] == f"{start.isoformat()} 00:00:00"
    assert campaign["endDateTime"] == f"{end.isoformat()} 23:59:59"
    assert campaign["trackingUrlTemplate"] == "{lpurl}?src=ads"
    assert campaign["finalUrlSuffix"] == "utm_source=google"
    assert campaign["urlCustomParameters"] == [{"key": "promo", "value": "fall"}]
    budget = _of(spec, "campaign_budget")[0].fields
    assert budget["period"] == "CUSTOM_PERIOD" and budget["totalAmountMicros"] == "600000000"
    assert budget["explicitlyShared"] is False


def test_a_start_of_today_is_left_to_google() -> None:
    spec = a_search(dates={"start": TODAY.isoformat()})
    assert "startDateTime" not in _of(spec, "campaign")[0].fields


def test_a_shared_budget_replaces_the_new_one() -> None:
    spec = a_search(budget={"shared": "customers/1/campaignBudgets/55", "amount": 0})
    assert _of(spec, "campaign_budget") == []
    assert _of(spec, "campaign")[0].fields["campaignBudget"] == "customers/1/campaignBudgets/55"


def a_pmax(**overrides: object) -> CampaignSpec:
    img = lambda n, w, h: {"asset": f"customers/1/assets/{n}", "width": w, "height": h}
    data: dict[str, object] = {
        "objective": "sales",
        "type": "PERFORMANCE_MAX",
        "name": "PDFezy PMax",
        "currency": "CAD",
        "eu_political": False,
        "bidding": {"focus": "conversion_value", "set_target": True, "target_roas": 300},
        "locations": {"mode": "custom", "targets": [{"resource": "geoTargetConstants/2124"}]},
        "budget": {"amount": 30},
        "pmax": {
            "asset_group": {
                "final_url": "https://pdfezy.com",
                "headlines": ["PDF tools", "Convert any PDF", "Edit PDFs online"],
                "long_headlines": ["Every PDF tool you need, in your browser"],
                "descriptions": [
                    "Convert, merge and edit PDFs.",
                    "Fast, private PDF tools that work on any device.",
                ],
                "business_name": "PDFezy",
                "call_to_action": "SIGN_UP",
                "marketing_images": [img(1, 1200, 628)],
                "square_images": [img(2, 1200, 1200)],
                "logos": [img(3, 1200, 1200)],
                "videos": ["dQw4w9WgXcQ"],
                "search_themes": ["pdf converter", "merge pdf"],
            },
            "excluded_ages": ["AGE_RANGE_18_24"],
            "url_exclusions": ["/careers"],
        },
    }
    data.update(overrides)
    return CampaignSpec.model_validate(data)


def test_pmax_follows_the_structure_guide() -> None:
    kinds = [op.resource_type for op in _ops(a_pmax())]
    last_asset = max(i for i, k in enumerate(kinds) if k == "asset")
    assert last_asset < kinds.index("campaign") < kinds.index("asset_group")
    run = [i for i, k in enumerate(kinds) if k == "asset_group_asset"]
    assert run == list(range(run[0], run[0] + len(run))), (
        "the asset group's links are one unbroken run"
    )
    assert kinds.index("asset_group") < run[0]


def test_pmax_brand_assets_go_on_the_campaign_with_brand_guidelines() -> None:
    spec = a_pmax()
    on_campaign = sorted(op.fields["fieldType"] for op in _of(spec, "campaign_asset"))
    assert on_campaign == ["BUSINESS_NAME", "LOGO"]
    on_group = sorted({op.fields["fieldType"] for op in _of(spec, "asset_group_asset")})
    assert on_group == sorted(
        [
            "HEADLINE",
            "LONG_HEADLINE",
            "DESCRIPTION",
            "MARKETING_IMAGE",
            "SQUARE_MARKETING_IMAGE",
            "YOUTUBE_VIDEO",
            "CALL_TO_ACTION_SELECTION",
        ]
    )
    campaign = _of(spec, "campaign")[0].fields
    assert campaign["brandGuidelinesEnabled"] is True
    assert campaign["maximizeConversionValue"] == {"targetRoas": 3.0}
    assert "networkSettings" not in campaign, "Performance Max has no network choice"


def test_pmax_without_brand_guidelines_links_brand_assets_to_the_group() -> None:
    spec = a_pmax()
    spec.pmax.brand_guidelines.enabled = False
    assert _of(spec, "campaign_asset") == []
    kinds = {op.fields["fieldType"] for op in _of(spec, "asset_group_asset")}
    assert {"BUSINESS_NAME", "LOGO"} <= kinds


def test_pmax_keeps_language_and_sends_exclusions_and_signals() -> None:
    criteria = [op.fields for op in _of(a_pmax(), "campaign_criterion")]
    assert any(
        c.get("language") == {"languageConstant": "languageConstants/1000"} for c in criteria
    )
    assert any(
        c.get("ageRange") == {"type": "AGE_RANGE_18_24"} and c.get("negative") for c in criteria
    )
    assert any("webpage" in c and c.get("negative") for c in criteria)
    themes = [op.fields["searchTheme"]["text"] for op in _of(a_pmax(), "asset_group_signal")]
    assert themes == ["pdf converter", "merge pdf"]


def test_problems_are_filed_against_googles_steps() -> None:
    spec = new_spec(
        objective="leads", type_="SEARCH", name="", website="pdfezy", currency="CAD", time_zone=""
    )
    found = problems(spec, today=TODAY)
    steps = {p.step for p in blocking(found)}
    assert {"goal", "settings", "ads", "budget"} <= steps
    words = " ".join(p.words for p in found)
    assert "EU political" in words


def test_a_complete_search_campaign_has_no_blocking_problem() -> None:
    assert blocking(problems(a_search(), today=TODAY)) == []


def test_manual_cpc_with_ai_max_matching_is_flagged() -> None:
    spec = a_search(bidding={"strategy": "manual_cpc", "default_bid": 1})
    assert any("manual CPC" in p.words for p in problems(spec, today=TODAY))


def test_overpinned_ad_is_flagged() -> None:
    spec = a_search()
    for h in spec.ad_groups[0].ads[0].headlines:
        h.pin = "HEADLINE_1"
    assert any("pins too many" in p.words for p in problems(spec, today=TODAY))


def test_pmax_minimums_are_checked() -> None:
    spec = a_pmax()
    spec.pmax.asset_group.square_images = []
    spec.pmax.asset_group.descriptions = [
        "A description that is quite long and certainly over sixty characters.",
        "Another one, also very much longer than sixty characters in all of it.",
    ]
    words = " ".join(p.words for p in blocking(problems(spec, today=TODAY)))
    assert "square image" in words and "60 characters" in words
    assert blocking(problems(a_pmax(), today=TODAY)) == []


def test_google_errors_go_to_the_right_step() -> None:
    assert step_of("campaign", "maximize_conversions.target_cpa_micros", "SEARCH") == "bidding"
    assert step_of("campaign_budget", "amount_micros", "SEARCH") == "budget"
    assert step_of("ad_group_ad", "ad.responsive_search_ad.headlines", "SEARCH") == "ads"
    assert step_of("asset", "text_asset", "PERFORMANCE_MAX") == "asset_group"


def test_old_drafts_are_told_apart() -> None:
    assert is_v2(a_search().dump()) and not is_v2({"name": "x", "themes": []})


def test_round_trip_through_json() -> None:
    spec = a_pmax()
    again = CampaignSpec.model_validate(spec.dump())
    assert again == spec


def _png(width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
    )


def _jpeg(width: int, height: int) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


def test_images_are_measured_from_their_own_bytes() -> None:
    assert images.read(_png(1200, 628)) == images.Picture("image/png", 1200, 628)
    assert images.read(_jpeg(1200, 1200)) == images.Picture("image/jpeg", 1200, 1200)
    assert images.read(b"GIF89a" + struct.pack("<HH", 300, 300)) == images.Picture(
        "image/gif", 300, 300
    )
    with pytest.raises(images.NotAnImage):
        images.read(base64.b64decode("aGVsbG8="))


def test_image_shapes_follow_googles_specification() -> None:
    assert images.fits(images.Picture("image/png", 1200, 628), "landscape") == ""
    assert "1:1 square" in images.fits(images.Picture("image/png", 1200, 628), "square")
    assert "at least 300 by 300" in images.fits(images.Picture("image/png", 200, 200), "square")
    assert images.fits(images.Picture("image/png", 1200, 300), "landscape_logo") == ""
