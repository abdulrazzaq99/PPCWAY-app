"""A whole new campaign as the one all-or-nothing request Google takes.

`spec.CampaignSpec` is what the merchant chose, step by step, on screens that
follow Google's own. This turns it into a `Together`: every operation in the
order Google's guides give for creating a campaign in one request, each
pointing at the others by temporary (negative) ids, applied whole or not at
all. Checked first with `validateOnly` by `gateway.create`, like every launch.

**The order is Google's.** Search follows its recommended creation order
(the budget, shared lists and their entries, new assets, the campaign, its
criteria, list and asset links, goals, ad groups, keywords, ads). Performance
Max follows its structure guide, which is stricter: every new asset before
the asset group, and the asset group's links in one unbroken run after it,
or Google checks the asset minimums too early and refuses the lot.

**What never goes in, whatever the screen holds:** a language on a Search
campaign, the campaign-level broad match setting, Enhanced CPC, and a start
date in the past. Google refuses each one, and one refusal here is the whole
campaign refused.

**Images are not uploaded here.** They are already in the account's asset
library, put there when the merchant added them (`gateway.assets`), the way
Google's own screens do it; this request only links them.

Field names are Google Ads API v25's REST names, checked against its
reference; the research is in `docs/reference/campaign-creation/`.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Final

from ppcway.builder.spec import AdGroup, Brand, CampaignSpec, Image, Segment, Sitelink
from ppcway.gateway.port import Doing, Operation, Together

#: Google's minute values for an ad schedule.
_MINUTE: Final = {0: "ZERO", 15: "FIFTEEN", 30: "THIRTY", 45: "FORTY_FIVE"}

#: Google's identifiers for the devices a Search campaign can adjust bids on.
DEVICES: Final = ("DESKTOP", "MOBILE", "TABLET", "CONNECTED_TV")

#: Responsive search ad limits (Google Ads Help 7684791).
HEADLINES_MOST: Final = 15
DESCRIPTIONS_MOST: Final = 4
ADS_PER_GROUP: Final = 3


def micros(amount: float | None) -> str:
    """Money in micros, as the decimal string REST wants for an int64."""
    return str(round((amount or 0) * 1_000_000))


@dataclass
class _Ids:
    """Temporary ids, unique across the whole request as Google requires."""

    customer_id: str
    _next: Iterator[int] = field(default_factory=lambda: itertools.count(1))

    def name(self, path: str) -> str:
        return f"customers/{self.customer_id}/{path}/-{next(self._next)}"


@dataclass(frozen=True, slots=True)
class Built:
    """The request, and what has to happen after it, which cannot go inside it."""

    together: Together
    #: Google keeps new-customer bidding out of the all-or-nothing request
    #: (`GoalService` and `CampaignGoalConfigService` are not mutate
    #: operations), so it is set once the campaign exists.
    new_customers: str = "off"


def build(spec: CampaignSpec, customer_id: str, *, tag: str, today: date) -> Built:
    """The campaign as one request. `tag` keeps the budget's name unique."""
    writers = {
        "SEARCH": _search,
        "PERFORMANCE_MAX": _pmax,
        "DEMAND_GEN": _demand_gen,
        "DISPLAY": _display,
        "SHOPPING": _shopping,
        "APP": _app,
    }
    if spec.type not in writers:
        raise ValueError(f"{spec.type} campaigns are not built by this request")
    ops = writers[spec.type](spec, _Ids(customer_id), tag=tag, today=today)
    return Built(
        together=Together(customer_id=customer_id, operations=tuple(ops)),
        new_customers=spec.bidding.new_customers,
    )


def _create(resource_type: str, fields: dict[str, Any], name: str | None = None) -> Operation:
    return Operation(
        resource_type=resource_type, doing=Doing.CREATE, resource_name=name, fields=fields
    )


# --- the parts every type shares --------------------------------------------


def _budget(
    spec: CampaignSpec, ids: _Ids, *, tag: str, daily_only: bool = False
) -> tuple[str, list[Operation]]:
    """The budget, or the shared budget the merchant picked instead."""
    if spec.budget.shared:
        return spec.budget.shared, []
    name = ids.name("campaignBudgets")
    fields: dict[str, Any] = {
        "name": f"{spec.name} · {tag}",
        "deliveryMethod": "STANDARD",
        # Google makes a new budget shared unless told otherwise.
        "explicitlyShared": False,
    }
    if spec.budget.type == "total" and not daily_only:
        fields["period"] = "CUSTOM_PERIOD"
        fields["totalAmountMicros"] = micros(spec.budget.amount)
    else:
        fields["amountMicros"] = micros(spec.budget.amount)
    return name, [_create("campaign_budget", fields, name)]


def _dates(spec: CampaignSpec, today: date) -> dict[str, Any]:
    """Start and end, in the account's time zone, as v25 spells them.

    A start of today or earlier is left out: Google starts a campaign now by
    default, and refuses a start in the past (`CANNOT_SET_DATE_TO_PAST`).
    """
    out: dict[str, Any] = {}
    if spec.dates.start and spec.dates.start > today:
        out["startDateTime"] = f"{spec.dates.start.isoformat()} 00:00:00"
    if spec.dates.end:
        out["endDateTime"] = f"{spec.dates.end.isoformat()} 23:59:59"
    return out


def _url_options(spec: CampaignSpec) -> dict[str, Any]:
    out: dict[str, Any] = {}
    options = spec.url_options
    if options.tracking_template.strip():
        out["trackingUrlTemplate"] = options.tracking_template.strip()
    if options.final_url_suffix.strip():
        out["finalUrlSuffix"] = options.final_url_suffix.strip().lstrip("?")
    params = [
        {"key": str(p.get("key", "")).strip().lstrip("_"), "value": str(p.get("value", "")).strip()}
        for p in options.custom_parameters
        if str(p.get("key", "")).strip()
    ][:8]
    if params:
        out["urlCustomParameters"] = params
    return out


def _bidding(spec: CampaignSpec) -> dict[str, Any]:
    """Google's bid strategy for what the merchant said to focus on."""
    b = spec.bidding
    if spec.type == "SEARCH" and b.strategy == "manual_cpc":
        # Enhanced CPC has done nothing on Search since March 2025; never sent.
        return {"manualCpc": {}}
    if b.focus == "conversion_value":
        inner: dict[str, Any] = {}
        if b.set_target and b.target_roas:
            inner["targetRoas"] = round(b.target_roas / 100, 4)
            if b.explore:
                tolerance = min(30, max(10, b.explore_tolerance))
                inner["targetRoasTolerancePercentMillis"] = str(tolerance * 1000)
        return {"maximizeConversionValue": inner}
    if b.focus == "clicks" and spec.type != "PERFORMANCE_MAX":
        return {"targetSpend": {"cpcBidCeilingMicros": micros(b.max_cpc)} if b.max_cpc else {}}
    if b.focus == "impression_share" and spec.type == "SEARCH":
        return {
            "targetImpressionShare": {
                "location": b.impression_location,
                "locationFractionMicros": str(round((b.impression_percent or 0) * 10_000)),
                "cpcBidCeilingMicros": micros(b.impression_max_cpc),
            }
        }
    inner = {}
    if b.set_target and b.target_cpa:
        inner["targetCpaMicros"] = micros(b.target_cpa)
    return {"maximizeConversions": inner}


