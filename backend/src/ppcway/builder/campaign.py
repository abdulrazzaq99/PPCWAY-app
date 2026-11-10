"""A new campaign as plain data, and the one request that creates it in Google.

The builder writes a `CampaignPlan`: what the campaign is about, where and in
which language it shows, what it spends, how Google bids, and per theme the
keywords Keyword Planner confirmed and the ad text that passed checking. The
merchant reads it, edits it, and approves it. `operations_for` then turns it
into a single `Together` request -- budget, campaign, places, language,
excluded searches, ad groups, keywords, ads -- that Google applies whole or
not at all, so a launch can never leave half a campaign spending money.

Every field sent was checked against Google Ads API v25's own definitions
before it was written, because one unknown field fails the whole request:

- **The EU political advertising declaration is required** on a new campaign.
  The merchant confirms it on the review screen; nothing is assumed for them.
- **No AI declaration on the ad.** The client's brief asks for
  `synthetic_content_info` on AI-drafted ads, and Google accepts it only on
  image and HTML5 ads -- a responsive search ad carrying it is refused. So the
  disclosure lives where PPCWay controls it: on the review screen and in the
  record of the launch. Recorded in the decision of 6 November.

Search only, as the brief says for the MVP: Google Search, no search partners,
no display network. Shown to people *in* the places chosen, not merely
interested in them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Final

from ppcway.builder.validate import (
    DESCRIPTIONS_LEAST,
    DESCRIPTIONS_WANTED,
    HEADLINES_LEAST,
    HEADLINES_WANTED,
    Business,
)
from ppcway.gateway.port import Doing, Operation, Together

#: How Google bids, by the choice a merchant is offered.
BIDDING: Final[dict[str, dict[str, Any]]] = {
    # Maximize clicks. The safe start for a new campaign: it needs no history,
    # and it does not chase a conversion count that may be mis-set.
    "clicks": {"targetSpend": {}},
    # Maximize conversions. Better once leads are counted properly; it bids
    # towards whatever the account counts as a conversion.
    "leads": {"maximizeConversions": {}},
}

#: The most keywords one theme takes into its ad group. Keyword Planner offers
#: hundreds; the ones people search most are the ones worth paying for first.
MOST_KEYWORDS: Final = 20

#: The most themes one campaign has. Each is an ad group with its own ad.
MOST_THEMES: Final = 5

MATCH: Final = "PHRASE"


@dataclass
class Place:
    """Somewhere the campaign shows, as Google names it."""

    resource: str  # "geoTargetConstants/2124"
    name: str
    kind: str = ""  # "Country", "City", "Region"


@dataclass
class Theme:
    """One ad group: a thing the business does, its keywords and its ad."""

    name: str
    keywords: list[dict[str, Any]] = field(default_factory=list)
    headlines: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    #: Candidates Keyword Planner did not confirm, kept to be shown, never used.
    dropped: list[dict[str, str]] = field(default_factory=list)
    #: Why the ad text came up short, where it did.
    short: str = ""


@dataclass
class CampaignPlan:
    """Everything a new campaign is, before it exists."""

    name: str
    daily_budget: float
    currency: str
    final_url: str
    places: list[Place] = field(default_factory=list)
    language: Place = field(default_factory=lambda: Place("languageConstants/1000", "English"))
    bidding: str = "clicks"
    themes: list[Theme] = field(default_factory=list)
    negatives: list[str] = field(default_factory=list)
    business: Business = field(default_factory=Business)
    #: Whether a model wrote any of the ad text. Shown on the review screen.
    ai_written: bool = False
    #: Set when the merchant confirms this is not EU political advertising.
    not_political: bool = False

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["business"] = {
            k: list(v) if isinstance(v, tuple) else v for k, v in out["business"].items()
        }
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CampaignPlan:
        business = dict(data.get("business") or {})
        for key in ("services", "places", "accreditations", "brand_words", "promises"):
            business[key] = tuple(business.get(key) or ())
        return cls(
            name=str(data.get("name", "")),
            daily_budget=float(data.get("daily_budget") or 0),
            currency=str(data.get("currency", "")),
            final_url=str(data.get("final_url", "")),
            places=[Place(**p) for p in data.get("places") or []],
            language=Place(**(data.get("language") or {"resource": "", "name": ""})),
            bidding=str(data.get("bidding", "clicks")),
            themes=[Theme(**t) for t in data.get("themes") or []],
            negatives=[str(n) for n in data.get("negatives") or []],
            business=Business(**business),
            ai_written=bool(data.get("ai_written")),
            not_political=bool(data.get("not_political")),
        )


def missing(plan: CampaignPlan) -> list[str]:
    """Everything stopping this plan from being launched, in words, together.

    All of them at once: a merchant fixing one thing and only then being told
    about the next is a merchant who gives up on the third.
    """
    out: list[str] = []
    if not plan.name.strip():
        out.append("The campaign needs a name.")
    if plan.daily_budget <= 0:
        out.append("Set a daily budget.")
    if not plan.final_url.startswith(("http://", "https://")):
        out.append("Give the page people land on, starting with https://.")
    if not plan.places:
        out.append("Choose at least one place for the ads to show.")
    if not plan.language.resource:
        out.append("Choose the language your customers search in.")
    if plan.bidding not in BIDDING:
        out.append("Choose how Google should bid.")
    if not plan.themes:
        out.append("The campaign has nothing in it yet.")
    for theme in plan.themes:
        if not theme.keywords:
            out.append(f'"{theme.name}" has no keywords people search for.')
        if len(theme.headlines) < HEADLINES_LEAST:
            out.append(f'"{theme.name}" needs at least {HEADLINES_LEAST} headlines.')
        if len(theme.descriptions) < DESCRIPTIONS_LEAST:
            out.append(f'"{theme.name}" needs at least {DESCRIPTIONS_LEAST} descriptions.')
    if not plan.not_political:
        out.append(
            "Google needs you to confirm the campaign is not political advertising in the EU."
        )
    return out


def operations_for(plan: CampaignPlan, customer_id: str, *, tag: str) -> Together:
    """The whole campaign as one all-or-nothing request.

    `tag` makes the budget's name unique, which Google requires of every
    budget in an account. Temporary ids are negative and only mean anything
    inside this one request.
    """
    budget = f"customers/{customer_id}/campaignBudgets/-1"
    campaign = f"customers/{customer_id}/campaigns/-2"

    ops: list[Operation] = [
        Operation(
            resource_type="campaign_budget",
            doing=Doing.CREATE,
            resource_name=budget,
            fields={
                "name": f"{plan.name} · {tag}",
                "amountMicros": str(round(plan.daily_budget * 1_000_000)),
                "deliveryMethod": "STANDARD",
                "explicitlyShared": False,
            },
        ),
        Operation(
            resource_type="campaign",
            doing=Doing.CREATE,
            resource_name=campaign,
            fields={
                "name": plan.name,
                "status": "ENABLED",
                "advertisingChannelType": "SEARCH",
                "campaignBudget": budget,
                "networkSettings": {
                    "targetGoogleSearch": True,
                    "targetSearchNetwork": False,
                    "targetContentNetwork": False,
                    "targetPartnerSearchNetwork": False,
                },
                "geoTargetTypeSetting": {
                    "positiveGeoTargetType": "PRESENCE",
                    "negativeGeoTargetType": "PRESENCE",
                },
                "containsEuPoliticalAdvertising": ("DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"),
                **BIDDING[plan.bidding],
            },
        ),
    ]
    for place in plan.places:
        ops.append(
            Operation(
                resource_type="campaign_criterion",
                doing=Doing.CREATE,
                fields={"campaign": campaign, "location": {"geoTargetConstant": place.resource}},
            )
        )
    ops.append(
        Operation(
            resource_type="campaign_criterion",
            doing=Doing.CREATE,
            fields={"campaign": campaign, "language": {"languageConstant": plan.language.resource}},
        )
    )
    for word in dict.fromkeys(n.strip().lower() for n in plan.negatives if n.strip()):
        ops.append(
            Operation(
                resource_type="campaign_criterion",
                doing=Doing.CREATE,
                fields={
                    "campaign": campaign,
                    "negative": True,
                    "keyword": {"text": word, "matchType": MATCH},
                },
            )
        )

    for at, theme in enumerate(plan.themes):
        group = f"customers/{customer_id}/adGroups/{-3 - at}"
        ops.append(
            Operation(
                resource_type="ad_group",
                doing=Doing.CREATE,
                resource_name=group,
                fields={
                    "name": theme.name,
                    "campaign": campaign,
                    "status": "ENABLED",
                    "type": "SEARCH_STANDARD",
                },
            )
        )
        for keyword in theme.keywords[:MOST_KEYWORDS]:
            ops.append(
                Operation(
                    resource_type="ad_group_criterion",
                    doing=Doing.CREATE,
                    fields={
                        "adGroup": group,
                        "status": "ENABLED",
                        "keyword": {"text": str(keyword["text"]), "matchType": MATCH},
                    },
                )
            )
        ops.append(
            Operation(
                resource_type="ad_group_ad",
                doing=Doing.CREATE,
                fields={
                    "adGroup": group,
                    "status": "ENABLED",
                    "ad": {
                        "finalUrls": [plan.final_url],
                        "responsiveSearchAd": {
                            "headlines": [{"text": h} for h in theme.headlines[:HEADLINES_WANTED]],
                            "descriptions": [
                                {"text": d} for d in theme.descriptions[:DESCRIPTIONS_WANTED]
                            ],
                        },
                    },
                },
            )
        )
    return Together(customer_id=customer_id, operations=tuple(ops))


def campaign_of(names: tuple[str, ...]) -> str:
    """The new campaign's resource name, out of what Google said it created."""
    return next((n for n in names if "/campaigns/" in n), "")


def in_one_sentence(plan: CampaignPlan) -> str:
    """The review screen's summary, from the plan rather than written by a model."""
    where = _listed([p.name for p in plan.places]) or "nowhere yet"
    searches = _listed([str(k["text"]) for t in plan.themes for k in t.keywords[:1]][:3])
    money = f"{plan.daily_budget:,.2f} {plan.currency}".strip()
    said = f"We'll show your ads to people in {where}"
    if searches:
        said += f" who search for things like {searches}"
    said += f". You'll spend up to {money} a day"
    if plan.final_url:
        said += f", and every click goes to {plan.final_url}"
    return said + "."


def _listed(items: list[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" and {items[-1]}"
