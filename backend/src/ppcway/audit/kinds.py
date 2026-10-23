"""What kind of business this is, and which checks that makes sensible.

The audit used to ask every business the same questions, and some of them were
nonsense. "Six businesses nearby are open twenty four hours, so Google sends
them the night calls" is a real and costly finding for an emergency plumber. It
is noise for a dentist and an insult to a law firm, neither of whom should open
at 3am, and telling them to is bad advice.

So each business gets a kind, and each kind decides three things about every
check: whether it applies at all, how much it moves the score, and what it says
when the plain wording would mislead.

**How the kind is worked out.** Google's Places API returns `primaryType` and
`types[]`, which are stable snake_case strings, and `primaryTypeDisplayName`
and `googleMapsTypeLabel`, which are localized display text. We key on the
stable ones and use the text only to break ties. We do *not* read the category
the owner chose in their Business Profile: that is a different, far larger list
and it is not public, so nothing here may claim to have read it.

**It will be wrong sometimes.** Google has no type at all for several ordinary
trades — heating engineers, pest control, cleaners, landscapers, towing — nor
for software companies or agencies. Those come back as `service`, or as nothing.
So a guess carries its own confidence, the screen shows the person what we
decided, and they can change it. A guess nobody can correct is just a bug with
a nicer name.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger(__name__)


class Kind(str, Enum):
    """The kinds we audit differently. One of these, never a free string."""

    EMERGENCY = "emergency"
    BOOKED = "booked"
    TRADES = "trades"
    RETAIL = "retail"
    ECOMMERCE = "ecommerce"
    FOOD = "food"
    PROFESSIONAL = "professional"
    HEALTH = "health"
    SOFTWARE = "software"
    EDUCATION = "education"
    AUTOMOTIVE = "automotive"
    PROPERTY = "property"
    HOSPITALITY = "hospitality"
    OTHER = "other"


#: What each kind is called on screen, and how somebody recognises themselves
#: in it. The question is "which of these is you?", so the words have to be the
#: ones a person would use about their own business.
SAID: dict[Kind, tuple[str, str]] = {
    Kind.EMERGENCY: (
        "Emergency call-outs",
        "People ring you when something has gone wrong, often out of hours.",
    ),
    Kind.BOOKED: (
        "Appointments and bookings",
        "People book a time with you: a chair, a slot, a session.",
    ),
    Kind.TRADES: (
        "Trades and home improvement",
        "People ask for a quote first, then you do the work.",
    ),
    Kind.RETAIL: ("A shop people come to", "You sell from a place people walk into."),
    Kind.ECOMMERCE: ("An online store", "People buy from your website."),
    Kind.FOOD: ("Restaurant, cafe or takeaway", "People eat in, order in or book a table."),
    Kind.PROFESSIONAL: (
        "Professional services",
        "Law, accounting, consulting, insurance and the like.",
    ),
    Kind.HEALTH: ("Health and medical", "A practice or clinic people are treated at."),
    Kind.SOFTWARE: (
        "Software or business services",
        "You sell to other businesses, mostly online.",
    ),
    Kind.EDUCATION: ("Courses and training", "People enrol, apply or book a place."),
    Kind.AUTOMOTIVE: ("Motor trade", "Selling, hiring, servicing or repairing vehicles."),
    Kind.PROPERTY: ("Property and lettings", "Selling, letting or managing property."),
    Kind.HOSPITALITY: ("Places to stay", "Hotels, guest houses, holiday lets and campsites."),
    Kind.OTHER: ("Something else", "None of these fits, so we will check the basics only."),
}

#: Google's own type strings, checked against its published list on 23 October
#: 2026. Only the ones that tell us something; a type we do not map falls to
#: OTHER and is logged, because Google adds types and never removes them.
BY_TYPE: dict[str, Kind] = {
    # Services that people call in a hurry.
    "plumber": Kind.EMERGENCY,
    "electrician": Kind.EMERGENCY,
    "locksmith": Kind.EMERGENCY,
    # Services where the job is quoted and then done.
    "roofing_contractor": Kind.TRADES,
    "painter": Kind.TRADES,
    "general_contractor": Kind.TRADES,
    "moving_company": Kind.TRADES,
    # Booked time, personal care and pets.
    "hair_salon": Kind.BOOKED,
    "barber_shop": Kind.BOOKED,
    "beauty_salon": Kind.BOOKED,
    "nail_salon": Kind.BOOKED,
    "hair_care": Kind.BOOKED,
    "beautician": Kind.BOOKED,
    "makeup_artist": Kind.BOOKED,
    "body_art_service": Kind.BOOKED,
    "tanning_studio": Kind.BOOKED,
    "foot_care": Kind.BOOKED,
    "massage": Kind.BOOKED,
    "massage_spa": Kind.BOOKED,
    "spa": Kind.BOOKED,
    "sauna": Kind.BOOKED,
    "yoga_studio": Kind.BOOKED,
    "wellness_center": Kind.BOOKED,
    "veterinary_care": Kind.BOOKED,
    "pet_care": Kind.BOOKED,
    "pet_boarding_service": Kind.BOOKED,
    "child_care_agency": Kind.BOOKED,
    "laundry": Kind.BOOKED,
    "tailor": Kind.BOOKED,
    "courier_service": Kind.BOOKED,
    "chauffeur_service": Kind.BOOKED,
    "storage": Kind.BOOKED,
    # Treated, not served.
    "dentist": Kind.HEALTH,
    "dental_clinic": Kind.HEALTH,
    "doctor": Kind.HEALTH,
    "medical_clinic": Kind.HEALTH,
    "medical_center": Kind.HEALTH,
    "medical_lab": Kind.HEALTH,
    "chiropractor": Kind.HEALTH,
    "physiotherapist": Kind.HEALTH,
    "skin_care_clinic": Kind.HEALTH,
    "hospital": Kind.HEALTH,
    "general_hospital": Kind.HEALTH,
    # Advice, sold by the hour or the matter.
    "lawyer": Kind.PROFESSIONAL,
    "accounting": Kind.PROFESSIONAL,
    "insurance_agency": Kind.PROFESSIONAL,
    "consultant": Kind.PROFESSIONAL,
    "marketing_consultant": Kind.PROFESSIONAL,
    "employment_agency": Kind.PROFESSIONAL,
    "travel_agency": Kind.PROFESSIONAL,
    "tour_agency": Kind.PROFESSIONAL,
    "funeral_home": Kind.PROFESSIONAL,
    # Food, whatever shape it takes.
    "restaurant": Kind.FOOD,
    "cafe": Kind.FOOD,
    "coffee_shop": Kind.FOOD,
    "bar": Kind.FOOD,
    "pub": Kind.FOOD,
    "bakery": Kind.FOOD,
    "deli": Kind.FOOD,
    "cafeteria": Kind.FOOD,
    "fast_food_restaurant": Kind.FOOD,
    "food_court": Kind.FOOD,
    "ice_cream_shop": Kind.FOOD,
    "sandwich_shop": Kind.FOOD,
    "meal_takeaway": Kind.FOOD,
    "meal_delivery": Kind.FOOD,
    "food_delivery": Kind.FOOD,
    "catering_service": Kind.FOOD,
    # Shops people walk into.
    "store": Kind.RETAIL,
    "convenience_store": Kind.RETAIL,
    "department_store": Kind.RETAIL,
    "discount_store": Kind.RETAIL,
    "general_store": Kind.RETAIL,
    "grocery_store": Kind.RETAIL,
    "supermarket": Kind.RETAIL,
    "shopping_mall": Kind.RETAIL,
    "clothing_store": Kind.RETAIL,
    "electronics_store": Kind.RETAIL,
    "furniture_store": Kind.RETAIL,
    "hardware_store": Kind.RETAIL,
    "home_goods_store": Kind.RETAIL,
    "home_improvement_store": Kind.RETAIL,
    "book_store": Kind.RETAIL,
    "shoe_store": Kind.RETAIL,
    "jewelry_store": Kind.RETAIL,
    "liquor_store": Kind.RETAIL,
    "pet_store": Kind.RETAIL,
    "sporting_goods_store": Kind.RETAIL,
    "toy_store": Kind.RETAIL,
    "warehouse_store": Kind.RETAIL,
    "food_store": Kind.RETAIL,
    "gift_shop": Kind.RETAIL,
    "market": Kind.RETAIL,
    "florist": Kind.RETAIL,
    "pharmacy": Kind.RETAIL,
    "drugstore": Kind.RETAIL,
    # Vehicles.
    "car_dealer": Kind.AUTOMOTIVE,
    "car_repair": Kind.AUTOMOTIVE,
    "car_wash": Kind.AUTOMOTIVE,
    "car_rental": Kind.AUTOMOTIVE,
    "tire_shop": Kind.AUTOMOTIVE,
    "truck_dealer": Kind.AUTOMOTIVE,
    # Teaching.
    "school": Kind.EDUCATION,
    "primary_school": Kind.EDUCATION,
    "secondary_school": Kind.EDUCATION,
    "preschool": Kind.EDUCATION,
    "university": Kind.EDUCATION,
    "educational_institution": Kind.EDUCATION,
    "academic_department": Kind.EDUCATION,
    "library": Kind.EDUCATION,
    "summer_camp_organizer": Kind.EDUCATION,
    # Property.
    "real_estate_agency": Kind.PROPERTY,
    "apartment_building": Kind.PROPERTY,
    "apartment_complex": Kind.PROPERTY,
    "condominium_complex": Kind.PROPERTY,
    "housing_complex": Kind.PROPERTY,
    # Somewhere to sleep.
    "hotel": Kind.HOSPITALITY,
    "motel": Kind.HOSPITALITY,
    "inn": Kind.HOSPITALITY,
    "hostel": Kind.HOSPITALITY,
    "bed_and_breakfast": Kind.HOSPITALITY,
    "guest_house": Kind.HOSPITALITY,
    "lodging": Kind.HOSPITALITY,
    "resort_hotel": Kind.HOSPITALITY,
    "extended_stay_hotel": Kind.HOSPITALITY,
    "campground": Kind.HOSPITALITY,
    "rv_park": Kind.HOSPITALITY,
    "cottage": Kind.HOSPITALITY,
    "farmstay": Kind.HOSPITALITY,
    "private_guest_room": Kind.HOSPITALITY,
}

#: Types that say nothing about the trade. Google's Table B, plus the catch-all
#: Table A entries. Skipped when picking a type out of the list.
EMPTY_WORDS = {
    "establishment",
    "point_of_interest",
    "food",
    "health",
    "finance",
    "political",
    "geocode",
    "premise",
    "subpremise",
    "street_address",
    "route",
    "landmark",
    "service",
    "association_or_organization",
    "non_profit_organization",
    "corporate_office",
}

#: Words in the Maps label or the business name that settle a close call. The
#: label is localized, so this is a tie-breaker and never the first answer.
URGENT_WORDS = ("emergency", "24 hour", "24-hour", "24/7", "breakdown", "callout", "call-out")

#: Trades Google has no type for at all. Without this, a heating engineer and a
#: pest controller come back as "service" and get a shop's audit.
NAME_WORDS: tuple[tuple[str, Kind], ...] = (
    ("plumb", Kind.EMERGENCY),
    ("locksmith", Kind.EMERGENCY),
    ("towing", Kind.EMERGENCY),
    ("boiler", Kind.EMERGENCY),
    ("heating", Kind.TRADES),
    ("hvac", Kind.TRADES),
    ("roofing", Kind.TRADES),
    ("roofer", Kind.TRADES),
    ("landscap", Kind.TRADES),
    ("pest control", Kind.TRADES),
    ("cleaning", Kind.TRADES),
    ("cleaners", Kind.TRADES),
    ("renovation", Kind.TRADES),
    ("builders", Kind.TRADES),
    ("flooring", Kind.TRADES),
    ("windows", Kind.TRADES),
    ("dental", Kind.HEALTH),
    ("dentist", Kind.HEALTH),
    ("clinic", Kind.HEALTH),
    ("physio", Kind.HEALTH),
    ("law", Kind.PROFESSIONAL),
    ("solicitor", Kind.PROFESSIONAL),
    ("accountant", Kind.PROFESSIONAL),
    ("insurance", Kind.PROFESSIONAL),
    ("software", Kind.SOFTWARE),
    ("app", Kind.SOFTWARE),
    ("digital", Kind.SOFTWARE),
)


@dataclass(frozen=True)
class Guess:
    """What we think this business is, and how sure we are.

    `sure` is not decoration. A guess we are not sure of is shown to the person
    differently, and the wrong-but-confident guess is the one that does damage.
    """

    kind: Kind = Kind.OTHER
    sure: bool = False
    #: The Google type we keyed on, kept so a wrong guess can be understood.
    from_type: str = ""
    #: In plain words, why we said this. Shown to the person.
    because: str = ""

    @property
    def label(self) -> str:
        return SAID[self.kind][0]

    @property
    def about(self) -> str:
        return SAID[self.kind][1]

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "about": self.about,
            "sure": self.sure,
            "from_type": self.from_type,
            "because": self.because,
        }


def first_real(types: list[str] | tuple[str, ...]) -> str:
    """The first type in the list that says something about the trade."""
    for one in types:
        if one and one not in EMPTY_WORDS:
            return one
    return ""


def classify(
    *,
    primary_type: str = "",
    types: list[str] | tuple[str, ...] = (),
    maps_label: str = "",
    business_name: str = "",
    open_24h: bool = False,
) -> Guess:
    """Work out the kind, in the order the signals deserve to be trusted."""
    said = f"{maps_label} {business_name}".lower()

    chosen = primary_type if primary_type and primary_type not in EMPTY_WORDS else ""
    if not chosen:
        chosen = first_real(types)

    kind = BY_TYPE.get(chosen) if chosen else None
    if kind is None and chosen:
        log.info("no kind for Google type %r", chosen)

    if kind is None:
        # Google has no type for this trade. The name is all we have left, and
        # it is a weak signal, so whatever it finds is offered unsurely.
        for word, guessed in NAME_WORDS:
            if word in said:
                return Guess(
                    kind=guessed,
                    sure=False,
                    from_type=chosen,
                    because="We guessed from your name. Change it if we have it wrong.",
                )
        return Guess(
            kind=Kind.OTHER,
            sure=False,
            from_type=chosen,
            because="Google does not say what kind of business this is.",
        )

    # A trade that is sometimes urgent and sometimes booked. Being open round
    # the clock, or saying "emergency", is what tells them apart.
    if kind is Kind.TRADES and (open_24h or any(w in said for w in URGENT_WORDS)):
        kind = Kind.EMERGENCY
    elif kind is Kind.EMERGENCY and not open_24h and not any(w in said for w in URGENT_WORDS):
        # A plumber with ordinary hours and no emergency wording is a booked
        # trade, and should not be told to open at night.
        kind = Kind.TRADES

    return Guess(
        kind=kind,
        sure=True,
        from_type=chosen,
        because=f"Google lists you as “{maps_label or chosen.replace('_', ' ')}”.",
    )


# ---------------------------------------------------------------------------
# What each kind makes of each check.
#
# Three decisions per check, and all three matter:
#
#   applies — whether to run it at all. An online store has no opening hours
#             and cannot have a Google listing, so asking about either is not a
#             hard question, it is a wrong one.
#   weight  — how much it moves the score. Photographs decide where people eat
#             and barely matter to a law firm.
#   instead — what to say when the plain wording would mislead. "Open twenty
#             four hours" is advice to an emergency plumber and an insult to a
#             solicitor; the honest version of that check for a solicitor is
#             about stating office hours and how fast they reply.
#
# Only the departures from the default are written down. Everything unlisted
# runs as it always did, which keeps this table about what is different.
# ---------------------------------------------------------------------------

#: Every check the audit can produce, named once so a typo cannot silently
#: switch one off.
CHECKS = (
    "counting",
    "firstscreen",
    "form",
    "health",
    "local",
    "match",
    "mobile",
    "policy",
    "speed",
    "tags",
    "trust",
    "listing_reviews",
    "listing_photos",
    "listing_hours",
    "listing_24h",
    "listing_website",
    "listing_phone",
    "listing_category",
    "rivals_reviews",
    "rivals_24h",
    "rivals_photos",
    "rivals_rating",
)

#: The checks that only mean anything to a business with a place, or a patch,
#: that customers come to. An online store and a software company have neither.
NEEDS_A_LISTING = (
    "listing_reviews",
    "listing_photos",
    "listing_hours",
    "listing_24h",
    "listing_website",
    "listing_phone",
    "listing_category",
    "rivals_reviews",
    "rivals_24h",
    "rivals_photos",
    "rivals_rating",
)


@dataclass(frozen=True)
class Rule:
    """What one kind makes of one check."""

    applies: bool = True
    #: 0 silences it, 1 is ordinary, above 1 is what this kind is judged on.
    weight: float = 1.0
    #: Replacement wording, when the plain version would mislead this kind.
    instead: str = ""


OFF = Rule(applies=False, weight=0.0)

#: Round-the-clock cover is a real finding for one kind of business and bad
#: advice for all the others, so it is off everywhere except there.
_NO_NIGHTS = {"listing_24h": OFF, "rivals_24h": OFF}

#: Nobody drives to them, so the whole Google listing half is beside the point.
_NO_PLACE = dict.fromkeys(NEEDS_A_LISTING, OFF)

POLICY: dict[Kind, dict[str, Rule]] = {
    Kind.EMERGENCY: {
        "listing_24h": Rule(weight=1.5),
        "rivals_24h": Rule(weight=1.5),
        "listing_phone": Rule(weight=1.5),
        "firstscreen": Rule(weight=1.5, instead="Can somebody ring you without scrolling?"),
        "speed": Rule(weight=1.5),
        "local": Rule(weight=1.5),
        # They ring. A form is a fallback, and judging it harshly says little.
        "form": Rule(weight=0.5),
    },
    Kind.BOOKED: {
        **_NO_NIGHTS,
        "listing_hours": Rule(instead="Do your hours cover the times people book?"),
        "listing_reviews": Rule(weight=1.5),
        "rivals_reviews": Rule(weight=1.5),
        "form": Rule(instead="Can somebody book a time without ringing you?"),
        "local": Rule(weight=0.5),
    },
    Kind.TRADES: {
        **_NO_NIGHTS,
        "listing_hours": Rule(instead="Do your hours say when you answer enquiries?"),
        "listing_photos": Rule(weight=1.5, instead="Photographs of work you have finished"),
        "rivals_photos": Rule(weight=1.5),
        "local": Rule(weight=1.5),
        "match": Rule(weight=1.5, instead="Does each job you do have its own page?"),
        "trust": Rule(weight=1.5),
    },
    Kind.RETAIL: {
        **_NO_NIGHTS,
        "listing_hours": Rule(weight=1.5),
        "listing_photos": Rule(weight=1.5),
        "listing_phone": Rule(weight=1.5),
        "local": OFF,
        "match": Rule(instead="Does each range you sell have its own page?"),
    },
    Kind.ECOMMERCE: {
        **_NO_PLACE,
        "local": OFF,
        "speed": Rule(weight=1.5),
        "counting": Rule(weight=1.5, instead="Is a purchase counted, with what it was worth?"),
        "match": Rule(instead="Does each thing you sell have its own page?"),
        "form": Rule(weight=0.5),
        "firstscreen": Rule(weight=0.5),
    },
    Kind.FOOD: {
        **_NO_NIGHTS,
        "listing_photos": Rule(weight=1.5),
        "rivals_photos": Rule(weight=1.5),
        "listing_reviews": Rule(weight=1.5),
        "rivals_reviews": Rule(weight=1.5),
        "listing_hours": Rule(
            weight=1.5, instead="Do your hours cover the meals people search for?"
        ),
        "local": Rule(weight=0.5, instead="If you deliver, do your pages say where?"),
        "match": Rule(instead="Is your menu a page, not a picture of one?"),
        "trust": Rule(weight=0.5),
    },
    Kind.PROFESSIONAL: {
        **_NO_NIGHTS,
        "listing_hours": Rule(instead="Do your pages say your hours and how fast you reply?"),
        # Five careful reviews is normal here. Telling a firm it is failing
        # against a plumber with four hundred is noise dressed as advice.
        "rivals_reviews": Rule(weight=0.5, instead="Recent reviews, and whether you reply"),
        "listing_photos": Rule(weight=0.5),
        "rivals_photos": OFF,
        "trust": Rule(weight=1.5, instead="Is the firm's registration on the site?"),
        "policy": Rule(weight=1.5),
        "local": Rule(weight=0.5),
        "firstscreen": Rule(instead="Is there a clear way to get in touch?"),
    },
    Kind.HEALTH: {
        **_NO_NIGHTS,
        "listing_hours": Rule(instead="Do your pages say what to do outside opening hours?"),
        "rivals_reviews": Rule(weight=0.5, instead="Recent reviews, and whether you reply"),
        "rivals_photos": OFF,
        # The wording rules for health advertising are strict, and a refusal
        # here costs more than anything else on the page.
        "policy": Rule(weight=1.5),
        "trust": Rule(weight=1.5, instead="Are the people treating patients named and registered?"),
        "form": Rule(instead="Can somebody book an appointment without ringing?"),
        "local": Rule(weight=0.5),
    },
    Kind.SOFTWARE: {
        **_NO_PLACE,
        "local": OFF,
        "counting": Rule(weight=1.5, instead="Is a demo or a trial counted as a conversion?"),
        "match": Rule(instead="Does each thing it does have its own page?"),
        "firstscreen": Rule(instead="Is there a demo or trial without scrolling?"),
        "trust": Rule(instead="Are there customers, case studies or security pages?"),
    },
    Kind.EDUCATION: {
        **_NO_NIGHTS,
        "listing_hours": Rule(weight=0.5),
        "match": Rule(weight=1.5, instead="Does each course have its own page?"),
        "trust": Rule(weight=1.5, instead="Is who accredits you on the site?"),
        "policy": Rule(weight=1.5),
        "local": Rule(weight=0.5),
    },
    Kind.AUTOMOTIVE: {
        **_NO_NIGHTS,
        "listing_hours": Rule(instead="Do your hours cover drop-off and collection?"),
        "listing_photos": Rule(weight=1.5),
        "listing_reviews": Rule(weight=1.5),
        "match": Rule(weight=1.5, instead="Does each vehicle or service have its own page?"),
        "local": Rule(weight=0.5),
    },
    Kind.PROPERTY: {
        **_NO_NIGHTS,
        "listing_hours": Rule(weight=0.5, instead="Do your pages say when viewings happen?"),
        "listing_photos": Rule(weight=1.5),
        "local": Rule(weight=1.5, instead="Does each area you cover have its own page?"),
        "match": Rule(weight=1.5, instead="Does each property have its own page?"),
        "speed": Rule(weight=1.5),
    },
    Kind.HOSPITALITY: {
        **_NO_NIGHTS,
        "listing_photos": Rule(weight=1.5),
        "rivals_photos": Rule(weight=1.5),
        "listing_reviews": Rule(weight=1.5),
        "rivals_reviews": Rule(weight=1.5),
        "listing_hours": Rule(
            weight=0.5, instead="Do your pages say check-in and check-out times?"
        ),
        "local": OFF,
        "match": Rule(instead="Does each room or stay have its own page?"),
    },
    # Nothing is assumed about a business we could not place. It gets the
    # checks that are true of everybody and none of the ones that are not.
    Kind.OTHER: {**_NO_NIGHTS, "local": Rule(weight=0.5)},
}

#: What every kind gets unless it says otherwise.
PLAIN = Rule()


def rule_for(kind: Kind, check: str) -> Rule:
    """What this kind makes of this check."""
    return POLICY.get(kind, {}).get(check, PLAIN)


def applies(kind: Kind, check: str) -> bool:
    """Whether to run a check at all for this kind of business."""
    return rule_for(kind, check).applies


def keep(kind: Kind, findings: list[dict[str, object]]) -> list[dict[str, object]]:
    """Drop the findings this kind of business should never have been asked.

    The wrong question is worse than no question: a solicitor told to open at
    three in the morning stops believing the rest of the report, and they are
    right to.
    """
    kept: list[dict[str, object]] = []
    for one in findings:
        key = str(one.get("key", ""))
        rule = rule_for(kind, key)
        if not rule.applies:
            continue
        if rule.instead:
            one = {**one, "title": rule.instead}
        kept.append(one)
    return kept