def _text_guidelines(term_exclusions: list[str], restrictions: list[str]) -> dict[str, Any]:
    terms = [t.strip()[:30] for t in term_exclusions if t.strip()][:25]
    rules = [r.strip()[:300] for r in restrictions if r.strip()][:40]
    if not terms and not rules:
        return {}
    out: dict[str, Any] = {}
    if terms:
        out["termExclusions"] = terms
    if rules:
        out["messagingRestrictions"] = [
            {"restrictionText": r, "restrictionType": "RESTRICTION_BASED_EXCLUSION"} for r in rules
        ]
    return {"textGuidelines": out}


def _automation(text: bool, url_expansion: bool) -> dict[str, Any]:
    return {
        "assetAutomationSettings": [
            {
                "assetAutomationType": "TEXT_ASSET_AUTOMATION",
                "assetAutomationStatus": "OPTED_IN" if text else "OPTED_OUT",
            },
            {
                "assetAutomationType": "FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION",
                # Final URL expansion needs text customization on.
                "assetAutomationStatus": "OPTED_IN" if text and url_expansion else "OPTED_OUT",
            },
        ]
    }


def _criterion(campaign: str, fields: dict[str, Any], *, negative: bool = False) -> Operation:
    body = {"campaign": campaign, **fields}
    if negative:
        body["negative"] = True
    return _create("campaign_criterion", body)


def _places(spec: CampaignSpec, campaign: str) -> list[Operation]:
    """Where the ads show: everywhere, the home country, or a chosen list."""
    loc = spec.locations
    ops: list[Operation] = []
    if loc.mode == "home" and loc.home:
        ops.append(_criterion(campaign, {"location": {"geoTargetConstant": loc.home.resource}}))
    elif loc.mode == "custom":
        for place in loc.targets:
            ops.append(_criterion(campaign, {"location": {"geoTargetConstant": place.resource}}))
        for circle in loc.radius:
            ops.append(
                _criterion(
                    campaign,
                    {
                        "proximity": {
                            "geoPoint": {
                                "latitudeInMicroDegrees": round(circle.latitude * 1_000_000),
                                "longitudeInMicroDegrees": round(circle.longitude * 1_000_000),
                            },
                            "radius": circle.radius,
                            "radiusUnits": circle.units,
                        }
                    },
                )
            )
    if loc.mode != "all" or loc.excluded:
        for place in loc.excluded:
            ops.append(
                _criterion(
                    campaign, {"location": {"geoTargetConstant": place.resource}}, negative=True
                )
            )
    return ops


def _schedule(spec: CampaignSpec, campaign: str, *, adjust: bool) -> list[Operation]:
    ops: list[Operation] = []
    for entry in spec.schedule:
        fields: dict[str, Any] = {
            "adSchedule": {
                "dayOfWeek": entry.day,
                "startHour": entry.start_hour,
                "startMinute": _MINUTE[entry.start_minute],
                "endHour": entry.end_hour,
                "endMinute": _MINUTE[entry.end_minute],
            }
        }
        if adjust and entry.bid_adjustment:
            fields["bidModifier"] = round(1 + entry.bid_adjustment / 100, 4)
        ops.append(_criterion(campaign, fields))
    return ops


def _negatives(spec: CampaignSpec, campaign: str) -> list[Operation]:
    seen: set[tuple[str, str]] = set()
    ops: list[Operation] = []
    for word in spec.negatives:
        text = " ".join(word.text.lower().split())
        if not text or (text, word.match) in seen:
            continue
        seen.add((text, word.match))
        ops.append(
            _criterion(
                campaign, {"keyword": {"text": text, "matchType": word.match}}, negative=True
            )
        )
    return ops


def _url_exclusions(urls: list[str], campaign: str) -> list[Operation]:
    """Pages final URL expansion must not send people to.

    A whole address is matched exactly; anything else is a "URL contains" rule,
    which is how Google's screen offers the two.
    """
    ops: list[Operation] = []
    for at, raw in enumerate(dict.fromkeys(u.strip() for u in urls if u.strip())):
        whole = raw.startswith(("http://", "https://"))
        ops.append(
            _criterion(
                campaign,
                {
                    "webpage": {
                        "criterionName": f"Excluded {at + 1}",
                        "conditions": [
                            {
                                "operand": "URL",
                                "operator": "EQUALS" if whole else "CONTAINS",
                                "argument": raw,
                            }
                        ],
                    }
                },
                negative=True,
            )
        )
    return ops


def _brand_list(
    ids: _Ids, brands: list[Brand], *, name: str
) -> tuple[str, list[Operation], list[Operation]]:
    """A brand list as Google keeps one: a shared set and one entry per brand."""
    shared = ids.name("sharedSets")
    sets = [_create("shared_set", {"name": name, "type": "BRANDS"}, shared)]
    entries = [
        _create("shared_criterion", {"sharedSet": shared, "brand": {"entityId": str(b.id)}})
        for b in brands
    ]
    return shared, sets, entries


def _segment(segment: Segment) -> dict[str, Any]:
    if segment.kind == "user_list":
        return {"userList": {"userList": segment.resource}}
    if segment.kind == "user_interest":
        return {"userInterest": {"userInterestCategory": segment.resource}}
    if segment.kind == "custom_audience":
        return {"customAudience": {"customAudience": segment.resource}}
    return {"combinedAudience": {"combinedAudience": segment.resource}}


def _goals(spec: CampaignSpec, campaign: str) -> list[Operation]:
    """Campaign-specific goals, in the same request as the campaign.

    Google's own sample does this with the temporary campaign id. Following
    the account's goals needs no operation at all: that is a new campaign's
    default.
    """
    if spec.goals.account_default:
        return []
    chosen = {(g.category, g.origin) for g in spec.goals.chosen}
    ops: list[Operation] = []
    for pair in spec.goals.available:
        ops.append(
            Operation(
                resource_type="campaign_conversion_goal",
                doing=Doing.UPDATE,
                resource_name=f"{campaign.replace('/campaigns/', '/campaignConversionGoals/')}"
                f"~{pair.category}~{pair.origin}",
                fields={"biddable": (pair.category, pair.origin) in chosen},
                update_mask=("biddable",),
            )
        )
    return ops


