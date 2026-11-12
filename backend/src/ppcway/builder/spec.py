"""A new campaign, setting for setting, the way Google's own "New campaign" flow has it.

On 12 November the client asked for campaign creation to follow Google Ads'
flow exactly: every step and every setting, through every API it needs. The
first builder (`campaign.CampaignPlan`) knew a Search campaign as places,
budget, two bidding choices and ad text. This is the whole of it, written as
the merchant's choices rather than as Google's request body, so the screens
read it and `ops` turns it into the one all-or-nothing request.

**Google's flow as it stands in November 2026, not as its older help pages
show it.** Several settings were retired in 2025 and 2026 and are left out on
purpose, because Google now refuses them: a language on a Search campaign
(refused since late September 2026), the campaign-level broad match setting
(refused since 3 August 2026, folded into AI Max), Enhanced CPC (gone since
March 2025), call-only ads (gone since January 2026), Smart campaigns through
the API (blocked since 23 September 2026) and new Dynamic Search Ads. The
research behind every field is in `docs/reference/campaign-creation/`.

**Google's defaults, not PPCWay's.** Where Google pre-selects something, so
does this: AI Max on for a new Search campaign, search partners and the
Display Network ticked, "Presence or interest" for locations, account goals.
The merchant sees each one and can change it, exactly as in Google Ads.

Stored in `CampaignDraft.plan` with `"v": 2`. A draft without it is the first
builder's and is read by `campaign.CampaignPlan` as before.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

VERSION: Final = 2

#: What Google asks first. The labels are Google's own.
Objective = Literal["sales", "leads", "traffic", "awareness", "app", "local", "none"]

#: The campaign types an app may create through the API in v25. Video and
#: Smart are offered on Google's screen too; the API refuses to create
#: either, so they are shown and explained rather than built (`TYPES`).
CampaignType = Literal["SEARCH", "PERFORMANCE_MAX", "DEMAND_GEN", "DISPLAY", "SHOPPING", "APP"]

#: Google's objective table (support.google.com/google-ads/answer/7450050),
#: with Performance Max under Website traffic as its current step-1 guide has it.
OBJECTIVES: Final[dict[str, dict[str, Any]]] = {
    "sales": {
        "label": "Sales",
        "help": "Drive sales online, in app, by phone or in store",
        "types": ["PERFORMANCE_MAX", "SEARCH", "DISPLAY", "DEMAND_GEN", "SHOPPING", "VIDEO"],
        "goals": True,
    },
    "leads": {
        "label": "Leads",
        "help": "Get leads and other conversions by encouraging customers to take action",
        "types": ["PERFORMANCE_MAX", "SEARCH", "DISPLAY", "DEMAND_GEN", "SHOPPING", "VIDEO"],
        "goals": True,
    },
    "traffic": {
        "label": "Website traffic",
        "help": "Get the right people to visit your website",
        "types": ["PERFORMANCE_MAX", "SEARCH", "DISPLAY", "DEMAND_GEN", "SHOPPING", "VIDEO"],
        "goals": True,
    },
    "awareness": {
        "label": "YouTube reach, views, and engagements",
        "help": "Increase reach and engagement on YouTube",
        "types": ["DISPLAY", "DEMAND_GEN", "VIDEO"],
        "goals": False,
    },
    "app": {
        "label": "App promotion",
        "help": "Get more installs, engagement and pre-registration for your app",
        "types": ["APP"],
        "goals": False,
    },
    "local": {
        "label": "Local store visits and promotions",
        "help": "Drive visits to local stores, including restaurants and dealerships",
        "types": ["PERFORMANCE_MAX", "SHOPPING"],
        "goals": True,
    },
    "none": {
        "label": "Create a campaign without guidance",
        "help": "You'll choose a campaign type next, and can set goals later",
        "types": [
            "SEARCH",
            "PERFORMANCE_MAX",
            "DEMAND_GEN",
            "VIDEO",
            "DISPLAY",
            "SHOPPING",
            "APP",
            "SMART",
        ],
        "goals": True,
    },
}

#: Every type Google's screen shows, and whether the API lets an app create it.
TYPES: Final[dict[str, dict[str, Any]]] = {
    "SEARCH": {
        "label": "Search",
        "help": "Reach customers interested in your product or service with text ads",
        "creatable": True,
    },
    "PERFORMANCE_MAX": {
        "label": "Performance Max",
        "help": "Reach audiences across all of Google with a single campaign",
        "creatable": True,
    },
    "DEMAND_GEN": {
        "label": "Demand Gen",
        "help": "Run ads on YouTube, Gmail, Discover and more",
        "creatable": True,
    },
    "VIDEO": {
        "label": "Video",
        "help": "Reach viewers on YouTube and get conversions",
        "creatable": False,
        "why": (
            "Google does not let apps create Video campaigns: its API has read them"
            " only since April 2025, and it points to Demand Gen for video ads."
        ),
    },
    "DISPLAY": {
        "label": "Display",
        "help": "Reach customers across 3 million sites and apps with engaging creative",
        "creatable": True,
        "note": "Google is moving Display campaigns into Demand Gen through 2026 and 2027.",
    },
    "SHOPPING": {
        "label": "Shopping",
        "help": "Showcase your products to shoppers as they explore what to buy",
        "creatable": True,
        "needs": "A Merchant Center account linked to this Google Ads account.",
    },
    "APP": {
        "label": "App",
        "help": "Drive downloads and grow engagement for your app",
        "creatable": True,
        "needs": "An app in Google Play or the App Store.",
    },
    "SMART": {
        "label": "Smart",
        "help": "Reach customers across Google with ads that are built for you",
        "creatable": False,
        "why": (
            "Google stopped apps creating Smart campaigns on 23 September 2026. It"
            " suggests Performance Max or Search instead."
        ),
    },
}

#: The types PPCWay builds, screens and request both. Google offers more on
#: its step 1; the rest are shown and marked.
BUILT: Final[tuple[str, ...]] = (
    "SEARCH",
    "PERFORMANCE_MAX",
    "DEMAND_GEN",
    "DISPLAY",
    "SHOPPING",
    "APP",
)

#: The order of the left-hand steps after "New campaign", per type, as
#: Google's guides list them. "goal" is step 1 and is not repeated here.
STEPS: Final[dict[str, list[str]]] = {
    "SEARCH": ["bidding", "settings", "ai_max", "generation", "ads", "budget", "review"],
    "PERFORMANCE_MAX": ["bidding", "settings", "asset_group", "budget", "review"],
    "DEMAND_GEN": ["settings", "bidding", "ad_group", "ads", "review"],
    "DISPLAY": ["settings", "bidding", "ad_group", "ads", "review"],
    "SHOPPING": ["settings", "bidding", "ad_group", "review"],
    "APP": ["settings", "bidding", "ads", "review"],
}

STEP_LABELS: Final[dict[str, str]] = {
    "goal": "Campaign type and goal",
    "bidding": "Bidding",
    "settings": "Campaign settings",
    "ai_max": "AI Max",
    "generation": "Keyword and asset generation",
    "ads": "Keywords and ads",
    "asset_group": "Asset group",
    "ad_group": "Ad group",
    "budget": "Budget",
    "review": "Review",
}


def step_labels(campaign_type: str) -> dict[str, str]:
    """The step names Google uses for this type: Demand Gen, Display, Shopping
    and App ask for the budget with bidding, and their ads are just ads."""
    labels = dict(STEP_LABELS)
    if "budget" not in STEPS.get(campaign_type, []):
        labels["bidding"] = "Bidding and budget"
    if campaign_type in {"DEMAND_GEN", "DISPLAY", "APP"}:
        labels["ads"] = "Ads"
    return labels


Match = Literal["BROAD", "PHRASE", "EXACT"]
Pin = Literal["HEADLINE_1", "HEADLINE_2", "HEADLINE_3", "DESCRIPTION_1", "DESCRIPTION_2"]
Day = Literal["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
Device = Literal["DESKTOP", "MOBILE", "TABLET", "CONNECTED_TV"]


class _Part(BaseModel):
    """Every part ignores fields it does not know, so a screen one release
    ahead of the server cannot fail a save, and forbids nothing it has."""

    model_config = ConfigDict(extra="ignore")


class Place(_Part):
    """A place as Google names it: `geoTargetConstants/2124`, "Canada", "Country"."""

    resource: str
    name: str = ""
    kind: str = ""


class Radius(_Part):
    """A circle around a point. Google targets the point, not the address."""

    label: str = ""
    latitude: float
    longitude: float
    radius: float = 10
    units: Literal["KILOMETERS", "MILES"] = "KILOMETERS"


class GoalPair(_Part):
    """One of the account's conversion goals: a category from one origin."""

    category: str
    origin: str
    name: str = ""


