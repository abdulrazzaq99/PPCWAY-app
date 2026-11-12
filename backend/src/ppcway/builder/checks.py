"""What stops a campaign being published, step by step, as Google's left menu flags it.

Google's creation screen keeps a progress menu on the left that marks each
step with what still has to be fixed, and its review page lists every problem
with a link back to the step. This is PPCWay's half of that: everything it can
see is wrong without asking Google, all at once, each against the step it
belongs to. Google's own check (a validate-only request, `gateway.create`)
runs on the review step after this one passes, and its errors are filed
against steps the same way (`step_of`).

A **problem** blocks publishing. A **warning** is Google's advice that does
not, such as fewer than four sitelinks, and is shown without stopping anyone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Final

from ppcway.builder.spec import STEPS, CampaignSpec

#: Google's own limits, from its help pages and the v25 reference.
HEADLINE: Final = 30
DESCRIPTION: Final = 90
LONG_HEADLINE: Final = 90
PATH: Final = 15
SITELINK_TEXT: Final = 25
SITELINK_LINE: Final = 35
CALLOUT: Final = 25
BUSINESS_NAME: Final = 25
KEYWORD_CHARS: Final = 80
KEYWORD_WORDS: Final = 10


@dataclass(frozen=True, slots=True)
class Problem:
    step: str
    words: str
    #: False for advice Google gives that does not stop publishing.
    blocks: bool = True

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def problems(spec: CampaignSpec, *, today: date) -> list[Problem]:
    """Everything wrong with the campaign, in step order."""
    out: list[Problem] = []
    out += _goal(spec)
    out += _bidding(spec)
    out += _settings(spec, today)
    if spec.type == "SEARCH":
        out += _ads(spec)
        out += _assets(spec)
    if spec.type == "PERFORMANCE_MAX":
        out += _asset_group(spec)
    if spec.type == "DEMAND_GEN":
        out += _demand_gen(spec)
    if spec.type == "DISPLAY":
        out += _display(spec)
    if spec.type == "SHOPPING":
        out += _shopping(spec)
    if spec.type == "APP":
        out += _app(spec)
    out += _budget(spec)
    steps = STEPS.get(spec.type, [])
    if "budget" not in steps:
        # Demand Gen, Display, Shopping and App ask for the budget with bidding.
        out = [Problem("bidding", p.words, p.blocks) if p.step == "budget" else p for p in out]
    order = {"goal": -1, **{step: at for at, step in enumerate(steps)}}
    return sorted(out, key=lambda p: order.get(p.step, 99))


def blocking(found: list[Problem]) -> list[Problem]:
    return [p for p in found if p.blocks]


def _goal(spec: CampaignSpec) -> list[Problem]:
    out: list[Problem] = []
    if not spec.name.strip():
        out.append(Problem("goal", "Give the campaign a name. Customers never see it."))
    if not spec.final_url.startswith(("http://", "https://")):
        out.append(Problem("goal", "Add your business's website, starting with https://."))
    if spec.ways.calls and not spec.ways.phone_number.strip():
        out.append(Problem("goal", "Add the phone number customers should call."))
    if not spec.goals.account_default and not spec.goals.chosen:
        out.append(
            Problem("goal", "Choose at least one conversion goal, or use the account goals.")
        )
    return out


def _bidding(spec: CampaignSpec) -> list[Problem]:
    b = spec.bidding
    out: list[Problem] = []
    if b.set_target and b.focus == "conversions" and not (b.target_cpa or 0) > 0:
        out.append(Problem("bidding", "Set the target cost per action, or untick it."))
    if b.set_target and b.focus == "conversion_value" and not (b.target_roas or 0) > 0:
        out.append(Problem("bidding", "Set the target return on ad spend, or untick it."))
    if spec.type == "SEARCH" and b.focus == "impression_share" and b.strategy != "manual_cpc":
        if not 0 < (b.impression_percent or 0) <= 100:
            out.append(Problem("bidding", "Say what percent of impressions to aim for, 1 to 100."))
        if not (b.impression_max_cpc or 0) > 0:
            out.append(Problem("bidding", "Target impression share needs a maximum CPC bid limit."))
    if spec.type == "PERFORMANCE_MAX" and b.focus not in {"conversions", "conversion_value"}:
        out.append(Problem("bidding", "Performance Max bids for conversions or conversion value."))
    if b.strategy == "manual_cpc" and not (b.default_bid or 0) > 0:
        out.append(Problem("bidding", "Manual CPC needs a default bid for each ad group."))
    if (
        spec.type == "SEARCH"
        and b.strategy == "manual_cpc"
        and spec.ai_max.enabled
        and spec.ai_max.search_term_matching
    ):
        out.append(
            Problem(
                "bidding",
                "AI Max search term matching does not work with manual CPC. Choose another"
                " strategy, or turn search term matching off on the AI Max step.",
            )
        )
    if b.new_customers == "bid_higher" and b.focus != "conversion_value":
        out.append(
            Problem(
                "bidding",
                "Bidding higher for new customers needs a focus on conversion value.",
            )
        )
    return out


def _settings(spec: CampaignSpec, today: date) -> list[Problem]:
    out: list[Problem] = []
    if spec.eu_political is None:
        out.append(
            Problem(
                "settings", "Say whether this campaign has EU political ads. Google requires it."
            )
        )
    loc = spec.locations
    if loc.mode == "custom" and not (loc.targets or loc.radius):
        out.append(Problem("settings", "Enter at least one location, or choose all countries."))
    if loc.mode == "home" and loc.home is None:
        out.append(Problem("settings", "Choose where your ads show."))
    for circle in loc.radius:
        if circle.radius < (1 if circle.units == "KILOMETERS" else 0.62):
            out.append(Problem("settings", "A radius has to be at least 1 km."))
            break
    if spec.type not in {"SEARCH", "SHOPPING"} and not spec.languages:
        out.append(Problem("settings", "Choose at least one language."))
    if spec.dates.end and spec.dates.end < today:
        out.append(Problem("settings", "The end date is in the past."))
    if spec.dates.start and spec.dates.end and spec.dates.end < spec.dates.start:
        out.append(Problem("settings", "The end date is before the start date."))
    per_day: dict[str, int] = {}
    for entry in spec.schedule:
        per_day[entry.day] = per_day.get(entry.day, 0) + 1
        if (entry.end_hour, entry.end_minute) <= (entry.start_hour, entry.start_minute):
            out.append(
                Problem("settings", f"An ad schedule on {entry.day.title()} ends before it starts.")
            )
    if any(n > 6 for n in per_day.values()):
        out.append(Problem("settings", "Google allows up to 6 ad schedules a day."))
    for device, adjustment in spec.devices.items():
        if adjustment is not None and not -100 <= adjustment <= 900:
            out.append(
                Problem("settings", f"The {device.lower()} bid adjustment must be -100% to +900%.")
            )
    if len(spec.ip_exclusions) > 500:
        out.append(Problem("settings", "Google allows up to 500 IP exclusions per campaign."))
    if len(spec.url_options.custom_parameters) > 8:
        out.append(Problem("settings", "Google allows up to 8 custom parameters."))
    for p in spec.url_options.custom_parameters:
        key = str(p.get("key", "")).lstrip("_")
        if key and (not key.isalnum() or len(key) > 16):
            out.append(Problem("settings", f'"{key}" must be up to 16 letters or numbers.'))
    tracking = spec.url_options.tracking_template.strip()
    if tracking and not ("{lpurl" in tracking or tracking.startswith(("http://", "https://"))):
        out.append(
            Problem("settings", "A tracking template starts with {lpurl} or an https:// address.")
        )
    ai = spec.ai_max
    if spec.type == "SEARCH" and ai.enabled:
        if len(ai.text_guidelines.term_exclusions) > 25:
            out.append(Problem("ai_max", "Google allows up to 25 term exclusions."))
        if any(len(t) > 30 for t in ai.text_guidelines.term_exclusions):
            out.append(Problem("ai_max", "A term exclusion is at most 30 characters."))
        if len(ai.text_guidelines.messaging_restrictions) > 40:
            out.append(Problem("ai_max", "Google allows up to 40 messaging restrictions."))
    return out


def _ads(spec: CampaignSpec) -> list[Problem]:
    out: list[Problem] = []
    if not spec.ad_groups:
        out.append(Problem("ads", "Add at least one ad group with keywords and an ad."))
    names: set[str] = set()
    for group in spec.ad_groups:
        label = f'"{group.name or "Ad group"}"'
        if group.name.strip().lower() in names:
            out.append(
                Problem("ads", f"Two ad groups are called {label}. Each needs its own name.")
            )
        names.add(group.name.strip().lower())
        if not group.keywords:
            out.append(Problem("ads", f"{label} has no keywords."))
        for word in group.keywords + group.negatives:
            if len(word.text) > KEYWORD_CHARS or len(word.text.split()) > KEYWORD_WORDS:
                out.append(
                    Problem("ads", f'The keyword "{word.text[:40]}" is longer than Google allows.')
                )
        if not group.ads:
            out.append(Problem("ads", f"{label} has no ad."))
        if len(group.ads) > 3:
            out.append(Problem("ads", f"{label} has more than 3 responsive search ads."))
        for at, ad in enumerate(group.ads, start=1):
            which = f"Ad {at} in {label}"
            heads = [h for h in ad.headlines if h.text.strip()]
            descs = [d for d in ad.descriptions if d.text.strip()]
            if len(heads) < 3:
                out.append(Problem("ads", f"{which} needs at least 3 headlines."))
            if len(descs) < 2:
                out.append(Problem("ads", f"{which} needs at least 2 descriptions."))
            if len(heads) > 15 or len(descs) > 4:
                out.append(Problem("ads", f"{which} has more than 15 headlines or 4 descriptions."))
            for h in heads:
                if len(h.text) > HEADLINE:
                    out.append(
                        Problem("ads", f'{which}: "{h.text[:32]}…" is over {HEADLINE} characters.')
                    )
            for d in descs:
                if len(d.text) > DESCRIPTION:
                    out.append(
                        Problem("ads", f"{which}: a description is over {DESCRIPTION} characters.")
                    )
            lowered = [h.text.strip().lower() for h in heads]
            if len(set(lowered)) != len(lowered):
                out.append(
                    Problem(
                        "ads",
                        f"{which} has the same headline twice; it is sent once.",
                        blocks=False,
                    )
                )
            if len(ad.path1) > PATH or len(ad.path2) > PATH:
                out.append(Problem("ads", f"{which}: a display path is over {PATH} characters."))
            if ad.path2.strip() and not ad.path1.strip():
                out.append(
                    Problem("ads", f"{which}: fill the first display path before the second.")
                )
            url = ad.final_url.strip() or spec.final_url
            if not url.startswith(("http://", "https://")):
                out.append(Problem("ads", f"{which} needs a final URL."))
            # Every position Google must fill has to be fillable: pinned there,
            # or left to an unpinned line (NOT_ENOUGH_AVAILABLE_ASSET_LINKS...).
            for lines, needed, kind in (
                (heads, ("HEADLINE_1", "HEADLINE_2"), "headlines"),
                (descs, ("DESCRIPTION_1",), "descriptions"),
            ):
                free = len([x for x in lines if not x.pin])
                for position in needed:
                    if not any(x.pin == position for x in lines):
                        free -= 1
                if lines and free < 0:
                    out.append(
                        Problem("ads", f"{which} pins too many {kind} to fill every position.")
                    )
    return out


def _assets(spec: CampaignSpec) -> list[Problem]:
    a = spec.assets
    out: list[Problem] = []
    for link in a.sitelinks:
        if len(link.text) > SITELINK_TEXT:
            out.append(
                Problem(
                    "ads", f'The sitelink "{link.text[:20]}…" is over {SITELINK_TEXT} characters.'
                )
            )
        if bool(link.description1.strip()) != bool(link.description2.strip()):
            out.append(
                Problem(
                    "ads", f'The sitelink "{link.text}" needs both description lines, or neither.'
                )
            )
        if len(link.description1) > SITELINK_LINE or len(link.description2) > SITELINK_LINE:
            out.append(
                Problem(
                    "ads", f'A description on "{link.text}" is over {SITELINK_LINE} characters.'
                )
            )
    sitelinks = len([s for s in a.sitelinks if s.text.strip()])
    if 0 < sitelinks < 2:
        out.append(Problem("ads", "Sitelinks show only when there are at least 2.", blocks=False))
    elif sitelinks < 4:
        out.append(Problem("ads", "Google recommends at least 4 sitelinks.", blocks=False))
    for text in a.callouts:
        if len(text) > CALLOUT:
            out.append(Problem("ads", f'The callout "{text[:20]}…" is over {CALLOUT} characters.'))
    for snippet in a.snippets:
        values = [v for v in snippet.values if v.strip()]
        if snippet.header and not 3 <= len(values) <= 10:
            out.append(Problem("ads", f"The {snippet.header} snippet needs 3 to 10 values."))
    if len(a.business_name) > BUSINESS_NAME:
        out.append(Problem("ads", f"The business name is over {BUSINESS_NAME} characters."))
    if a.call and not a.call_number.strip() and not spec.ways.phone_number.strip():
        out.append(Problem("ads", "The call asset needs a phone number."))
    if a.images and not any(i.width and i.width == i.height for i in a.images):
        out.append(Problem("ads", "Search image assets need at least one square image."))
    if (
        a.price
        and a.price.items
        and not 3 <= len([i for i in a.price.items if i.header.strip()]) <= 8
    ):
        out.append(Problem("ads", "A price asset needs 3 to 8 items."))
    form = a.lead_form
    if form and form.headline.strip():
        if not form.privacy_policy_url.startswith(("http://", "https://")):
            out.append(Problem("ads", "The lead form needs your privacy policy's address."))
        if not form.description.strip():
            out.append(Problem("ads", "The lead form needs a description."))
    return out


def _asset_group(spec: CampaignSpec) -> list[Problem]:
    g = spec.pmax.asset_group
    out: list[Problem] = []

    def count(values: list[str], longest: int) -> int:
        return len({v.strip().lower() for v in values if v.strip() and len(v) <= longest})

    if not g.final_url.startswith(("http://", "https://")) and not spec.final_url:
        out.append(Problem("asset_group", "The asset group needs a final URL."))
    if count(g.headlines, HEADLINE) < 3:
        out.append(Problem("asset_group", "Add at least 3 headlines of up to 30 characters."))
    if not any(len(h.strip()) <= 15 for h in g.headlines if h.strip()):
        out.append(
            Problem(
                "asset_group",
                "Google asks for one headline of 15 characters or fewer.",
                blocks=False,
            )
        )
    if count(g.long_headlines, LONG_HEADLINE) < 1:
        out.append(Problem("asset_group", "Add at least 1 long headline."))
    if count(g.descriptions, DESCRIPTION) < 2:
        out.append(Problem("asset_group", "Add at least 2 descriptions."))
    if not any(len(d.strip()) <= 60 for d in g.descriptions if d.strip()):
        out.append(Problem("asset_group", "One description has to be 60 characters or fewer."))
    if not (g.business_name or spec.assets.business_name).strip():
        out.append(Problem("asset_group", "Add your business name."))
    if len(g.business_name) > BUSINESS_NAME:
        out.append(Problem("asset_group", f"The business name is over {BUSINESS_NAME} characters."))
    if not g.marketing_images:
        out.append(Problem("asset_group", "Add at least 1 landscape image (1.91:1)."))
    if not g.square_images:
        out.append(Problem("asset_group", "Add at least 1 square image (1:1)."))
    if len(g.marketing_images) < 4 or len(g.square_images) < 4:
        out.append(
            Problem(
                "asset_group",
                "Google recommends 4 or more landscape and square images.",
                blocks=False,
            )
        )
    if not g.logos:
        out.append(Problem("asset_group", "Add at least 1 square logo."))
    if len(g.logos) + len(g.landscape_logos) > 5:
        out.append(Problem("asset_group", "Google allows up to 5 logos in all."))
    if len(g.search_themes) > 50:
        out.append(Problem("asset_group", "Google allows up to 50 search themes."))
    for video in g.videos:
        if len(video.strip()) != 11:
            out.append(Problem("asset_group", f'"{video}" is not a YouTube video id.'))
    if not g.videos:
        out.append(
            Problem(
                "asset_group",
                "With no video, Google may make one from your images.",
                blocks=False,
            )
        )
    return out


def _demand_gen(spec: CampaignSpec) -> list[Problem]:
    dg = spec.demand_gen
    out: list[Problem] = []
    if spec.bidding.focus == "impression_share" or spec.bidding.strategy == "manual_cpc":
        out.append(
            Problem("bidding", "Demand Gen bids for conversions, conversion value or clicks.")
        )
    if dg.channels == "choose" and not dg.selected:
        out.append(Problem("ad_group", "Choose at least one channel, or use all Google channels."))
    if not dg.ads:
        out.append(Problem("ads", "Add at least one ad."))
    for at, ad in enumerate(dg.ads, start=1):
        which = f'Ad {at} ("{ad.name or "Ad"}")'
        business = (ad.business_name or spec.assets.business_name).strip()
        if not business:
            out.append(Problem("ads", f"{which} needs your business name."))
        if not ad.logos:
            out.append(Problem("ads", f"{which} needs a square logo."))
        if not (ad.final_url or spec.final_url).startswith(("http://", "https://")):
            out.append(Problem("ads", f"{which} needs a final URL."))
        heads = [h for h in ad.headlines if h.strip()]
        descs = [d for d in ad.descriptions if d.strip()]
        if ad.format == "image":
            if not (ad.marketing_images or ad.square_images):
                out.append(Problem("ads", f"{which} needs a landscape or square image."))
            if not heads or not descs:
                out.append(
                    Problem("ads", f"{which} needs at least one headline and one description.")
                )
        elif ad.format == "video":
            if not ad.videos:
                out.append(Problem("ads", f"{which} needs at least one YouTube video."))
            if not heads or not descs or not [h for h in ad.long_headlines if h.strip()]:
                out.append(
                    Problem("ads", f"{which} needs a headline, a long headline and a description.")
                )
        else:
            cards = [c for c in ad.cards if (c.get("image") or {}).get("asset")]
            if not 2 <= len(cards) <= 10:
                out.append(Problem("ads", f"{which} needs 2 to 10 cards, each with an image."))
            if not heads or not descs:
                out.append(Problem("ads", f"{which} needs a headline and a description."))
        if any(len(h) > 40 for h in heads):
            out.append(Problem("ads", f"{which} has a headline over 40 characters."))
    if 0 < spec.budget.amount < 5 and spec.budget.type == "daily":
        # Google's floor is 5 USD or the same in the account's currency, which
        # only USD and CAD can be sure of here; elsewhere it is advice.
        out.append(
            Problem(
                "budget",
                "Demand Gen needs a daily budget of at least 5 USD or the same in your currency.",
                blocks=spec.currency in {"USD", "CAD"},
            )
        )
    if (
        spec.locations.mode == "custom"
        and spec.locations.radius
        and not dg.campaign_level_targeting
    ):
        out.append(
            Problem(
                "settings",
                "A radius needs campaign level location targeting in Demand Gen. Turn on"
                ' "Enable campaign level location and language targeting", or use places.',
            )
        )
    return out


def _display(spec: CampaignSpec) -> list[Problem]:
    d = spec.display
    out: list[Problem] = []
    if spec.bidding.focus == "impression_share":
        out.append(Problem("bidding", "Display does not bid for impression share."))
    if not d.marketing_images:
        out.append(Problem("ads", "Add at least one landscape image (1.91:1)."))
    if not d.square_images:
        out.append(Problem("ads", "Add at least one square image (1:1)."))
    if not [h for h in d.headlines if h.strip()]:
        out.append(Problem("ads", "Add at least one short headline."))
    if not d.long_headline.strip():
        out.append(Problem("ads", "Add a long headline."))
    if not [x for x in d.descriptions if x.strip()]:
        out.append(Problem("ads", "Add at least one description."))
    if not (d.business_name or spec.assets.business_name).strip():
        out.append(Problem("ads", "Add your business name."))
    if spec.bidding.strategy == "manual_cpc" and not (d.default_bid or spec.bidding.default_bid):
        out.append(Problem("ad_group", "Manual CPC needs a default bid."))
    return out


def _shopping(spec: CampaignSpec) -> list[Problem]:
    sh = spec.shopping
    out: list[Problem] = []
    if not sh.merchant_id:
        out.append(
            Problem(
                "settings",
                "Choose the Merchant Center account with your products. It has to be linked to"
                " this Google Ads account first.",
            )
        )
    if (
        spec.bidding.focus in {"conversions", "impression_share"}
        and spec.bidding.strategy != "manual_cpc"
    ):
        out.append(
            Problem("bidding", "Shopping bids for clicks, conversion value, or with manual CPC.")
        )
    if spec.bidding.strategy == "manual_cpc" and not (sh.default_bid or spec.bidding.default_bid):
        out.append(Problem("ad_group", "Manual CPC needs a bid for the ad group."))
    return out


def _app(spec: CampaignSpec) -> list[Problem]:
    app = spec.app
    out: list[Problem] = []
    if not app.app_id.strip():
        out.append(Problem("settings", "Choose the app to promote."))
    if not [h for h in app.headlines if h.strip()]:
        out.append(Problem("ads", "Add at least one headline."))
    if not [x for x in app.descriptions if x.strip()]:
        out.append(Problem("ads", "Add at least one description."))
    if any(len(h) > HEADLINE for h in app.headlines):
        out.append(Problem("ads", f"A headline is over {HEADLINE} characters."))
    if app.subtype == "APP_CAMPAIGN_FOR_ENGAGEMENT" and not any(
        s.kind == "user_list" for s in spec.audiences.segments
    ):
        out.append(Problem("settings", "App engagement campaigns need a list of your app's users."))
    if spec.budget.type == "total":
        out.append(Problem("budget", "App campaigns take a daily budget."))
    if app.subtype == "APP_CAMPAIGN_FOR_ENGAGEMENT" and app.focus == "installs":
        out.append(
            Problem("bidding", "An engagement campaign bids for in-app actions, not installs.")
        )
    if (app.focus != "installs" or app.subtype == "APP_CAMPAIGN_FOR_PRE_REGISTRATION") and not (
        app.conversion_actions
    ):
        out.append(
            Problem(
                "bidding",
                "Choose the in-app actions to bid for. Google may refuse the campaign without them.",
                blocks=False,
            )
        )
    return out


def _budget(spec: CampaignSpec) -> list[Problem]:
    out: list[Problem] = []
    if spec.budget.shared:
        return out
    if not spec.budget.amount > 0:
        out.append(Problem("budget", "Set a budget above zero."))
    if spec.budget.type == "total":
        if not (spec.dates.start or spec.dates.end):
            out.append(Problem("budget", "A campaign total budget needs start and end dates."))
        elif spec.dates.end is None:
            out.append(Problem("budget", "A campaign total budget needs an end date."))
    if spec.ai_max.enabled and spec.type == "SEARCH" and 0 < spec.budget.amount < 5:
        out.append(Problem("budget", "AI Max works poorly on a very small budget.", blocks=False))
    return out


#: Which step a refusal from Google belongs to, by the kind of thing refused.
_STEP_OF: Final = {
    "campaign_budget": "budget",
    "campaign": "settings",
    "campaign_criterion": "settings",
    "campaign_shared_set": "settings",
    "shared_set": "settings",
    "shared_criterion": "ai_max",
    "campaign_conversion_goal": "goal",
    "ad_group": "ads",
    "ad_group_criterion": "ads",
    "ad_group_ad": "ads",
    "asset": "ads",
    "campaign_asset": "ads",
    "asset_group": "asset_group",
    "asset_group_asset": "asset_group",
    "asset_group_signal": "asset_group",
    "audience": "asset_group",
}


def step_of(resource_type: str, field: str, campaign_type: str) -> str:
    """The step a Google error about one operation should send the merchant to."""
    if resource_type == "campaign" and any(
        word in field
        for word in ("bidding", "maximize", "target_", "manual_cpc", "target_spend", "Bidding")
    ):
        return "bidding"
    if resource_type == "campaign" and (
        "ai_max" in field or "asset_automation" in field or "text_guidelines" in field
    ):
        return "ai_max" if campaign_type == "SEARCH" else "settings"
    step = _STEP_OF.get(resource_type, "review")
    if campaign_type == "PERFORMANCE_MAX" and step == "ads":
        return "asset_group"
    if campaign_type in {"DEMAND_GEN", "DISPLAY", "SHOPPING"} and resource_type in {
        "ad_group",
        "ad_group_criterion",
        "audience",
    }:
        return "ad_group"
    if campaign_type != "SEARCH" and step == "budget":
        return "bidding" if campaign_type not in {"PERFORMANCE_MAX"} else "budget"
    if campaign_type != "SEARCH" and step == "ai_max":
        return "settings"
    return step