def _sitelink_asset(ids: _Ids, link: Sitelink, fallback_url: str) -> tuple[str, Operation]:
    name = ids.name("assets")
    sitelink: dict[str, Any] = {"linkText": link.text.strip()[:25]}
    if link.description1.strip() and link.description2.strip():
        sitelink["description1"] = link.description1.strip()[:35]
        sitelink["description2"] = link.description2.strip()[:35]
    return name, _create(
        "asset",
        {"sitelinkAsset": sitelink, "finalUrls": [link.final_url.strip() or fallback_url]},
        name,
    )


# --- Search -----------------------------------------------------------------


def _search(spec: CampaignSpec, ids: _Ids, *, tag: str, today: date) -> list[Operation]:
    budget, budget_ops = _budget(spec, ids, tag=tag)
    ai = spec.ai_max
    landing = spec.final_url

    lists: list[Operation] = []
    entries: list[Operation] = []
    include_list = exclude_list = ""
    if ai.enabled and ai.brand_inclusions:
        include_list, sets, more = _brand_list(
            ids, ai.brand_inclusions, name=f"{spec.name} brands · {tag}"
        )
        lists += sets
        entries += more
    if ai.enabled and ai.brand_exclusions:
        exclude_list, sets, more = _brand_list(
            ids, ai.brand_exclusions, name=f"{spec.name} excluded brands · {tag}"
        )
        lists += sets
        entries += more

    assets, links = _search_assets(spec, ids, landing)

    campaign = ids.name("campaigns")
    fields: dict[str, Any] = {
        "name": spec.name,
        "status": "ENABLED",
        "advertisingChannelType": "SEARCH",
        "campaignBudget": budget,
        "networkSettings": {
            "targetGoogleSearch": True,
            "targetSearchNetwork": spec.networks.search_partners,
            "targetContentNetwork": spec.networks.display,
            "targetPartnerSearchNetwork": False,
        },
        "geoTargetTypeSetting": {
            "positiveGeoTargetType": spec.locations.target_option,
            "negativeGeoTargetType": "PRESENCE",
        },
        "containsEuPoliticalAdvertising": (
            "CONTAINS_EU_POLITICAL_ADVERTISING"
            if spec.eu_political
            else "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"
        ),
        **_bidding(spec),
        **_dates(spec, today),
        **_url_options(spec),
    }
    if ai.enabled:
        fields["aiMaxSetting"] = {"enableAiMax": True}
        fields.update(_automation(ai.text_customization, ai.final_url_expansion))
        if ai.text_customization:
            fields.update(
                _text_guidelines(
                    ai.text_guidelines.term_exclusions, ai.text_guidelines.messaging_restrictions
                )
            )
    if spec.audiences.segments:
        fields["targetingSetting"] = {
            "targetRestrictions": [
                {"targetingDimension": "AUDIENCE", "bidOnly": spec.audiences.mode == "observation"}
            ]
        }

    manual = spec.bidding.strategy == "manual_cpc"
    adjustable = manual or spec.bidding.focus == "clicks"
    criteria = _places(spec, campaign)
    criteria += _schedule(spec, campaign, adjust=adjustable)
    for device in DEVICES:
        adjustment = spec.devices.get(device)
        if adjustment is None or adjustment == 0 or device == "CONNECTED_TV":
            continue
        modifier = 0.0 if adjustment <= -100 else round(1 + adjustment / 100, 4)
        criteria.append(_criterion(campaign, {"device": {"type": device}, "bidModifier": modifier}))
    criteria += _negatives(spec, campaign)
    for address in dict.fromkeys(a.strip() for a in spec.ip_exclusions if a.strip()):
        criteria.append(_criterion(campaign, {"ipBlock": {"ipAddress": address}}, negative=True))
    for segment in spec.audiences.segments:
        criteria.append(_criterion(campaign, _segment(segment), negative=segment.excluded))
    if include_list:
        criteria.append(_criterion(campaign, {"brandList": {"sharedSet": include_list}}))
    if exclude_list:
        criteria.append(
            _criterion(campaign, {"brandList": {"sharedSet": exclude_list}}, negative=True)
        )
    if ai.enabled and ai.text_customization and ai.final_url_expansion:
        criteria += _url_exclusions(ai.url_exclusions, campaign)

    shared_links = [
        _create("campaign_shared_set", {"campaign": campaign, "sharedSet": str(item["resource"])})
        for item in spec.negative_lists
        if str(item.get("resource", "")).startswith("customers/")
    ]
    asset_links = [
        _create("campaign_asset", {"campaign": campaign, "asset": asset, "fieldType": kind})
        for asset, kind in links
    ]

    groups: list[Operation] = []
    group_criteria: list[Operation] = []
    ads: list[Operation] = []
    for group in spec.ad_groups:
        name = ids.name("adGroups")
        groups.append(_create("ad_group", _ad_group_fields(spec, group, campaign, manual), name))
        group_criteria += _keywords(group, name, ai_max=ai.enabled)
        for ad in group.ads[:ADS_PER_GROUP]:
            ads.append(_create("ad_group_ad", _search_ad(ad, name, landing)))

    return [
        *budget_ops,
        *lists,
        *entries,
        *assets,
        _create("campaign", fields, campaign),
        *criteria,
        *shared_links,
        *asset_links,
        *_goals(spec, campaign),
        *groups,
        *group_criteria,
        *ads,
    ]


def _ad_group_fields(
    spec: CampaignSpec, group: AdGroup, campaign: str, manual: bool
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "name": group.name.strip()[:255] or "Ad group",
        "campaign": campaign,
        "status": "ENABLED",
        "type": "SEARCH_STANDARD",
    }
    if manual and (group.default_bid or spec.bidding.default_bid):
        fields["cpcBidMicros"] = micros(group.default_bid or spec.bidding.default_bid)
    # Smart Bidding always optimises rotation; the choice exists for the rest.
    if spec.ad_rotation == "ROTATE_FOREVER" and (manual or spec.bidding.focus == "clicks"):
        fields["adRotationMode"] = "ROTATE_FOREVER"
    if spec.ai_max.enabled and not spec.ai_max.search_term_matching:
        fields["aiMaxAdGroupSetting"] = {"disableSearchTermMatching": True}
    return fields


def _keywords(group: AdGroup, ad_group: str, *, ai_max: bool) -> list[Operation]:
    ops: list[Operation] = []
    seen: set[tuple[str, str, bool]] = set()
    for word, negative in [(k, False) for k in group.keywords] + [
        (k, True) for k in group.negatives
    ]:
        text = " ".join(word.text.split())[:80]
        key = (text.lower(), word.match, negative)
        if not text or key in seen:
            continue
        seen.add(key)
        fields: dict[str, Any] = {
            "adGroup": ad_group,
            "keyword": {"text": text, "matchType": word.match},
        }
        if negative:
            fields["negative"] = True
        else:
            fields["status"] = "ENABLED"
        ops.append(_create("ad_group_criterion", fields))
    if ai_max:
        for place in group.locations_of_interest:
            ops.append(
                _create(
                    "ad_group_criterion",
                    {"adGroup": ad_group, "location": {"geoTargetConstant": place.resource}},
                )
            )
    return ops