class Goals(_Part):
    #: True follows the account's default goals, as Google pre-selects them.
    account_default: bool = True
    #: The goals this campaign bids for when it does not follow the account.
    chosen: list[GoalPair] = Field(default_factory=list)
    #: Every goal the account had when the merchant chose, so a campaign that
    #: picks its own can say "not this one" to each of the others.
    available: list[GoalPair] = Field(default_factory=list)


class Ways(_Part):
    """ "Select the ways you'd like to reach your goal"."""

    website: bool = True
    website_url: str = ""
    calls: bool = False
    phone_country: str = ""
    phone_number: str = ""
    store_visits: bool = False
    app: bool = False
    app_id: str = ""
    app_store: Literal["GOOGLE_APP_STORE", "APPLE_APP_STORE"] = "GOOGLE_APP_STORE"
    lead_forms: bool = False


class Bidding(_Part):
    """ "What do you want to focus on?", the optional target, and the rest.

    `focus` is Google's question; `strategy` is set only when the merchant
    picked "Select a bid strategy directly", which is how manual CPC is reached.
    """

    focus: Literal["conversions", "conversion_value", "clicks", "impression_share"] = "conversions"
    strategy: Literal["", "manual_cpc"] = ""
    set_target: bool = False
    #: Target cost per action, in the account currency.
    target_cpa: float | None = None
    #: Target return on ad spend, as a percentage: 350 means 350%.
    target_roas: float | None = None
    #: Maximum CPC bid limit for "Clicks".
    max_cpc: float | None = None
    impression_location: Literal["ANYWHERE_ON_PAGE", "TOP_OF_PAGE", "ABSOLUTE_TOP_OF_PAGE"] = (
        "ANYWHERE_ON_PAGE"
    )
    impression_percent: float | None = None
    impression_max_cpc: float | None = None
    #: Smart Bidding Exploration for Target ROAS: how far below target, 10 to 30%.
    explore: bool = False
    explore_tolerance: int = 10
    #: Customer acquisition: equal, "Bid higher for new customers", "Bid only for new customers".
    new_customers: Literal["off", "bid_higher", "only"] = "off"
    #: What a new customer is worth beyond the sale, for "Bid higher for new customers".
    new_customer_value: float | None = None
    #: The default ad group bid under manual CPC.
    default_bid: float | None = None
    enhanced: bool = False  # Never sent: Enhanced CPC is gone for Search.


