"""Demand Gen, Display, Shopping and App campaigns become the requests Google documents.

Field names are the v25 protos'; each assertion is a rule Google states for
the type.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ppcway.builder.checks import blocking, problems
from ppcway.builder.ops import build
from ppcway.builder.spec import CampaignSpec

CUSTOMER = "2580586343"
TODAY = datetime.now(UTC).date()


def img(n: int, w: int, h: int) -> dict[str, object]:
    return {"asset": f"customers/1/assets/{n}", "width": w, "height": h}


def spec_of(kind: str, **extra: object) -> CampaignSpec:
    data: dict[str, object] = {
        "type": kind,
        "name": f"{kind} test",
        "currency": "CAD",
        "eu_political": False,
        "ways": {"website_url": "https://pdfezy.com"},
        "locations": {"mode": "custom", "targets": [{"resource": "geoTargetConstants/2124"}]},
        "budget": {"amount": 20},
        "assets": {"business_name": "PDFezy"},
    }
    data.update(extra)
    return CampaignSpec.model_validate(data)


def ops(spec: CampaignSpec) -> list:
    return list(build(spec, CUSTOMER, tag="t", today=TODAY).together.operations)


def of(spec: CampaignSpec, kind: str) -> list:
    return [op for op in ops(spec) if op.resource_type == kind]


def a_demand_gen(**dg: object) -> CampaignSpec:
    base: dict[str, object] = {
        "ads": [
            {
                "format": "image",
                "name": "Spring",
                "headlines": ["Edit PDFs anywhere"],
                "descriptions": ["Convert and edit PDFs in your browser."],
                "marketing_images": [img(1, 1200, 628)],
                "square_images": [img(2, 1200, 1200)],
                "logos": [img(3, 1200, 1200)],
                "call_to_action": "Sign up",
            },
            {
                "format": "video",
                "name": "Video",
                "headlines": ["PDF tools"],
                "long_headlines": ["Every PDF tool in your browser"],
                "descriptions": ["Fast and private."],
                "videos": ["dQw4w9WgXcQ"],
                "logos": [img(3, 1200, 1200)],
                "call_to_action": "SIGN_UP",
            },
            {
                "format": "carousel",
                "name": "Cards",
                "headlines": ["Our tools"],
                "descriptions": ["Pick a tool."],
                "logos": [img(3, 1200, 1200)],
                "cards": [
                    {"image": img(4, 1200, 1200), "headline": "Merge"},
                    {
                        "image": img(5, 1200, 628),
                        "headline": "Split",
                        "final_url": "https://pdfezy.com/split",
                    },
                ],
            },
        ]
    }
    base.update(dg)
    return spec_of("DEMAND_GEN", demand_gen=base, bidding={"focus": "conversions"})


def test_demand_gen_keeps_upgraded_targeting_with_places_on_the_ad_group() -> None:
    spec = a_demand_gen()
    campaign = of(spec, "campaign")[0].fields
    assert campaign["advertisingChannelType"] == "DEMAND_GEN"
    assert campaign["demandGenCampaignSettings"] == {"upgradedTargeting": True}
    assert not any("location" in op.fields for op in of(spec, "campaign_criterion"))
    group_places = [op.fields for op in of(spec, "ad_group_criterion") if "location" in op.fields]
    assert group_places and group_places[0]["location"] == {
        "geoTargetConstant": "geoTargetConstants/2124"
    }
    assert any("language" in op.fields for op in of(spec, "ad_group_criterion"))


def test_demand_gen_campaign_level_targeting_moves_places_to_the_campaign() -> None:
    spec = a_demand_gen(campaign_level_targeting=True)
    assert of(spec, "campaign")[0].fields["demandGenCampaignSettings"] == {
        "upgradedTargeting": False
    }
    assert any("location" in op.fields for op in of(spec, "campaign_criterion"))


def test_demand_gen_channels_all_or_chosen() -> None:
    group = of(a_demand_gen(), "ad_group")[0].fields
    assert group["demandGenAdGroupSettings"] == {
        "channelControls": {"channelStrategy": "ALL_CHANNELS"}
    }
    assert "type" not in group, "Demand Gen ad groups leave type unset"
    chosen = of(a_demand_gen(channels="choose", selected=["youtube_shorts", "gmail"]), "ad_group")[
        0
    ].fields
    selected = chosen["demandGenAdGroupSettings"]["channelControls"]["selectedChannels"]
    assert (
        selected["youtubeShorts"] is True
        and selected["gmail"] is True
        and selected["display"] is False
    )


def test_demand_gen_ads_use_each_formats_own_fields() -> None:
    spec = a_demand_gen()
    ads = [op.fields["ad"] for op in of(spec, "ad_group_ad")]
    image, video, carousel = ads
    multi = image["demandGenMultiAssetAd"]
    assert multi["marketingImages"] == [{"asset": "customers/1/assets/1"}]
    assert multi["businessName"] == "PDFezy", "a plain string on the image ad"
    assert multi["callToActionText"] == "Sign up"
    responsive = video["demandGenVideoResponsiveAd"]
    assert responsive["businessName"] == {"text": "PDFezy"}, "a text asset on the video ad"
    assert responsive["videos"][0]["asset"].startswith(f"customers/{CUSTOMER}/assets/-")
    assert responsive["callToActions"][0]["asset"].startswith(f"customers/{CUSTOMER}/assets/-")
    cards = carousel["demandGenCarouselAd"]["carouselCards"]
    assert len(cards) == 2
    card_assets = [
        op.fields for op in of(spec, "asset") if "demandGenCarouselCardAsset" in op.fields
    ]
    assert "squareMarketingImageAsset" in card_assets[0]["demandGenCarouselCardAsset"]
    assert "marketingImageAsset" in card_assets[1]["demandGenCarouselCardAsset"]
    assert card_assets[1]["finalUrls"] == ["https://pdfezy.com/split"]


def test_demand_gen_target_cpc_only_when_bidding_for_clicks() -> None:
    spec = a_demand_gen(target_cpc=0.8)
    spec.bidding.focus = "clicks"
    assert of(spec, "campaign")[0].fields["targetCpc"] == {"targetCpcMicros": "800000"}


def test_demand_gen_audience_goes_through_an_audience() -> None:
    spec = a_demand_gen(segments=[{"kind": "user_list", "resource": "customers/1/userLists/9"}])
    audience = of(spec, "audience")[0]
    criterion = next(op.fields for op in of(spec, "ad_group_criterion") if "audience" in op.fields)
    assert criterion["audience"] == {"audience": audience.resource_name}


def test_a_complete_demand_gen_campaign_passes_and_gaps_are_named() -> None:
    assert blocking(problems(a_demand_gen(), today=TODAY)) == []
    empty = spec_of("DEMAND_GEN", demand_gen={"ads": [{"format": "video"}]})
    words = " ".join(p.words for p in blocking(problems(empty, today=TODAY)))
    assert "YouTube video" in words and "square logo" in words


def a_display() -> CampaignSpec:
    return spec_of(
        "DISPLAY",
        bidding={"focus": "conversions"},
        display={
            "headlines": ["PDF tools"],
            "long_headline": "Every PDF tool you need, in your browser",
            "descriptions": ["Convert and edit PDFs."],
            "marketing_images": [img(1, 1200, 628)],
            "square_images": [img(2, 1200, 1200)],
            "logos": [img(3, 1200, 1200)],
            "keywords": ["pdf editor"],
        },
    )


def test_display_is_a_responsive_display_ad_in_a_standard_ad_group() -> None:
    spec = a_display()
    assert of(spec, "campaign")[0].fields["advertisingChannelType"] == "DISPLAY"
    assert of(spec, "ad_group")[0].fields["type"] == "DISPLAY_STANDARD"
    rda = of(spec, "ad_group_ad")[0].fields["ad"]["responsiveDisplayAd"]
    assert rda["longHeadline"] == {"text": "Every PDF tool you need, in your browser"}
    assert rda["squareLogoImages"] == [{"asset": "customers/1/assets/3"}]
    assert blocking(problems(spec, today=TODAY)) == []


def test_shopping_needs_a_merchant_and_builds_one_product_group() -> None:
    spec = spec_of(
        "SHOPPING",
        shopping={"merchant_id": 123456, "priority": 1, "default_bid": 0.5},
        bidding={"strategy": "manual_cpc", "default_bid": 0.5},
    )
    campaign = of(spec, "campaign")[0].fields
    assert campaign["shoppingSetting"]["merchantId"] == "123456"
    assert campaign["shoppingSetting"]["campaignPriority"] == 1
    assert campaign["networkSettings"]["targetContentNetwork"] is False
    assert of(spec, "ad_group")[0].fields["type"] == "SHOPPING_PRODUCT_ADS"
    root = next(op.fields for op in of(spec, "ad_group_criterion") if "listingGroup" in op.fields)
    assert root["listingGroup"] == {"type": "UNIT"} and root["cpcBidMicros"] == "500000"
    assert of(spec, "ad_group_ad")[0].fields["ad"] == {"shoppingProductAd": {}}
    no_merchant = spec_of("SHOPPING", bidding={"focus": "clicks"})
    assert any("Merchant Center" in p.words for p in blocking(problems(no_merchant, today=TODAY)))


def test_app_campaign_goal_follows_focus_and_target() -> None:
    spec = spec_of(
        "APP",
        app={
            "app_id": "com.pdfezy.app",
            "focus": "installs",
            "target_cpa": 2,
            "headlines": ["Edit PDFs on the go"],
            "descriptions": ["The PDF app for everything."],
        },
    )
    campaign = of(spec, "campaign")[0].fields
    assert campaign["advertisingChannelType"] == "MULTI_CHANNEL"
    assert campaign["advertisingChannelSubType"] == "APP_CAMPAIGN"
    assert campaign["appCampaignSetting"] == {
        "appId": "com.pdfezy.app",
        "appStore": "GOOGLE_APP_STORE",
        "biddingStrategyGoalType": "OPTIMIZE_INSTALLS_TARGET_INSTALL_COST",
    }
    assert campaign["targetCpa"] == {"targetCpaMicros": "2000000"}
    assert of(spec, "campaign_budget")[0].fields["amountMicros"] == "20000000"
    assert "type" not in of(spec, "ad_group")[0].fields
    assert blocking(problems(spec, today=TODAY)) == []
    spec.app.focus = "in_app_value"
    spec.app.target_roas = None
    assert (
        of(spec, "campaign")[0].fields["appCampaignSetting"]["biddingStrategyGoalType"]
        == "OPTIMIZE_TOTAL_VALUE_WITHOUT_TARGET_ROAS"
    )


def test_budget_problems_move_to_bidding_where_there_is_no_budget_step() -> None:
    spec = a_demand_gen()
    spec.budget.amount = 0
    assert any(p.step == "bidding" and "budget" in p.words for p in problems(spec, today=TODAY))


def test_a_radius_is_sent_where_google_takes_one_and_refused_where_it_does_not() -> None:
    radius = {"label": "Toronto", "latitude": 43.65, "longitude": -79.38, "radius": 15}
    display = spec_of(
        "DISPLAY",
        bidding={"focus": "conversions"},
        locations={"mode": "custom", "targets": [], "radius": [radius]},
        display=a_display().display.model_dump(),
    )
    assert any("proximity" in op.fields for op in of(display, "campaign_criterion"))
    dg = a_demand_gen()
    dg.locations = display.locations
    assert not any("proximity" in op.fields for op in of(dg, "ad_group_criterion"))
    assert any("campaign level" in p.words for p in blocking(problems(dg, today=TODAY)))
    dg.demand_gen.campaign_level_targeting = True
    assert any("proximity" in op.fields for op in of(dg, "campaign_criterion"))


def test_shopping_and_app_send_the_location_option() -> None:
    shop = spec_of("SHOPPING", shopping={"merchant_id": 1}, bidding={"focus": "clicks"})
    shop.locations.target_option = "PRESENCE"
    assert (
        of(shop, "campaign")[0].fields["geoTargetTypeSetting"]["positiveGeoTargetType"]
        == "PRESENCE"
    )


def test_each_app_subtype_sends_its_own_ad_and_chosen_conversions() -> None:
    base = {
        "app_id": "com.pdfezy.app",
        "headlines": ["Edit PDFs"],
        "descriptions": ["The PDF app."],
        "videos": ["dQw4w9WgXcQ"],
    }
    installs = spec_of("APP", app=base)
    assert "appAd" in of(installs, "ad_group_ad")[0].fields["ad"]
    assert "selectiveOptimization" not in of(installs, "campaign")[0].fields
    engage = spec_of(
        "APP",
        app={
            **base,
            "subtype": "APP_CAMPAIGN_FOR_ENGAGEMENT",
            "focus": "in_app_actions",
            "conversion_actions": ["customers/1/conversionActions/5"],
        },
        audiences={"segments": [{"kind": "user_list", "resource": "customers/1/userLists/2"}]},
    )
    ad = of(engage, "ad_group_ad")[0].fields["ad"]
    assert "appEngagementAd" in ad and "videos" in ad["appEngagementAd"]
    assert of(engage, "campaign")[0].fields["selectiveOptimization"] == {
        "conversionActions": ["customers/1/conversionActions/5"]
    }
    pre = spec_of("APP", app={**base, "subtype": "APP_CAMPAIGN_FOR_PRE_REGISTRATION"})
    assert "appPreRegistrationAd" in of(pre, "ad_group_ad")[0].fields["ad"]
    bad = spec_of(
        "APP", app={**base, "subtype": "APP_CAMPAIGN_FOR_ENGAGEMENT", "focus": "installs"}
    )
    assert any("not installs" in p.words for p in blocking(problems(bad, today=TODAY)))


def test_step_names_follow_google_for_each_type() -> None:
    from ppcway.builder.spec import step_labels

    assert step_labels("SEARCH")["bidding"] == "Bidding"
    assert step_labels("SEARCH")["ads"] == "Keywords and ads"
    assert step_labels("DEMAND_GEN")["bidding"] == "Bidding and budget"
    assert step_labels("APP")["ads"] == "Ads"