def _search_ad(ad: Any, ad_group: str, landing: str) -> dict[str, Any]:
    def assets(items: list[Any], most: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            text = item.text.strip()
            # Google refuses the same text twice in one ad (DUPLICATE_ASSET).
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())
            one: dict[str, Any] = {"text": text}
            if item.pin:
                one["pinnedField"] = item.pin
            out.append(one)
        return out[:most]

    rsa: dict[str, Any] = {
        "headlines": assets(ad.headlines, HEADLINES_MOST),
        "descriptions": assets(ad.descriptions, DESCRIPTIONS_MOST),
    }
    if ad.path1.strip():
        rsa["path1"] = ad.path1.strip()[:15]
        if ad.path2.strip():
            rsa["path2"] = ad.path2.strip()[:15]
    return {
        "adGroup": ad_group,
        "status": "ENABLED",
        "ad": {"finalUrls": [ad.final_url.strip() or landing], "responsiveSearchAd": rsa},
    }


def _search_assets(
    spec: CampaignSpec, ids: _Ids, landing: str
) -> tuple[list[Operation], list[tuple[str, str]]]:
    """New assets, and every (asset, field type) the campaign links."""
    a = spec.assets
    ops: list[Operation] = []
    links: list[tuple[str, str]] = []

    def add(fields: dict[str, Any], kind: str) -> None:
        name = ids.name("assets")
        ops.append(_create("asset", fields, name))
        links.append((name, kind))

    for link in a.sitelinks:
        if link.text.strip():
            name, op = _sitelink_asset(ids, link, landing)
            ops.append(op)
            links.append((name, "SITELINK"))
    for text in dict.fromkeys(c.strip() for c in a.callouts if c.strip()):
        add({"calloutAsset": {"calloutText": text[:25]}}, "CALLOUT")
    for snippet in a.snippets:
        values = [v.strip()[:25] for v in snippet.values if v.strip()][:10]
        if snippet.header and len(values) >= 3:
            add(
                {"structuredSnippetAsset": {"header": snippet.header, "values": values}},
                "STRUCTURED_SNIPPET",
            )
    number = a.call_number.strip() or (spec.ways.phone_number.strip() if spec.ways.calls else "")
    country = a.call_country.strip() or spec.ways.phone_country.strip()
    if (a.call or spec.ways.calls) and number and country:
        add({"callAsset": {"countryCode": country.upper(), "phoneNumber": number}}, "CALL")
    if a.business_name.strip():
        add({"textAsset": {"text": a.business_name.strip()[:25]}}, "BUSINESS_NAME")
    if a.logo:
        links.append((a.logo.asset, "BUSINESS_LOGO"))
    for image in a.images[:20]:
        links.append((image.asset, "AD_IMAGE"))
    if a.price and len([i for i in a.price.items if i.header.strip()]) >= 3:
        add({"priceAsset": _price(spec)}, "PRICE")
    if a.promotion and a.promotion.item.strip():
        promo, url = _promotion(spec)
        add({"promotionAsset": promo, "finalUrls": [url or landing]}, "PROMOTION")
    if a.lead_form and a.lead_form.headline.strip():
        add(
            {
                "leadFormAsset": _lead_form(spec),
                "finalUrls": [a.lead_form.privacy_policy_url.strip() or landing],
            },
            "LEAD_FORM",
        )
    if a.app and a.app.app_id.strip():
        add(
            {
                "mobileAppAsset": {
                    "appId": a.app.app_id.strip(),
                    "appStore": a.app.store,
                    "linkText": (a.app.link_text.strip() or "Get the app")[:25],
                }
            },
            "MOBILE_APP",
        )
    return ops, links


def _price(spec: CampaignSpec) -> dict[str, Any]:
    price = spec.assets.price
    assert price is not None
    offerings = []
    for item in price.items[:8]:
        if not item.header.strip():
            continue
        one: dict[str, Any] = {
            "header": item.header.strip()[:25],
            "description": (item.description.strip() or item.header.strip())[:25],
            "price": {"currencyCode": spec.currency, "amountMicros": micros(item.price)},
            "finalUrl": item.final_url.strip() or spec.final_url,
        }
        if item.unit:
            one["unit"] = item.unit
        offerings.append(one)
    out: dict[str, Any] = {
        "type": price.type,
        "languageCode": price.language or "en",
        "priceOfferings": offerings,
    }
    if price.qualifier:
        out["priceQualifier"] = price.qualifier
    return out


def _promotion(spec: CampaignSpec) -> tuple[dict[str, Any], str]:
    p = spec.assets.promotion
    assert p is not None
    out: dict[str, Any] = {
        "promotionTarget": p.item.strip()[:20],
        "languageCode": p.language or "en",
    }
    if p.up_to:
        out["discountModifier"] = "UP_TO"
    if p.discount == "percent":
        # Google counts a whole 100% as 1,000,000.
        out["percentOff"] = str(round(p.amount * 10_000))
    else:
        out["moneyAmountOff"] = {"currencyCode": spec.currency, "amountMicros": micros(p.amount)}
    if p.details == "code" and p.code.strip():
        out["promotionCode"] = p.code.strip()[:15]
    elif p.details == "orders_over" and p.orders_over:
        out["ordersOverAmount"] = {
            "currencyCode": spec.currency,
            "amountMicros": micros(p.orders_over),
        }
    if p.occasion:
        out["occasion"] = p.occasion
    if p.start:
        out["startDate"] = p.start.isoformat()
    if p.end:
        out["endDate"] = p.end.isoformat()
    return out, p.final_url.strip()


def _lead_form(spec: CampaignSpec) -> dict[str, Any]:
    form = spec.assets.lead_form
    assert form is not None
    out: dict[str, Any] = {
        "businessName": (
            form.business_name.strip() or spec.assets.business_name.strip() or spec.name
        )[:25],
        "callToActionType": form.call_to_action,
        "callToActionDescription": form.call_to_action_description.strip()[:30],
        "headline": form.headline.strip()[:30],
        "description": form.description.strip()[:200],
        "privacyPolicyUrl": form.privacy_policy_url.strip(),
        "fields": [{"inputType": f} for f in dict.fromkeys(form.fields)],
    }
    if form.post_submit_headline.strip():
        out["postSubmitHeadline"] = form.post_submit_headline.strip()[:30]
    if form.post_submit_description.strip():
        out["postSubmitDescription"] = form.post_submit_description.strip()[:200]
    return out


# --- Performance Max --------------------------------------------------------