class Networks(_Part):
    search_partners: bool = True
    display: bool = True


class Locations(_Part):
    #: "All countries and territories", the account's own country, or a list.
    mode: Literal["all", "home", "custom"] = "custom"
    home: Place | None = None
    targets: list[Place] = Field(default_factory=list)
    excluded: list[Place] = Field(default_factory=list)
    radius: list[Radius] = Field(default_factory=list)
    #: Who counts as "in" a place. Google's default and recommendation first.
    target_option: Literal["PRESENCE_OR_INTEREST", "PRESENCE"] = "PRESENCE_OR_INTEREST"
    #: Exclusions can only be "Presence" now.
    exclude_option: Literal["PRESENCE"] = "PRESENCE"


class Segment(_Part):
    """An audience segment from the account's library or Google's."""

    kind: Literal["user_list", "user_interest", "custom_audience", "combined_audience"]
    resource: str
    name: str = ""
    excluded: bool = False


class Audiences(_Part):
    #: Observation is what Google recommends for every Search campaign.
    mode: Literal["observation", "targeting"] = "observation"
    segments: list[Segment] = Field(default_factory=list)


class Brand(_Part):
    """A brand from Google's brand library (`BrandSuggestionService`)."""

    id: str
    name: str = ""


class TextGuidelines(_Part):
    #: Up to 25 words or phrases kept out of generated text, 30 characters each.
    term_exclusions: list[str] = Field(default_factory=list)
    #: Up to 40 restrictions, 300 characters each.
    messaging_restrictions: list[str] = Field(default_factory=list)