def _pmax(spec: CampaignSpec, ids: _Ids, *, tag: str, today: date) -> list[Operation]:
    """Google's structure guide, step for step."""
    pm = spec.pmax
    group = pm.asset_group
    landing = group.final_url.strip() or spec.final_url
    budget, budget_ops = _budget(spec, ids, tag=tag)

    lists: list[Operation] = []
    entries: list[Operation] = []
    exclude_list = ""
    if pm.brand_exclusions:
        exclude_list, lists, entries = _brand_list(
            ids, pm.brand_exclusions, name=f"{spec.name} excluded brands · {tag}"
        )

    # Every new asset first. Text assets are created per use, because one
    # asset in two roles would be two links Google counts separately anyway.
    assets: list[Operation] = []
    group_links: list[tuple[str, str]] = []
    campaign_links: list[tuple[str, str]] = []

    def text(value: str, kind: str, *, on_campaign: bool = False) -> None:
        name = ids.name("assets")
        assets.append(_create("asset", {"textAsset": {"text": value}}, name))
        (campaign_links if on_campaign else group_links).append((name, kind))

    for value in _unique(group.headlines, 30, 15):
        text(value, "HEADLINE")
    for value in _unique(group.long_headlines, 90, 5):
        text(value, "LONG_HEADLINE")
    for value in _unique(group.descriptions, 90, 5):
        text(value, "DESCRIPTION")
    brand_on_campaign = pm.brand_guidelines.enabled
    business = (group.business_name or spec.assets.business_name).strip()[:25]
    if business:
        text(business, "BUSINESS_NAME", on_campaign=brand_on_campaign)
    for video in dict.fromkeys(v.strip() for v in group.videos if v.strip()):
        name = ids.name("assets")
        assets.append(_create("asset", {"youtubeVideoAsset": {"youtubeVideoId": video}}, name))
        group_links.append((name, "YOUTUBE_VIDEO"))
    if group.call_to_action:
        name = ids.name("assets")
        assets.append(
            _create("asset", {"callToActionAsset": {"callToAction": group.call_to_action}}, name)
        )
        group_links.append((name, "CALL_TO_ACTION_SELECTION"))
    sitelinks: list[tuple[str, str]] = []
    for link in [*spec.assets.sitelinks, *group.sitelinks]:
        if link.text.strip():
            name, op = _sitelink_asset(ids, link, landing)
            assets.append(op)
            sitelinks.append((name, "SITELINK"))

    def images(items: list[Image], kind: str, most: int, *, on_campaign: bool = False) -> None:
        for image in items[:most]:
            (campaign_links if on_campaign else group_links).append((image.asset, kind))

    images(group.marketing_images, "MARKETING_IMAGE", 20)
    images(group.square_images, "SQUARE_MARKETING_IMAGE", 20)
    images(group.portrait_images, "PORTRAIT_MARKETING_IMAGE", 20)
    images(group.logos, "LOGO", 5, on_campaign=brand_on_campaign)
    images(group.landscape_logos, "LANDSCAPE_LOGO", 5, on_campaign=brand_on_campaign)

    campaign = ids.name("campaigns")
    fields: dict[str, Any] = {
        "name": spec.name,
        "status": "ENABLED",
        "advertisingChannelType": "PERFORMANCE_MAX",
        "campaignBudget": budget,
        "containsEuPoliticalAdvertising": (
            "CONTAINS_EU_POLITICAL_ADVERTISING"
            if spec.eu_political
            else "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"
        ),
        "geoTargetTypeSetting": {
            "positiveGeoTargetType": spec.locations.target_option,
            "negativeGeoTargetType": "PRESENCE",
        },
        "brandGuidelinesEnabled": pm.brand_guidelines.enabled,
        **_bidding(spec),
        **_automation(pm.text_customization, pm.final_url_expansion),
        **_dates(spec, today),
        **_url_options(spec),
    }
    style: dict[str, Any] = {}
    if (
        pm.brand_guidelines.enabled
        and pm.brand_guidelines.main_color
        and pm.brand_guidelines.accent_color
    ):
        style["mainColor"] = pm.brand_guidelines.main_color
        style["accentColor"] = pm.brand_guidelines.accent_color
    if pm.brand_guidelines.enabled and pm.brand_guidelines.font:
        style["predefinedFontFamily"] = pm.brand_guidelines.font
    if style:
        fields["brandGuidelines"] = style
    if pm.text_customization:
        fields.update(
            _text_guidelines(
                pm.text_guidelines.term_exclusions, pm.text_guidelines.messaging_restrictions
            )
        )

    campaign_assets = [
        _create("campaign_asset", {"campaign": campaign, "asset": asset, "fieldType": kind})
        for asset, kind in [*campaign_links, *sitelinks]
    ]

    criteria = _places(spec, campaign)
    for language in spec.languages:
        criteria.append(_criterion(campaign, {"language": {"languageConstant": language.resource}}))
    criteria += _schedule(spec, campaign, adjust=False)
    for device in DEVICES:
        if (spec.devices.get(device) or 0) <= -100:
            criteria.append(_criterion(campaign, {"device": {"type": device}}, negative=True))
    for age in pm.excluded_ages:
        criteria.append(_criterion(campaign, {"ageRange": {"type": age}}, negative=True))
    for gender in pm.excluded_genders:
        criteria.append(_criterion(campaign, {"gender": {"type": gender}}, negative=True))
    criteria += _negatives(spec, campaign)
    if exclude_list:
        criteria.append(
            _criterion(campaign, {"brandList": {"sharedSet": exclude_list}}, negative=True)
        )
    if pm.text_customization and pm.final_url_expansion:
        criteria += _url_exclusions(pm.url_exclusions, campaign)

    audiences: list[Operation] = []
    audience = ""
    if group.signal:
        audience = ids.name("audiences")
        audiences.append(
            _create(
                "audience",
                {
                    "name": f"{spec.name} signal · {tag}",
                    "dimensions": [
                        {
                            "audienceSegments": {
                                "segments": [_audience_segment(s) for s in group.signal]
                            }
                        }
                    ],
                },
                audience,
            )
        )

    asset_group = ids.name("assetGroups")
    group_fields: dict[str, Any] = {
        "name": group.name.strip()[:128] or "Asset group 1",
        "campaign": campaign,
        "finalUrls": [landing],
        "status": "ENABLED",
    }
    if group.path1.strip():
        group_fields["path1"] = group.path1.strip()[:15]
        if group.path2.strip():
            group_fields["path2"] = group.path2.strip()[:15]

    group_assets = [
        _create("asset_group_asset", {"assetGroup": asset_group, "asset": asset, "fieldType": kind})
        for asset, kind in group_links
    ]
    signals = [
        _create("asset_group_signal", {"assetGroup": asset_group, "searchTheme": {"text": theme}})
        for theme in _unique(group.search_themes, 80, 50)
    ]
    if audience:
        signals.append(
            _create(
                "asset_group_signal",
                {"assetGroup": asset_group, "audience": {"audience": audience}},
            )
        )

    return [
        *budget_ops,
        *lists,
        *entries,
        *assets,
        _create("campaign", fields, campaign),
        *campaign_assets,
        *criteria,
        *_goals(spec, campaign),
        *audiences,
        _create("asset_group", group_fields, asset_group),
        *group_assets,
        *signals,
    ]


def _audience_segment(segment: Segment) -> dict[str, Any]:
    if segment.kind == "user_list":
        return {"userList": {"userList": segment.resource}}
    if segment.kind == "user_interest":
        return {"userInterest": {"userInterestCategory": segment.resource}}
    return {"customAudience": {"customAudience": segment.resource}}


def _unique(values: list[str], longest: int, most: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(value.split())[:longest]
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    return out[:most]


def campaign_of(names: tuple[str, ...]) -> str:
    """The new campaign's resource name, out of what Google said it created."""
    return next((n for n in names if "/campaigns/" in n), "")


# --- Demand Gen, Display, Shopping and App ----------------------------------
#
# Field names from the v25 protos (common/ad_type_infos.proto,
# resources/ad_group.proto, resources/campaign.proto), read on 12 November.


def _common_campaign(spec: CampaignSpec, budget: str, channel: str, today: date) -> dict[str, Any]:
    return {
        "name": spec.name,
        "status": "ENABLED",
        "advertisingChannelType": channel,
        "campaignBudget": budget,
        "containsEuPoliticalAdvertising": (
            "CONTAINS_EU_POLITICAL_ADVERTISING"
            if spec.eu_political
            else "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"
        ),
        **_dates(spec, today),
        **_url_options(spec),
    }


def _texts(values: list[str], longest: int, most: int) -> list[dict[str, str]]:
    return [{"text": t} for t in _unique(values, longest, most)]


def _pictures(items: list[Image], most: int) -> list[dict[str, str]]:
    return [{"asset": i.asset} for i in items[:most]]


def _youtube(
    ids: _Ids, videos: list[str], most: int
) -> tuple[list[Operation], list[dict[str, str]]]:
    """YouTube videos as assets created in the same request, and references to them."""
    ops: list[Operation] = []
    refs: list[dict[str, str]] = []
    for video in list(dict.fromkeys(v.strip() for v in videos if v.strip()))[:most]:
        name = ids.name("assets")
        ops.append(_create("asset", {"youtubeVideoAsset": {"youtubeVideoId": video}}, name))
        refs.append({"asset": name})
    return ops, refs


def _targeting_criteria(spec: CampaignSpec, owner: dict[str, str], kind: str) -> list[Operation]:
    """Places and languages, on the campaign or (Demand Gen) on the ad group."""
    ops: list[Operation] = []
    loc = spec.locations

    def one(fields: dict[str, Any], negative: bool = False) -> Operation:
        body = {**owner, **fields}
        if negative:
            body["negative"] = True
        return _create(kind, body)

    if loc.mode == "home" and loc.home:
        ops.append(one({"location": {"geoTargetConstant": loc.home.resource}}))
    elif loc.mode == "custom":
        ops += [one({"location": {"geoTargetConstant": p.resource}}) for p in loc.targets]
        if kind == "campaign_criterion":
            # A radius is a campaign criterion only; Demand Gen ad groups
            # cannot take one, which `checks` says before anything is sent.
            for circle in loc.radius:
                ops.append(
                    one(
                        {
                            "proximity": {
                                "geoPoint": {
                                    "latitudeInMicroDegrees": round(circle.latitude * 1_000_000),
                                    "longitudeInMicroDegrees": round(circle.longitude * 1_000_000),
                                },
                                "radius": circle.radius,
                                "radiusUnits": circle.units,
                            }
                        }
                    )
                )
    for place in loc.excluded:
        ops.append(one({"location": {"geoTargetConstant": place.resource}}, negative=True))
    ops += [one({"language": {"languageConstant": lang.resource}}) for lang in spec.languages]
    return ops


def _demand_gen(spec: CampaignSpec, ids: _Ids, *, tag: str, today: date) -> list[Operation]:
    dg = spec.demand_gen
    landing = spec.final_url
    budget, budget_ops = _budget(spec, ids, tag=tag)
    campaign = ids.name("campaigns")
    fields = _common_campaign(spec, budget, "DEMAND_GEN", today)
    fields["demandGenCampaignSettings"] = {"upgradedTargeting": not dg.campaign_level_targeting}
    if spec.bidding.focus == "clicks" and dg.target_cpc:
        fields["targetCpc"] = {"targetCpcMicros": micros(dg.target_cpc)}
    else:
        fields.update(_bidding(spec))
    fields["geoTargetTypeSetting"] = {
        "positiveGeoTargetType": spec.locations.target_option,
        "negativeGeoTargetType": "PRESENCE",
    }

    assets: list[Operation] = []
    ads: list[dict[str, Any]] = []
    for ad in dg.ads:
        url = ad.final_url.strip() or landing
        base: dict[str, Any] = {"name": ad.name.strip()[:255] or "Ad", "finalUrls": [url]}
        business = (ad.business_name or spec.assets.business_name).strip()[:25]
        if ad.format == "video":
            made, videos = _youtube(ids, ad.videos, 5)
            assets += made
            info: dict[str, Any] = {
                "headlines": _texts(ad.headlines, 40, 5),
                "longHeadlines": _texts(ad.long_headlines, 90, 5),
                "descriptions": _texts(ad.descriptions, 90, 5),
                "videos": videos,
                "logoImages": _pictures(ad.logos, 5),
                "businessName": {"text": business},
            }
            if ad.call_to_action:
                cta = ids.name("assets")
                assets.append(
                    _create(
                        "asset", {"callToActionAsset": {"callToAction": ad.call_to_action}}, cta
                    )
                )
                info["callToActions"] = [{"asset": cta}]
            ads.append({**base, "demandGenVideoResponsiveAd": info})
        elif ad.format == "carousel":
            cards: list[dict[str, str]] = []
            for card in ad.cards[:10]:
                image = card.get("image") or {}
                square = bool(image.get("width")) and image.get("width") == image.get("height")
                name = ids.name("assets")
                body: dict[str, Any] = {
                    "squareMarketingImageAsset" if square else "marketingImageAsset": str(
                        image.get("asset", "")
                    ),
                    "headline": str(card.get("headline") or "")[:40],
                }
                if card.get("call_to_action"):
                    body["callToActionText"] = str(card["call_to_action"])[:10]
                assets.append(
                    _create(
                        "asset",
                        {
                            "demandGenCarouselCardAsset": body,
                            "finalUrls": [str(card.get("final_url") or url)],
                        },
                        name,
                    )
                )
                cards.append({"asset": name})
            info = {
                "businessName": business,
                "logoImage": {"asset": ad.logos[0].asset} if ad.logos else {},
                "headline": {"text": (ad.headlines or [""])[0][:40]},
                "description": {"text": (ad.descriptions or [""])[0][:90]},
                "carouselCards": cards,
            }
            if ad.call_to_action:
                info["callToActionText"] = ad.call_to_action[:10]
            ads.append({**base, "demandGenCarouselAd": info})
        else:
            info = {
                "marketingImages": _pictures(ad.marketing_images, 20),
                "squareMarketingImages": _pictures(ad.square_images, 20),
                "portraitMarketingImages": _pictures(ad.portrait_images, 20),
                "logoImages": _pictures(ad.logos, 5),
                "headlines": _texts(ad.headlines, 40, 5),
                "descriptions": _texts(ad.descriptions, 90, 5),
                "businessName": business,
            }
            if ad.call_to_action:
                info["callToActionText"] = ad.call_to_action[:10]
            ads.append({**base, "demandGenMultiAssetAd": info})

    group = ids.name("adGroups")
    controls: dict[str, Any] = (
        {"channelStrategy": "ALL_CHANNELS"}
        if dg.channels == "all"
        else {
            "selectedChannels": {
                channel: channel in dg.selected
                for channel in (
                    "youtube_in_stream",
                    "youtube_in_feed",
                    "youtube_shorts",
                    "discover",
                    "gmail",
                    "display",
                    "maps",
                )
            }
        }
    )
    if "selectedChannels" in controls:
        controls["selectedChannels"] = {
            _camel(k): v for k, v in controls["selectedChannels"].items()
        }
    group_fields: dict[str, Any] = {
        "name": dg.ad_group_name.strip()[:255] or "Ad group 1",
        "campaign": campaign,
        "status": "ENABLED",
        "demandGenAdGroupSettings": {"channelControls": controls},
        "optimizedTargetingEnabled": dg.optimized_targeting,
    }
    audience_ops: list[Operation] = []
    group_criteria: list[Operation] = []
    if dg.segments:
        audience = ids.name("audiences")
        audience_ops.append(
            _create(
                "audience",
                {
                    "name": f"{spec.name} audience · {tag}",
                    "dimensions": [
                        {
                            "audienceSegments": {
                                "segments": [_audience_segment(s) for s in dg.segments]
                            }
                        }
                    ],
                },
                audience,
            )
        )
        group_criteria.append(
            _create("ad_group_criterion", {"adGroup": group, "audience": {"audience": audience}})
        )

    campaign_criteria: list[Operation] = []
    if dg.campaign_level_targeting:
        campaign_criteria = _targeting_criteria(spec, {"campaign": campaign}, "campaign_criterion")
    else:
        group_criteria = (
            _targeting_criteria(spec, {"adGroup": group}, "ad_group_criterion") + group_criteria
        )
    for device in DEVICES:
        if (spec.devices.get(device) or 0) <= -100:
            campaign_criteria.append(
                _criterion(campaign, {"device": {"type": device}}, negative=True)
            )
    campaign_criteria += _schedule(spec, campaign, adjust=False)

    return [
        *budget_ops,
        *assets,
        _create("campaign", fields, campaign),
        *campaign_criteria,
        *_goals(spec, campaign),
        *audience_ops,
        _create("ad_group", group_fields, group),
        *group_criteria,
        *[_create("ad_group_ad", {"adGroup": group, "status": "ENABLED", "ad": ad}) for ad in ads],
    ]


def _camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(word.title() for word in rest)


def _display(spec: CampaignSpec, ids: _Ids, *, tag: str, today: date) -> list[Operation]:
    d = spec.display
    budget, budget_ops = _budget(spec, ids, tag=tag)
    campaign = ids.name("campaigns")
    fields = _common_campaign(spec, budget, "DISPLAY", today)
    manual = spec.bidding.strategy == "manual_cpc"
    fields.update(_bidding(spec) if not manual else {"manualCpc": {}})
    fields["geoTargetTypeSetting"] = {
        "positiveGeoTargetType": spec.locations.target_option,
        "negativeGeoTargetType": "PRESENCE",
    }
    made, videos = _youtube(ids, d.videos, 5)
    group = ids.name("adGroups")
    group_fields: dict[str, Any] = {
        "name": d.ad_group_name.strip()[:255] or "Ad group 1",
        "campaign": campaign,
        "status": "ENABLED",
        "type": "DISPLAY_STANDARD",
        "optimizedTargetingEnabled": d.optimized_targeting,
    }
    if manual and (d.default_bid or spec.bidding.default_bid):
        group_fields["cpcBidMicros"] = micros(d.default_bid or spec.bidding.default_bid)
    criteria = [
        _create(
            "ad_group_criterion",
            {"adGroup": group, **_segment(s)} | ({"negative": True} if s.excluded else {}),
        )
        for s in d.segments
    ]
    criteria += [
        _create(
            "ad_group_criterion", {"adGroup": group, "keyword": {"text": k, "matchType": "BROAD"}}
        )
        for k in _unique(d.keywords, 80, 200)
    ]
    rda: dict[str, Any] = {
        "marketingImages": _pictures(d.marketing_images, 15),
        "squareMarketingImages": _pictures(d.square_images, 15),
        "squareLogoImages": _pictures(d.logos, 5),
        "logoImages": _pictures(d.landscape_logos, 5),
        "headlines": _texts(d.headlines, 30, 5),
        "longHeadline": {"text": d.long_headline.strip()[:90]},
        "descriptions": _texts(d.descriptions, 90, 5),
        "businessName": (d.business_name or spec.assets.business_name).strip()[:25],
    }
    if videos:
        rda["youtubeVideos"] = videos
    if d.call_to_action:
        rda["callToActionText"] = d.call_to_action[:30]
    campaign_criteria = _targeting_criteria(spec, {"campaign": campaign}, "campaign_criterion")
    campaign_criteria += _schedule(spec, campaign, adjust=manual)
    for device in DEVICES:
        adjustment = spec.devices.get(device)
        if adjustment is not None and adjustment <= -100:
            campaign_criteria.append(
                _criterion(campaign, {"device": {"type": device}, "bidModifier": 0.0})
            )
    return [
        *budget_ops,
        *made,
        _create("campaign", fields, campaign),
        *campaign_criteria,
        *_goals(spec, campaign),
        _create("ad_group", group_fields, group),
        *criteria,
        _create(
            "ad_group_ad",
            {
                "adGroup": group,
                "status": "ENABLED",
                "ad": {
                    "finalUrls": [d.final_url.strip() or spec.final_url],
                    "responsiveDisplayAd": rda,
                },
            },
        ),
    ]


def _shopping(spec: CampaignSpec, ids: _Ids, *, tag: str, today: date) -> list[Operation]:
    sh = spec.shopping
    budget, budget_ops = _budget(spec, ids, tag=tag)
    campaign = ids.name("campaigns")
    fields = _common_campaign(spec, budget, "SHOPPING", today)
    setting: dict[str, Any] = {
        "merchantId": str(sh.merchant_id or 0),
        "campaignPriority": sh.priority,
        "enableLocal": sh.enable_local,
    }
    if sh.feed_label.strip():
        setting["feedLabel"] = sh.feed_label.strip()[:20]
    fields["shoppingSetting"] = setting
    fields["geoTargetTypeSetting"] = {
        "positiveGeoTargetType": spec.locations.target_option,
        "negativeGeoTargetType": "PRESENCE",
    }
    fields["networkSettings"] = {
        "targetGoogleSearch": True,
        "targetSearchNetwork": spec.networks.search_partners,
        # Google refuses the Display Network on Shopping (CANNOT_TARGET_CONTENT_NETWORK).
        "targetContentNetwork": False,
        "targetPartnerSearchNetwork": False,
    }
    manual = spec.bidding.strategy == "manual_cpc"
    if manual:
        fields["manualCpc"] = {}
    elif spec.bidding.focus == "conversion_value":
        fields.update(_bidding(spec))
    else:
        fields["targetSpend"] = (
            {"cpcBidCeilingMicros": micros(spec.bidding.max_cpc)} if spec.bidding.max_cpc else {}
        )
    group = ids.name("adGroups")
    group_fields: dict[str, Any] = {
        "name": sh.ad_group_name.strip()[:255] or "Ad group 1",
        "campaign": campaign,
        "status": "ENABLED",
        "type": "SHOPPING_PRODUCT_ADS",
    }
    bid = sh.default_bid or spec.bidding.default_bid
    if manual and bid:
        group_fields["cpcBidMicros"] = micros(bid)
    root: dict[str, Any] = {"adGroup": group, "status": "ENABLED", "listingGroup": {"type": "UNIT"}}
    if manual and bid:
        root["cpcBidMicros"] = micros(bid)
    criteria = (
        _places(spec, campaign)
        + _schedule(spec, campaign, adjust=manual)
        + _negatives(spec, campaign)
    )
    return [
        *budget_ops,
        _create("campaign", fields, campaign),
        *criteria,
        *_goals(spec, campaign),
        _create("ad_group", group_fields, group),
        # One product group for every product, as a new Shopping ad group starts.
        _create("ad_group_criterion", root),
        _create(
            "ad_group_ad", {"adGroup": group, "status": "ENABLED", "ad": {"shoppingProductAd": {}}}
        ),
    ]


#: Google's App bidding goals, by focus and whether a target was set.
_APP_GOALS: Final = {
    ("installs", True): "OPTIMIZE_INSTALLS_TARGET_INSTALL_COST",
    ("installs", False): "OPTIMIZE_INSTALLS_WITHOUT_TARGET_INSTALL_COST",
    ("in_app_actions", True): "OPTIMIZE_IN_APP_CONVERSIONS_TARGET_CONVERSION_COST",
    ("in_app_actions", False): "OPTIMIZE_IN_APP_CONVERSIONS_WITHOUT_TARGET_CPA",
    ("in_app_value", True): "OPTIMIZE_RETURN_ON_ADVERTISING_SPEND",
    ("in_app_value", False): "OPTIMIZE_TOTAL_VALUE_WITHOUT_TARGET_ROAS",
}


def _app(spec: CampaignSpec, ids: _Ids, *, tag: str, today: date) -> list[Operation]:
    app = spec.app
    budget, budget_ops = _budget(spec, ids, tag=tag, daily_only=True)
    campaign = ids.name("campaigns")
    fields = _common_campaign(spec, budget, "MULTI_CHANNEL", today)
    fields["advertisingChannelSubType"] = app.subtype
    fields["geoTargetTypeSetting"] = {
        "positiveGeoTargetType": spec.locations.target_option,
        "negativeGeoTargetType": "PRESENCE",
    }
    pre = app.subtype == "APP_CAMPAIGN_FOR_PRE_REGISTRATION"
    value = app.focus == "in_app_value"
    has_target = bool(app.target_roas if value else app.target_cpa)
    goal = (
        "OPTIMIZE_PRE_REGISTRATION_CONVERSION_VOLUME"
        if pre
        else _APP_GOALS[(app.focus, has_target)]
    )
    fields["appCampaignSetting"] = {
        "appId": app.app_id.strip(),
        "appStore": app.store,
        "biddingStrategyGoalType": goal,
    }
    if pre:
        fields["optimizationGoalSetting"] = {"optimizationGoalTypes": ["APP_PRE_REGISTRATION"]}
        fields["maximizeConversions"] = {}
    elif value:
        fields.update(
            {"targetRoas": {"targetRoas": round((app.target_roas or 0) / 100, 4)}}
            if has_target
            else {"maximizeConversionValue": {}}
        )
    else:
        fields.update(
            {"targetCpa": {"targetCpaMicros": micros(app.target_cpa)}}
            if has_target
            else {"maximizeConversions": {}}
        )
    if app.conversion_actions and (pre or app.focus != "installs"):
        fields["selectiveOptimization"] = {"conversionActions": list(app.conversion_actions)}
    made, videos = _youtube(ids, app.videos, 20)
    group = ids.name("adGroups")
    group_criteria: list[Operation] = []
    if app.subtype == "APP_CAMPAIGN_FOR_ENGAGEMENT":
        group_criteria = [
            _create("ad_group_criterion", {"adGroup": group, **_segment(s)})
            for s in spec.audiences.segments
            if s.kind == "user_list"
        ]
    return [
        *budget_ops,
        *made,
        _create("campaign", fields, campaign),
        *_targeting_criteria(spec, {"campaign": campaign}, "campaign_criterion"),
        _create(
            "ad_group",
            {
                "name": app.ad_group_name.strip()[:255] or "Ad group 1",
                "campaign": campaign,
                "status": "ENABLED",
            },
            group,
        ),
        *group_criteria,
        _create(
            "ad_group_ad",
            {
                "adGroup": group,
                "status": "ENABLED",
                "ad": _app_ad(app, videos),
            },
        ),
    ]


def _app_ad(app: Any, videos: list[dict[str, str]]) -> dict[str, Any]:
    """Each App subtype has its own ad in v25: AppAdInfo for installs,
    AppEngagementAdInfo for engagement, AppPreRegistrationAdInfo for
    pre-registration. The engagement ad calls its videos `videos`."""
    texts = {
        "headlines": _texts(app.headlines, 30, 5),
        "descriptions": _texts(app.descriptions, 90, 5),
        "images": _pictures(app.images, 20),
    }
    if app.subtype == "APP_CAMPAIGN_FOR_ENGAGEMENT":
        return {"appEngagementAd": {**texts, "videos": videos}}
    if app.subtype == "APP_CAMPAIGN_FOR_PRE_REGISTRATION":
        return {"appPreRegistrationAd": {**texts, "youtubeVideos": videos}}
    return {"appAd": {**texts, "youtubeVideos": videos}}