class AiMax(_Part):
    """AI Max for Search: on by default for every new Search campaign."""

    enabled: bool = True
    search_term_matching: bool = True
    text_customization: bool = True
    final_url_expansion: bool = True
    #: URLs or "URL contains" rules that final URL expansion must not use.
    url_exclusions: list[str] = Field(default_factory=list)
    brand_inclusions: list[Brand] = Field(default_factory=list)
    brand_exclusions: list[Brand] = Field(default_factory=list)
    text_guidelines: TextGuidelines = Field(default_factory=TextGuidelines)


class Schedule(_Part):
    """One ad schedule entry. Up to six per day."""

    day: Day
    start_hour: int = 0
    start_minute: Literal[0, 15, 30, 45] = 0
    end_hour: int = 24
    end_minute: Literal[0, 15, 30, 45] = 0
    #: Bid adjustment in percent, -90 to +900. None means no adjustment.
    bid_adjustment: float | None = None


class UrlOptions(_Part):
    tracking_template: str = ""
    final_url_suffix: str = ""
    #: Up to 8 name and value pairs.
    custom_parameters: list[dict[str, str]] = Field(default_factory=list)


class Keyword(_Part):
    text: str
    match: Match = "BROAD"
    #: What Keyword Planner said about it, where it said anything. Shown, never sent.
    monthly: int = 0
    competition: str = ""
    top_of_page_low: float = 0
    top_of_page_high: float = 0


class AdText(_Part):
    text: str
    pin: Pin | None = None


class SearchAd(_Part):
    """A responsive search ad."""

    final_url: str = ""
    path1: str = ""
    path2: str = ""
    headlines: list[AdText] = Field(default_factory=list)
    descriptions: list[AdText] = Field(default_factory=list)
    #: True when Otto wrote any of it. Shown on the review screen.
    ai_written: bool = False


class AdGroup(_Part):
    name: str
    keywords: list[Keyword] = Field(default_factory=list)
    negatives: list[Keyword] = Field(default_factory=list)
    ads: list[SearchAd] = Field(default_factory=list)
    #: Manual CPC only.
    default_bid: float | None = None
    #: AI Max "locations of interest", targeted inside this ad group only.
    locations_of_interest: list[Place] = Field(default_factory=list)
    #: Keyword Planner's candidates it did not confirm, kept to be shown.
    dropped: list[dict[str, str]] = Field(default_factory=list)
    short: str = ""


class Sitelink(_Part):
    text: str
    description1: str = ""
    description2: str = ""
    final_url: str = ""


class Snippet(_Part):
    header: str
    values: list[str] = Field(default_factory=list)


class PriceItem(_Part):
    header: str
    description: str = ""
    price: float = 0
    unit: Literal["", "PER_HOUR", "PER_DAY", "PER_WEEK", "PER_MONTH", "PER_YEAR", "PER_NIGHT"] = ""
    final_url: str = ""


class Price(_Part):
    type: str = "SERVICES"
    qualifier: Literal["", "FROM", "UP_TO", "AVERAGE"] = ""
    language: str = "en"
    items: list[PriceItem] = Field(default_factory=list)


class Promotion(_Part):
    item: str = ""
    occasion: str = ""
    discount: Literal["percent", "money"] = "percent"
    #: Percent off (10 means 10%) or an amount off in the account currency.
    amount: float = 0
    up_to: bool = False
    details: Literal["none", "code", "orders_over"] = "none"
    code: str = ""
    orders_over: float = 0
    final_url: str = ""
    start: date | None = None
    end: date | None = None
    language: str = "en"


class LeadForm(_Part):
    business_name: str = ""
    headline: str = ""
    description: str = ""
    privacy_policy_url: str = ""
    call_to_action: str = "LEARN_MORE"
    call_to_action_description: str = ""
    #: Google's prefilled field types: FULL_NAME, EMAIL, PHONE_NUMBER, POSTAL_CODE...
    fields: list[str] = Field(default_factory=lambda: ["FULL_NAME", "EMAIL", "PHONE_NUMBER"])
    post_submit_headline: str = ""
    post_submit_description: str = ""


class AppLink(_Part):
    app_id: str = ""
    store: Literal["GOOGLE_APP_STORE", "APPLE_APP_STORE"] = "GOOGLE_APP_STORE"
    link_text: str = ""


class Image(_Part):
    """An image already in the account's asset library.

    Google's screens add an image to the library the moment it is uploaded,
    and so does PPCWay (`assets.upload_image`); the campaign then links it.
    """

    asset: str  # customers/123/assets/456
    url: str = ""
    width: int = 0
    height: int = 0
    name: str = ""


class Assets(_Part):
    """The campaign's assets, which Google shows under the ad."""

    sitelinks: list[Sitelink] = Field(default_factory=list)
    callouts: list[str] = Field(default_factory=list)
    snippets: list[Snippet] = Field(default_factory=list)
    call: bool = False
    call_country: str = ""
    call_number: str = ""
    business_name: str = ""
    logo: Image | None = None
    images: list[Image] = Field(default_factory=list)
    price: Price | None = None
    promotion: Promotion | None = None
    lead_form: LeadForm | None = None
    app: AppLink | None = None


class Budget(_Part):
    type: Literal["daily", "total"] = "daily"
    amount: float = 0
    #: An existing shared budget, by resource name, instead of a new one.
    shared: str = ""
    shared_name: str = ""


class Dates(_Part):
    start: date | None = None
    end: date | None = None


class AssetGroup(_Part):
    """A Performance Max asset group: one before publishing, as in Google's flow."""

    name: str = "Asset group 1"
    final_url: str = ""
    path1: str = ""
    path2: str = ""
    headlines: list[str] = Field(default_factory=list)
    long_headlines: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)
    business_name: str = ""
    call_to_action: str = ""  # empty means "Automated"
    marketing_images: list[Image] = Field(default_factory=list)
    square_images: list[Image] = Field(default_factory=list)
    portrait_images: list[Image] = Field(default_factory=list)
    logos: list[Image] = Field(default_factory=list)
    landscape_logos: list[Image] = Field(default_factory=list)
    #: YouTube video ids, 11 characters each.
    videos: list[str] = Field(default_factory=list)
    search_themes: list[str] = Field(default_factory=list)
    #: Segments for the audience signal, if any.
    signal: list[Segment] = Field(default_factory=list)
    sitelinks: list[Sitelink] = Field(default_factory=list)


class BrandGuidelines(_Part):
    enabled: bool = True
    main_color: str = ""
    accent_color: str = ""
    font: str = ""


class PerformanceMax(_Part):
    asset_group: AssetGroup = Field(default_factory=AssetGroup)
    brand_guidelines: BrandGuidelines = Field(default_factory=BrandGuidelines)
    text_customization: bool = True
    final_url_expansion: bool = True
    url_exclusions: list[str] = Field(default_factory=list)
    brand_exclusions: list[Brand] = Field(default_factory=list)
    excluded_ages: list[str] = Field(default_factory=list)
    excluded_genders: list[str] = Field(default_factory=list)
    text_guidelines: TextGuidelines = Field(default_factory=TextGuidelines)


class DemandGenAd(_Part):
    """One Demand Gen ad: Google's "Image ad", "Video ad" or "Carousel ad"."""

    format: Literal["image", "video", "carousel"] = "image"
    name: str = "Ad 1"
    final_url: str = ""
    headlines: list[str] = Field(default_factory=list)
    #: Video ads only; up to 5, 90 characters.
    long_headlines: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)
    business_name: str = ""
    call_to_action: str = ""
    marketing_images: list[Image] = Field(default_factory=list)
    square_images: list[Image] = Field(default_factory=list)
    portrait_images: list[Image] = Field(default_factory=list)
    logos: list[Image] = Field(default_factory=list)
    #: YouTube video ids for a video ad.
    videos: list[str] = Field(default_factory=list)
    #: Carousel cards: an image each, a headline and the button's words.
    cards: list[dict[str, Any]] = Field(default_factory=list)


class DemandGen(_Part):
    """Demand Gen's steps: targeting, the ad group's channels and audience, the ads."""

    #: "Enable campaign level location and language targeting". Off by default,
    #: which keeps Google's upgraded targeting: places and languages per ad group.
    campaign_level_targeting: bool = False
    ad_group_name: str = "Ad group 1"
    #: "All Google channels" (recommended) or "Let me choose".
    channels: Literal["all", "choose"] = "all"
    selected: list[str] = Field(
        default_factory=lambda: [
            "youtube_in_stream",
            "youtube_in_feed",
            "youtube_shorts",
            "discover",
            "gmail",
            "display",
        ]
    )
    optimized_targeting: bool = True
    segments: list[Segment] = Field(default_factory=list)
    ads: list[DemandGenAd] = Field(default_factory=lambda: [DemandGenAd()])
    #: Target CPC, offered only when bidding for clicks.
    target_cpc: float | None = None


class Display(_Part):
    """Display's ad group and its responsive display ad."""

    ad_group_name: str = "Ad group 1"
    optimized_targeting: bool = True
    segments: list[Segment] = Field(default_factory=list)
    #: Content keywords, which tell Google what pages to look for.
    keywords: list[str] = Field(default_factory=list)
    default_bid: float | None = None
    final_url: str = ""
    headlines: list[str] = Field(default_factory=list)
    long_headline: str = ""
    descriptions: list[str] = Field(default_factory=list)
    business_name: str = ""
    call_to_action: str = ""
    marketing_images: list[Image] = Field(default_factory=list)
    square_images: list[Image] = Field(default_factory=list)
    logos: list[Image] = Field(default_factory=list)
    landscape_logos: list[Image] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)


class Shopping(_Part):
    """A standard Shopping campaign: products from a linked Merchant Center."""

    merchant_id: int | None = None
    feed_label: str = ""
    #: Google's campaign priority, Low 0, Medium 1, High 2.
    priority: Literal[0, 1, 2] = 0
    enable_local: bool = False
    ad_group_name: str = "Ad group 1"
    default_bid: float | None = None


class App(_Part):
    """An App campaign for installs, engagement or pre-registration."""

    subtype: Literal[
        "APP_CAMPAIGN", "APP_CAMPAIGN_FOR_ENGAGEMENT", "APP_CAMPAIGN_FOR_PRE_REGISTRATION"
    ] = "APP_CAMPAIGN"
    app_id: str = ""
    store: Literal["GOOGLE_APP_STORE", "APPLE_APP_STORE"] = "GOOGLE_APP_STORE"
    #: "What do you want to focus on?": installs, in-app actions, in-app action value.
    focus: Literal["installs", "in_app_actions", "in_app_value"] = "installs"
    #: Target cost per install or per action, or target return, by focus.
    target_cpa: float | None = None
    target_roas: float | None = None
    ad_group_name: str = "Ad group 1"
    headlines: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)
    images: list[Image] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)
    #: The in-app conversion actions to bid for, by resource name. Google asks
    #: for them for in-app actions, in-app value and pre-registration.
    conversion_actions: list[str] = Field(default_factory=list)


class Generation(_Part):
    """ "Keyword and asset generation": what Otto reads before it writes."""

    url: str = ""
    summary: str = ""
    services: list[str] = Field(default_factory=list)
    kind: str = ""
    promises: list[str] = Field(default_factory=list)
    done: bool = False


class CampaignSpec(_Part):
    """Everything a new campaign is, in the order Google asks for it."""

    v: int = VERSION
    objective: Objective = "none"
    type: CampaignType = "SEARCH"
    goals: Goals = Field(default_factory=Goals)
    ways: Ways = Field(default_factory=Ways)
    name: str = ""
    #: None until the merchant answers; Google will not take a campaign without it.
    eu_political: bool | None = None
    currency: str = ""
    time_zone: str = ""

    bidding: Bidding = Field(default_factory=Bidding)
    networks: Networks = Field(default_factory=Networks)
    locations: Locations = Field(default_factory=Locations)
    #: Performance Max, Demand Gen, Display and App only. Search has none now.
    languages: list[Place] = Field(
        default_factory=lambda: [Place(resource="languageConstants/1000", name="English")]
    )
    audiences: Audiences = Field(default_factory=Audiences)
    ai_max: AiMax = Field(default_factory=AiMax)
    dates: Dates = Field(default_factory=Dates)
    schedule: list[Schedule] = Field(default_factory=list)
    #: Bid adjustment per device in percent; -100 stops ads on it.
    devices: dict[str, float] = Field(default_factory=dict)
    url_options: UrlOptions = Field(default_factory=UrlOptions)
    ip_exclusions: list[str] = Field(default_factory=list)
    ad_rotation: Literal["OPTIMIZE", "ROTATE_FOREVER"] = "OPTIMIZE"
    negatives: list[Keyword] = Field(default_factory=list)
    #: Existing shared negative keyword lists to attach, by resource name.
    negative_lists: list[dict[str, str]] = Field(default_factory=list)

    generation: Generation = Field(default_factory=Generation)
    ad_groups: list[AdGroup] = Field(default_factory=list)
    assets: Assets = Field(default_factory=Assets)
    budget: Budget = Field(default_factory=Budget)

    pmax: PerformanceMax = Field(default_factory=PerformanceMax)
    demand_gen: DemandGen = Field(default_factory=DemandGen)
    display: Display = Field(default_factory=Display)
    shopping: Shopping = Field(default_factory=Shopping)
    app: App = Field(default_factory=App)

    #: What the copy checks read (`validate.Business`), as data.
    business: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_search(self) -> bool:
        return self.type == "SEARCH"

    @property
    def is_pmax(self) -> bool:
        return self.type == "PERFORMANCE_MAX"

    @property
    def final_url(self) -> str:
        """The landing page the campaign is about, wherever it was given."""
        if self.is_pmax and self.pmax.asset_group.final_url:
            return self.pmax.asset_group.final_url
        return self.ways.website_url or self.generation.url

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def is_v2(plan: dict[str, Any] | None) -> bool:
    return bool(plan) and int((plan or {}).get("v") or 0) >= VERSION


def new_spec(
    *,
    objective: str,
    type_: str,
    name: str,
    website: str,
    currency: str,
    time_zone: str,
    home: Place | None = None,
) -> CampaignSpec:
    """A campaign with Google's own defaults filled in, before step 2."""
    spec = CampaignSpec.model_validate(
        {
            "objective": objective if objective in OBJECTIVES else "none",
            "type": type_,
            "name": name.strip(),
            "currency": currency,
            "time_zone": time_zone,
            "ways": {"website": True, "website_url": website.strip()},
            "generation": {"url": website.strip()},
        }
    )
    if home is not None:
        spec.locations = Locations(mode="home", home=home)
    if spec.is_pmax:
        spec.pmax.asset_group.final_url = website.strip()
    if spec.type == "DISPLAY":
        spec.display.final_url = website.strip()
    if spec.type == "SHOPPING":
        # Shopping bids for clicks or value; Google pre-selects maximise clicks.
        spec.bidding.focus = "clicks"
        spec.languages = []
    if objective == "traffic":
        spec.bidding.focus = "clicks"
    if spec.objective == "awareness":
        spec.bidding.focus = "conversions"
    return spec
